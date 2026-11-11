"""Modal runner for the exploratory choice-set intervention."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import modal

app = modal.App('llm-cooperation-choice-set-mistral-retry')
cache = modal.Volume.from_name('llm-coop-hf-cache', create_if_missing=True)
results = modal.Volume.from_name('llm-coop-results', create_if_missing=True)
image = (modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch>=2.2', 'transformers>=4.40,<5', 'accelerate>=0.29', 'safetensors', 'sentencepiece', 'protobuf')
    .add_local_python_source('llm_cooperation')
    .add_local_file('data/scenarios_phase1_prospective.json', '/root/data/phase1.json')
    .add_local_file('data/choice_set_neutral_replacements.json', '/root/data/neutral_replacements.json'))

def execute(model_name, run_id, mode):
    import torch, transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from llm_cooperation.choice_set_intervention import load_bank, load_replacements, presentations, parse_response, summarize, answer_token_ids
    os.environ['HF_HOME'] = '/root/hf_cache'
    scenarios, bank_hash = load_bank('/root/data/phase1.json')
    replacements, replacement_hash = load_replacements('/root/data/neutral_replacements.json', scenarios)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map='auto', trust_remote_code=True)
    model.eval()
    actual_revision = getattr(model.config, '_commit_hash', None)
    folder = Path('/root/results/choice_set') / run_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'rows.jsonl'
    rows = []
    with path.open('w', encoding='utf-8') as out:
        for n, scenario in enumerate(scenarios, 1):
            for p in presentations(scenario, replacements, mode):
                inputs = tokenizer(p['prompt'], return_tensors='pt').to(model.device)
                with torch.inference_mode():
                    next_logits = model(**inputs).logits[0, -1, :].float()
                    output = model.generate(**inputs, max_new_tokens=5, do_sample=False, pad_token_id=tokenizer.pad_token_id)
                raw = tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
                token_ids, spacer = answer_token_ids(tokenizer, p['prompt'], p['letter_to_strategy'])
                forced = None
                if token_ids:
                    logits = next_logits
                    values = torch.stack([logits[token_ids[k]] for k in token_ids])
                    probs = torch.softmax(values, dim=0).tolist()
                    prob_map = dict(zip(token_ids, probs))
                    selected = max(prob_map, key=prob_map.get)
                    forced = {'letter': selected, 'strategy': p['letter_to_strategy'][selected],
                              'conditional_probabilities': prob_map, 'raw_logits': dict(zip(token_ids, values.tolist())),
                              'full_vocab_logprobs': {k: float(torch.log_softmax(logits, dim=0)[v].item()) for k, v in token_ids.items()},
                              'token_ids': token_ids, 'answer_prefix': spacer}
                letter, strategy = parse_response(raw, p['letter_to_strategy'])
                row = {**p, 'generated_raw_text': raw, 'generated_letter': letter, 'generated_strategy': strategy, 'forced_choice': forced}
                out.write(json.dumps(row, ensure_ascii=False) + '\n')
                rows.append(row)
            out.flush()
            results.commit()
            print(f'{model_name}: {n}/{len(scenarios)} scenarios', flush=True)
    metadata = {'run_id': run_id, 'model': model_name, 'resolved_model_revision': actual_revision,
        'bank_sha256': bank_hash, 'choice_set_mode': mode,
        'replacement_bank_sha256': replacement_hash if mode != 'standard' else None, 'bank_status': 'draft_pending_review', 'torch_version': torch.__version__,
        'transformers_version': transformers.__version__, 'precision': str(model.dtype),
        'generated_max_new_tokens': 5, 'summary': summarize(rows)}
    (folder / 'summary.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    results.commit()
    cache.commit()
    return {'metadata': metadata, 'rows': path.read_text(encoding='utf-8')}

@app.function(image=image, gpu='A10G', timeout=14400, volumes={'/root/hf_cache': cache, '/root/results': results})
def run_small(model_name: str, run_id: str, mode: str):
    return execute(model_name, run_id, mode)

@app.function(image=image, gpu='L40S', timeout=14400, volumes={'/root/hf_cache': cache, '/root/results': results})
def run_medium(model_name: str, run_id: str, mode: str):
    return execute(model_name, run_id, mode)

@app.local_entrypoint()
def main(model: str, gpu: str = 'small', mode: str = 'standard'):
    if gpu not in ('small', 'medium'): raise ValueError('gpu must be small or medium')
    if mode not in ('standard', 'all', 'replacement-only'): raise ValueError('Invalid mode')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    print(f'Run ID: {run_id}; model: {model}; GPU: {gpu}', flush=True)
    fn = run_small if gpu == 'small' else run_medium
    if os.environ.get('MODAL_USE_HF_SECRET', '').lower() in ('1', 'true', 'yes'):
        fn = fn.with_options(secrets=[modal.Secret.from_name('huggingface-secret')])
    result = fn.remote(model, run_id, mode)
    target = Path('results/choice_set') / run_id
    target.mkdir(parents=True, exist_ok=False)
    (target / 'rows.jsonl').write_text(result['rows'], encoding='utf-8')
    (target / 'summary.json').write_text(json.dumps(result['metadata'], indent=2), encoding='utf-8')
    print(f'Local results: {target}')
    print(json.dumps(result['metadata']['summary'], indent=2))
