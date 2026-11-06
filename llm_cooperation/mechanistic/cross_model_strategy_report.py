"""Versioned, CPU-only per-strategy held-out report for saved cross-model runs.

This additive report reads hash-verified full-run activations. It never writes to
the plan, evidence directory, original Qwen report, or scientific analysis output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from . import cross_model_replication as cm
from .contrastive_mapping import STRATEGIES


REPORT_VERSION = "cross-model-strategy-heldout-v1"
CS = (0.01, 0.1, 1.0, 10.0)


def _folds(groups: np.ndarray):
    from sklearn.model_selection import GroupKFold

    unique = len(set(groups))
    if unique < 2:
        raise ValueError("At least two discovery groups are needed for grouped fitting")
    return GroupKFold(min(4, unique)).split(np.zeros(len(groups)), groups=groups)


def _probabilities(rows, x, y, groups, train, test, *, feature_kind: str, activation=None):
    """Select binary logistic C on discovery groups; optionally append activations."""
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler

    texts = np.asarray([r["action_text"] for r in rows], dtype=object)[:, None]
    numeric = np.asarray(x, dtype=float)
    if activation is not None:
        numeric = np.column_stack([numeric, np.asarray(activation, dtype=float)])
    data = np.column_stack([texts, numeric.astype(object)])
    transformers = []
    if feature_kind == "length":
        transformers.append(("length", Pipeline([
            ("poly", PolynomialFeatures(2, include_bias=False)),
            ("scale", StandardScaler()),
        ]), list(range(1, 5))))
    elif feature_kind == "lexical":
        transformers.append(("lexical", TfidfVectorizer(
            ngram_range=(1, 2), max_features=2048, sublinear_tf=True,
        ), 0))
    elif feature_kind != "activation":
        raise ValueError("feature_kind must be length, lexical, or activation")
    if feature_kind == "activation" and activation is None:
        raise ValueError("Activation features are required for activation-only performance")
    if activation is not None:
        start = 5 if feature_kind == "length" else 1
        transformers.append(("activation", StandardScaler(), list(range(start, data.shape[1]))))

    def make(c):
        return Pipeline([
            ("features", ColumnTransformer(transformers, sparse_threshold=1)),
            ("classifier", LogisticRegression(C=c, max_iter=1000, random_state=cm.SEED)),
        ])

    train_indices = np.flatnonzero(train)
    train_groups = groups[train]
    scores = []
    for c in CS:
        fold_losses = []
        for a, b in _folds(train_groups):
            model = make(c).fit(data[train_indices[a]], y[train_indices[a]])
            p = model.predict_proba(data[train_indices[b]])[:, 1]
            loss = -np.log(np.maximum(np.where(y[train_indices[b]] == 1, p, 1 - p), 1e-15))
            fold_losses.append(float(np.mean([
                loss[train_groups[b] == g].mean() for g in sorted(set(train_groups[b]))
            ])))
        scores.append(float(np.mean(fold_losses)))
    c = CS[int(np.argmin(scores))]
    fitted = make(c).fit(data[train], y[train])
    probs = fitted.predict_proba(data[test])[:, 1]
    return probs, {"C": c, "grouped_cv_log_loss": scores}


def build_report(plan, run):
    """Recompute held-out one-vs-rest performance and conditional gains on CPU."""
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                                 f1_score, precision_score, recall_score,
                                 roc_auc_score)

    run_manifest, rows, arrays = cm.load_run(plan, run)
    sids, meta, centered = cm.scenario_center(rows, arrays)
    byid = {(r["scenario_id"], r["strategy"]): r for r in rows}
    ordered = [byid[(sid, strategy)] for sid in sids for strategy in STRATEGIES]
    state = cm.read(Path(plan) / f"{run_manifest['key']}_tokenization.json")
    token = {entry["prompt_id"]: entry for entry in state}
    lengths = np.asarray([
        [token[r["prompt_id"]]["action_tokens"], token[r["prompt_id"]]["prompt_tokens"],
         r["action_word_count"], r["action_char_count"]]
        for r in ordered
    ], dtype=float)
    groups_by_split = {
        "family": ("split", "group_key"),
        "domain": ("domain_split", "domain"),
    }
    report = {
        "version": REPORT_VERSION,
        "model": run_manifest["model"],
        "run_manifest_sha256": cm.sha(Path(run) / "manifest.json"),
        "run_evidence_hashes_sha256": cm.sha(Path(run) / "evidence_hashes.json"),
        "plan_manifest_sha256": cm.sha(Path(plan) / "manifest.json"),
        "source_analysis": "Independent CPU recomputation from verified saved FP32 activations; source plan and evidence are read-only.",
        "target": "One-vs-rest held-out strategy prediction from scenario-centered residual activations.",
        "conditional_gain": "Per-strategy held-out log-loss gain in bits/action for length+activation versus length-only; both models tune C on discovery groups only.",
        "splits": {},
    }
    for split_name, (split_field, group_field) in groups_by_split.items():
        train = np.asarray([r[split_field] == "discovery" for r in meta])
        groups_scenario = np.asarray([r[group_field] for r in meta], dtype=object)
        groups = np.repeat(groups_scenario, 4)
        train_rows = np.repeat(train, 4)
        test_rows = ~train_rows
        y4 = np.tile(np.arange(4), len(sids))
        split = {"heldout_clusters": sorted(set(groups[test_rows])), "layers": []}
        for layer, depth in enumerate(cm.DEPTHS):
            activation = centered[:, :, layer].reshape(-1, centered.shape[-1])
            layer_row = {"target_depth": depth, "block_index": run_manifest["indices"][layer], "strategies": {}}
            for si, strategy in enumerate(STRATEGIES):
                binary_y = (y4 == si).astype(int)
                perf_prob, perf_cv = _probabilities(
                    ordered, lengths, binary_y, groups, train_rows, test_rows,
                    feature_kind="activation", activation=activation,
                )
                base_prob, base_cv = _probabilities(
                    ordered, lengths, binary_y, groups, train_rows, test_rows,
                    feature_kind="length",
                )
                truth = binary_y[test_rows]
                prediction = (perf_prob >= 0.5).astype(int)
                gains = np.log2(
                    np.maximum(np.where(truth == 1, perf_prob, 1 - perf_prob), 1e-15)
                    / np.maximum(np.where(truth == 1, base_prob, 1 - base_prob), 1e-15)
                )
                cluster_metrics = {}
                for group in split["heldout_clusters"]:
                    mask = groups[test_rows] == group
                    cluster_metrics[str(group)] = {
                        "n": int(mask.sum()),
                        "accuracy": float(accuracy_score(truth[mask], prediction[mask])),
                        "balanced_accuracy": float(balanced_accuracy_score(truth[mask], prediction[mask])),
                        "precision": float(precision_score(truth[mask], prediction[mask], zero_division=0)),
                        "recall": float(recall_score(truth[mask], prediction[mask], zero_division=0)),
                        "f1": float(f1_score(truth[mask], prediction[mask], zero_division=0)),
                        "conditional_gain_bits_per_action": float(gains[mask].mean()),
                    }
                layer_row["strategies"][strategy] = {
                    "heldout": {
                        "n": int(test_rows.sum()),
                        "accuracy": float(accuracy_score(truth, prediction)),
                        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
                        "precision": float(precision_score(truth, prediction, zero_division=0)),
                        "recall": float(recall_score(truth, prediction, zero_division=0)),
                        "f1": float(f1_score(truth, prediction, zero_division=0)),
                        "roc_auc": float(roc_auc_score(truth, perf_prob)),
                        "conditional_gain_bits_per_action": float(gains.mean()),
                        "conditional_gain_cluster_equal_weighted": float(np.mean([
                            cluster_metrics[str(g)]["conditional_gain_bits_per_action"]
                            for g in split["heldout_clusters"]
                        ])),
                        "metrics_by_cluster": cluster_metrics,
                    },
                    "discovery_selection": {"performance": perf_cv, "length_baseline": base_cv},
                }
            split["layers"].append(layer_row)
        report["splits"][split_name] = split
    return report


def write_report(plan, run, output):
    out = Path(output)
    if out.exists():
        raise FileExistsError(out)
    report = build_report(plan, run)
    out.mkdir(parents=True)
    cm.write(out / "strategy_heldout_report.json", report)
    lines = [
        f"# Per-strategy held-out report ({REPORT_VERSION})", "",
        f"Model: `{report['model']['model_id']}` revision `{report['model']['revision']}`", "",
        "CPU-only additive analysis of hash-verified full-run activations. Each score is one-vs-rest and each conditional gain is held-out log-loss improvement over length-only features, in bits/action. Hyperparameters are selected using discovery groups only.", "",
    ]
    for split, data in report["splits"].items():
        lines += [f"## {split.title()} held out", "", "| Depth | Strategy | Balanced accuracy | F1 | AUROC | Conditional gain (bits/action) |", "|---:|---|---:|---:|---:|---:|"]
        for layer in data["layers"]:
            for strategy, values in layer["strategies"].items():
                m = values["heldout"]
                lines.append(f"| {layer['target_depth']:.3f} | {strategy} | {m['balanced_accuracy']:.3f} | {m['f1']:.3f} | {m['roc_auc']:.3f} | {m['conditional_gain_cluster_equal_weighted']:.4f} |")
        lines.append("")
    (out / "strategy_heldout_report.md").write_text("\n".join(lines) + "\n", encoding="utf8", newline="\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_report(args.plan, args.run, args.output)


if __name__ == "__main__":
    main()
