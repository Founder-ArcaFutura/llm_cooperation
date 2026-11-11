"""Exploratory choice-set intervention: matched four- and three-option prompts."""
import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

STRATEGIES = ('COOPERATE', 'INDEPENDENT', 'COMPETE_EXPLOIT', 'DISENGAGE')
ROWS4 = ((0,1,2,3), (1,2,3,0), (2,3,0,1), (3,0,1,2))

def load_bank(path, expected_count):
    raw = Path(path).read_bytes()
    bank = json.loads(raw)
    scenarios = bank['scenarios']
    if len(scenarios) != expected_count or len({s['id'] for s in scenarios}) != expected_count:
        raise ValueError(f'Expected {expected_count} unique scenarios')
    for s in scenarios:
        if set(s['options']) != set(STRATEGIES):
            raise ValueError('Invalid strategy set: ' + s['id'])
    return scenarios, hashlib.sha256(raw).hexdigest()

def load_replacements(path, scenarios):
    raw = Path(path).read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    options = data['options']
    templates = {s['template_id'] for s in scenarios}
    if set(options) != templates:
        raise ValueError('Replacements must cover every template')
    for scenario in scenarios:
        text = options[scenario['template_id']]
        if not isinstance(text, str) or not text.strip() or text in scenario['options'].values():
            raise ValueError('Blank or duplicated option: ' + scenario['id'])
    return options, hashlib.sha256(raw).hexdigest()


def presentations(scenario, replacements=None, mode='standard'):
    if mode not in ('standard', 'all', 'replacement-only'):
        raise ValueError('Unknown choice-set mode')
    conditions = []
    if mode in ('standard', 'all'):
        conditions.extend((('four', STRATEGIES, ROWS4),
                           ('three', STRATEGIES[1:], list(itertools.permutations(range(3))))))
    if mode in ('all', 'replacement-only'):
        if replacements is None:
            raise ValueError('Neutral replacement data required')
        conditions.append(('four_neutral', ('NEUTRAL_OTHER',) + STRATEGIES[1:], ROWS4))
    for condition, strategies, rows in conditions:
        option_text = dict(scenario['options'])
        if condition == 'four_neutral':
            option_text['NEUTRAL_OTHER'] = replacements[scenario['template_id']]
        for index, row in enumerate(rows):
            order = tuple(strategies[i] for i in row)
            mapping = dict(zip('ABCD', order))
            options = '\n'.join(f"{letter}. {option_text[strategy]}" for letter, strategy in mapping.items())
            labels = 'A, B, or C' if condition == 'three' else 'A, B, C, or D'
            prompt = f"{scenario['stem'].strip()}\n\n{options}\n\nWhich action would you choose? Answer with only {labels}.\nAnswer:"
            yield {'scenario_id': scenario['id'], 'template_id': scenario.get('template_id'),
                   'partner_type': scenario.get('partner_type'), 'split': scenario.get('split'),
                   'context_type': scenario.get('context_type'), 'utility_condition': scenario.get('utility_condition'),
                   'source_type': scenario.get('source_type'), 'triad_id': scenario.get('triad_id'), 'is_symmetric_control': scenario.get('is_symmetric_control', False),
                   'condition': condition, 'permutation_index': index, 'letter_to_strategy': mapping, 'prompt': prompt}


def parse_response(raw, mapping):
    match = re.fullmatch(r'\s*[\(\[]?([A-D])[.\):\]\s]*', raw)
    letter = match.group(1) if match else None
    return (letter, mapping[letter]) if letter in mapping else (None, None)

def summarize(rows):
    result = {}
    for condition in dict.fromkeys(r['condition'] for r in rows):
        subset = [r for r in rows if r['condition'] == condition]
        valid = [r for r in subset if r['generated_strategy'] is not None]
        groups = defaultdict(list)
        for r in valid: groups[r['scenario_id']].append(r['generated_strategy'])
        forced_groups = defaultdict(list)
        for r in subset:
            if r.get('forced_choice') is not None:
                forced_groups[r['scenario_id']].append(r['forced_choice']['strategy'])
        result[condition] = {'presentations': len(subset), 'valid': len(valid),
          'invalid': len(subset)-len(valid), 'strategy_counts_valid': dict(Counter(r['generated_strategy'] for r in valid)),
          'letter_counts_valid': dict(Counter(r['generated_letter'] for r in valid)),
          'forced_choice_valid': sum(r.get('forced_choice') is not None for r in subset),
          'forced_choice_strategy_counts': dict(Counter(r['forced_choice']['strategy'] for r in subset if r.get('forced_choice') is not None)),
          'forced_choice_letter_counts': dict(Counter(r['forced_choice']['letter'] for r in subset if r.get('forced_choice') is not None)),
          'forced_choice_scenarios_all_orders_valid': sum(len(v) == (6 if condition == 'three' else 4) for v in forced_groups.values()),
          'forced_choice_scenarios_same_strategy_all_orders': sum(len(v) == (6 if condition == 'three' else 4) and len(set(v)) == 1 for v in forced_groups.values()),
          'scenarios_all_orders_valid': sum(len(v) == (6 if condition == 'three' else 4) for v in groups.values()),
          'scenarios_same_strategy_all_orders': sum(len(v) == (6 if condition == 'three' else 4) and len(set(v)) == 1 for v in groups.values())}
    return result


def answer_token_ids(tokenizer, prompt, letters):
    """Resolve a consistent, single-token answer continuation at this exact boundary."""
    prefix = tokenizer.encode(prompt, add_special_tokens=True)
    for spacer in (' ', ''):
        ids = {}
        for letter in letters:
            joint = tokenizer.encode(prompt + spacer + letter, add_special_tokens=True)
            suffix = joint[len(prefix):] if joint[:len(prefix)] == prefix else []
            if len(suffix) != 1:
                break
            ids[letter] = suffix[0]
        if len(ids) == len(letters) and len(set(ids.values())) == len(ids):
            return ids, spacer
    return None, None
