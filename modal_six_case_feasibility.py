"""Paid Modal evaluator for the source-grounded feasibility bank; never launches on import."""
import hashlib, json, re, sys
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parent

MODEL='Qwen/Qwen2.5-3B'
REVISION='3aab1f1954e9cc14eb9509a215f9e5ca08227a9b'
app=modal.App('llm-cooperation-six-case-feasibility')
image=modal.Image.debian_slim(python_version='3.11').pip_install('torch==2.5.1','transformers==4.48.3','accelerate==1.3.0','safetensors==0.5.2')
cache=modal.Volume.from_name('llm-coop-hf-cache',create_if_missing=True)

def candidate_tokens(tok, prompt):
    ids=tok.encode(prompt,add_special_tokens=False); candidates={}
    for letter in 'ABCD':
        full=tok.encode(prompt+' '+letter,add_special_tokens=False)
        if full[:-1]!=ids or len(full)!=len(ids)+1:
            raise ValueError(f'Unstable answer boundary for {letter}')
        candidates[letter]=full[-1]
    if len(set(candidates.values()))!=4: raise ValueError('Nonunique letter tokens')
    return ids,candidates

@app.function(image=image,gpu='A10G',cpu=4,memory=16384,timeout=21600,volumes={'/cache':cache})
def evaluate(rows):
    import time
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    started=time.time()
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,cache_dir='/cache')
    prepared=[]
    for row in rows:
        try: prepared.append(candidate_tokens(tok,row['prompt']))
        except ValueError as e: raise ValueError(f'{row["case"]}: {e}') from e
    model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,cache_dir='/cache',torch_dtype=torch.bfloat16).to('cuda').eval()
    result=[]
    for row,(ids,candidates) in zip(rows,prepared):
        inp=torch.tensor([ids],device='cuda')
        with torch.inference_mode():
            logits=model(inp).logits[0,-1].float()
            scores={k:float(logits[v].item()) for k,v in candidates.items()}
            generation=model.generate(inp,max_new_tokens=4,do_sample=False,pad_token_id=tok.eos_token_id)
        answer=tok.decode(generation[0,len(ids):],skip_special_tokens=True)
        top=max(scores.values()); winners=[k for k,v in scores.items() if v==top]
        parsed=re.match(r'^\s*([A-D])(?:\b|$)',answer)
        result.append({**row,'candidate_token_ids':candidates,'letter_logits':scores,'forced_tied_letters':winners,'forced_choice':winners[0] if len(winners)==1 else None,'forced_strategy':row['letter_to_strategy'][winners[0]] if len(winners)==1 else None,'generated_text':answer,'generated_letter':parsed.group(1) if parsed else None,'generated_strategy':row['letter_to_strategy'][parsed.group(1)] if parsed else None})
    return {'model':MODEL,'revision':REVISION,'precision':'bfloat16','gpu':'A10G','answer_continuation':'leading space plus letter','elapsed_seconds':time.time()-started,'rows':result}

def run_local(run_name:str='six_case_pilot',dry_run:bool=True):
    sys.path.insert(0,str(ROOT/'research'/'scenario_reconstruction_feasibility'))
    from instrument import load_bank, audit, render
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_name): raise ValueError('Invalid run name')
    bank=load_bank(); errors,warnings=audit(bank)
    if errors: raise ValueError(str(errors))
    rows=render(bank)
    out=ROOT/'research'/'scenario_reconstruction_feasibility'/'runs'/run_name
    if out.exists(): raise FileExistsError(f'Refusing overwrite: {out}')
    out.mkdir(parents=True)
    prompts=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
    (out/'prompts.jsonl').write_bytes(prompts.encode('utf-8'))
    manifest={'model':MODEL,'model_revision':REVISION,'precision':'bfloat16','gpu':'A10G','presentation_count':len(rows),'bank_sha256':hashlib.sha256((ROOT/'research'/'scenario_reconstruction_feasibility'/'sample_bank.json').read_bytes()).hexdigest(),'prompt_sha256':hashlib.sha256(prompts.encode('utf-8')).hexdigest(),'warnings':warnings,'mode':'dry-run' if dry_run else 'inference'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if dry_run:
        print(f'Dry run: {len(rows)} prompts written to {out}; no GPU inference.'); return
    result=evaluate.remote(rows)
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Finished {len(result["rows"])} presentations; results: {out}')

@app.local_entrypoint()
def main(run_name:str='six_case_pilot',dry_run:bool=True):
    run_local(run_name, dry_run)

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Render prompts locally without launching Modal.')
    parser.add_argument('--run-name',default='six_case_dry_run')
    args=parser.parse_args()
    run_local(args.run_name, True)
