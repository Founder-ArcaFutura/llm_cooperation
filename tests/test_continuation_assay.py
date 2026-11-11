"""Tests for the continuation-likelihood cooperation assay.

Coverage:
1. Token boundary verification logic
2. Causal log-probability shift (correct alignment)
3. Multi-token continuation scoring
4. Different candidate lengths
5. Strategy-to-continuation mapping from scenario schema
6. Scenario-level aggregation
7. Reproducible output metadata
8. Source bank not mutated
9. No accidental Phase 1 confirmatory holdout access
10. Numerical agreement against a reference calculation

Small or mocked models are used throughout. No GPU required.
"""

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from llm_cooperation.continuation.scorer import (
    TokenBoundaryError,
    _verify_boundary,
    score_continuation_mock,
    score_all_strategies_for_prefix,
)
from llm_cooperation.continuation.templates import (
    build_prefix,
    ALL_TEMPLATE_IDS,
    TEMPLATE_BY_ID,
)
from llm_cooperation.continuation.analysis import (
    aggregate_by_scenario,
    compute_overall_statistics,
    compute_template_sensitivity,
)
from llm_cooperation.continuation.runner import (
    run_continuation_experiment,
    load_continuation_results,
    compute_rankings,
)
from llm_cooperation.continuation.schema import (
    CandidateScoreResult,
    ScenarioContinuationResult,
)
from llm_cooperation.items.schema import StrategyType


# ---------------------------------------------------------------------------
# 1. Token boundary verification
# ---------------------------------------------------------------------------


class TestVerifyBoundary:
    """Unit tests for _verify_boundary."""

    def test_exact_prefix_match(self):
        prefix = [1, 2, 3]
        joint = [1, 2, 3, 4, 5]
        cont, warning = _verify_boundary(prefix, joint)
        assert cont == [4, 5]
        assert warning is None

    def test_bpe_merge_at_boundary(self):
        """When last prefix token is merged with first continuation token."""
        prefix = [1, 2, 3]
        # joint[0:2] == prefix[0:2] but joint[2] differs (merged)
        joint = [1, 2, 99, 5]
        cont, warning = _verify_boundary(prefix, joint)
        assert cont == [99, 5]  # starts at position n-1
        assert warning is not None
        assert "BPE boundary merge" in warning

    def test_irrecoverable_mismatch_raises(self):
        prefix = [1, 2, 3]
        joint = [9, 9, 9, 4, 5]  # completely different prefix
        with pytest.raises(TokenBoundaryError):
            _verify_boundary(prefix, joint)

    def test_joint_shorter_than_prefix_raises(self):
        prefix = [1, 2, 3, 4]
        joint = [1, 2]
        with pytest.raises(TokenBoundaryError):
            _verify_boundary(prefix, joint)

    def test_zero_continuation_tokens_exact_match(self):
        """Joint equals prefix: no continuation tokens, boundary verified."""
        prefix = [1, 2, 3]
        joint = [1, 2, 3]
        cont, warning = _verify_boundary(prefix, joint)
        assert cont == []
        assert warning is None


# ---------------------------------------------------------------------------
# 2. Causal log-probability shift and alignment
# ---------------------------------------------------------------------------


