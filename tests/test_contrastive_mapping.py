"""Tests for exploratory contrastive representation-mapping module."""

import json
from pathlib import Path
import pytest
import numpy as np

from llm_cooperation.mechanistic.contrastive_mapping import (
    DEFAULT_MODEL_ID,
    DEFAULT_REVISION,
    STRATEGIES,
    TRAILING_MARKER,
    format_single_action_prompt,
    load_scenarios,
    partition_families,
    prepare,
    run_inference,
    compute_paired_differences,
    bootstrap_ci,
    analyze_contrastive_mapping,
)


def test_prompt_formatting():
    stem = "Scenario stem text."
    action = "Perform action independently."
    prompt = format_single_action_prompt(stem, action, TRAILING_MARKER)
    assert prompt == "Scenario stem text.\n\nAction: Perform action independently.\nDecision:"
    assert "A." not in prompt
    assert "B." not in prompt
    assert "Choose" not in prompt


def test_partition_families_preserves_clusters():
    scenarios = [
        {"id": "s1_h", "template_id": "t1", "triad_id": None, "stem": "stem 1", "options": {}},
        {"id": "s1_ai", "template_id": "t1", "triad_id": None, "stem": "stem 1", "options": {}},
        {"id": "s2_h", "template_id": "t2", "triad_id": "triad_1", "stem": "stem 2", "options": {}},
        {"id": "s2_ai", "template_id": "t2", "triad_id": "triad_1", "stem": "stem 2", "options": {}},
        {"id": "s3_h", "template_id": "t3", "triad_id": "triad_1", "stem": "stem 3", "options": {}},
        {"id": "s4_h", "template_id": "t4", "triad_id": None, "stem": "stem 4", "options": {}},
    ]
    disc_ids, eval_ids = partition_families(scenarios, discovery_fraction=0.5, seed=42)

    # All IDs must be accounted for
    all_partitioned = set(disc_ids) | set(eval_ids)
    assert all_partitioned == {s["id"] for s in scenarios}
    assert len(set(disc_ids) & set(eval_ids)) == 0

    # s1_h and s1_ai must be in the same partition (shared template t1)
    assert ("s1_h" in disc_ids and "s1_ai" in disc_ids) or ("s1_h" in eval_ids and "s1_ai" in eval_ids)

    # s2_h, s2_ai, and s3_h must be in the same partition (shared triad triad_1)
    triad_ids = {"s2_h", "s2_ai", "s3_h"}
    assert triad_ids.issubset(set(disc_ids)) or triad_ids.issubset(set(eval_ids))


def test_prepare_offline_dataset(tmp_path):
    out_dir = tmp_path / "prepared"
    manifest = prepare(out_dir, smoke=True)
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "prompts.jsonl").exists()

    prompts = [json.loads(line) for line in (out_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(prompts) == manifest["num_prompts"]

    # Each scenario must have 4 strategies
    by_scenario = {}
    for p in prompts:
        by_scenario.setdefault(p["scenario_id"], []).append(p["strategy"])
    for sid, strats in by_scenario.items():
        assert sorted(strats) == sorted(STRATEGIES)


def test_authorization_guard(tmp_path):
    out_dir = tmp_path / "prep"
    prepare(out_dir, smoke=True)
    run_dir = tmp_path / "run"

    # Must raise PermissionError when authorize=False and mock=False
    with pytest.raises(PermissionError, match="authorization"):
        run_inference(out_dir, run_dir, authorize=False, mock=False)


def test_paired_differences_and_bootstrap_math():
    # Unit test bootstrap math
    by_fam = {
        "fam1": [1.0, 1.2],
        "fam2": [2.0, 2.1],
        "fam3": [3.0, 2.9],
        "fam4": [4.0, 4.1],
    }
    mean_val, low, high = bootstrap_ci(by_fam, n_boot=500, seed=123)
    assert 2.0 < mean_val < 3.0
    assert low < mean_val < high

    # Unit test paired difference calculation
    activations = {
        "scen1_COOPERATE": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        "scen1_INDEPENDENT": np.array([[0.5, 1.0], [1.0, 2.0]], dtype=np.float32),
    }
    diffs = compute_paired_differences(activations, "COOPERATE", "INDEPENDENT")
    assert "scen1" in diffs
    expected = np.array([[0.5, 1.0], [2.0, 2.0]], dtype=np.float32)
    np.testing.assert_allclose(diffs["scen1"], expected)


def test_smoke_end_to_end(tmp_path):
    plan_dir = tmp_path / "plan"
    run_dir = tmp_path / "run"
    analysis_dir = tmp_path / "analysis"

    prepare(plan_dir, smoke=True)
    manifest = run_inference(plan_dir, run_dir, mock=True)
    assert manifest["status"] == "completed"
    assert (run_dir / "evidence_hashes.json").exists()

    report = analyze_contrastive_mapping(
        run_dir=run_dir,
        prompts_path=plan_dir / "prompts.jsonl",
        output_dir=analysis_dir,
        n_boot=100,
    )
    assert (analysis_dir / "contrastive_report.json").exists()
    assert (analysis_dir / "contrastive_report.md").exists()
    assert len(report["layer_metrics"]) == 28
    assert "coop_minus_compete" in report["alternative_strategy_contrasts"]
    assert len(report["lexical_length_correlations"]) == 28
