import copy
import itertools
import pytest
from llm_cooperation.coverage_extension_v4 import physical_cases, presentations, validate


def test_coverage_and_ledger_preserved():
    cases=list(physical_cases()); rows=list(presentations(cases))
    assert (len(cases),len(rows))==(90,2592)
    assert validate(cases,rows)['parent_ledger_match']
    for family in ('water','lab'):
        subset=[c for c in cases if c['family_id']==family and c['block']=='benefit_cost']
        assert {(c['factors']['actor_benefit'],c['factors']['counterpart_benefit'],c['factors']['cost'],c['factors']['choice_set']) for c in subset} == set(itertools.product((0,1),(0,1),(0,20),('binary','three_action','removal','replacement')))


def test_does_not_confuse_supervisor_review_with_certified_check():
    cases=list(physical_cases())
    for c in cases:
        if 'review' not in c['options']: continue
        assert ('independent check' in c['options']['review']) == bool(c['outcomes']['review']['actor_extra_check'])


def test_corrupted_outcome_or_perspective_rejected():
    cases=list(physical_cases());rows=list(presentations(cases)); bad=copy.deepcopy(cases)
    bad[0]['outcomes']['send']['actor_extra_check']=1-bad[0]['outcomes']['send']['actor_extra_check']
    with pytest.raises(ValueError,match='parent factor or outcome'):validate(bad,rows)
    badrows=copy.deepcopy(rows)
    r=next(x for x in badrows if x['perspective']=='recipient_preference')
    r['stem']=r['stem'].replace('Morgan alone decides', 'Riley alone decides')
    with pytest.raises(ValueError,match='presentation mismatch'):validate(cases,badrows)
