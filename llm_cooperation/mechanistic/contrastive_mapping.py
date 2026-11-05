"""Exploratory one-shot contrastive representation-mapping experiment.

Scientific objective:
Determine whether a reproducible, distributed activation direction distinguishes
cooperative actions from independent actions across the Phase 0B scenario bank.
Scientific boundary:
A reproducible direction would establish linear accessibility of action-related
information, not that the model prefers cooperation or uses that direction causally.

No model calls occur on import. Paid/real GPU inference requires explicit authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

VERSION = "contrastive-mapping-v1"
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-1.5B"
DEFAULT_REVISION = "8faed761d45a263340a0528343f099c05c9a4323"
BANK_PATH = Path("data/scenarios_phase0b_utility_matched.json")
TRAILING_MARKER = "\nDecision:"
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")


def sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def format_single_action_prompt(stem: str, action_text: str, marker: str = TRAILING_MARKER) -> str:
    """Format single-action prompt with standardized stem and trailing marker."""
    clean_stem = stem.strip()
    clean_action = action_text.strip()
    return f"{clean_stem}\n\nAction: {clean_action}{marker}"


def load_scenarios(bank_path: Path | str = BANK_PATH) -> List[Dict[str, Any]]:
    path = Path(bank_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "scenarios" in data:
        return data["scenarios"]
    elif isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized scenario bank format in {bank_path}")


def partition_families(
    scenarios: Sequence[Dict[str, Any]],
    discovery_fraction: float = 0.5,
    seed: int = 42,
) -> Tuple[List[str], List[str]]:
    """Partition scenarios into discovery and evaluation sets by template/domain family.

    Crucially, keep human/AI variants and sensitivity-triad relatives together:
    group_key = triad_id or template_id.
    """
    clusters: Dict[str, List[str]] = {}
    for s in scenarios:
        group_key = s.get("triad_id") or s.get("template_id")
        if not group_key:
            group_key = s["id"]
        clusters.setdefault(group_key, []).append(s["id"])

    # Deterministic seeded ordering of family keys
    sorted_groups = sorted(clusters.keys())
    # Sort deterministically using hash with salt
    sorted_groups.sort(key=lambda g: hashlib.sha256(f"contrastive-split:{seed}:{g}".encode()).hexdigest())

    n_discovery = max(1, int(math.ceil(len(sorted_groups) * discovery_fraction)))
    disc_groups = set(sorted_groups[:n_discovery])
    eval_groups = set(sorted_groups[n_discovery:])

    discovery_ids = [sid for g in sorted_groups if g in disc_groups for sid in clusters[g]]
    evaluation_ids = [sid for g in sorted_groups if g in eval_groups for sid in clusters[g]]
    return discovery_ids, evaluation_ids


def prepare(
    output_dir: Path | str,
    bank_path: Path | str = BANK_PATH,
    discovery_fraction: float = 0.5,
    seed: int = 42,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Offline preparation of single-action contrastive prompts and manifests."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)

    scenarios = load_scenarios(bank_path)
    if smoke:
        # Select first 6 unique template/triad families for a small smoke test
        seen_families = set()
        smoke_scenarios = []
        for s in scenarios:
            f = s.get("triad_id") or s.get("template_id")
            if f not in seen_families:
                if len(seen_families) >= 6:
                    continue
                seen_families.add(f)
            smoke_scenarios.append(s)
        scenarios = smoke_scenarios

    discovery_ids, evaluation_ids = partition_families(scenarios, discovery_fraction, seed)
    disc_set = set(discovery_ids)

    prompts: List[Dict[str, Any]] = []
    for s in scenarios:
        sid = s["id"]
        group_key = s.get("triad_id") or s.get("template_id")
        split = "discovery" if sid in disc_set else "evaluation"
        domain = s.get("domain", "unknown")
        partner_type = s.get("partner_type", "unknown")
        context_type = s.get("context_type", "unknown")
        utility_condition = s.get("utility_condition", "unknown")
        stem = s["stem"]

        for strat in STRATEGIES:
            action_text = s["options"][strat]
            prompt_text = format_single_action_prompt(stem, action_text, TRAILING_MARKER)
            prompt_id = f"{sid}_{strat}"
            prompts.append({
                "prompt_id": prompt_id,
                "scenario_id": sid,
                "template_id": s.get("template_id"),
                "triad_id": s.get("triad_id"),
                "group_key": group_key,
                "split": split,
                "strategy": strat,
                "partner_type": partner_type,
                "context_type": context_type,
                "utility_condition": utility_condition,
                "domain": domain,
                "action_text": action_text,
                "action_word_count": len(action_text.split()),
                "action_char_count": len(action_text),
                "trailing_marker": TRAILING_MARKER,
                "prompt_text": prompt_text,
            })

    prompts_file = out / "prompts.jsonl"
    with prompts_file.open("w", encoding="utf-8") as f:
        for p in prompts:
            f.write(json.dumps(p) + "\n")

    manifest = {
        "version": VERSION,
        "status": "prepared",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "bank_path": str(bank_path),
        "bank_sha256": sha256_file(bank_path),
        "script_sha256": sha256_file(__file__),
        "num_scenarios": len(scenarios),
        "num_prompts": len(prompts),
        "num_families": len({p["group_key"] for p in prompts}),
        "discovery_scenarios": len(discovery_ids),
        "evaluation_scenarios": len(evaluation_ids),
        "discovery_families": len({p["group_key"] for p in prompts if p["split"] == "discovery"}),
        "evaluation_families": len({p["group_key"] for p in prompts if p["split"] == "evaluation"}),
        "smoke": smoke,
        "seed": seed,
        "trailing_marker": TRAILING_MARKER,
        "strategies": list(STRATEGIES),
        "target_model": DEFAULT_MODEL_ID,
        "target_revision": DEFAULT_REVISION,
    }
    manifest_file = out / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def mock_forward_pass(
    prompt_ids: Sequence[str],
    num_layers: int = 28,
    hidden_size: int = 1536,
    seed: int = 101,
) -> Dict[str, np.ndarray]:
    """Synthetic forward pass generator for testing/smoke runs without GPU inference.

    Generates deterministic pseudo-random residual vectors [num_layers, hidden_size] in FP32.
    """
    rng = np.random.RandomState(seed)
    activations = {}
    for pid in prompt_ids:
        # Seed slightly by prompt id hash to make repeatable
        h = int(hashlib.md5(pid.encode()).hexdigest()[:8], 16)
        local_rng = np.random.RandomState(h % (2**31 - 1))
        # [num_layers, hidden_size] in FP32
        arr = local_rng.randn(num_layers, hidden_size).astype(np.float32)
        activations[pid] = arr
    return activations


def run_inference(
    plan_dir: Path | str,
    output_dir: Path | str,
    model_id: str = DEFAULT_MODEL_ID,
    revision: str = DEFAULT_REVISION,
    authorize: bool = False,
    mock: bool = False,
    device: str = "auto",
) -> Dict[str, Any]:
    """Capture residual-stream vectors at the final trailing marker token for every layer."""
    plan_path = Path(plan_dir)
    manifest_path = plan_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Plan manifest not found at {manifest_path}")

    prep_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prompts_path = plan_path / "prompts.jsonl"
    prompts = [json.loads(line) for line in prompts_path.read_text(encoding="utf-8").splitlines()]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)

    run_manifest = dict(prep_manifest)
    run_manifest.update({
        "status": "running",
        "model_id": model_id,
        "model_revision": revision,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "mock": mock,
    })
    (out / "manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    act_dir = out / "activations"
    act_dir.mkdir(parents=True, exist_ok=False)

    if mock:
        run_manifest.update({
            "num_layers": 28,
            "hidden_size": 1536,
            "dtype": "float32",
            "device": "mock_cpu",
        })
        act_map = mock_forward_pass([p["prompt_id"] for p in prompts])
        for pid, tensor in act_map.items():
            np.savez_compressed(act_dir / f"{pid}.npz", residual=tensor)
    else:
        if not authorize:
            raise PermissionError(
                "Execution requires explicit authorization flag (--authorize-inference locally or --authorize-paid-run on Modal)"
            )
        if model_id != DEFAULT_MODEL_ID or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError(f"Model ID must be {DEFAULT_MODEL_ID} with exact 40-char SHA revision")

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=torch.float32,
            device_map=device,
        )
        model.eval()

        layers = model.model.layers
        num_layers = len(layers)
        hidden_size = model.config.hidden_size

        run_manifest.update({
            "num_layers": num_layers,
            "hidden_size": hidden_size,
            "dtype": "float32",
            "device": str(model.device),
            "torch_version": torch.__version__,
        })

        for p in prompts:
            prompt_text = p["prompt_text"]
            inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

            cache: Dict[int, np.ndarray] = {}
            handles = []
            for l_idx, layer in enumerate(layers):
                def make_hook(idx: int):
                    def hook_fn(module: Any, args: Any, output: Any):
                        hidden = output[0] if isinstance(output, tuple) else output
                        # Capture residual at the final prompt token (index -1)
                        cache[idx] = hidden[0, -1, :].detach().float().cpu().numpy()
                    return hook_fn
                handles.append(layer.register_forward_hook(make_hook(l_idx)))

            try:
                with torch.inference_mode():
                    model(**inputs, use_cache=False)
            finally:
                for h in handles:
                    h.remove()

            # Stack layers: [num_layers, hidden_size] in FP32
            stacked = np.stack([cache[i] for i in range(num_layers)], axis=0).astype(np.float32)
            np.savez_compressed(act_dir / f"{p['prompt_id']}.npz", residual=stacked)

    # Save evidence hashes
    evidence_hashes = {}
    evidence_hashes["prompts.jsonl"] = sha256_file(prompts_path)
    for npz_path in sorted(act_dir.glob("*.npz")):
        evidence_hashes[f"activations/{npz_path.name}"] = sha256_file(npz_path)

    (out / "evidence_hashes.json").write_text(json.dumps(evidence_hashes, indent=2), encoding="utf-8")
    run_manifest["status"] = "completed"
    run_manifest["ended_utc"] = datetime.now(timezone.utc).isoformat()
    run_manifest["evidence_hashes_sha256"] = sha256_file(out / "evidence_hashes.json")
    (out / "manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    return run_manifest


def bootstrap_ci(
    values_by_family: Dict[str, List[float]],
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[float, float, float]:
    """Compute mean and cluster-bootstrap (1-alpha) confidence interval across families."""
    family_keys = sorted(values_by_family.keys())
    if not family_keys:
        return 0.0, 0.0, 0.0

    # Family-level mean values
    family_means = np.array([np.mean(values_by_family[k]) for k in family_keys])
    point_estimate = float(np.mean(family_means))
    if len(family_keys) < 2:
        return point_estimate, point_estimate, point_estimate

    rng = np.random.RandomState(seed)
    boot_means = []
    n = len(family_keys)
    for _ in range(n_boot):
        sample_indices = rng.choice(n, size=n, replace=True)
        boot_means.append(np.mean(family_means[sample_indices]))

    low = float(np.percentile(boot_means, 100 * (alpha / 2)))
    high = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return point_estimate, low, high


def compute_paired_differences(
    activations: Dict[str, np.ndarray],
    strat_a: str = "COOPERATE",
    strat_b: str = "INDEPENDENT",
    scenario_ids: Optional[Sequence[str]] = None,
) -> Dict[str, np.ndarray]:
    """Compute difference vectors diff_s = act(strat_a) - act(strat_b) for each scenario.

    Returns dict mapping scenario_id -> np.ndarray of shape [num_layers, hidden_size].
    """
    diffs = {}
    # Determine all candidate scenario IDs from activation keys
    if scenario_ids is None:
        candidates = set()
        for k in activations.keys():
            if k.endswith(f"_{strat_a}"):
                candidates.add(k[:-len(f"_{strat_a}")])
        scenario_ids = sorted(candidates)

    for sid in scenario_ids:
        key_a = f"{sid}_{strat_a}"
        key_b = f"{sid}_{strat_b}"
        if key_a in activations and key_b in activations:
            diffs[sid] = (activations[key_a] - activations[key_b]).astype(np.float32)

    return diffs


def analyze_contrastive_mapping(
    run_dir: Path | str,
    prompts_path: Path | str,
    output_dir: Optional[Path | str] = None,
    n_boot: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Execute rigorous statistical analysis of contrastive representations."""
    run_path = Path(run_dir)
    act_dir = run_path / "activations"
    prompts = [json.loads(line) for line in Path(prompts_path).read_text(encoding="utf-8").splitlines()]

    # Load all activations
    activations: Dict[str, np.ndarray] = {}
    for p in prompts:
        pid = p["prompt_id"]
        npz_file = act_dir / f"{pid}.npz"
        if npz_file.exists():
            data = np.load(npz_file)
            activations[pid] = data["residual"]

    if not activations:
        raise ValueError(f"No activations found in {act_dir}")

    # Metadata lookups
    scenarios_meta: Dict[str, Dict[str, Any]] = {}
    for p in prompts:
        sid = p["scenario_id"]
        if sid not in scenarios_meta:
            scenarios_meta[sid] = {
                "scenario_id": sid,
                "group_key": p["group_key"],
                "split": p["split"],
                "domain": p["domain"],
                "partner_type": p["partner_type"],
                "context_type": p["context_type"],
                "utility_condition": p["utility_condition"],
                "action_word_counts": {},
            }
        scenarios_meta[sid]["action_word_counts"][p["strategy"]] = p["action_word_count"]

    first_act = next(iter(activations.values()))
    num_layers, hidden_size = first_act.shape

    # 1. Primary Paired Differences: COOPERATE - INDEPENDENT
    coop_indep_diffs = compute_paired_differences(activations, "COOPERATE", "INDEPENDENT")

    # Split scenarios into discovery and evaluation
    discovery_sids = [sid for sid, meta in scenarios_meta.items() if meta["split"] == "discovery" and sid in coop_indep_diffs]
    evaluation_sids = [sid for sid, meta in scenarios_meta.items() if meta["split"] == "evaluation" and sid in coop_indep_diffs]

    # Compute discovery mean directions per layer: shape [hidden_size]
    # Clustered across discovery families
    disc_families: Dict[str, List[str]] = {}
    for sid in discovery_sids:
        gk = scenarios_meta[sid]["group_key"]
        disc_families.setdefault(gk, []).append(sid)

    # Average diff within each discovery family first (equal family weighting)
    disc_family_diffs = []
    for gk, sids in disc_families.items():
        fam_diff = np.mean([coop_indep_diffs[sid] for sid in sids], axis=0)  # [num_layers, hidden_size]
        disc_family_diffs.append(fam_diff)
    disc_mean_diff = np.mean(disc_family_diffs, axis=0)  # [num_layers, hidden_size]

    # Discovery unit directions
    disc_norm = np.linalg.norm(disc_mean_diff, axis=-1, keepdims=True)  # [num_layers, 1]
    disc_directions = np.divide(disc_mean_diff, disc_norm, out=np.zeros_like(disc_mean_diff), where=disc_norm > 1e-12)

    # Split-half direction cosine similarity: Fold A vs Fold B of discovery families
    disc_family_keys = sorted(disc_families.keys())
    split_half_cosines = []
    if len(disc_family_keys) >= 2:
        half_n = len(disc_family_keys) // 2
        fold_a_keys = disc_family_keys[:half_n]
        fold_b_keys = disc_family_keys[half_n:]
        fold_a_diff = np.mean([np.mean([coop_indep_diffs[s] for s in disc_families[k]], axis=0) for k in fold_a_keys], axis=0)
        fold_b_diff = np.mean([np.mean([coop_indep_diffs[s] for s in disc_families[k]], axis=0) for k in fold_b_keys], axis=0)
        norm_a = np.linalg.norm(fold_a_diff, axis=-1)
        norm_b = np.linalg.norm(fold_b_diff, axis=-1)
        dot_ab = np.sum(fold_a_diff * fold_b_diff, axis=-1)
        denom = norm_a * norm_b
        split_half_cosines = np.divide(dot_ab, denom, out=np.zeros_like(dot_ab), where=denom > 1e-12).tolist()
    else:
        split_half_cosines = [0.0] * num_layers

    # Held-out evaluation projections: p_s = diff_s . v_disc
    # Projections shape: [len(eval_sids), num_layers]
    eval_projections_by_sid: Dict[str, np.ndarray] = {}
    for sid in evaluation_sids:
        # dot product for each layer: (num_layers, hidden_size) * (num_layers, hidden_size) sum along axis 1
        proj = np.sum(coop_indep_diffs[sid] * disc_directions, axis=-1)  # [num_layers]
        eval_projections_by_sid[sid] = proj

    # Group evaluation projections by family
    eval_families: Dict[str, List[str]] = {}
    for sid in evaluation_sids:
        gk = scenarios_meta[sid]["group_key"]
        eval_families.setdefault(gk, []).append(sid)

    # 2. Layer-by-layer evaluation metrics
    layer_metrics: List[Dict[str, Any]] = []
    for l in range(num_layers):
        projs_by_fam: Dict[str, List[float]] = {}
        for gk, sids in eval_families.items():
            projs_by_fam[gk] = [float(eval_projections_by_sid[sid][l]) for sid in sids]

        mean_proj, ci_low, ci_high = bootstrap_ci(projs_by_fam, n_boot=n_boot, seed=seed)

        # Cohen's d: mean / std across family means
        fam_means = [np.mean(vals) for vals in projs_by_fam.values()]
        fam_std = float(np.std(fam_means, ddof=1)) if len(fam_means) > 1 else 1.0
        cohens_d = float(mean_proj / fam_std) if fam_std > 1e-12 else 0.0

        # Sign-shuffled paired difference null: randomly flip sign of diff_s
        rng = np.random.RandomState(seed + l)
        null_dist = []
        for _ in range(500):
            shuffled_fam_means = []
            for gk, sids in eval_families.items():
                signs = rng.choice([-1.0, 1.0], size=len(sids))
                shuffled_fam_means.append(np.mean([eval_projections_by_sid[sid][l] * signs[i] for i, sid in enumerate(sids)]))
            null_dist.append(float(np.mean(shuffled_fam_means)))

        null_mean = float(np.mean(null_dist))
        null_ci_low = float(np.percentile(null_dist, 2.5))
        null_ci_high = float(np.percentile(null_dist, 97.5))

        layer_metrics.append({
            "layer": l,
            "split_half_cosine_similarity": float(split_half_cosines[l]),
            "held_out_mean_projection": mean_proj,
            "held_out_ci_95": [ci_low, ci_high],
            "cohens_d": cohens_d,
            "sign_shuffled_null_mean": null_mean,
            "sign_shuffled_null_ci_95": [null_ci_low, null_ci_high],
        })

    # 3. Lexical Length Control: Test if projection is driven by action word count differences
    # delta_words = len(COOPERATE words) - len(INDEPENDENT words)
    delta_words = np.array([
        scenarios_meta[sid]["action_word_counts"]["COOPERATE"] - scenarios_meta[sid]["action_word_counts"]["INDEPENDENT"]
        for sid in evaluation_sids
    ], dtype=np.float64)

    lexical_correlations = []
    for l in range(num_layers):
        proj_vals = np.array([eval_projections_by_sid[sid][l] for sid in evaluation_sids], dtype=np.float64)
        if np.std(delta_words) > 1e-12 and np.std(proj_vals) > 1e-12:
            r = float(np.corrcoef(delta_words, proj_vals)[0, 1])
        else:
            r = 0.0
        lexical_correlations.append(r)

    # 4. Alternative Strategy Contrasts:
    # Estimate alignment between COOP-INDEP direction and other contrasts
    alt_contrasts = {}
    for pair_name, (s1, s2) in [
        ("coop_minus_compete", ("COOPERATE", "COMPETE_EXPLOIT")),
        ("coop_minus_disengage", ("COOPERATE", "DISENGAGE")),
        ("compete_minus_disengage", ("COMPETE_EXPLOIT", "DISENGAGE")),
    ]:
        alt_diffs = compute_paired_differences(activations, s1, s2, evaluation_sids)
        if alt_diffs:
            # Held-out projection onto discovery COOP-INDEP direction
            alt_projs_by_layer = []
            for l in range(num_layers):
                fam_means = []
                for gk, sids in eval_families.items():
                    sids_present = [sid for sid in sids if sid in alt_diffs]
                    if sids_present:
                        f_proj = np.mean([np.sum(alt_diffs[sid][l] * disc_directions[l]) for sid in sids_present])
                        fam_means.append(f_proj)
                alt_projs_by_layer.append(float(np.mean(fam_means)) if fam_means else 0.0)
            alt_contrasts[pair_name] = alt_projs_by_layer

    report = {
        "version": VERSION,
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "num_layers": num_layers,
        "hidden_size": hidden_size,
        "num_discovery_scenarios": len(discovery_sids),
        "num_discovery_families": len(disc_families),
        "num_evaluation_scenarios": len(evaluation_sids),
        "num_evaluation_families": len(eval_families),
        "layer_metrics": layer_metrics,
        "lexical_length_correlations": lexical_correlations,
        "alternative_strategy_contrasts": alt_contrasts,
        "note": (
            "Exploratory representation-mapping analysis. Clustered by template/domain family; "
            "paired variants kept together. Linear decodability indicates representation availability, "
            "not preference or causal mechanism."
        ),
    }

    if output_dir:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        (out_p / "contrastive_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        _write_markdown_report(report, out_p / "contrastive_report.md")

    return report


def _write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Exploratory Contrastive Representation-Mapping Report",
        "",
        f"- **Timestamp:** `{report['analysis_timestamp_utc']}`",
        f"- **Layers Analyzed:** {report['num_layers']} (hidden dimension: {report['hidden_size']})",
        f"- **Discovery Split:** {report['num_discovery_scenarios']} scenarios across {report['num_discovery_families']} independent families",
        f"- **Held-Out Split:** {report['num_evaluation_scenarios']} scenarios across {report['num_evaluation_families']} independent families",
        "",
        "## Scientific Boundary Note",
        report["note"],
        "",
        "## Layer-by-Layer Geometry & Evaluation",
        "",
        "| Layer | Split-Half Cosine Sim | Held-Out Proj [95% CI] | Cohen's d | Sign-Shuffled Null [95% CI] | Lexical Length r |",
        "|---|---|---|---|---|---|",
    ]
    for lm in report["layer_metrics"]:
        l = lm["layer"]
        sim = f"{lm['split_half_cosine_similarity']:.3f}"
        proj = f"{lm['held_out_mean_projection']:.3f} [{lm['held_out_ci_95'][0]:.3f}, {lm['held_out_ci_95'][1]:.3f}]"
        d = f"{lm['cohens_d']:.2f}"
        null = f"{lm['sign_shuffled_null_mean']:.3f} [{lm['sign_shuffled_null_ci_95'][0]:.3f}, {lm['sign_shuffled_null_ci_95'][1]:.3f}]"
        r_lex = f"{report['lexical_length_correlations'][l]:.3f}"
        lines.append(f"| {l} | {sim} | {proj} | {d} | {null} | {r_lex} |")

    lines.extend([
        "",
        "## Alternative Strategy Contrasts (Projection onto COOP-INDEP Direction)",
        "",
        "| Layer | COOP - INDEP (Primary) | COOP - COMPETE | COOP - DISENGAGE | COMPETE - DISENGAGE |",
        "|---|---|---|---|---|",
    ])
    for lm in report["layer_metrics"]:
        l = lm["layer"]
        p_prim = f"{lm['held_out_mean_projection']:.3f}"
        p_comp = f"{report['alternative_strategy_contrasts'].get('coop_minus_compete', [0.0]*report['num_layers'])[l]:.3f}"
        p_dis = f"{report['alternative_strategy_contrasts'].get('coop_minus_disengage', [0.0]*report['num_layers'])[l]:.3f}"
        p_cd = f"{report['alternative_strategy_contrasts'].get('compete_minus_disengage', [0.0]*report['num_layers'])[l]:.3f}"
        lines.append(f"| {l} | {p_prim} | {p_comp} | {p_dis} | {p_cd} |")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    # prepare
    p_prep = sub.add_parser("prepare", help="Prepare offline prompt dataset and manifests")
    p_prep.add_argument("--output", required=True, help="Directory for prepared prompt dataset")
    p_prep.add_argument("--bank", default=str(BANK_PATH), help="Scenario bank path")
    p_prep.add_argument("--discovery-fraction", type=float, default=0.5, help="Fraction of families for discovery")
    p_prep.add_argument("--seed", type=int, default=42, help="Deterministic partition seed")
    p_prep.add_argument("--smoke", action="store_true", help="Prepare small subset for smoke test")

    # run
    p_run = sub.add_parser("run", help="Run model inference and capture residual-stream activations")
    p_run.add_argument("--plan", required=True, help="Prepared plan directory")
    p_run.add_argument("--output", required=True, help="Output directory for activations")
    p_run.add_argument("--model", default=DEFAULT_MODEL_ID, help="Target model identifier")
    p_run.add_argument("--revision", default=DEFAULT_REVISION, help="Target model revision SHA")
    p_run.add_argument("--authorize-inference", action="store_true", help="Authorize actual model inference")
    p_run.add_argument("--mock", action="store_true", help="Run mock synthetic passes without GPU")

    # analyze
    p_ana = sub.add_parser("analyze", help="Analyze contrastive geometry on captured activations")
    p_ana.add_argument("--run-dir", required=True, help="Run directory with activations and manifest")
    p_ana.add_argument("--prompts", required=True, help="Path to prompts.jsonl")
    p_ana.add_argument("--output", required=True, help="Output directory for reports")
    p_ana.add_argument("--n-boot", type=int, default=1000, help="Bootstrap resamples")

    # smoke-test
    p_smoke = sub.add_parser("smoke-test", help="Run complete mock end-to-end smoke test")
    p_smoke.add_argument("--output", required=True, help="Output directory for smoke test artifacts")

    args = parser.parse_args()

    if args.command == "prepare":
        res = prepare(args.output, args.bank, args.discovery_fraction, args.seed, args.smoke)
        print(json.dumps(res, indent=2))
    elif args.command == "run":
        res = run_inference(
            args.plan,
            args.output,
            args.model,
            args.revision,
            authorize=args.authorize_inference,
            mock=args.mock,
        )
        print(json.dumps(res, indent=2))
    elif args.command == "analyze":
        res = analyze_contrastive_mapping(args.run_dir, args.prompts, args.output, args.n_boot)
        print(f"Analysis completed. Report written to {args.output}")
    elif args.command == "smoke-test":
        smoke_out = Path(args.output)
        plan_dir = smoke_out / "plan"
        run_dir = smoke_out / "run"
        analysis_dir = smoke_out / "analysis"
        print("1. Preparing smoke plan...")
        prepare(plan_dir, smoke=True)
        print("2. Running mock inference...")
        run_inference(plan_dir, run_dir, mock=True)
        print("3. Analyzing contrastive representations...")
        res = analyze_contrastive_mapping(run_dir, plan_dir / "prompts.jsonl", analysis_dir, n_boot=200)
        print(f"Smoke test succeeded! Reports generated at {analysis_dir}")


if __name__ == "__main__":
    main()
