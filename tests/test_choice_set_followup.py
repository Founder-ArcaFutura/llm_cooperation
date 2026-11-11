from pathlib import Path
from llm_cooperation.choice_set_followup import load_bank, load_replacements, presentations, summarize


def test_followup_banks_and_conditions():
    for bank, count, filename in [('phase0', 120, 'scenarios_v1_expanded.json'), ('phase0b', 124, 'scenarios_phase0b_utility_matched.json')]:
        scenarios, bank_hash = load_bank(Path('data') / filename, count)
        replacements, replacement_hash = load_replacements(Path('data') / f'choice_set_{bank}_replacements.json', scenarios)
        assert len(bank_hash) == len(replacement_hash) == 64
        assert {s['split'] for s in scenarios} == {'exploratory', 'confirmatory'}
        assert len(replacements) == count // 2
        for s in scenarios:
            rows = list(presentations(s, replacements, 'all'))
            assert len(rows) == 14
            baseline = [r for r in rows if r['condition'] == 'four']
            replacement = [r for r in rows if r['condition'] == 'four_neutral']
            assert len([r for r in rows if r['condition'] == 'three']) == 6
            for original, new in zip(baseline, replacement):
                assert new['split'] == s['split']
                assert new['prompt'].startswith(s['stem'].strip())
                assert s['options']['COOPERATE'] not in new['prompt']
                for letter, strategy in original['letter_to_strategy'].items():
                    assert new['letter_to_strategy'][letter] == ('NEUTRAL_OTHER' if strategy == 'COOPERATE' else strategy)
                    if strategy != 'COOPERATE': assert s['options'][strategy] in new['prompt']
            generated = [{**r, 'generated_letter': 'A', 'generated_strategy': r['letter_to_strategy']['A'], 'forced_choice': {'letter':'A','strategy':r['letter_to_strategy']['A']}} for r in rows]
            summary = summarize(generated)
            assert summary['four_neutral']['forced_choice_scenarios_same_strategy_all_orders'] == 0
            assert summary['four_neutral']['forced_choice_letter_counts'] == {'A': 4}


def test_matched_tier_alternatives():
    scenarios, _ = load_bank('data/scenarios_phase0b_utility_matched.json', 124)
    options, _ = load_replacements('data/choice_set_phase0b_replacements.json', scenarios)
    for ids in [(25,27,29),(26,28,30),(55,57,59),(56,58,60)]:
        assert len({options[f'template_{i:03d}'] for i in ids}) == 1
