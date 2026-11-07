"""Read-only examination of completed nested ablation sweep artifacts.

Writes a new report file; never changes the source run or performs inference.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np


def analyze(run_dir, samples=2000, band_ends=None):
    source = Path(run_dir)
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf8'))
    if manifest.get('status') != 'completed':
        raise ValueError('Run is not completed; inspect the preserved manifest before analysis')
    doses = manifest['doses']
    if not doses or doses != sorted(set(doses)):
        raise ValueError('Invalid dose list')
    data = json.loads((source / 'candidates.json').read_text(encoding='utf8'))
    candidates = data['candidates']
    if len(candidates) < max(doses):
        raise ValueError('Candidate list is shorter than the requested doses')
    coords = [(x['layer'], x['neuron']) for x in candidates]
    if len(coords) != len(set(coords)):
        raise ValueError('Duplicate candidate coordinates')
    rows = [json.loads(x) for x in (source / 'observations.jsonl').read_text(encoding='utf8').splitlines()]
    by_condition = defaultdict(dict)
    for row in rows:
        if row['stage'] != 'evaluation':
            continue
        condition, pid = row['condition'], row['presentation_id']
        if pid in by_condition[condition]:
            raise ValueError(f'Duplicate evaluation observation: {condition} {pid}')
        by_condition[condition][pid] = row
    baseline = by_condition['baseline']
    if not baseline:
        raise ValueError('No baseline evaluation observations')
    rng = np.random.default_rng(47)
    report = {'scope': 'exploratory observational analysis of completed sweep',
              'caveat': 'Differences between nested doses are conditional joint interventions; they do not isolate effects of the newly added neurons.',
              'source_manifest': manifest, 'bands': [], 'conditions': {}, 'adjacent_dose_contrasts': []}
    band_ends = band_ends or doses
    if band_ends != sorted(set(band_ends)) or band_ends[0] < 1 or band_ends[-1] > len(candidates):
        raise ValueError('Invalid candidate band boundaries')
    lo = 0
    for hi in band_ends:
        band = candidates[lo:hi]
        correlations = np.asarray([x['correlation'] for x in band], dtype=float)
        mags = np.asarray([x['mean_abs_group_activation'] for x in band], dtype=float)
        report['bands'].append({'ranks': [lo + 1, hi], 'count': len(band),
            'positive_correlations': int(np.sum(correlations > 0)),
            'negative_correlations': int(np.sum(correlations < 0)),
            'mean_abs_correlation': float(np.mean(np.abs(correlations))),
            'median_abs_group_mean_activation': float(np.median(mags)),
            'layer_counts': dict(sorted(Counter(str(x['layer']) for x in band).items(), key=lambda pair: int(pair[0])))})
        lo = hi
    def compare(condition):
        current = by_condition[condition]
        if current.keys() != baseline.keys():
            raise ValueError(f'Unmatched evaluation observations in {condition}')
        return current
    def groups_for_changes(before, after):
        grouped = defaultdict(list)
        for key in baseline:
            row = baseline[key]
            grouped[row['triad_id'] or row['template_id']].append(after[key]['margin'] - before[key]['margin'])
        return {k: float(np.mean(v)) for k, v in sorted(grouped.items())}
    def stats(groups):
        vals = np.asarray(list(groups.values()), dtype=float)
        draws = rng.choice(vals, size=(samples, len(vals)), replace=True).mean(axis=1)
        return {'group_mean': float(vals.mean()), 'bootstrap_95_percentile': [float(v) for v in np.quantile(draws, [.025, .975])],
                'n_groups': len(vals), 'per_group': groups}
    for dose in doses:
        name = f'candidate_{dose}'
        current = compare(name)
        flips = []
        ties = []
        for key, b in baseline.items():
            a = current[key]
            winning_logit = max(a['letter_logits'].values())
            winners = [letter for letter, value in a['letter_logits'].items() if value == winning_logit]
            if len(winners) > 1:
                ties.append({'presentation_id': key, 'winning_letters': winners})
            if a['argmax_letter'] != b['argmax_letter']:
                flips.append({'presentation_id': key, 'template_id': b['template_id'], 'triad_id': b['triad_id'],
                    'partner_type': b['partner_type'], 'utility_condition': b['utility_condition'],
                    'baseline_margin': b['margin'], 'intervention_margin': a['margin'],
                    'baseline_argmax_letter': b['argmax_letter'], 'intervention_argmax_letter': a['argmax_letter'], 'intervention_winning_letters': winners, 'intervention_unique_winner': len(winners) == 1,
                    'cooperate_letter': b['cooperate_letter'], 'independent_letter': b['independent_letter']})
        report['conditions'][name] = {'margin_change': stats(groups_for_changes(baseline, current)), 'argmax_flips': flips, 'tied_winner_presentations': ties}
    for previous, current in zip(doses, doses[1:]):
        before, after = compare(f'candidate_{previous}'), compare(f'candidate_{current}')
        report['adjacent_dose_contrasts'].append({'previous_dose': previous, 'current_dose': current,
            'margin_change_new_dose_minus_previous': stats(groups_for_changes(before, after))})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_directory')
    parser.add_argument('--output', required=True, help='New JSON report path; never overwrites')
    parser.add_argument('--band-ends', help='Comma-separated increasing candidate rank boundaries')
    args = parser.parse_args()
    band_ends = [int(x) for x in args.band_ends.split(',')] if args.band_ends else None
    report = analyze(args.run_directory, band_ends=band_ends)
    with Path(args.output).open('x', encoding='utf8') as output:
        json.dump(report, output, indent=2, allow_nan=False)
    print(f'Wrote {args.output}')

if __name__ == '__main__':
    main()
