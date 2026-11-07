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
    assert hasattr(modal_app, "run_evaluation_mock_remote")
    assert hasattr(modal_app, "run_evaluation_remote")


def _create_synthetic_qualifying_run_file(filepath: Path, model_name: str, run_id: str, is_mock: bool = False):
    metadata = {
        "run_id": run_id,
        "model_name": model_name,
        "model_revision": None,
        "effective_precision": "bfloat16",
        "mock": is_mock,
        "num_scenarios": 24,
        "num_presentations": 96,
    }
    records = []
    latin_square = [
        ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"],
        ["INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE", "COOPERATE"],
        ["COMPETE_EXPLOIT", "DISENGAGE", "COOPERATE", "INDEPENDENT"],
        ["DISENGAGE", "COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT"],
    ]
    context_types = (
        ["neutral_or_costless"] * 6
        + ["modest_cost"] * 6
        + ["conflict_with_objective"] * 6
        + ["ineffective_or_inappropriate"] * 6
    )
    for sc in range(24):
        ctx = context_types[sc]
        partner = "human" if sc % 2 == 0 else "ai"
        for p in range(4):
            mapping = latin_square[p]
            strat_to_letter = {strat: chr(65 + idx) for idx, strat in enumerate(mapping)}
            letter_to_strat = {chr(65 + idx): strat for idx, strat in enumerate(mapping)}

            if ctx in ["neutral_or_costless", "modest_cost"]:
                chosen_strat = "COOPERATE"
            else:
                chosen_strat = "INDEPENDENT"

            chosen_letter = strat_to_letter[chosen_strat]
            probs = {letter: (0.70 if letter == chosen_letter else 0.10) for letter in ["A", "B", "C", "D"]}

            records.append({
                "presentation_id": f"sc_{sc}_perm_{p}",
                "scenario_id": f"sc_{sc}",
                "permutation_index": p,
                "partner_type": partner,
                "context_type": ctx,
                "letter_to_strategy": letter_to_strat,
                "strategy_to_letter": strat_to_letter,
                "candidate_tokens": {"A": 1, "B": 2, "C": 3, "D": 4},
                "raw_logits": {k: 5.0 for k in ["A", "B", "C", "D"]},
                "conditional_logprobs": {k: -1.0 for k in ["A", "B", "C", "D"]},
                "raw_logprobs": {k: -1.0 for k in ["A", "B", "C", "D"]},
                "conditional_probs": probs,
                "forced_choice_argmax_letter": chosen_letter,
                "forced_choice_argmax_strategy": chosen_strat,
                "generated_raw_text": chosen_letter,
                "generated_letter": chosen_letter,
                "is_valid_letter": True,
                "generated_strategy": chosen_strat,
                "elapsed_seconds": 0.01,
            })

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_cross_model_gate_requires_independent_families(tmp_path):
    """Verify deduplication of runs and requirement of distinct model families for advancement."""
    out_dir = tmp_path / "reports"

    # 1. Same model checkpoint supplied twice (e.g. duplicate runs or duplicate files)
    run1 = tmp_path / "olmo1b_run1.jsonl"
    run2 = tmp_path / "olmo1b_run2.jsonl"
    _create_synthetic_qualifying_run_file(run1, "allenai/OLMo-2-1124-1B", "run_olmo1b_1")
    _create_synthetic_qualifying_run_file(run2, "allenai/OLMo-2-1124-1B", "run_olmo1b_2")

    report_dup = compare_models([str(run1), str(run2)], output_dir=str(out_dir / "dup"), num_bootstraps=100)
    with open(report_dup, "r", encoding="utf-8") as f:
        content_dup = f.read()

    assert "ADVANCE TO PHASE 1" not in content_dup
    assert "REVISE / EXTEND SCREEN" in content_dup
    assert "Cross-family replication not yet achieved" in content_dup

    # 2. Two checkpoints from the SAME family (OLMo-1B and OLMo-7B)
    run_olmo7b = tmp_path / "olmo7b.jsonl"
    _create_synthetic_qualifying_run_file(run_olmo7b, "allenai/OLMo-2-1124-7B", "run_olmo7b")

    report_same_fam = compare_models([str(run1), str(run_olmo7b)], output_dir=str(out_dir / "same_fam"), num_bootstraps=100)
    with open(report_same_fam, "r", encoding="utf-8") as f:
        content_same_fam = f.read()

    assert "ADVANCE TO PHASE 1" not in content_same_fam
    assert "REVISE / EXTEND SCREEN" in content_same_fam
    assert "Only 1 base model family (OLMO with 2 checkpoint(s)" in content_same_fam
    assert "Cross-family replication not yet achieved" in content_same_fam

    # 3. Two checkpoints from DISTINCT families (OLMo-1B [olmo] and Qwen2.5-3B [qwen])
    run_qwen = tmp_path / "qwen3b.jsonl"
    _create_synthetic_qualifying_run_file(run_qwen, "Qwen/Qwen2.5-3B", "run_qwen3b")

    report_multi_fam = compare_models([str(run1), str(run_qwen)], output_dir=str(out_dir / "multi_fam"), num_bootstraps=100)
    with open(report_multi_fam, "r", encoding="utf-8") as f:
        content_multi_fam = f.read()

    assert "HUMAN SCIENTIFIC REVIEW RECOMMENDED (POTENTIAL PHASE 1 PILOT)" in content_multi_fam
    assert "Multiple independent base model families (2: OLMO, QWEN; 2 distinct model checkpoints)" in content_multi_fam


