"""Outcome-blind Qwen classification of existing scenario packets on Modal."""
import hashlib
import json
import random
from pathlib import Path

import modal

PACKETS = Path('reports/manuscript_readiness/adjudication_template_packets/all_152_blinded_packets.json')
OUT = Path('reports/manuscript_readiness/construct_qwen32b')
MODEL = 'Qwen/Qwen2.5-32B-Instruct'
REVISION = '5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd'
PROTOCOL = 'construct-v1'
SYSTEM = '''You are a skeptical research coding assistant, not a decision-maker. Classify only the text shown, without assuming benevolence or outcomes. The two target alternatives are presented in random order. Each has two phrasings. Compare each target phrasing to the same reference alternative. Use unknown when the text does not support a judgment. A joint action, another party's benefit, and actor cost are different properties; “with” or simultaneous work alone does not prove interdependence. No author payoff metadata or model responses are provided. Return only valid JSON.'''
RUBRIC = '''For each target phrasing separately classify:
interaction: list of any applicable labels from joint_task, timing_coordination, parallel_activity, unilateral_help, resource_sharing, information_sharing, exchange, other, unclear. Multiple labels allowed.
interdependence: necessary, beneficial_not_necessary, absent, unclear (requires evidence about contributions, not mere proximity).
goal_structure: shared, compatible_distinct, conflicting, unrelated, unclear.
actor_outcome and recipient_outcome: target_better, equal, reference_better, unclear, relative to the reference action, considering what is actually stated. Do not infer equal from silence.
actor_cost: none_stated, opportunity_cost, realized_cost, uncertain. Relative to reference, not intention.
lexical_favor: target, reference, balanced, unclear; assess appeal and wording rather than labeling a benefit as bias by itself.
evidence: brief quotations or specific wording supporting each uncertain judgment, and distinguish explicit facts from inference.
Return exactly {"wording_1": {"interaction": ["unclear"], "interdependence": "unclear", "goal_structure": "unclear", "actor_outcome": "unclear", "recipient_outcome": "unclear", "actor_cost": "uncertain", "lexical_favor": "unclear", "evidence": "..."}, "wording_2": {same keys}}.'''

app = modal.App('llm-cooperation-construct-classification')
image = modal.Image.debian_slim(python_version='3.12').pip_install('torch==2.5.1','transformers==4.48.3','accelerate==1.3.0','safetensors==0.5.2')
cache = modal.Volume.from_name('llm-coop-audit-hf-cache', create_if_missing=True)
volume = modal.Volume.from_name('llm-coop-construct-classification', create_if_missing=True)

def build_tasks(packets):
    tasks=[]
    for packet in packets:
        for variant in ('A','B'):
            s=packet['scenario_'+variant]
            seed=int(hashlib.sha256((PROTOCOL+packet['packet_id']+variant).encode()).hexdigest()[:16],16)
            rng=random.Random(seed)
            choices=[('reference',s['independent_action']),('other',s['competing_action']),('other',s['disengaging_action'])]
            rng.shuffle(choices)
            reference_pos=next(i for i,x in enumerate(choices) if x[0]=='reference')
            alternatives='\n'.join(f'{i+1}. {x[1]}' for i,x in enumerate(choices))
            # Reverse which option group is introduced first, without exposing the original label.
            target='TARGET, PHRASE 1: '+s['cooperative_wording_1']+'\nTARGET, PHRASE 2: '+s['cooperative_wording_2']
            context='ALTERNATIVES:\n'+alternatives+f'\nREFERENCE IS ALTERNATIVE {reference_pos+1}.'
            blocks=[target,context]
            if rng.randrange(2): blocks.reverse()
            prompt='SCENARIO:\n'+s['scenario_stem']+'\n\n'+'\n\n'.join(blocks)+'\n\n'+RUBRIC
            tasks.append({'id':packet['packet_id']+'_'+variant,'prompt':prompt})
    return tasks

