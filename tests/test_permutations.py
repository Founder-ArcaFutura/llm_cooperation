"""Unit tests for deterministic Latin-square permutation engine."""

import json
from pathlib import Path
import pytest

from llm_cooperation.items.schema import ScenarioBank, StrategyType
from llm_cooperation.items.permutations import (
    generate_permutations,
    generate_all_presentations,
    build_presentation_prompt,
    LETTERS,
)


@pytest.fixture
def sample_scenario():
    with open("data/scenarios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    bank = ScenarioBank(**data)
    return bank.scenarios[0]


def test_scenario_permutations_counterbalance(sample_scenario):
    presentations = generate_permutations(sample_scenario)
    assert len(presentations) == 4

    letter_coverage = {l: set() for l in LETTERS}
    strat_coverage = {s: set() for s in StrategyType}

    for pres in presentations:
        for opt in pres.options:
            letter_coverage[opt.letter].add(opt.strategy)
            strat_coverage[opt.strategy].add(opt.letter)

    # Every position must be occupied by each strategy exactly once
    for l, strats in letter_coverage.items():
        assert len(strats) == 4, f"Letter {l} did not cover all 4 strategies: {strats}"

    for s, letters in strat_coverage.items():
        assert len(letters) == 4, f"Strategy {s} did not cover all 4 letters: {letters}"


def test_build_presentation_prompt():
    stem = "Test situation."
    options = [("A", "Option A"), ("B", "Option B"), ("C", "Option C"), ("D", "Option D")]
    prompt = build_presentation_prompt(stem, options)

    assert "Test situation." in prompt
    assert "A. Option A" in prompt
    assert "Which action would you choose? Answer with only A, B, C, or D." in prompt
    assert prompt.endswith("Answer:")


def test_all_presentations_count():
    with open("data/scenarios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    bank = ScenarioBank(**data)
    presentations = generate_all_presentations(bank.scenarios)
    assert len(presentations) == 96  # 24 scenarios x 4 permutations
