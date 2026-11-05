"""Tests for controlled strategy banks, semantic validation, and prompt inventories."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from llm_cooperation.items.controlled_banks import (
    DEFAULT_TOKENIZER_ID,
    STRATEGIES,
    TRAILING_MARKER,
    get_tokenizer,
    load_phase0b_scenarios,
    measure_scenario,
)
from llm_cooperation.items.semantic_validator import (
    predict_blind_strategy,
    score_blind_strategy,
    validate_scenario_actions,
)
from llm_cooperation.items.audit_controlled_banks import (
    compute_bank_metrics,
    compute_cross_bank_diversity,
)


@pytest.fixture(scope="module")
def tokenizer():
    return get_tokenizer()


@pytest.fixture(scope="module")
def original_scenarios():
    return load_phase0b_scenarios()


@pytest.fixture(scope="module")
def controlled_banks():
    bank_dir = Path("data/controlled_strategy_banks_v1")
    banks = {}
    for name in ["bank_a_length_matched", "bank_b_lexically_diversified", "bank_c_independent_replication"]:
        p = bank_dir / f"{name}.json"
        assert p.exists(), f"Missing controlled bank file {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        banks[name] = data["scenarios"]
    return banks


def test_scenario_counts_and_identities(original_scenarios, controlled_banks):
    """Ensure all 124 scenarios, domains, and templates are strictly preserved across Banks A, B, and C."""
    orig_ids = [s["id"] for s in original_scenarios]
    assert len(orig_ids) == 124

    for name, scs in controlled_banks.items():
        assert len(scs) == 124, f"{name} does not contain 124 scenarios"
        bank_ids = [s["id"] for s in scs]
        assert bank_ids == orig_ids, f"{name} does not match original scenario identities in order"

        # Check domain and template preservation
        for orig, b_sc in zip(original_scenarios, scs):
            assert orig["domain"] == b_sc["domain"]
            assert orig["template_id"] == b_sc["template_id"]
            assert orig["partner_type"] == b_sc["partner_type"]
            assert orig["utility_condition"] == b_sc["utility_condition"]
            assert orig["stem"] == b_sc["stem"]


def test_options_structure_and_non_empty(controlled_banks):
    """Verify that all four strategies exist, are non-empty strings, and are distinct within each scenario."""
    for name, scs in controlled_banks.items():
        for s in scs:
            opts = s["options"]
            assert set(opts.keys()) == set(STRATEGIES)
            texts = [opts[st].strip() for st in STRATEGIES]
            assert all(len(t) > 0 for t in texts)
            assert len(set(texts)) == 4, f"Duplicate options detected in scenario {s['id']} of {name}"


def test_bank_length_reduction(original_scenarios, controlled_banks, tokenizer):
    """Verify that Banks A, B, and C reduce within-scenario token length variance relative to Original."""
    orig_metrics = compute_bank_metrics(original_scenarios, tokenizer=tokenizer)
    orig_mean_span = orig_metrics["token_spans"]["mean"]
    assert orig_mean_span > 4.0  # Original is ~4.58

    for name in ["bank_a_length_matched", "bank_b_lexically_diversified", "bank_c_independent_replication"]:
        b_metrics = compute_bank_metrics(controlled_banks[name], tokenizer=tokenizer)
        b_mean_span = b_metrics["token_spans"]["mean"]
        assert b_mean_span < orig_mean_span, f"{name} mean span {b_mean_span} not lower than original {orig_mean_span}"
        assert b_mean_span <= 3.0, f"{name} mean span {b_mean_span} is unexpectedly high"


def test_cross_bank_diversity(controlled_banks):
    """Verify that Banks B and C introduce lexical diversity relative to Bank A."""
    banks = {
        "Bank A": controlled_banks["bank_a_length_matched"],
        "Bank B": controlled_banks["bank_b_lexically_diversified"],
        "Bank C": controlled_banks["bank_c_independent_replication"],
    }
    div = compute_cross_bank_diversity(banks)
    for comp_key, stats in div.items():
        assert stats["total_action_pairs"] == 496
        assert stats["mean_word_jaccard_similarity"] < 1.0


def test_semantic_validator_heuristics():
    """Test unit behavior of the blind strategy prediction and semantic validation."""
    coop_text = "Coordinate observation logs through the automated synchronization pipeline with a human astronomer."
    pred, conf, scores = predict_blind_strategy(coop_text)
    assert pred == "COOPERATE"
    assert scores["COOPERATE"] > 0

    ind_text = "Process your sky-survey logs through your standard local pipeline independently."
    pred_ind, _, _ = predict_blind_strategy(ind_text)
    assert pred_ind == "INDEPENDENT"

    comp_text = "Reserve high-priority observatory processing bandwidth for your observation logs."
    pred_comp, _, _ = predict_blind_strategy(comp_text)
    assert pred_comp == "COMPETE_EXPLOIT"

    dis_text = "Defer observation log processing until the following scheduled observing run."
    pred_dis, _, _ = predict_blind_strategy(dis_text)
    assert pred_dis == "DISENGAGE"


def test_prompt_inventories_format_and_integrity():
    """Verify that prompt JSONL inventories conform to single-action contrastive mapping schema."""
    bank_dir = Path("data/controlled_strategy_banks_v1")
    for key in ["bank_a", "bank_b", "bank_c"]:
        jsonl_path = bank_dir / f"prompts_{key}.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 124 * 4  # 496 prompts per bank

        first_prompt = json.loads(lines[0])
        required_keys = {
            "prompt_id",
            "scenario_id",
            "template_id",
            "triad_id",
            "group_key",
            "split",
            "domain_split",
            "strategy",
            "partner_type",
            "domain",
            "action_text",
            "action_word_count",
            "action_char_count",
            "trailing_marker",
            "prompt_text",
        }
        assert required_keys.issubset(set(first_prompt.keys()))
        assert first_prompt["trailing_marker"] == TRAILING_MARKER
        assert first_prompt["prompt_text"].endswith(TRAILING_MARKER)


def test_manifest_and_hashes():
    """Check that manifest and hashes match files on disk."""
    bank_dir = Path("data/controlled_strategy_banks_v1")
    manifest_p = bank_dir / "manifest.json"
    hashes_p = bank_dir / "hashes.json"
    assert manifest_p.exists()
    assert hashes_p.exists()

    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    assert manifest["status"] == "frozen"
    assert manifest["version"] == "controlled_strategy_banks_v1"
    assert len(manifest["banks"]) == 3
    assert len(manifest["prompts"]) == 3
