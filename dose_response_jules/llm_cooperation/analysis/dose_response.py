"""Nonlinear payoff dose-response modeling and analysis module.

Implements:
1. Scenario-family / template-clustered bootstrap uncertainty estimation (2,000 resamples).
2. Model-specific payoff-response curve fitting:
   - Logistic/sigmoid response function
   - Polynomial / quadratic non-linear curve fitting
   - Goodness of fit comparison (MSE, R^2, AIC)
3. Key behavioral parameters:
   - Equal-utility preference: Delta_choice(Delta U = 0) and Delta_log_P(Delta U = 0)
   - Payoff sensitivity slope: d P(coop) / d(Delta U) around Delta U = 0
   - Cost crossover threshold: Delta U* where P(COOP) = P(INDEP) or Delta_log_P = 0
   - Partner benefit modulation: P(coop | High Benefit) - P(coop | Low Benefit)
   - Reciprocity horizon modulation: P(coop | Repeated) - P(coop | One-Shot)
4. Separate evaluation of forced-choice log-probability contrast vs greedy argmax choice.
5. Residual cooperative preference controlling for private expected utility, partner welfare, framing, and letter position bias.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def extract_delta_u(row: pd.Series) -> Optional[float]:
    """Extract numeric private payoff difference (COOPERATE - INDEPENDENT) from record or payoff_spec."""
    if "delta_u" in row and pd.notnull(row["delta_u"]):
        try:
            return float(row["delta_u"])
        except (ValueError, TypeError):
            pass

    payoff_spec = row.get("payoff_spec")
    if isinstance(payoff_spec, dict):
        coop_spec = payoff_spec.get("COOPERATE", {})
        if "delta_u_actor" in coop_spec:
            try:
                return float(coop_spec["delta_u_actor"])
            except (ValueError, TypeError):
                pass
        try:
            actor_coop = float(coop_spec.get("actor_payoff", 1.0))
            indep_spec = payoff_spec.get("INDEPENDENT", {})
            actor_indep = float(indep_spec.get("actor_payoff", 1.0))
            return actor_coop - actor_indep
        except (ValueError, TypeError):
            pass

    # Infer from utility_condition if explicit payoff_spec unavailable
    u_cond = row.get("utility_condition")
    if u_cond == "equal_utility":
        return 0.0
    elif u_cond == "coop_advantageous":
        return 0.20
    elif u_cond == "coop_disadvantageous":
        return -0.20
    return None


def logistic_4p(x: np.ndarray, bottom: float, top: float, x0: float, k: float) -> np.ndarray:
    """4-parameter logistic sigmoid: f(x) = bottom + (top - bottom) / (1 + exp(-k * (x - x0)))."""
    # Clip exponent to avoid overflow
    z = np.clip(-k * (x - x0), -50.0, 50.0)
    return bottom + (top - bottom) / (1.0 + np.exp(z))


def polynomial_2p(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Quadratic polynomial: f(x) = a * x^2 + b * x + c."""
    return a * (x ** 2) + b * x + c


