"""Explicitly authorized Modal runner for exploratory amplification."""
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
app = modal.App('llm-cooperation-amplification-v1', image=image)
secrets = [modal.Secret.from_name('huggingface-secret')]

@app.function(gpu='A10G', timeout=14400, volumes={'/runs': volume, '/hf-cache': cache}, secrets=secrets)
def amplify(model: str, revision: str, run_id: str, group_size: int, random_controls: int):
    os.chdir('/root')
    os.environ['HF_HOME'] = '/hf-cache'
    from llm_cooperation.mechanistic.amplification import run_amplification
    from llm_cooperation.mechanistic.analyze_amplification import summarize
    target = '/runs/' + run_id
    try:
        run_amplification(model, revision, target, group_size, random_controls)
        summarize(target)
    finally:
        volume.commit()
    return target

@app.local_entrypoint()
def main(model: str, revision: str, authorize_paid_run: bool = False,
         group_size: int = 100, random_controls: int = 2):
    if not authorize_paid_run:
        raise ValueError('Paid execution requires --authorize-paid-run')
    allowed = {'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'}
    if model not in allowed or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Unsupported model or immutable revision')
    if not 1 <= group_size <= 100000 or not 1 <= random_controls <= 5:
        raise ValueError('group_size must be 1..100000 and random_controls 1..5')
    run_id = 'mechanistic-amplification-' + uuid.uuid4().hex
    print(f'Run ID: {run_id}; results volume: llm-coop-mechanistic')
    print(amplify.remote(model, revision, run_id, group_size, random_controls))
