import copy
import itertools
import pytest
from llm_cooperation.coverage_extension_v5 import physical_cases, presentations, validate


def test_explicit_benefits_and_no_benefit_controls():
    cases=list(physical_cases()); rows=list(presentations(cases))
    assert (len(cases),len(rows))==(90,2592)
    assert validate(cases,rows)['factor_and_outcome_mapping_match']
    for family in ('water','lab'):
        subset=[c for c in cases if c['family_id']==family and c['block']=='benefit_cost' and c['factors']['choice_set']=='binary']
        assert {(c['factors']['actor_benefit'],c['factors']['counterpart_benefit'],c['factors']['cost']) for c in subset}==set(itertools.product((0,1),(0,1),(0,20)))
        for c in subset:
            target=c['outcomes']['send']; f=c['factors']
            assert target['actor_budget_bonus_usd']==20*f['actor_benefit']
            assert target['counterpart_budget_bonus_usd']==20*f['counterpart_benefit']
            assert target['actor_extra_minutes']==f['cost']
            assert c['outcomes']['retain']['actor_budget_bonus_usd']==0
            assert c['outcomes']['retain']['counterpart_budget_bonus_usd']==0
            assert 'check' not in c['facts'].lower()


def test_changed_dollars_or_role_are_rejected():
    cases=list(physical_cases()); rows=list(presentations(cases))
    bad=copy.deepcopy(cases)
    bad[0]['outcomes']['send']['actor_budget_bonus_usd']=999
    with pytest.raises(ValueError,match='mapped outcome'):validate(bad,rows)
    badrows=copy.deepcopy(rows)
    r=next(r for r in badrows if r['perspective']=='recipient_preference')
    r['stem']=r['stem'].replace('Morgan alone decides','Riley alone decides')
    with pytest.raises(ValueError,match='presentation mismatch'):validate(cases,badrows)


def test_recipient_preference_and_conditional_return():
    cases=list(physical_cases()); rows=list(presentations(cases))
    for c in cases:
        if c['block']=='return_cost' and c['factors']['return']:
            assert 'Riley will later do a task saving Morgan 10 minutes.' in c['facts']
            assert 'Riley does no extra work today.' in c['facts']
    for r in rows:
        if r['perspective']=='recipient_preference':
            assert 'You are Riley.' in r['prompt'] and 'Morgan alone decides' in r['prompt']
            assert 'most want Morgan to choose' in r['prompt']
