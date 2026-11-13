"""Structural checks only; passing cannot establish meaning or validity."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/multidimensional_cooperation_v1/candidate_families_v1.json'
BANKS={'phase0':'data/scenarios_v1_expanded.json','phase0b':'data/scenarios_phase0b_utility_matched.json','phase1':'data/scenarios_phase1_prospective.json'}

def validate(data,banks):
    errors=[]; ids=set()
    for family in data.get('families',[]):
        fid=family.get('family_id')
        if not fid or fid in ids: errors.append('Missing or duplicate family id')
        ids.add(fid)
        bank=family.get('anchor',{}).get('bank'); templates=family.get('anchor',{}).get('templates',[])
        if bank not in banks: errors.append(f'{fid}: unknown bank')
        elif not templates or not set(templates)<=banks[bank]: errors.append(f'{fid}: missing source template')
        conditions=family.get('conditions',[])
        if len(conditions)<2 or len({x.get('id') for x in conditions})!=len(conditions) or any(not x.get('sentence') for x in conditions): errors.append(f'{fid}: invalid conditions')
        if set(family.get('options',{}))!={'target','reference','alternative_3','alternative_4'} or len(set(family.get('options',{}).values()))!=4: errors.append(f'{fid}: invalid options')
        if not family.get('common_context') or not family.get('confounds_and_review'): errors.append(f'{fid}: missing context or limitations')
    return errors

def main():
    data=json.loads(DATA.read_text(encoding='utf-8'))
    banks={bank:{s['template_id'] for s in json.loads((ROOT/path).read_text(encoding='utf-8'))['scenarios']} for bank,path in BANKS.items()}
    errors=validate(data,banks)
    for error in errors: print(error)
    if errors: raise SystemExit(1)
    print(f"{len(data['families'])} candidate families pass structural checks only; scientific review remains required")

if __name__=='__main__': main()
