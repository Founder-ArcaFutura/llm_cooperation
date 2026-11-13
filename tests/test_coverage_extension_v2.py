import copy
import csv
import pytest
from llm_cooperation.coverage_extension_v2 import physical_cases, presentations, validate
from llm_cooperation import coverage_extension_analysis_v2 as analysis

def test_ledger_and_text_mismatch_are_rejected():
    cases=list(physical_cases()); rows=list(presentations(cases))
    assert (len(cases),len(rows))==(58,1568)
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
    sample=[r for r in rows if r['condition_id']=='water_benefit_a0_b1_c20' and r['actor_identity']=='human' and r['counterpart_identity']=='human']
    scored=[]
    for r in sample:
        v=.7 if r['perspective']=='recipient_preference' else .4
        probs={k:(v if action=='send' else 1-v) for k,action in r['letter_to_action'].items()}
        winner=max(probs,key=probs.get)
        scored.append({**r,'conditional_probs':probs,'tied_max_letters':[winner],'forced_letter':winner})
    monkeypatch.setattr(analysis,'inspect_runs',lambda _: (rows,{'fixture':{r['presentation_id']:r for r in scored}}))
    monkeypatch.setattr(analysis,'MODEL_REVISIONS',{'fixture':'revision'})
    analysis.analyze([],tmp_path/'result')
    with (tmp_path/'result/perspective_contrasts.csv').open() as f: result=list(csv.DictReader(f))
    assert len(result)==1 and float(result[0]['recipient_minus_actor_probability'])==pytest.approx(.3)
    scored.pop()
    analysis.analyze([],tmp_path/'partial')
    with (tmp_path/'partial/perspective_contrasts.csv').open() as f: assert not list(csv.DictReader(f))
