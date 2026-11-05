"""Separate delayed-mapping pilot. Preparation is offline; execution needs authorization."""
import os
import uuid
from pathlib import Path

import modal

volume = modal.Volume.from_name('llm-coop-mechanistic', create_if_missing=True)
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch==2.5.1', 'transformers==4.46.3', 'accelerate==1.1.1', 'numpy==1.26.4')
         .add_local_python_source('llm_cooperation'))
app = modal.App('llm-cooperation-delayed-mapping-v1', image=image)


@app.function(gpu='A10G', timeout=14400, retries=0,
              volumes={'/runs': volume, '/hf-cache': cache})
def pilot(model: str, revision: str, run_id: str, plan_files: dict,
          dtype: str, generate: bool):
    os.environ['HF_HOME'] = '/hf-cache'
    from llm_cooperation.mechanistic.delayed_mapping import run
    from llm_cooperation.mechanistic.plan_transport import unpack_plan
    plan = unpack_plan(Path('/tmp') / (run_id + '-plan'), plan_files)
    try:
        run(plan, '/runs/' + run_id, model, revision, True, dtype, generate)
    finally:
        volume.commit()
    return '/runs/' + run_id


@app.local_entrypoint()
def main(plan: str, revision: str, model: str = 'Qwen/Qwen2.5-1.5B',
         dtype: str = 'float32', generate: bool = False, authorize_paid_run: bool = False):
    if not authorize_paid_run:
        raise ValueError('Paid execution requires --authorize-paid-run')
    import re
    from llm_cooperation.mechanistic.delayed_mapping import read_plan
    from llm_cooperation.mechanistic.plan_transport import pack_plan
    if model not in ('Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B') or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Supply supported small base model and immutable revision')
    if dtype not in ('float32', 'bfloat16'):
        raise ValueError('Unsupported dtype')
    manifest, _ = read_plan(plan)
    files = pack_plan(plan)
    run_id = 'delayed-mapping-' + uuid.uuid4().hex
    print(f'Run ID: {run_id}; volume: llm-coop-mechanistic; {manifest["presentations"]} presentations')
    print('A10G, 4-hour timeout, no retry, no dollar cap. Preserve failed runs.')
    print(pilot.remote(model, revision, run_id, files, dtype, generate))
