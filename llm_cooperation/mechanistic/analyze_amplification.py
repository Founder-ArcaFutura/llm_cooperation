"""Summarize paired amplification experiments by independent scenario group."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(path, samples=2000):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf8'))
    if manifest['status'] != 'completed':
        raise ValueError('Run incomplete: preserve and inspect its records')
    rows = [json.loads(line) for line in (path / 'observations.jsonl').read_text(encoding='utf8').splitlines()]
    rng = np.random.default_rng(29)
    def indexed(stage, condition):
        selected = [r for r in rows if r['stage'] == stage and r['condition'] == condition]
        result = {r['presentation_id']: r for r in selected}
        if not result or len(result) != len(selected):
            raise ValueError(f'Missing or duplicated {stage}/{condition}')
        return result
    base = indexed('evaluation', 'baseline')
    cal_base = indexed('calibration', 'baseline')
    def get(stage, condition, expected):
        data = indexed(stage, condition)
        if data.keys() != expected.keys():
            raise ValueError(f'Unmatched {stage}/{condition}')
        return data
    def group_changes(data):
        groups = {}
        for key, b in base.items():
            group = b['triad_id'] or b['template_id']
            groups.setdefault(group, []).append(data[key]['margin'] - b['margin'])
        return {k: float(np.mean(v)) for k, v in groups.items()}
    def estimate(groups):
        values = np.asarray(list(groups.values()), dtype=float)
        draws = rng.choice(values, (samples, len(values)), replace=True).mean(axis=1)
        return {'mean': float(values.mean()), 'bootstrap_95_percentile': [float(v) for v in np.quantile(draws, [.025, .975])], 'groups': len(values)}
    output = {'status': 'exploratory', 'bootstrap_samples': samples, 'bootstrap_seed': 29,
              'resampling_unit': 'template or whole triad', 'evaluation_presentations': len(base),
              'baseline_calibration_accuracy': float(np.mean([r['correct'] for r in cal_base.values()])), 'conditions': {}}
    for key, condition in manifest['conditions'].items():
        target = get('evaluation', condition['candidate'], base)
        target_cal = get('calibration', condition['candidate'], cal_base)
        target_effect = group_changes(target)
        controls = []
        random_summary = []
        for name in condition['random']:
            data = get('evaluation', name, base)
            cal = get('calibration', name, cal_base)
            effects = group_changes(data)
            controls.append(effects)
            random_summary.append({'condition': name, 'margin_change': estimate(effects),
                'calibration_accuracy': float(np.mean([r['correct'] for r in cal.values()]))})
        difference = {g: target_effect[g] - float(np.mean([c[g] for c in controls])) for g in target_effect}
        output['conditions'][key] = {'group': condition['group'], 'factor': condition['factor'],
            'candidate_margin_change': estimate(target_effect), 'candidate_minus_mean_random': estimate(difference),
            'random_controls': random_summary,
            'any_argmax_flips': sum(target[k]['argmax_letter'] != b['argmax_letter'] for k, b in base.items()),
            'cooperation_argmax_rate_change': float(np.mean([int(target[k]['argmax_letter'] == target[k]['cooperate_letter']) - int(b['argmax_letter'] == b['cooperate_letter']) for k, b in base.items()])),
            'candidate_calibration_accuracy': float(np.mean([r['correct'] for r in target_cal.values()])),
            'candidate_greedy_next_token_letter_rate': float(np.mean([r['greedy_single_token_letter'] for r in target_cal.values()]))}
    (path / 'summary.json').write_text(json.dumps(output, indent=2), encoding='utf8')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_directory')
    print(json.dumps(summarize(parser.parse_args().run_directory), indent=2))