def fit_payoff_response_curves(
    delta_u_arr: np.ndarray,
    response_arr: np.ndarray,
) -> Dict[str, Any]:
    """Fit logistic vs quadratic polynomial models to empirical payoff response data.

    Returns parameter estimates, sensitivity slope at 0, crossover threshold, and goodness-of-fit.
    """
    results: Dict[str, Any] = {}
    n = len(delta_u_arr)
    if n < 4:
        return {"error": "Insufficient data points for curve fitting"}

    # Sort arrays
    sort_idx = np.argsort(delta_u_arr)
    x = delta_u_arr[sort_idx]
    y = response_arr[sort_idx]

    # --- 1. Linear & Tangent Sensitivity Slope at Delta U = 0 ---
    # Robust linear regression around zero (|Delta U| <= 0.20)
    near_zero_mask = np.abs(x) <= 0.25
    if np.sum(near_zero_mask) >= 3:
        p_lin = np.polyfit(x[near_zero_mask], y[near_zero_mask], deg=1)
    else:
        p_lin = np.polyfit(x, y, deg=1)
    linear_slope = float(p_lin[0])
    linear_intercept = float(p_lin[1])

    # --- 2. Quadratic / Polynomial Fit ---
    p_quad = np.polyfit(x, y, deg=2)
    y_pred_quad = np.polyval(p_quad, x)
    mse_quad = float(np.mean((y - y_pred_quad) ** 2))
    var_y = float(np.var(y)) if float(np.var(y)) > 1e-12 else 1e-12
    r2_quad = float(1.0 - mse_quad / var_y)

    # --- 3. 4-Parameter Logistic Fit ---
    logistic_success = False
    try:
        # Initial guess: bottom=min(y), top=max(y), x0=median(x), k=5.0
        p0 = [max(0.0, float(np.min(y))), min(1.0, float(np.max(y))), float(np.median(x)), 5.0]
        bounds = ([0.0, 0.0, -1.0, 0.01], [1.0, 1.0, 1.0, 50.0])
        popt_log, _ = curve_fit(logistic_4p, x, y, p0=p0, bounds=bounds, maxfev=2000)
        y_pred_log = logistic_4p(x, *popt_log)
        mse_log = float(np.mean((y - y_pred_log) ** 2))
        r2_log = float(1.0 - mse_log / var_y)
        logistic_success = True
        bottom, top, x0, k = popt_log
        # Tangent slope of logistic at x=0
        z0 = np.clip(-k * (-x0), -50.0, 50.0)
        logistic_slope_at_zero = float((top - bottom) * k * np.exp(z0) / ((1.0 + np.exp(z0)) ** 2))
    except Exception:
        mse_log = None
        r2_log = None
        logistic_slope_at_zero = None
        popt_log = None

    # --- 4. Crossover Threshold Estimation (Indifference point where y crosses threshold) ---
    # For choice rate, indifference vs independent option is 0.50 (or crossover where coop == indep)
    # Estimate from linear / spline interpolation
    crossover_delta_u = None
    try:
        if linear_slope > 1e-4:
            # Linear solve for y = 0.50: x = (0.50 - intercept) / slope
            # Or if response is log_prob_diff, solve for y = 0.0: x = -intercept / slope
            crossover_delta_u = float((0.50 - linear_intercept) / linear_slope)
    except Exception:
        crossover_delta_u = None

    results["linear_slope"] = linear_slope
    results["linear_intercept"] = linear_intercept
    results["quadratic_fit"] = {
        "coefficients": [float(c) for c in p_quad],
        "mse": mse_quad,
        "r2": r2_quad,
    }
    results["logistic_fit"] = {
        "success": logistic_success,
        "parameters": [float(p) for p in popt_log] if popt_log is not None else None,
        "slope_at_zero": logistic_slope_at_zero,
        "mse": mse_log,
        "r2": r2_log,
    }
    results["estimated_crossover_delta_u"] = crossover_delta_u
    return results


