"""Tests for Phase 0 expansion: 120-scenario bank, calibration suite, and template clustering."""

import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from llm_cooperation.items.schema import (
    ScenarioBank,
    Scenario,
    PartnerType,
    ContextType,
    StrategyType,
    CalibrationBank,
    CalibrationItem,
)
from llm_cooperation.items.permutations import (
    generate_all_presentations,
    generate_all_calibration_presentations,
)
from llm_cooperation.items.audit import audit_scenarios, audit_calibration
from llm_cooperation.harness.runner import run_calibration, run_experiment
from llm_cooperation.analysis.metrics import (
    load_run_results,
    aggregate_by_scenario,
    template_cluster_bootstrap,
    scenario_cluster_bootstrap,
)
from llm_cooperation.analysis.pipeline import analyze_results


def test_expanded_bank_schema_and_balance():
    """Verify that data/scenarios_v1_expanded.json conforms to all factorial balance rules."""
    bank_path = "data/scenarios_v1_expanded.json"
    assert Path(bank_path).exists()

    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bank = ScenarioBank(**data)
    scenarios = bank.scenarios
    assert len(scenarios) == 120
    assert bank.status == "pending_human_scientific_review"

    # Cell balance: 15 per cell
    cells = {}
    for s in scenarios:
        cell = (s.partner_type.value, s.context_type.value)
        cells[cell] = cells.get(cell, 0) + 1

    for p in ["human", "ai"]:
        for c in ContextType:
            assert cells.get((p, c.value)) == 15

    # Template pairing: exactly 60 templates with 1 human and 1 ai variant
    templates = {}
    for s in scenarios:
        assert s.template_id is not None
        templates.setdefault(s.template_id, []).append(s)

    assert len(templates) == 60
    exp_templates = 0
    conf_templates = 0
    for tid, scs in templates.items():
        assert len(scs) == 2
        partners = {sc.partner_type for sc in scs}
        assert partners == {PartnerType.HUMAN, PartnerType.AI}
        splits = {sc.split for sc in scs}
        assert len(splits) == 1
        split_val = list(splits)[0]
        assert split_val in ("exploratory", "confirmatory")
        if split_val == "exploratory":
            exp_templates += 1
        else:
            conf_templates += 1

    assert exp_templates == 40
    assert conf_templates == 20

    # Latin square permutation check
    all_pres = generate_all_presentations(scenarios)
    assert len(all_pres) == 480
    letter_counts = {l: {st: 0 for st in StrategyType} for l in ["A", "B", "C", "D"]}
    for p in all_pres:
        for opt in p.options:
            letter_counts[opt.letter][opt.strategy] += 1

    for l in ["A", "B", "C", "D"]:
        for st in StrategyType:
            assert letter_counts[l][st] == 120


def test_calibration_bank_schema_and_balance():
    """Verify that data/calibration_bank.json contains 24 items balanced under Latin square."""
    calib_path = "data/calibration_bank.json"
    assert Path(calib_path).exists()

    with open(calib_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bank = CalibrationBank(**data)
    items = bank.items
    assert len(items) == 24

    opt_counts = {}
    for it in items:
        opt_counts[it.correct_option_id] = opt_counts.get(it.correct_option_id, 0) + 1

    for opt_id in ["opt_1", "opt_2", "opt_3", "opt_4"]:
        assert opt_counts[opt_id] == 6

    # Latin square permutations
    presentations = generate_all_calibration_presentations(items)
    assert len(presentations) == 96

    correct_letters = {"A": 0, "B": 0, "C": 0, "D": 0}
    for p in presentations:
        correct_letters[p.correct_letter] += 1

    for l in ["A", "B", "C", "D"]:
        assert correct_letters[l] == 24


def test_audit_functions():
    """Test audit_scenarios and audit_calibration programmatic APIs."""
    assert audit_scenarios("data/scenarios.json") is True
    assert audit_scenarios("data/scenarios_v1_expanded.json") is True
    assert audit_calibration("data/calibration_bank.json") is True


def test_calibration_mock_and_invariant_a_detector(tmp_path):
    """Verify calibration runner correctly detects Pythia-style invariant-A pathology."""
    out_dir = tmp_path / "calib_results"

    # 1. Normal model should PASS
    normal_path, normal_summary = run_calibration(
        model_name="mock-qwen2.5-3b",
        output_dir=str(out_dir),
        mock=True,
    )
    assert normal_summary["status"] == "PASS"
    assert normal_summary["forced_choice_accuracy"] >= 0.90
    assert normal_summary["invariant_a_detected"] is False

    # 2. Pythia-style model should fail and trigger invariant-A detector
    pythia_path, pythia_summary = run_calibration(
        model_name="mock-pythia-2.8b",
        output_dir=str(out_dir),
        mock=True,
    )
    assert pythia_summary["invariant_a_detected"] is True
    assert pythia_summary["position_distribution"]["A"] >= 0.95


def test_template_level_clustering(tmp_path):
    """Verify that template_cluster_bootstrap groups paired human/AI variants."""
    df_data = []
    for i in range(1, 11):
        tid = f"template_{i:03d}"
        # Human variant
        df_data.append({
            "scenario_id": f"sc_{i}_human",
            "template_id": tid,
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "coop_argmax_rate": 0.8,
            "coop_cond_prob": 0.7,
        })
        # AI variant
        df_data.append({
            "scenario_id": f"sc_{i}_ai",
            "template_id": tid,
            "partner_type": "ai",
            "context_type": "neutral_or_costless",
            "coop_argmax_rate": 0.8,
            "coop_cond_prob": 0.7,
        })
    df = pd.DataFrame(df_data)

    boot = template_cluster_bootstrap(df, "coop_argmax_rate", n_bootstraps=500)
    assert boot["clustering_level"] == "template"
    assert boot["num_clusters"] == 10
    assert 0.75 <= boot["mean"] <= 0.85


def test_expanded_run_and_analysis_mock(tmp_path):
    """Verify end-to-end synthetic run and analysis on the expanded bank."""
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"

    # Run mock on expanded bank
    run_file = run_experiment(
        model_name="mock-qwen-test",
        scenarios_path="data/scenarios_v1_expanded.json",
        output_dir=str(out_dir),
        mock=True,
        seed=42,
    )
    assert run_file.exists()

    # Analyze
    report_dict = analyze_results(
        results_path=str(run_file),
        output_dir=str(report_dir),
        num_bootstraps=500,
    )
    assert Path(report_dict["report_markdown"]).exists()
    assert Path(report_dict["scenario_csv"]).exists()

    # Verify report contains exploratory, confirmatory, and principal contrast sections
    with open(report_dict["report_markdown"], "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "Exploratory Split" in md_text
    assert "Held-Out Confirmatory Split" in md_text
    assert "Preregistered Primary Confirmatory Contrast" in md_text
