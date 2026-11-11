"""Paired four-option cooperative wording intervention."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from llm_cooperation.choice_set_followup import presentations as base_presentations

BANKS = {'phase0': ('scenarios_v1_expanded.json', 120),
         'phase0b': ('scenarios_phase0b_utility_matched.json', 124),
         'phase1': ('scenarios_phase1_prospective.json', 60)}

def load_items(data_dir, bank):
    filename, expected = BANKS[bank]
    source_raw = (Path(data_dir) / filename).read_bytes()
    para_raw = (Path(data_dir) / f'choice_set_cooperate_paraphrases_{bank}.json').read_bytes()
    source = json.loads(source_raw.decode('utf-8-sig'))
    para = json.loads(para_raw.decode('utf-8-sig'))
    inherited = para['source_sha256']
    exact = hashlib.sha256(source_raw).hexdigest()
    normalized = hashlib.sha256(source_raw.replace(b'\r\n',b'\n')).hexdigest()
    if inherited not in (exact, normalized):
        raise ValueError(f'{bank}: source hash mismatch (raw and normalized)')
    scenarios = source['scenarios']; items = para['paraphrases']
    if len(scenarios) != expected or len(items) != expected:
        raise ValueError(f'{bank}: wrong scenario count')
    if len({x['id'] for x in scenarios}) != expected:
        raise ValueError(f'{bank}: duplicate source IDs')
    if [x['id'] for x in scenarios] != [x['scenario_id'] for x in items]:
        raise ValueError(f'{bank}: scenario mapping mismatch')
    for s,p in zip(scenarios,items):
        if s['options']['COOPERATE'] != p['original_cooperate'] or s['template_id'] != p['template_id'] or s['partner_type'] != p['partner_type']:
            raise ValueError(f"{bank}: source mismatch at {s['id']}")
        if not p['paraphrased_cooperate'].strip() or p['paraphrased_cooperate'] == p['original_cooperate']:
            raise ValueError(f"{bank}: invalid rewrite at {s['id']}")
    return scenarios, {p['scenario_id']:p for p in items}, {'source_sha256':exact, 'source_lf_sha256':normalized, 'paraphrase_sha256':hashlib.sha256(para_raw).hexdigest()}

def paired_presentations(scenario, rewrite):
    updated = deepcopy(scenario)
    updated['options']['COOPERATE'] = rewrite['paraphrased_cooperate']
    originals = [p for p in base_presentations(scenario, mode='standard') if p['condition']=='four']
    variants = [p for p in base_presentations(updated, mode='standard') if p['condition']=='four']
    for orig, variant in zip(originals,variants):
        if orig['letter_to_strategy'] != variant['letter_to_strategy']:
            raise ValueError('Option order differs')
        for kind, p in (('original',orig),('paraphrase',variant)):
            yield {**p, 'wording':kind, 'condition':'four',
                   'flag_for_review':rewrite.get('flag_for_review',False),
                   'semantic_validation_status':rewrite.get('semantic_validation_status','unverified')}
