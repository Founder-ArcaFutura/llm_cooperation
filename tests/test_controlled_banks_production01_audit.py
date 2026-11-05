"""Tests for the offline scientific audit of production01 controlled strategy banks."""
import json
from pathlib import Path

import pytest

from scripts.audit_controlled_production01 import (
    audit_production01,
    jaccard_similarity,
    tokenize_words,
    get_ngrams,
    BAD_PATTERNS,
)


@pytest.fixture(scope="module")
def audit_results():
    prod_dir = "research/controlled_rewrites/production01"
    phase0b_path = "data/scenarios_phase0b_utility_matched.json"
    metrics, report_md = audit_production01(prod_dir, phase0b_path, verify_tokenizer=True)
    return metrics, report_md


def test_provenance_and_accounting(audit_results):
    metrics, _ = audit_results
    prov = metrics["provenance"]
    assert prov["total_records_analyzed"] == 372
    assert prov["provenance_issues_count"] == 0
    recon = prov["reconciliation"]
    assert recon["manifest_matches_records"] is True
    assert recon["records_accepted"] == {"A": 30, "B": 21, "C": 21}
    assert recon["records_unresolved"] == {"A": 94, "B": 103, "C": 103}
    assert recon["unresolved_file_length"] == 300
    assert prov["candidate_file_counts"] == {"A": 30, "B": 21, "C": 21}

    # Complete triads verification: exactly 8 complete triads exist
    assert recon["complete_triad_count"] == 8
    assert recon["complete_triad_indices"] == [2, 3, 28, 29, 35, 65, 72, 114]

    # Retokenization verification against authoritative pinned tokenizer
    assert prov["independent_tokenizer_retokenization_verified"] is True
    assert prov["independent_retokenization_mismatches"] == 0


def test_token_matching_distributions(audit_results):
    metrics, _ = audit_results
    tm = metrics["token_matching"]
    cov = tm["coverage_by_threshold"]

    # Span <= 1 must strictly match the 72 accepted count
    assert cov[1]["both_spans_count"] == 72
    assert cov[1]["by_bank"] == {"A": 30, "B": 21, "C": 21}

    # Spans must monotonically non-decrease
    counts = [cov[t]["both_spans_count"] for t in [1, 2, 3, 4, 5]]
    assert counts == sorted(counts)
    assert counts[0] == 72
    assert counts[1] == 157
    assert counts[2] == 240


def test_lexical_diversity_metrics(audit_results):
    metrics, _ = audit_results
    lex = metrics["lexical_diversity"]

    # Cross-bank exact duplicates across 496 option comparisons
    assert lex["cross_bank_exact_duplicate_actions"]["A_vs_B"] == 2
    assert lex["cross_bank_exact_duplicate_actions"]["A_vs_C"] == 10
    assert lex["cross_bank_exact_duplicate_actions"]["B_vs_C"] == 38

    # Cross-bank mean Jaccard shows moderate overlap reflecting domain noun sharing
    for pair, sim in lex["cross_bank_jaccard_mean"].items():
        assert 0.3 < sim < 0.65, f"Unexpected cross-bank similarity for {pair}: {sim}"


def test_semantic_flags_counts_and_triads(audit_results):
    metrics, _ = audit_results
    sem = metrics["semantic_triage"]
    p_cues = sem["partner_cue_flags_summary"]
    p_shifts = sem["polarity_shift_flags_summary"]

    # 103 partner cue loss flags (72 human, 31 AI)
    assert p_cues["human"] == 72
    assert p_cues["ai"] == 31
    assert p_cues["human"] + p_cues["ai"] == 103

    # 182 polarity shift flags (179 introduced, 3 removed)
    assert p_shifts["introduced"] == 179
    assert p_shifts["removed"] == 3
    assert p_shifts["introduced"] + p_shifts["removed"] == 182

    # 42 of 72 accepted variants carry semantic flags
    assert sem["accepted_variants_with_semantic_flags"] == 42


def test_repair_queue_partitioning_incorporates_collisions(audit_results):
    metrics, _ = audit_results
    q_sum = metrics["repair_queue_summary"]
    queue = metrics["repair_queue"]

    # Verify mutually exclusive partition summing to 372
    total_queued = (
        q_sum["automatic_pass_count"]
        + q_sum["priority_1_count"]
        + q_sum["priority_2_count"]
        + q_sum["priority_3_count"]
    )
    assert total_queued == 372
    assert q_sum["automatic_pass_count"] == 72
    assert len(queue["automatic_pass_pending_human_review"]) == 72
    assert len(queue["priority_1_near_miss_targeted_repair"]) == q_sum["priority_1_count"]
    assert len(queue["priority_2_moderate_repair"]) == q_sum["priority_2_count"]
    assert len(queue["priority_3_substantial_reconstruction"]) == q_sum["priority_3_count"]

    # Verify that Priority 1 items have NO cross-bank collisions
    for item in queue["priority_1_near_miss_targeted_repair"]:
        assert len(item["computed_cross_bank_collisions"]) == 0, f"Item {item['record']} in Priority 1 has collisions!"

    # Verify scenario 014_C (index 14, Bank C) is in Priority 3 due to cross-bank collision with Bank A
    p3_records = {item["record"]: item for item in queue["priority_3_substantial_reconstruction"]}
    assert "014_C" in p3_records
    assert any("exact duplicate of Bank A" in col for col in p3_records["014_C"]["computed_cross_bank_collisions"])


def test_helper_nlp_functions():
    toks = tokenize_words("Deliver observations safely, without delay!")
    assert toks == ["deliver", "observations", "safely", "without", "delay"]

    ngrams = get_ngrams(toks, 3)
    assert len(ngrams) == 3
    assert ("deliver", "observations", "safely") in ngrams

    j_sim = jaccard_similarity("run local pipeline", "run local pipeline alone")
    assert 0.7 < j_sim < 1.0

    # Check bad padding regexes
    assert any(p.search("deliver packages according in order to schedule") for p in BAD_PATTERNS)
    assert any(p.search("wait exactly first") for p in BAD_PATTERNS)
    assert any(p.search("until tonight until tomorrow") for p in BAD_PATTERNS)
    assert not any(p.search("normal sentence describing collaboration") for p in BAD_PATTERNS)
