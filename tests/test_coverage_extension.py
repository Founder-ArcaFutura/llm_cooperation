import itertools
import pytest
from llm_cooperation.coverage_extension import physical_cases, presentations, validate


def test_complete_cross_and_perspective_preserves_physical_situation():
    cases=list(physical_cases()); rows=list(presentations(cases))
    assert len(cases)==42 and len(rows)==800
    assert validate(cases,rows)['structural_pass']
    for family in ('water','lab'):
        subset=[c for c in cases if c['family_id']==family and c['block']=='benefit_cost']
        assert {(c['factors']['actor_benefit'],c['factors']['counterpart_benefit'],c['factors']['cost']) for c in subset} == set(itertools.product((0,1),(0,1),(0,20)))
    row=next(r for r in rows if r['perspective']=='recipient_preference')
    assert 'You are Riley' in row['stem'] and 'Morgan alone controls the decision' in row['stem']
    assert 'What action would you most want Morgan to choose?' in row['stem']


def test_choice_sets_keep_shared_text_and_ledgers():
    cases=list(physical_cases())
    for family in ('water','lab'):
        groups={c['factors']['choice_set']:c for c in cases if c['family_id']==family and c['block']=='choice_set'}
        base,removal,replacement=(groups[x] for x in ('base','removal','replacement'))
        assert set(base['options'])=={'send','retain','review'}
        assert set(removal['options'])=={'retain','review'}
        assert set(replacement['options'])=={'retain','review','alternative'}
        for option in ('retain','review'):
            assert base['options'][option]==removal['options'][option]==replacement['options'][option]
            assert base['outcomes'][option]==removal['outcomes'][option]==replacement['outcomes'][option]


def test_detect_corrupt_mapping_and_missing_order():
    cases=list(physical_cases()); rows=list(presentations(cases))
    with pytest.raises(ValueError,match='incomplete orders'): validate(cases,rows[1:])
    rows[0]['options']['A']='different action'
    with pytest.raises(ValueError,match='mapping mismatch'): validate(cases,rows)
