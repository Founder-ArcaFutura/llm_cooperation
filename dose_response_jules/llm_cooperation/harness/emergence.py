"""Pretraining emergence experiment harness for EleutherAI Pythia checkpoint sequence.

Evaluates the frozen dose-response instrument across training checkpoints, measuring:
1. Equal-utility cooperative preference: Delta_choice and Delta_log_P at Delta U = 0
2. Payoff response slope: d P(coop) / d(Delta U)
3. Cost crossover threshold: Delta U*
4. Decoupled format calibration: evaluates data/calibration_bank.json to prevent confusing
   early letter/token artifacts with preference absence.
5. Strategic concept decoding probe: lightweight linear probe on residual stream
   differentiating COOPERATE vs INDEPENDENT option representations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


@dataclass
class CheckpointSpec:
    model_id: str
    step: int
    revision: str
    training_tokens_billion: float
    is_step0: bool = False


# Canonical EleutherAI Pythia 1.4B / 2.8B intermediate checkpoint schedule
PYTHIA_1_4B_CHECKPOINTS = [
    CheckpointSpec("EleutherAI/pythia-1.4b", 0, "step0", 0.0, is_step0=True),
    CheckpointSpec("EleutherAI/pythia-1.4b", 1000, "step1000", 2.1),
    CheckpointSpec("EleutherAI/pythia-1.4b", 10000, "step10000", 21.0),
    CheckpointSpec("EleutherAI/pythia-1.4b", 50000, "step50000", 105.0),
    CheckpointSpec("EleutherAI/pythia-1.4b", 100000, "step100000", 210.0),
    CheckpointSpec("EleutherAI/pythia-1.4b", 143000, "step143000", 300.0),
]


def evaluate_mock_checkpoint_emergence(
    checkpoints: List[CheckpointSpec] = PYTHIA_1_4B_CHECKPOINTS,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic developmental trajectory to test analysis and decoding pipeline."""
    rng = np.random.default_rng(seed)
    rows = []

    for ckpt in checkpoints:
        step = ckpt.step
        # Format calibration improves with training: low early, high late
        calib_acc = 0.25 if step == 0 else min(0.95, 0.25 + 0.70 * (1.0 - np.exp(-step / 30000.0)))

        # Equal utility log prob preference: 0 at step 0, gradually emerges
        log_p_pref = 0.0 if step == 0 else min(0.65, 0.65 * (1.0 - np.exp(-max(0, step - 5000) / 40000.0)))
        choice_pref = 0.0 if step == 0 else min(0.28, 0.28 * (1.0 - np.exp(-max(0, step - 8000) / 45000.0)))

        # Payoff sensitivity slope (slope w.r.t delta_u) emerges later than format
        slope = 0.0 if step < 1000 else min(1.20, 1.20 * (1.0 - np.exp(-max(0, step - 10000) / 50000.0)))

        # Crossover threshold: shifts from undefined/0 to negative (willingness to absorb small cost)
        crossover = None if step < 10000 else float(-0.08 * (1.0 - np.exp(-step / 60000.0)))

        # Representation decoding accuracy (COOP vs INDEP linear probe)
        probe_acc = 0.50 if step == 0 else min(0.88, 0.50 + 0.38 * (1.0 - np.exp(-max(0, step - 15000) / 40000.0)))

        # Add small random noise
        noise = rng.normal(0.0, 0.015)

        rows.append({
            "model_id": ckpt.model_id,
            "step": step,
            "revision": ckpt.revision,
            "tokens_billion": ckpt.training_tokens_billion,
            "format_calibration_accuracy": float(np.clip(calib_acc + noise, 0.0, 1.0)),
            "equal_utility_log_prob_diff": float(log_p_pref + noise),
            "equal_utility_choice_diff": float(choice_pref + noise),
            "payoff_sensitivity_slope": float(slope + abs(noise)),
            "estimated_crossover_delta_u": crossover,
            "linear_probe_decodability": float(np.clip(probe_acc + noise, 0.0, 1.0)),
            "preference_precedes_decoding": bool(log_p_pref > 0.15 and probe_acc < 0.65),
        })

    return pd.DataFrame(rows)


def analyze_emergence_trajectory(emergence_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze the relationship between training progress, behavioral preference, and representation decoding."""
    df = emergence_df.sort_values("step").copy()

    # Step 0 baseline check (falsification: preferences should not exist at step 0)
    step0_row = df[df["step"] == 0]
    step0_clean = True
    if not step0_row.empty:
        step0_log_diff = step0_row["equal_utility_log_prob_diff"].values[0]
        step0_slope = step0_row["payoff_sensitivity_slope"].values[0]
        if abs(step0_log_diff) > 0.10 or abs(step0_slope) > 0.20:
            step0_clean = False

    # Detection of format onset vs preference onset vs slope onset vs decoding onset
    onset_format = None
    onset_preference = None
    onset_slope = None
    onset_probe = None

    for _, row in df.iterrows():
        s = int(row["step"])
        if onset_format is None and row["format_calibration_accuracy"] >= 0.60:
            onset_format = s
        if onset_preference is None and row["equal_utility_log_prob_diff"] >= 0.20:
            onset_preference = s
        if onset_slope is None and row["payoff_sensitivity_slope"] >= 0.40:
            onset_slope = s
        if onset_probe is None and row["linear_probe_decodability"] >= 0.70:
            onset_probe = s

    # Final checkpoint status
    final_row = df.iloc[-1]

    return {
        "step0_baseline_valid": step0_clean,
        "onset_steps": {
            "format_competence_step": onset_format,
            "equal_utility_preference_step": onset_preference,
            "payoff_sensitivity_step": onset_slope,
            "linear_concept_decoding_step": onset_probe,
        },
        "order_of_emergence": [
            ("format", onset_format),
            ("preference", onset_preference),
            ("sensitivity", onset_slope),
            ("probe_decodability", onset_probe),
        ],
        "final_checkpoint_metrics": {
            "step": int(final_row["step"]),
            "equal_utility_log_prob_diff": float(final_row["equal_utility_log_prob_diff"]),
            "equal_utility_choice_diff": float(final_row["equal_utility_choice_diff"]),
            "payoff_sensitivity_slope": float(final_row["payoff_sensitivity_slope"]),
            "crossover_threshold": final_row.get("estimated_crossover_delta_u"),
            "linear_probe_decodability": float(final_row["linear_probe_decodability"]),
        },
    }
