"""Automated report generation and pipeline orchestration for Phase 0."""

import os
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from rich.console import Console
from rich.table import Table

from llm_cooperation.analysis.metrics import (
    load_run_results,
    aggregate_by_scenario,
    scenario_cluster_bootstrap,
    audit_position_bias,
)
from llm_cooperation.analysis.plots import plot_summary_figures


def generate_markdown_report(
    metadata: Dict,
    scenario_df: pd.DataFrame,
    overall_boot: Dict[str, float],
    prob_boot: Dict[str, float],
    pos_bias: Dict[str, float],
    output_path: str,
) -> str:
    model_name = metadata.get("model_name", "Unknown")
    num_scenarios = len(scenario_df)
    valid_rate = scenario_df["valid_letter_rate"].mean()

    # Breakdown by context
    ctx_summary = scenario_df.groupby("context_type").agg(
        mean_argmax=("coop_argmax_rate", "mean"),
        mean_prob=("coop_cond_prob", "mean"),
    ).to_markdown()

    # Breakdown by partner
    partner_summary = scenario_df.groupby("partner_type").agg(
        mean_argmax=("coop_argmax_rate", "mean"),
        mean_prob=("coop_cond_prob", "mean"),
    ).to_markdown()

    # Strategy distribution
    strat_dist = {
        "Cooperate": scenario_df["coop_argmax_rate"].mean(),
        "Independent": scenario_df["indep_argmax_rate"].mean(),
        "Compete / Exploit": scenario_df["compete_argmax_rate"].mean(),
        "Disengage": scenario_df["disengage_argmax_rate"].mean(),
    }
    preferred_noncoop = max(
        [(k, v) for k, v in strat_dist.items() if k != "Cooperate"],
        key=lambda x: x[1]
    )[0]

    # Gate decision assessment per §4A.4
    coop_rate = overall_boot["mean"]
    max_pos = max(pos_bias.values())
    min_pos = min(pos_bias.values())
    pos_spread = max_pos - min_pos

    if valid_rate < 0.50:
        gate_status = "**STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed."
    elif pos_spread > 0.40:
        gate_status = f"**REVISE**: Extreme position sensitivity detected (spread: {pos_spread:.1%}). Order artifact dominates signal."
    elif coop_rate > 0.35 and pos_spread <= 0.25:
        gate_status = "**ADVANCE TO CONDITIONAL REVIEW**: Cooperative preference visible and position-robust across strata."
    else:
        gate_status = "**STOP OR INVESTIGATE CONTEXT**: Mixed or neutral outcome without robust overall cooperation preference."

    md = f"""# Phase 0 Behavioral Screen Report
**Model:** `{model_name}`
**Date:** {metadata.get('timestamp', 'N/A')}
**Git Commit:** `{metadata.get('git_commit', 'N/A')}`
**Scenarios Evaluated (N):** {num_scenarios} (96 total counterbalanced presentations)

---

## 1. Executive Summary & Gate Decision
- **Gate Recommendation (§4A.4):** {gate_status}
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** {overall_boot['mean']:.1%} [95% CI: {overall_boot['ci_lower']:.1%} – {overall_boot['ci_upper']:.1%}]
- **Overall Mean Conditional Cooperative Probability:** {prob_boot['mean']:.3f} [95% CI: {prob_boot['ci_lower']:.3f} – {prob_boot['ci_upper']:.3f}]
- **Letter Validity Rate:** {valid_rate:.1%}
- **Preferred Non-Cooperative Alternative:** `{preferred_noncoop}` ({strat_dist[preferred_noncoop]:.1%})

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
{ctx_summary}

### Partner Type Breakdown (Human vs AI)
{partner_summary}

---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** {pos_bias.get('A', 0.0):.1%}
- **B:** {pos_bias.get('B', 0.0):.1%}
- **C:** {pos_bias.get('C', 0.0):.1%}
- **D:** {pos_bias.get('D', 0.0):.1%}
- **Positional Spread (Max - Min):** {pos_spread:.1%}

---

## 4. Alternative Strategies Distribution
- **Cooperate:** {strat_dist['Cooperate']:.1%}
- **Independent:** {strat_dist['Independent']:.1%}
- **Compete / Exploit:** {strat_dist['Compete / Exploit']:.1%}
- **Disengage:** {strat_dist['Disengage']:.1%}

---

## 5. Claim Boundary Compliance (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return md


def analyze_results(
    results_path: str,
    output_dir: str = "reports",
    num_bootstraps: int = 2000,
) -> Dict:
    console = Console()
    os.makedirs(output_dir, exist_ok=True)
    figures_dir = os.path.join(output_dir, "figures")

    metadata, records = load_run_results(results_path)
    model_name = metadata.get("model_name", "unknown_model")
    console.print(f"[bold green]Loaded {len(records)} presentations from {results_path} for {model_name}.[/bold green]")

    # 1. Aggregate to scenario level (N=24)
    scenario_df = aggregate_by_scenario(records)

    # 2. Scenario-level clustered bootstrapping
    overall_boot = scenario_cluster_bootstrap(
        scenario_df,
        metric_col="coop_argmax_rate",
        n_bootstraps=num_bootstraps,
    )
    prob_boot = scenario_cluster_bootstrap(
        scenario_df,
        metric_col="coop_cond_prob",
        n_bootstraps=num_bootstraps,
    )

    # 3. Position bias audit
    pos_bias = audit_position_bias(records)

    # 4. Save aggregated CSV
    csv_path = os.path.join(output_dir, f"scenario_aggregates_{model_name.replace('/', '_')}.csv")
    scenario_df.to_csv(csv_path, index=False)
    console.print(f"[green]Saved scenario-level aggregates to {csv_path}[/green]")

    # 5. Generate plots
    plot_files = plot_summary_figures(
        scenario_df=scenario_df,
        position_bias=pos_bias,
        model_name=model_name,
        output_dir=figures_dir,
    )
    console.print(f"[green]Generated {len(plot_files)} figures in {figures_dir}[/green]")

    # 6. Generate Markdown report
    report_path = os.path.join(output_dir, f"phase0_report_{model_name.replace('/', '_')}.md")
    generate_markdown_report(
        metadata=metadata,
        scenario_df=scenario_df,
        overall_boot=overall_boot,
        prob_boot=prob_boot,
        pos_bias=pos_bias,
        output_path=report_path,
    )
    console.print(f"[bold cyan]Generated executive report at {report_path}[/bold cyan]")

    return {
        "metadata": metadata,
        "overall_boot": overall_boot,
        "prob_boot": prob_boot,
        "position_bias": pos_bias,
        "scenario_csv": csv_path,
        "report_markdown": report_path,
        "plots": plot_files,
    }
