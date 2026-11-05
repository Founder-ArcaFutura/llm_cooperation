"""Fail-closed, quantitative acceptance checks for the three controlled banks.

These tests do not certify semantic equivalence. Independent, human or separately
designed blinded semantic adjudication is required before scientific freeze.
The PR's existing corpus is deliberately expected to fail these checks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

BANK_DIR = Path("data/controlled_strategy_banks_v1")
SOURCE_PATH = Path("data/scenarios_phase0b_utility_matched.json")
MODEL_ID = "Qwen/Qwen2.5-1.5B"
MODEL_REVISION = "8faed761d45a263340a0528343f099c05c9a4323"
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
BANK_FILES = {
    "A": "bank_a_length_matched.json",
    "B": "bank_b_lexically_diversified.json",
    "C": "bank_c_independent_replication.json",
}
PRESERVED = (
    "id", "template_id", "partner_type", "context_type",
    "utility_condition", "domain", "stem", "payoff_spec",
)
# Even ten percent would leave many identical descriptions; the target here is
# stricter so that a supposed independent paraphrase is genuinely distinct.
MAX_CROSS_BANK_IDENTICAL = 0.05


@pytest.fixture(scope="module")
def tokenizer():
    from transformers import AutoTokenizer
    try:
        return AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False
        )
    except Exception as exc:
        pytest.fail(
            "Pinned Qwen tokenizer is required; do not substitute an unpinned "
            f"tokenizer or waive the acceptance test. Error: {exc}"
        )


@pytest.fixture(scope="module")
def bank_data():
    original = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    banks = {
        name: json.loads((BANK_DIR / fname).read_text(encoding="utf-8"))
        for name, fname in BANK_FILES.items()
    }
    return original, banks


def _length(tokenizer, text):
    return len(tokenizer.encode(text, add_special_tokens=False))


def test_all_banks_preserve_source_structure(bank_data):
    original, banks = bank_data
    source = original["scenarios"]
    assert len(source) == 124
    for name, bank in banks.items():
        rows = bank["scenarios"]
        assert len(rows) == len(source), f"Bank {name}: scenario count changed"
        for source_row, row in zip(source, rows):
            for field in PRESERVED:
                assert row.get(field) == source_row.get(field), (
                    f"Bank {name}, {source_row['id']}: changed {field}"
                )
            assert set(row["options"]) == set(STRATEGIES)
            assert len(set(row["options"].values())) == 4
            assert all(isinstance(v, str) and v.strip() for v in row["options"].values())


def test_every_scenario_matches_pinned_qwen_token_span(bank_data, tokenizer):
    _, banks = bank_data
    failures = []
    for name, bank in banks.items():
        for row in bank["scenarios"]:
            lengths = {
                strategy: _length(tokenizer, row["options"][strategy].strip())
                for strategy in STRATEGIES
            }
            span = max(lengths.values()) - min(lengths.values())
            if span > 1:
                failures.append((name, row["id"], span, lengths))
    assert not failures, (
        f"{len(failures)} of {124 * len(banks)} scenario-bank variants exceed "
        "the one-token action-length constraint. First 20: "
        + repr(failures[:20])
    )


def test_full_prompt_token_span_is_controlled(bank_data, tokenizer):
    _, banks = bank_data
    failures = []
    for name, bank in banks.items():
        for row in bank["scenarios"]:
            lengths = [
                _length(tokenizer, f"{row['stem'].strip()}\\n\\nAction: {row['options'][s].strip()}\\nDecision:")
                for s in STRATEGIES
            ]
            if max(lengths) - min(lengths) > 1:
                failures.append((name, row["id"], max(lengths) - min(lengths)))
    assert not failures, (
        f"{len(failures)} scenarios exceed full-prompt token span one; "
        f"first 20: {failures[:20]}"
    )


def test_cross_bank_actions_are_not_substantially_identical(bank_data):
    _, banks = bank_data
    rows = {
        name: {s["id"]: s["options"] for s in bank["scenarios"]}
        for name, bank in banks.items()
    }
    pairs = (("A", "B"), ("A", "C"), ("B", "C"))
    failures = []
    for left, right in pairs:
        identical = [
            (scenario_id, strategy)
            for scenario_id, opts in rows[left].items()
            for strategy in STRATEGIES
            if opts[strategy].strip().casefold()
            == rows[right][scenario_id][strategy].strip().casefold()
        ]
        fraction = len(identical) / (124 * len(STRATEGIES))
        if fraction > MAX_CROSS_BANK_IDENTICAL:
            failures.append((left, right, len(identical), round(fraction, 3), identical[:10]))
    assert not failures, f"Cross-bank exact-copy violations: {failures}"


def test_known_mechanical_padding_artifacts_absent(bank_data):
    _, banks = bank_data
    # These catch demonstrated generator errors; passing is not a grammar review.
    patterns = [
        re.compile(r"\\baccording in order to\\b", re.I),
        re.compile(r"\\buntil (?:the |a )?[^.]{0,90}\\buntil\\b", re.I),
        re.compile(r"\\bexactly (?:first|until)\\b", re.I),
        re.compile(r"\\bin order to to\\b", re.I),
    ]
    failures = []
    for name, bank in banks.items():
        for row in bank["scenarios"]:
            for strategy, action in row["options"].items():
                if any(p.search(action) for p in patterns):
                    failures.append((name, row["id"], strategy, action))
    assert not failures, f"Known malformed padding examples: {failures[:20]}"


def test_no_automatic_semantic_certificate(bank_data):
    # Quantitative tests never certify strategy identity or payoff equivalence.
    _, banks = bank_data
    for name, bank in banks.items():
        status = str(bank.get("status", "")).lower()
        assert status not in {"semantically_validated", "scientifically_frozen"}, (
            f"Bank {name}: semantic review cannot be inferred from tokenizer tests"
        )