def test_modal_app_mock_and_gpu_routing(monkeypatch):
    """Verify mock execution is routed to zero-GPU CPU function while real runs use GPU."""
    import modal_app

    assert hasattr(modal_app, "run_evaluation_mock_remote")
    assert hasattr(modal_app, "run_evaluation_remote")
    assert hasattr(modal_app, "run_evaluation_remote_l40s")
    assert hasattr(modal_app, "resolve_model_gpu")

    # Verify 12B model selects L40S
    assert modal_app.resolve_model_gpu("EleutherAI/pythia-12b-deduped") == "L40S"
    assert modal_app.resolve_model_gpu("OpenAssistant/oasst-sft-1-pythia-12b") == "L40S"
    assert modal_app.resolve_model_gpu("Qwen/Qwen2.5-3B") == "A10G"

    # run_evaluation_remote rejects mock=True
    with pytest.raises(ValueError, match="provisions paid GPU resources"):
        modal_app.run_evaluation_remote.local(model_name="mock-test", mock=True)

    # Test CLI entrypoint routing
    mock_calls = []
    gpu_calls = []

    monkeypatch.setattr(
        modal_app.run_evaluation_mock_remote,
        "remote",
        lambda **kwargs: mock_calls.append(kwargs) or "/root/results/mock_result.jsonl",
    )
    monkeypatch.setattr(
        modal_app.run_evaluation_remote,
        "remote",
        lambda **kwargs: gpu_calls.append(kwargs) or "/root/results/gpu_result.jsonl",
    )

    # Calling main with mock=True routes to mock remote function (CPU)
    modal_app.main(model="test-model", mock=True)
    assert len(mock_calls) == 1
    assert len(gpu_calls) == 0

    # Calling main with mock=False without authorization raises PermissionError
    with pytest.raises(PermissionError, match="PAID RUN GUARD TRIGGERED"):
        modal_app.main(model="test-model", mock=False, authorize_paid_run=False)

    # Calling main with mock=False and authorize_paid_run=True routes to GPU remote function
    modal_app.main(model="test-model", mock=False, authorize_paid_run=True)
    assert len(mock_calls) == 1
    assert len(gpu_calls) == 1
    assert gpu_calls[0]["mock"] is False


def test_modal_app_phase0b_routing_and_guards(monkeypatch):
    """Verify modal_app packages and routes Phase 0B, defaults to exploratory,

    requires confirmatory authorization, and fails on unsupported banks.
    """
    import modal_app

    # 1. Unsupported bank fails fast
    with pytest.raises(ValueError, match="Unsupported bank 'unknown_invalid_bank'"):
        modal_app.resolve_bank_and_split("unknown_invalid_bank")

    # 2. Phase 0B defaults to exploratory
    p_path, p_split = modal_app.resolve_bank_and_split("phase0b")
    assert p_path == "/root/data/scenarios_phase0b_utility_matched.json"
    assert p_split == "exploratory"

    u_path, u_split = modal_app.resolve_bank_and_split("utility-matched")
    assert u_path == "/root/data/scenarios_phase0b_utility_matched.json"
    assert u_split == "exploratory"

    # 3. Phase 0B confirmatory requires authorization
    with pytest.raises(PermissionError, match="CONFIRMATORY SPLIT GUARD"):
        modal_app.resolve_bank_and_split("phase0b", split="confirmatory", authorize_confirmatory=False)

    with pytest.raises(PermissionError, match="CONFIRMATORY SPLIT GUARD"):
        modal_app.resolve_bank_and_split("phase0b", split="all", authorize_confirmatory=False)

    # 4. Phase 0B confirmatory succeeds with authorization
    _, auth_split = modal_app.resolve_bank_and_split("phase0b", split="confirmatory", authorize_confirmatory=True)
    assert auth_split == "confirmatory"

    # 5. Modal app main routes split and bank parameters
    mock_calls = []
    monkeypatch.setattr(
        modal_app.run_evaluation_mock_remote,
        "remote",
        lambda **kwargs: mock_calls.append(kwargs) or "/root/results/mock_result.jsonl",
    )

    modal_app.main(model="test-model", mock=True, bank="phase0b")
    assert len(mock_calls) == 1
    assert mock_calls[0]["bank"] == "phase0b"
    assert mock_calls[0]["split"] is None  # Defaults inside resolve_bank_and_split to exploratory


