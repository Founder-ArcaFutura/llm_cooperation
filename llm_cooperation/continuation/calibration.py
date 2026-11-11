"""Calibration runner for the continuation-likelihood assay.

Scores candidate actions in calibration scenarios where context clearly
favors a specific strategy. Establishes whether continuation log-probability
is meaningfully context-sensitive.

This is a diagnostic tool, not a measure of cooperative preference.
An inability to recover calibration signals does not imply that
cooperative representations are absent — it means the measurement
is insufficiently discriminative.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from llm_cooperation.continuation.runner import compute_file_hash
from llm_cooperation.continuation.scorer import (
    score_all_strategies_for_prefix,
)
from llm_cooperation.continuation.templates import build_prefix, ALL_TEMPLATE_IDS
from llm_cooperation.items.schema import StrategyType

STRATEGIES = ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]

CALIBRATION_BANK_PATH = "data/continuation_calibration_bank.json"


def load_calibration_bank(path: str = CALIBRATION_BANK_PATH) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_continuation_calibration(
    model,
    tokenizer,
    model_name: str,
    model_revision: Optional[str],
    effective_precision: str,
    mock: bool = False,
    template_ids: Optional[List[str]] = None,
    calibration_path: str = CALIBRATION_BANK_PATH,
    rng: Optional[np.random.Generator] = None,
) -> Dict:
    """Score calibration bank and return context-sensitivity diagnostics.

    Returns:
        Dict with per-scenario expected/actual top strategy and
        overall calibration accuracy.
    """
    if template_ids is None:
        template_ids = ALL_TEMPLATE_IDS

    if rng is None:
        rng = np.random.default_rng(seed=0)

    bank = load_calibration_bank(calibration_path)
    scenarios = bank["scenarios"]

    results = []
    for sc in scenarios:
        expected = sc["expected_top_strategy"]
        stem = sc["stem"]
        options = sc["options"]

        strategy_continuations = {
            StrategyType(k): v for k, v in options.items()
        }

        per_template_top: List[str] = []

        for template_id in template_ids:
            prefix_text = build_prefix(stem, template_id)
            scores = score_all_strategies_for_prefix(
                model=model,
                tokenizer=tokenizer,
                prefix_text=prefix_text,
                strategy_continuations=strategy_continuations,
                model_name=model_name,
                model_revision=model_revision,
                precision=effective_precision,
                scenario_id=sc["id"],
                template_id=template_id,
                candidate_wording_id="original",
                mock=mock,
                rng=rng,
            )

            # Find top strategy by sum log-prob
            top_strat = max(scores.items(), key=lambda kv: kv[1].sum_log_prob)[0]
            per_template_top.append(top_strat)

        # Majority vote across templates
        from collections import Counter
        majority_top = Counter(per_template_top).most_common(1)[0][0]
        correct = (majority_top == expected)

        results.append({
            "scenario_id": sc["id"],
            "expected_top_strategy": expected,
            "actual_top_by_majority": majority_top,
            "per_template_top": per_template_top,
            "correct": correct,
            "rationale": sc.get("rationale", ""),
        })

    n_correct = sum(1 for r in results if r["correct"])
    n_total = len(results)
    accuracy = n_correct / n_total if n_total > 0 else 0.0

    return {
        "accuracy": accuracy,
        "n_correct": n_correct,
        "n_total": n_total,
        "calibration_path": calibration_path,
        "bank_hash": compute_file_hash(calibration_path),
        "templates_used": template_ids,
        "results": results,
        "interpretation": (
            f"Context-sensitivity calibration: {n_correct}/{n_total} scenarios ({100*accuracy:.1f}%) "
            f"recovered expected top strategy. "
            f"Failure to recover expected strategies does not disprove cooperation representations; "
            f"it indicates the log-probability measurement is insufficiently discriminative."
        ),
    }
