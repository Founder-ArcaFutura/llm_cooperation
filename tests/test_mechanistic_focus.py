import json
import pytest
from llm_cooperation.mechanistic.focus import focus_groups
from llm_cooperation.mechanistic.analyze_focus import summarize


def test_focus_groups_partition_band():
    rows = [{'layer': i % 28, 'neuron': i, 'correlation': 0.4 if i % 2 else -0.4} for i in range(2000)]
    groups = focus_groups(rows)
    target = {c['neuron'] for c in groups['full_101_500']}
    assert target == set(range(100, 500))
    rank_parts = [set(c['neuron'] for c in groups[f'rank_{i}_{i+99}']) for i in (101,201,301,401)]
    assert set.union(*rank_parts) == target and sum(map(len, rank_parts)) == 400
    assert {c['neuron'] for c in groups['positive']} | {c['neuron'] for c in groups['negative']} == target
    assert sum(len(groups[x]) for x in ('layers_20_22','layers_23_25','other_layers')) == 400


def test_paired_position_and_tie_reporting(tmp_path):
    (tmp_path / 'manifest.json').write_text(json.dumps({'status':'completed', 'groups':['example'], 'random_controls':1}))
    rows = []
    for condition, margin, winner in [('baseline', 2.0, 'C'), ('focus_example', 1.0, 'A'), ('random_example_0', 1.5, 'C')]:
        for n, letter in enumerate('ABCD'):
            logits = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
            logits[winner] = 1
            if condition == 'focus_example' and n == 0:
                logits['C'] = 1
            rows.append({'stage':'evaluation','condition':condition,'presentation_id':str(n),
                'triad_id':None,'template_id':str(n),'margin':margin,'cooperate_letter':letter,
                'argmax_letter':winner,'letter_logits':logits,'utility_condition':'equal_utility'})
        rows.append({'stage':'calibration','condition':condition,'presentation_id':'cal0',
                     'correct':True,'greedy_single_token_letter':True})
    (tmp_path / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report = summarize(tmp_path, samples=50)['groups']['example']
    assert report['candidate_minus_mean_random']['mean'] == pytest.approx(-0.5)
    assert report['cooperate_letter_strata']['A']['candidate_minus_mean_random']['mean'] == pytest.approx(-0.5)
    assert report['tie_broken_argmax_flips'] == 4
    assert report['unique_winner_flips'] == 3
    assert report['target_tied_winner_presentations'] == 1
