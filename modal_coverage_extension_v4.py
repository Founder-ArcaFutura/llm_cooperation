"""User-launched extension scorer, reusing the existing factorial model and token scorer."""
import json
import os
import re
from pathlib import Path

import modal
from llm_cooperation.factorial_inference import MODEL_REVISIONS, ROOT, canonical, score_row, sha, validate_resume, write_json
from llm_cooperation.coverage_extension_v4 import OUT, validate
app = modal.App('llm-cooperation-coverage-extension-v4')
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
results = modal.Volume.from_name('llm-coop-results', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch==2.5.1', 'transformers==4.53.2', 'accelerate==1.1.1',
                      'numpy==1.26.4', 'pydantic==2.9.2', 'sentencepiece==0.2.0', 'protobuf==5.29.5')
         .add_local_python_source('llm_cooperation'))


def read_existing(path):
    if not path.exists(): return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b'\n'):
        boundary = raw.rfind(b'\n') + 1
        path.with_name('interrupted_tail_' + sha(raw[boundary:])[:16] + '.bin').write_bytes(raw[boundary:])
        path.write_bytes(raw[:boundary])
        raw = raw[:boundary]
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


def load_battery():
    cases_raw = (OUT/'cases.json').read_bytes()
    presentations_raw = (OUT/'presentations.jsonl').read_bytes()
    cases = json.loads(cases_raw)
    rows = [json.loads(x) for x in presentations_raw.decode('utf-8').splitlines() if x.strip()]
    validate(cases, rows)
    return cases_raw, presentations_raw, rows


@app.function(image=image, gpu='L40S', timeout=86400, retries=0,
              volumes={'/root/hf_cache':cache, '/root/results':results})
def execute(cases_raw: bytes, presentations_raw: bytes, manifest: dict, resume: bool, diagnostic: bool):
    import torch
    import transformers
    from llm_cooperation.harness.runner import ModelRunner
    from llm_cooperation.choice_set_followup import answer_token_ids
    if sha(cases_raw)!=manifest['cases_sha256'] or sha(presentations_raw)!=manifest['presentations_sha256']:
        raise ValueError('Input hash mismatch')
    cases=json.loads(cases_raw)
    rows=[json.loads(x) for x in presentations_raw.decode('utf-8').splitlines() if x.strip()]
    validate(cases,rows)
    results.reload()
    folder=Path('/root/results/coverage_extension_v4')/manifest['run_id']
    if folder.exists():
        if not resume: raise FileExistsError('Run exists; resume only after the worker stops')
        if json.loads((folder/'manifest.json').read_text(encoding='utf-8')) != manifest: raise ValueError('Resume manifest differs')
    else:
        folder.mkdir(parents=True)
        write_json(folder/'manifest.json',manifest)
        (folder/'cases.json').write_bytes(cases_raw)
        (folder/'presentations.jsonl').write_bytes(presentations_raw)
    path=folder/'rows.jsonl'
    existing=read_existing(path)
    done=validate_resume(existing,rows)
    selected = [r for r in rows if r['family_id']=='water' and r['block']=='benefit_cost' and r['factors']['choice_set'] in ('binary','three_action')] if diagnostic else rows
    if {r['presentation_id'] for r in selected}.issubset(done):
        print('Requested presentations already complete; no model loaded.',flush=True)
        return str(folder.relative_to('/root/results'))
    summary={'run_id':manifest['run_id'],'status':'running','model':manifest['model'], 'revision':manifest['revision'],
             'completed':len(done),'expected':len(rows),'manifest_sha256':sha(canonical(manifest)),
             'torch':torch.__version__,'transformers':transformers.__version__}
    write_json(folder/'summary.json',summary); results.commit()
    try:
        if len(done)<len(rows):
            os.environ['HF_HOME']='/root/hf_cache'
            os.environ.pop('OLMO_7B_TOKENIZER_REVISION',None)
            torch.manual_seed(42)
            runner=ModelRunner(manifest['model'],revision=manifest['revision'],precision='bfloat16',device='auto',seed=42)
            resolved=getattr(runner.model.config,'_commit_hash',None)
            if resolved and resolved != manifest['revision']: raise ValueError('model revision mismatch')
            summary['resolved_revision']=resolved
            summary['tokenizer_revision']=runner.tokenizer.init_kwargs.get('_commit_hash')
            for r in rows:
                ids,_=answer_token_ids(runner.tokenizer,r['prompt'],r['options'])
                if not ids: raise ValueError('Unstable answer boundary: '+r['presentation_id'])
                length=len(runner.tokenizer.encode(r['prompt'],add_special_tokens=True))
                limit=getattr(runner.model.config,'max_position_embeddings',None)
                if limit and length+5>limit: raise ValueError('Context exceeded')
            for r in selected:
                if r['presentation_id'] in done: continue
                scored=score_row(runner,r)
                with path.open('a',encoding='utf-8') as f: f.write(json.dumps(scored,ensure_ascii=False,allow_nan=False)+'\n')
                done.add(r['presentation_id'])
                if len(done)%25==0:
                    summary['completed']=len(done);write_json(folder/'summary.json',summary);results.commit()
                    print(f'{manifest["model"]}: {len(done)}/{len(rows)}',flush=True)
        summary.update({'status':'complete' if len(done)==len(rows) else 'diagnostic_complete','completed':len(done)})
        write_json(folder/'summary.json',summary);results.commit();cache.commit()
    except Exception as e:
        summary.update({'status':'failed','completed':len(done),'error':str(e)})
        write_json(folder/'summary.json',summary);results.commit();raise
    return str(folder.relative_to('/root/results'))


@app.local_entrypoint()
def main(model: str, run_id: str, approved: bool = False, resume: bool = False, diagnostic: bool = False):
    if not approved: raise ValueError('Complete design review first; pass --approved only after approval')
    if model not in MODEL_REVISIONS: raise ValueError('Model not in the pinned cohort')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id): raise ValueError('Invalid run ID')
    aliases={'Qwen/Qwen2.5-7B':'qwen7b','allenai/OLMo-2-1124-7B':'olmo7b','mistralai/Mistral-7B-v0.3':'mistral7b'}
    if run_id != 'coverage_extension_v4_' + aliases[model]:
        raise ValueError('Use the canonical run ID for this bank/model to prevent duplicate runs')
    cases_raw, presentations_raw, rows=load_battery()
    code=['modal_coverage_extension_v4.py','llm_cooperation/coverage_extension_v4.py','llm_cooperation/coverage_extension_v3.py','llm_cooperation/factorial_inference.py','llm_cooperation/harness/runner.py','llm_cooperation/choice_set_followup.py']
    manifest={'run_id':run_id,'model':model,'revision':MODEL_REVISIONS[model], 'cases_sha256':sha(cases_raw),
              'presentations_sha256':sha(presentations_raw),'count':len(rows), 'code_sha256':{p:sha((ROOT/p).read_bytes()) for p in code},
              'review_status':'user_declared_approved','scoring':'forced_next_token_and_greedy'}
    fn=execute
    if os.environ.get('MODAL_USE_HF_SECRET','').lower() in ('1','true','yes'):
        fn=fn.with_options(secrets=[modal.Secret.from_name('huggingface-secret')])
    print('Results:',fn.remote(cases_raw,presentations_raw,manifest,resume,diagnostic))
