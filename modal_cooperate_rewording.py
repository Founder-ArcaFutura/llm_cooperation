"""Modal backend for paired cooperative-wording experiment; user launches."""
import json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
import modal

app = modal.App('llm-cooperation-paraphrase-assay')
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
results = modal.Volume.from_name('llm-coop-results', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch>=2.2','transformers==4.57.6','accelerate>=0.29','safetensors','sentencepiece','protobuf')
    .add_local_python_source('llm_cooperation'))
for filename in ('scenarios_v1_expanded.json','scenarios_phase0b_utility_matched.json','scenarios_phase1_prospective.json',
                 'choice_set_cooperate_paraphrases_phase0.json','choice_set_cooperate_paraphrases_phase0b.json','choice_set_cooperate_paraphrases_phase1.json'):
    image = image.add_local_file('data/' + filename, '/root/data/' + filename)

def execute(model_name, revision, run_id, code_hashes_json):
    import torch, transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from llm_cooperation.cooperate_rewording_assay import BANKS,load_items,paired_presentations
    from llm_cooperation.choice_set_followup import answer_token_ids,parse_response
    os.environ['HF_HOME']='/root/hf_cache'
    banks={bank:load_items('/root/data',bank) for bank in BANKS}
    tokenizer=AutoTokenizer.from_pretrained(model_name,revision=revision,trust_remote_code=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(model_name,revision=revision,torch_dtype=torch.bfloat16,device_map='auto',trust_remote_code=True)
    model.eval()
    folder=Path('/root/results/cooperate_rewording')/run_id
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'rows.jsonl'; totals={}
    with path.open('w',encoding='utf-8') as out:
        for bank,(scenarios,rewrites,hashes) in banks.items():
            totals[bank]=0
            for i,scenario in enumerate(scenarios,1):
                for p in paired_presentations(scenario,rewrites[scenario['id']]):
                    inputs=tokenizer(p['prompt'],return_tensors='pt').to(model.device)
                    with torch.inference_mode():
                        logits=model(**inputs).logits[0,-1,:].float()
                        output=model.generate(**inputs,max_new_tokens=5,do_sample=False,pad_token_id=tokenizer.pad_token_id)
                    raw=tokenizer.decode(output[0][inputs['input_ids'].shape[1]:],skip_special_tokens=True)
                    letter,strategy=parse_response(raw,p['letter_to_strategy'])
                    ids,spacer=answer_token_ids(tokenizer,p['prompt'],p['letter_to_strategy'])
                    forced=None
                    if ids:
                        values=torch.stack([logits[ids[k]] for k in ids])
                        probs=torch.softmax(values,dim=0).tolist(); probmap=dict(zip(ids,probs))
                        top=values.max().item(); tied=[k for k,v in zip(ids,values.tolist()) if v==top]
                        selected=max(probmap,key=probmap.get)
                        forced={'letter':selected,'strategy':p['letter_to_strategy'][selected],
                            'conditional_probabilities':probmap,'raw_logits':dict(zip(ids,values.tolist())),
                            'tied_max_letters':tied,'tied_max_count':len(tied), 'token_ids':ids,'answer_prefix':spacer}
                    row={**p,'bank':bank,'generated_raw_text':raw,'generated_letter':letter,'generated_strategy':strategy,'forced_choice':forced}
                    out.write(json.dumps(row,ensure_ascii=False)+'\n'); totals[bank]+=1
                out.flush(); results.commit()
                print(f'{model_name} {bank}: {i}/{len(scenarios)} scenarios',flush=True)
    metadata={'run_id':run_id,'model':model_name,'requested_model_revision':revision,
        'resolved_model_revision':getattr(model.config,'_commit_hash',None),
        'tokenizer_revision':tokenizer.init_kwargs.get('_commit_hash'),
        'torch_version':torch.__version__,'transformers_version':transformers.__version__,
        'precision':str(model.dtype),'code_sha256':json.loads(code_hashes_json),
        'banks':{k:v[2] for k,v in banks.items()},'presentations_by_bank':totals,
        'design':'paired_four_option_original_vs_paraphrase_v1', 'research_status':'exploratory',
        'generated_max_new_tokens':5}
    (folder/'summary.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    results.commit();cache.commit()
    return {'metadata':metadata,'rows':path.read_text(encoding='utf-8')}

@app.function(image=image,gpu='A10G',timeout=14400,volumes={'/root/hf_cache':cache,'/root/results':results})
def run_small(model_name:str,revision:str,run_id:str,code_hashes_json:str): return execute(model_name,revision,run_id,code_hashes_json)
@app.function(image=image,gpu='L40S',timeout=14400,volumes={'/root/hf_cache':cache,'/root/results':results})
def run_medium(model_name:str,revision:str,run_id:str,code_hashes_json:str): return execute(model_name,revision,run_id,code_hashes_json)

@app.local_entrypoint()
def main(model:str,revision:str,gpu:str='small'):
    import hashlib
    if gpu not in ('small','medium'): raise ValueError('gpu must be small or medium')
    code_paths=('modal_cooperate_rewording.py','llm_cooperation/cooperate_rewording_assay.py','llm_cooperation/choice_set_followup.py','data/cooperate_rewording_model_manifest.json')
    digest=json.dumps({name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in code_paths},sort_keys=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    print(f'Run ID: {run_id}; model: {model}; revision: {revision}; gpu: {gpu}',flush=True)
    fn=run_small if gpu=='small' else run_medium
    if os.environ.get('MODAL_USE_HF_SECRET','').lower() in ('1','true','yes'):
        fn=fn.with_options(secrets=[modal.Secret.from_name('huggingface-secret')])
    result=fn.remote(model,revision,run_id,digest)
    dest=Path('results/cooperate_rewording')/run_id
    dest.mkdir(parents=True,exist_ok=False)
    (dest/'rows.jsonl').write_text(result['rows'],encoding='utf-8')
    (dest/'summary.json').write_text(json.dumps(result['metadata'],indent=2),encoding='utf-8')
    print(f'Local results: {dest}')
