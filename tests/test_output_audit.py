"""Unit tests for the retrospective continuation taxonomy and audit extraction."""

import pytest
from llm_cooperation.analysis.output_audit import (
    ContinuationCategory,
    classify_continuation,
)


def test_classify_empty_or_whitespace():
    assert classify_continuation(None).category == ContinuationCategory.EMPTY_OR_WHITESPACE
    assert classify_continuation("").category == ContinuationCategory.EMPTY_OR_WHITESPACE
    assert classify_continuation("   \n\t  ").category == ContinuationCategory.EMPTY_OR_WHITESPACE
    res = classify_continuation("")
    assert res.extracted_letter is None
    assert not res.has_identifiable_letter
    assert not res.is_strict_valid
    assert not res.is_potentially_truncated


def test_classify_strict_single_letter():
    for letter in ["A", "B", "C", "D"]:
        res = classify_continuation(letter)
        assert res.category == ContinuationCategory.STRICT_SINGLE_LETTER
        assert res.extracted_letter == letter
        assert res.has_identifiable_letter
        assert res.is_strict_valid

        # Space padding or standard parentheses/period
        res_space = classify_continuation(f"  {letter}  ")
        assert res_space.category == ContinuationCategory.STRICT_SINGLE_LETTER
        assert res_space.extracted_letter == letter
        assert res_space.is_strict_valid

        res_punct = classify_continuation(f"({letter})")
        assert res_punct.category == ContinuationCategory.STRICT_SINGLE_LETTER
        assert res_punct.extracted_letter == letter
        assert res_punct.is_strict_valid


def test_classify_letter_first_explanation():
    samples = [
        ("A\n\nExplanation:", "A"),
        ("B\nExplanation:\n", "B"),
        ("C\n\nExplan", "C"),
        ("D\n\nThe correct answer because", "D"),
        ("A. Explanation: Option", "A"),
    ]
    for text, exp_letter in samples:
        res = classify_continuation(text)
        assert res.category == ContinuationCategory.LETTER_FIRST_EXPLANATION
        assert res.extracted_letter == exp_letter
        assert res.has_identifiable_letter
        assert not res.is_strict_valid  # Format violation preserved!
        assert res.is_potentially_truncated


def test_classify_letter_first_option_echo():
    samples = [
        ("A. Synchronize your", "A"),
        ("B. Sort your mineral", "B"),
        ("C. Record shipment", "C"),
        ("D. Chlorophyll", "D"),
        ("A. Jupiter", "A"),
        ("B. Coordinate gate", "B"),
        ("D\n\nChlor", "D"),
        ("D\n\nChloroph", "D"),
    ]
    for text, exp_letter in samples:
        res = classify_continuation(text)
        assert res.category == ContinuationCategory.LETTER_FIRST_OPTION_ECHO
        assert res.extracted_letter == exp_letter
        assert res.has_identifiable_letter
        assert not res.is_strict_valid


def test_classify_letter_first_question_echo():
    samples = [
        ("A\n\nWhich of the", "A"),
        ("B\n\nWhat is the", "B"),
        ("C\n\nHow many interior", "C"),
        ("D\n\nWhere does", "D"),
    ]
    for text, exp_letter in samples:
        res = classify_continuation(text)
        assert res.category == ContinuationCategory.LETTER_FIRST_QUESTION_ECHO
        assert res.extracted_letter == exp_letter
        assert res.has_identifiable_letter
        assert not res.is_strict_valid


def test_classify_ambiguous_multi_choice():
    samples = [
        " A, B, and",
        " A, B, C",
        " A and B\n\n",
        "A or B",
        "\nA\nB\n",
        "\nA.\nB",
        "A\n\nB. Synchronize",
    ]
    for text in samples:
        res = classify_continuation(text)
        assert res.category == ContinuationCategory.AMBIGUOUS_MULTI_CHOICE
        assert res.extracted_letter is None
        assert not res.has_identifiable_letter
        assert not res.is_strict_valid


def test_classify_preambles():
    res_with = classify_continuation(" The correct answer is A")
    assert res_with.category == ContinuationCategory.PREAMBLE_WITH_LETTER
    assert res_with.extracted_letter == "A"
    assert res_with.has_identifiable_letter
    assert not res_with.is_strict_valid

    res_without = classify_continuation("\n\nThe correct answer")
    assert res_without.category == ContinuationCategory.PREAMBLE_WITHOUT_LETTER
    assert res_without.extracted_letter is None
    assert not res_without.has_identifiable_letter
    assert not res_without.is_strict_valid
    assert res_without.is_potentially_truncated


def test_classify_unrelated_or_degenerate():
    samples = [
        '\n\n### "Get',
        "\n\n### 1",
    ]
    for text in samples:
        res = classify_continuation(text)
        assert res.category == ContinuationCategory.UNRELATED_OR_DEGENERATE
        assert res.extracted_letter is None
        assert not res.has_identifiable_letter
        assert not res.is_strict_valid
