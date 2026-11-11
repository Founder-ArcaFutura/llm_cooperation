"""Analysis and reporting for continuation-likelihood assay results.

Provides:
- Scenario-level aggregation across templates (treating templates as
  repeated measurements, not independent samples)
- Rank distributions for all four strategies
- Cooperation margins (sum and mean log-probability)
- Template sensitivity analysis
- Length-normalization sensitivity
- Control-context delta computation
- Stratification by partner_type, context_type, domain
- Bootstrap confidence intervals (scenario-clustered)
- Cross-model comparison on matched scenarios
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from llm_cooperation.continuation.runner import load_continuation_results

STRATEGIES = ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]


def _safe_mean(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return float(np.mean(vals))


def _bootstrap_ci(
    vals: List[float],
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float, float]:
    """Bootstrap mean and CI for a list of values.

    Returns: (mean, lower_ci, upper_ci)
    """
    if not vals:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.array(vals, dtype=float)
    if rng is None:
        rng = np.random.default_rng(seed=42)
    boot_means = [
        float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_boot)
    ]
    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_means, 100 * alpha))
    upper = float(np.percentile(boot_means, 100 * (1.0 - alpha)))
    return (float(np.mean(arr)), lower, upper)


def aggregate_by_scenario(records: List[Dict]) -> Dict[str, Dict]:
    """Group records by scenario_id, aggregating across templates.

    Returns dict: scenario_id -> aggregated stats dict.
    """
    by_scenario: Dict[str, List[Dict]] = {}
    for rec in records:
        sid = rec["scenario_id"]
        if sid not in by_scenario:
            by_scenario[sid] = []
        by_scenario[sid].append(rec)

    aggregated = {}
    for sid, recs in by_scenario.items():
        # Collect per-strategy sum and mean log-probs across templates
        per_strategy_sums: Dict[str, List[float]] = {s: [] for s in STRATEGIES}
        per_strategy_means: Dict[str, List[float]] = {s: [] for s in STRATEGIES}
        per_strategy_ntokens: Dict[str, List[int]] = {s: [] for s in STRATEGIES}
        templates_seen = set()
        coop_first_sum_count = 0
        coop_first_mean_count = 0

        partner_type = recs[0].get("partner_type")
        context_type = recs[0].get("context_type")
        domain = recs[0].get("domain")
        split = recs[0].get("split")

        for rec in recs:
            templates_seen.add(rec.get("template_id"))
            coop_first_sum_count += int(rec.get("coop_first_by_sum", False))
            coop_first_mean_count += int(rec.get("coop_first_by_mean", False))

            scores = rec.get("scores", {})
            for strat in STRATEGIES:
                if strat in scores:
                    s = scores[strat]
                    per_strategy_sums[strat].append(s["sum_log_prob"])
                    per_strategy_means[strat].append(s["mean_log_prob"])
                    per_strategy_ntokens[strat].append(s["num_scored_tokens"])

        n_templates = len(recs)

        # Mean rank under sum across templates
        avg_sum: Dict[str, float] = {}
        avg_mean: Dict[str, float] = {}
        avg_ntokens: Dict[str, float] = {}
        for strat in STRATEGIES:
            sl = per_strategy_sums[strat]
            ml = per_strategy_means[strat]
            avg_sum[strat] = float(np.mean(sl)) if sl else float("nan")
            avg_mean[strat] = float(np.mean(ml)) if ml else float("nan")
            avg_ntokens[strat] = float(np.mean(per_strategy_ntokens[strat])) if per_strategy_ntokens[strat] else 0.0

        # Rank by average sum
        sorted_by_avg_sum = sorted(STRATEGIES, key=lambda s: avg_sum.get(s, float("-inf")), reverse=True)
        rank_by_avg_sum = {s: i + 1 for i, s in enumerate(sorted_by_avg_sum)}

        sorted_by_avg_mean = sorted(STRATEGIES, key=lambda s: avg_mean.get(s, float("-inf")), reverse=True)
        rank_by_avg_mean = {s: i + 1 for i, s in enumerate(sorted_by_avg_mean)}

        coop_sum = avg_sum.get("COOPERATE", float("nan"))
        indep_sum = avg_sum.get("INDEPENDENT", float("nan"))
        comp_sum = avg_sum.get("COMPETE_EXPLOIT", float("nan"))

        aggregated[sid] = {
            "scenario_id": sid,
            "partner_type": partner_type,
            "context_type": context_type,
            "domain": domain,
            "split": split,
            "n_templates": n_templates,
            "templates": sorted(templates_seen),
            "avg_sum_log_prob": avg_sum,
            "avg_mean_log_prob": avg_mean,
            "avg_num_tokens": avg_ntokens,
            "rank_by_avg_sum": rank_by_avg_sum,
            "rank_by_avg_mean": rank_by_avg_mean,
            "coop_first_by_sum_fraction": coop_first_sum_count / n_templates if n_templates else 0.0,
            "coop_first_by_mean_fraction": coop_first_mean_count / n_templates if n_templates else 0.0,
            "coop_vs_independent_sum_delta": (
                coop_sum - indep_sum
                if not (np.isnan(coop_sum) or np.isnan(indep_sum)) else None
            ),
            "coop_vs_compete_sum_delta": (
                coop_sum - comp_sum
                if not (np.isnan(coop_sum) or np.isnan(comp_sum)) else None
            ),
        }

    return aggregated


def compute_overall_statistics(
    aggregated: Dict[str, Dict],
    n_bootstraps: int = 2000,
    rng: Optional[np.random.Generator] = None,
) -> Dict:
    """Compute experiment-level statistics over all scenarios.

    Unit of analysis: scenario (not individual template or token).
    Templates are treated as repeated measurements within scenarios.
    """
    if rng is None:
        rng = np.random.default_rng(seed=42)

    agg_list = list(aggregated.values())
    n_scenarios = len(agg_list)

    if n_scenarios == 0:
        return {"error": "No scenarios to analyze"}

    # --- Strategy rank distributions ---
    rank_distributions: Dict[str, Dict[int, int]] = {s: {1: 0, 2: 0, 3: 0, 4: 0} for s in STRATEGIES}
    for agg in agg_list:
        for strat in STRATEGIES:
            r = agg["rank_by_avg_sum"].get(strat, 0)
            if r in rank_distributions[strat]:
                rank_distributions[strat][r] += 1

    rank_pct: Dict[str, Dict[int, float]] = {}
    for strat in STRATEGIES:
        rank_pct[strat] = {
            r: round(100.0 * count / n_scenarios, 1)
            for r, count in rank_distributions[strat].items()
        }

    # --- Cooperation first ---
    coop_first_by_sum = [agg["coop_first_by_sum_fraction"] for agg in agg_list]
    coop_first_by_mean = [agg["coop_first_by_mean_fraction"] for agg in agg_list]

    # Scenario-level: did coop rank first across >50% of templates?
    coop_majority_first_sum = sum(1 for x in coop_first_by_sum if x > 0.5)
    coop_majority_first_mean = sum(1 for x in coop_first_by_mean if x > 0.5)

    # --- Log-probability margins ---
    coop_vs_indep_deltas = [
        agg["coop_vs_independent_sum_delta"]
        for agg in agg_list
        if agg["coop_vs_independent_sum_delta"] is not None
    ]
    coop_vs_comp_deltas = [
        agg["coop_vs_compete_sum_delta"]
        for agg in agg_list
        if agg["coop_vs_compete_sum_delta"] is not None
    ]

    ci_coop_indep = _bootstrap_ci(coop_vs_indep_deltas, n_boot=n_bootstraps, rng=rng)
    ci_coop_comp = _bootstrap_ci(coop_vs_comp_deltas, n_boot=n_bootstraps, rng=rng)

    # --- Length sensitivity ---
    # Compute average token count per strategy to flag length confounds
    avg_tokens_per_strategy: Dict[str, List[float]] = {s: [] for s in STRATEGIES}
    for agg in agg_list:
        for strat in STRATEGIES:
            nt = agg["avg_num_tokens"].get(strat, 0.0)
            if nt > 0:
                avg_tokens_per_strategy[strat].append(nt)
    mean_tokens: Dict[str, Optional[float]] = {
        s: _safe_mean(vals) for s, vals in avg_tokens_per_strategy.items()
    }

    return {
        "n_scenarios": n_scenarios,
        "strategy_rank_distributions_pct": rank_pct,
        "coop_first_pct_by_sum": round(100.0 * coop_majority_first_sum / n_scenarios, 1),
        "coop_first_pct_by_mean": round(100.0 * coop_majority_first_mean / n_scenarios, 1),
        "coop_vs_independent_sum_delta": {
            "mean": ci_coop_indep[0],
            "ci_lower": ci_coop_indep[1],
            "ci_upper": ci_coop_indep[2],
            "n": len(coop_vs_indep_deltas),
        },
        "coop_vs_compete_sum_delta": {
            "mean": ci_coop_comp[0],
            "ci_lower": ci_coop_comp[1],
            "ci_upper": ci_coop_comp[2],
            "n": len(coop_vs_comp_deltas),
        },
        "mean_num_tokens_per_strategy": mean_tokens,
        "length_confound_note": (
            "Length differences between strategies may confound sum log-probability "
            "rankings. Use mean log-probability as a cross-length reference but do not "
            "treat it as an unbiased estimator."
        ),
    }


def compute_stratified_statistics(
    aggregated: Dict[str, Dict],
    stratify_by: str = "partner_type",
) -> Dict[str, Dict]:
    """Compute statistics separately for each stratum.

    Args:
        aggregated: Output of aggregate_by_scenario().
        stratify_by: Field name to stratify by (e.g. 'partner_type', 'context_type').

    Returns:
        Dict: stratum_value -> statistics dict.
    """
    strata: Dict[str, List[Dict]] = {}
    for agg in aggregated.values():
        val = agg.get(stratify_by) or "unknown"
        if val not in strata:
            strata[val] = []
        strata[val].append(agg)

    results = {}
    for stratum_val, agg_list in strata.items():
        n = len(agg_list)
        if n == 0:
            continue
        coop_first = sum(1 for a in agg_list if a["coop_first_by_sum_fraction"] > 0.5)
        deltas = [a["coop_vs_independent_sum_delta"] for a in agg_list if a["coop_vs_independent_sum_delta"] is not None]
        results[stratum_val] = {
            "n_scenarios": n,
            "coop_first_pct": round(100.0 * coop_first / n, 1),
            "coop_vs_independent_sum_delta_mean": _safe_mean(deltas),
            "coop_vs_independent_sum_delta_std": float(np.std(deltas)) if len(deltas) > 1 else None,
        }
    return results


def compute_template_sensitivity(records: List[Dict]) -> Dict[str, Dict]:
    """Compute per-template statistics to assess template sensitivity.

    Returns dict: template_id -> statistics.
    """
    by_template: Dict[str, List[Dict]] = {}
    for rec in records:
        tid = rec.get("template_id", "unknown")
        if tid not in by_template:
            by_template[tid] = []
        by_template[tid].append(rec)

    results = {}
    for tid, recs in by_template.items():
        n = len(recs)
        coop_first_sum = sum(1 for r in recs if r.get("coop_first_by_sum", False))
        deltas = [r.get("coop_vs_independent_sum_delta") for r in recs if r.get("coop_vs_independent_sum_delta") is not None]
        results[tid] = {
            "n_presentations": n,
            "coop_first_pct": round(100.0 * coop_first_sum / n, 1),
            "coop_vs_independent_sum_delta_mean": _safe_mean(deltas),
        }
    return results


def compare_models(
    result_paths: List[str],
    n_bootstraps: int = 2000,
    rng: Optional[np.random.Generator] = None,
) -> Dict:
    """Cross-model comparison on matched scenarios.

    Args:
        result_paths: Paths to JSONL files from multiple model runs.
        n_bootstraps: Bootstrap resamples for CIs.

    Returns:
        Dict with per-model statistics and paired scenario differences.
    """
    if rng is None:
        rng = np.random.default_rng(seed=42)

    per_model: Dict[str, Dict] = {}  # model_name -> {scenario_id -> agg}

    for path in result_paths:
        metadata, records = load_continuation_results(path)
        model_name = metadata.get("model_name", Path(path).stem)
        agg = aggregate_by_scenario(records)
        per_model[model_name] = {
            "metadata": metadata,
            "aggregated": agg,
            "statistics": compute_overall_statistics(agg, n_bootstraps=n_bootstraps, rng=rng),
        }

    # Identify scenarios common to all models
    if per_model:
        common_scenarios = set.intersection(
            *[set(d["aggregated"].keys()) for d in per_model.values()]
        )
    else:
        common_scenarios = set()

    # Paired scenario deltas (model A vs model B on matched scenarios)
    paired_diffs: Dict[str, Dict] = {}
    model_names = list(per_model.keys())
    for i in range(len(model_names)):
        for j in range(i + 1, len(model_names)):
            ma, mb = model_names[i], model_names[j]
            pair_key = f"{ma} vs {mb}"
            coop_indep_diffs = []
            for sid in common_scenarios:
                agg_a = per_model[ma]["aggregated"][sid]
                agg_b = per_model[mb]["aggregated"][sid]
                d_a = agg_a.get("coop_vs_independent_sum_delta")
                d_b = agg_b.get("coop_vs_independent_sum_delta")
                if d_a is not None and d_b is not None:
                    coop_indep_diffs.append(d_a - d_b)
            ci = _bootstrap_ci(coop_indep_diffs, n_boot=n_bootstraps, rng=rng)
            paired_diffs[pair_key] = {
                "n_matched_scenarios": len(common_scenarios),
                "coop_vs_independent_delta_diff": {
                    "mean": ci[0], "ci_lower": ci[1], "ci_upper": ci[2],
                    "n": len(coop_indep_diffs),
                },
            }

    return {
        "per_model": {m: d["statistics"] for m, d in per_model.items()},
        "paired_scenario_diffs": paired_diffs,
        "n_common_scenarios": len(common_scenarios),
        "model_names": model_names,
    }


def generate_text_report(
    metadata: Dict,
    aggregated: Dict[str, Dict],
    overall_stats: Dict,
    output_path: Optional[str] = None,
) -> str:
    """Generate a Markdown-format report for a single model run."""
    model_name = metadata.get("model_name", "unknown")
    run_id = metadata.get("run_id", "unknown")
    n_scenarios = overall_stats.get("n_scenarios", 0)
    templates = metadata.get("templates_used", [])
    research_status = metadata.get("research_status", "exploratory")

    lines = [
        "# Continuation-Likelihood Cooperation Assay: Results",
        "",
        f"> **Research status**: {research_status}  ",
        f"> **Model**: `{model_name}`  ",
        f"> **Run ID**: `{run_id}`  ",
        f"> **Scenarios evaluated**: {n_scenarios}  ",
        f"> **Templates**: {', '.join(templates)}  ",
        "",
        "> [!IMPORTANT]",
        "> This assay measures conditional language probability, not agent intent.",
        "> Results are exploratory. Do not interpret as confirmatory evidence.",
        "",
        "## 1. Strategy Rank Distributions",
        "",
        "Percentage of scenarios in which each strategy ranks at each position",
        "(ranking by average sum log-probability across templates):",
        "",
        "| Strategy | Rank 1 (%) | Rank 2 (%) | Rank 3 (%) | Rank 4 (%) |",
        "| --- | --- | --- | --- | --- |",
    ]

    rd = overall_stats.get("strategy_rank_distributions_pct", {})
    for strat in STRATEGIES:
        pct = rd.get(strat, {})
        lines.append(
            f"| {strat} | {pct.get(1, 0):.1f} | {pct.get(2, 0):.1f} | "
            f"{pct.get(3, 0):.1f} | {pct.get(4, 0):.1f} |"
        )

    coop_first_sum = overall_stats.get("coop_first_pct_by_sum", 0.0)
    coop_first_mean = overall_stats.get("coop_first_pct_by_mean", 0.0)

    ci_coop_indep = overall_stats.get("coop_vs_independent_sum_delta", {})
    ci_coop_comp = overall_stats.get("coop_vs_compete_sum_delta", {})

    lines += [
        "",
        "## 2. Cooperation Preference Summary",
        "",
        f"- Scenarios where COOPERATE ranks first (by sum log-P): **{coop_first_sum:.1f}%**",
        f"- Scenarios where COOPERATE ranks first (by mean log-P): **{coop_first_mean:.1f}%**",
        "",
        "## 3. Log-Probability Margins (bootstrap 95% CI, scenario-clustered)",
        "",
        "| Comparison | Mean delta | 95% CI lower | 95% CI upper | N scenarios |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| COOP vs INDEPENDENT | {ci_coop_indep.get('mean', float('nan')):.3f} | "
            f"{ci_coop_indep.get('ci_lower', float('nan')):.3f} | "
            f"{ci_coop_indep.get('ci_upper', float('nan')):.3f} | "
            f"{ci_coop_indep.get('n', 0)} |"
        ),
        (
            f"| COOP vs COMPETE | {ci_coop_comp.get('mean', float('nan')):.3f} | "
            f"{ci_coop_comp.get('ci_lower', float('nan')):.3f} | "
            f"{ci_coop_comp.get('ci_upper', float('nan')):.3f} | "
            f"{ci_coop_comp.get('n', 0)} |"
        ),
        "",
        "## 4. Length Information",
        "",
        "Mean number of tokens per strategy (affects sum log-probability):",
        "",
        "| Strategy | Mean tokens |",
        "| --- | --- |",
    ]

    tokens_info = overall_stats.get("mean_num_tokens_per_strategy", {})
    for strat in STRATEGIES:
        t = tokens_info.get(strat)
        t_str = f"{t:.1f}" if t is not None else "N/A"
        lines.append(f"| {strat} | {t_str} |")

    lines += [
        "",
        f"> {overall_stats.get('length_confound_note', '')}",
        "",
        "## 5. Methodological Limitations",
        "",
        "- Continuation likelihood reflects the model's learned language distribution,",
        "  not an explicit behavioral choice.",
        "- Length differences between strategies confound sum log-probability rankings.",
        "- Template framing may interact with strategy descriptions.",
        "- Results may reflect grammaticality, fluency, or frequency differences",
        "  that are independent of cooperative intent.",
        "- A positive cooperative preference signal requires robustness under",
        "  lexical and template controls before scientific interpretation.",
    ]

    report = "\n".join(lines)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(report, encoding="utf-8")

    return report
