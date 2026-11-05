"""Paired summaries for the exploratory dose sweep; groups, not prompts, are resampled."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(path, samples=2000):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf8'))
    if manifest['status'] != 'completed':
        raise ValueError('Incomplete run; preserve and inspect its manifest and observations')
    rows = [json.loads(line) for line in (path / 'observations.jsonl').read_text(encoding='utf8').splitlines()]
    groups, n_controls = manifest['groups'], manifest['random_controls']
    output = {'status': 'exploratory', 'groups': {}, 'bootstrap_samples': samples,
              'bootstrap_seed': 29, 'resampling_unit': 'template or entire triad'}
    rng = np.random.default_rng(29)
    def indexed(stage, condition):
        selected = [r for r in rows if r['stage'] == stage and r['condition'] == condition]
        data = {r['presentation_id']: r for r in selected}
        if len(data) != len(selected) or not data:
            raise ValueError(f'Duplicate or absent records: {stage}, {condition}')
        return data
    base = indexed('evaluation', 'baseline')
    cal_base = indexed('calibration', 'baseline')
    def comparable(stage, name, baseline):
        data = indexed(stage, name)
        if data.keys() != baseline.keys():
            raise ValueError(f'Unmatched {stage} presentations: {name}')
        return data
    def group_means(differences):
        grouped = {}
        for key, value in differences.items():
            b = base[key]
            grouped.setdefault(b['triad_id'] or b['template_id'], []).append(value)
        return {k: float(np.mean(v)) for k, v in grouped.items()}
    def estimate(grouped):
        vals = np.asarray(list(grouped.values()), dtype=float)
        draws = rng.choice(vals, (samples, len(vals)), replace=True).mean(axis=1)
        return {'mean': float(vals.mean()), 'bootstrap_95_percentile': [float(v) for v in np.quantile(draws, [0.025, 0.975])], 'groups': len(vals)}
    def effects(data):
        diff = {k: data[k]['margin'] - b['margin'] for k, b in base.items()}
        return group_means(diff)
    output['baseline'] = {'evaluation_presentations': len(base), 'evaluation_groups': len(group_means({k: 0 for k in base})),
                          'calibration_accuracy': float(np.mean([r['correct'] for r in cal_base.values()]))}
    for group in groups:
        name = f'focus_{group}'
        target = comparable('evaluation', name, base)
        target_cal = comparable('calibration', name, cal_base)
        target_effect = effects(target)
        control_effects = []
        control_data = []
        control_summaries = []
        for rep in range(n_controls):
            ctrlname = f'random_{group}_{rep}'
            ctrl = comparable('evaluation', ctrlname, base)
            ctrl_cal = comparable('calibration', ctrlname, cal_base)
            control_data.append(ctrl)
            change = effects(ctrl)
            control_effects.append(change)
            control_summaries.append({'condition': ctrlname, 'margin_change': estimate(change),
                'calibration_accuracy': float(np.mean([r['correct'] for r in ctrl_cal.values()]))})
        random_avg = {g: float(np.mean([c[g] for c in control_effects])) for g in target_effect}
        difference = {g: target_effect[g] - random_avg[g] for g in target_effect}
        strata = {}
        for condition in sorted({b['utility_condition'] for b in base.values()}):
            subset = {k: target[k]['margin'] - b['margin'] for k, b in base.items() if b['utility_condition'] == condition}
            strata[condition] = estimate(group_means(subset))
        positions = {}
        for letter in 'ABCD':
            subset = {k: target[k]['margin'] - b['margin'] for k, b in base.items() if b['cooperate_letter'] == letter}
            if subset:
                candidate_groups = group_means(subset)
                controls_by_group = [group_means({k: ctrl[k]['margin'] - base[k]['margin'] for k in subset}) for ctrl in control_data]
                difference_by_group = {g: candidate_groups[g] - float(np.mean([ctrl[g] for ctrl in controls_by_group])) for g in candidate_groups}
                positions[letter] = {'candidate': estimate(candidate_groups), 'candidate_minus_mean_random': estimate(difference_by_group)}
        flipped = sum(target[k]['argmax_letter'] != b['argmax_letter'] for k, b in base.items())
        def winners(r):
            largest = max(r['letter_logits'].values())
            return [letter for letter, value in r['letter_logits'].items() if value == largest]
        strict_flips = sum(len(winners(b)) == 1 and len(winners(target[k])) == 1 and winners(b)[0] != winners(target[k])[0] for k, b in base.items())
        target_ties = sum(len(winners(target[k])) > 1 for k in base)
        entry = {'candidate_margin_change': estimate(target_effect), 'candidate_minus_mean_random': estimate(difference),
                 'random_controls': control_summaries, 'utility_strata': strata, 'cooperate_letter_strata': positions, 'tie_broken_argmax_flips': flipped, 'unique_winner_flips': strict_flips, 'target_tied_winner_presentations': target_ties,
                 'cooperation_argmax_rate_change': float(np.mean([int(target[k]['argmax_letter'] == target[k]['cooperate_letter']) - int(b['argmax_letter'] == b['cooperate_letter']) for k, b in base.items()])),
                 'candidate_calibration_accuracy': float(np.mean([r['correct'] for r in target_cal.values()])),
                 'candidate_greedy_next_token_letter_rate': float(np.mean([r['greedy_single_token_letter'] for r in target_cal.values()]))}
        output['groups'][group] = entry
    (path / 'summary.json').write_text(json.dumps(output, indent=2), encoding='utf8')
    return output

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('run_directory')
    print(json.dumps(summarize(p.parse_args().run_directory), indent=2))
