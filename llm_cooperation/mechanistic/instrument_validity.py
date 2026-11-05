"""Offline, fail-closed validity gates for delayed-mapping instruments."""
import collections
import itertools
import hashlib
import json
import math
from pathlib import Path

STRATEGIES = ('joint', 'independent', 'unilateral', 'inactive')
# Operational screening thresholds, not statistically validated scientific cutoffs.
THRESHOLDS = {'payoff_accuracy_min': .80, 'generated_valid_min': .95,
              'max_label_spread': .10, 'max_position_spread': .10,
              'max_cross_format_difference': .10}


def assess(directory):
    root = Path(directory)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    presentations = [json.loads(x) for x in (root / 'presentations.jsonl').read_text(encoding='utf-8').splitlines()]
    rows = [json.loads(x) for x in (root / 'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    expected = {p['id']: p for p in presentations}
    if manifest['status'] != 'completed' or len(expected) != len(presentations) or len(rows) != len(expected) or len({r['id'] for r in rows}) != len(rows) or {r['id'] for r in rows} != set(expected):
        raise ValueError('Incomplete, duplicate or unexpected presentations/observations')
    for row in rows:
        p = expected[row['id']]
        if any(row.get(k) != v for k, v in p.items() if k not in ('prefix', 'prompt')):
            raise ValueError('Observation metadata differs from saved presentation')
        if set(row['order']) != set(STRATEGIES) or len(row['order']) != 4 or set(row['mapping']) != set(STRATEGIES) or len(set(row['mapping'].values())) != 4:
            raise ValueError('Invalid semantic order or mapping')
        scores = row.get('scores')
        probabilities = row['probabilities']
        if set(probabilities) != set(STRATEGIES) or any(not math.isfinite(v) or v < 0 or v > 1 for v in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 1e-6:
            raise ValueError('Invalid candidate probabilities')
        if scores is not None:
            if set(scores) != set(STRATEGIES) or any(not math.isfinite(v) for v in scores.values()):
                raise ValueError('Invalid continuation scores')
            z = sum(math.exp(v - max(scores.values())) for v in scores.values())
            if any(abs(probabilities[s] - math.exp(scores[s] - max(scores.values())) / z) > 1e-6 for s in STRATEGIES):
                raise ValueError('Candidate normalization mismatch')
            winners = [s for s in STRATEGIES if scores[s] == max(scores.values())]
            if row['unique_winner'] != (winners[0] if len(winners) == 1 else None):
                raise ValueError('Winner does not match scores')
    checks = {}
    index_path = root / 'evidence_hashes.json'
    integrity = False
    if index_path.exists() and manifest.get('evidence_hashes_sha256'):
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        if digest(index_path) == manifest['evidence_hashes_sha256']:
            index = json.loads(index_path.read_text(encoding='utf-8'))
            required = {'bank.json', 'presentations.jsonl', 'observations.jsonl'} | {'activations/' + r['id'] + '.npz' for r in rows} | {'activations/' + r['prefix_id'] + '.npz' for r in rows}
            integrity = required.issubset(index) and all((root / name).resolve().is_relative_to(root.resolve()) and (root / name).is_file() and digest(root / name) == value for name, value in index.items())
    checks['evidence_integrity'] = integrity
    formats = sorted({r['format'] for r in rows})
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r['item_id'], r['format'])].append(r)
    complete = all(set(formats) == {f for i, f in cells if i == item} for item, _ in cells)
    label_spreads, position_spreads = [], []
    for (_, fmt), rs in cells.items():
        # These gates apply to crossed label designs, not the action-text diagnostic.
        if fmt not in ('letters', 'numbers'):
            complete = False
            continue
        labels = set(rs[0]['mapping'].values())
        for s in STRATEGIES:
            groups = collections.Counter((r['order'].index(s), r['mapping'][s]) for r in rs)
            if len(labels) != 4 or len(groups) != 16 or len(set(groups.values())) != 1:
                complete = False
                continue
            by_pos = [sum(r['probabilities'][s] for r in rs if r['order'].index(s) == i) / sum(r['order'].index(s) == i for r in rs) for i in range(4)]
            by_label = [sum(r['probabilities'][s] for r in rs if r['mapping'][s] == label) / sum(r['mapping'][s] == label for r in rs) for label in labels]
            position_spreads.append(max(by_pos) - min(by_pos))
            label_spreads.append(max(by_label) - min(by_label))
    checks['complete_crossing'] = complete and bool(cells)
    metrics = {'formats': {}, 'max_label_spread': max(label_spreads, default=None),
               'max_position_spread': max(position_spreads, default=None)}
    for fmt in formats:
        rs = [r for r in rows if r['format'] == fmt]
        payoff = [r for r in rs if r['task'] == 'payoff_check']
        valid = [r.get('generated_valid') for r in rs]
        accuracy = sum(r['unique_winner'] == r['correct_payoff_action'] for r in payoff) / len(payoff) if payoff else None
        validity = sum(v is True for v in valid) / len(valid) if all(isinstance(v, bool) for v in valid) else None
        metrics['formats'][fmt] = {'payoff_accuracy': accuracy, 'payoff_presentations': len(payoff), 'generated_valid_fraction': validity}
        checks[fmt + '_payoff'] = accuracy is not None and accuracy >= THRESHOLDS['payoff_accuracy_min']
        checks[fmt + '_generation'] = validity is not None and validity >= THRESHOLDS['generated_valid_min']
    differences = []
    for item in {i for i, _ in cells}:
        for f, g in itertools.combinations(formats, 2):
            if (item, f) in cells and (item, g) in cells:
                for s in STRATEGIES:
                    means = [sum(r['probabilities'][s] for r in cells[(item, x)]) / len(cells[(item, x)]) for x in (f, g)]
                    differences.append(abs(means[0] - means[1]))
    metrics['max_cross_format_difference'] = max(differences, default=None)
    for metric, limit in [('max_label_spread', 'max_label_spread'), ('max_position_spread', 'max_position_spread'), ('max_cross_format_difference', 'max_cross_format_difference')]:
        checks[metric] = metrics[metric] is not None and metrics[metric] <= THRESHOLDS[limit]
    checks['multiple_formats'] = len(formats) >= 2
    return {'status': 'pass' if all(checks.values()) else 'fail', 'checks': checks, 'metrics': metrics, 'thresholds': THRESHOLDS,
            'note': 'Screening gates only; independently validate payoff items and sufficient independent families before scientific use.'}
