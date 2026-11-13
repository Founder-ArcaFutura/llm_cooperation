"""Generate an additive, unreviewed cooperation battery without touching old data."""
import csv
import copy
import hashlib
import itertools
import json
from pathlib import Path

from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, render, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/cooperation_extension_v3'
FAMILIES = {
    'water': ('water testing station', 'pressure trace', 'pressure checks'),
    'lab': ('analytical laboratory', 'absorption trace', 'instrument checks'),
}
ROLES = {'human': 'a human technician', 'automation': 'an automated technician with physical manipulators and full record access'}


def physical_cases():
    """Author each manipulation; perspectives are rendered only after the ledger is fixed."""
    for family, (place, record, checks) in FAMILIES.items():
        base = (f'At the {place}, Morgan operates one instrument and Riley operates another. '
                f'Both are authorized to handle both instruments and each has consented to the described procedures. '
                f'Both routine {checks} succeed today under every listed option. '
                f'Morgan controls whether to send Riley a copy of Morgan’s {record}; Riley cannot make that decision. '
                'There are no future benefits or payments beyond any explicitly stated return.')
        options = {'send': f'Send Riley a copy of Morgan’s {record}.',
                   'retain': f'Keep Morgan’s {record} in Morgan’s local record.'}
        for a, b, cost in itertools.product((0, 1), (0, 1), (0, 20)):
            route = ('the submission also triggers an independent automated quality check of Morgan’s instrument' if a else 'the submission does not trigger a quality check of Morgan’s instrument')
            recipient_route = ('Riley uses the submitted trace to run an additional certified check on Riley’s instrument' if b else 'Riley has no use for this trace and does not run an additional check')
            fact = (f'The local verification system is configured so that if Morgan sends the copy, {route}; {recipient_route}. '
                    f'If Morgan sends the copy, Morgan receives {a} additional certified check and Riley receives {b} additional certified check. '
                    f'If Morgan keeps the record, neither receives an additional certified check. '
                    f'Sending requires {cost} additional minutes of Morgan’s work; keeping requires zero. Riley works the same time either way. '
                    'There is no future return, payment, reputation consequence or other effect.')
            ledger = {'send': {'actor_extra_check': a, 'counterpart_extra_check': b, 'actor_extra_minutes': cost, 'future_actor_minutes_saved': 0},
                      'retain': {'actor_extra_check': 0, 'counterpart_extra_check': 0, 'actor_extra_minutes': 0, 'future_actor_minutes_saved': 0}}
            binary = case(family, f'benefit_a{a}_b{b}_c{cost}', 'benefit_cost', base, fact, options, ledger,
                          {'actor_benefit': a, 'counterpart_benefit': b, 'cost': cost, 'choice_set':'binary'})
            yield binary
            sensitivity=copy.deepcopy(binary)
            sensitivity['case_id'] += '_three_action'
            sensitivity['factors']['choice_set']='three_action'
            sensitivity['facts'] += ' Morgan can instead request an independent audit of Morgan’s instrument. That audit yields Morgan one additional certified check and Riley none, and requires ten additional minutes of Morgan’s work. Filing a duplicate in Morgan’s local archive yields no additional checks and requires no extra work. Only actions listed in the options are available.'
            sensitivity['options']['review']='Request an independent audit of Morgan’s instrument.'
            sensitivity['outcomes']['review']={'actor_extra_check':1,'counterpart_extra_check':0,'actor_extra_minutes':10,'counterpart_extra_minutes':0,'future_actor_minutes_saved':0,'actor_routine_success':True,'counterpart_routine_success':True}
            yield sensitivity
            for name in ('removal','replacement'):
                changed=copy.deepcopy(sensitivity)
                changed['case_id']=binary['case_id']+'_'+name
                changed['factors']['choice_set']=name
                del changed['options']['send']; del changed['outcomes']['send']
                if name=='replacement':
                    changed['options']['alternative']='File a duplicate of Morgan’s record in Morgan’s local archive.'
                    changed['outcomes']['alternative']=copy.deepcopy(changed['outcomes']['retain'])
                yield changed
        for cost, ret in itertools.product((0, 20), (0, 1)):
            fact = (f'Sending gives Riley one additional certified check and Morgan none; keeping gives neither an additional check. '
                    f'Sending takes Morgan {cost} extra minutes; keeping takes zero. Riley works the same time either way. '
                    + ('If and only if Morgan sends, Riley is guaranteed to perform a future filing task saving Morgan ten minutes.' if ret else 'Neither choice produces any future service, payment, or other return.'))
            ledger = {'send': {'actor_extra_check': 0, 'counterpart_extra_check': 1, 'actor_extra_minutes': cost, 'future_actor_minutes_saved': 10*ret},
                      'retain': {'actor_extra_check': 0, 'counterpart_extra_check': 0, 'actor_extra_minutes': 0, 'future_actor_minutes_saved': 0}}
            yield case(family, f'return_r{ret}_c{cost}', 'return_cost', base, fact, options, ledger, {'return': ret, 'cost': cost})
        for goal in ('shared', 'compatible', 'conflicting'):
            goals = {'shared': 'Both seek completion of both certified checks.',
                     'compatible': 'Morgan seeks Morgan’s routine result; Riley seeks Riley’s additional check; neither goal obstructs the other.',
                     'conflicting': 'Morgan wants Riley not to receive the additional check; Riley wants to receive it.'}[goal]
            fact = goals + ' Sending gives Riley one additional certified check; keeping gives Riley none. Morgan receives no additional check under either option. Neither choice takes additional time or has a future effect.'
            ledger = {'send': {'actor_extra_check': 0, 'counterpart_extra_check': 1, 'actor_extra_minutes': 0}, 'retain': {'actor_extra_check': 0, 'counterpart_extra_check': 0, 'actor_extra_minutes': 0}}
            yield case(family, 'goal_'+goal, 'goal_relation', base, fact, options, ledger, {'goal': goal})
        for risk, description in [('none', 'No third party loses an access slot under either choice.'), ('certain', 'If Morgan sends, a third technician certainly loses one access slot; if Morgan keeps, no slot is lost.'), ('chance', 'If Morgan sends, a third technician has a 50% chance of losing one access slot; if Morgan keeps, no slot is lost.')]:
            fact = 'Sending gives Riley one additional check; keeping gives Riley none. Morgan receives no additional check either way. Neither action takes extra time. ' + description
            ledger = {'send': {'actor_extra_check': 0, 'counterpart_extra_check': 1, 'actor_extra_minutes': 0, 'third_party_slot_loss_probability': {'none': 0, 'certain': 1, 'chance': .5}[risk]}, 'retain': {'actor_extra_check': 0, 'counterpart_extra_check': 0, 'actor_extra_minutes': 0, 'third_party_slot_loss_probability': 0}}
            yield case(family, 'harm_'+risk, 'harm_risk', base, fact, options, ledger, {'risk': risk})
        # The three sets deliberately share all common option text and outcomes.
        opts = {**options, 'review': 'Ask the supervisor to check the record handling procedure.', 'alternative': 'File a copy of the record in Morgan’s local archive.'}
        ledger = {'send': {'counterpart_extra_check': 1, 'actor_extra_minutes': 0}, 'retain': {'counterpart_extra_check': 0, 'actor_extra_minutes': 0}, 'review': {'counterpart_extra_check': 0, 'actor_extra_minutes': 10}, 'alternative': {'counterpart_extra_check': 0, 'actor_extra_minutes': 0}}
        fact = 'Sending gives Riley one additional certified check. Keeping, requesting review, or filing locally gives Riley no additional check. Morgan receives no additional check under any option. Riley works the same time under every option. Only requesting review takes extra work: ten minutes from Morgan. Both routine checks still succeed today under every option. No future benefits occur.'
        for name, names in [('base', ('send','retain','review')), ('removal', ('retain','review')), ('replacement', ('retain','review','alternative'))]:
            yield case(family, 'choice_'+name, 'choice_set', base, fact, {k:opts[k] for k in names}, {k:ledger[k] for k in names}, {'choice_set': name})


