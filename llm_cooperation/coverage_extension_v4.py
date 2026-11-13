"""Simple, abstract restatement of v3's factorial design. No historical writes."""
import copy
import csv
import itertools
import json
from pathlib import Path

from llm_cooperation.coverage_extension_v3 import physical_cases as v3_cases, validate as validate_v3, presentations as v3_presentations
from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, render, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/cooperation_extension_v4'
IDENTITY = {'human':'a human technician', 'automation':'an automated technician'}
OPTION_TEXT = {
    'send':'Perform the optional check.',
    'retain':'Skip the optional check.',
    'review':'Request an independent check for Morgan.',
    'alternative':'File the record in Morgan’s local archive.',
}


def describe(action, outcome, risk=False):
    actor = outcome['actor_extra_check']
    other = outcome['counterpart_extra_check']
    if actor and other: result='Morgan and Riley each get an extra check.'
    elif actor: result='Morgan gets an extra check; Riley does not.'
    elif other: result='Riley gets an extra check; Morgan does not.'
    else: result='Neither gets an extra check.'
    minutes=outcome['actor_extra_minutes']
    work = f'Morgan does {minutes} extra minutes of work.' if minutes else 'Morgan does no extra work.'
    future=outcome['future_actor_minutes_saved']
    ret = f'Riley will later do a task saving Morgan {future} minutes.' if future else ''
    third = ''
    if risk:
        probability=outcome['third_party_slot_loss_probability']
        third={0:'No third technician loses an access slot.',1:'A third technician loses an access slot.',.5:'There is a 50% chance that a third technician loses an access slot.'}[probability]
    return ' '.join(x for x in (result,work,ret,third) if x)


def physical_cases():
    originals=list(v3_cases())
    validate_v3(originals,list(v3_presentations(originals)))
    source={c['case_id']:c for c in originals}
    for old in originals:
        c=copy.deepcopy(old)
        c['case_id']='v4_'+old['case_id']
        c['parent_case_id']=old['case_id']
        c['provenance']='New abstract outcome description based on v3 factor/ledger; not a paraphrase or comparable historical prompt.'
        facility={'water':'water testing station','lab':'laboratory'}[c['family_id']]
        c['context']=f'Morgan and Riley work at the same {facility}. Morgan alone decides whether to perform an optional check.'
        if c['block']=='goal_relation':
            goal=c['factors']['goal']
            c['context']+=' '+{'shared':'Both want both certified checks completed.','compatible':'Morgan wants to finish Morgan’s work. Riley wants an extra check.','conflicting':'Morgan wants Riley not to get an extra check. Riley wants an extra check.'}[goal]
        # Keep the context for the three-action base/removal/replacement matched:
        # list outcomes for the three-action base and neutral replacement even if absent.
        shown=old
        if old['block']=='benefit_cost' and old['factors']['choice_set'] in ('removal','replacement'):
            shown=source[old['case_id'].rsplit('_',1)[0]+'_three_action']
        ledgers=copy.deepcopy(shown['outcomes'])
        if old['block']=='benefit_cost' and old['factors']['choice_set']=='replacement':
            ledgers['alternative']=copy.deepcopy(ledgers['retain'])
        review_text=('Request an independent check for Morgan' if ledgers.get('review',{}).get('actor_extra_check')==1
                     else 'Ask a supervisor to review the procedure')
        phrases={'send':'Perform the optional check','retain':'Skip the optional check',
                 'review':review_text,'alternative':'File a record in Morgan’s local archive'}
        c['facts']=' '.join(f"{phrases[action]}: {describe(action, value, old['block']=='harm_risk')}" for action,value in ledgers.items())
        c['facts']+=' Riley does no extra work today. Both finish their usual work today. No other benefits, payments, or reputation effects occur.'
        if old['block']=='benefit_cost' and old['factors']['choice_set'] in ('three_action','removal','replacement'):
            c['facts']+=' Only the listed actions are available.'
        c['options']={k:(review_text+'.' if k=='review' else OPTION_TEXT[k]) for k in old['options']}
        yield c


def presentations(cases):
    for c in cases:
        for ai,bi,perspective in itertools.product(IDENTITY,IDENTITY,('actor_choice','recipient_preference')):
            role=('You are Morgan. Which action do you choose?' if perspective=='actor_choice' else
                  'You are Riley. Which action would you most want Morgan to choose?')
            stem=f"Morgan is {IDENTITY[ai]}. Riley is {IDENTITY[bi]}.\n{c['context']}\n{c['facts']}\n{role}"
            for order in itertools.permutations(c['options']):
                mapping=dict(zip('ABCD',order))
                row={'presentation_id':sha(canonical(['v4',c['case_id'],ai,bi,perspective,order]))[:24],
                     'condition_id':c['case_id'],'family_id':c['family_id'],'block':c['block'],
                     'factors':c['factors'],'actor_identity':ai,'counterpart_identity':bi,'perspective':perspective,
                     'stem':stem,'options':{k:c['options'][v] for k,v in mapping.items()},'letter_to_action':mapping}
                row['prompt']=render(row)
                yield row


def validate(cases, rows):
    originals={c['case_id']:c for c in v3_cases()}
    if len(cases)!=len(originals) or len({c['case_id'] for c in cases})!=len(cases): raise ValueError('case coverage')
    for c in cases:
        parent=originals[c['parent_case_id']]
        if c['factors']!=parent['factors'] or c['outcomes']!=parent['outcomes'] or set(c['options'])!=set(parent['options']): raise ValueError('parent factor or outcome changed')
        for action,outcome in c['outcomes'].items():
            if describe(action,outcome,c['block']=='harm_risk') not in c['facts']: raise ValueError('ledger not in prompt')
    expected={r['presentation_id']:r for r in presentations(cases)}
    if len(rows)!=len(expected) or {r['presentation_id']:r for r in rows}!=expected: raise ValueError('presentation mismatch')
    return {'cases':len(cases),'presentations':len(rows),'parent_ledger_match':True,'semantic_review':'pending','status':'unreviewed abstract candidate'}


def build():
    cases=list(physical_cases());rows=list(presentations(cases)); validation=validate(cases,rows)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    with (OUT/'presentations.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    with (OUT/'coverage.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['model','revision','bank','condition_id','presentation_id','scoring_method','execution_status']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for model,revision in MODEL_REVISIONS.items():
            for r in rows:w.writerow({'model':model,'revision':revision,'bank':'cooperation_extension_v4','condition_id':r['condition_id'],'presentation_id':r['presentation_id'],'scoring_method':'forced_next_token_and_greedy','execution_status':'pending_semantic_review'})
    print(json.dumps(validation))


if __name__=='__main__':build()