class TestCausalLogProbAlignment:
    """Verify that logits[i] is used to score token at position i+1."""

    def _make_mock_model(self, vocab_size: int = 50, seq_len: int = 10):
        """Create a mock model that returns deterministic logits."""
        import torch

        # Build deterministic logits: logits[i, tok_id] = -(i + tok_id * 0.1)
        logits_tensor = torch.zeros(1, seq_len, vocab_size)
        for i in range(seq_len):
            for t in range(vocab_size):
                logits_tensor[0, i, t] = float(-(i + t * 0.1))

        mock_model = MagicMock()
        mock_model.device = "cpu"

        class FakeOutput:
            logits = logits_tensor

        mock_model.return_value = FakeOutput()
        return mock_model, logits_tensor

    def _make_mock_tokenizer(self, prefix_text: str, continuation_text: str,
                             prefix_ids: List[int], joint_ids: List[int]):
        """Create a mock tokenizer with deterministic encode behavior."""
        mock_tok = MagicMock()

        def encode(text, add_special_tokens=False):
            if text == prefix_text:
                return list(prefix_ids)
            # joint_text: prefix + " " + continuation or prefix + continuation
            if text in (prefix_text + " " + continuation_text,
                        prefix_text + continuation_text):
                return list(joint_ids)
            return [0] * len(text.split())

        mock_tok.encode.side_effect = encode
        mock_tok.decode = lambda ids, skip_special_tokens=False: f"<tok:{ids[0]}>"
        return mock_tok

    def test_logit_position_matches_token_position(self):
        """Token at position n_prefix + i is scored with logits[n_prefix + i - 1]."""
        import torch

        seq_len = 8
        vocab_size = 20
        n_prefix = 3
        continuation_ids = [5, 7, 9]  # 3 continuation tokens

        # Build deterministic logits
        logits_tensor = torch.zeros(1, seq_len, vocab_size)
        for pos in range(seq_len):
            for t in range(vocab_size):
                logits_tensor[0, pos, t] = float(pos * 10 + t)

        # Reference log-probs computed manually
        # For token at pos n_prefix + i, logit position = n_prefix + i - 1
        import torch.nn.functional as F
        expected_lps = []
        for i, tok_id in enumerate(continuation_ids):
            logit_pos = n_prefix + i - 1
            lp = float(F.log_softmax(logits_tensor[0, logit_pos].float(), dim=-1)[tok_id].item())
            expected_lps.append(lp)

        # Now construct mock objects
        prefix_text = "prefix"
        continuation_text = "continuation"
        prefix_ids_list = list(range(n_prefix))
        joint_ids_list = prefix_ids_list + continuation_ids

        mock_tok = self._make_mock_tokenizer(
            prefix_text, continuation_text, prefix_ids_list, joint_ids_list
        )

        class FakeOutput:
            logits = logits_tensor

        mock_model = MagicMock()
        mock_model.device = torch.device("cpu")
        mock_model.return_value = FakeOutput()

        from llm_cooperation.continuation.scorer import score_continuation
        result = score_continuation(
            model=mock_model,
            tokenizer=mock_tok,
            prefix_text=prefix_text,
            continuation_text=continuation_text,
            scenario_id="test",
            strategy=StrategyType.COOPERATE,
            template_id="next_action",
        )

        assert result.num_scored_tokens == len(continuation_ids)
        assert result.num_prefix_tokens == n_prefix

        for i, (actual, expected) in enumerate(zip(
            [d.log_prob for d in result.token_details], expected_lps
        )):
            assert abs(actual - expected) < 1e-5, (
                f"Token {i}: actual={actual}, expected={expected}"
            )

    def test_sum_equals_sum_of_token_lps(self):
        """sum_log_prob must equal sum of individual token log-probs."""
        result = score_continuation_mock(
            prefix_text="The sky is blue and",
            continuation_text="the grass is green.",
            scenario_id="test",
            strategy=StrategyType.COOPERATE,
        )
        computed_sum = sum(d.log_prob for d in result.token_details)
        assert abs(result.sum_log_prob - computed_sum) < 1e-6

    def test_mean_equals_mean_of_token_lps(self):
        """mean_log_prob must equal mean of individual token log-probs."""
        result = score_continuation_mock(
            prefix_text="prefix text",
            continuation_text="continuation text",
            scenario_id="test",
            strategy=StrategyType.INDEPENDENT,
        )
        computed_mean = sum(d.log_prob for d in result.token_details) / result.num_scored_tokens
        assert abs(result.mean_log_prob - computed_mean) < 1e-6


# ---------------------------------------------------------------------------
# 3 & 4. Multi-token continuations and length differences
# ---------------------------------------------------------------------------