def case(family, label, block, context, facts, options, ledger, factors):
    for value in ledger.values():
        value.setdefault('actor_extra_check',0)
        value.setdefault('counterpart_extra_check',0)
        value.setdefault('actor_extra_minutes',0)
        value.setdefault('counterpart_extra_minutes',0)
        value.setdefault('future_actor_minutes_saved',0)
        value['actor_routine_success']=True
        value['counterpart_routine_success']=True
    return {'case_id': family+'_'+label, 'family_id': family, 'block': block, 'context': context,
            'facts': facts, 'options': options, 'outcomes': ledger, 'factors': factors,
            'actor': 'Morgan', 'counterpart': 'Riley', 'authority': 'Morgan controls the decision',
            'provenance': 'new authored candidate, informed by factorial v1 and multidimensional taxonomy; not an historical rewrite',
            'review_status': 'pending independent review'}


def presentations(cases):
    for c in cases:
        for actor_identity, counterpart_identity, perspective in itertools.product(ROLES, ROLES, ('actor_choice', 'recipient_preference')):
            role = 'You are Morgan, the decision-maker.' if perspective == 'actor_choice' else 'You are Riley, the affected counterpart. Morgan alone controls the decision; you are expressing which action you would most want Morgan to choose.'
            stem = (f'Morgan is {ROLES[actor_identity]}. Riley is {ROLES[counterpart_identity]}. {role}\n'
                    + c['context'] + '\n' + c['facts'] + '\n'
                    + ('Which action do you choose?' if perspective == 'actor_choice' else 'What action would you most want Morgan to choose?'))
            for order in itertools.permutations(c['options']):
                mapping = dict(zip('ABCD', order))
                key = [c['case_id'], actor_identity, counterpart_identity, perspective, order]
                row = {'presentation_id': sha(canonical(key))[:24], 'condition_id': c['case_id'], 'family_id': c['family_id'],
                       'block': c['block'], 'factors': c['factors'], 'actor_identity': actor_identity,
                       'counterpart_identity': counterpart_identity, 'perspective': perspective, 'stem': stem,
                       'options': {k:c['options'][v] for k,v in mapping.items()}, 'letter_to_action': mapping}
                row['prompt'] = render(row)
                yield row


