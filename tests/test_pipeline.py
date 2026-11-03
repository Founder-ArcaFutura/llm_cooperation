"""Unit tests for letter parsing, scoring, and analysis pipeline."""

import json
from pathlib import Path
import pytest

from llm_cooperation.harness.runner import parse_generated_letter
from llm_cooperation.harness.runner import run_experiment
from llm_cooperation.analysis.pipeline import analyze_results
from llm_cooperation.analysis.metrics import (
    load_run_results,
    aggregate_by_scenario,
    scenario_cluster_bootstrap,
    audit_position_bias,
)


def test_parse_generated_letter():
    # Valid exact letters
    assert parse_generated_letter("A") == ("A", True)
    assert parse_generated_letter("B") == ("B", True)
    assert parse_generated_letter(" C") == ("C", True)
    assert parse_generated_letter("D\n") == ("D", True)

    # Valid with punctuation / prefix
    assert parse_generated_letter("A.") == ("A", True)
    assert parse_generated_letter("B, because...") == ("B", True)
    assert parse_generated_letter(" C: action") == ("C", True)

    # Invalid responses
    assert parse_generated_letter("") == (None, False)
    assert parse_generated_letter("   ") == (None, False)
    assert parse_generated_letter("I would choose to collaborate.") == (None, False)
    assert parse_generated_letter("None of the above") == (None, False)
    assert parse_generated_letter("E") == (None, False)


def test_end_to_end_mock_pipeline(tmp_path):
    output_dir = tmp_path / "results"
    reports_dir = tmp_path / "reports"

    # Run mock experiment
    result_file = run_experiment(
        model_name="test-mock-model",
        output_dir=str(output_dir),
        mock=True,
        seed=123,
    )
    assert Path(result_file).exists()

    # Verify records in output
    metadata, records = load_run_results(str(result_file))
    assert metadata["model_name"] == "test-mock-model"
    assert metadata["num_scenarios"] == 24
    assert len(records) == 96

    # Verify scenario aggregation
    scenario_df = aggregate_by_scenario(records)
    assert len(scenario_df) == 24
    assert set(scenario_df.columns).issuperset({
        "scenario_id", "partner_type", "context_type",
        "coop_cond_prob", "coop_argmax_rate", "valid_letter_rate"
    })

    # Run full analysis
    analysis_res = analyze_results(str(result_file), output_dir=str(reports_dir))
    assert Path(analysis_res["scenario_csv"]).exists()
    assert Path(analysis_res["report_markdown"]).exists()
    assert len(analysis_res["plots"]) == 3
    for p in analysis_res["plots"]:
        assert Path(p).exists()
