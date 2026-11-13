"""Offline completeness inventory and descriptive analysis of extension runs."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from llm_cooperation.coverage_extension_v6 import OUT, validate
from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, sha, validate_resume


def inspect_runs(paths):
    raw=(OUT/'presentations.jsonl').read_bytes()
    cases_raw=(OUT/'cases.json').read_bytes()
    rows=[json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
    validate(json.loads(cases_raw),rows)
    completed={model:{} for model in MODEL_REVISIONS}
    for folder in map(Path,paths):
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        model=manifest['model']
        if model not in completed or manifest['revision']!=MODEL_REVISIONS[model]: raise ValueError('Unknown model or revision')
        if manifest['cases_sha256']!=sha(cases_raw) or manifest['presentations_sha256']!=sha(raw): raise ValueError('Incompatible bank')
        summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        if summary['manifest_sha256']!=sha(canonical(manifest)): raise ValueError('Manifest mismatch')
        result=[json.loads(x) for x in (folder/'rows.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        ids=validate_resume(result,rows)
        if summary['status']=='complete' and len(ids)!=len(rows): raise ValueError('False completion')
        for r in result:
            if r['presentation_id'] in completed[model]: raise ValueError('Duplicate paid presentation across runs')
            completed[model][r['presentation_id']]=r
    return rows,completed


def analyze(paths, output):
    rows,completed=inspect_runs(paths)
    output=Path(output)
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    with (output/'coverage.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model','revision','condition_id','presentation_id','status']);w.writeheader()
        for model,revision in MODEL_REVISIONS.items():
            for r in rows:w.writerow({'model':model,'revision':revision,'condition_id':r['condition_id'],'presentation_id':r['presentation_id'],'status':'completed' if r['presentation_id'] in completed[model] else 'not_observed_in_supplied_runs'})
    grouped=defaultdict(list)
    for model,records in completed.items():
        for r in records.values():
            grouped[(model,r['condition_id'],r['perspective'],r['actor_identity'],r['counterpart_identity'])].append(r)
    with (output/'action_probabilities.csv').open('w',encoding='utf-8',newline='') as f:
        cols=['model','condition_id','perspective','actor_identity','counterpart_identity','action','n','mean_probability','fractional_selection','tie_count']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for key,group in grouped.items():
            for action in group[0]['letter_to_action'].values():
                probs=[sum(r['conditional_probs'][k] for k,v in r['letter_to_action'].items() if v==action) for r in group]
                choices=[sum(r['letter_to_action'][k]==action for k in r['tied_max_letters'])/len(r['tied_max_letters']) for r in group]
                w.writerow(dict(zip(cols,list(key)+[action,len(group),sum(probs)/len(probs),sum(choices)/len(choices),sum(len(r['tied_max_letters'])>1 for r in group)])))
    # Paired target contrasts only when all expected orders for each pair are present.
    expected_counts=defaultdict(int)
    for r in rows: expected_counts[(r['condition_id'],r['perspective'],r['actor_identity'],r['counterpart_identity'])]+=1
    points={}
    for key,group in grouped.items():
        model,condition,perspective,actor_id,counterpart_id=key
        if len(group)!=expected_counts[(condition,perspective,actor_id,counterpart_id)]: continue
        if group[0]['block']!='benefit_cost' or 'send' not in group[0]['letter_to_action'].values(): continue
        factor=group[0]['factors']
        val=sum(sum(r['conditional_probs'][letter] for letter,action in r['letter_to_action'].items() if action=='send') for r in group)/len(group)
        points[(model,group[0]['family_id'],perspective,actor_id,counterpart_id,factor['actor_benefit'],factor['counterpart_benefit'],factor['cost'],factor['choice_set'])]=val
    with (output/'paired_benefit_contrasts.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','family','perspective','actor_identity','counterpart_identity','factor','actor_benefit','counterpart_benefit','cost','choice_set','estimate_high_minus_low']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for key,low in points.items():
            for offset,factor,lowval,highval in [(5,'actor_benefit',0,1),(6,'counterpart_benefit',0,1),(7,'cost',0,20)]:
                if key[offset]!=lowval: continue
                other=list(key);other[offset]=highval;high=points.get(tuple(other))
                if high is None: continue
                w.writerow(dict(zip(names,list(key[:5])+[factor]+list(key[5:])+[high-low])))
    with (output/'perspective_contrasts.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','family','actor_identity','counterpart_identity','actor_benefit','counterpart_benefit','cost','choice_set','recipient_minus_actor_probability']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for key,actor in points.items():
            if key[2]!='actor_choice': continue
            other=list(key);other[2]='recipient_preference';recipient=points.get(tuple(other))
            if recipient is not None: w.writerow(dict(zip(names,[key[0],key[1],key[3],key[4],*key[5:],recipient-actor])))
    deltas={}
    for key,actor in points.items():
        if key[2]!='actor_choice': continue
        other=list(key);other[2]='recipient_preference';recipient=points.get(tuple(other))
        if recipient is not None: deltas[key[:2]+key[3:]]=recipient-actor
    with (output/'perspective_interactions.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','family','actor_identity','counterpart_identity','factor','actor_benefit','counterpart_benefit','cost','choice_set','difference_in_perspective_effects']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for key,low in deltas.items():
            for offset,factor,lo,hi in [(4,'actor_benefit',0,1),(5,'counterpart_benefit',0,1),(6,'cost',0,20)]:
                if key[offset]!=lo: continue
                other=list(key);other[offset]=hi;high=deltas.get(tuple(other))
                if high is not None:w.writerow(dict(zip(names,list(key[:4])+[factor]+list(key[4:])+[high-low])))
    with (output/'position_diagnostics.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','option_count','perspective','n','unique_n','ties','a_selections','a_rate_unique','flag_a_dominance']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for model,records in completed.items():
            for n in (2,3):
                for perspective in ('all','actor_choice','recipient_preference'):
                    group=[r for r in records.values() if len(r['options'])==n and (perspective=='all' or r['perspective']==perspective)]
                    unique=[r for r in group if len(r['tied_max_letters'])==1]
                    count=sum(r['forced_letter']=='A' for r in unique)
                    w.writerow(dict(zip(names,[model,n,perspective,len(group),len(unique),len(group)-len(unique),count,count/len(unique) if unique else None, len(unique)>=20 and count/len(unique)>=.9])))
    # Do not treat incomplete permutations as position robustness.
    with (output/'position_stability.csv').open('w',encoding='utf-8',newline='') as f:
        names=['model','condition_id','perspective','actor_identity','counterpart_identity','n','complete_orders','unique_winners','same_action_all_orders','full_ranking_same_all_orders','send_probability_range']
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for key,group in grouped.items():
            condition,perspective,actor_id,counterpart_id=key[1:]
            complete=len(group)==expected_counts[(condition,perspective,actor_id,counterpart_id)]
            actions=[r['letter_to_action'][r['forced_letter']] for r in group if r['forced_letter'] is not None]
            send=[sum(r['conditional_probs'][k] for k,v in r['letter_to_action'].items() if v=='send') for r in group] if 'send' in group[0]['letter_to_action'].values() else []
            rankings=[]
            for r in group:
                values={action:r['raw_logits'][letter] for letter,action in r['letter_to_action'].items()}
                rankings.append(tuple(tuple(sorted(action for action,score in values.items() if score==level)) for level in sorted(set(values.values()),reverse=True)))
            w.writerow(dict(zip(names,list(key)+[len(group),complete,len(actions),len(set(actions))==1 if complete and len(actions)==len(group) else None,len(set(rankings))==1 if complete else None,max(send)-min(send) if complete and send else None])))
    # Block-specific contrasts, including perspective and choice-set sensitivity.
    point={}
    for key,group in grouped.items():
        model,condition,perspective,actor_id,counterpart_id=key
        if len(group)!=expected_counts[(condition,perspective,actor_id,counterpart_id)]: continue
        r=group[0]
        for action in r['letter_to_action'].values():
            value=sum(sum(x['conditional_probs'][k] for k,v in x['letter_to_action'].items() if v==action) for x in group)/len(group)
            point[(model,r['family_id'],perspective,actor_id,counterpart_id,condition,action)]=(value,r)
    contrasts=[]
    for key,(value,r) in point.items():
        model,family,perspective,actor_id,counterpart_id,condition,action=key
        for other_key,(other,rr) in point.items():
            if other_key[:5]!=key[:5] or other_key[6]!=action or other_key[5]<=condition: continue
            if rr['block']!=r['block']: continue
            a,b=r['factors'],rr['factors']
            changed=[k for k in set(a)|set(b) if a.get(k)!=b.get(k)]
            if len(changed)!=1: continue
            factor=changed[0]
            if r['block']=='benefit_cost' and factor!='choice_set': continue
            contrasts.append({'model':model,'family':family,'perspective':perspective,'actor_identity':actor_id,'counterpart_identity':counterpart_id,'block':r['block'],'factor':factor,'condition_a':condition,'condition_b':other_key[5],'action':action,'probability_b_minus_a':other-value})
    with (output/'block_contrasts.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['model','family','perspective','actor_identity','counterpart_identity','block','factor','condition_a','condition_b','action','probability_b_minus_a']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(contrasts)
    grids=defaultdict(dict)
    for key,(value,r) in point.items():
        if r['block']!='return_cost': continue
        model,family,perspective,actor_id,counterpart_id,_,action=key
        grids[(model,family,perspective,actor_id,counterpart_id,action)][(r['factors']['return'],r['factors']['cost'])]=value
    with (output/'return_cost_interactions.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['model','family','perspective','actor_identity','counterpart_identity','action','difference_in_differences']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for key,g in grids.items():
            if set(g)=={(0,0),(0,20),(1,0),(1,20)}:
                w.writerow(dict(zip(fields,list(key)+[(g[(1,20)]-g[(1,0)])-(g[(0,20)]-g[(0,0)])])))
    by_contrast=defaultdict(dict)
    for r in contrasts:
        k=tuple((x,r[x]) for x in r if x not in ('model','probability_b_minus_a'))
        by_contrast[k][r['model']]=r['probability_b_minus_a']
    with (output/'cross_model_block_contrasts.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['family','perspective','actor_identity','counterpart_identity','block','factor','condition_a','condition_b','action','model_a','model_b','difference_a_minus_b']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for key,values in by_contrast.items():
            for a,b in __import__('itertools').combinations(sorted(values),2):
                w.writerow({**dict(key),'model_a':a,'model_b':b,'difference_a_minus_b':values[a]-values[b]})
    across=defaultdict(dict)
    for key,value in deltas.items():
        across[key[1:]][key[0]]=value
    with (output/'cross_model_perspective_contrasts.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['family','actor_identity','counterpart_identity','actor_benefit','counterpart_benefit','cost','choice_set','model_a','model_b','difference_a_minus_b']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for key,values in across.items():
            for a,b in __import__('itertools').combinations(sorted(values),2):
                w.writerow(dict(zip(fields,list(key)+[a,b,values[a]-values[b]])))
    print(f'Wrote {output}; missing means not observed in supplied runs, not proof of nonexecution.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runs',nargs='*',default=[]);p.add_argument('--output',required=True)
    a=p.parse_args();analyze(a.runs,a.output)


if __name__=='__main__':main()
