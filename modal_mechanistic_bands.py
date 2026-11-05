"""Ablate disjoint rank bands copied from a completed, user-provided sweep."""
import json
import os
from pathlib import Path
import uuid
import modal

volume = modal.Volume.from_name('llm-coop-mechanistic', create_if_missing=True)
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('torch==2.5.1', 'transformers==4.46.3', 'accelerate==1.1.1', 'pydantic==2.9.2', 'numpy==1.26.4')
    .add_local_python_source('llm_cooperation')
    .add_local_file('data/scenarios_phase0b_utility_matched.json', '/root/data/scenarios_phase0b_utility_matched.json')
    .add_local_file('data/calibration_bank.json', '/root/data/calibration_bank.json'))
app = modal.App('llm-cooperation-rank-bands-v1', image=image)
secrets = [modal.Secret.from_name('huggingface-secret')] if os.environ.get('MODAL_USE_HF_SECRET') == '1' else []

@app.function(gpu='A10G', timeout=14400, volumes={'/runs': volume, '/hf-cache': cache}, secrets=secrets)
def bands(model: str, revision: str, run_id: str, source_manifest: dict, source_candidates: dict, random_controls: int):
    os.chdir('/root')
    os.environ['HF_HOME'] = '/hf-cache'
    from llm_cooperation.mechanistic.bands import run_bands
    from llm_cooperation.mechanistic.analyze_bands import summarize
    target = '/runs/' + run_id
    try:
        run_bands(model, revision, target, source_manifest, source_candidates, random_controls)
        summarize(target)
    finally:
        volume.commit()
    return target

@app.local_entrypoint()
def main(source: str, authorize_paid_run: bool = False, random_controls: int = 3):
    if not authorize_paid_run:
        raise ValueError('Paid execution requires --authorize-paid-run')
    import re
    from llm_cooperation.mechanistic.bands import BANK, CALIBRATION, digest, select_items_sweep
    source_path = Path(source)
    manifest = json.loads((source_path / 'manifest.json').read_text(encoding='utf-8-sig'))
    candidates = json.loads((source_path / 'candidates.json').read_text(encoding='utf-8-sig'))
    model, revision = manifest.get('model'), manifest.get('revision')
    allowed = {'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'}
    if manifest.get('status') != 'completed' or model not in allowed or not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Source model, revision, or completion status invalid')
    if len(candidates.get('candidates', [])) < 2000 or not 1 <= random_controls <= 5:
        raise ValueError('Source needs at least 2000 candidates; controls must be 1..5')
    if manifest.get('bank_sha256') != digest(BANK) or manifest.get('calibration_sha256') != digest(CALIBRATION):
        raise ValueError('Local source bank fingerprints do not match')
    if {s.id: part for s, part in select_items_sweep()} != manifest.get('split'):
        raise ValueError('Local split differs from source')
    run_id = 'mechanistic-bands-' + uuid.uuid4().hex
    print(f'Run ID: {run_id}; results volume: llm-coop-mechanistic')
    print(bands.remote(model, revision, run_id, manifest, candidates, random_controls))
