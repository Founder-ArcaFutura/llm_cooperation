"""Thin Modal adapter for frozen factorial presentations. User launches inference."""
import json
import os
import re
from pathlib import Path

import modal
from llm_cooperation.factorial_inference import (
    DEFAULT_INPUT, MODEL_REVISIONS, ROOT, canonical, load_inputs, prepare,
    score_row, sha, validate_resume, write_json,
)

app = modal.App('llm-cooperation-factorial-v1')
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
results = modal.Volume.from_name('llm-coop-results', create_if_missing=True)
# Same pinned loader runtime as the existing OLMo behavioral runner; no new serving stack.
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('torch==2.5.1', 'transformers==4.53.2', 'accelerate==1.1.1',
                      'numpy==1.26.4', 'pydantic==2.9.2', 'sentencepiece==0.2.0', 'protobuf==5.29.5')
         .add_local_python_source('llm_cooperation'))


def read_existing(path):
    if not path.exists(): return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b'\n'):
        # Preserve an interrupted append before discarding only its uncommitted tail.
        boundary = raw.rfind(b'\n') + 1
        backup = path.with_name('interrupted_tail_' + sha(raw[boundary:])[:16] + '.bin')
        backup.write_bytes(raw[boundary:])
        path.write_bytes(raw[:boundary])
        raw = raw[:boundary]
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


@app.function(image=image, gpu='L40S', timeout=86400, retries=0,
              volumes={'/root/hf_cache': cache, '/root/results': results})
def evaluate(presentation_bytes: bytes, condition_bytes: bytes, manifest: dict, resume: bool):
    from datetime import datetime, timezone
    import torch
    import transformers
    from llm_cooperation.harness.runner import ModelRunner
    from llm_cooperation.choice_set_followup import answer_token_ids

    rows, fingerprint = prepare(presentation_bytes, condition_bytes, manifest['scope'] == 'smoke')
    if any(manifest.get(k) != v for k, v in fingerprint.items()): raise ValueError('Transport/input hash mismatch')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', manifest['run_id']): raise ValueError('Invalid run ID')
    folder = Path('/root/results/factorial') / manifest['run_id']
    results.reload()
    if folder.exists():
        if not resume: raise FileExistsError(f'Refusing overwrite: {folder}; use --resume for the identical run')
        if json.loads((folder / 'manifest.json').read_text(encoding='utf-8')) != manifest:
            raise ValueError('Resume requires identical model, scope, source, renderer and scoring code')
    else:
        folder.mkdir(parents=True)
        write_json(folder / 'manifest.json', manifest)
        (folder / 'presentations_input.jsonl').write_bytes(presentation_bytes)
        (folder / 'candidate_conditions.json').write_bytes(condition_bytes)
    path = folder / 'rows.jsonl'
    existing = read_existing(path)
    done = validate_resume(existing, rows)
    fingerprint_hash = sha(canonical(manifest))
    old_summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8')) if (folder / 'summary.json').exists() else {}
    if len(done) == len(rows) and old_summary.get('status') == 'complete':
        return str(folder.relative_to('/root/results'))
    summary = {**old_summary, 'run_id': manifest['run_id'], 'status': 'running', 'model': manifest['model'],
               'fingerprint_sha256': fingerprint_hash, 'completed_presentations': len(done),
               'expected_presentations': len(rows), 'gpu': 'L40S', 'precision': 'bfloat16',
               'torch_version': torch.__version__, 'transformers_version': transformers.__version__,
               'started_utc': old_summary.get('started_utc', datetime.now(timezone.utc).isoformat())}
    write_json(folder / 'summary.json', summary); results.commit()
    try:
        os.environ['HF_HOME'] = '/root/hf_cache'
        # A trajectory-only override in the legacy loader must not leak into these pinned base checkpoints.
        os.environ.pop('OLMO_7B_TOKENIZER_REVISION', None)
        torch.manual_seed(42)
        if len(done) < len(rows):
            runner = ModelRunner(manifest['model'], revision=manifest['revision'],
                                 precision='bfloat16', device='auto', mock=False, seed=42)
            resolved = getattr(runner.model.config, '_commit_hash', None)
            if resolved and resolved != manifest['revision']: raise ValueError('Resolved model revision differs from requested pin')
            summary.update({'resolved_model_revision': resolved, 'requested_tokenizer_revision': manifest['revision'],
                            'resolved_tokenizer_revision': runner.tokenizer.init_kwargs.get('_commit_hash'),
                            'model_class': type(runner.model).__name__, 'effective_precision': runner.effective_precision})
            # Fail boundary/context incompatibility before collecting a selectively retained partial assay.
            for row in rows:
                token_ids, _ = answer_token_ids(runner.tokenizer, row['prompt'], row['options'])
                if not token_ids: raise ValueError(f'Unstable answer token boundary: {row["presentation_id"]}')
                length = len(runner.tokenizer.encode(row['prompt'], add_special_tokens=True))
                max_context = getattr(runner.model.config, 'max_position_embeddings', None)
                if max_context and length + 5 > max_context: raise ValueError('Prompt exceeds model context; truncation is prohibited')
            for row in rows:
                if row['presentation_id'] in done: continue
                scored = score_row(runner, row)
                # Close every append before a volume commit; interrupted tails are preserved on resume.
                with path.open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps(scored, ensure_ascii=False, allow_nan=False) + '\n')
                done.add(row['presentation_id'])
                if len(done) % 25 == 0:
                    summary['completed_presentations'] = len(done)
                    write_json(folder / 'summary.json', summary); results.commit()
                    print(f'{manifest["model"]}: {len(done)}/{len(rows)}', flush=True)
        summary.update({'status': 'complete', 'completed_presentations': len(done),
                        'finished_utc': datetime.now(timezone.utc).isoformat()})
        summary.pop('error', None)
        write_json(folder / 'summary.json', summary); results.commit(); cache.commit()
    except Exception as error:
        summary.update({'status': 'failed', 'completed_presentations': len(done), 'error': f'{type(error).__name__}: {error}'})
        write_json(folder / 'summary.json', summary); results.commit(); cache.commit()
        raise
    return str(folder.relative_to('/root/results'))