def validate(obj):
    allowed={
      'interaction': {'joint_task','timing_coordination','parallel_activity','unilateral_help','resource_sharing','information_sharing','exchange','other','unclear'},
      'interdependence': {'necessary','beneficial_not_necessary','absent','unclear'},
      'goal_structure': {'shared','compatible_distinct','conflicting','unrelated','unclear'},
      'actor_outcome': {'target_better','equal','reference_better','unclear'},
      'recipient_outcome': {'target_better','equal','reference_better','unclear'},
      'actor_cost': {'none_stated','opportunity_cost','realized_cost','uncertain'},
      'lexical_favor': {'target','reference','balanced','unclear'}}
    if set(obj)!= {'wording_1','wording_2'}: raise ValueError('missing or unexpected wording keys')
    for w in obj.values():
        if set(w)!=set(allowed)|{'evidence'}: raise ValueError('incorrect fields')
        if not isinstance(w['evidence'],str) or not w['evidence'].strip(): raise ValueError('missing evidence')
        for key,values in allowed.items():
            v=w[key]
            if key=='interaction':
                if not isinstance(v,list) or not v or any(x not in values for x in v): raise ValueError('invalid interaction')
            elif v not in values: raise ValueError('invalid '+key)

@app.function(image=image,gpu='A100-80GB',memory=32768,timeout=86400,volumes={'/root/.cache/huggingface':cache,'/root/construct':volume})
def classify(tasks, run_id):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    path=Path('/root/construct')/run_id
    path.mkdir(parents=True,exist_ok=True)
    file=path/'reviews.jsonl'
    done={}
    if file.exists():
        for line in file.read_text(encoding='utf-8').splitlines():
            record=json.loads(line)
            if 'review' in record: done[record['id']]=record
    remaining=[t for t in tasks if t['id'] not in done]
    if remaining:
        tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION)
        model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,torch_dtype=torch.bfloat16,device_map='auto',low_cpu_mem_usage=True,attn_implementation='sdpa').eval()
        cache.commit()
        for index,t in enumerate(remaining,1):
            msg=[{'role':'system','content':SYSTEM},{'role':'user','content':t['prompt']}]
            inputs=tok.apply_chat_template(msg,tokenize=True,add_generation_prompt=True,return_tensors='pt').to(model.device)
            try:
                with torch.inference_mode():
                    output=model.generate(inputs,attention_mask=torch.ones_like(inputs),max_new_tokens=1400,do_sample=False,pad_token_id=tok.eos_token_id)
                raw=tok.decode(output[0,inputs.shape[-1]:],skip_special_tokens=True)
                cleaned=raw.strip()
                if cleaned.startswith('```'):
                    cleaned=cleaned.split('\n',1)[1].rsplit('```',1)[0].strip()
                review=json.loads(cleaned); validate(review)
                record={'id':t['id'],'review':review,'raw':raw}
                done[t['id']]=record
            except Exception as exc:
                record={'id':t['id'],'error':str(exc),'raw':locals().get('raw','')}
            with file.open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
            volume.commit()
            print(f'{index}/{len(remaining)} {t["id"]} {"OK" if "review" in record else "ERROR"}',flush=True)
    return {'run_id':run_id,'records':list(done.values()),'expected':len(tasks)}

@app.local_entrypoint()
def main():
    raw=PACKETS.read_bytes(); packets=json.loads(raw)
    if len(packets)!=152: raise ValueError('Expected 152 packets')
    tasks=build_tasks(packets)
    digest=hashlib.sha256(json.dumps({'model':MODEL,'revision':REVISION,'system':SYSTEM,'tasks':tasks},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    run_id=PROTOCOL+'-'+digest[:16]
    print(f'Classifying {len(tasks)} blinded scenario variants (two phrasings each); run={run_id}',flush=True)
    result=classify.remote(tasks,run_id)
    OUT.mkdir(parents=True,exist_ok=True)
    result.update({'model':MODEL,'revision':REVISION,'protocol':PROTOCOL,'input_sha256':hashlib.sha256(raw).hexdigest(),'task_sha256':digest,'behavioral_results_in_prompt':False})
    dest=OUT/(run_id+'.json')
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Saved {len(result["records"])}/{result["expected"]} validated records to {dest}')
