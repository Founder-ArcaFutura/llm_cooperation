"""Tests for Phase 0B: Utility-Matched Cooperation Assay.

Validates:
1. Bank schema, template counts (60 templates: 30 reused exploratory, 30 new confirmatory).
2. Paired human and AI design across all 60 templates.
3. Utility condition distribution: equal_utility, coop_advantageous, coop_disadvantageous.
4. Objective payoff specifications and absence of taboo words / destructive markers.
5. Permutation counterbalancing: 480 presentations with exact strategy balance at positions A, B, C, D.
6. Analytical extensions: compute_utility_matched_contrast, log-probability differences, sensitivity triads.
7. Mock runner and end-to-end analysis on Phase 0B bank.
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from llm_cooperation.items.schema import (
    ScenarioBank,
    Scenario,
    PartnerType,
    StrategyType,
    UtilityCondition,
)
from llm_cooperation.items.permutations import generate_all_presentations
from llm_cooperation.items.audit import audit_scenarios
from llm_cooperation.harness.runner import run_experiment
from llm_cooperation.analysis.metrics import (
    aggregate_by_scenario,
    compute_utility_matched_contrast,
    compute_utility_sensitivity_contrast,
    template_cluster_bootstrap,
)
from llm_cooperation.analysis.pipeline import analyze_results


def test_phase0b_bank_schema_and_balance():
    """Verify that data/scenarios_phase0b_utility_matched.json meets all assay specifications."""
    bank_path = "data/scenarios_phase0b_utility_matched.json"
    assert Path(bank_path).exists()

    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bank = ScenarioBank(**data)
    scenarios = bank.scenarios
    assert len(scenarios) == 124
    assert bank.version == "1.0.0-phase0b"
    assert bank.status == "pending_human_scientific_review"

    # Template pairing
    templates = {}
    for s in scenarios:
        assert s.template_id is not None
        assert s.utility_condition is not None
        assert s.source_type in ("reused", "new", "control")
        assert s.split in ("exploratory", "confirmatory")
        assert s.payoff_spec is not None
        # Check payoff spec keys
        for st in [st.value for st in StrategyType]:
            assert st in s.payoff_spec
            assert "actor_expected_utility" in s.payoff_spec[st]
            assert "time" in s.payoff_spec[st]
            assert "cost" in s.payoff_spec[st]
            assert "risk" in s.payoff_spec[st]
            assert "success_prob" in s.payoff_spec[st]
            assert "actor_payoff" in s.payoff_spec[st]
            assert "partner_payoff" in s.payoff_spec[st]

        templates.setdefault(s.template_id, []).append(s)

    assert len(templates) == 62

    reused_count = 0
    new_count = 0
    control_count = 0
    equal_count = 0
    adv_count = 0
    disadv_count = 0
    triad_ids = set()

    for tid, scs in templates.items():
        assert len(scs) == 2
        partners = {sc.partner_type for sc in scs}
        assert partners == {PartnerType.HUMAN, PartnerType.AI}

        splits = {sc.split for sc in scs}
        assert len(splits) == 1
        split_val = list(splits)[0]

        sources = {sc.source_type for sc in scs}
        assert len(sources) == 1
        src_val = list(sources)[0]

        uconds = {sc.utility_condition for sc in scs}
        assert len(uconds) == 1
        ucond_val = list(uconds)[0]

        for sc in scs:
            if sc.triad_id:
                triad_ids.add(sc.triad_id)

        if src_val == "reused":
            reused_count += 1
            assert split_val == "exploratory"
        elif src_val == "control":
            control_count += 1
            assert split_val == "confirmatory"
        else:
            new_count += 1
            assert split_val == "confirmatory"

        if ucond_val == UtilityCondition.EQUAL_UTILITY:
            equal_count += 1
        elif ucond_val == UtilityCondition.COOP_ADVANTAGEOUS:
            adv_count += 1
        elif ucond_val == UtilityCondition.COOP_DISADVANTAGEOUS:
            disadv_count += 1

    assert reused_count == 30
    assert new_count == 30
    assert control_count == 2
    assert equal_count == 54  # 52 regular equal + 2 symmetric control
    assert adv_count == 4      # 2 reused triad + 2 new triad
    assert disadv_count == 4   # 2 reused triad + 2 new triad
    assert len(triad_ids) == 4

    # 4-position counterbalancing
    all_pres = generate_all_presentations(scenarios)
    assert len(all_pres) == 496
    letter_counts = {l: {st: 0 for st in StrategyType} for l in ["A", "B", "C", "D"]}
    for p in all_pres:
        for opt in p.options:
            letter_counts[opt.letter][opt.strategy] += 1

    for l in ["A", "B", "C", "D"]:
        for st in StrategyType:
            assert letter_counts[l][st] == 124


def test_phase0b_audit_cli_api(capsys):
    """Verify programmatic audit function succeeds on Phase 0B bank."""
    assert audit_scenarios("data/scenarios_phase0b_utility_matched.json") is True
    output = capsys.readouterr().out
    assert "exploratory 30 templates (60 scenarios)" in output
    assert "confirmatory 32 new/control templates (64 scenarios" in output
    assert "2 x 4 context-cell balance is not asserted" in output
    assert "option-length spread is 3.14 words" in output
    assert "3.1-word target" in output
    assert "perfectly balanced across 2 partner x 4 context strata" not in output


def test_utility_matched_contrast_calculation():
    """Test compute_utility_matched_contrast and compute_utility_sensitivity_contrast."""
    records = []
    # Test with controlled matched triad templates
    for i in range(1, 11):
        if i == 8:
            tid = "template_025"
            ucond = "coop_advantageous"
            coop_prob, indep_prob = 0.8, 0.1
            coop_argmax, indep_argmax = 1.0, 0.0
        elif i == 9:
            tid = "template_027"
            ucond = "equal_utility"
            coop_prob, indep_prob = 0.5, 0.5
            coop_argmax, indep_argmax = 0.5, 0.5
        elif i == 10:
            tid = "template_029"
            ucond = "coop_disadvantageous"
            coop_prob, indep_prob = 0.2, 0.7
            coop_argmax, indep_argmax = 0.0, 1.0
        else:
            tid = f"template_{i:03d}"
            ucond = "equal_utility"
            coop_prob, indep_prob = 0.6, 0.3
            coop_argmax, indep_argmax = 1.0, 0.0

        for p_type in ["human", "ai"]:
            sc_id = f"sc_{i}_{p_type}"
            records.append({
                "scenario_id": sc_id,
                "template_id": tid,
                "partner_type": p_type,
                "context_type": "neutral_or_costless",
                "utility_condition": ucond,
                "split": "exploratory" if i <= 5 else "confirmatory",
                "source_type": "reused" if i <= 5 else "new",
                "coop_argmax_rate": coop_argmax,
                "indep_argmax_rate": indep_argmax,
                "compete_argmax_rate": 0.0,
                "disengage_argmax_rate": 0.0,
                "coop_cond_prob": coop_prob,
                "indep_cond_prob": indep_prob,
                "log_prob_coop_indep_diff": float(np.log(coop_prob) - np.log(indep_prob)),
            })

    df = pd.DataFrame(records)

    # Add triad_id to df
    for r in records:
        if r["template_id"] in ("template_025", "template_027", "template_029"):
            r["triad_id"] = "triad_01"
        else:
            r["triad_id"] = None
        r["is_symmetric_control"] = False

    df = pd.DataFrame(records)

    contrast = compute_utility_matched_contrast(df, n_bootstraps=500)
    assert contrast is not None
    assert contrast["choice_diff_mean"] > 0
    assert contrast["log_prob_diff_mean"] > 0

    sensitivity = compute_utility_sensitivity_contrast(df)
    assert sensitivity is not None
    assert sensitivity["coop_advantageous_mean"] == 1.0
    # Paired within-triad baseline is 0.5
    assert sensitivity["coop_equal_mean"] == 0.5
    assert sensitivity["coop_disadvantageous_mean"] == 0.0
    assert sensitivity["adv_vs_disadv_spread"] == 1.0
    assert sensitivity["monotonic_ordering"] is True


def test_symmetric_controls_cannot_change_primary_estimate():
    """Regression test: symmetric control items (is_symmetric_control=True) are excluded

    from the primary equal-utility contrast and cannot change the primary estimate.
    """
    base_records = [
        {
            "template_id": "template_001",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": False,
            "coop_argmax_rate": 0.8,
            "indep_argmax_rate": 0.1,
            "log_prob_coop_indep_diff": 0.6,
        },
        {
            "template_id": "template_001",
            "partner_type": "ai",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": False,
            "coop_argmax_rate": 0.8,
            "indep_argmax_rate": 0.1,
            "log_prob_coop_indep_diff": 0.6,
        },
        {
            "template_id": "template_002",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": False,
            "coop_argmax_rate": 0.5,
            "indep_argmax_rate": 0.3,
            "log_prob_coop_indep_diff": 0.2,
        },
        {
            "template_id": "template_002",
            "partner_type": "ai",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": False,
            "coop_argmax_rate": 0.5,
            "indep_argmax_rate": 0.3,
            "log_prob_coop_indep_diff": 0.2,
        },
    ]

    control_records = [
        {
            "template_id": "template_061",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": True,
            "coop_argmax_rate": 0.05,
            "indep_argmax_rate": 0.95,
            "log_prob_coop_indep_diff": -2.5,
        },
        {
            "template_id": "template_061",
            "partner_type": "ai",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": True,
            "coop_argmax_rate": 0.05,
            "indep_argmax_rate": 0.95,
            "log_prob_coop_indep_diff": -2.5,
        },
        {
            "template_id": "template_062",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": True,
            "coop_argmax_rate": 0.1,
            "indep_argmax_rate": 0.9,
            "log_prob_coop_indep_diff": -2.0,
        },
        {
            "template_id": "template_062",
            "partner_type": "ai",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "is_symmetric_control": True,
            "coop_argmax_rate": 0.1,
            "indep_argmax_rate": 0.9,
            "log_prob_coop_indep_diff": -2.0,
        },
    ]

    df_without_controls = pd.DataFrame(base_records)
    df_with_controls = pd.DataFrame(base_records + control_records)

    contrast_without = compute_utility_matched_contrast(df_without_controls, seed=123, n_bootstraps=500)
    contrast_with = compute_utility_matched_contrast(df_with_controls, seed=123, n_bootstraps=500)

    assert contrast_without is not None
    assert contrast_with is not None
    assert contrast_without["choice_diff_mean"] == pytest.approx(contrast_with["choice_diff_mean"])
    assert contrast_without["log_prob_diff_mean"] == pytest.approx(contrast_with["log_prob_diff_mean"])
    assert contrast_without["coop_rate_mean"] == pytest.approx(contrast_with["coop_rate_mean"])
    assert contrast_without["indep_rate_mean"] == pytest.approx(contrast_with["indep_rate_mean"])
    assert contrast_without["num_templates"] == contrast_with["num_templates"] == 2


def test_phase0b_mock_end_to_end_analysis(tmp_path):
    """Verify end-to-end mock execution and analysis on Phase 0B bank."""
    out_dir = tmp_path / "results"
    report_dir = tmp_path / "reports"

    run_file = run_experiment(
        model_name="mock-qwen-phase0b",
        scenarios_path="data/scenarios_phase0b_utility_matched.json",
        output_dir=str(out_dir),
        mock=True,
        seed=42,
    )
    assert run_file.exists()

    report_dict = analyze_results(
        results_path=str(run_file),
        output_dir=str(report_dir),
        num_bootstraps=500,
    )

    report_file = Path(report_dict["report_markdown"])
    assert report_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "Phase 0B: Utility-Matched Construct Validation Contrasts" in md_text
    # Separate confirmatory and exploratory contrasts
    assert "Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition" in md_text
    assert "FORMAL REPLICATION TEST" in md_text
    assert "Exploratory Utility-Matched Contrast (Rewritten Existing Templates" in md_text
    assert "Controlled Utility Sensitivity Triad" in md_text
    assert "Within-Triad Baseline" in md_text
    assert "Symmetric Outcome Control Subset" in md_text
    assert "Source Type Breakdown (Reused vs New Templates)" in md_text
