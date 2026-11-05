"""Summarize paired held-out intervention effects; bootstrap independent groups."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(path, samples=2000, seed=29):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['status'] != 'completed':
        raise ValueError('Run is incomplete; inspect preserved observations and manifest')
    rows = [json.loads(x) for x in (path / 'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    output = {'status': 'exploratory', 'effects': {}, 'calibration': {}, 'baseline_contrasts': {}}
    eval_rows = [r for r in rows if r['stage'] == 'evaluation']
    base = {r['presentation_id']: r for r in eval_rows if r['condition'] == 'baseline'}
    rng = np.random.default_rng(seed)
    changes = {}
    for condition in ('candidate_zero', 'random_zero'):
        other = {r['presentation_id']: r for r in eval_rows if r['condition'] == condition}
        if set(base) != set(other) or not base:
            raise ValueError('Missing or unmatched evaluation presentations')
        grouped = {}
        for key, b in base.items():
            # Triad variants and paired partners remain in the same resampling group.
            group = b['triad_id'] or b['template_id']
            grouped.setdefault(group, []).append(other[key]['margin'] - b['margin'])
        changes[condition] = {k: float(np.mean(v)) for k, v in grouped.items()}
        vals = np.array(list(changes[condition].values()))
        draws = rng.choice(vals, (samples, len(vals)), replace=True).mean(axis=1)
        output['effects'][condition] = {'mean_margin_change': float(vals.mean()),
            'bootstrap_95_percentile': [float(x) for x in np.quantile(draws, [0.025, 0.975])],
            'independent_groups': len(vals), 'presentations': len(base),
            'cooperate_argmax_rate_change': float(np.mean([int(other[k]['argmax_letter'] == other[k]['cooperate_letter']) - int(b['argmax_letter'] == b['cooperate_letter']) for k, b in base.items()]))}
    diff = np.array([changes['candidate_zero'][k] - changes['random_zero'][k] for k in changes['candidate_zero']])
    draws = rng.choice(diff, (samples, len(diff)), replace=True).mean(axis=1)
    output['effects']['candidate_minus_random'] = {'mean_margin_change_difference': float(diff.mean()),
        'bootstrap_95_percentile': [float(x) for x in np.quantile(draws, [0.025, 0.975])]}
    for condition in ('baseline', 'candidate_zero', 'random_zero'):
        subset = [r for r in rows if r['stage'] == 'calibration' and r['condition'] == condition]
        if not subset:
            raise ValueError('Missing calibration observations')
        output['calibration'][condition] = {'n': len(subset), 'forced_choice_accuracy': float(np.mean([r['correct'] for r in subset])),
            'greedy_next_token_letter_rate': float(np.mean([r['greedy_single_token_letter'] for r in subset]))}
    # Descriptive contrasts. The models and bank were not selected blind.
    for key in ('partner_type', 'utility_condition'):
        for value in sorted({r[key] for r in base.values()}):
            subset = [r for r in base.values() if r[key] == value]
            groups = {}
            for r in subset:
                groups.setdefault(r['triad_id'] or r['template_id'], []).append(r['margin'])
            output['baseline_contrasts'][f'{key}:{value}'] = {'group_mean_margin': float(np.mean([np.mean(v) for v in groups.values()])), 'groups': len(groups)}
    (path / 'summary.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_directory')
    args = parser.parse_args()
    print(json.dumps(summarize(args.run_directory), indent=2))
