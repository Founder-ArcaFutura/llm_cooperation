"""Regression and acceptance tests for Phase 0 repairs and improvements.

Covers:
1. Precision mapping and effective precision tracking (Codex finding 1).
2. Strict letter-only parsing and ambiguous output rejection (Codex finding 2).
3. Conservative decision gates, strata failure detection, and mock ADVANCE barrier (Codex finding 3).
4. Plot and report overwrite prevention across multiple runs (Codex finding 4).
5. Tokenizer candidate diagnostic validation and multi-token errors.
6. Run data integrity validation (missing records, corrupted probabilities).
7. Model manifest validation and Pythia-12B SFT comparator configuration.
8. Cross-model comparison report distinguishing base models and SFT comparators.
9. Modal application structure without GPU execution.
"""

import json
from pathlib import Path
import pytest
import yaml

from llm_cooperation.harness.runner import (
    ModelRunner,
    parse_generated_letter,
    run_experiment,
)
from llm_cooperation.harness.tokenizer_probe import (
    resolve_candidate_token_ids,
    TokenizerCandidateError,
)
from llm_cooperation.analysis.metrics import (
    load_run_results,
    validate_run_data,
    RunDataValidationError,
    aggregate_by_scenario,
    scenario_cluster_bootstrap,
    audit_position_bias,
)
from llm_cooperation.analysis.pipeline import (
    analyze_results,
    compare_models,
    generate_markdown_report,
)
from llm_cooperation.items.schema import ScenarioBank


def test_precision_mapping_and_effective_dtype():
    """Verify precision mapping for float32, float16, and bfloat16."""
    import torch

    assert ModelRunner.resolve_torch_dtype("bfloat16") == torch.bfloat16
    assert ModelRunner.resolve_torch_dtype("float16") == torch.float16
    assert ModelRunner.resolve_torch_dtype("float32") == torch.float32

    with pytest.raises(ValueError, match="Unsupported precision"):
        ModelRunner.resolve_torch_dtype("int8")

    # Mock runner records effective precision
    runner = ModelRunner("mock-model", precision="float32", mock=True)
    assert runner.requested_precision == "float32"
    assert runner.effective_precision == "float32"


def test_strict_letter_parsing():
    """Verify ambiguous, disjunctive, and explanatory responses are strictly rejected."""
    # Valid isolated letters
    assert parse_generated_letter("A") == ("A", True)
    assert parse_generated_letter(" B ") == ("B", True)
    assert parse_generated_letter("A.") == ("A", True)
    assert parse_generated_letter("(C)") == ("C", True)
    assert parse_generated_letter("[D]") == ("D", True)
    assert parse_generated_letter("B)") == ("B", True)
    assert parse_generated_letter("C:") == ("C", True)

    # Disjunctions / ambiguous multiple letters
    assert parse_generated_letter("A or B") == (None, False)
    assert parse_generated_letter("A, B, C, or D") == (None, False)
    assert parse_generated_letter("Neither A nor B") == (None, False)
    assert parse_generated_letter("Either C or D") == (None, False)
    assert parse_generated_letter("Both A and B") == (None, False)

    # Explanations / non-letter-only contract
    assert parse_generated_letter("A is best because it helps") == (None, False)
    assert parse_generated_letter("B, because of the deadline") == (None, False)
    assert parse_generated_letter("I choose C") == (None, False)
    assert parse_generated_letter("Option D") == (None, False)
    assert parse_generated_letter("Action A") == (None, False)


def test_tokenizer_multi_token_diagnostic_error():
    """Verify multi-token candidate letters raise explicit TokenizerCandidateError."""
    class FakeMultiTokenTokenizer:
        def encode(self, text, add_special_tokens=False):
            if text.strip() == "A":
                return [101, 102]  # multi-token
            return [200]

    with pytest.raises(TokenizerCandidateError, match="multi-token sequence"):
        resolve_candidate_token_ids(FakeMultiTokenTokenizer())


def test_mock_run_cannot_advance():
    """Verify mock runs cannot produce an ADVANCE recommendation."""
    # Simulate mock metadata
    metadata = {
        "model_name": "mock-test",
        "mock": True,
        "timestamp": "2026-11-03T00:00:00Z",
    }
    # Create fake scenario df with high cooperation
    import pandas as pd
    scenario_df = pd.DataFrame([
        {"scenario_id": f"s_{i}", "partner_type": "human", "context_type": "neutral_or_costless",
         "coop_argmax_rate": 0.9, "coop_cond_prob": 0.85, "valid_letter_rate": 1.0}
        for i in range(24)
    ])
    overall_boot = {"mean": 0.90, "ci_lower": 0.85, "ci_upper": 0.95}
    prob_boot = {"mean": 0.85, "ci_lower": 0.80, "ci_upper": 0.90}
    pos_bias = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}

    report = generate_markdown_report(
        metadata=metadata,
        scenario_df=scenario_df,
        overall_boot=overall_boot,
        prob_boot=prob_boot,
        pos_bias=pos_bias,
        output_path="/dev/null",
    )
    assert "MOCK RUN (NO SCIENTIFIC ADVANCEMENT)" in report
    assert "ADVANCE" not in report.split("Gate Recommendation")[1].split("Overall Cooperative")[0].replace("NO SCIENTIFIC ADVANCEMENT", "")