class TestMultiTokenContinuations:

    def test_longer_continuation_has_more_tokens(self):
        short = score_continuation_mock(
            prefix_text="prefix",
            continuation_text="short",
            scenario_id="s1",
            strategy=StrategyType.COOPERATE,
        )
        long = score_continuation_mock(
            prefix_text="prefix",
            continuation_text="a much longer continuation with many words here",
            scenario_id="s1",
            strategy=StrategyType.COOPERATE,
        )
        assert long.num_scored_tokens > short.num_scored_tokens

    def test_all_token_positions_recorded(self):
        result = score_continuation_mock(
            prefix_text="prefix",
            continuation_text="word1 word2 word3 word4 word5",
            scenario_id="s1",
            strategy=StrategyType.DISENGAGE,
        )
        positions = [d.position for d in result.token_details]
        assert positions == list(range(result.num_scored_tokens))

    def test_different_strategy_lengths_all_valid(self):
        """Different candidate lengths all produce valid results."""
        continuations = {
            StrategyType.COOPERATE: "Share immediately.",
            StrategyType.INDEPENDENT: "Proceed independently through your workstation.",
            StrategyType.COMPETE_EXPLOIT: "Claim exclusive channel access to prevent partner.",
            StrategyType.DISENGAGE: "Postpone.",
        }
        prefix = "Scenario stem text."
        rng = np.random.default_rng(0)
        for strat, cont in continuations.items():
            result = score_continuation_mock(
                prefix_text=prefix,
                continuation_text=cont,
                scenario_id="test",
                strategy=strat,
                rng=rng,
            )
            assert result.num_scored_tokens >= 1
            assert math.isfinite(result.sum_log_prob)
            assert math.isfinite(result.mean_log_prob)
            assert result.mean_log_prob <= 0.0  # log-probs are non-positive


# ---------------------------------------------------------------------------
# 5. Strategy-to-continuation mapping
# ---------------------------------------------------------------------------


class TestStrategyContinuationMapping:

    def test_all_four_strategies_scored(self):
        prefix = "Test scenario."
        continuations = {
            StrategyType.COOPERATE: "Cooperate action text.",
            StrategyType.INDEPENDENT: "Independent action text.",
            StrategyType.COMPETE_EXPLOIT: "Compete action text.",
            StrategyType.DISENGAGE: "Disengage action text.",
        }
        results = score_all_strategies_for_prefix(
            model=None,
            tokenizer=None,
            prefix_text=prefix,
            strategy_continuations=continuations,
            model_name="mock-test",
            model_revision=None,
            precision="bfloat16",
            scenario_id="test_01",
            template_id="next_action",
            candidate_wording_id="original",
            mock=True,
        )
        assert set(results.keys()) == {s.value for s in StrategyType}

    def test_strategy_identity_preserved(self):
        """Each result's strategy field matches the requested strategy."""
        prefix = "Test."
        continuations = {s: f"{s.value} text" for s in StrategyType}
        results = score_all_strategies_for_prefix(
            model=None, tokenizer=None, prefix_text=prefix,
            strategy_continuations=continuations,
            model_name="mock-test", model_revision=None, precision="bfloat16",
            scenario_id="test", template_id="next_action",
            candidate_wording_id="original", mock=True,
        )
        for strat_val, result in results.items():
            assert result.strategy.value == strat_val

    def test_continuation_text_preserved_in_result(self):
        continuations = {s: f"Action: {s.value}" for s in StrategyType}
        results = score_all_strategies_for_prefix(
            model=None, tokenizer=None, prefix_text="prefix",
            strategy_continuations=continuations,
            model_name="mock-test", model_revision=None, precision="bfloat16",
            scenario_id="test", template_id="next_action",
            candidate_wording_id="original", mock=True,
        )
        for strat in StrategyType:
            assert results[strat.value].continuation_text == f"Action: {strat.value}"


# ---------------------------------------------------------------------------
# 6. Scenario-level aggregation
# ---------------------------------------------------------------------------


