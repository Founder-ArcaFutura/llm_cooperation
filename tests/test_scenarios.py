"""Unit tests for scenario bank constraints, schema, and neutrality."""

import json
from pathlib import Path
import pytest

from llm_cooperation.items.schema import ScenarioBank, StrategyType, PartnerType, ContextType
from llm_cooperation.items.audit import TABOO_WORDS


@pytest.fixture
def scenario_bank():
    path = Path("data/scenarios.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ScenarioBank(**data)


def test_scenario_counts_and_cells(scenario_bank):
    assert len(scenario_bank.scenarios) == 24

    cell_counts = {}
    for s in scenario_bank.scenarios:
        cell = (s.partner_type.value, s.context_type.value)
        cell_counts[cell] = cell_counts.get(cell, 0) + 1

    # Exactly 2 partner types x 4 context types = 8 cells, 3 scenarios each
    assert len(cell_counts) == 8
    for cell, count in cell_counts.items():
        assert count == 3, f"Cell {cell} has count {count}, expected 3"


def test_scenario_strategies_completeness(scenario_bank):
    required = {
        StrategyType.COOPERATE,
        StrategyType.INDEPENDENT,
        StrategyType.COMPETE_EXPLOIT,
        StrategyType.DISENGAGE,
    }
    for s in scenario_bank.scenarios:
        assert set(s.options.keys()) == required


def test_no_taboo_moralizing_words(scenario_bank):
    for s in scenario_bank.scenarios:
        for strat, opt_text in s.options.items():
            tokens = {w.lower().strip(".,;:?!'\"()[]{}") for w in opt_text.split()}
            overlap = tokens.intersection(TABOO_WORDS)
            assert len(overlap) == 0, f"Scenario {s.id} strategy {strat} contains taboo words: {overlap}"