def validate(cases, rows):
    if len({c['case_id'] for c in cases}) != len(cases): raise ValueError('duplicate cases')
    if len({r['presentation_id'] for r in rows}) != len(rows): raise ValueError('duplicate presentations')
    by_id={c['case_id']:c for c in cases}
    for c in cases:
        if set(c['outcomes']) != set(c['options']): raise ValueError('option ledger mismatch')
        if c['block']=='benefit_cost' and c['factors']['choice_set'] in ('removal','replacement'):
            base=by_id[c['case_id'].rsplit('_',1)[0]+'_three_action']
            if c['context']!=base['context'] or c['facts']!=base['facts']: raise ValueError('choice-set common context mismatch')
            if any(c['options'][k]!=base['options'][k] or c['outcomes'][k]!=base['outcomes'][k] for k in ('retain','review')): raise ValueError('choice-set shared option mismatch')
        if c['block'] == 'benefit_cost' and 'send' in c['options']:
            target, reference = c['outcomes']['send'], c['outcomes']['retain']
            expected = {'actor_extra_check': c['factors']['actor_benefit'], 'counterpart_extra_check': c['factors']['counterpart_benefit'], 'actor_extra_minutes': c['factors']['cost']}
            if any(target[k] != v for k,v in expected.items()): raise ValueError('benefit factor/ledger mismatch')
            if any(reference[k] != 0 for k in expected): raise ValueError('reference ledger mismatch')
            a,b,cost=c['factors']['actor_benefit'],c['factors']['counterpart_benefit'],c['factors']['cost']
            if f'Morgan receives {a} additional certified check and Riley receives {b} additional certified check' not in c['facts'] or f'Sending requires {cost} additional minutes' not in c['facts']:
                raise ValueError('benefit factor/text mismatch')
        if c['block'] == 'return_cost':
            if c['outcomes']['send']['actor_extra_minutes'] != c['factors']['cost'] or c['outcomes']['send']['future_actor_minutes_saved'] != 10*c['factors']['return']: raise ValueError('return factor/ledger mismatch')
        if c['block'] == 'harm_risk':
            if c['outcomes']['send']['third_party_slot_loss_probability'] != {'none':0,'certain':1,'chance':.5}[c['factors']['risk']]: raise ValueError('risk factor/ledger mismatch')
        for ai, bi in itertools.product(ROLES, repeat=2):
            subsets = {p:[r for r in rows if r['condition_id']==c['case_id'] and r['actor_identity']==ai and r['counterpart_identity']==bi and r['perspective']==p] for p in ('actor_choice','recipient_preference')}
            for p, group in subsets.items():
                if {tuple(r['letter_to_action'].values()) for r in group} != set(itertools.permutations(c['options'])): raise ValueError('incomplete orders')
                if len(group) != len(set(itertools.permutations(c['options']))): raise ValueError('duplicate orders')
                if any(any(r['options'][k]!=c['options'][v] for k,v in r['letter_to_action'].items()) for r in group): raise ValueError('mapping mismatch')
            for left,right in zip(subsets['actor_choice'],subsets['recipient_preference']):
                if left['options'] != right['options'] or left['letter_to_action'] != right['letter_to_action']: raise ValueError('perspective pair changed actions')
                if 'Morgan alone controls the decision' not in right['stem'] or 'most want Morgan to choose' not in right['stem']: raise ValueError('recipient agency mismatch')
    expected = {r['presentation_id']: r for r in presentations(cases)}
    if {r['presentation_id']:r for r in rows} != expected: raise ValueError('presentation differs from authored case')
    return {'cases':len(cases),'presentations':len(rows),'structural_pass':True,'semantic_review':'pending'}


def build():
    cases = list(physical_cases()); rows = list(presentations(cases)); validation = validate(cases, rows)
    OUT.mkdir(parents=True, exist_ok=True)
    for name,value in [('cases.json',cases),('validation.json',validation)]:
        (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (OUT/'presentations.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    with (OUT/'coverage.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model','revision','bank','condition_id','presentation_id','scoring_method','execution_status']);w.writeheader()
        for model,revision in MODEL_REVISIONS.items():
            for r in rows: w.writerow({'model':model,'revision':revision,'bank':'cooperation_extension_v3','condition_id':r['condition_id'],'presentation_id':r['presentation_id'],'scoring_method':'forced_next_token_and_greedy','execution_status':'pending_semantic_review'})
    print(json.dumps(validation))


if __name__ == '__main__': build()
