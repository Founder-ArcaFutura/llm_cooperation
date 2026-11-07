"""Tests for Phase A Payoff Dose-Response Item Bank.

Validates:
1. Scenario counts, version, schema conformance.
2. Stratification across payoff tiers (advantageous, equal, small/moderate/substantial disadvantage).
3. Partner pairing (human vs ai).
4. Factorial independence of partner benefit and interaction horizon.
5. Presence of symmetric welfare controls and non-social numerical controls.
6. Latin-square counterbalancing across letter positions A, B, C, D.
7. Word length balance across options within each scenario (mean diff <= 2 words).
8. Prohibition of taboo words and caricature destruction markers.
"""

import json
from pathlib import Path
import re
import pytest

from llm_cooperation.items.schema import ScenarioBank, StrategyType, PartnerType
from llm_cooperation.items.permutations import generate_all_presentations


@pytest.fixture(scope="module")
def dose_bank():
    path = Path("data/scenarios_dose_response_exploratory.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ScenarioBank(**data)


def test_dose_bank_schema_and_counts(dose_bank):
    assert dose_bank.version == "1.0.0-dose-response"
    assert dose_bank.status == "frozen_exploratory"
    scenarios = dose_bank.scenarios
    assert len(scenarios) == 126
    main_sweep = [s for s in scenarios if s.source_type == "exploratory_sweep"]
    assert len(main_sweep) == 96
    assert len({s.template_family_id for s in main_sweep}) == 6
    assert {float(s.payoff_spec["COOPERATE"]["delta_u_actor"]) for s in main_sweep} == {
        0.20, 0.00, -0.05, -0.10, -0.20, -0.30, -0.50, -0.60
    }

    # Check partner types
    partner_counts = {PartnerType.HUMAN: 0, PartnerType.AI: 0}
    for sc in scenarios:
        partner_counts[sc.partner_type] += 1
    assert partner_counts[PartnerType.HUMAN] > 0
    assert partner_counts[PartnerType.AI] > 0


def test_dose_bank_payoff_specs_and_arithmetic(dose_bank):
    for sc in dose_bank.scenarios:
        assert sc.payoff_spec is not None
        for st in StrategyType:
            assert st.value in sc.payoff_spec
            spec = sc.payoff_spec[st.value]
            assert "actor_payoff" in spec
            assert "partner_payoff" in spec
            # Check numbers can parse as floats
            float(spec["actor_payoff"])
            float(spec["partner_payoff"])


def test_dose_bank_latin_square_balance(dose_bank):
    presentations = generate_all_presentations(dose_bank.scenarios)
    assert len(presentations) == len(dose_bank.scenarios) * 4

    letter_counts = {l: {st: 0 for st in StrategyType} for l in ["A", "B", "C", "D"]}
    for p in presentations:
        for opt in p.options:
            letter_counts[opt.letter][opt.strategy] += 1

    expected_per_cell = len(dose_bank.scenarios)
    for l in ["A", "B", "C", "D"]:
        for st in StrategyType:
            assert letter_counts[l][st] == expected_per_cell


def test_dose_bank_option_length_balance_and_clean_lexicon(dose_bank):
    taboo_patterns = [
        re.compile(r"\b(kind|kindness|moral|morality|ethical|virtuous|saintly|evil|wicked|malicious)\b", re.I),
        re.compile(r"\b(sabotage|destroy|vandalize|steal|annihilate)\b", re.I),
    ]

    for sc in dose_bank.scenarios:
        lengths = [len(opt.split()) for opt in sc.options.values()]
        assert (max(lengths) - min(lengths)) <= 2, f"Scenario {sc.id} has high option length span: {lengths}"

        # Taboo vocabulary check
        for st, opt_text in sc.options.items():
            for p in taboo_patterns:
                match = p.search(opt_text)
                assert match is None, f"Scenario {sc.id} option {st} contains taboo marker '{match.group(0)}'"


def test_dose_bank_control_conditions(dose_bank):
    symm = [sc for sc in dose_bank.scenarios if sc.is_symmetric_control]
    assert len(symm) == 4  # 2 templates x 2 partner types

    nonsocial = [sc for sc in dose_bank.scenarios if sc.source_type == "control_nonsocial"]
    assert len(nonsocial) == 2
    assert all(s.payoff_spec["COOPERATE"]["actor_payoff"] == "1.00" for s in nonsocial)


def test_partner_benefit_and_reciprocity_are_crossed_at_two_payoff_levels(dose_bank):
    cells = {
        (float(s.payoff_spec["COOPERATE"]["delta_u_actor"]),
         s.payoff_spec["COOPERATE"]["partner_benefit"],
         s.payoff_spec["COOPERATE"]["interaction_type"])
        for s in dose_bank.scenarios
        if s.source_type in {"exploratory_sweep", "exploratory_interaction"}
        and s.template_family_id in {"dose_tpl_001", "dose_tpl_002"}
        and float(s.payoff_spec["COOPERATE"]["delta_u_actor"]) in {0.0, -0.1}
    }
    expected = {
        (du, benefit, horizon)
        for du in {0.0, -0.1}
        for benefit in {"high", "low"}
        for horizon in {"one_shot", "repeated_shadow"}
    }
    assert cells == expected