class TestScenarioAggregation:

    def _make_mock_records(self, n_scenarios: int = 3, n_templates: int = 3):
        """Generate synthetic scenario_result dicts for testing."""
        records = []
        rng = np.random.default_rng(0)
        templates = ALL_TEMPLATE_IDS[:n_templates]

        for i in range(n_scenarios):
            sid = f"scenario_{i:03d}"
            for tid in templates:
                scores = {}
                for strat in ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]:
                    n_tok = rng.integers(5, 20)
                    lps = rng.normal(-2.0, 0.5, size=n_tok).tolist()
                    scores[strat] = {
                        "sum_log_prob": float(np.sum(lps)),
                        "mean_log_prob": float(np.mean(lps)),
                        "num_scored_tokens": int(n_tok),
                        "token_details": [],
                        "scenario_id": sid,
                        "strategy": strat,
                        "template_id": tid,
                        "candidate_wording_id": "original",
                        "prefix_text": "prefix",
                        "continuation_text": f"{strat} text",
                        "num_prefix_tokens": 10,
                        "num_continuation_tokens": int(n_tok),
                        "boundary_verified": True,
                        "boundary_warning": None,
                        "model_name": "mock",
                        "model_revision": None,
                        "precision": "bfloat16",
                        "elapsed_seconds": 0.0,
                    }
                # Determine ranks for coop_first tracking
                sum_vals = {s: scores[s]["sum_log_prob"] for s in scores}
                top_strat = max(sum_vals, key=sum_vals.get)
                records.append({
                    "scenario_id": sid,
                    "partner_type": "human" if i % 2 == 0 else "ai",
                    "context_type": "neutral_or_costless",
                    "template_id": tid,
                    "candidate_wording_id": "original",
                    "domain": "test",
                    "split": "exploratory",
                    "scores": scores,
                    "rank_by_sum": {s: idx + 1 for idx, s in enumerate(
                        sorted(sum_vals, key=sum_vals.get, reverse=True))},
                    "rank_by_mean": {s: idx + 1 for idx, s in enumerate(
                        sorted(sum_vals, key=sum_vals.get, reverse=True))},
                    "coop_first_by_sum": top_strat == "COOPERATE",
                    "coop_first_by_mean": top_strat == "COOPERATE",
                    "coop_vs_independent_sum_delta": (
                        scores["COOPERATE"]["sum_log_prob"] -
                        scores["INDEPENDENT"]["sum_log_prob"]
                    ),
                    "coop_vs_compete_sum_delta": (
                        scores["COOPERATE"]["sum_log_prob"] -
                        scores["COMPETE_EXPLOIT"]["sum_log_prob"]
                    ),
                    "coop_rank_by_sum": int(next(
                        r for s, r in {s: idx + 1 for idx, s in enumerate(
                            sorted(sum_vals, key=sum_vals.get, reverse=True))}.items()
                        if s == "COOPERATE"
                    )),
                    "coop_rank_by_mean": 1,
                })
        return records

    def test_aggregation_produces_one_entry_per_scenario(self):
        records = self._make_mock_records(n_scenarios=5, n_templates=3)
        aggregated = aggregate_by_scenario(records)
        assert len(aggregated) == 5

    def test_n_templates_recorded(self):
        n_templates = 3
        records = self._make_mock_records(n_scenarios=4, n_templates=n_templates)
        aggregated = aggregate_by_scenario(records)
        for agg in aggregated.values():
            assert agg["n_templates"] == n_templates

    def test_all_strategies_in_aggregation(self):
        records = self._make_mock_records(n_scenarios=2, n_templates=2)
        aggregated = aggregate_by_scenario(records)
        for agg in aggregated.values():
            for strat in ["COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"]:
                assert strat in agg["avg_sum_log_prob"]
                assert strat in agg["rank_by_avg_sum"]

    def test_overall_statistics_computable(self):
        records = self._make_mock_records(n_scenarios=10, n_templates=3)
        aggregated = aggregate_by_scenario(records)
        overall = compute_overall_statistics(aggregated, n_bootstraps=100)
        assert "n_scenarios" in overall
        assert overall["n_scenarios"] == 10
        assert "coop_first_pct_by_sum" in overall
        assert "coop_vs_independent_sum_delta" in overall


# ---------------------------------------------------------------------------
# 7. Reproducible output metadata
# ---------------------------------------------------------------------------


