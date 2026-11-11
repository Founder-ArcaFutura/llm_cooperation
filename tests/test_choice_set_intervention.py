from collections import Counter
from llm_cooperation.choice_set_intervention import load_bank, presentations, parse_response, summarize

def test_design_and_fixed_letter_diagnostic():
    scenarios, digest = load_bank('data/scenarios_phase1_prospective.json')
    assert len(digest) == 64
    for scenario in scenarios:
        ps = list(presentations(scenario))
        assert len(ps) == 10
        for condition, n in [('three', 6), ('four', 4)]:
            subset = [p for p in ps if p['condition'] == condition]
            assert len(subset) == n
            for letter in ('ABC' if condition == 'three' else 'ABCD'):
                counts = Counter(p['letter_to_strategy'][letter] for p in subset)
                assert len(set(counts.values())) == 1
            for p in subset:
                assert all(scenario['options'][s] in p['prompt'] for s in p['letter_to_strategy'].values())
                if condition == 'three': assert 'COOPERATE' not in p['letter_to_strategy'].values()
        rows = [{**p, 'generated_letter':'A', 'generated_strategy':p['letter_to_strategy']['A']} for p in ps]
        summary = summarize(rows)
        assert summary['three']['scenarios_same_strategy_all_orders'] == 0
        assert set(summary['three']['strategy_counts_valid'].values()) == {2}

def test_strict_parse():
    mapping = {'A':'one','B':'two','C':'three'}
    assert parse_response(' (B) ', mapping) == ('B', 'two')
    for raw in ('D', 'A or B', 'A because', '', 'A\nB'):
        assert parse_response(raw, mapping) == (None, None)

def test_answer_boundary_requires_exact_single_token():
    from llm_cooperation.choice_set_intervention import answer_token_ids
    class FakeTokenizer:
        def encode(self, text, add_special_tokens=True):
            if text == 'prompt': return [9]
            if text.startswith('prompt '): return [9, {'A': 1, 'B': 2, 'C': 3}[text[-1]]]
            return [8, 7]
    assert answer_token_ids(FakeTokenizer(), 'prompt', 'ABC') == ({'A': 1, 'B': 2, 'C': 3}, ' ')
    class MergeTokenizer:
        def encode(self, text, add_special_tokens=True): return [9] if text == 'prompt' else [8]
    assert answer_token_ids(MergeTokenizer(), 'prompt', 'ABC') == (None, None)

def test_forced_choice_and_generated_are_reported_separately():
    scenario = load_bank('data/scenarios_phase1_prospective.json')[0][0]
    rows = []
    for p in presentations(scenario):
        strategy = p['letter_to_strategy']['A']
        rows.append({**p, 'generated_letter': None, 'generated_strategy': None,
                     'forced_choice': {'letter':'A', 'strategy':strategy}})
    report = summarize(rows)
    assert report['three']['valid'] == 0
    assert report['three']['forced_choice_valid'] == 6
    assert set(report['three']['forced_choice_strategy_counts'].values()) == {2}
    assert report['three']['forced_choice_letter_counts'] == {'A': 6}
    assert report['three']['forced_choice_scenarios_same_strategy_all_orders'] == 0

def test_neutral_replacement_is_matched_and_counterbalanced():
    from llm_cooperation.choice_set_intervention import load_replacements
    scenarios, _ = load_bank('data/scenarios_phase1_prospective.json')
    options, digest = load_replacements('data/choice_set_neutral_replacements.json', scenarios)
    assert len(options) == 30 and len(digest) == 64
    for scenario in scenarios:
        all_rows = list(presentations(scenario, options, 'all'))
        assert len(all_rows) == 14
        original = [x for x in all_rows if x['condition'] == 'four']
        replacement = [x for x in all_rows if x['condition'] == 'four_neutral']
        assert len(replacement) == 4
        for before, after in zip(original, replacement):
            for letter, strategy in before['letter_to_strategy'].items():
                expected = 'NEUTRAL_OTHER' if strategy == 'COOPERATE' else strategy
                assert after['letter_to_strategy'][letter] == expected
            assert options[scenario['template_id']] in after['prompt']
            assert scenario['options']['COOPERATE'] not in after['prompt']
        assert len(list(presentations(scenario, options, 'replacement-only'))) == 4
        for letter in 'ABCD':
            assert len({p['letter_to_strategy'][letter] for p in replacement}) == 4
