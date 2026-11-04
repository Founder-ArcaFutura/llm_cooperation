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
    principal_context_contrast,
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
    assert "Preregistered Principal Contrast" in md_text
    assert "480 total counterbalanced presentations" in md_text


def test_principal_contrast_keeps_human_ai_rows_paired():
    """Perfectly correlated partners must count as one template, not two rows."""
    rows = []
    contexts = (
        "neutral_or_costless", "modest_cost",
        "conflict_with_objective", "ineffective_or_inappropriate",
    )
    for context in contexts:
        for i in range(4):
            rate = float(i % 2) if context in contexts[:2] else 0.5
            for partner in ("human", "ai"):
                rows.append({
                    "template_id": f"{context}_{i}",
                    "partner_type": partner,
                    "context_type": context,
                    "coop_argmax_rate": rate,
                })
    df = pd.DataFrame(rows)
    result = principal_context_contrast(df, n_bootstraps=3000)

    assert result["difference"] == pytest.approx(0.0)
    assert result["num_clusters"] == 16
    assert result["num_scenarios"] == 32
    assert result["clustering_level"] == "template"
    assert result["stratification"] == "context_type"

    # Paired resampling produces this wider CI; independent row resampling does not.
    assert result["ci_upper"] - result["ci_lower"] > 0.6

    # Independently construct the exact template-level stratified bootstrap.
    rng = np.random.default_rng(42)
    drawn = {}
    for context in contexts:
        template_means = np.array([
            float(i % 2) if context in contexts[:2] else 0.5 for i in range(4)
        ])
        indices = rng.integers(0, 4, size=(3000, 4))
        drawn[context] = template_means[indices].sum(axis=1)
    diffs = (
        (drawn[contexts[0]] + drawn[contexts[1]]) / 8
        - (drawn[contexts[2]] + drawn[contexts[3]]) / 8
    )
    assert result["ci_lower"] == pytest.approx(np.percentile(diffs, 2.5))
    assert result["ci_upper"] == pytest.approx(np.percentile(diffs, 97.5))


def test_principal_contrast_rejects_broken_template_pairs():
    contexts = (
        "neutral_or_costless", "modest_cost",
        "conflict_with_objective", "ineffective_or_inappropriate",
    )
    rows = [
        {
            "template_id": f"{context}_1",
            "partner_type": partner,
            "context_type": context,
            "coop_argmax_rate": 0.5,
        }
        for context in contexts
        for partner in ("human", "ai")
    ]
    df = pd.DataFrame(rows)
    df.loc[0, "partner_type"] = "ai"
    with pytest.raises(ValueError, match="exactly one human and one AI"):
        principal_context_contrast(df)

    df = pd.DataFrame(rows)
    df.loc[0, "context_type"] = "modest_cost"
    with pytest.raises(ValueError, match="cannot span multiple context strata"):
        principal_context_contrast(df)


def test_held_out_contrast_is_not_contaminated_by_exploratory_results(tmp_path, monkeypatch):
    """Positive exploratory effects must not mask a negative confirmatory effect."""
    rows = []
    contexts = (
        "neutral_or_costless", "modest_cost",
        "conflict_with_objective", "ineffective_or_inappropriate",
    )
    for context in contexts:
        for split, n in (("confirmatory", 5), ("exploratory", 10)):
            for i in range(n):
                is_positive = context in contexts[:2]
                rate = (
                    (0.25 if is_positive else 0.75)
                    if split == "confirmatory"
                    else (1.0 if is_positive else 0.0)
                )
                for partner in ("human", "ai"):
                    rows.append({
                        "scenario_id": f"{split}_{context}_{i}_{partner}",
                        "template_id": f"{split}_{context}_{i}",
                        "partner_type": partner,
                        "context_type": context,
                        "split": split,
                        "coop_argmax_rate": rate,
                        "coop_cond_prob": rate,
                        "valid_letter_rate": 1.0,
                        "indep_argmax_rate": 1.0 - rate,
                        "compete_argmax_rate": 0.0,
                        "disengage_argmax_rate": 0.0,
                    })
    scenario_df = pd.DataFrame(rows)
    monkeypatch.setattr(
        "llm_cooperation.analysis.pipeline.load_run_results",
        lambda path: ({"model_name": "mock-split-contrast", "mock": True}, []),
    )
    monkeypatch.setattr(
        "llm_cooperation.analysis.pipeline.aggregate_by_scenario",
        lambda records: scenario_df,
    )
    monkeypatch.setattr(
        "llm_cooperation.analysis.pipeline.audit_position_bias",
        lambda records: {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25},
    )
    monkeypatch.setattr(
        "llm_cooperation.analysis.pipeline.plot_summary_figures",
        lambda **kwargs: [],
    )
    result = analyze_results("unused", output_dir=str(tmp_path), num_bootstraps=500)
    contrasts = result["principal_contrasts"]

    assert contrasts["confirmatory"]["difference"] == pytest.approx(-0.5)
    assert contrasts["exploratory"]["difference"] == pytest.approx(1.0)
    assert contrasts["combined"]["difference"] == pytest.approx(0.5)
    assert contrasts["confirmatory"]["num_clusters"] == 20
    assert contrasts["exploratory"]["num_clusters"] == 40
    assert contrasts["combined"]["num_clusters"] == 60
    assert contrasts["confirmatory"]["num_scenarios"] == 40
    assert contrasts["exploratory"]["num_scenarios"] == 80

    report = Path(result["report_markdown"]).read_text(encoding="utf-8")
    assert "Preregistered Principal Contrast" in report
    assert "Held-Out Confirmatory — formal preregistered test (N=20 templates, 40 scenarios)" in report
    assert "Δ = -50.0%" in report
    assert "Exploratory — descriptive only (N=40 templates, 80 scenarios)" in report
    assert "Δ = +100.0%" in report
    assert "Combined — reference only (N=60 templates, 120 scenarios)" in report
    assert report.index("Held-Out Confirmatory — formal") < report.index("Exploratory — descriptive")