@app.local_entrypoint()
def main(model: str, run_id: str, input: str = str(DEFAULT_INPUT), revision: str = '',
         smoke: bool = False, resume: bool = False):
    if model not in MODEL_REVISIONS: raise ValueError(f'Model must be one of {list(MODEL_REVISIONS)}')
    revision = revision or MODEL_REVISIONS[model]
    if not re.fullmatch(r'[0-9a-f]{40}', revision): raise ValueError('Use an immutable 40-character model revision')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id): raise ValueError('Run ID may contain only letters, numbers, hyphens and underscores')
    rows, manifest, presentation_bytes, condition_bytes = load_inputs(Path(input), smoke=smoke)
    code_paths = ['modal_factorial_cooperation.py', 'llm_cooperation/factorial_inference.py',
                  'llm_cooperation/harness/runner.py', 'llm_cooperation/harness/tokenizer_probe.py',
                  'llm_cooperation/choice_set_followup.py']
    manifest.update({'run_id': run_id, 'model': model, 'revision': revision,
                     'code_sha256': {p: sha((ROOT / p).read_bytes()) for p in code_paths}})
    print(f'{len(rows)} {manifest["scope"]} presentations on L40S; model={model}; revision={revision}', flush=True)
    print(f'Results: llm-coop-results/factorial/{run_id}', flush=True)
    fn = evaluate
    if os.environ.get('MODAL_USE_HF_SECRET', '').lower() in ('1', 'true', 'yes'):
        fn = fn.with_options(secrets=[modal.Secret.from_name('huggingface-secret')])
    remote = fn.remote(presentation_bytes, condition_bytes, manifest, resume)
    print(f'Completed. Retrieve: python -m modal volume get llm-coop-results {remote} results/factorial/{run_id}', flush=True)
