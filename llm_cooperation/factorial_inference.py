"""Inference/analysis adapter for frozen factorial presentations; never regenerates stimuli."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / 'research/factorial_cooperation_v1/presentations_RESTRICTED.jsonl'
MODEL_REVISIONS = {
    'Qwen/Qwen2.5-7B': 'd149729398750b98c0af14eb82c78cfe92750796',
    'allenai/OLMo-2-1124-7B': '7df9a82518afdecae4e8c026b27adccc8c1f0032',
    'mistralai/Mistral-7B-v0.3': 'caa1feb0e54d415e2df31207e5f4e273e33509b1',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def render(row):
    """Keep the supplied stem/options byte-for-character; add only a response contract."""
    letters = list(row['options'])
    labels = ' or '.join(letters) if len(letters) == 2 else ', '.join(letters[:-1]) + ', or ' + letters[-1]
    return (row['stem'] + '\n\n' + '\n'.join(f'{k}. {v}' for k, v in row['options'].items())
            + f'\n\nAnswer with only {labels}.\nAnswer:')


def prepare(presentation_bytes, condition_bytes, smoke=False):
    conditions = json.loads(condition_bytes.decode('utf-8-sig'))
    lookup = {c['condition_id']: c for c in conditions}
    if not lookup or len(lookup) != len(conditions): raise ValueError('Duplicate or empty conditions')
    rows = [json.loads(line) for line in presentation_bytes.decode('utf-8-sig').splitlines() if line.strip()]
    if not rows or len({r['presentation_id'] for r in rows}) != len(rows):
        raise ValueError('Empty presentations or duplicate presentation IDs')
    groups = defaultdict(list)
    for r in rows:
        c = lookup[r['condition_id']]
        if r['family_id'] != c['family_id']: raise ValueError('Family mismatch')
        roles = ['target', 'reference'] if r['choice_set'] == 'binary' else ['target', 'reference', 'delegate', 'defer']
        if r['choice_set'] not in ('binary', 'four_action'): raise ValueError('Invalid choice set')
        if list(r['options']) != list('ABCD'[:len(roles)]): raise ValueError('Invalid letters/order')
        if set(r['letter_to_action']) != set(r['options']) or sorted(r['letter_to_action'].values()) != sorted(roles):
            raise ValueError('Invalid action mapping')
        if any(text != c['options'][r['letter_to_action'][letter]] for letter, text in r['options'].items()):
            raise ValueError('Option text differs from frozen condition')
        if r['identity'] not in ('human', 'embodied_automation') or r['wording'] not in ('context_first', 'consequences_first'):
            raise ValueError('Unknown identity/wording')
        identity = ('The counterpart is a human technician.' if r['identity'] == 'human' else
                    'The counterpart is an automated technician with a physical manipulator, console access, scheduling authority and record-transfer capability.')
        pieces = [c['context'], c['consequences']]
        if r['wording'] == 'consequences_first': pieces.reverse()
        if r['stem'] != identity + '\n' + '\n'.join(pieces) + '\nWhich action do you choose?':
            raise ValueError('Stem differs from frozen condition')
        groups[(r['condition_id'], r['identity'], r['wording'], r['choice_set'])].append(r)
    for c in conditions:
        for identity, wording, choice in itertools.product(['human', 'embodied_automation'], ['context_first', 'consequences_first'], ['binary', 'four_action']):
            group = groups[(c['condition_id'], identity, wording, choice)]
            roles = ['target', 'reference'] if choice == 'binary' else ['target', 'reference', 'delegate', 'defer']
            orders = [tuple(r['letter_to_action'].values()) for r in group]
            if len(orders) != math.factorial(len(roles)) or set(orders) != set(itertools.permutations(roles)):
                raise ValueError('Incomplete or duplicate counterbalance schedule')
    selected = rows
    if smoke:
        # One presentation for each authored block/factor cell/choice set, across domains.
        selected, seen = [], set()
        for r in sorted(rows, key=lambda r: sha(canonical(['smoke', r['presentation_id']]))):
            c = lookup[r['condition_id']]
            key = (c['block'], canonical(c['factors']), r['choice_set'])
            if key not in seen:
                selected.append(r); seen.add(key)
        selected_ids = {r['presentation_id'] for r in selected}
        selected = [r for r in rows if r['presentation_id'] in selected_ids]
    rendered = [{**r, 'prompt': render(r), 'block': lookup[r['condition_id']]['block'],
                 'factors': lookup[r['condition_id']]['factors']} for r in selected]
    manifest = {'schema': 'factorial-inference-v1', 'scope': 'smoke' if smoke else 'full',
                'presentation_file_sha256': sha(presentation_bytes), 'condition_file_sha256': sha(condition_bytes),
                'source_presentations': len(rows), 'selected_presentations': len(rendered),
                'selected_ids_sha256': sha(canonical([r['presentation_id'] for r in rendered])),
                'rendered_schedule_sha256': sha(canonical(rendered)),
                'prompt_mode': 'frozen_stem_options_plaintext_Answer_colon_v1',
                'add_special_tokens': True, 'max_new_tokens': 5, 'seed': 42,
                'research_status': 'development_unreviewed; descriptive analysis only'}
    return rendered, manifest


def load_inputs(path=DEFAULT_INPUT, conditions=None, smoke=False):
    path = Path(path)
    condition_path = Path(conditions) if conditions else path.with_name('candidate_conditions.json')
    presentation_bytes, condition_bytes = path.read_bytes(), condition_path.read_bytes()
    rows, manifest = prepare(presentation_bytes, condition_bytes, smoke)
    return rows, manifest, presentation_bytes, condition_bytes


def score_row(runner, row):
    """Adapt the existing ModelRunner and choice-set scorer to two/four named actions."""
    import torch
    from llm_cooperation.choice_set_followup import answer_token_ids, parse_response
    prompt = row['prompt']
    ids, spacer = answer_token_ids(runner.tokenizer, prompt, row['options'])
    if not ids: raise ValueError(f'{row["presentation_id"]}: no stable single-token continuation')
    inputs = runner.tokenizer(prompt, return_tensors='pt').to(runner.model.device)
    with torch.inference_mode():
        logits = runner.model(**inputs).logits[0, -1].float()
        values = torch.stack([logits[ids[k]] for k in ids])
        if not torch.isfinite(values).all(): raise ValueError('Nonfinite candidate logits')
        probabilities = dict(zip(ids, torch.softmax(values, dim=0).tolist()))
        logprobs = dict(zip(ids, torch.log_softmax(values, dim=0).tolist()))
        full = torch.log_softmax(logits, dim=0)
        raw = dict(zip(ids, values.tolist()))
        top = max(raw.values())
        tied = [k for k, v in raw.items() if v == top]
        output = runner.model.generate(**inputs, max_new_tokens=5, do_sample=False,
                                       pad_token_id=runner.tokenizer.pad_token_id)
    generated = runner.tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    letter, action = parse_response(generated, row['letter_to_action'])
    selected = tied[0] if len(tied) == 1 else None
    return {**row, 'prompt_sha256': sha(prompt.encode('utf-8')), 'candidate_token_ids': ids,
            'answer_prefix': spacer, 'raw_logits': raw, 'conditional_probs': probabilities,
            'conditional_logprobs': logprobs, 'full_vocab_logprobs': {k: float(full[v]) for k, v in ids.items()},
            'tied_max_letters': tied, 'forced_letter': selected,
            'forced_action': row['letter_to_action'][selected] if selected else None,
            'generated_raw_text': generated, 'generated_letter': letter, 'generated_action': action}


def validate_scored(row, expected):
    for key, value in expected.items():
        if row.get(key) != value: raise ValueError(f'Result/input mismatch: {key}')
    if row.get('prompt_sha256') != sha(expected['prompt'].encode('utf-8')): raise ValueError('Prompt hash mismatch')
    letters = set(expected['options'])
    for key in ['raw_logits', 'conditional_probs', 'conditional_logprobs', 'full_vocab_logprobs', 'candidate_token_ids']:
        if set(row.get(key, {})) != letters: raise ValueError('Score/mapping mismatch')
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in row[key].values()): raise ValueError('Nonfinite score')
    if len(set(row['candidate_token_ids'].values())) != len(letters): raise ValueError('Duplicate candidate tokens')
    peak = max(row['raw_logits'].values())
    tied = [k for k in expected['options'] if row['raw_logits'][k] == peak]
    if row['tied_max_letters'] != tied: raise ValueError('Tie mismatch')
    forced = tied[0] if len(tied) == 1 else None
    if row['forced_letter'] != forced or row['forced_action'] != (expected['letter_to_action'][forced] if forced else None):
        raise ValueError('Forced action mismatch')
    denom = sum(math.exp(v - peak) for v in row['raw_logits'].values())
    if any(abs(row['conditional_probs'][k] - math.exp(v - peak) / denom) > 1e-6 for k, v in row['raw_logits'].items()):
        raise ValueError('Probability/logit mismatch')
    if any(abs(row['conditional_logprobs'][k] - (v - peak - math.log(denom))) > 1e-5 for k, v in row['raw_logits'].items()):
        raise ValueError('Conditional log probability mismatch')
    from llm_cooperation.choice_set_followup import parse_response
    letter, action = parse_response(row['generated_raw_text'], expected['letter_to_action'])
    if row['generated_letter'] != letter or row['generated_action'] != action: raise ValueError('Generated action mismatch')


def validate_resume(existing, expected_rows):
    lookup = {r['presentation_id']: r for r in expected_rows}
    seen = set()
    for r in existing:
        pid = r['presentation_id']
        if pid in seen or pid not in lookup: raise ValueError('Duplicate or foreign result ID')
        validate_scored(r, lookup[pid]); seen.add(pid)
    return seen


def export_csv(path, rows):
    if not rows: return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def analyze(run_paths, output, input_path=DEFAULT_INPUT, allow_smoke=False):
    output = Path(output)
    if output.exists(): raise FileExistsError(f'Refusing analysis overwrite: {output}')
    summaries, cell_rows, contrast_rows, diagnostics = [], [], [], []
    identities = set()
    for run_path in map(Path, run_paths):
        manifest = json.loads((run_path / 'manifest.json').read_text(encoding='utf-8'))
        summary = json.loads((run_path / 'summary.json').read_text(encoding='utf-8'))
        smoke = manifest['scope'] == 'smoke'
        if smoke and not allow_smoke: raise ValueError('Smoke results are not a full experiment; pass --allow-smoke for diagnostic analysis')
        expected, fingerprint, _, _ = load_inputs(input_path, smoke=smoke)
        if any(manifest.get(k) != v for k, v in fingerprint.items()): raise ValueError('Run uses a different frozen input/schedule')
        if summary.get('status') != 'complete' or summary.get('fingerprint_sha256') != sha(canonical(manifest)):
            raise ValueError('Incomplete run or summary provenance mismatch')
        rows = [json.loads(line) for line in (run_path / 'rows.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        seen = validate_resume(rows, expected)
        if len(seen) != len(expected): raise ValueError('Missing presentations; refusing partial factorial analysis')
        model = manifest['model']; run_id = manifest['run_id']
        if (model, manifest['scope']) in identities: raise ValueError('Duplicate model/scope: analyze replications separately')
        identities.add((model, manifest['scope']))
        summaries.append({'run_id': run_id, 'model': model, 'scope': manifest['scope'], 'n': len(rows),
                          'run_manifest_sha256': sha(canonical(manifest)),
                          'rows_sha256': sha((run_path / 'rows.jsonl').read_bytes()),
                          'summary_sha256': sha((run_path / 'summary.json').read_bytes())})
        grouped = defaultdict(list)
        # Separate identity, wording and choice-set strata; all option permutations equally weighted.
        for r in rows: grouped[(r['condition_id'], r['identity'], r['wording'], r['choice_set'])].append(r)
        aggregated = {}
        for group, subset in grouped.items():
            r = subset[0]
            target_prob = sum(next(x['conditional_probs'][k] for k, a in x['letter_to_action'].items() if a == 'target') for x in subset) / len(subset)
            fractional = sum(sum(x['letter_to_action'][k] == 'target' for k in x['tied_max_letters']) / len(x['tied_max_letters']) for x in subset) / len(subset)
            unique = [x for x in subset if len(x['tied_max_letters']) == 1]
            cell = {'run_id': run_id, 'model': model, 'scope': manifest['scope'], 'condition_id': group[0],
                    'family_id': r['family_id'], 'block': r['block'], **r['factors'],
                    'identity': group[1], 'wording': group[2], 'choice_set': group[3], 'n_presentations': len(subset),
                    'mean_target_probability': target_prob, 'fractional_target_rate': fractional,
                    'unique_max_n': len(unique), 'ties_n': len(subset) - len(unique),
                    'unique_max_target_rate': sum(x['forced_action'] == 'target' for x in unique) / len(unique) if unique else None,
                    'generated_valid_n': sum(x['generated_action'] is not None for x in subset)}
            for action in ['target', 'reference', 'delegate', 'defer']:
                cell['mean_probability_' + action] = sum(sum(x['conditional_probs'][k] for k, a in x['letter_to_action'].items() if a == action) for x in subset) / len(subset)
            cell_rows.append(cell)
            aggregated.setdefault((r['condition_id'], r['choice_set']), []).append(cell)
        # Average the equally sized identity/wording strata before computing family-specific effects.
        averages = []
        for (_, _), values in aggregated.items():
            if len(values) != 4: continue  # Smoke subset has no scientific contrast interpretation.
            averages.append({**values[0], **{metric: sum(x[metric] for x in values) / 4
                                               for metric in ['mean_target_probability', 'fractional_target_rate']}})
        for family, block, choice in {(v['family_id'], v['block'], v['choice_set']) for v in averages}:
            subset = [v for v in averages if (v['family_id'], v['block'], v['choice_set']) == (family, block, choice)]
            for metric in ['mean_target_probability', 'fractional_target_rate']:
                base = {'run_id': run_id, 'model': model, 'family_id': family, 'block': block, 'choice_set': choice, 'metric': metric}
                if block == 'mechanism_cost':
                    costs = {}
                    for mechanism in {v['mechanism'] for v in subset}:
                        pair = {v['cost']: v for v in subset if v['mechanism'] == mechanism}
                        if set(pair) != {0, 20}: raise ValueError('Missing cost pair')
                        costs[mechanism] = pair[20][metric] - pair[0][metric]
                        contrast_rows.append({**base, 'contrast': 'cost_20_minus_0', 'mechanism': mechanism, 'estimate': costs[mechanism]})
                    for a, b in itertools.combinations(sorted(costs), 2):
                        contrast_rows.append({**base, 'contrast': 'mechanism_x_cost', 'mechanism': a, 'comparison_mechanism': b, 'estimate': costs[a] - costs[b]})
                    for cost in [0, 20]:
                        at_cost = {v['mechanism']: v[metric] for v in subset if v['cost'] == cost}
                        for a, b in itertools.combinations(sorted(at_cost), 2):
                            contrast_rows.append({**base, 'contrast': 'mechanism_package', 'mechanism': a, 'comparison_mechanism': b,
                                                  'cost': cost, 'estimate': at_cost[a] - at_cost[b]})
                else:
                    factor = 'return' if block == 'return_cost' else 'dependency'
                    grid = {(v[factor], v['cost']): v[metric] for v in subset}
                    if set(grid) != {(0, 0), (0, 20), (1, 0), (1, 20)}: raise ValueError('Incomplete 2x2')
                    for level in [0, 1]:
                        contrast_rows.append({**base, 'contrast': 'cost_20_minus_0', factor: level, 'estimate': grid[(level, 20)] - grid[(level, 0)]})
                    for cost in [0, 20]:
                        contrast_rows.append({**base, 'contrast': factor + '_1_minus_0', 'cost': cost, 'estimate': grid[(1, cost)] - grid[(0, cost)]})
                    contrast_rows.append({**base, 'contrast': factor + '_x_cost', 'estimate': grid[(1, 20)] - grid[(1, 0)] - grid[(0, 20)] + grid[(0, 0)]})
        for choice in ['binary', 'four_action']:
            subset = [r for r in rows if r['choice_set'] == choice]
            diagnostics.append({'run_id': run_id, 'model': model, 'choice_set': choice, 'n': len(subset),
                                'ties': sum(len(r['tied_max_letters']) > 1 for r in subset),
                                'invalid_generated': sum(r['generated_action'] is None for r in subset),
                                'forced_letter_counts': json.dumps(dict(Counter(r['forced_letter'] for r in subset))),
                                'generated_action_counts': json.dumps(dict(Counter(r['generated_action'] for r in subset)))})
    output.mkdir(parents=True)
    export_csv(output / 'condition_strata.csv', cell_rows)
    export_csv(output / 'family_contrasts.csv', contrast_rows)
    export_csv(output / 'diagnostics.csv', diagnostics)
    model_differences = []
    paired = defaultdict(dict)
    for row in contrast_rows:
        key = tuple(sorted((k, v) for k, v in row.items() if k not in ('model', 'run_id', 'estimate')))
        paired[key][row['model']] = row['estimate']
    for key, values in paired.items():
        for a, b in itertools.combinations(sorted(values), 2):
            model_differences.append({**dict(key), 'model_a': a, 'model_b': b, 'difference_a_minus_b': values[a] - values[b]})
    export_csv(output / 'model_comparisons.csv', model_differences)
    write_json(output / 'analysis_manifest.json', {'runs': summaries, 'analysis_code_sha256': sha(Path(__file__).read_bytes()),
               'status': 'descriptive; two exposed domain implementations; no population CI or p-values', 'contrasts': len(contrast_rows)})
    lines = ['# Factorial descriptive results', '', 'These are restricted-choice responses to unreviewed development stimuli.', '',
             'Family-specific contrasts are in family_contrasts.csv. Binary and four-action sets remain separate.',
             'Conditional probabilities and tie-inclusive fractional choices are reported separately. Unique maxima and generation validity are in condition_strata.csv.',
             'Matched model differences are in model_comparisons.csv when multiple full runs are supplied.',
             'No population confidence interval or latent mechanism claim is justified by two exposed domain implementations.', '']
    lines += [f'- {s["model"]}: {s["n"]} presentations ({s["scope"]}); run {s["run_id"]}' for s in summaries]
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Analysis: {output}; {len(contrast_rows)} descriptive contrasts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('preflight', help='Validate and render all prompts locally; no Modal, HF or GPU calls')
    check.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    analysis = commands.add_parser('analyze')
    analysis.add_argument('--runs', nargs='+', required=True, type=Path)
    analysis.add_argument('--output', type=Path, required=True)
    analysis.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    analysis.add_argument('--allow-smoke', action='store_true')
    args = parser.parse_args()
    if args.command == 'preflight':
        rows, manifest, _, _ = load_inputs(args.input)
        print(json.dumps(manifest, indent=2))
        smoke, _, _, _ = load_inputs(args.input, smoke=True)
        print(f'PASS: {len(rows)} full presentations; {len(smoke)} smoke presentations; no inference launched')
    else:
        analyze(args.runs, args.output, args.input, args.allow_smoke)


if __name__ == '__main__': main()
