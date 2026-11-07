"""Offline, family-held-out paired analysis. No model loading or inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .lexical_pilot import STRATEGIES, SEED, sha, read_json, write_json
from .lexical_pilot_run import verify_plan


def family_weights(groups):
    groups = np.asarray(groups)
    return np.array(
        [len(groups) / (len(set(groups)) * sum(groups == g)) for g in groups]
    )


def macro_accuracy(y, pred, groups):
    return float(
        np.mean(
            [np.mean(pred[groups == g] == y[groups == g]) for g in sorted(set(groups))]
        )
    )


def fit_nested(x, y, groups, kind, seed=SEED):
    """All preprocessing and C selection are contained in training families."""
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import GroupKFold

    groups = np.asarray(groups)
    y = np.asarray(y)
    if len(set(groups)) < 2:
        raise ValueError("Need >=2 training families for nested selection")

    def create(c):
        prep = (
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
            if kind == "lexical"
            else StandardScaler()
        )
        return make_pipeline(
            prep, LogisticRegression(C=c, max_iter=2000, random_state=seed)
        )

    scores = []
    for c in (0.01, 0.1, 1.0, 10.0):
        values = []
        for tr, va in GroupKFold(n_splits=min(4, len(set(groups)))).split(x, y, groups):
            model = create(c)
            model.fit(
                x[tr],
                y[tr],
                logisticregression__sample_weight=family_weights(groups[tr]),
            )
            values.append(macro_accuracy(y[va], model.predict(x[va]), groups[va]))
        scores.append(float(np.mean(values)))
    c = (0.01, 0.1, 1.0, 10.0)[int(np.argmax(scores))]
    model = create(c)
    model.fit(x, y, logisticregression__sample_weight=family_weights(groups))
    return model, {"C": c, "cv_accuracy": scores}


def cosine(a, b):
    scale = np.linalg.norm(a) * np.linalg.norm(b)
    return None if scale <= 1e-12 else float(np.clip(np.dot(a, b) / scale, -1, 1))


def angle(c):
    return None if c is None else float(np.degrees(np.arccos(c)))


def interval(values, alpha=0.05, n_boot=2000, seed=SEED):
    values = np.asarray([v for v in values if v is not None], dtype=float)
    if not len(values):
        return {"mean": None, "lower": None, "upper": None, "n_families": 0}
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), size=(n_boot, len(values)))].mean(
        axis=1
    )
    return {
        "mean": float(values.mean()),
        "lower": float(np.quantile(means, alpha / 2)),
        "upper": float(np.quantile(means, 1 - alpha / 2)),
        "n_families": len(values),
        "confidence": 1 - alpha,
    }


def load_run(plan, run):
    plan, run = Path(plan), Path(run)
    pm = verify_plan(plan)
    rm = read_json(run / "manifest.json")
    if sha(__file__) != pm["analysis_sha256"]:
        raise ValueError(
            "Analysis changed since freeze; prepare a documented new analysis version"
        )
    if rm.get("mock") or rm.get("status") != "completed":
        raise ValueError("Scientific analyzer accepts only completed non-mock runs")
    for k in (
        "target_model",
        "target_revision",
        "prompts_sha256",
        "source_packet_manifest_sha256",
        "analysis_sha256",
    ):
        if rm.get(k) != pm[k]:
            raise ValueError(f"Run/plan mismatch: {k}")
    if (
        rm.get("model_id") != pm["target_model"]
        or rm.get("model_revision") != pm["target_revision"]
    ):
        raise ValueError("Executed model/revision mismatch")
    if rm.get("dtype") != "float32" or (
        rm.get("num_layers"),
        rm.get("hidden_size"),
    ) != (28, 1536):
        raise ValueError("Unexpected numerical precision or architecture")
    if sha(run / "evidence_hashes.json") != rm["evidence_hashes_sha256"]:
        raise ValueError("Evidence index hash mismatch")
    hashes = read_json(run / "evidence_hashes.json")
    if (run / "prompts.jsonl").read_bytes() != (plan / "prompts.jsonl").read_bytes():
        raise ValueError("Run prompt bytes differ from plan")
    rows = [
        json.loads(line)
        for line in (plan / "prompts.jsonl").read_text(encoding="utf8").splitlines()
    ]
    expected = {"prompts.jsonl"} | {f"activations/{p['prompt_id']}.npz" for p in rows}
    if (
        set(hashes) != expected
        or len(rows) != pm["num_prompts"]
        or len({p["prompt_id"] for p in rows}) != len(rows)
    ):
        raise ValueError("Evidence inventory mismatch")
    if {p.name for p in (run / "activations").glob("*.npz")} != {
        f"{p['prompt_id']}.npz" for p in rows
    }:
        raise ValueError("Missing or unexpected activation file")
    for name, expected_hash in hashes.items():
        if sha(run / name) != expected_hash:
            raise ValueError(f"Evidence hash mismatch: {name}")
    arrays = {}
    for row in rows:
        with np.load(
            run / "activations" / f"{row['prompt_id']}.npz", allow_pickle=False
        ) as f:
            arr = f["residual"]
        if arr.shape != (28, 1536) or not np.isfinite(arr).all():
            raise ValueError("Invalid activation tensor")
        arrays[row["prompt_id"]] = arr.astype(float)
    return pm, rows, read_json(plan / "panels.json"), arrays


def assemble(rows, panels, arrays, layers):
    from sklearn.preprocessing import PolynomialFeatures

    by_id = {r["prompt_id"]: r for r in rows}
    data = {}
    for cond in sorted({p["condition"] for p in panels}):
        ps = sorted(
            [p for p in panels if p["condition"] == cond],
            key=lambda p: p["scenario_id"],
        )
        x, lens, texts, changed, groups, sids = [], [], [], [], [], []
        for p in ps:
            rs = [by_id[p["prompt_ids"][st]] for st in STRATEGIES]
            tensor = np.stack([arrays[r["prompt_id"]][layers] for r in rs])
            tensor -= tensor.mean(axis=0, keepdims=True)
            x.extend(tensor)
            lens.extend(
                [
                    [
                        r["measurement"][f]
                        for f in (
                            "action_tokens",
                            "prompt_tokens",
                            "words",
                            "characters",
                        )
                    ]
                    for r in rs
                ]
            )
            texts.extend(r["action_text"] for r in rs)
            changed.extend(st in p.get("changed_strategies", []) for st in STRATEGIES)
            groups.extend([p["family"]] * 4)
            sids.extend([p["scenario_id"]] * 4)
        data[cond] = {
            "x": np.array(x),
            "length": PolynomialFeatures(2, include_bias=False).fit_transform(lens),
            "lexical": np.array(texts),
            "changed": np.array(changed),
            "groups": np.array(groups),
            "sids": np.array(sids),
            "y": np.tile(np.arange(4), len(ps)),
        }
    first = next(iter(data.values()))
    for d in data.values():
        if not np.array_equal(d["sids"], first["sids"]) or not np.array_equal(
            d["groups"], first["groups"]
        ):
            raise ValueError(
                "Analysis requires identical complete scenario/family inventories across conditions"
            )
    return data


def direction(x, y, groups):
    return np.mean(
        [
            x[(groups == g) & (y == 0)].mean(axis=0)
            - x[(groups == g) & (y != 0)].mean(axis=0)
            for g in sorted(set(groups))
        ],
        axis=0,
    )


def evaluate(data, layers=(18, 22), n_boot=2000, progress=True):
    from sklearn.metrics import f1_score

    groups = data["original"]["groups"]
    families = sorted(set(groups))
    if len(families) < 6:
        raise ValueError("At least six complete families required")
    results, predictions = [], []
    for train_cond, train in data.items():
        # Training on a selectively corrupted strategy can create an easy shortcut.
        # Cross-perturbation fits remain descriptive and are prominently marked.
        for held in families:
            tr = groups != held
            te = groups == held
            assert not set(groups[tr]) & set(groups[te])
            base_models = {
                kind: fit_nested(train[kind][tr], train["y"][tr], groups[tr], kind)
                for kind in ("length", "lexical")
            }
            for li, layer in enumerate(layers):
                xm = train["x"][:, li, :]
                activation_model, hp = fit_nested(
                    xm[tr], train["y"][tr], groups[tr], "activation"
                )
                joint = np.concatenate([train["length"], xm], axis=1)
                joint_model, joint_hp = fit_nested(
                    joint[tr], train["y"][tr], groups[tr], "joint"
                )
                train_dir = direction(xm[tr], train["y"][tr], groups[tr])
                original_dir = direction(
                    data["original"]["x"][te, li], train["y"][te], groups[te]
                )
                for test_cond, test in data.items():
                    xv = test["x"][te, li]
                    y = test["y"][te]
                    prob = activation_model.predict_proba(xv)
                    pred = activation_model.classes_[prob.argmax(axis=1)]
                    lp = base_models["length"][0].predict_proba(test["length"][te])
                    lex = base_models["lexical"][0].predict(test["lexical"][te])
                    jp = joint_model.predict_proba(
                        np.concatenate([test["length"][te], xv], axis=1)
                    )
                    # classes_ is checked to avoid treating a missing-class column as label 0.
                    for model in (
                        activation_model,
                        base_models["length"][0],
                        joint_model,
                    ):
                        if list(model.classes_) != [0, 1, 2, 3]:
                            raise ValueError(
                                "All four classes must be present in every training fold"
                            )
                    ll = -np.log2(np.maximum(lp[np.arange(len(y)), y], 1e-15))
                    jl = -np.log2(np.maximum(jp[np.arange(len(y)), y], 1e-15))
                    target_dir = direction(xv, y, groups[te])
                    align = cosine(train_dir, target_dir)
                    stable = cosine(original_dir, target_dir)
                    changed = test["changed"][te]
                    rec = {
                        "train_condition": train_cond,
                        "test_condition": test_cond,
                        "family": held,
                        "layer": layer,
                        "accuracy": float(np.mean(pred == y)),
                        "macro_f1": float(f1_score(y, pred, average="macro")),
                        "recall": {
                            STRATEGIES[i]: float(np.mean(pred[y == i] == i))
                            for i in range(4)
                        },
                        "length_accuracy": float(np.mean(lp.argmax(axis=1) == y)),
                        "lexical_accuracy": float(np.mean(lex == y)),
                        "conditional_gain_bits": float(np.mean(ll - jl)),
                        "length_loss_bits": float(ll.mean()),
                        "length_plus_activation_loss_bits": float(jl.mean()),
                        "alignment": align,
                        "angle_degrees": angle(align),
                        "paired_direction_stability": stable,
                        "paired_angle_degrees": angle(stable),
                        "changed_only_accuracy": float(
                            np.mean(pred[changed] == y[changed])
                        )
                        if changed.any()
                        else None,
                        "changed_count": int(changed.sum()),
                        "probe_hyperparameters": hp,
                        "joint_hyperparameters": joint_hp,
                        "length_hyperparameters": base_models["length"][1],
                        "lexical_hyperparameters": base_models["lexical"][1],
                    }
                    results.append(rec)
                    for i, sid in enumerate(test["sids"][te]):
                        predictions.append(
                            {
                                "train_condition": train_cond,
                                "test_condition": test_cond,
                                "family": held,
                                "layer": layer,
                                "scenario_id": str(sid),
                                "strategy": STRATEGIES[int(y[i])],
                                "predicted_strategy": STRATEGIES[int(pred[i])],
                                "probabilities": prob[i].tolist(),
                                "changed": bool(changed[i]),
                            }
                        )
        if progress:
            print(f"Completed held-out-family fits from {train_cond}", flush=True)
    indexed = {
        (r["train_condition"], r["test_condition"], r["family"], r["layer"]): r
        for r in results
    }
    for r in results:
        original = indexed[(r["train_condition"], "original", r["family"], r["layer"])]
        r["paired_accuracy_change"] = r["accuracy"] - original["accuracy"]
        r["paired_cooperation_recall_change"] = (
            r["recall"]["COOPERATE"] - original["recall"]["COOPERATE"]
        )
        if r["test_condition"] == "low_ablation" and "random_deletion" in data:
            other = indexed[
                (r["train_condition"], "random_deletion", r["family"], r["layer"])
            ]
            r["low_minus_random_accuracy"] = r["accuracy"] - other["accuracy"]
            r["low_minus_random_cooperation_recall"] = (
                r["recall"]["COOPERATE"] - other["recall"]["COOPERATE"]
            )
    summary = []
    metrics = (
        "accuracy",
        "macro_f1",
        "length_accuracy",
        "lexical_accuracy",
        "conditional_gain_bits",
        "alignment",
        "angle_degrees",
        "paired_direction_stability",
        "paired_angle_degrees",
        "paired_accuracy_change",
        "paired_cooperation_recall_change",
        "changed_only_accuracy",
        "low_minus_random_accuracy",
        "low_minus_random_cooperation_recall",
    )
    for train_cond in data:
        for test_cond in data:
            for layer in layers:
                rs = [
                    r
                    for r in results
                    if (r["train_condition"], r["test_condition"], r["layer"])
                    == (train_cond, test_cond, layer)
                ]
                summary.append(
                    {
                        "train_condition": train_cond,
                        "test_condition": test_cond,
                        "layer": layer,
                        "intervals": {
                            metric: interval([r.get(metric) for r in rs], n_boot=n_boot)
                            for metric in metrics
                        },
                        "recall": {
                            st: interval([r["recall"][st] for r in rs], n_boot=n_boot)
                            for st in STRATEGIES
                        },
                    }
                )
    primary = []
    for layer in layers:
        rs = [
            r
            for r in results
            if (r["train_condition"], r["test_condition"], r["layer"])
            == ("original", "inversion", layer)
        ]
        if not rs:
            continue
        checks = {
            metric: interval([r[metric] for r in rs], alpha=0.05 / 8, n_boot=n_boot)
            for metric in (
                "accuracy",
                "alignment",
                "conditional_gain_bits",
                "paired_accuracy_change",
            )
        }
        thresholds = {
            "accuracy": 0.25,
            "alignment": 0,
            "conditional_gain_bits": 0,
            "paired_accuracy_change": -0.10,
        }
        primary.append(
            {
                "layer": layer,
                "checks": checks,
                "passes": all(
                    checks[k]["lower"] is not None
                    and checks[k]["n_families"] == len(families)
                    and checks[k]["lower"] > v
                    for k, v in thresholds.items()
                ),
            }
        )
    return {
        "families": families,
        "layers": list(layers),
        "n_boot": n_boot,
        "seed": SEED,
        "summary": summary,
        "per_family": results,
        "predictions": predictions,
        "primary_inversion": primary,
        "preliminary_survival": (
            len(primary) == 2 and all(x["passes"] for x in primary)
        )
        if primary
        else None,
        "limitations": [
            "Previously inspected families; feasibility evidence only.",
            "Intervals resample complete paired OOF family summaries, conditional on fitted models.",
            "Lexical stress conditions can selectively corrupt cooperation; report altered-only recall and matched controls.",
            "Conditional gain is finite-model held-out predictive information, not universal mutual information.",
            "No behavior or causal mechanism conclusion follows from decoding.",
        ],
    }


def analyze(plan, run, output):
    out = Path(output)
    if out.exists():
        raise FileExistsError(out)
    manifest, rows, panels, arrays = load_run(plan, run)
    layers = [18, 22]
    data = assemble(rows, panels, arrays, layers)
    report = evaluate(data, layers)
    report.update(
        {
            "plan_manifest_sha256": sha(Path(plan) / "manifest.json"),
            "run_manifest_sha256": sha(Path(run) / "manifest.json"),
            "analysis_sha256": sha(__file__),
            "status": "EXPLORATORY_REAL_ACTIVATION_ANALYSIS",
        }
    )
    out.mkdir(parents=True)
    write_json(out / "analysis.json", report)
    lines = [
        "# Lexical pilot analysis",
        "",
        f"Families: {len(report['families'])}. Primary inversion preliminary survival: {report['preliminary_survival']}.",
        "",
        "| Train | Test | Layer | Accuracy | Alignment | Conditional gain (bits) | Paired accuracy change |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["summary"]:

        def show(k):
            v = row["intervals"][k]
            return (
                "undefined"
                if v["mean"] is None
                else f"{v['mean']:.3f} [{v['lower']:.3f}, {v['upper']:.3f}]"
            )

        lines.append(
            f"| {row['train_condition']} | {row['test_condition']} | {row['layer']} | {show('accuracy')} | {show('alignment')} | {show('conditional_gain_bits')} | {show('paired_accuracy_change')} |"
        )
    lines += [
        "",
        "Intervals in this table are 95%; primary decision uses the separately recorded 99.375% intervals.",
        "",
        *report["limitations"],
    ]
    (out / "analysis.md").write_text(
        "\n".join(lines) + "\n", encoding="utf8", newline="\n"
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    r = analyze(a.plan, a.run, a.output)
    print(
        json.dumps(
            {
                "preliminary_survival": r["preliminary_survival"],
                "families": len(r["families"]),
            }
        )
    )


if __name__ == "__main__":
    main()