def test_markdown_report_presentation_count_label():
    """Verify generate_markdown_report reflects actual presentation count rather than hardcoded 96."""
    import pandas as pd
    from llm_cooperation.analysis.pipeline import generate_markdown_report

    metadata = {"model_name": "test-model", "num_presentations": 480}
    records = [
        {"scenario_id": f"s_{i}", "partner_type": "human", "context_type": "neutral_or_costless",
         "coop_argmax_rate": 0.5, "coop_cond_prob": 0.5, "valid_letter_rate": 1.0, "num_permutations": 4}
        for i in range(120)
    ]
    df = pd.DataFrame(records)
    boot = {"mean": 0.5, "ci_lower": 0.4, "ci_upper": 0.6}
    pos_bias = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}

    report = generate_markdown_report(
        metadata=metadata,
        scenario_df=df,
        overall_boot=boot,
        prob_boot=boot,
        pos_bias=pos_bias,
        output_path="/dev/null",
    )

    assert "Scenarios Evaluated (N):** 120 (480 total counterbalanced presentations)" in report
    assert "Presentation frequency of chosen letters across all 480 counterbalanced presentations:" in report
    assert "96 total counterbalanced presentations" not in report
    assert "across all 96 counterbalanced presentations" not in report

def test_prompt_boundary_token_validation():
    """Verify prompt boundary token validation detects multi-token fragmentation and incompatible token IDs."""
    from llm_cooperation.harness.tokenizer_probe import (
        resolve_candidate_token_ids,
        TokenizerCandidateError,
        validate_candidate_tokens_at_boundary,
    )

    class GoodBoundaryTokenizer:
        def encode(self, text, add_special_tokens=False):
            if text == "A": return [1]
            if text == "B": return [2]
            if text == "C": return [3]
            if text == "D": return [4]
            if text == " A": return [11]
            if text == " B": return [12]
            if text == " C": return [13]
            if text == " D": return [14]
            if text == "Answer:": return [100, 101]
            if text == "Answer: A": return [100, 101, 11]
            if text == "Answer: B": return [100, 101, 12]
            if text == "Answer: C": return [100, 101, 13]
            if text == "Answer: D": return [100, 101, 14]
            return [999]

    tok = GoodBoundaryTokenizer()
    res = resolve_candidate_token_ids(tok, sample_prompt="Answer:")
    assert res == {"A": 11, "B": 12, "C": 13, "D": 14}

    class IncompatibleBoundaryTokenizer(GoodBoundaryTokenizer):
        def encode(self, text, add_special_tokens=False):
            if text == "Answer: A": return [100, 101, 999]
            return super().encode(text, add_special_tokens=add_special_tokens)

    bad_tok = IncompatibleBoundaryTokenizer()
    with pytest.raises(TokenizerCandidateError, match="Incompatible token substitution barred"):
        resolve_candidate_token_ids(bad_tok, sample_prompt="Answer:")


def test_scenario_banks_hash_traceability():
    """Verify legacy and revised scenario banks exist with distinct sha256 hashes."""
    import hashlib
    p_rev = Path("data/scenarios.json")
    p_leg = Path("data/scenarios_legacy_v020.json")
    assert p_rev.exists()
    assert p_leg.exists()

    h_rev = hashlib.sha256(p_rev.read_bytes()).hexdigest()
    h_leg = hashlib.sha256(p_leg.read_bytes()).hexdigest()
    assert h_rev != h_leg

def test_gpu_profile_numeric_parsing():
    """Verify GPU hardware selection uses numeric parsing rather than naive substring matching."""
    import modal_app
    # 2.8B must resolve to small (A10G), not medium (L40S)
    assert modal_app.resolve_model_gpu("EleutherAI/pythia-2.8b") == "A10G"
    assert modal_app.resolve_model_gpu("Qwen/Qwen2.5-3B") == "A10G"
    assert modal_app.resolve_model_gpu("allenai/OLMo-2-1124-1B") == "A10G"

    # 7B and 12B must resolve to medium (L40S)
    assert modal_app.resolve_model_gpu("allenai/OLMo-2-1124-7B") == "L40S"
    assert modal_app.resolve_model_gpu("mistralai/Mistral-7B-v0.3") == "L40S"
    assert modal_app.resolve_model_gpu("EleutherAI/pythia-12b-deduped") == "L40S"
    assert modal_app.resolve_model_gpu("OpenAssistant/oasst-sft-1-pythia-12b") == "L40S"

    # 70B must resolve to large (A100-80GB)
    assert modal_app.resolve_model_gpu("meta-llama/Llama-2-70b-hf") == "A100-80GB"

    # Unsupported large profile fails before provisioning
    with pytest.raises(NotImplementedError, match="not currently provisioned"):
        modal_app.main(model="meta-llama/Llama-2-70b-hf", mock=False, authorize_paid_run=True)