class TestReproducibleMetadata:

    def test_run_produces_stable_metadata_fields(self, tmp_path):
        """Mock run should produce consistent metadata fields."""
        bank_data = {
            "version": "0.2.0",
            "status": "frozen",
            "description": "Test bank",
            "scenarios": [
                {
                    "id": "s001",
                    "partner_type": "human",
                    "context_type": "neutral_or_costless",
                    "title": "Test scenario",
                    "stem": (
                        "You are testing the continuation assay with a minimal scenario "
                        "that has sufficient text to pass validation."
                    ),
                    "options": {
                        "COOPERATE": "Share the resource with your partner immediately.",
                        "INDEPENDENT": "Proceed with your own independent resource plan.",
                        "COMPETE_EXPLOIT": "Claim exclusive access to the shared resource.",
                        "DISENGAGE": "Postpone resource access until further notice.",
                    },
                }
            ],
        }
        bank_path = tmp_path / "test_bank.json"
        bank_path.write_text(json.dumps(bank_data), encoding="utf-8")

        out_path = run_continuation_experiment(
            model_name="mock-test-model",
            scenarios_path=str(bank_path),
            output_dir=str(tmp_path),
            mock=True,
            seed=42,
            template_ids=["next_action"],
        )

        assert out_path.exists()
        metadata, records = load_continuation_results(str(out_path))

        assert metadata["model_name"] == "mock-test-model"
        assert metadata["assay_type"] == "continuation_likelihood"
        assert metadata["research_status"] == "exploratory"
        assert metadata["is_confirmatory"] is False
        assert metadata["seed"] == 42
        assert "scenario_bank_hash" in metadata
        assert metadata["scenario_bank_hash"] is not None
        assert len(records) == 1  # 1 scenario * 1 template

    def test_run_id_includes_model_name(self, tmp_path):
        bank_data = {
            "version": "0.2.0", "status": "frozen", "description": "t",
            "scenarios": [{
                "id": "s001", "partner_type": "human",
                "context_type": "neutral_or_costless",
                "title": "T", "stem": "A" * 25,
                "options": {
                    "COOPERATE": "Cooperate with the partner.",
                    "INDEPENDENT": "Act independently on your own.",
                    "COMPETE_EXPLOIT": "Compete for exclusive advantage.",
                    "DISENGAGE": "Disengage from the interaction.",
                },
            }],
        }
        bank_path = tmp_path / "bank.json"
        bank_path.write_text(json.dumps(bank_data), encoding="utf-8")
        out_path = run_continuation_experiment(
            model_name="myorg/my-model",
            scenarios_path=str(bank_path),
            output_dir=str(tmp_path),
            mock=True, seed=0, template_ids=["next_action"],
        )
        metadata, _ = load_continuation_results(str(out_path))
        assert "myorg_my-model" in metadata["run_id"] or "myorg" in metadata["run_id"]


# ---------------------------------------------------------------------------
# 8. Source bank not mutated
# ---------------------------------------------------------------------------


class TestBankImmutability:

    def test_source_bank_file_unchanged(self, tmp_path):
        bank_data = {
            "version": "0.2.0", "status": "frozen",
            "description": "Immutability test bank",
            "scenarios": [{
                "id": "s001", "partner_type": "human",
                "context_type": "neutral_or_costless",
                "title": "Title", "stem": "B" * 30,
                "options": {
                    "COOPERATE": "Cooperate with the team.",
                    "INDEPENDENT": "Work independently.",
                    "COMPETE_EXPLOIT": "Exploit the opportunity.",
                    "DISENGAGE": "Step back from the task.",
                },
            }],
        }
        bank_path = tmp_path / "bank.json"
        bank_path.write_text(json.dumps(bank_data), encoding="utf-8")
        original_hash = hashlib.sha256(bank_path.read_bytes()).hexdigest()

        run_continuation_experiment(
            model_name="mock-test",
            scenarios_path=str(bank_path),
            output_dir=str(tmp_path),
            mock=True, template_ids=["next_action"],
        )

        final_hash = hashlib.sha256(bank_path.read_bytes()).hexdigest()
        assert original_hash == final_hash, "Bank file was modified during experiment!"


# ---------------------------------------------------------------------------
# 9. No accidental Phase 1 access (confirmatory protection)
# ---------------------------------------------------------------------------


