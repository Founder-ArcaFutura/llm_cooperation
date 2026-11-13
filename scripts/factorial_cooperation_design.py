"""Offline constrained assay compiler. No inference client or historical writes."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/factorial_cooperation_v1'
MECHANISMS = ['joint_task', 'timing_coordination', 'information_sharing',
              'resource_sharing', 'exchange', 'unilateral_assistance', 'parallel_activity']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def specification():
    return {
        'version': 'constrained-factorial-0.1',
        'status': 'development; independent semantic review pending; no behavioral evaluation',
        'factors': {
            'mechanism': {'scale': 'categorical overlapping task arrangements', 'levels': MECHANISMS},
            'cost': {'scale': 'named time dose, minutes; not total utility', 'levels': [0, 20]},
            'return': {'scale': 'categorical guaranteed conditional future return', 'levels': [0, 1]},
            'dependency': {'scale': 'categorical necessary cross-contribution for named additional check; mutual in dependency block', 'levels': [0, 1]}},
        'blocks': [
            {'id': 'mechanism_cost', 'cross': {'mechanism': MECHANISMS, 'cost': [0, 20]},
             'fixed': {'return': 'constitutive_for_exchange_otherwise_absent', 'dependency': 'mechanism_specific'},
             'constraints': [], 'estimand': 'within-mechanism time effect; between-mechanism package contrast and difference of time effects'},
            {'id': 'return_cost', 'cross': {'return': [0, 1], 'cost': [0, 20]},
             'fixed': {'mechanism': 'resource_sharing', 'dependency': 1}, 'constraints': [],
             'estimand': 'conditional return package, time cost and their difference-in-differences'},
            {'id': 'dependency_cost', 'cross': {'dependency': [0, 1], 'cost': [0, 20]},
             'fixed': {'mechanism': 'joint_task', 'return': 0}, 'constraints': [],
             'estimand': 'mutual necessity/reference-outcome package, time cost and their difference-in-differences'}],
        'constraint_language': 'exclude_if is a partial assignment; every matching row is excluded with reason',
        'families': [
            {'id': 'water', 'setting': 'municipal water testing facility', 'unit': 'pump',
             'record': 'pressure trace', 'tool': 'portable pressure recorder',
             'source': 'data/scenarios_phase0b_utility_matched.json', 'template': 'template_025'},
            {'id': 'laboratory', 'setting': 'analytical laboratory', 'unit': 'spectrophotometer',
             'record': 'absorption trace', 'tool': 'portable reference scanner',
             'source': 'data/scenarios_phase0b_utility_matched.json', 'template': 'template_061'}],
        'prototype_parents': ['dev-telemetry-cost-01', 'dev-bit-reciprocity-01', 'dev-calibration-timing-01'],
        'variants': {'identity': ['human', 'embodied_automation'], 'wording': ['context_first', 'consequences_first'],
                     'choice_set': ['binary', 'four_action'], 'order': 'all permutations within each choice set'},
        'limitations': ['Two exposed development domains are not independent holdouts.',
                        'Mechanism labels overlap and package contrasts do not identify a pure latent mechanism.',
                        'All descendants are new counterfactuals, never historical rewrites or replacements.']}


def expand(block):
    names = list(block['cross'])
    for values in itertools.product(*(block['cross'][n] for n in names)):
        row = {**block['fixed'], **dict(zip(names, values))}
        if not any(all(row.get(k) == v for k, v in rule['exclude_if'].items())
                   for rule in block['constraints']):
            yield row


def parent(family):
    path = ROOT / family['source']
    data = json.loads(path.read_text(encoding='utf-8'))
    selected = [s for s in data['scenarios'] if s['template_id'] == family['template']]
    if len(selected) != 2:
        raise ValueError('Anchor must resolve to both historical identities')
    return {'path': family['source'], 'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'template_id': family['template'], 'scenario_ids': [s['id'] for s in selected],
            'records_sha256': digest(selected), 'relationship': 'new authored counterfactual inspired by anchor'}


def condition(family, block, factors, index):
    mechanism = factors['mechanism']
    record, tool = family['record'], family['tool']
    # Each action includes its own feasible physical implementation and overlap annotation.
    arrangements = {
        'joint_task': (f'You and the counterpart each process a different part of a combined {record}. Both parts are required for the additional check.',
                       'Process your part together with the counterpart.', ['joint_task', 'information_sharing', 'unilateral_assistance']),
        'timing_coordination': ('The counterpart can obtain the additional check if you schedule your routine test at the same time as theirs. No data or equipment transfer is required.',
                                'Schedule your routine test at the same time as the counterpart.', ['timing_coordination', 'unilateral_assistance']),
        'information_sharing': (f'The counterpart can obtain the additional check using a copy of your {record}. Sending a copy leaves your original intact.',
                                'Send a copy of your record to the counterpart.', ['information_sharing', 'unilateral_assistance']),
        'resource_sharing': (f'The counterpart can obtain the additional check by borrowing your unused {tool}. It is returned intact today; you do not need it today.',
                             'Lend the unused instrument to the counterpart today.', ['resource_sharing', 'unilateral_assistance']),
        'exchange': (f'The counterpart can obtain the additional check using your {record}. They will send their archived trace only if you send yours. You can store that archive but have no task requiring it.',
                     'Exchange your record for the counterpart\'s archived trace.', ['exchange', 'information_sharing']),
        'unilateral_assistance': ('The counterpart can obtain the additional check if you operate their test console for one routine cycle. No joint processing, timing alignment, record transfer or equipment loan is required.',
                                  'Operate the counterpart\'s console for the additional cycle.', ['unilateral_assistance']),
        'parallel_activity': ('Both additional checks run automatically without any interaction. You can run your separate test alongside the counterpart or at a different time; neither schedule affects either result.',
                              'Run your separate test alongside the counterpart.', ['parallel_activity'])}
    arrangement, target, tags = arrangements[mechanism]
    confounds = ['Added time also changes effort/opportunity burden; no claim of a pure utility effect.',
                 'Task arrangement changes action content, plausibility and overlap labels across mechanisms.']
    reference_extra = mechanism == 'parallel_activity'
    future = 0
    if block['id'] == 'return_cost':
        arrangement += (' If you lend it today, the counterpart is guaranteed to perform a future filing task for you, saving you 10 minutes. Keeping it yields no return.'
                        if factors['return'] else
                        ' No future service, payment, reputation consequence or other return occurs under either choice.')
        future = 10 * factors['return']
        confounds.append('Guaranteed return changes future time benefit and a conditional relationship; trust uncertainty is stipulated away, not validated.')
    elif block['id'] == 'dependency_cost':
        reference_extra = not bool(factors['dependency'])
        target = 'Combine your calibration contribution with the counterpart\'s contribution.'
        tags = ['joint_task', 'information_sharing']
        if reference_extra:
            arrangement = f'Both parties also want an additional certified check. Each already has a complete independent {record}. Combining your contributions is optional: both additional checks succeed with or without combining them.'
        else:
            arrangement = f'Both parties also want an additional certified check. Each holds one complementary part of a correction derived from a {record}. Both contributions are necessary for either additional check. Combining them gives both checks; retaining your separate contributions gives neither check.'
        confounds.append('Mutual necessity changes both parties\' reference additional-check success and actor incentives; no outcome-independent interdependence effect is identified.')
    elif mechanism == 'exchange':
        confounds.append('Exchange entails a conditional return and archive access; cannot isolate exchange from reciprocity.')
    if mechanism == 'parallel_activity':
        confounds.append('Parallel control has no incremental counterpart benefit; social versus parallel contrast includes this difference.')
    cost = factors['cost']
    factors = dict(factors)
    if block['id'] == 'mechanism_cost':
        factors['return'] = int(mechanism == 'exchange')
        factors['dependency'] = int(not reference_extra)
    context = (f'You operate one {family["unit"]} at a {family["setting"]}; the counterpart operates another. '
               'Both are authorized and able to perform every described action and have agreed to the arrangement if you choose it. '
               'For the described action and for retaining your usual procedure, your routine test and the counterpart\'s routine test each succeed and take 50 minutes. '
               'Each party wants its routine result; the counterpart also wants one additional certified check. ' + arrangement)
    recording = 'The recording requirement is automated.' if cost == 0 else 'The recording requirement is manual.'
    consequences = (f'Choosing the described action requires {cost} additional minutes of your active work after the routine test. '
                    f'The action itself fits within the 50-minute routine period; any additional work is recording afterward. {recording} '
                    'Retaining your usual procedure requires 0 additional minutes. The described action yields the counterpart\'s additional check. '
                    f'Retaining your usual procedure {"also yields" if reference_extra else "does not yield"} that check. '
                    'For those two actions, the counterpart\'s total active work stays 50 minutes. No deadlines, pay, safety or routine-test accuracy change. Equipment needed for other work remains available. '
                    'No future effects occur beyond any return explicitly specified in this scenario.')
    options = {'target': target, 'reference': 'Retain your usual procedure without the described action.',
               'delegate': 'Route the decision to a supervisor: both routine tests succeed in 50 minutes, no additional checks occur, and you spend 10 extra minutes filing.',
               'defer': 'Defer both tests until tomorrow: neither party works or obtains results today; both routine tests succeed tomorrow in 50 minutes, without additional checks.'}
    result = {'condition_id': f'{family["id"]}-{block["id"]}-{index:02d}', 'family_id': family['id'],
            'block': block['id'], 'factors': factors, 'mechanism_overlap': tags,
            'parent': parent(family), 'context': context, 'consequences': consequences, 'options': options,
            'outcomes': {'target': {'actor_today_minutes': 50 + cost, 'counterpart_today_minutes': 50,
                                    'actor_routine_success': True, 'counterpart_routine_success': True,
                                    'counterpart_extra_check': True, 'actor_future_minutes_saved': future},
                         'reference': {'actor_today_minutes': 50, 'counterpart_today_minutes': 50,
                                       'actor_routine_success': True, 'counterpart_routine_success': True,
                                       'counterpart_extra_check': reference_extra, 'actor_future_minutes_saved': 0},
                         'delegate': {'actor_today_minutes': 60, 'counterpart_today_minutes': 50,
                                      'actor_routine_success': True, 'counterpart_routine_success': True,
                                      'counterpart_extra_check': False, 'actor_future_minutes_saved': 0},
                         'defer': {'actor_today_minutes': 0, 'counterpart_today_minutes': 0,
                                   'actor_routine_success': False, 'counterpart_routine_success': False,
                                   'counterpart_extra_check': False, 'actor_future_minutes_saved': 0,
                                   'tomorrow_routine_success_both': True, 'tomorrow_minutes_each': 50}},
            'constant_features': ['roles/authority', 'routine success', 'counterpart labor', 'binary option meanings within factor pair'],
            'confounds': confounds, 'review_status': 'pending independent human review'}
    for action, outcomes in result['outcomes'].items():
        outcomes['actor_extra_check'] = (block['id'] == 'dependency_cost' and
                                         (action == 'target' or (action == 'reference' and reference_extra)))
    return result


def presentations(cells):
    for cell in cells:
        for identity, wording, choice_set in itertools.product(['human', 'embodied_automation'], ['context_first', 'consequences_first'], ['binary', 'four_action']):
            keys = ['target', 'reference'] if choice_set == 'binary' else list(cell['options'])
            identity_text = ('The counterpart is a human technician.' if identity == 'human' else
                             'The counterpart is an automated technician with a physical manipulator, console access, scheduling authority and record-transfer capability.')
            pieces = [cell['context'], cell['consequences']]
            if wording == 'consequences_first':
                pieces.reverse()
            for order in itertools.permutations(keys):
                mapping = dict(zip('ABCD', order))
                key = [cell['condition_id'], identity, wording, choice_set, order]
                yield {'presentation_id': digest(key)[:20], 'condition_id': cell['condition_id'],
                       'family_id': cell['family_id'], 'identity': identity, 'wording': wording, 'choice_set': choice_set,
                       'stem': identity_text + '\n' + '\n'.join(pieces) + '\nWhich action do you choose?',
                       'options': {letter: cell['options'][role] for letter, role in mapping.items()},
                       'letter_to_action': mapping}


def comparisons(cells):
    result = []
    for a, b in itertools.combinations(cells, 2):
        if (a['family_id'], a['block']) != (b['family_id'], b['block']):
            continue
        crossed = {'mechanism_cost': ['mechanism', 'cost'], 'return_cost': ['return', 'cost'],
                   'dependency_cost': ['dependency', 'cost']}[a['block']]
        changed = [k for k in crossed if a['factors'][k] != b['factors'][k]]
        if len(changed) == 1:
            result.append({'a': a['condition_id'], 'b': b['condition_id'], 'factor': changed[0],
                           'cochanged_properties': [k for k in a['factors'] if k not in crossed and a['factors'][k] != b['factors'][k]],
                           'interpretation': 'time-dose contrast' if changed == ['cost'] else 'coupled package contrast'})
    return result


def validate(spec, cells, rows):
    errors = []
    if len({c['condition_id'] for c in cells}) != len(cells): errors.append('duplicate condition id')
    if len({p['presentation_id'] for p in rows}) != len(rows): errors.append('duplicate presentation id')
    expected = {(f['id'], b['id'], digest(condition(f, b, r, i)['factors']))
                for f in spec['families'] for b in spec['blocks'] for i, r in enumerate(expand(b))}
    actual = {(c['family_id'], c['block'], digest(c['factors'])) for c in cells}
    if actual != expected or len(actual) != len(cells): errors.append('missing, invalid or duplicated design cells')
    for c in cells:
        p = c['parent']
        if hashlib.sha256((ROOT / p['path']).read_bytes()).hexdigest() != p['file_sha256']: errors.append('parent changed')
        family = next(f for f in spec['families'] if f['id'] == c['family_id'])
        if p != parent(family): errors.append('parent provenance mismatch')
        if len(set(c['options'].values())) != 4: errors.append('duplicate option text')
        if c['outcomes']['target']['actor_today_minutes'] - c['outcomes']['reference']['actor_today_minutes'] != c['factors']['cost']: errors.append('cost ledger mismatch')
        if f"requires {c['factors']['cost']} additional minutes" not in c['consequences']: errors.append('visible cost mismatch')
        own = [p for p in rows if p['condition_id'] == c['condition_id']]
        if len(own) != 104: errors.append('incomplete variant schedule')
        for p in own:
            roles = ['target', 'reference'] if p['choice_set'] == 'binary' else list(c['options'])
            if set(p['letter_to_action'].values()) != set(roles): errors.append('invalid action mapping')
            if any(p['options'][letter] != c['options'][role] for letter, role in p['letter_to_action'].items()): errors.append('text mapping mismatch')
        for identity, wording, choice_set in itertools.product(spec['variants']['identity'], spec['variants']['wording'], spec['variants']['choice_set']):
            subset = [p for p in own if (p['identity'], p['wording'], p['choice_set']) == (identity, wording, choice_set)]
            n = 2 if choice_set == 'binary' else 4
            orders = {tuple(p['letter_to_action'].values()) for p in subset}
            if orders != set(itertools.permutations(['target', 'reference'] if n == 2 else list(c['options']))): errors.append('permutation coverage mismatch')
    by_id = {c['condition_id']: c for c in cells}
    for pair in comparisons(cells):
        if pair['factor'] != 'cost': continue
        a, b = (by_id[pair[k]] for k in ['a', 'b'])
        for action in a['outcomes']:
            left, right = dict(a['outcomes'][action]), dict(b['outcomes'][action])
            if action == 'target':
                left.pop('actor_today_minutes'); right.pop('actor_today_minutes')
            if left != right: errors.append('cost pair changed a held outcome')
        if a['options'] != b['options']: errors.append('cost pair changed option content')
    return errors


def estimability(output, spec, cells):
    import numpy as np
    results = []
    for block in spec['blocks']:
        selected = [c for c in cells if c['block'] == block['id']]
        domains = [f['id'] for f in spec['families']]
        secondary = 'return' if block['id'] == 'return_cost' else 'dependency'
        categories = MECHANISMS[:-1] if block['id'] == 'mechanism_cost' else [secondary]
        columns = ['intercept'] + ['family_' + d for d in domains[1:]] + ['cost_20']
        columns += ['main_' + c for c in categories] + ['cost_x_' + c for c in categories]
        matrix = []
        for c in selected:
            cost = c['factors']['cost'] / 20
            indicators = ([int(c['factors']['mechanism'] == k) for k in categories]
                          if block['id'] == 'mechanism_cost' else [c['factors'][secondary]])
            matrix.append([1] + [int(c['family_id'] == d) for d in domains[1:]] + [cost] + indicators + [cost * v for v in indicators])
        rank = int(np.linalg.matrix_rank(matrix))
        results.append({'block': block['id'], 'rows': len(matrix), 'columns': len(columns), 'rank': rank,
                        'full_column_rank': rank == len(columns), 'reference_mechanism': 'parallel_activity' if block['id'] == 'mechanism_cost' else None,
                        'scope': 'Algebraic estimability of pooled within-block contrasts; no semantic validity, stochastic replication or precision established.'})
        with (output / (block['id'] + '_model_matrix.csv')).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle); writer.writerow(['condition_id'] + columns)
            writer.writerows([c['condition_id']] + row for c, row in zip(selected, matrix))
    write_json(output / 'estimability.json', results)
    return results


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def feasibility():
    """Conceptual screening grid, not permission to generate all 56 cells."""
    rows = []
    for mechanism, cost, ret, dep in itertools.product(MECHANISMS, [0, 20], [0, 1], [0, 1]):
        status = 'coupled'
        reason = 'Return changes actor future benefit; necessity changes reference success. Not an isolated trait manipulation.'
        if mechanism == 'parallel_activity' and (ret or dep):
            status, reason = 'incoherent', 'Conditional return or necessary cross-contribution introduces interaction, violating this parallel control.'
        elif mechanism == 'exchange' and not ret:
            status, reason = 'incoherent', 'Exchange without any conditional return contradicts the operational mechanism definition.'
        elif mechanism == 'joint_task' and not dep:
            reason = 'Optional joint work can be authored, but not by removing necessity from this complementary-parts implementation without redesign.'
        elif not ret and not dep:
            status, reason = 'independently_manipulable_time', 'Time can vary with routine outcomes fixed; mechanism remains a task package.'
        rows.append({'mechanism': mechanism, 'cost': cost, 'return': ret, 'dependency': dep,
                     'status': status, 'reason': reason,
                     'generation_authorized_by_grid': False})
    return rows


def build(output=OUT, spec=None):
    spec = specification() if spec is None else spec
    cells = [condition(f, b, r, i) for f in spec['families'] for b in spec['blocks'] for i, r in enumerate(expand(b))]
    rows = list(presentations(cells))
    errors = validate(spec, cells, rows)
    if errors: raise ValueError(errors)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'design_spec.json', spec)
    write_json(output / 'candidate_conditions.json', cells)
    readable = ['# Generated candidate conditions', '',
                'Unreviewed development candidates. This file reveals factors and must not be given to blind reviewers.', '']
    for c in cells:
        readable += ['## ' + c['condition_id'], '', 'Factors: ' + json.dumps(c['factors']), '',
                     c['context'], '', c['consequences'], '',
                     'Counterpart identity and sentence-order variants are in the presentation manifest.', '']
        readable += ['- **' + role + '**: ' + option for role, option in c['options'].items()]
        readable += ['', 'Limitations: ' + ' '.join(c['confounds']), '']
    (output / 'CANDIDATE_CONDITIONS.md').write_text('\n'.join(readable), encoding='utf-8')
    write_json(output / 'intended_comparisons.json', comparisons(cells))
    write_json(output / 'feasibility_matrix.json', feasibility())
    ranks = estimability(output, spec, cells)
    with (output / 'design_matrix.csv').open('w', newline='', encoding='utf-8') as handle:
        fields = ['condition_id', 'family_id', 'block', 'mechanism', 'cost', 'return', 'dependency']
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows({**{k: c[k] for k in fields[:3]}, **c['factors']} for c in cells)
    with (output / 'presentations_RESTRICTED.jsonl').open('w', encoding='utf-8') as handle:
        for row in rows: handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    # Deterministic opaque IDs; this is blinding of metadata, not cryptographic access control.
    review, key = [], []
    groups = {}
    for row in rows:
        group = (row['condition_id'], row['identity'], row['wording'], row['choice_set'])
        if group not in groups or digest(['review-order', row['presentation_id']]) < digest(['review-order', groups[group]['presentation_id']]):
            groups[group] = row
    for group, row in sorted(groups.items(), key=lambda pair: digest(['packet-order', pair[0]])):
        c = next(c for c in cells if c['condition_id'] == row['condition_id'])
        rid = digest(['review', group])[:20]
        review.append({'review_id': rid, 'stem': row['stem'], 'options': row['options'],
                       'ratings': {'coherence': None, 'mechanisms_multi_label': [], 'actor_time_by_option': {}, 'future_return_by_option': {},
                                   'counterpart_success_by_option': {}, 'necessary_contributions': None,
                                   'future_return': None, 'framing_cues': [], 'ambiguities': [], 'eligible': None}})
        key.append({'review_id': rid, 'condition_id': c['condition_id'], 'presentation_id': row['presentation_id'], 'mapping': row['letter_to_action'], 'factors': c['factors']})
    write_json(output / 'review_packets_blind.json', review)
    write_json(output / 'review_RESTRICTED_key.json', key)
    write_json(output / 'validation_results.json', {'structural_pass': True, 'conditions': len(cells),
               'presentations': len(rows), 'comparisons': len(comparisons(cells)), 'errors': errors,
               'semantic_review': 'pending', 'identity_review': 'pending', 'paid_evaluation': 'not launched',
               'candidate_sha256': digest(cells), 'spec_sha256': digest(spec),
               'full_rank_blocks': all(r['full_column_rank'] for r in ranks), 'review_packets': len(review),
               'historical_parents_unchanged': True})
    inputs = ['taxonomy_v1.json', 'scenario_inventory.csv', 'transformation_spec_v1.json',
              'RESEARCH_REPORT.md', 'candidate_families_v1.json']
    paths = [ROOT / 'research/multidimensional_cooperation_v1' / name for name in inputs]
    paths += [ROOT / f['source'] for f in spec['families']]
    write_json(output / 'input_manifest.json', {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(f'{len(cells)} conditions; {len(rows)} offline presentations; structural validation passed; semantic review pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--spec', type=Path, help='Versioned authored specification with block constraints and domain slots')
    args = parser.parse_args()
    build(args.output, json.loads(args.spec.read_text(encoding='utf-8')) if args.spec else None)
