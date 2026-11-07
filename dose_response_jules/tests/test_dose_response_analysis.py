"""Unit tests for the Nonlinear Payoff Dose-Response modeling module."""

import numpy as np
import pandas as pd
import pytest

from llm_cooperation.analysis.dose_response import (
    logistic_4p,
    polynomial_2p,
    fit_payoff_response_curves,
    analyze_payoff_dose_response,
)


def test_logistic_and_polynomial_functions():
    x = np.linspace(-1.0, 1.0, 11)
    y_log = logistic_4p(x, bottom=0.1, top=0.9, x0=0.0, k=5.0)
    assert len(y_log) == 11
    assert y_log[0] < y_log[-1]
    assert np.isclose(y_log[5], 0.5, atol=0.01)

    y_poly = polynomial_2p(x, a=-0.2, b=0.5, c=0.4)
    assert len(y_poly) == 11
    assert np.isclose(y_poly[5], 0.4, atol=1e-5)


def test_fit_payoff_response_curves_monotonic():
    # Synthetic sigmoid response: high coop at delta_u = +0.2, low coop at delta_u = -0.5
    delta_u = np.array([-0.50, -0.30, -0.20, -0.10, -0.05, 0.00, 0.10, 0.20])
    response = logistic_4p(delta_u, bottom=0.10, top=0.90, x0=-0.08, k=6.0)

    fits = fit_payoff_response_curves(delta_u, response)
    assert "linear_slope" in fits
    assert fits["linear_slope"] > 0
    assert fits["quadratic_fit"]["r2"] > 0.90
    assert fits["logistic_fit"]["success"] is True
    assert fits["logistic_fit"]["r2"] > 0.95
    # Crossover near -0.08
    assert fits["estimated_crossover_delta_u"] is not None
    assert fits["estimated_crossover_delta_u"] < 0.05


def test_analyze_payoff_dose_response_synthetic_dataset():
    records = []
    templates = [f"dose_tpl_{i:03d}" for i in range(1, 7)]
    sweep_tiers = [
        ("advantageous", 0.20, 0.85, 0.80),
        ("equal_utility", 0.00, 0.65, 0.40),
        ("small_disadvantage_near_zero", -0.05, 0.58, 0.20),
        ("small_disadvantage", -0.10, 0.48, -0.10),
        ("moderate_disadvantage", -0.20, 0.35, -0.50),
        ("substantial_disadvantage", -0.50, 0.15, -1.20),
    ]

    for tpl in templates:
        for tier_name, du, c_rate, log_diff in sweep_tiers:
            for p_type in ["human", "ai"]:
                records.append({
                    "scenario_id": f"sc_{tpl}_{tier_name}_{p_type}",
                    "template_id": f"{tpl}_{tier_name}",
                    "template_family_id": tpl,
                    "partner_type": p_type,
                    "delta_u": du,
                    "coop_argmax_rate": c_rate + (0.02 if p_type == "human" else -0.02),
                    "indep_argmax_rate": (1.0 - c_rate),
                    "log_prob_coop_indep_diff": log_diff,
                    "is_symmetric_control": False,
                    "source_type": "exploratory_sweep",
                    "payoff_spec": {
                        "COOPERATE": {"partner_benefit": "high", "interaction_type": "one_shot"}
                    }
                })

    # Add 2 symmetric controls and 2 non-social controls
    for p_type in ["human", "ai"]:
        records.append({
            "scenario_id": f"sc_symm_{p_type}",
            "template_id": "symm_ctrl_01",
            "partner_type": p_type,
            "delta_u": 0.00,
            "coop_argmax_rate": 0.60,
            "indep_argmax_rate": 0.35,
            "log_prob_coop_indep_diff": 0.30,
            "is_symmetric_control": True,
            "source_type": "control_symmetric",
            "payoff_spec": {"COOPERATE": {"partner_benefit": "none"}}
        })
        records.append({
            "scenario_id": f"sc_nonsocial_{p_type}",
            "template_id": "nonsocial_ctrl_01",
            "partner_type": p_type,
            "delta_u": 0.00,
            "coop_argmax_rate": 0.30,
            "indep_argmax_rate": 0.65,
            "log_prob_coop_indep_diff": -0.60,
            "is_symmetric_control": False,
            "source_type": "control_nonsocial",
            "payoff_spec": {"COOPERATE": {"partner_benefit": "none"}}
        })

    df = pd.DataFrame(records)
    analysis = analyze_payoff_dose_response(df, n_bootstraps=200, seed=42)

    assert analysis is not None
    assert analysis["num_templates_analyzed"] == len(templates)
    # Check equal utility preference
    eq = analysis["equal_utility_baseline"]
    assert eq["choice_diff_mean"] > 0
    assert eq["log_prob_diff_mean"] > 0
    assert eq["choice_diff_ci"][0] > 0

    # Check sensitivity slope
    slope = analysis["payoff_sensitivity"]
    assert slope["choice_slope"] > 0
    assert slope["log_prob_slope"] > 0
    assert slope["choice_slope_ci"][0] > 0

    # Check controls
    controls = analysis["controls"]
    assert controls["symmetric_welfare_control"] is not None
    assert controls["symmetric_welfare_control"]["coop_rate"] == 0.60
    assert controls["nonsocial_numerical_control"] is not None
    assert controls["nonsocial_numerical_control"]["opt_alpha_coop_rate"] == 0.30


