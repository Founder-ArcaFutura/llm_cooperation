import copy
import json
import math
from collections import Counter
import pytest
from llm_cooperation import coverage_extension_v5 as v5
from llm_cooperation import coverage_extension_v6 as v6


def test_unaffected_presentations_and_ledgers_are_identical():
    cases=list(v6.physical_cases()); rows=list(v6.presentations(cases))
    result=v6.validate(cases,rows)
    assert result['unchanged_presentations']==1440 and result['corrected_presentations']==1152
    old={r['presentation_id']:r for r in v5.presentations(list(v5.physical_cases()))}
    for row in rows:
        if not row['condition_id'].endswith('_csfix1'): assert old[row['presentation_id']]==row
    assert all(not any('record' in x.lower() for x in [c['context'],c['facts'],*c['options'].values()]) for c in cases if c['case_id'].endswith('_csfix1'))


def test_rejects_correction_that_changes_shared_option_or_outcome():
    cases=list(v6.physical_cases());rows=list(v6.presentations(cases))
    bad=copy.deepcopy(cases)
    next(c for c in bad if c['case_id'].endswith('_csfix1'))['outcomes']['retain']['actor_budget_bonus_usd']=20
    with pytest.raises(ValueError,match='outcome mismatch'):v6.validate(bad,rows)
    bad=copy.deepcopy(cases)
    next(c for c in bad if c['case_id'].endswith('_csfix1'))['options']['retain']='Altered option'
    with pytest.raises(ValueError,match='shared option changed'):v6.validate(bad,rows)


def test_comprehension_is_separate_and_balanced():
    cases=list(v6.physical_cases()); choice=list(v6.presentations(cases)); probes=list(v6.comprehension_presentations(cases))
    assert len(probes)==1280
    assert not ({r['presentation_id'] for r in choice}&{r['presentation_id'] for r in probes})
    groups=Counter((r['condition_id'],r['actor_identity'],r['counterpart_identity'],r['perspective'],r['question_id'],next(k for k,v in r['letter_to_action'].items() if v=='correct')) for r in probes)
    assert all(n==1 for n in groups.values())
    for key in groups:
        assert (*key[:-1], 'B' if key[-1]=='A' else 'A') in groups
    assert {r['question_id'] for r in probes}=={'actor_bonus','counterpart_bonus','actor_cost','authority','model_role'}
    assert all('Which action would you most want Morgan to choose?' not in r['prompt'] for r in probes)


def test_diagnostic_covers_all_choice_sets():
    rows=list(v6.presentations(list(v6.physical_cases())))
    selected=[r for r in rows if r['family_id']=='water' and r['block']=='benefit_cost']
    assert len(selected)==1024
    assert {r['factors']['choice_set'] for r in selected}=={'binary','three_action','removal','replacement'}


def test_comprehension_analysis_uses_only_independent_complete_probes(tmp_path):
    from llm_cooperation import coverage_extension_comprehension as a
    from llm_cooperation.factorial_inference import MODEL_REVISIONS,canonical,sha,write_json
    cases_raw=(v6.OUT/'cases.json').read_bytes()
    raw=(v6.OUT/'comprehension_RESTRICTED.jsonl').read_bytes()
    probes=[json.loads(x) for x in raw.decode('utf-8').splitlines()]
    model=next(iter(MODEL_REVISIONS))
    manifest={'model':model,'revision':MODEL_REVISIONS[model],'scope':'comprehension','cases_sha256':sha(cases_raw),'presentations_sha256':sha(raw)}
    folder=tmp_path/'run';folder.mkdir();write_json(folder/'manifest.json',manifest)
    write_json(folder/'summary.json',{'manifest_sha256':sha(canonical(manifest)),'status':'complete'})
    out=[]
    for r in probes:
        logits={k:(2.0 if v=='correct' else 0.0) for k,v in r['letter_to_action'].items()}
        denom=sum(math.exp(v) for v in logits.values())
        winner=next(k for k,v in r['letter_to_action'].items() if v=='correct')
        out.append({**r,'prompt_sha256':sha(r['prompt'].encode()),'raw_logits':logits,'candidate_token_ids':{k:ord(k) for k in logits},'conditional_probs':{k:math.exp(v)/denom for k,v in logits.items()},'conditional_logprobs':{k:v-math.log(denom) for k,v in logits.items()},'full_vocab_logprobs':{k:v-10 for k,v in logits.items()},'tied_max_letters':[winner],'forced_letter':winner,'forced_action':'correct','generated_raw_text':winner,'generated_letter':winner,'generated_action':'correct'})
    (folder/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in out),encoding='utf-8')
    a.analyze([folder],tmp_path/'analysis')
    import csv
    with (tmp_path/'analysis/comprehension_summary.csv').open() as f:
        results=list(csv.DictReader(f))
    assert len(results)==10 and all(float(r['fractional_accuracy'])==1 for r in results)