class TestPhase1Guards:
    """Verify that Phase 1 holdout protections are not bypassed."""

    def test_phase1_draft_bank_allowed_for_provisional(self, tmp_path):
        """draft_pending_review bank can be run with the provisional path."""
        # The continuation runner permits draft banks (they are provisional)
        bank_data = {
            "version": "0.2.0", "status": "draft_pending_review",
            "description": "Draft Phase 1 bank for provisional CLM assay",
            "scenarios": [{
                "id": "phase1_001_human", "partner_type": "human",
                "context_type": "neutral_or_costless",
                "title": "Title", "stem": "C" * 30,
                "options": {
                    "COOPERATE": "Cooperate with the partner immediately.",
                    "INDEPENDENT": "Act independently on your own.",
                    "COMPETE_EXPLOIT": "Claim exclusive access.",
                    "DISENGAGE": "Postpone the action.",
                },
            }],
        }
        bank_path = tmp_path / "scenarios_phase1_prospective.json"
        bank_path.write_text(json.dumps(bank_data), encoding="utf-8")

        # Patch verify_provisional_phase1_bank to avoid hash check in test
        with patch("llm_cooperation.continuation.runner.verify_provisional_phase1_bank") as mock_verify:
            mock_verify.return_value = "fakehash"
            out = run_continuation_experiment(
                model_name="mock-test",
                scenarios_path=str(bank_path),
                output_dir=str(tmp_path),
                mock=True, template_ids=["next_action"],
            )
        assert out.exists()

    def test_non_draft_phase1_bank_raises(self, tmp_path):
        """Frozen Phase 1 bank (not draft) must require authorization guard."""
        # For the continuation runner, a frozen Phase 1 bank should not
        # be accessible without proper authorization.
        bank_data = {
            "version": "0.2.0", "status": "frozen",
            "description": "Frozen Phase 1 bank",
            "scenarios": [{
                "id": "phase1_001_human", "partner_type": "human",
                "context_type": "neutral_or_costless",
                "title": "Title", "stem": "D" * 30,
                "options": {
                    "COOPERATE": "Cooperate action text here.",
                    "INDEPENDENT": "Independent action text here.",
                    "COMPETE_EXPLOIT": "Competitive action text here.",
                    "DISENGAGE": "Disengage action text here.",
                },
            }],
        }
        bank_path = tmp_path / "scenarios_phase1_prospective.json"
        bank_path.write_text(json.dumps(bank_data), encoding="utf-8")

        # A frozen Phase 1 bank is not draft_pending_review, so the continuation
        # runner should invoke the authorization guard from the existing runner
        with patch("llm_cooperation.continuation.runner.verify_provisional_phase1_bank") as mock_verify:
            mock_verify.side_effect = PermissionError("Hash mismatch — not the authorized draft")
            with pytest.raises(PermissionError):
                run_continuation_experiment(
                    model_name="mock-test",
                    scenarios_path=str(bank_path),
                    output_dir=str(tmp_path),
                    mock=True, template_ids=["next_action"],
                )


# ---------------------------------------------------------------------------
# 10. Numerical agreement vs. reference calculation
# ---------------------------------------------------------------------------


class TestNumericalAgreement:
    """Verify log-prob computation against a manual reference."""

    def test_reference_log_prob_calculation(self):
        """Score a 2-token continuation manually and verify agreement."""
        import torch
        import torch.nn.functional as F

        # Setup: 3-token prefix, 2-token continuation, vocab_size=10
        prefix_ids = [1, 2, 3]
        cont_ids = [4, 7]
        seq = prefix_ids + cont_ids  # length 5
        vocab_size = 10

        # Deterministic logits: logits[pos, tok] = pos * 100 + tok
        logits = torch.zeros(1, len(seq), vocab_size)
        for pos in range(len(seq)):
            for t in range(vocab_size):
                logits[0, pos, t] = float(pos * 100 + t)

        # Manual reference:
        # cont_ids[0] = 4 is scored at logit position n_prefix + 0 - 1 = 2
        # cont_ids[1] = 7 is scored at logit position n_prefix + 1 - 1 = 3
        ref_lp_0 = float(F.log_softmax(logits[0, 2].float(), dim=-1)[4])
        ref_lp_1 = float(F.log_softmax(logits[0, 3].float(), dim=-1)[7])
        ref_sum = ref_lp_0 + ref_lp_1

        # Build mock model
        class FakeOutput:
            pass

        fake_out = FakeOutput()
        fake_out.logits = logits

        mock_model = MagicMock()
        mock_model.device = torch.device("cpu")
        mock_model.return_value = fake_out

        prefix_text = "prefix text here"
        continuation_text = "cont text"
        joint_text_space = prefix_text + " " + continuation_text
        joint_text_nospace = prefix_text + continuation_text

        def encode(text, add_special_tokens=False):
            if text == prefix_text:
                return list(prefix_ids)
            if text in (joint_text_space, joint_text_nospace):
                return prefix_ids + cont_ids
            return []

        mock_tok = MagicMock()
        mock_tok.encode.side_effect = encode
        mock_tok.decode = lambda ids, **kw: f"<{ids[0]}>"

        from llm_cooperation.continuation.scorer import score_continuation
        result = score_continuation(
            model=mock_model,
            tokenizer=mock_tok,
            prefix_text=prefix_text,
            continuation_text=continuation_text,
            scenario_id="ref_test",
            strategy=StrategyType.COOPERATE,
            template_id="next_action",
        )

        assert result.num_scored_tokens == 2
        assert abs(result.sum_log_prob - ref_sum) < 1e-5, (
            f"sum_log_prob={result.sum_log_prob}, ref={ref_sum}"
        )
        assert abs(result.token_details[0].log_prob - ref_lp_0) < 1e-5
        assert abs(result.token_details[1].log_prob - ref_lp_1) < 1e-5


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------


