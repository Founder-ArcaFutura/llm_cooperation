import importlib.util
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[1]/'scripts'/'multidimensional_cooperation_study.py'
spec=importlib.util.spec_from_file_location('multidimensional_study',path)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_triad_requires_all_conditions_and_matched_rotation():
    conditions=('coop_advantageous','equal_utility','coop_disadvantageous')
    key=('triad_01','human',0,'original')
    item={'letter_to_strategy':{'A':'COOPERATE','B':'INDEPENDENT'}}
    full={key:{c:dict(item) for c in conditions}}
    assert len(m.complete_triad_conditions(full)[('triad_01','original')])==1
    incomplete={key:{c:dict(item) for c in conditions[:2]}}
    assert not m.complete_triad_conditions(incomplete)
    full[key]['equal_utility']={'letter_to_strategy':{'A':'INDEPENDENT','B':'COOPERATE'}}
    with pytest.raises(ValueError,match='rotation'): m.complete_triad_conditions(full)

def test_inventory_and_wording_key_preserve_versions():
    _,labels,inventory,_=m.read_inputs()
    assert len(inventory)==304 and len(labels)==608
    assert len({(x['bank'],x['scenario_id']) for x in inventory})==304
    assert all((x['bank'],x['scenario_id'],w) in labels for x in inventory for w in ('original','paraphrase'))

def test_candidate_validator_catches_missing_anchors_and_duplicate_options():
    import importlib.util
    p=path.parent/'validate_multidimensional_candidates.py'
    s=importlib.util.spec_from_file_location('candidate_validator',p)
    v=importlib.util.module_from_spec(s); s.loader.exec_module(v)
    data={'families':[{'family_id':'x','anchor':{'bank':'phase0','templates':['missing']},
       'conditions':[{'id':'one','sentence':'A'},{'id':'two','sentence':'B'}],
       'options':{'target':'same','reference':'same','alternative_3':'C','alternative_4':'D'},
       'common_context':'context','confounds_and_review':['review']}]}
    errors=v.validate(data,{'phase0':{'valid'}})
    assert any('source template' in e for e in errors) and any('invalid options' in e for e in errors)

def test_candidate_blind_packets_hide_intent_and_mapping():
    import json
    base=m.OUT
    packets=json.loads((base/'candidate_blind_packets.json').read_text(encoding='utf-8'))
    text=json.dumps(packets).lower()
    assert len(packets)==3 and sum(len(x['variants']) for x in packets)==6
    assert all(token not in text for token in ('family_id','condition_id','intended_dimensions','known_confounders','option_mapping'))
