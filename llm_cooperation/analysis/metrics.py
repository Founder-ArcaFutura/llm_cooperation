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
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from llm_cooperation.items.schema import StrategyType


def load_run_results(file_path: str) -> Tuple[Dict, List[Dict]]:
    metadata = None
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if first_line:
            metadata = json.loads(first_line)
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
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

    # Group by scenario_id
    grouped = df.groupby(["scenario_id", "partner_type", "context_type"])

    agg_df = grouped.agg(
        # Mean conditional probability across the 4 permutations
        coop_cond_prob=("prob_COOPERATE", "mean"),
        indep_cond_prob=("prob_INDEPENDENT", "mean"),
        compete_cond_prob=("prob_COMPETE_EXPLOIT", "mean"),
        disengage_cond_prob=("prob_DISENGAGE", "mean"),
        # Argmax selection rate (fraction of 4 permutations where COOPERATE won)
        coop_argmax_rate=("is_argmax_COOPERATE", "mean"),
        indep_argmax_rate=("is_argmax_INDEPENDENT", "mean"),
        compete_argmax_rate=("is_argmax_COMPETE_EXPLOIT", "mean"),
        disengage_argmax_rate=("is_argmax_DISENGAGE", "mean"),
        # Generated compliance
        valid_letter_rate=("is_valid_letter", "mean"),
        gen_coop_rate=("is_gen_COOPERATE", "mean"),
        num_permutations=("permutation_index", "count"),
    ).reset_index()

    return agg_df


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
