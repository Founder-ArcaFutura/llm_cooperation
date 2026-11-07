"""Capture input-boundary lexical states on a CUDA host; no generation."""
import argparse, hashlib, json, os, time
from pathlib import Path
import numpy as np

def sha(data): return hashlib.sha256(data).hexdigest()

def token_positions(offsets, start, end):
    span=[i for i,(a,b) in enumerate(offsets) if b>a and b>start and a<end]
    if not span or min(offsets[i][0] for i in span)>start or max(offsets[i][1] for i in span)<end:
        raise ValueError('Lexical span not covered')
    final=[i for i,(a,b) in enumerate(offsets) if b>a][-1]
    return span, final

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--model', choices=['qwen','olmo7b','mistral7b'], required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int, default=0, help='0 means full inventory; use a small positive value for smoke')
    p.add_argument('--local-files-only', action='store_true')
    p.add_argument('--condition', choices=['isolated','neutral'], default='isolated')
    p.add_argument('--authorize-gpu-capture', action='store_true', help='Required after explicit authorization for this capture')
    args=p.parse_args()
    if args.limit < 0: raise ValueError('limit must be nonnegative')
    if not args.authorize_gpu_capture: raise RuntimeError('GPU capture requires explicit authorization')
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available(): raise RuntimeError('CUDA is required for real-weight capture')
    manifest=json.loads((args.plan/'manifest.json').read_text(encoding='utf-8'))
    payload=(args.plan/'inventory.jsonl').read_bytes()
    if sha(payload)!=manifest['inventory_sha256']: raise ValueError('inventory hash mismatch')
    rows=[json.loads(line) for line in payload.splitlines()]
    rows=[row for row in rows if row['condition']==args.condition]
    if len(rows)!=1000: raise ValueError('Expected 1000 lexical entries in condition')
    if args.limit: rows=rows[:args.limit]
    state=manifest['models'][args.model]
    identity={'plan_sha256':sha((args.plan/'manifest.json').read_bytes()),'model':args.model,
              'revision':state['revision'],'condition':args.condition,'limit':args.limit,'dtype':'float32'}
    args.output.mkdir(parents=True,exist_ok=True)
    identity_path=args.output/'capture_identity.json'
    if identity_path.exists():
        if json.loads(identity_path.read_text(encoding='utf-8')) != identity: raise ValueError('output identity differs')
    else: identity_path.write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8')
    t=time.monotonic()
    tok=AutoTokenizer.from_pretrained(state['model_id'],revision=state['revision'],use_fast=True,local_files_only=args.local_files_only)
    if not tok.is_fast: raise ValueError('Fast tokenizer offsets required')
    model=AutoModelForCausalLM.from_pretrained(state['model_id'],revision=state['revision'],torch_dtype=torch.float32,local_files_only=args.local_files_only).cuda().eval()
    layers=model.model.layers
    if len(layers)!=state['num_layers']: raise ValueError('Unexpected decoder layer count')
    indices=state['indices']; results={}; handles=[]
    for i in indices:
        def hook(_module,_inputs,output,i=i):
            value=output[0] if isinstance(output,tuple) else output
            results[i]=value.detach().float().cpu().numpy()[0]
        handles.append(layers[i].register_forward_hook(hook))
    capture_dir=args.output/'records'; capture_dir.mkdir(exist_ok=True)
    processed=0
    for row in rows:
        name=f"{row['id']}_{row['language']}_{row['condition']}"
        meta=capture_dir/(name+'.json'); data=capture_dir/(name+'.npz')
        if meta.exists() and data.exists():
            saved=json.loads(meta.read_text(encoding='utf-8'))
            if saved['record'] != row or saved['sha256'] != sha(data.read_bytes()): raise ValueError(f'Corrupt saved record {name}')
            continue
        if meta.exists() or data.exists(): raise ValueError(f'Incomplete record {name}; preserve and inspect before recovery')
        enc=tok(row['text'],add_special_tokens=True,return_offsets_mapping=True,return_tensors='pt')
        offsets=enc.pop('offset_mapping')[0].tolist(); ids=enc['input_ids'][0].tolist()
        start,end=row['lexical_chars']
        span,final=token_positions(offsets,start,end)
        results.clear()
        with torch.inference_mode(): model.model(**{k:v.cuda() for k,v in enc.items()},use_cache=False)
        lexical=np.stack([results[i][span].mean(axis=0) for i in indices])
        boundary=np.stack([results[i][final] for i in indices])
        if lexical.shape != (8,state['hidden_size']) or not np.isfinite(lexical).all() or not np.isfinite(boundary).all(): raise ValueError('Invalid activations')
        tmp=data.with_suffix('.tmp.npz'); np.savez_compressed(tmp,lexical=lexical,final=boundary); os.replace(tmp,data)
        record={'record':row,'input_ids':ids,'offsets':offsets,'lexical_token_indices':span,'final_token_index':final,'sha256':sha(data.read_bytes())}
        tmp_meta=meta.with_suffix('.tmp'); tmp_meta.write_text(json.dumps(record,ensure_ascii=False)+'\n',encoding='utf-8'); os.replace(tmp_meta,meta)
        processed+=1
    for h in handles: h.remove()
    receipt={'identity':identity,'total_records':len(rows),'new_records':processed,'elapsed_seconds_including_load':time.monotonic()-t,
             'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'complete':True,'smoke':bool(args.limit)}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
