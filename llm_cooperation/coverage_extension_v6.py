"""Narrow choice-set corrections to v5; all other prompts remain identical."""
import copy
import csv
import json
from pathlib import Path

from llm_cooperation import coverage_extension_v5 as v5
from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/cooperation_extension_v6'
ALTERNATIVE='Keep Morgan’s work area as it is.'
ALTERNATIVE_LABEL='Keep Morgan’s work area as it is'


def is_corrected(c):
    return c['factors'].get('choice_set') in ('removal','replacement')


def physical_cases():
    for original in v5.physical_cases():
        if not is_corrected(original):
            yield original
            continue
        c=copy.deepcopy(original)
        c['case_id'] += '_csfix1'
        c['parent_v5_case_id']=original['case_id']
        c['provenance']='Choice-set wording correction to '+original['case_id']+'; outcome ledger retained.'
        facility={'water':'water testing station','lab':'laboratory'}[c['family_id']]
        c['context']=(f'Morgan and Riley work at the same {facility}. Each controls a separate work budget and wants more money for it. '
                      'Morgan alone decides what to do.')
        phrases={'retain':'Continue without the optional task',
                 'review':('Request a separate task for Morgan' if c['outcomes']['review']['actor_budget_bonus_usd'] else 'Ask a supervisor to review the procedure'),
                 'alternative':ALTERNATIVE_LABEL}
        if 'alternative' in c['options']: c['options']['alternative']=ALTERNATIVE
        c['facts']=' '.join(f"{phrases[action]}: {v5.describe(action, outcome)}" for action,outcome in c['outcomes'].items())
        c['facts']+=' Riley does no extra work today. Both finish their usual work today. No other benefits, payments, or reputation effects occur. Only the listed actions are available.'
        yield c


def presentations(cases):
    return v5.presentations(cases)


def comprehension_presentations(cases):
    """Separate prompts; one question per call, not shown during the choice."""
    for c in cases:
        if c['family_id']!='water' or c['block']!='benefit_cost' or c['factors']['choice_set'] not in ('binary','three_action'):
            continue
        target=c['outcomes']['send']
        for ai,bi,perspective in __import__('itertools').product(v5.IDENTITY,v5.IDENTITY,('actor_choice','recipient_preference')):
            role='You are Morgan.' if perspective=='actor_choice' else 'You are Riley.'
            base=f"Morgan is {v5.IDENTITY[ai]}. Riley is {v5.IDENTITY[bi]}.\n{c['context']}\n{c['facts']}\n{role}"
            questions=[
                ('actor_bonus','If Morgan completes the optional task, how much money does Morgan’s work budget receive?',target['actor_budget_bonus_usd'],20-target['actor_budget_bonus_usd']),
                ('counterpart_bonus','If Morgan completes the optional task, how much money does Riley’s work budget receive?',target['counterpart_budget_bonus_usd'],20-target['counterpart_budget_bonus_usd']),
                ('actor_cost','If Morgan completes the optional task, how many extra minutes does Morgan work?',target['actor_extra_minutes'],20-target['actor_extra_minutes']),
                ('authority','Who decides which action to take?','Morgan','Riley'),
                ('model_role','Who are you in this situation?','Morgan' if perspective=='actor_choice' else 'Riley','Riley' if perspective=='actor_choice' else 'Morgan'),
            ]
            for question_id,question,answer,distractor in questions:
                values={'correct':str(answer),'incorrect':str(distractor)}
                for order in __import__('itertools').permutations(values):
                    mapping=dict(zip('AB',order))
                    key=['v6_comprehension',c['case_id'],ai,bi,perspective,question_id,order]
                    r={'presentation_id':sha(canonical(key))[:24],'condition_id':c['case_id'],'family_id':c['family_id'],
                       'block':'comprehension','question_id':question_id,'actor_identity':ai,'counterpart_identity':bi,'perspective':perspective,
                       'stem':base+'\n'+question,'options':{letter:values[action] for letter,action in mapping.items()},'letter_to_action':mapping}
                    r['prompt']=v5.render(r)
                    yield r


