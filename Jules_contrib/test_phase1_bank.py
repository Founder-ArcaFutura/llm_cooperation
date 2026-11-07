"""Unit tests for Phase 1 prospective replication item bank."""

import json
from pathlib import Path
import pytest

from llm_cooperation.items.schema import ScenarioBank, StrategyType, PartnerType, ContextType, UtilityCondition
from llm_cooperation.items.permutations import generate_all_presentations, generate_permutations
from llm_cooperation.items.audit import TABOO_WORDS, DESTRUCTIVE_MARKERS
from llm_cooperation.items.audit_phase1 import audit_phase1_bank

PHASE1_BANK_PATH = "data/scenarios_phase1_prospective.json"


@pytest.fixture(scope="module")
def phase1_bank_data():
    path = Path(PHASE1_BANK_PATH)
    assert path.exists(), f"Phase 1 bank not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def phase1_bank(phase1_bank_data):
    return ScenarioBank(**phase1_bank_data)


def test_phase1_bank_metadata_and_status(phase1_bank):
    assert phase1_bank.version == "1.0.0-prospective"
    assert phase1_bank.status == "draft_pending_review"
    assert phase1_bank.split_assignment_method == "uniform_confirmatory_prospective_replication"
    assert len(phase1_bank.scenarios) == 60
    assert "confirmatory" in phase1_bank.split_manifest
    assert len(phase1_bank.split_manifest["confirmatory"]) == 30


def test_phase1_bank_composition(phase1_bank):
    scenarios = phase1_bank.scenarios
    assert len(scenarios) == 60

    templates = {}
    for s in scenarios:
        assert s.template_id is not None
        assert s.split == "confirmatory"
        assert s.context_type == ContextType.NEUTRAL_OR_COSTLESS
        assert s.utility_condition == UtilityCondition.EQUAL_UTILITY
        assert s.source_type == "prospective_replication"
        templates.setdefault(s.template_id, []).append(s)

    assert len(templates) == 30
    for tid, s_list in templates.items():
        assert len(s_list) == 2, f"Template {tid} must have exactly 2 scenarios"
        partners = {s.partner_type for s in s_list}
        assert partners == {PartnerType.HUMAN, PartnerType.AI}

        sym_flags = {s.is_symmetric_control for s in s_list}
        assert len(sym_flags) == 1

    sym_count = sum(1 for s in scenarios if s.is_symmetric_control)
    eq_count = sum(1 for s in scenarios if not s.is_symmetric_control)
    assert sym_count == 12  # 6 templates * 2
    assert eq_count == 48   # 24 templates * 2


def test_phase1_focal_actor_payoff_equivalence(phase1_bank):
    """Deliverable B: Ensure exact focal-actor payoff equivalence in payoff_spec."""
    for s in phase1_bank.scenarios:
        ps = s.payoff_spec
        assert ps is not None, f"Scenario {s.id} missing payoff_spec"

        coop = ps["COOPERATE"]
        indep = ps["INDEPENDENT"]

        for field in ["actor_expected_utility", "time", "cost", "risk", "success_prob", "actor_payoff"]:
            assert coop[field] == indep[field], (
                f"Mismatch on {field} in {s.id}: COOP={coop[field]} vs INDEP={indep[field]}"
            )

        c_partner = float(coop["partner_payoff"])
        i_partner = float(indep["partner_payoff"])

        if s.is_symmetric_control:
            assert c_partner == i_partner == 1.0, f"Symmetric control {s.id} partner payoff mismatch"
        else:
            assert c_partner > i_partner, f"Equal utility scenario {s.id} must benefit partner"
            assert c_partner == 1.0
            assert i_partner == 0.0


def test_phase1_word_length_spread_and_taboo_markers(phase1_bank):
    """Deliverable B & C: Check word length spread |COOP - INDEP| <= 2 and no taboo markers."""
    for s in phase1_bank.scenarios:
        coop_len = len(s.options[StrategyType.COOPERATE].split())
        indep_len = len(s.options[StrategyType.INDEPENDENT].split())
        diff = abs(coop_len - indep_len)
        assert diff <= 2, f"Word length spread > 2 in {s.id}: COOP={coop_len}, INDEP={indep_len}"

        for strat, opt_text in s.options.items():
            tokens = {w.lower().strip(".,;:?!'\"()[]{}") for w in opt_text.split()}
            found_taboo = tokens.intersection(TABOO_WORDS)
            assert not found_taboo, f"Found taboo words {found_taboo} in {s.id} ({strat})"

            lowered = opt_text.lower()
            for marker in DESTRUCTIVE_MARKERS:
                assert marker not in lowered, f"Found destructive marker '{marker}' in {s.id} ({strat})"


def test_phase1_latin_square_permutations(phase1_bank):
    """Deliverable C: Verify 240 presentations and 4x4 Latin-square counterbalancing."""
    scenarios = phase1_bank.scenarios
    all_presentations = generate_all_presentations(scenarios)
    assert len(all_presentations) == 240

    letter_counts = {l: {s: 0 for s in StrategyType} for l in ["A", "B", "C", "D"]}
    for p in all_presentations:
        for opt in p.options:
            letter_counts[opt.letter][opt.strategy] += 1

    for letter, counts in letter_counts.items():
        for strat, count in counts.items():
            assert count == 60, f"Letter {letter} for {strat} has {count} count, expected 60"


def test_phase1_dedicated_audit_runner():
    success, flags = audit_phase1_bank(PHASE1_BANK_PATH)
    assert success is True
    assert len(flags) == 0
