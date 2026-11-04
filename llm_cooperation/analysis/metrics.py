"""Statistical aggregation and metrics computation for Phase 0 results.

Per experimental specification (§4A.3, §6, §8):
1. Aggregation is performed at the scenario level across the 4 permutations before estimating
   cooperative-choice rates and conditional probabilities.
2. The 24 scenarios—NOT the 96 presentations—are treated as the independent starting units
   for uncertainty analysis to prevent pseudoreplication.
3. Clustered bootstrap intervals (resampling at scenario level) are computed.
4. Position bias (A/B/C/D frequency) and format validity rates are audited.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from llm_cooperation.items.schema import StrategyType


class RunDataValidationError(Exception):
    """Raised when experimental output records fail scientific integrity validation."""
    pass


def validate_run_data(metadata: Dict, records: List[Dict], expected_scenarios: Optional[int] = None):
    """Rigorous pre-analysis validation of experimental run records."""
    if not records:
        raise RunDataValidationError("Run dataset contains no presentation records.")

    # Determine expected scenarios if not specified
    if expected_scenarios is None:
        expected_scenarios = metadata.get("num_scenarios", 24)

    expected_presentations = expected_scenarios * 4
    if len(records) != expected_presentations:
        raise RunDataValidationError(
            f"Expected {expected_presentations} presentations ({expected_scenarios} scenarios x 4 permutations), "
            f"found {len(records)}."
        )

    # Check unique presentation IDs
    pres_ids = [r["presentation_id"] for r in records]
    if len(set(pres_ids)) != len(pres_ids):
        duplicates = [pid for pid in set(pres_ids) if pres_ids.count(pid) > 1]
        raise RunDataValidationError(f"Duplicate presentation IDs found: {duplicates}")

    # Check scenario representation and exact 4 permutations per scenario
    scenario_perms = {}
    for r in records:
        sc_id = r["scenario_id"]
        perm_idx = r["permutation_index"]
        if sc_id not in scenario_perms:
            scenario_perms[sc_id] = set()
        scenario_perms[sc_id].add(perm_idx)

        # Check finite and valid probabilities
        cond_probs = r.get("conditional_probs", {})
        if set(cond_probs.keys()) != {"A", "B", "C", "D"}:
            raise RunDataValidationError(f"Presentation {r['presentation_id']} missing A/B/C/D conditional probs.")
        for l, p in cond_probs.items():
            if not np.isfinite(p) or p < 0.0 or p > 1.0:
                raise RunDataValidationError(
                    f"Presentation {r['presentation_id']} has invalid conditional probability for {l}: {p}"
                )
        prob_sum = sum(cond_probs.values())
        if abs(prob_sum - 1.0) > 1e-4:
            raise RunDataValidationError(
                f"Presentation {r['presentation_id']} conditional probabilities sum to {prob_sum}, expected 1.0."
            )

    if len(scenario_perms) != expected_scenarios:
        raise RunDataValidationError(
            f"Expected {expected_scenarios} distinct scenarios, found {len(scenario_perms)}."
        )

    for sc_id, perms in scenario_perms.items():
        if perms != {0, 1, 2, 3}:
            raise RunDataValidationError(
                f"Scenario {sc_id} does not have complete permutations 0..3: {perms}"
            )


def load_run_results(file_path: str, validate: bool = True) -> Tuple[Dict, List[Dict]]:
    metadata = None
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if first_line:
            metadata = json.loads(first_line)
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))

    if validate and metadata is not None:
        validate_run_data(metadata, records)

    return metadata, records


def aggregate_by_scenario(records: List[Dict]) -> pd.DataFrame:
    """Aggregate the 4 counterbalanced permutations into scenario-level metrics."""
    df = pd.DataFrame(records)

    # For each record, unpack conditional prob for each strategy
    for strat in [s.value for s in StrategyType]:
        df[f"prob_{strat}"] = df.apply(
            lambda row: row["conditional_probs"][row["strategy_to_letter"][strat]],
            axis=1,
        )
        df[f"is_argmax_{strat}"] = (df["forced_choice_argmax_strategy"] == strat).astype(float)
        df[f"is_gen_{strat}"] = (df["generated_strategy"] == strat).astype(float)

    # Grouping columns: preserve template_id, split, domain if available
    group_cols = ["scenario_id", "partner_type", "context_type"]
    extra_meta_cols = [c for c in ["template_id", "split", "domain"] if c in df.columns]

    agg_dict = {
        # Mean conditional probability across the 4 permutations
        "coop_cond_prob": ("prob_COOPERATE", "mean"),
        "indep_cond_prob": ("prob_INDEPENDENT", "mean"),
        "compete_cond_prob": ("prob_COMPETE_EXPLOIT", "mean"),
        "disengage_cond_prob": ("prob_DISENGAGE", "mean"),
        # Argmax selection rate (fraction of 4 permutations where COOPERATE won)
        "coop_argmax_rate": ("is_argmax_COOPERATE", "mean"),
        "indep_argmax_rate": ("is_argmax_INDEPENDENT", "mean"),
        "compete_argmax_rate": ("is_argmax_COMPETE_EXPLOIT", "mean"),
        "disengage_argmax_rate": ("is_argmax_DISENGAGE", "mean"),
        # Generated compliance
        "valid_letter_rate": ("is_valid_letter", "mean"),
        "gen_coop_rate": ("is_gen_COOPERATE", "mean"),
        "num_permutations": ("permutation_index", "count"),
    }
    for col in extra_meta_cols:
        agg_dict[col] = (col, "first")

    agg_df = df.groupby(group_cols).agg(**agg_dict).reset_index()

    # If template_id was not explicitly in records, infer template_id if scenario_id matches expanded pattern
    if "template_id" not in agg_df.columns:
        # Check if scenario_01/scenario_13 near-match or expanded_001_human pattern
        def infer_tid(row):
            sid = str(row["scenario_id"])
            if sid.startswith("expanded_"):
                # expanded_001_human -> template_001
                parts = sid.split("_")
                if len(parts) >= 2:
                    return f"template_{parts[1]}"
            return None
        agg_df["template_id"] = agg_df.apply(infer_tid, axis=1)

    return agg_df


def template_cluster_bootstrap(
    scenario_df: pd.DataFrame,
    metric_col: str,
    n_bootstraps: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, float]:
    """Bootstrap confidence intervals by resampling situation templates (keeping human and AI paired variants together).

    If template_id is present, resamples templates with replacement, taking both human and AI rows.
    If template_id is not present, falls back gracefully to scenario_cluster_bootstrap.
    """
    if "template_id" not in scenario_df.columns or scenario_df["template_id"].isnull().all():
        return scenario_cluster_bootstrap(scenario_df, metric_col, n_bootstraps=n_bootstraps, alpha=alpha, seed=seed)

    rng = np.random.default_rng(seed)
    unique_templates = scenario_df["template_id"].dropna().unique()
    n_templates = len(unique_templates)

    # Pre-index template rows
    template_groups = {tid: scenario_df[scenario_df["template_id"] == tid][metric_col].values for tid in unique_templates}

    boot_means = []
    for _ in range(n_bootstraps):
        sampled_tids = rng.choice(unique_templates, size=n_templates, replace=True)
        sampled_vals = np.concatenate([template_groups[tid] for tid in sampled_tids])
        boot_means.append(float(np.mean(sampled_vals)))

    all_vals = scenario_df[metric_col].values
    ci_lower = float(np.percentile(boot_means, 100 * (alpha / 2)))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    mean_val = float(np.mean(all_vals))
    std_val = float(np.std(all_vals, ddof=1)) if len(all_vals) > 1 else 0.0

    return {
        "mean": mean_val,
        "std": std_val,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "bootstrap_samples": n_bootstraps,
        "clustering_level": "template",
        "num_clusters": n_templates,
    }


def scenario_cluster_bootstrap(
    scenario_df: pd.DataFrame,
    metric_col: str,
    n_bootstraps: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, float]:
    """Bootstrap confidence intervals by resampling at the scenario level (N=24).

    Avoids pseudoreplication across permutations.
    """
    rng = np.random.default_rng(seed)
    values = scenario_df[metric_col].values
    n = len(values)
    boot_means = []

    for _ in range(n_bootstraps):
        sample = rng.choice(values, size=n, replace=True)
        boot_means.append(np.mean(sample))

    ci_lower = float(np.percentile(boot_means, 100 * (alpha / 2)))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))

    return {
        "mean": mean_val,
        "std": std_val,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "bootstrap_samples": n_bootstraps,
    }


def audit_position_bias(records: List[Dict]) -> Dict[str, float]:
    """Compute forced-choice argmax selection frequency by letter A, B, C, D."""
    df = pd.DataFrame(records)
    counts = df["forced_choice_argmax_letter"].value_counts(normalize=True)
    return {letter: float(counts.get(letter, 0.0)) for letter in ["A", "B", "C", "D"]}