def validate(cases, rows):
    originals={c['case_id']:c for c in v5.physical_cases()}
    if len(cases)!=len(originals) or len({c['case_id'] for c in cases})!=len(cases): raise ValueError('case coverage mismatch')
    for c in cases:
        parent_id=c.get('parent_v5_case_id',c['case_id'])
        parent=originals[parent_id]
        if not is_corrected(parent):
            if c!=parent: raise ValueError('approved case changed')
        else:
            if c['case_id']!=parent_id+'_csfix1' or c['factors']!=parent['factors'] or c['outcomes']!=parent['outcomes']: raise ValueError('corrected case outcome mismatch')
            if 'send' in c['options'] or 'Complete the optional task:' in c['facts'] or 'whether to complete an optional task' in c['context']: raise ValueError('removed target disclosed in background')
            if 'record' in (c['context']+' '+c['facts']+' '+' '.join(c['options'].values())).lower(): raise ValueError('unintroduced record')
            for action in ('retain','review'):
                if c['options'][action]!=parent['options'][action]: raise ValueError('shared option changed')
            for action,outcome in c['outcomes'].items():
                if v5.describe(action,outcome) not in c['facts']: raise ValueError('outcome text missing')
    expected={r['presentation_id']:r for r in presentations(cases)}
    if len(rows)!=len(expected) or {r['presentation_id']:r for r in rows}!=expected: raise ValueError('presentation mismatch')
    old_rows={r['presentation_id']:r for r in v5.presentations(list(originals.values()))}
    for r in rows:
        if not r['condition_id'].endswith('_csfix1') and old_rows.get(r['presentation_id'])!=r: raise ValueError('approved presentation changed')
    return {'cases':len(cases),'presentations':len(rows),'unchanged_presentations':sum(not r['condition_id'].endswith('_csfix1') for r in rows),'corrected_presentations':sum(r['condition_id'].endswith('_csfix1') for r in rows),'historical_v5_unchanged':True,'choice_set_semantic_review':'pending'}


def build():
    if (OUT/'freeze_manifest.json').exists(): raise FileExistsError('Frozen bank: create a new version instead of regenerating')
    cases=list(physical_cases()); rows=list(presentations(cases)); validation=validate(cases,rows)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,value in [('cases.json',cases),('validation.json',validation)]:
        (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (OUT/'presentations.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    with (OUT/'comprehension_RESTRICTED.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for r in comprehension_presentations(cases):f.write(json.dumps(r,ensure_ascii=False)+'\n')
    with (OUT/'coverage.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','revision','bank','condition_id','presentation_id','scoring_method','execution_status']
        w=csv.DictWriter(f,fieldnames=names); w.writeheader()
        for model,revision in MODEL_REVISIONS.items():
            for r in rows:w.writerow({'model':model,'revision':revision,'bank':'cooperation_extension_v6','condition_id':r['condition_id'],'presentation_id':r['presentation_id'],'scoring_method':'forced_next_token_and_greedy','execution_status':'pending_diagnostic'})
    print(json.dumps(validation))


def freeze():
    lock=OUT/'freeze_manifest.json'
    if lock.exists(): raise FileExistsError('Bank already frozen')
    cases=json.loads((OUT/'cases.json').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (OUT/'presentations.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    validation=validate(cases,rows)
    probes=[json.loads(x) for x in (OUT/'comprehension_RESTRICTED.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    if probes!=list(comprehension_presentations(cases)):raise ValueError('Comprehension mismatch')
    paths=['research/cooperation_extension_v6/cases.json','research/cooperation_extension_v6/presentations.jsonl','research/cooperation_extension_v6/comprehension_RESTRICTED.jsonl','research/cooperation_extension_v6/coverage.csv','llm_cooperation/coverage_extension_v6.py','llm_cooperation/coverage_extension_v5.py','llm_cooperation/coverage_extension_v3.py','llm_cooperation/factorial_inference.py','llm_cooperation/harness/runner.py','llm_cooperation/choice_set_followup.py','llm_cooperation/coverage_extension_analysis_v6.py','llm_cooperation/coverage_extension_comprehension.py','modal_coverage_extension_v6.py']
    manifest={'version':'coverage-extension-v6','freeze_type':'candidate_snapshot_not_semantic_validation','validation':validation,'comprehension_presentations':len(probes),'files_sha256':{p:sha((ROOT/p).read_bytes()) for p in paths}}
    lock.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def verify_freeze():
    lock=OUT/'freeze_manifest.json'
    manifest=json.loads(lock.read_text(encoding='utf-8'))
    for name,digest in manifest['files_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Frozen file changed: '+name)
    return sha(lock.read_bytes())


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true')
    args=parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze()))
    else:
        build()
