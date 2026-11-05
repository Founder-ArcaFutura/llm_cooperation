"""Explicitly authorized, bounded Modal entry point for the exploratory MLP screen."""
import os
import uuid
import modal

volume = modal.Volume.from_name('llm-coop-mechanistic', create_if_missing=True)
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('torch==2.5.1', 'transformers==4.46.3', 'accelerate==1.1.1', 'pydantic==2.9.2', 'numpy==1.26.4')
    .add_local_python_source('llm_cooperation')
    .add_local_file('data/scenarios_phase0b_utility_matched.json', '/root/data/scenarios_phase0b_utility_matched.json')
    .add_local_file('data/calibration_bank.json', '/root/data/calibration_bank.json'))
app = modal.App('llm-cooperation-mechanistic-v1', image=image)
secrets = [modal.Secret.from_name('huggingface-secret')] if os.environ.get('MODAL_USE_HF_SECRET') == '1' else []

@app.function(gpu='A10G', timeout=7200, volumes={'/runs': volume, '/hf-cache': cache}, secrets=secrets)
def screen(model: str, revision: str, run_id: str, top_k: int):
    os.chdir('/root')
    os.environ['HF_HOME'] = '/hf-cache'
    from llm_cooperation.mechanistic.screen import run
    from llm_cooperation.mechanistic.analyze import summarize
    target = '/runs/' + run_id
    try:
        run(model, revision, target, top_k)
        summarize(target)
    finally:
        volume.commit()
    return target

@app.local_entrypoint()
def main(model: str, revision: str, authorize_paid_run: bool = False, top_k: int = 10):
    if not authorize_paid_run:
        raise ValueError('Paid execution requires --authorize-paid-run')
    import re
    allowed = {'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'}
    if model not in allowed or not re.fullmatch(r'[0-9a-f]{40}', revision) or not 1 <= top_k <= 100:
        raise ValueError('Unsupported model, revision, or top_k; see documentation')
    run_id = 'mechanistic-' + uuid.uuid4().hex
    print(f'Run ID: {run_id}; results volume: llm-coop-mechanistic')
    print(screen.remote(model, revision, run_id, top_k))