def test_crossover_is_cooperate_vs_independent_not_all_four_choices():
    rows = []
    doses = [-0.60, -0.50, -0.30, -0.20, -0.10, -0.05, 0.00, 0.20]
    for family in [f"family_{i}" for i in range(6)]:
        for du in doses:
            coop = 0.30 + du * 0.20
            indep = 0.30 - du * 0.20
            rows.append({
                "scenario_id": f"{family}_{du}",
                "template_id": f"{family}_{du}",
                "template_family_id": family,
                "delta_u": du,
                "coop_argmax_rate": coop,
                "indep_argmax_rate": indep,
                "log_prob_coop_indep_diff": np.log(coop / indep),
                "source_type": "exploratory_sweep",
                "is_symmetric_control": False,
                "partner_benefit": "high",
                "interaction_type": "one_shot",
            })
    result = analyze_payoff_dose_response(pd.DataFrame(rows), n_bootstraps=20)
    # P(COOPERATE) never approaches 0.50 because COMPETE/DISENGAGE carry the remaining share.
    # COOPERATE and INDEPENDENT are equal at delta U = 0.
    assert result["payoff_sensitivity"]["crossover_threshold_delta_u"] == pytest.approx(0.0, abs=1e-8)
    assert result["payoff_sensitivity"]["log_prob_crossover_threshold_delta_u"] == pytest.approx(0.0, abs=1e-3)


def test_dose_response_specific_bank_audit_passes():
    from llm_cooperation.items.dose_response_bank import audit_dose_response_bank
    assert audit_dose_response_bank("data/scenarios_dose_response_exploratory.json") is True


def test_undefined_pair_shares_are_excluded_without_poisoning_fits():
    rows = []
    for family in ["family_a", "family_b"]:
        for du in [-0.60, -0.50, -0.30, -0.20, -0.10, -0.05, 0.0, 0.20]:
            missing = du == -0.20
            coop = 0.0 if missing else 0.35 + 0.20 * du
            indep = 0.0 if missing else 0.35 - 0.20 * du
            rows.append({
                "scenario_id": f"{family}_{du}",
                "template_id": f"{family}_{du}",
                "template_family_id": family,
                "delta_u": du,
                "coop_argmax_rate": coop,
                "indep_argmax_rate": indep,
                "log_prob_coop_indep_diff": 2.0 * du,
                "is_symmetric_control": False,
                "source_type": "exploratory_sweep",
                "partner_benefit": "high",
                "interaction_type": "one_shot",
            })
    result = analyze_payoff_dose_response(pd.DataFrame(rows), n_bootstraps=30)
    assert np.isfinite(result["payoff_sensitivity"]["choice_slope"])
    assert np.isfinite(result["payoff_sensitivity"]["log_prob_slope"])
    assert result["curve_fits"]["choice_curve"]["num_excluded_nonfinite"] == 2
    assert all(np.isfinite(v) for v in result["payoff_sensitivity"]["choice_slope_ci"])


def test_all_pair_shares_undefined_report_not_estimable():
    rows = []
    for family in ["family_a", "family_b"]:
        for du in [-0.60, -0.50, -0.30, -0.20, -0.10, -0.05, 0.0, 0.20]:
            rows.append({
                "scenario_id": f"{family}_{du}",
                "template_id": f"{family}_{du}",
                "template_family_id": family,
                "delta_u": du,
                "coop_argmax_rate": 0.0,
                "indep_argmax_rate": 0.0,
                "log_prob_coop_indep_diff": 2.0 * du,
                "is_symmetric_control": False,
                "source_type": "exploratory_sweep",
                "partner_benefit": "high",
                "interaction_type": "one_shot",
            })
    result = analyze_payoff_dose_response(pd.DataFrame(rows), n_bootstraps=30)
    fit = result["curve_fits"]["choice_curve"]
    assert fit["num_valid"] == 0
    # Two families each contribute eight dose cells with undefined pair shares.
    assert fit["num_excluded_nonfinite"] == 16
    assert "Not estimable" in fit["error"]
    assert result["payoff_sensitivity"]["choice_slope"] is None
    assert result["payoff_sensitivity"]["choice_slope_ci"] == [None, None]
    assert result["payoff_sensitivity"]["crossover_threshold_delta_u"] is None
    assert result["payoff_sensitivity"]["crossover_threshold_ci"] == [None, None]
    assert result["payoff_sensitivity"]["log_prob_slope"] > 0