def test_unverified_model_cohort_separation(tmp_path):
    """Verify unknown/unverified models are isolated into a third cohort and excluded from base conclusions."""
    out_dir = tmp_path / "reports"
    run_unverified = tmp_path / "unknown_model.jsonl"
    _create_synthetic_qualifying_run_file(run_unverified, "some-org/unverified-unknown-model", "run_unknown")

    report_file = compare_models([str(run_unverified)], output_dir=str(out_dir), num_bootstraps=50)
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Unverified / Unknown Provenance Cohort" in content
    assert "some-org/unverified-unknown-model" in content
    assert "STOP OR REVISE" in content
    assert "ADVANCE" not in content


def test_prompt_boundary_prefix_retokenization_error():
    """Verify boundary validator detects when appending a letter causes prefix retokenization."""
    from llm_cooperation.harness.tokenizer_probe import (
        resolve_candidate_token_ids,
        TokenizerCandidateError,
    )

    class RetokenizingTokenizer:
        def encode(self, text, add_special_tokens=False):
            if text == "A": return [1]
            if text == "B": return [2]
            if text == "C": return [3]
            if text == "D": return [4]
            if text == " A": return [11]
            if text == " B": return [12]
            if text == " C": return [13]
            if text == " D": return [14]
            if text == "Answer:": return [100, 101]
            if text == "Answer: A": return [100, 999]  # retokenized previous token!
            if text == "Answer: B": return [100, 101, 12]
            if text == "Answer: C": return [100, 101, 13]
            if text == "Answer: D": return [100, 101, 14]
            return [500]

    tok = RetokenizingTokenizer()
    with pytest.raises(TokenizerCandidateError, match="prefix retokenization"):
        resolve_candidate_token_ids(tok, sample_prompt="Answer:")

def test_real_model_runner_loading_and_presentation_preflight(monkeypatch):
    """Verify ModelRunner._load_model loads model, sets effective precision, and validates all presentation boundaries."""
    import torch
    from llm_cooperation.harness.runner import ModelRunner
    from llm_cooperation.items.schema import ScenarioBank
    from llm_cooperation.items.permutations import generate_all_presentations

    # Load all 96 presentations from scenarios.json
    with open("data/scenarios.json", "r", encoding="utf-8") as f:
        bank_data = json.load(f)
    bank = ScenarioBank(**bank_data)
    presentations = generate_all_presentations(bank.scenarios)
    assert len(presentations) == 96

    class FakeTokenizer:
        def __init__(self):
            self.pad_token = None
            self.eos_token = "<eos>"

        def encode(self, text, add_special_tokens=False):
            if text == "A": return [1]
            if text == "B": return [2]
            if text == "C": return [3]
            if text == "D": return [4]
            if text == " A": return [11]
            if text == " B": return [12]
            if text == " C": return [13]
            if text == " D": return [14]
            # When ending with Answer: continuation is " A", etc.
            if text.endswith("Answer:"):
                return list(range(len(text.split())))
            if text.endswith("Answer: A"):
                prefix = list(range(len(text[:-2].split())))
                return prefix + [11]
            if text.endswith("Answer: B"):
                prefix = list(range(len(text[:-2].split())))
                return prefix + [12]
            if text.endswith("Answer: C"):
                prefix = list(range(len(text[:-2].split())))
                return prefix + [13]
            if text.endswith("Answer: D"):
                prefix = list(range(len(text[:-2].split())))
                return prefix + [14]
            return [100]

    class FakeModel:
        def __init__(self):
            self.dtype = torch.bfloat16
            self.eval_called = False

        def eval(self):
            self.eval_called = True

    monkeypatch.setattr(
        "transformers.AutoTokenizer.from_pretrained",
        lambda *args, **kwargs: FakeTokenizer(),
    )
    monkeypatch.setattr(
        "transformers.AutoModelForCausalLM.from_pretrained",
        lambda *args, **kwargs: FakeModel(),
    )

    # Initialize real (non-mock) ModelRunner
    runner = ModelRunner("test-real-model", precision="bfloat16", mock=False)

    # Verify model loading was completed within _load_model
    assert runner.model is not None
    assert runner.model.eval_called is True
    assert runner.effective_precision == "bfloat16"
    assert runner.candidate_token_ids == {"A": 11, "B": 12, "C": 13, "D": 14}

    # Verify validate_presentation_boundaries runs preflight across all 96 presentations without error
    runner.validate_presentation_boundaries(presentations)