def test_strata_conflict_contradiction_gate():
    """Verify aggregate cooperation cannot conceal failure in conflicting/ineffective strata."""
    import pandas as pd
    metadata = {"model_name": "real-test", "mock": False}
    # 18 neutral scenarios with high coop, 6 conflicting with high coop (indiscriminate agreement)
    records = []
    for i in range(12):
        records.append({"scenario_id": f"s_{i}", "partner_type": "human", "context_type": "neutral_or_costless",
                        "coop_argmax_rate": 0.8, "coop_cond_prob": 0.7, "valid_letter_rate": 1.0})
    for i in range(12, 24):
        records.append({"scenario_id": f"s_{i}", "partner_type": "human", "context_type": "conflict_with_objective",
                        "coop_argmax_rate": 0.75, "coop_cond_prob": 0.7, "valid_letter_rate": 1.0})
    scenario_df = pd.DataFrame(records)

    overall_boot = {"mean": 0.775, "ci_lower": 0.72, "ci_upper": 0.82}
    prob_boot = {"mean": 0.70, "ci_lower": 0.65, "ci_upper": 0.75}
    pos_bias = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}

    report = generate_markdown_report(
        metadata=metadata,
        scenario_df=scenario_df,
        overall_boot=overall_boot,
        prob_boot=prob_boot,
        pos_bias=pos_bias,
        output_path="/dev/null",
    )
    assert "Indiscriminate agreement detected" in report
    assert "ADVANCE" not in report.split("Gate Recommendation")[1].split("Overall Cooperative")[0]


def test_plot_overwrite_prevention(tmp_path):
    """Verify unique run IDs prevent overwriting plot files across runs."""
    out_dir = tmp_path / "results"
    reports_dir = tmp_path / "reports"

    # Run 1
    r1 = run_experiment("test-model", output_dir=str(out_dir), mock=True, seed=1)
    res1 = analyze_results(str(r1), output_dir=str(reports_dir))

    # Run 2
    r2 = run_experiment("test-model", output_dir=str(out_dir), mock=True, seed=2)
    res2 = analyze_results(str(r2), output_dir=str(reports_dir))

    # Check distinct plots and files
    assert r1 != r2
    assert Path(res1["report_markdown"]).exists()
    assert Path(res2["report_markdown"]).exists()
    assert res1["report_markdown"] != res2["report_markdown"]
    for p in res1["plots"]:
        assert Path(p).exists()
    for p in res2["plots"]:
        assert Path(p).exists()


def test_run_data_validation():
    """Verify corrupted or incomplete run data raises RunDataValidationError."""
    metadata = {"model_name": "test"}
    # Missing records
    with pytest.raises(RunDataValidationError, match="Expected 96 presentations"):
        validate_run_data(metadata, [{"presentation_id": "1"}])

    # Corrupted probability sum
    corrupted_records = []
    for sc in range(24):
        for p in range(4):
            corrupted_records.append({
                "presentation_id": f"s_{sc}_p_{p}",
                "scenario_id": f"s_{sc}",
                "permutation_index": p,
                "conditional_probs": {"A": 0.2, "B": 0.2, "C": 0.2, "D": 0.2},  # sums to 0.8
            })
    with pytest.raises(RunDataValidationError, match="conditional probabilities sum to"):
        validate_run_data(metadata, corrupted_records)


def test_model_manifest_provenance():
    """Verify configs/models.yaml specifies correct Pythia-12B SFT comparator."""
    with open("configs/models.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Base models
    assert "qwen2.5_3b" in cfg["base_models"]
    assert "pythia_2.8b" in cfg["base_models"]
    assert "olmo2_1b" in cfg["base_models"]

    # Post-trained comparator
    pythia_sft = cfg["post_trained_comparators"]["pythia_12b_sft"]
    assert pythia_sft["hf_id"] == "OpenAssistant/oasst-sft-1-pythia-12b"
    assert pythia_sft["revision"] == "293df535fe7711a5726987fc2f17dfc87de452a1"
    assert pythia_sft["is_base"] is False
    assert "openassistant" in pythia_sft["prompt_mode_support"]

    # Same-size base comparator
    pythia_base = cfg["optional_models"]["pythia_12b_deduped_base"]
    assert pythia_base["hf_id"] == "EleutherAI/pythia-12b-deduped"
    assert pythia_base["is_base"] is True


def test_cross_model_comparison_reporting(tmp_path):
    """Verify cross-model comparison report strictly distinguishes base models from comparators."""
    out_dir = tmp_path / "results"
    reports_dir = tmp_path / "reports"

    r_base = run_experiment("Qwen/Qwen2.5-3B", output_dir=str(out_dir), mock=True, seed=10)
    r_sft = run_experiment("OpenAssistant/oasst-sft-1-pythia-12b", output_dir=str(out_dir), mock=True, seed=20)

    report_file = compare_models([str(r_base), str(r_sft)], output_dir=str(reports_dir))
    assert Path(report_file).exists()

    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Pretrained Base Model Cohort" in content
    assert "Post-Trained Comparators" in content
    assert "Qwen/Qwen2.5-3B" in content.split("Post-Trained Comparators")[0]
    assert "OpenAssistant/oasst-sft-1-pythia-12b" in content.split("Post-Trained Comparators")[1]


def test_modal_app_module_structure():
    """Verify Modal app definition without launching GPU compute."""
    import modal_app
    assert modal_app.app.name == "llm-cooperation-phase0"
    assert modal_app.hf_cache_volume is not None
    assert modal_app.results_volume is not None
    assert "L40S" in modal_app.GPU_PROFILES.values()
