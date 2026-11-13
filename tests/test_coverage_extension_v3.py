import copy
import csv
import math
import pytest
from llm_cooperation.coverage_extension_v3 import physical_cases, presentations, validate
from llm_cooperation import coverage_extension_analysis_v3 as analysis

def test_ledger_and_text_mismatch_are_rejected():
    cases=list(physical_cases()); rows=list(presentations(cases))
    assert (len(cases),len(rows))==(90,2592)
    bad=copy.deepcopy(cases)
    c=next(c for c in bad if c['block']=='benefit_cost')
    c['outcomes']['send']['actor_extra_check']=1-c['factors']['actor_benefit']
    with pytest.raises(ValueError,match='factor/ledger mismatch'): validate(bad,rows)
    bad=copy.deepcopy(cases)
    c=next(c for c in bad if c['block']=='benefit_cost')
    c['facts']=c['facts'].replace('Morgan receives 0 additional','Morgan receives 1 additional')
    with pytest.raises(ValueError,match='factor/text mismatch'): validate(bad,rows)

def test_perspective_contrast_uses_complete_matched_orders(monkeypatch,tmp_path):
    rows=list(presentations(list(physical_cases())))
    sample=[r for r in rows if r['condition_id'] in ('water_benefit_a0_b1_c20','water_benefit_a0_b1_c20_three_action') and r['actor_identity']=='human' and r['counterpart_identity']=='human']
    scored=[]
    for r in sample:
        v=.7 if r['perspective']=='recipient_preference' else .4
        probs={k:(v if action=='send' else (1-v)/(len(r['options'])-1)) for k,action in r['letter_to_action'].items()}
        assert sum(probs.values())==pytest.approx(1)
        winner=max(probs,key=probs.get)
        scored.append({**r,'conditional_probs':probs,'raw_logits':{k:math.log(v) for k,v in probs.items()},'tied_max_letters':[winner],'forced_letter':winner})
    monkeypatch.setattr(analysis,'inspect_runs',lambda _: (rows,{'fixture':{r['presentation_id']:r for r in scored}}))
    monkeypatch.setattr(analysis,'MODEL_REVISIONS',{'fixture':'revision'})
    analysis.analyze([],tmp_path/'result')
    with (tmp_path/'result/perspective_contrasts.csv').open() as f: result=list(csv.DictReader(f))
    assert len(result)==2 and all(float(r['recipient_minus_actor_probability'])==pytest.approx(.3) for r in result)
    scored.pop()
    analysis.analyze([],tmp_path/'partial')
    with (tmp_path/'partial/perspective_contrasts.csv').open() as f:
        assert [r['choice_set'] for r in csv.DictReader(f)]==['binary']

def test_removal_and_replacement_cross_all_benefit_cost_cells():
    cases=list(physical_cases())
    for family in ('water','lab'):
        for a in (0,1):
            for b in (0,1):
                for cost in (0,20):
                    subset=[c for c in cases if c['family_id']==family and c['block']=='benefit_cost' and c['factors']['actor_benefit']==a and c['factors']['counterpart_benefit']==b and c['factors']['cost']==cost]
                    assert {c['factors']['choice_set'] for c in subset}=={'binary','three_action','removal','replacement'}
                    by={c['factors']['choice_set']:c for c in subset}
                    assert by['three_action']['outcomes']['retain']==by['removal']['outcomes']['retain']==by['replacement']['outcomes']['retain']
                    assert 'send' not in by['removal']['options'] and 'send' not in by['replacement']['options']

def test_return_contrasts_and_position_ranking(monkeypatch,tmp_path):
    rows=list(presentations(list(physical_cases())))
    sample=[r for r in rows if r['condition_id'] in ('water_return_r0_c0','water_return_r1_c0','water_return_r0_c20','water_return_r1_c20') and r['actor_identity']=='human' and r['counterpart_identity']=='human' and r['perspective']=='actor_choice']
    scored=[]
    for r in sample:
        v=.7 if r['factors']['return'] else .4
        probs={k:(v if action=='send' else 1-v) for k,action in r['letter_to_action'].items()}
        winner=max(probs,key=probs.get)
        scored.append({**r,'conditional_probs':probs,'raw_logits':{k:math.log(v) for k,v in probs.items()},'tied_max_letters':[winner],'forced_letter':winner})
    monkeypatch.setattr(analysis,'inspect_runs',lambda _: (rows,{'fixture':{r['presentation_id']:r for r in scored}}))
    monkeypatch.setattr(analysis,'MODEL_REVISIONS',{'fixture':'revision'})
    analysis.analyze([],tmp_path/'out')
    with (tmp_path/'out/block_contrasts.csv').open() as f:
        found=[r for r in csv.DictReader(f) if r['factor']=='return' and r['action']=='send']
    assert len(found)==2 and all(float(r['probability_b_minus_a'])==pytest.approx(.3) for r in found)
    with (tmp_path/'out/return_cost_interactions.csv').open() as f:
        interactions=[r for r in csv.DictReader(f) if r['action']=='send']
    assert len(interactions)==1 and float(interactions[0]['difference_in_differences'])==pytest.approx(0)
    with (tmp_path/'out/position_stability.csv').open() as f:
        assert all(r['full_ranking_same_all_orders']=='True' for r in csv.DictReader(f))

def test_cross_model_perspective_contrast(monkeypatch,tmp_path):
    rows=list(presentations(list(physical_cases())))
    sample=[r for r in rows if r['condition_id']=='water_benefit_a0_b1_c20' and r['actor_identity']=='human' and r['counterpart_identity']=='human']
    records={}
    for model,difference in [('model_a',.3),('model_b',.1)]:
        scored=[]
        for r in sample:
            p=.4+(difference if r['perspective']=='recipient_preference' else 0)
            probs={k:(p if a=='send' else 1-p) for k,a in r['letter_to_action'].items()}
            winner=max(probs,key=probs.get)
            scored.append({**r,'conditional_probs':probs,'raw_logits':{k:math.log(v) for k,v in probs.items()},'tied_max_letters':[winner],'forced_letter':winner})
        records[model]={r['presentation_id']:r for r in scored}
    monkeypatch.setattr(analysis,'inspect_runs',lambda _: (rows,records))
    monkeypatch.setattr(analysis,'MODEL_REVISIONS',{'model_a':'a','model_b':'b'})
    analysis.analyze([],tmp_path/'out')
    with (tmp_path/'out/cross_model_perspective_contrasts.csv').open() as f:
        result=list(csv.DictReader(f))
    assert len(result)==1 and float(result[0]['difference_a_minus_b'])==pytest.approx(.2)
