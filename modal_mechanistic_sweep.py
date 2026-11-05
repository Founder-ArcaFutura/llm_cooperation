"""Paid GPU sweep; does nothing until explicitly launched with authorization."""
import os
import re
import uuid
import modal

volume = modal.Volume.from_name('llm-coop-mechanistic', create_if_missing=True)
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('torch==2.5.1', 'transformers==4.46.3', 'accelerate==1.1.1', 'pydantic==2.9.2', 'numpy==1.26.4')
    .add_local_python_source('llm_cooperation')
    .add_local_file('data/scenarios_phase0b_utility_matched.json', '/root/data/scenarios_phase0b_utility_matched.json')
    .add_local_file('data/calibration_bank.json', '/root/data/calibration_bank.json'))
app = modal.App('llm-cooperation-mechanistic-sweep-v1', image=image)
secrets = [modal.Secret.from_name('huggingface-secret')]

@app.function(gpu='A10G', timeout=14400, volumes={'/runs': volume, '/hf-cache': cache}, secrets=secrets)
def sweep(model: str, revision: str, run_id: str, doses: list[int], random_controls: int):
    os.chdir('/root')
    os.environ['HF_HOME'] = '/hf-cache'
    from llm_cooperation.mechanistic.sweep import run_sweep
    from llm_cooperation.mechanistic.analyze_sweep import summarize
    target = '/runs/' + run_id
    try:
        run_sweep(model, revision, target, doses, random_controls)
        summarize(target)
    finally:
        volume.commit()
    return target

@app.local_entrypoint()
def main(model: str, revision: str, authorize_paid_run: bool = False,
         doses: str = '10,100,500,1000', random_controls: int = 3):
    if not authorize_paid_run:
        raise ValueError('Paid execution requires --authorize-paid-run')
    allowed = {'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'}
    if model not in allowed or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Unsupported model or immutable revision')
    values = [int(v) for v in doses.split(',')]
    if not values or values != sorted(set(values)) or values[0] < 1 or values[-1] > 100000 or not 1 <= random_controls <= 5:
        raise ValueError('Doses must increase within 1..100000; random controls must be 1..5')
    run_id = 'mechanistic-sweep-' + uuid.uuid4().hex
    print(f'Run ID: {run_id}; results volume: llm-coop-mechanistic')
    print(sweep.remote(model, revision, run_id, values, random_controls))
