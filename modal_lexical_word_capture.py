"""Single bounded lexical capture per explicitly authorized Modal invocation."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parent
PLAN=ROOT/'research/lexical_strategy_bridge_v1/frozen'
SOURCE=ROOT/'research/lexical_strategy_bridge_v1/capture.py'
app=modal.App('llm-cooperation-lexical-words-v1')
volume=modal.Volume.from_name('llm-cooperation-cross-model-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12').pip_install('numpy==2.3.1','transformers==5.5.4','torch==2.10.0','tokenizers==0.22.1','huggingface-hub==1.33.0','accelerate>=1.0'))

def validate(model,action,tag,inference,paid,full):
    if model not in ('qwen','olmo7b','mistral7b') or action not in ('smoke','full') or not re.fullmatch(r'[a-zA-Z0-9_-]{1,48}',tag): raise ValueError('Invalid model, action or tag')
    if not inference or not paid or (action=='full' and not full): raise PermissionError('Explicit inference and paid authorization required; full capture requires its own authorization')
    m=(PLAN/'manifest.json').read_bytes(); inventory=(PLAN/'inventory.jsonl').read_bytes(); plan=json.loads(m)
    if hashlib.sha256(inventory).hexdigest()!=plan['inventory_sha256']: raise ValueError('Frozen inventory differs from manifest')
    return m,inventory,SOURCE.read_bytes()

@app.function(image=image,gpu='A100-80GB',volumes={'/mnt/evidence':volume},timeout=14400)
def run_capture(model,action,tag,manifest,inventory,source):
    root=Path('/mnt/evidence/lexical_words_v1')
    dest=root/f'{model}_{action}_{tag}'
    if dest.exists(): raise FileExistsError('Output tag already exists; inspect preserved evidence')
    dest.mkdir(parents=True); plan=dest/'plan'; plan.mkdir()
    (plan/'manifest.json').write_bytes(manifest); (plan/'inventory.jsonl').write_bytes(inventory)
    code=dest/'capture.py'; code.write_bytes(source)
    cmd=[sys.executable,str(code),'--plan',str(plan),'--model',model,'--output',str(dest/'capture'),'--condition','isolated','--authorize-gpu-capture']
    if action=='smoke': cmd.extend(['--limit','10'])
    try:
        subprocess.run(cmd,check=True,timeout=1200 if action=='smoke' else 14100)
    finally:
        volume.commit()
    return {'artifact_path':str(dest),'receipt':json.loads((dest/'capture/receipt.json').read_text())}

@app.local_entrypoint()
def main(model: str='', action: str='', tag: str='', authorize_inference: bool=False, authorize_paid_run: bool=False, authorize_full_capture: bool=False):
    manifest,inventory,source=validate(model,action,tag,authorize_inference,authorize_paid_run,authorize_full_capture)
    print(json.dumps(run_capture.remote(model,action,tag,manifest,inventory,source),indent=2))
