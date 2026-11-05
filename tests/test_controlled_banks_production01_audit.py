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
    metrics, report_md = audit_production01(prod_dir, phase0b_path)
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


def test_repair_queue_partitioning(audit_results):
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