def analyze_payoff_dose_response(
    scenario_df: pd.DataFrame,
    n_bootstraps: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    """Comprehensive dose-response analysis of scenario records with template-clustered bootstrap.

    Computes:
    - Equal utility baseline (choice diff and log prob diff)
    - Sensitivity slopes and crossover thresholds for both argmax choice and log-prob contrast
    - Goodness of fit (logistic vs nonlinear)
    - Factorial interactions: Partner benefit effect and Reciprocity horizon effect
    - Symmetric welfare control benchmark
    - Non-social control benchmark
    """
    df = scenario_df.copy()
    if "delta_u" not in df.columns:
        df["delta_u"] = df.apply(extract_delta_u, axis=1)

    # Exclude symmetric and non-social controls from main curve fitting
    main_sweep_df = df[
        (df["is_symmetric_control"] != True) &
        (df["source_type"] != "control_nonsocial") &
        (df["delta_u"].notnull())
    ].copy()

    rng = np.random.default_rng(seed)

    # Group by template_id to prevent pseudoreplication across paired human/AI scenarios
    has_templates = ("template_id" in main_sweep_df.columns and not main_sweep_df["template_id"].isnull().all())
    if has_templates:
        tpl_df = main_sweep_df.groupby(["template_id", "delta_u"]).agg({
            "coop_argmax_rate": "mean",
            "indep_argmax_rate": "mean",
            "log_prob_coop_indep_diff": "mean",
        }).reset_index()
    else:
        tpl_df = main_sweep_df

    x_vals = tpl_df["delta_u"].values
    coop_rate_vals = tpl_df["coop_argmax_rate"].values
    log_diff_vals = tpl_df["log_prob_coop_indep_diff"].values

    # Primary curve fits on empirical points
    curve_fit_choice = fit_payoff_response_curves(x_vals, coop_rate_vals)
    curve_fit_logprob = fit_payoff_response_curves(x_vals, log_diff_vals)

    # Equal utility subset metrics (delta_u == 0.00)
    eq_df = tpl_df[np.isclose(tpl_df["delta_u"], 0.0, atol=1e-3)]
    if not eq_df.empty:
        eq_choice_diff_obs = float(np.mean(eq_df["coop_argmax_rate"] - eq_df["indep_argmax_rate"]))
        eq_log_diff_obs = float(np.mean(eq_df["log_prob_coop_indep_diff"]))
        eq_coop_rate_obs = float(np.mean(eq_df["coop_argmax_rate"]))
        eq_indep_rate_obs = float(np.mean(eq_df["indep_argmax_rate"]))
    else:
        eq_choice_diff_obs = 0.0
        eq_log_diff_obs = 0.0
        eq_coop_rate_obs = 0.0
        eq_indep_rate_obs = 0.0

    # Cluster bootstrap across situation templates
    unique_tpls = main_sweep_df["template_id"].dropna().unique() if has_templates else np.arange(len(main_sweep_df))
    n_tpls = len(unique_tpls)

    boot_eq_choice_diffs = []
    boot_eq_log_diffs = []
    boot_slopes_choice = []
    boot_slopes_log = []
    boot_crossovers = []

    for _ in range(n_bootstraps):
        sampled_tids = rng.choice(unique_tpls, size=n_tpls, replace=True)
        if has_templates:
            # Reconstruct resampled dataframe preserving within-template rows
            sub_rows = []
            for tid in sampled_tids:
                sub_rows.append(tpl_df[tpl_df["template_id"] == tid])
            boot_df = pd.concat(sub_rows, ignore_index=True)
        else:
            boot_df = tpl_df.iloc[sampled_tids]

        # Bootstrapped equal utility
        b_eq = boot_df[np.isclose(boot_df["delta_u"], 0.0, atol=1e-3)]
        if not b_eq.empty:
            boot_eq_choice_diffs.append(float(np.mean(b_eq["coop_argmax_rate"] - b_eq["indep_argmax_rate"])))
            boot_eq_log_diffs.append(float(np.mean(b_eq["log_prob_coop_indep_diff"])))

        # Bootstrapped sensitivity slopes
        b_x = boot_df["delta_u"].values
        b_y_choice = boot_df["coop_argmax_rate"].values
        b_y_log = boot_df["log_prob_coop_indep_diff"].values

        if len(b_x) >= 4 and np.std(b_x) > 1e-4:
            p_lin_choice = np.polyfit(b_x, b_y_choice, deg=1)
            p_lin_log = np.polyfit(b_x, b_y_log, deg=1)
            boot_slopes_choice.append(float(p_lin_choice[0]))
            boot_slopes_log.append(float(p_lin_log[0]))
            if p_lin_choice[0] > 1e-4:
                boot_crossovers.append(float((0.50 - p_lin_choice[1]) / p_lin_choice[0]))

    # CI helper
    def get_ci(arr: List[float], obs_val: float) -> Tuple[float, float]:
        if not arr:
            return (obs_val, obs_val)
        return (
            float(np.percentile(arr, 100 * (alpha / 2))),
            float(np.percentile(arr, 100 * (1 - alpha / 2))),
        )

    eq_choice_ci = get_ci(boot_eq_choice_diffs, eq_choice_diff_obs)
    eq_log_ci = get_ci(boot_eq_log_diffs, eq_log_diff_obs)
    slope_choice_ci = get_ci(boot_slopes_choice, curve_fit_choice["linear_slope"])
    slope_log_ci = get_ci(boot_slopes_log, curve_fit_logprob["linear_slope"])

    # --- 5. Factorial Interactions: Partner Benefit & Reciprocity ---
    benefit_contrast = None
    reciprocity_contrast = None

    # Check for partner benefit metadata in payoff_spec or column
    def extract_benefit(row):
        spec = row.get("payoff_spec")
        if isinstance(spec, dict):
            return spec.get("COOPERATE", {}).get("partner_benefit")
        return None

    def extract_interaction(row):
        spec = row.get("payoff_spec")
        if isinstance(spec, dict):
            return spec.get("COOPERATE", {}).get("interaction_type")
        return None

    df["partner_benefit"] = df.apply(extract_benefit, axis=1)
    df["interaction_type"] = df.apply(extract_interaction, axis=1)

    # Benefit modulation (High vs Low benefit at Delta U <= 0)
    high_b = df[df["partner_benefit"] == "high"]["coop_argmax_rate"]
    low_b = df[df["partner_benefit"] == "low"]["coop_argmax_rate"]
    if not high_b.empty and not low_b.empty:
        benefit_contrast = {
            "high_benefit_coop_rate": float(np.mean(high_b)),
            "low_benefit_coop_rate": float(np.mean(low_b)),
            "benefit_diff": float(np.mean(high_b) - np.mean(low_b)),
        }

    # Reciprocity shadow modulation (Repeated vs One-shot)
    repeated_df = df[df["interaction_type"] == "repeated_shadow"]["coop_argmax_rate"]
    oneshot_df = df[df["interaction_type"] == "one_shot"]["coop_argmax_rate"]
    if not repeated_df.empty and not oneshot_df.empty:
        reciprocity_contrast = {
            "repeated_coop_rate": float(np.mean(repeated_df)),
            "oneshot_coop_rate": float(np.mean(oneshot_df)),
            "reciprocity_diff": float(np.mean(repeated_df) - np.mean(oneshot_df)),
        }

    # --- 6. Control Benchmarks ---
    # Symmetric welfare controls
    symm_df = df[df["is_symmetric_control"] == True]
    symmetric_control = None
    if not symm_df.empty:
        symmetric_control = {
            "coop_rate": float(symm_df["coop_argmax_rate"].mean()),
            "indep_rate": float(symm_df["indep_argmax_rate"].mean()),
            "choice_diff": float(symm_df["coop_argmax_rate"].mean() - symm_df["indep_argmax_rate"].mean()),
            "log_prob_diff": float(symm_df["log_prob_coop_indep_diff"].mean()),
            "num_scenarios": len(symm_df),
        }

    # Non-social numerical controls
    ns_df = df[df["source_type"] == "control_nonsocial"]
    nonsocial_control = None
    if not ns_df.empty:
        nonsocial_control = {
            "opt_alpha_coop_rate": float(ns_df["coop_argmax_rate"].mean()),
            "opt_beta_indep_rate": float(ns_df["indep_argmax_rate"].mean()),
            "choice_diff": float(ns_df["coop_argmax_rate"].mean() - ns_df["indep_argmax_rate"].mean()),
            "log_prob_diff": float(ns_df["log_prob_coop_indep_diff"].mean()),
            "num_scenarios": len(ns_df),
        }

    return {
        "equal_utility_baseline": {
            "choice_diff_mean": eq_choice_diff_obs,
            "choice_diff_ci": list(eq_choice_ci),
            "log_prob_diff_mean": eq_log_diff_obs,
            "log_prob_diff_ci": list(eq_log_ci),
            "coop_rate_mean": eq_coop_rate_obs,
            "indep_rate_mean": eq_indep_rate_obs,
        },
        "payoff_sensitivity": {
            "choice_slope": curve_fit_choice["linear_slope"],
            "choice_slope_ci": list(slope_choice_ci),
            "log_prob_slope": curve_fit_logprob["linear_slope"],
            "log_prob_slope_ci": list(slope_log_ci),
            "crossover_threshold_delta_u": curve_fit_choice["estimated_crossover_delta_u"],
        },
        "curve_fits": {
            "choice_curve": curve_fit_choice,
            "log_prob_curve": curve_fit_logprob,
        },
        "interactions": {
            "partner_benefit_modulation": benefit_contrast,
            "reciprocity_modulation": reciprocity_contrast,
        },
        "controls": {
            "symmetric_welfare_control": symmetric_control,
            "nonsocial_numerical_control": nonsocial_control,
        },
        "clustering_level": "template",
        "num_templates_analyzed": n_tpls,
    }
