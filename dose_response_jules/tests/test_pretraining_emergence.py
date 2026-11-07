"""Tests for Pretraining Emergence checkpoint schedule and trajectory analysis."""

import pandas as pd
import pytest

from llm_cooperation.harness.emergence import (
    PYTHIA_1_4B_CHECKPOINTS,
    evaluate_mock_checkpoint_emergence,
    analyze_emergence_trajectory,
)


def test_pythia_checkpoint_schedule():
    assert len(PYTHIA_1_4B_CHECKPOINTS) == 6
    steps = [c.step for c in PYTHIA_1_4B_CHECKPOINTS]
    assert steps == [0, 1000, 10000, 50000, 100000, 143000]
    assert PYTHIA_1_4B_CHECKPOINTS[0].is_step0 is True
    assert PYTHIA_1_4B_CHECKPOINTS[-1].training_tokens_billion == 300.0


def test_evaluate_mock_checkpoint_emergence_trajectory():
    df = evaluate_mock_checkpoint_emergence(seed=123)
    assert len(df) == 6
    assert set(df.columns) >= {
        "model_id",
        "step",
        "tokens_billion",
        "format_calibration_accuracy",
        "equal_utility_log_prob_diff",
        "equal_utility_choice_diff",
        "payoff_sensitivity_slope",
        "linear_probe_decodability",
    }

    # Step 0 baseline should have ~0 preference
    step0 = df[df["step"] == 0].iloc[0]
    assert abs(step0["equal_utility_log_prob_diff"]) < 0.05
    assert step0["payoff_sensitivity_slope"] < 0.10

    # Final checkpoint should show developed preferences and positive sensitivity slope
    final = df.iloc[-1]
    assert final["format_calibration_accuracy"] > 0.80
    assert final["equal_utility_log_prob_diff"] > 0.40
    assert final["payoff_sensitivity_slope"] > 0.80

    # Emergence trajectory analysis
    summary = analyze_emergence_trajectory(df)
    assert summary["step0_baseline_valid"] is True
    onsets = summary["onset_steps"]
    assert onsets["format_competence_step"] is not None
    assert onsets["equal_utility_preference_step"] is not None
