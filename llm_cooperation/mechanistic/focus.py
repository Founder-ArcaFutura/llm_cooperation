"""Exploratory, template-separated MLP-neuron screen for Qwen2 and Llama.

No model calls occur on import. See docs/mechanistic_exploration.md.
"""
import hashlib
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from llm_cooperation.items.schema import ScenarioBank, CalibrationBank, StrategyType
from llm_cooperation.items.permutations import generate_permutations, generate_calibration_permutations
from llm_cooperation.harness.tokenizer_probe import resolve_candidate_token_ids, validate_candidate_tokens_at_boundary

BANK = Path('data/scenarios_phase0b_utility_matched.json')
CALIBRATION = Path('data/calibration_bank.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select_items_sweep():
    bank = ScenarioBank.model_validate_json(BANK.read_text(encoding='utf-8'))
    items = [s for s in bank.scenarios if s.split == 'exploratory']
    # Keep sensitivity triads and human/AI variants together, even across templates.
    triads = sorted({s.triad_id for s in items if s.triad_id})
    ordinary = sorted({s.template_id for s in items if not s.triad_id},
                      key=lambda x: hashlib.sha256(('mechanistic-sweep-v1:' + x).encode()).hexdigest())
    if len(triads) < 2 or len(ordinary) < 8:
        raise ValueError('Expected two exploratory triads and at least eight ordinary groups')
    # One whole triad plus seven other templates. This is a new exploratory split,
    # and is not independent of the preceding screen or earlier behavioral work.
    heldout = {triads[0], *ordinary[:7]}
    return [(s, 'evaluation' if (s.triad_id or s.template_id) in heldout else 'discovery') for s in items]



def rank_candidates(features, margins, k):
    """Rank by absolute Pearson association across equally weighted templates."""
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(margins, dtype=np.float64)
    if x.ndim != 3 or len(y) != len(x) or len(y) < 3:
        raise ValueError('Need at least three independent template groups')
    x -= x.mean(axis=0)
    y -= y.mean()
    if np.linalg.norm(y) < 1e-12:
        raise ValueError('Discovery margins are constant; neuron ranking is undefined')
    denom = np.sqrt((x*x).sum(axis=0) * (y*y).sum())
    corr = np.divide((x*y[:, None, None]).sum(axis=0), denom,
                     out=np.zeros_like(denom), where=denom > 1e-12)
    if np.count_nonzero(denom > 1e-12) < k:
        raise ValueError('Too few varying neurons for the requested candidate count')
    order = np.argsort(-np.abs(corr).ravel(), kind='stable')[:k]
    return [{'layer': int(i // x.shape[2]), 'neuron': int(i % x.shape[2]),
             'correlation': float(corr.ravel()[i])} for i in order]


def control_candidates(candidates, width, seed=17):
    rng = random.Random(seed)
    by_layer = {}
    for c in candidates:
        by_layer.setdefault(c['layer'], set()).add(c['neuron'])
    result = []
    for layer, selected in sorted(by_layer.items()):
        pool = [i for i in range(width) if i not in selected]
        if len(pool) < len(selected):
            raise ValueError('Not enough unselected neurons for random control')
        result.extend({'layer': layer, 'neuron': n} for n in rng.sample(pool, len(selected)))
    return result


def focus_groups(candidates):
    """Partition source ranks 101-500 by rank, correlation sign and layer."""
    band = candidates[100:500]
    if len(band) != 400 or any(not np.isfinite(c['correlation']) for c in band):
        raise ValueError('Source needs 400 finite-correlation candidates at ranks 101-500')
    groups = {'full_101_500': band}
    for start in (101, 201, 301, 401):
        groups[f'rank_{start}_{start+99}'] = candidates[start-1:start+99]
    groups['positive'] = [c for c in band if c['correlation'] > 0]
    groups['negative'] = [c for c in band if c['correlation'] < 0]
    groups['layers_20_22'] = [c for c in band if 20 <= c['layer'] <= 22]
    groups['layers_23_25'] = [c for c in band if 23 <= c['layer'] <= 25]
    groups['other_layers'] = [c for c in band if not 20 <= c['layer'] <= 25]
    if any(not v for v in groups.values()):
        raise ValueError('At least one predefined subgroup is empty')
    return groups


def run_focus(model_id, revision, output, source_manifest, source_candidates, random_controls=3):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if model_id not in ('Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'):
        raise ValueError('Model is outside the supported small base-model list')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Supply an immutable 40-character model revision SHA')
    if not 1 <= random_controls <= 5:
        raise ValueError('random_controls must be between 1 and 5')
    group_names = list(focus_groups(source_candidates.get('candidates', [])))
    if source_manifest.get('status') != 'completed' or source_manifest.get('model') != model_id or source_manifest.get('revision') != revision:
        raise ValueError('Source must be a completed sweep with the exact model and revision')
    if source_manifest.get('bank_sha256') != digest(BANK) or source_manifest.get('calibration_sha256') != digest(CALIBRATION):
        raise ValueError('Source bank fingerprints do not match current files')
    candidates = source_candidates.get('candidates', [])
    if len(candidates) < 2000:
        raise ValueError('Source run needs at least 2000 ranked candidates')
    candidates = candidates[:2000]
    if len({(c['layer'], c['neuron']) for c in candidates}) != 2000:
        raise ValueError('Duplicate source candidate coordinates')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    selected = select_items_sweep()
    if {s.id: part for s, part in selected} != source_manifest.get('split'):
        raise ValueError('Current split differs from source sweep')
    manifest = {'status': 'running', 'model': model_id, 'revision': revision,
                'started_utc': datetime.now(timezone.utc).isoformat(), 'bank_sha256': digest(BANK),
                'calibration_sha256': digest(CALIBRATION), 'split': {s.id: part for s, part in selected},
                'groups': group_names, 'random_controls': random_controls, 'source_manifest_canonical_sha256': hashlib.sha256(json.dumps(source_manifest, sort_keys=True).encode('utf8')).hexdigest(), 'source_candidates_canonical_sha256': hashlib.sha256(json.dumps(source_candidates, sort_keys=True).encode('utf8')).hexdigest(), 'focus_screen_sha256': digest(__file__), 'torch': torch.__version__, 'transformers': transformers.__version__,
                'python': sys.version, 'feature': 'down_proj input, final prompt token', 'ablation': 'zero at final prompt token',
                'score': 'next-token COOPERATE minus INDEPENDENT letter logit', 'exploratory': True}
    def write_manifest():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_manifest()
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        token_ids = resolve_candidate_token_ids(tokenizer, sample_prompt='Answer:')
        model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, torch_dtype=torch.bfloat16, device_map='auto')
        model.eval()
        if getattr(model.config, 'model_type', '') not in ('qwen2', 'llama'):
            raise ValueError('Only Qwen2 and Llama MLP layouts are supported')
        layers = model.model.layers
        width = model.config.intermediate_size
        manifest.update({'model_type': model.config.model_type, 'layers': len(layers), 'intermediate_size': width,
                         'candidate_token_ids': token_ids, 'device': str(model.device), 'dtype': str(model.dtype)})
        write_manifest()
        records = out / 'observations.jsonl'
        def evaluate(p, stage, condition, features=False, neurons=None, scenario=None):
            validate_candidate_tokens_at_boundary(tokenizer, p.prompt_text, token_ids)
            cache = {}
            handles = []
            grouped = {}
            for c in neurons or []:
                grouped.setdefault(c['layer'], []).append(c['neuron'])
            for layer_idx, layer in enumerate(layers):
                if not features and layer_idx not in grouped:
                    continue
                def hook(module, args, idx=layer_idx):
                    x = args[0]
                    if features:
                        cache[idx] = x[0, -1, :].detach().float().cpu().numpy()
                    if idx in grouped:
                        x = x.clone()
                        x[:, -1, grouped[idx]] = 0
                        return (x,) + args[1:]
                handles.append(layer.mlp.down_proj.register_forward_pre_hook(hook))
            try:
                inputs = tokenizer(p.prompt_text, return_tensors='pt').to(model.device)
                with torch.inference_mode():
                    logits = model(**inputs).logits[0, -1].float()
                vals = {letter: float(logits[token_ids[letter]]) for letter in 'ABCD'}
                greedy_id = int(logits.argmax())
                greedy_text = tokenizer.decode([greedy_id])
                row = {'stage': stage, 'condition': condition, 'presentation_id': p.presentation_id,
                       'letter_logits': vals, 'greedy_token_id': greedy_id, 'greedy_token_text': greedy_text,
                       'greedy_single_token_letter': greedy_text.strip() in list('ABCD')}
                if scenario is not None:
                    c = p.strategy_to_letter[StrategyType.COOPERATE]
                    i = p.strategy_to_letter[StrategyType.INDEPENDENT]
                    row.update({'scenario_id': scenario.id, 'template_id': scenario.template_id, 'triad_id': scenario.triad_id,
                                'partner_type': scenario.partner_type.value, 'utility_condition': scenario.utility_condition.value,
                                'cooperate_letter': c, 'independent_letter': i,
                                'margin': vals[c] - vals[i], 'argmax_letter': max(vals, key=vals.get)})
                else:
                    row.update({'item_id': p.item_id, 'correct_letter': p.correct_letter,
                                'correct': max(vals, key=vals.get) == p.correct_letter})
                with records.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(row, allow_nan=False) + '\n')
                return row, np.stack([cache[i] for i in range(len(layers))]) if features else None
            finally:
                for h in handles:
                    h.remove()
        if any(not (0 <= c['layer'] < len(layers) and 0 <= c['neuron'] < width) for c in candidates):
            raise ValueError('Source candidate coordinate is outside the model dimensions')
        excluded = {}
        for c in candidates:
            excluded.setdefault(c['layer'], set()).add(c['neuron'])
        conditions = [('baseline', None)]
        controls = {}
        groups = focus_groups(candidates)
        for group_index, (name, current) in enumerate(groups.items()):
            conditions.append((f'focus_{name}', current))
            counts = {}
            for c in current:
                counts[c['layer']] = counts.get(c['layer'], 0) + 1
            for replicate in range(random_controls):
                rng = random.Random(480000 + group_index * 100 + replicate)
                sample = []
                for layer, count in sorted(counts.items()):
                    pool = [i for i in range(width) if i not in excluded.get(layer, set())]
                    if len(pool) < count:
                        raise ValueError(f'Insufficient controls in layer {layer}: need {count}, available {len(pool)}')
                    sample.extend({'layer': layer, 'neuron': i} for i in rng.sample(pool, count))
                control_name = f'random_{name}_{replicate}'
                controls[control_name] = sample
                conditions.append((control_name, sample))
        (out / 'source_manifest.json').write_text(json.dumps(source_manifest, indent=2), encoding='utf8')
        (out / 'source_candidates.json').write_text(json.dumps(source_candidates, indent=2), encoding='utf8')
        (out / 'candidates.json').write_text(json.dumps({'candidates': candidates, 'random_controls': controls,
            'groups': groups, 'selection': 'source ranks 101-500, partitioned by rank, correlation sign and layer'}, indent=2), encoding='utf8')
        calibration = CalibrationBank.model_validate_json(CALIBRATION.read_text(encoding='utf-8'))
        for condition, neurons in conditions:
            for s, part in selected:
                if part == 'evaluation':
                    for p in generate_permutations(s):
                        evaluate(p, part, condition, neurons=neurons, scenario=s)
            for item in calibration.items:
                for p in generate_calibration_permutations(item):
                    evaluate(p, 'calibration', condition, neurons=neurons)
        manifest['status'] = 'completed'
    except BaseException as exc:
        manifest.update({'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        raise
    finally:
        manifest['ended_utc'] = datetime.now(timezone.utc).isoformat()
        write_manifest()
