"""Plotting routines for Phase 0 cooperation screen analysis."""

import os
from pathlib import Path
from typing import Dict, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_summary_figures(
    scenario_df: pd.DataFrame,
    position_bias: Dict[str, float],
    model_name: str,
    output_dir: str = "reports/figures",
    run_id: Optional[str] = None,
) -> List[str]:
    """Generate publication-ready figures for Phase 0 analysis.

    Uses model slug and optional run_id in filenames to prevent overwrites.
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []

    model_slug = model_name.replace("/", "_")
    prefix = f"{model_slug}_{run_id}_" if run_id else f"{model_slug}_"

    # Clean styling
    plt.rcParams.update({"font.size": 11, "font.family": "sans-serif"})

    # 1. Figure: Cooperation Rate by Context Type & Partner Type
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)

    # By Context Type
    context_order = [
        "neutral_or_costless",
        "modest_cost",
        "conflict_with_objective",
        "ineffective_or_inappropriate",
    ]
    ctx_labels = [
        "Neutral / Costless",
        "Modest Cost",
        "Conflict w/ Goal",
        "Ineffective / Inappr.",
    ]

    ctx_means = scenario_df.groupby("context_type")["coop_argmax_rate"].mean().reindex(context_order)
    ctx_errors = scenario_df.groupby("context_type")["coop_argmax_rate"].sem().reindex(context_order)

    bars1 = ax1.bar(range(len(context_order)), ctx_means, yerr=ctx_errors, capsize=4, color="#2b5c8f", alpha=0.85)
    ax1.axhline(0.25, color="red", linestyle="--", linewidth=1.2, label="25% Reference (Four-choice Share)")
    ax1.set_xticks(range(len(context_order)))
    ax1.set_xticklabels(ctx_labels, rotation=20, ha="right")
    ax1.set_ylabel("Cooperative Argmax Rate (Scenario-Mean)")
    ax1.set_title("Cooperation by Context / Cost Stratum")
    ax1.set_ylim(0, 1.0)
    ax1.legend(loc="upper right")
    ax1.grid(axis="y", linestyle=":", alpha=0.6)

    # By Partner Type
    partner_order = ["human", "ai"]
    partner_labels = ["Human Interaction", "AI Interaction"]
    p_means = scenario_df.groupby("partner_type")["coop_argmax_rate"].mean().reindex(partner_order)
    p_errors = scenario_df.groupby("partner_type")["coop_argmax_rate"].sem().reindex(partner_order)

    bars2 = ax2.bar(range(len(partner_order)), p_means, yerr=p_errors, capsize=4, color="#3e8e75", alpha=0.85)
    ax2.axhline(0.25, color="red", linestyle="--", linewidth=1.2, label="25% Reference")
    ax2.set_xticks(range(len(partner_order)))
    ax2.set_xticklabels(partner_labels)
    ax2.set_title("Cooperation by Partner Type")
    ax2.grid(axis="y", linestyle=":", alpha=0.6)

    fig.suptitle(f"Phase 0 Behavioural Screen: {model_name}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    f1_path = os.path.join(output_dir, f"{prefix}cooperation_by_strata.png")
    plt.savefig(f1_path, dpi=300)
    plt.close()
    generated_files.append(f1_path)

    # 2. Figure: Strategy Allocation Distribution (Overall & Context)
    fig, ax = plt.subplots(figsize=(8, 5))
    strategies = ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]
    strat_colors = ["#2b5c8f", "#e67e22", "#c0392b", "#7f8c8d"]
    strat_labels = ["Cooperate", "Independent", "Compete / Exploit", "Disengage"]

    strat_rates = [
        scenario_df["coop_argmax_rate"].mean(),
        scenario_df["indep_argmax_rate"].mean(),
        scenario_df["compete_argmax_rate"].mean(),
        scenario_df["disengage_argmax_rate"].mean(),
    ]

    bars = ax.bar(strat_labels, strat_rates, color=strat_colors, alpha=0.9)
    ax.axhline(0.25, color="black", linestyle="--", linewidth=1.2, label="25% Reference")
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.1%}", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    ax.set_ylim(0, max(strat_rates) * 1.25 if max(strat_rates) > 0 else 1.0)
    ax.set_ylabel("Selection Rate Across Scenarios")
    ax.set_title(f"Strategy Distribution Breakdown: {model_name}")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    f2_path = os.path.join(output_dir, f"{prefix}strategy_distribution.png")
    plt.savefig(f2_path, dpi=300)
    plt.close()
    generated_files.append(f2_path)

    # 3. Figure: Answer Position Sensitivity Audit
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    letters = ["A", "B", "C", "D"]
    pos_rates = [position_bias.get(l, 0.0) for l in letters]
    ax.bar(letters, pos_rates, color="#5c6bc0", alpha=0.85)
    ax.axhline(0.25, color="red", linestyle="--", linewidth=1.2, label="25% Uniform Baseline")
    for l, r in zip(letters, pos_rates):
        ax.annotate(f"{r:.1%}", xy=(l, r), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom")
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Presentation Position Letter")
    ax.set_ylabel("Selection Frequency")
    ax.set_title(f"Answer Position Bias Audit: {model_name}")
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    f3_path = os.path.join(output_dir, f"{prefix}position_bias_audit.png")
    plt.savefig(f3_path, dpi=300)
    plt.close()
    generated_files.append(f3_path)

    return generated_files
