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
    valid = np.flatnonzero((denom > 1e-12).ravel())
    if k is not None and len(valid) < k:
        raise ValueError('Too few varying neurons for the requested candidate count')
    order = valid[np.argsort(-np.abs(corr).ravel()[valid], kind='stable')]
    if k is not None:
        order = order[:k]
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


def run_amplification(model_id, revision, output, group_size=100, random_controls=2):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if model_id not in ('Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-1B', 'meta-llama/Llama-3.2-3B'):
        raise ValueError('Model is outside the supported small base-model list')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Supply an immutable 40-character model revision SHA')
    if not 1 <= group_size <= 100000:
        raise ValueError('group_size must be between 1 and 100000')
    if not 1 <= random_controls <= 5:
        raise ValueError('random_controls must be between 1 and 5')
    factors = (0.0, 1.5, 2.0)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    selected = select_items_sweep()
    manifest = {'status': 'running', 'model': model_id, 'revision': revision,
                'started_utc': datetime.now(timezone.utc).isoformat(), 'bank_sha256': digest(BANK),
                'calibration_sha256': digest(CALIBRATION), 'split': {s.id: part for s, part in selected},
                'ranking': 'all varying neurons, absolute correlation', 'group_size': group_size, 'factors': factors, 'random_controls': random_controls, 'control_seed_rule': '280000 + group_index * 100 + replicate', 'amplification_sha256': digest(__file__), 'torch': torch.__version__, 'transformers': transformers.__version__,
                'python': sys.version, 'feature': 'down_proj input, final prompt token', 'intervention': 'multiply down_proj input at final prompt token',
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
        def evaluate(p, stage, condition, features=False, neurons=None, scenario=None, factor=1.0):
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
                        x[:, -1, grouped[idx]] *= factor
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
        # Average permutations, partners and triad variants within independent groups.
        by_template = {}
        for s, part in selected:
            if part != 'discovery':
                continue
            for p in generate_permutations(s):
                row, feature = evaluate(p, part, 'baseline', features=True, scenario=s)
                by_template.setdefault(s.triad_id or s.template_id, []).append((feature, row['margin']))
        features = [np.mean([x[0] for x in rows], axis=0) for rows in by_template.values()]
        margins = [np.mean([x[1] for x in rows]) for rows in by_template.values()]
        ranked = rank_candidates(features, margins, None)
        positive = [c for c in ranked if c['correlation'] > 0][:group_size]
        negative = [c for c in ranked if c['correlation'] < 0][:group_size]
        if len(ranked) < group_size or len(positive) < group_size or len(negative) < group_size:
            raise ValueError('Insufficient varying neurons with each correlation sign for group_size')
        # Preserve the original top-1000 exclusion at small sizes and include every
        # selected sign-specific candidate when the requested groups are larger.
        prefix = max(1000, ranked.index(positive[-1]) + 1, ranked.index(negative[-1]) + 1, group_size)
        candidates = ranked[:prefix]
        # Group-mean absolute activations provide a descriptive magnitude check.
        magnitude = np.mean(np.abs(np.asarray(features, dtype=np.float64)), axis=0)
        for c in candidates:
            c['mean_abs_group_activation'] = float(magnitude[c['layer'], c['neuron']])
        groups = {'mixed': ranked[:group_size], 'positive': positive, 'negative': negative}
        # Random controls exclude the original top 1000 and all selected groups.
        excluded = {}
        for c in candidates[:1000] + sum(groups.values(), []):
            excluded.setdefault(c['layer'], set()).add(c['neuron'])
        controls = {}
        conditions = [('baseline', None, 1.0)]
        condition_manifest = {}
        for group_index, (group_name, current) in enumerate(groups.items()):
            counts = {}
            for c in current:
                counts[c['layer']] = counts.get(c['layer'], 0) + 1
            samples = []
            for replicate in range(random_controls):
                rng = random.Random(280000 + group_index * 100 + replicate)
                sample = []
                for layer, count in sorted(counts.items()):
                    pool = [i for i in range(width) if i not in excluded.get(layer, set())]
                    if len(pool) < count:
                        raise ValueError(f'Insufficient layer-matched noncandidate controls in layer {layer}: need {count}, available {len(pool)}')
                    sample.extend({'layer': layer, 'neuron': i} for i in rng.sample(pool, count))
                controls[f'{group_name}_{replicate}'] = sample
                samples.append(sample)
            for factor_index, factor in enumerate(factors):
                key = f'{group_name}_factor_{factor_index}'
                target_name = f'{key}_candidate'
                conditions.append((target_name, current, factor))
                names = []
                for replicate, sample in enumerate(samples):
                    name = f'{key}_random_{replicate}'
                    names.append(name)
                    conditions.append((name, sample, factor))
                condition_manifest[key] = {'group': group_name, 'factor': factor,
                    'candidate': target_name, 'random': names}
        manifest['conditions'] = condition_manifest
        write_manifest()
        (out / 'candidates.json').write_text(json.dumps({'ranking': candidates, 'groups': groups, 'random_controls': controls,
            'discovery_groups': list(by_template), 'selection': 'all varying neurons ranked by absolute correlation; sign groups selected from full ranking; stored ranking is the selected prefix'}, indent=2), encoding='utf-8')
        del features, by_template, magnitude
        calibration = CalibrationBank.model_validate_json(CALIBRATION.read_text(encoding='utf-8'))
        for condition, neurons, factor in conditions:
            for s, part in selected:
                if part == 'evaluation':
                    for p in generate_permutations(s):
                        evaluate(p, part, condition, neurons=neurons, scenario=s, factor=factor)
            for item in calibration.items:
                for p in generate_calibration_permutations(item):
                    evaluate(p, 'calibration', condition, neurons=neurons, factor=factor)
        manifest['status'] = 'completed'
    except BaseException as exc:
        manifest.update({'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        raise
    finally:
        manifest['ended_utc'] = datetime.now(timezone.utc).isoformat()
        write_manifest()