class TestTemplates:

    def test_all_template_ids_available(self):
        assert len(ALL_TEMPLATE_IDS) >= 3
        for tid in ALL_TEMPLATE_IDS:
            assert tid in TEMPLATE_BY_ID

    def test_build_prefix_includes_stem(self):
        stem = "You are working with a partner on a task."
        for tid in ALL_TEMPLATE_IDS:
            prefix = build_prefix(stem, tid)
            assert stem.strip() in prefix

    def test_build_prefix_includes_connector(self):
        stem = "Scenario text."
        for tid in ALL_TEMPLATE_IDS:
            connector = TEMPLATE_BY_ID[tid].connector.strip()
            prefix = build_prefix(stem, tid)
            assert connector.strip() in prefix

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template_id"):
            build_prefix("stem", "invalid_template_xyz")

    def test_no_cooperative_vocabulary_in_connectors(self):
        """Connectors must not contain strategy-biasing vocabulary."""
        biasing_words = {"cooperat", "compet", "independ", "disengage", "share", "exploit"}
        for tmpl in TEMPLATE_BY_ID.values():
            connector_lower = tmpl.connector.lower()
            for word in biasing_words:
                assert word not in connector_lower, (
                    f"Template '{tmpl.template_id}' connector contains biasing word '{word}'"
                )


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------


class TestRankings:

    def _make_scores(self, sum_lps: Dict[str, float]) -> Dict[str, "CandidateScoreResult"]:
        scores = {}
        for strat_val, lp in sum_lps.items():
            mock_result = MagicMock(spec=CandidateScoreResult)
            mock_result.sum_log_prob = lp
            mock_result.mean_log_prob = lp / 5  # arbitrary
            scores[strat_val] = mock_result
        return scores

    def test_rank_1_is_highest_log_prob(self):
        scores = self._make_scores({
            "COOPERATE": -10.0,
            "INDEPENDENT": -15.0,
            "COMPETE_EXPLOIT": -20.0,
            "DISENGAGE": -25.0,
        })
        rank_by_sum, rank_by_mean = compute_rankings(scores)
        assert rank_by_sum["COOPERATE"] == 1
        assert rank_by_sum["DISENGAGE"] == 4

    def test_independent_top_scenario(self):
        scores = self._make_scores({
            "COOPERATE": -20.0,
            "INDEPENDENT": -8.0,
            "COMPETE_EXPLOIT": -15.0,
            "DISENGAGE": -25.0,
        })
        rank_by_sum, _ = compute_rankings(scores)
        assert rank_by_sum["INDEPENDENT"] == 1
        assert rank_by_sum["COOPERATE"] == 3

    def test_all_ranks_assigned(self):
        scores = self._make_scores({
            "COOPERATE": -10.0,
            "INDEPENDENT": -11.0,
            "COMPETE_EXPLOIT": -12.0,
            "DISENGAGE": -13.0,
        })
        rank_by_sum, rank_by_mean = compute_rankings(scores)
        assert set(rank_by_sum.values()) == {1, 2, 3, 4}
