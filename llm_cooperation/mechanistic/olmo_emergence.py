"""Checkpoint selection and longitudinal analysis for OLMo 2 1B emergence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL_ID = "allenai/OLMo-2-0425-1B"
BANK = Path("data/scenarios_phase0b_utility_matched.json")
SELECTION_VERSION = "olmo2-1b-emergence-selection-v1"
# The stage-one trajectory is sampled at 0%, 20%, 60%, and its endpoint;
# the fifth point is the official seed-42 stage-two pretrained base endpoint.
STAGE1_TARGET_FRACTIONS = (0.0, 0.20, 0.60, 1.0)
FINAL_STAGE2_TAG = "stage2-ingredient3-step23852-tokens51B"
STRATEGY_NAMES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _parse_stage1(tag):
    match = re.fullmatch(r"stage1-step(\d+)-tokens(\d+)B", tag)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def resolve_checkpoints(repo_id=MODEL_ID, *, api=None):
    """Resolve five broadly spaced revisions from live official Hub refs."""
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    refs = api.list_repo_refs(repo_id, repo_type="model")
    available = {ref.name: ref.target_commit for ref in [*refs.branches, *refs.tags]}
    stage1 = [(name, _parse_stage1(name), commit) for name, commit in available.items()]
    stage1 = [(name, parsed, commit) for name, parsed, commit in stage1 if parsed is not None]
    if len(stage1) < 4:
        raise RuntimeError(f"Expected at least four official stage-one refs; found {len(stage1)}")
    max_tokens = max(parsed[1] for _, parsed, _ in stage1)
    selected = []
    for fraction in STAGE1_TARGET_FRACTIONS:
        target = fraction * max_tokens
        name, (step, tokens), commit = min(stage1, key=lambda row: (abs(row[1][1] - target), row[1][1]))
        if name in {row["revision"] for row in selected}:
            raise RuntimeError("Live stage-one refs do not provide four distinct, broadly spaced checkpoints")
        selected.append({"model_id": repo_id, "revision": name, "commit_sha": commit,
                         "training_stage": "stage1_pretraining", "training_step": step,
                         "stage_tokens_billions": tokens, "cumulative_tokens_billions": tokens,
                         "trajectory_lineage": "official_0425_seed42_stage1"})
    final_revision = FINAL_STAGE2_TAG if FINAL_STAGE2_TAG in available else "main" if "main" in available else None
    if final_revision is None:
        raise RuntimeError("No official final stage-two/base ref was found; refusing to invent one")
    # The model card describes stage two as a 51B-token continuation from the
    # stage-one endpoint. The final checkpoint may be exposed under the named
    # stage2 ref or main; either ref is recorded with its immutable commit SHA.
    final_commit = available[final_revision]
    if final_revision == "main" and final_commit == selected[-1]["commit_sha"]:
        raise RuntimeError("The main ref resolves to the stage-one endpoint, not a distinct final base")
    selected.append({"model_id": repo_id, "revision": final_revision, "commit_sha": final_commit,
                     "training_stage": "stage2_mid_training_pretrained_base",
                     "training_step": 23852,
                     "stage_tokens_billions": 51,
                     "cumulative_tokens_billions": max_tokens + 51,
                     "trajectory_lineage": "official_0425_seed42_stage1_then_stage2"})
    if len({row["commit_sha"] for row in selected}) != 5:
        raise RuntimeError("Checkpoint selection contains duplicate immutable commits")
    for index, row in enumerate(selected):
        row["checkpoint_order"] = index
        row["training_stage_label"] = ("initialization" if index == 0 else
                                       "early_stage1" if index == 1 else
                                       "intermediate_stage1" if index == 2 else
                                       "late_stage1_endpoint" if index == 3 else "completed_pretrained_base")
    return {"version": SELECTION_VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
            "model_id": repo_id, "selection_method": "live list_repo_refs; nearest available stage1 cumulative-token refs at 0%, 20%, 60%, 100%, plus official seed-42 stage2 endpoint",
            "stage1_source_repo": repo_id, "early_training_reconstruction_used": False,
            "stage_relationship": "The final seed-42 stage2 checkpoint continues from the official stage1 endpoint; intermediate points remain on the official stage1 lineage.",
            "checkpoints": selected}


def prepare_plans(selection_path, output_root, *, bank_path=BANK):
    """Prepare checkpoint-specific, byte-identical prompt plans from the frozen bank."""
    from .contrastive_mapping import prepare
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    bank_path = Path(bank_path)
    if len(json.loads(bank_path.read_text(encoding="utf-8")).get("scenarios", [])) != 124:
        raise ValueError("Frozen Phase 0B bank must contain exactly 124 scenarios")
    prompt_hashes = set()
    plan_rows = []
    for row in selection["checkpoints"]:
        plan = output_root / f"checkpoint-{row['checkpoint_order']:02d}"
        prepared = prepare(plan, bank_path=bank_path, seed=42, model_id=row["model_id"], revision=row["commit_sha"])
        prompt_hashes.add(prepared["prompts_sha256"])
        (plan / "checkpoint.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        plan_rows.append({**row, "plan_dir": str(plan.resolve()), "plan_manifest_sha256": _sha(plan / "manifest.json"),
                          "prompts_sha256": prepared["prompts_sha256"]})
    if len(prompt_hashes) != 1:
        raise RuntimeError("Checkpoint prompt inventories are not byte-identical")
    result = {**selection, "plans": plan_rows, "bank_path": str(bank_path), "bank_sha256": _sha(bank_path),
              "prompts_sha256": next(iter(prompt_hashes))}
    (output_root / "selection_and_plans.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def prepare_smoke_plan(selection_path, output_root, *, bank_path=BANK):
    """Prepare a small one-checkpoint model-load/capture check; no inference is run."""
    from .contrastive_mapping import prepare
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    if len(selection.get("checkpoints", [])) != 5:
        raise ValueError("Smoke preparation requires the verified five-checkpoint selection")
    row = dict(selection["checkpoints"][0])
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    plan = output_root / "checkpoint-00"
    prepared = prepare(plan, bank_path=bank_path, seed=42, smoke=True,
                       model_id=row["model_id"], revision=row["commit_sha"])
    (plan / "checkpoint.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    payload = {**selection, "bank_path": str(Path(bank_path)), "bank_sha256": _sha(bank_path),
               "technical_smoke": True, "plans": [{**row, "plan_dir": str(plan.resolve()),
                   "plan_manifest_sha256": _sha(plan / "manifest.json"), "prompts_sha256": prepared["prompts_sha256"]}]}
    (output_root / "selection_and_plans.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _bonferroni_lower(values, *, alpha, n_boot, seed):
    vals = np.asarray(list(values), dtype=float)
    if not len(vals):
        return None
    rng = np.random.default_rng(seed)
    draws = rng.choice(vals, size=(n_boot, len(vals)), replace=True).mean(axis=1)
    return float(np.quantile(draws, alpha))


def analyze_trajectory(checkpoint_analyses, output_dir, *, n_boot=20000, alpha=0.05):
    """Aggregate per-checkpoint probe outputs using normalized depth and FWER control."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    loaded = []
    for item in checkpoint_analyses:
        data = json.loads(Path(item["analysis_json"]).read_text(encoding="utf-8"))
        checkpoint = item["checkpoint"]
        loaded.append((checkpoint, data))
    loaded.sort(key=lambda pair: pair[0]["checkpoint_order"])
    if len(loaded) != 5:
        raise ValueError("Trajectory analysis requires exactly five selected checkpoints")
    if len({d["provenance"]["prompts_sha256"] for _, d in loaded}) != 1:
        raise ValueError("Analysis prompt inventories differ across checkpoints")
    n_layers = [len(d["domain_held_out"]["layer_metrics"]) for _, d in loaded]
    correction_tests = sum(n_layers) * len(STRATEGY_NAMES)
    adjusted_alpha = alpha / correction_tests
    trajectories = {strategy: [] for strategy in STRATEGY_NAMES}
    for checkpoint, data in loaded:
        depth = len(data["domain_held_out"]["layer_metrics"])
        directions = data["domain_held_out"]["directional_consistency_primary_outcome"]
        for layer in range(depth):
            metrics = data["domain_held_out"]["layer_metrics"][layer]
            ba = metrics["balanced_accuracy"]
            adj_ba = metrics["lexical_adjusted_balanced_accuracy"]
            for strategy in STRATEGY_NAMES:
                v = directions[layer]["by_strategy"][strategy]
                ac = v["lexically_adjusted_heldout_domain_direction_alignment_cosine"]
                margin = v["lexically_adjusted_heldout_domain_projection_margin"]
                align_domains = v["lexically_adjusted_heldout_domain_alignment_by_domain"].values()
                margin_domains = v["lexically_adjusted_heldout_domain_margin_by_domain"].values()
                lower_align = _bonferroni_lower(align_domains, alpha=adjusted_alpha, n_boot=n_boot,
                                                seed=checkpoint["checkpoint_order"] * 100000 + layer * 100 + STRATEGY_NAMES.index(strategy))
                lower_margin = _bonferroni_lower(margin_domains, alpha=adjusted_alpha, n_boot=n_boot,
                                                 seed=checkpoint["checkpoint_order"] * 100000 + layer * 100 + STRATEGY_NAMES.index(strategy) + 50000)
                detectable = bool(lower_align is not None and lower_margin is not None and lower_align > 0 and lower_margin > 0)
                trajectories[strategy].append({"checkpoint_order": checkpoint["checkpoint_order"],
                    "revision": checkpoint["revision"], "training_stage": checkpoint["training_stage_label"],
                    "cumulative_tokens_billions": checkpoint["cumulative_tokens_billions"],
                    "layer": layer, "normalized_depth": layer / max(depth - 1, 1),
                    "raw_alignment_mean": v["heldout_domain_direction_alignment_cosine"][0],
                    "length_adjusted_alignment_mean": ac[0],
                    "length_adjusted_alignment_fwer_lower": lower_align,
                    "length_adjusted_margin_mean": margin[0], "length_adjusted_margin_fwer_lower": lower_margin,
                    "raw_domain_balanced_accuracy": ba[0], "raw_domain_ba_ci_lower": ba[1],
                    "length_adjusted_domain_balanced_accuracy": adj_ba,
                    "within_scenario_permutation_q95": metrics["permutation_balanced_accuracy"]["q975"],
                    "cross_domain_detectable": detectable})
    earliest = {}
    for strategy, rows in trajectories.items():
        hits = [r for r in rows if r["cross_domain_detectable"]]
        earliest[strategy] = ({"checkpoint_order": hits[0]["checkpoint_order"], "revision": hits[0]["revision"],
                               "training_stage": hits[0]["training_stage"], "cumulative_tokens_billions": hits[0]["cumulative_tokens_billions"],
                               "normalized_depth": hits[0]["normalized_depth"]} if hits else None)
    report = {"version": "olmo2-emergence-trajectory-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": loaded[0][1]["model_id"], "prompt_inventory_sha256": loaded[0][1]["provenance"]["prompts_sha256"],
        "statistical_criterion": {"familywise_alpha": alpha, "bonferroni_tests": correction_tests,
            "per_test_one_sided_alpha": adjusted_alpha, "bootstrap_resamples": n_boot,
            "rule": "For each strategy and layer, both the lexical-adjusted held-out-domain direction-alignment and projection-margin cluster bootstrap lower bounds exceed zero; Bonferroni controls familywise error across all sampled checkpoint x layer x strategy tests. Earliest sampled checkpoint satisfying the rule is reported; no exact emergence time is inferred."},
        "earliest_detectable_sampled_checkpoint_by_strategy": earliest,
        "strategy_layer_trajectories": trajectories,
        "interpretation_boundary": "This study measures strategy-related information in residual streams. It does not show that those representations cause cooperative decisions or establish a cooperative preference."}
    (output_dir / "olmo_emergence_trajectory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), constrained_layout=True)
    common_depth = np.linspace(0, 1, 100)
    for column, strategy in enumerate(STRATEGY_NAMES):
        rows = trajectories[strategy]
        raw_matrix = np.full((5, len(common_depth)), np.nan)
        adjusted_matrix = np.full_like(raw_matrix, np.nan)
        by_checkpoint = {}
        for row in rows:
            by_checkpoint.setdefault(row["checkpoint_order"], []).append(row)
        for checkpoint_order, checkpoint_rows in by_checkpoint.items():
            checkpoint_rows.sort(key=lambda row: row["normalized_depth"])
            depths = [row["normalized_depth"] for row in checkpoint_rows]
            raw_matrix[checkpoint_order] = np.interp(common_depth, depths, [row["raw_alignment_mean"] for row in checkpoint_rows])
            adjusted_matrix[checkpoint_order] = np.interp(common_depth, depths, [row["length_adjusted_alignment_mean"] for row in checkpoint_rows])
        for ax, matrix, title in ((axes[0, column], raw_matrix, "raw"), (axes[1, column], adjusted_matrix, "length-adjusted")):
            im = ax.imshow(matrix, aspect="auto", origin="lower", vmin=-1, vmax=1, cmap="coolwarm", extent=(0, 1, -.5, 4.5))
            ax.set(title=f"{strategy}: {title} alignment", xlabel="Normalized transformer depth", ylabel="Checkpoint order")
            fig.colorbar(im, ax=ax, fraction=.046, pad=.04, label="Cosine")
    fig.suptitle("OLMo 2 1B held-out-domain direction alignment")
    fig.savefig(output_dir / "olmo_emergence_layer_by_checkpoint.png", dpi=160)
    plt.close(fig)
    raw_ba = np.full((5, len(common_depth)), np.nan)
    adjusted_ba = np.full_like(raw_ba, np.nan)
    class_rows = {}
    for row in trajectories[STRATEGY_NAMES[0]]:
        class_rows.setdefault(row["checkpoint_order"], []).append(row)
    for checkpoint_order, checkpoint_rows in class_rows.items():
        checkpoint_rows.sort(key=lambda row: row["normalized_depth"])
        depths = [row["normalized_depth"] for row in checkpoint_rows]
        raw_ba[checkpoint_order] = np.interp(common_depth, depths, [row["raw_domain_balanced_accuracy"] for row in checkpoint_rows])
        adjusted_ba[checkpoint_order] = np.interp(common_depth, depths, [row["length_adjusted_domain_balanced_accuracy"] for row in checkpoint_rows])
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for ax, matrix, title in ((axes2[0], raw_ba, "raw four-class balanced accuracy"),
                              (axes2[1], adjusted_ba, "length-adjusted four-class balanced accuracy")):
        im = ax.imshow(matrix, aspect="auto", origin="lower", vmin=0.25, vmax=1.0, cmap="viridis", extent=(0, 1, -.5, 4.5))
        ax.set(title=title, xlabel="Normalized transformer depth", ylabel="Checkpoint order")
        fig2.colorbar(im, ax=ax, fraction=.046, pad=.04, label="Balanced accuracy")
    fig2.suptitle("OLMo 2 1B cross-domain strategy separability")
    fig2.savefig(output_dir / "olmo_emergence_separability_layer_by_checkpoint.png", dpi=160)
    plt.close(fig2)
    (output_dir / "olmo_emergence_trajectory.md").write_text(_trajectory_markdown(report), encoding="utf-8")
    return report


def _trajectory_markdown(report):
    lines = ["# OLMo 2 1B pretraining-emergence trajectory", "",
        "![Cross-domain strategy direction alignment](olmo_emergence_layer_by_checkpoint.png)", "",
        "![Four-class strategy separability](olmo_emergence_separability_layer_by_checkpoint.png)", "",
        "## Earliest sampled checkpoint meeting the criterion", "", "| Strategy | Checkpoint order | Revision | Stage | Cumulative tokens (B) | Normalized depth |", "|---|---:|---|---|---:|---:|"]
    for name, row in report["earliest_detectable_sampled_checkpoint_by_strategy"].items():
        if row is None:
            lines.append(f"| {name} | — | No sampled checkpoint | — | — | — |")
        else:
            lines.append(f"| {name} | {row['checkpoint_order']} | `{row['revision']}` | {row['training_stage']} | {row['cumulative_tokens_billions']} | {row['normalized_depth']:.3f} |")
    lines += ["", "## Criterion", "", report["statistical_criterion"]["rule"], "",
        "Raw and length-adjusted trajectory values are included separately in the JSON. Layer depth is normalized within each model checkpoint. These five samples do not identify an exact emergence time.", "", report["interpretation_boundary"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    psel = sub.add_parser("select")
    psel.add_argument("--output", required=True)
    pp = sub.add_parser("prepare-plans")
    pp.add_argument("--selection", required=True)
    pp.add_argument("--output", required=True)
    ps = sub.add_parser("prepare-smoke")
    ps.add_argument("--selection", required=True)
    ps.add_argument("--output", required=True)
    pan = sub.add_parser("analyze-trajectory")
    pan.add_argument("--inputs", required=True, help="JSON list of {checkpoint, analysis_json} objects")
    pan.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "select":
        Path(args.output).write_text(json.dumps(resolve_checkpoints(), indent=2), encoding="utf-8")
    elif args.command == "prepare-plans":
        prepare_plans(args.selection, args.output)
    elif args.command == "prepare-smoke":
        prepare_smoke_plan(args.selection, args.output)
    else:
        analyze_trajectory(json.loads(Path(args.inputs).read_text(encoding="utf-8")), args.output)


if __name__ == "__main__":
    main()
