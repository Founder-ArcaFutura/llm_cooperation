"""Full quantitative offline analysis engine for the cooperative rewording assay.

Performs:
1. Recomputes primary and secondary descriptive results from raw JSONL:
   - Per-model and per-bank original & paraphrased COOPERATE-minus-INDEPENDENT forced-choice margins.
   - Paired changes (paraphrase - original).
   - Equal-private-utility non-symmetric vs symmetric-control splits.
   - Full context strata (neutral_or_costless, modest_cost, conflict_with_objective, ineffective_or_inappropriate).
   - Partner strata (human vs ai).
   - Tie, non-token-score, and exclusion counts.
   - Conditional log-probability contrasts: ln P(COOPERATE) - ln P(INDEPENDENT).
2. Resampling & Clustering:
   - Template/triad-clustered bootstrap with presentation-weighted aggregations.
   - 95% CIs, exact seeds, estimands, cluster counts, and sensitivity to exclusion choices.
   - Treats 4 position permutations, paired partner cases, and 2 wordings as repeated measures.
3. Family-aware aggregation:
   - Evaluated as exploratory, keeping base checkpoints, instruction tunes, and model families distinct.
4. Generated-answer audit:
   - Strict regex parser vs recovered secondary initial-answer-letter rule vs forced-choice scoring.
   - Categorization into valid initial, valid with text, ambiguous multi-answer, contradictory, unparseable.
   - Agreement rates with forced-choice scoring across checkpoints, banks, and positions.
5. Instrument failure diagnostics (Pythia 12B base and exploratory fine-tune):
   - Positional frequency distributions, conditional probability spreads, calibration, and format failure.
"""
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from llm_cooperation.response_parser import parse_strict, parse_generated_secondary

ROOT = Path('results/cooperate_rewording')
FAMILY_MAPPING = {
    'Qwen/Qwen2.5-3B': 'Qwen',
    'Qwen/Qwen2.5-1.5B': 'Qwen',
    'Qwen/Qwen2.5-7B': 'Qwen',
    'allenai/OLMo-2-0425-1B': 'OLMo',
    'allenai/OLMo-2-1124-7B': 'OLMo',
    'meta-llama/Llama-3.2-3B': 'Llama',
    'google/gemma-2-2b': 'Gemma',
    'google/gemma-2-9b': 'Gemma',
    'ibm-granite/granite-3.3-2b-base': 'Granite',
    'deepseek-ai/deepseek-llm-7b-base': 'DeepSeek',
    'mistralai/Mistral-7B-v0.3': 'Mistral',
    'EleutherAI/pythia-12b-deduped': 'Pythia',
    # Instruction-tuned / exploratory variants kept in distinct families
    'Qwen/Qwen2.5-3B-Instruct': 'Qwen_Instruct',
    'founder-arcafutura/pythia-12b-exploratory-20261022': 'Pythia_Exploratory'
}

BASE_CHECKPOINTS = [
    'Qwen/Qwen2.5-3B', 'Qwen/Qwen2.5-1.5B', 'allenai/OLMo-2-0425-1B', 'meta-llama/Llama-3.2-3B',
    'google/gemma-2-2b', 'ibm-granite/granite-3.3-2b-base', 'Qwen/Qwen2.5-7B', 'allenai/OLMo-2-1124-7B',
    'deepseek-ai/deepseek-llm-7b-base', 'mistralai/Mistral-7B-v0.3', 'google/gemma-2-9b',
    'EleutherAI/pythia-12b-deduped'
]


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    x = (len(values) - 1) * q
    lo = int(x)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def bootstrap_ci(samples: List[float]) -> List[float]:
    if not samples:
        return [0.0, 0.0]
    sorted_s = sorted(samples)
    return [percentile(sorted_s, 0.025), percentile(sorted_s, 0.975)]


def compute_logprob_contrast(row: dict) -> Optional[float]:
    """Compute ln P(COOPERATE) - ln P(INDEPENDENT) from conditional probabilities."""
    fc = row.get('forced_choice')
    if not fc or not fc.get('conditional_probabilities'):
        return None
    l2s = row.get('letter_to_strategy', {})
    s2l = {v: k for k, v in l2s.items()}
    if 'COOPERATE' not in s2l or 'INDEPENDENT' not in s2l:
        return None
    c_prob = fc['conditional_probabilities'].get(s2l['COOPERATE'], 0.0)
    i_prob = fc['conditional_probabilities'].get(s2l['INDEPENDENT'], 0.0)
    if c_prob <= 0.0 or i_prob <= 0.0:
        return None
    return math.log(c_prob) - math.log(i_prob)


def analyze_stratum_pairs(
    pairs: List[dict],
    mode: str = 'forced_no_ties',
    bootstrap: int = 2000,
    seed: int = 42
) -> Dict[str, Any]:
    """Resample template/triad clusters for paired presentations."""
    clean_pairs = []
    for p in pairs:
        orig = p['original']
        para = p['paraphrase']

        if mode == 'forced_no_ties':
            # Exclude pairs where either side is missing forced_choice or is tied
            fc_o = orig.get('forced_choice')
            fc_p = para.get('forced_choice')
            if not fc_o or fc_o.get('tied_max_count', 0) != 1:
                continue
            if not fc_p or fc_p.get('tied_max_count', 0) != 1:
                continue
            clean_pairs.append(p)
        elif mode == 'forced_include_ties':
            # Do not exclude tied pairs (argmax breaks ties deterministically or keeps first)
            fc_o = orig.get('forced_choice')
            fc_p = para.get('forced_choice')
            if not fc_o or not fc_p:
                continue
            clean_pairs.append(p)
        elif mode == 'strict_generated':
            # Require both sides to have valid strict generated strategies
            if orig.get('generated_strategy') is None or para.get('generated_strategy') is None:
                continue
            clean_pairs.append(p)
        elif mode == 'recovered_generated':
            # Require both sides to have valid secondary recovered strategies
            if orig.get('recovered_strategy') is None or para.get('recovered_strategy') is None:
                continue
            clean_pairs.append(p)

    clusters = defaultdict(list)
    for p in clean_pairs:
        item = p['original']
        cluster = ('triad', item['triad_id']) if item.get('triad_id') else ('template', item['template_id'])
        clusters[cluster].append(p)

    if not clusters:
        return {
            'paired_presentations': 0,
            'excluded_pairs': len(pairs),
            'clusters': 0,
            'estimand': 'COOPERATE_minus_INDEPENDENT',
            'original_margin': None,
            'paraphrase_margin': None,
            'change_delta': None
        }

    # Group metrics for presentation-weighted cluster bootstrap
    groups = []
    logprob_groups = []

    for cluster_id, group in clusters.items():
        # Stratum counts for cluster
        c_orig, i_orig = 0, 0
        c_para, i_para = 0, 0
        lp_orig_sum, lp_para_sum = 0.0, 0.0
        lp_count = 0

        for p in group:
            orig = p['original']
            para = p['paraphrase']

            if mode in ('forced_no_ties', 'forced_include_ties'):
                s_o = orig['forced_choice']['strategy']
                s_p = para['forced_choice']['strategy']
            elif mode == 'strict_generated':
                s_o = orig['generated_strategy']
                s_p = para['generated_strategy']
            elif mode == 'recovered_generated':
                s_o = orig['recovered_strategy']
                s_p = para['recovered_strategy']

            if s_o == 'COOPERATE': c_orig += 1
            elif s_o == 'INDEPENDENT': i_orig += 1

            if s_p == 'COOPERATE': c_para += 1
            elif s_p == 'INDEPENDENT': i_para += 1

            # Log-prob contrast
            lp_o = compute_logprob_contrast(orig)
            lp_p = compute_logprob_contrast(para)
            if lp_o is not None and lp_p is not None:
                lp_orig_sum += lp_o
                lp_para_sum += lp_p
                lp_count += 1

        groups.append((c_orig - i_orig, c_para - i_para, len(group)))
        if lp_count > 0:
            logprob_groups.append((lp_orig_sum, lp_para_sum, lp_count))

    total_pairs = len(clean_pairs)
    orig_margin = sum(x[0] for x in groups) / total_pairs
    para_margin = sum(x[1] for x in groups) / total_pairs
    delta = para_margin - orig_margin

    # Resampling
    rng = random.Random(seed)
    orig_samples, para_samples, delta_samples = [], [], []

    for _ in range(bootstrap):
        draw = [rng.choice(groups) for _ in groups]
        denom = sum(x[2] for x in draw)
        if denom == 0:
            continue
        s_orig = sum(x[0] for x in draw) / denom
        s_para = sum(x[1] for x in draw) / denom
        orig_samples.append(s_orig)
        para_samples.append(s_para)
        delta_samples.append(s_para - s_orig)

    # Logprob contrast summaries
    lp_stats = {}
    if logprob_groups:
        lp_total = sum(x[2] for x in logprob_groups)
        lp_orig_mean = sum(x[0] for x in logprob_groups) / lp_total
        lp_para_mean = sum(x[1] for x in logprob_groups) / lp_total
        lp_delta_mean = lp_para_mean - lp_orig_mean

        lp_draws_orig, lp_draws_para, lp_draws_delta = [], [], []
        for _ in range(bootstrap):
            draw = [rng.choice(logprob_groups) for _ in logprob_groups]
            denom = sum(x[2] for x in draw)
            if denom == 0: continue
            so = sum(x[0] for x in draw) / denom
            sp = sum(x[1] for x in draw) / denom
            lp_draws_orig.append(so)
            lp_draws_para.append(sp)
            lp_draws_delta.append(sp - so)

        lp_stats = {
            'pairs_with_logprobs': lp_total,
            'original_mean_contrast': lp_orig_mean,
            'paraphrase_mean_contrast': lp_para_mean,
            'delta_mean_contrast': lp_delta_mean,
            'original_95pct_ci': bootstrap_ci(lp_draws_orig),
            'paraphrase_95pct_ci': bootstrap_ci(lp_draws_para),
            'delta_95pct_ci': bootstrap_ci(lp_draws_delta)
        }

    strategy_counts = {
        'original': dict(Counter(
            (p['original']['forced_choice']['strategy'] if 'forced' in mode else
             p['original'].get('recovered_strategy' if 'recovered' in mode else 'generated_strategy'))
            for p in clean_pairs
        )),
        'paraphrase': dict(Counter(
            (p['paraphrase']['forced_choice']['strategy'] if 'forced' in mode else
             p['paraphrase'].get('recovered_strategy' if 'recovered' in mode else 'generated_strategy'))
            for p in clean_pairs
        ))
    }

    return {
        'mode': mode,
        'paired_presentations': total_pairs,
        'excluded_pairs': len(pairs) - total_pairs,
        'clusters': len(groups),
        'bootstrap_resamples': bootstrap,
        'seed': seed,
        'estimand': 'COOPERATE_minus_INDEPENDENT_fraction',
        'strategy_counts': strategy_counts,
        'original_margin': orig_margin,
        'paraphrase_margin': para_margin,
        'change_delta': delta,
        'original_margin_95pct_ci': bootstrap_ci(orig_samples),
        'paraphrase_margin_95pct_ci': bootstrap_ci(para_samples),
        'change_delta_95pct_ci': bootstrap_ci(delta_samples),
        'logprob_contrast': lp_stats
    }


def analyze_model_rows(rows: List[dict], bootstrap: int = 2000, seed: int = 42) -> Dict[str, Any]:
    # Annotate rows with secondary recovered letter and strategy
    for r in rows:
        raw = r.get('generated_raw_text', '')
        l2s = r.get('letter_to_strategy', {})
        cat, let, strat = parse_generated_secondary(raw, l2s)
        r['recovered_category'] = cat
        r['recovered_letter'] = let
        r['recovered_strategy'] = strat

    # Group into pairs
    grouped = defaultdict(dict)
    for r in rows:
        key = (r['bank'], r['scenario_id'], r['permutation_index'])
        if r['wording'] in grouped[key]:
            raise ValueError(f"Duplicate presentation {key}")
        grouped[key][r['wording']] = r

    if any(set(v.keys()) != {'original', 'paraphrase'} for v in grouped.values()):
        raise ValueError("Incomplete original/paraphrase pairing")

    output = {'banks': {}, 'parser_audit': {}, 'pythia_diagnostics': {}}

    # Parser diagnostics across all presentations
    parser_cats = Counter(r['recovered_category'] for r in rows)
    strict_valid_count = sum(1 for r in rows if r.get('generated_strategy') is not None)
    rec_valid_count = sum(1 for r in rows if r.get('recovered_strategy') is not None)

    # Agreement with forced choice
    fc_agree_strict = sum(
        1 for r in rows
        if r.get('generated_strategy') is not None and
        r['forced_choice'] and r['generated_strategy'] == r['forced_choice']['strategy']
    )
    fc_agree_rec = sum(
        1 for r in rows
        if r.get('recovered_strategy') is not None and
        r['forced_choice'] and r['recovered_strategy'] == r['forced_choice']['strategy']
    )

    output['parser_audit']['overall'] = {
        'total_rows': len(rows),
        'strict_valid': strict_valid_count,
        'recovered_valid': rec_valid_count,
        'category_counts': dict(parser_cats),
        'strict_fc_agreement_rate': (fc_agree_strict / strict_valid_count) if strict_valid_count else 0.0,
        'recovered_fc_agreement_rate': (fc_agree_rec / rec_valid_count) if rec_valid_count else 0.0
    }

    # Positional diagnostics (critical for Pythia and position biases)
    fc_letters = Counter(r['forced_choice']['letter'] for r in rows if r.get('forced_choice'))
    gen_letters = Counter(r['recovered_letter'] for r in rows if r.get('recovered_letter'))
    fc_strategies = Counter(r['forced_choice']['strategy'] for r in rows if r.get('forced_choice'))
    
    # Conditional probability diagnostic for A vs other letters
    a_probs = [
        r['forced_choice']['conditional_probabilities']['A']
        for r in rows if r.get('forced_choice') and 'A' in r['forced_choice']['conditional_probabilities']
    ]

    output['pythia_diagnostics'] = {
        'fc_letter_distribution': dict(fc_letters),
        'gen_recovered_letter_distribution': dict(gen_letters),
        'fc_strategy_distribution': dict(fc_strategies),
        'mean_prob_letter_A': sum(a_probs) / len(a_probs) if a_probs else 0.0,
        'rate_letter_A': fc_letters.get('A', 0) / len(rows)
    }

    for bank in sorted({k[0] for k in grouped}):
        all_pairs = [v for k, v in grouped.items() if k[0] == bank]
        strata = {
            'all': all_pairs,
            'symmetric_control': [p for p in all_pairs if p['original'].get('is_symmetric_control')],
            'non_control_equal_utility': [
                p for p in all_pairs
                if p['original'].get('utility_condition') == 'equal_utility' and not p['original'].get('is_symmetric_control')
            ]
        }

        # Add partner strata
        for partner in ('human', 'ai'):
            strata[f'partner={partner}'] = [p for p in all_pairs if p['original'].get('partner_type') == partner]

        # Add context strata
        for ctx in ('neutral_or_costless', 'modest_cost', 'conflict_with_objective', 'ineffective_or_inappropriate'):
            strata[f'context={ctx}'] = [p for p in all_pairs if p['original'].get('context_type') == ctx]

        # Add split strata if present
        for sp in ('exploratory', 'confirmatory_heldout'):
            matching = [p for p in all_pairs if p['original'].get('split') == sp]
            if matching:
                strata[f'split={sp}'] = matching

        bank_results = {}
        for s_name, s_pairs in strata.items():
            if not s_pairs:
                continue
            bank_results[s_name] = {
                'forced_no_ties': analyze_stratum_pairs(s_pairs, 'forced_no_ties', bootstrap, seed),
                'forced_include_ties': analyze_stratum_pairs(s_pairs, 'forced_include_ties', bootstrap, seed),
                'strict_generated': analyze_stratum_pairs(s_pairs, 'strict_generated', bootstrap, seed),
                'recovered_generated': analyze_stratum_pairs(s_pairs, 'recovered_generated', bootstrap, seed)
            }

        # Bank parser agreement breakdown
        bank_rows = [r for r in rows if r['bank'] == bank]
        b_rec_valid = sum(1 for r in bank_rows if r.get('recovered_strategy') is not None)
        b_rec_agree = sum(
            1 for r in bank_rows
            if r.get('recovered_strategy') is not None and
            r['forced_choice'] and r['recovered_strategy'] == r['forced_choice']['strategy']
        )
        b_strict_valid = sum(1 for r in bank_rows if r.get('generated_strategy') is not None)
        b_strict_agree = sum(
            1 for r in bank_rows
            if r.get('generated_strategy') is not None and
            r['forced_choice'] and r['generated_strategy'] == r['forced_choice']['strategy']
        )

        output['banks'][bank] = {
            'strata': bank_results,
            'parser_audit': {
                'total_rows': len(bank_rows),
                'strict_valid': b_strict_valid,
                'recovered_valid': b_rec_valid,
                'strict_agreement_rate': (b_strict_agree / b_strict_valid) if b_strict_valid else 0.0,
                'recovered_agreement_rate': (b_rec_agree / b_rec_valid) if b_rec_valid else 0.0
            }
        }

    return output


def run_full_cohort_analysis(
    manifest_info: dict,
    bootstrap: int = 2000,
    seed: int = 42
) -> Dict[str, Any]:
    canonical_runs = manifest_info['canonical_runs']
    per_model_results = {}

    for model, run_info in canonical_runs.items():
        run_dir = ROOT / run_info['directory']
        rows = [json.loads(line) for line in (run_dir / 'rows.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        res = analyze_model_rows(rows, bootstrap=bootstrap, seed=seed)
        per_model_results[model] = {
            'run_id': run_info['run_id'],
            'directory': run_info['directory'],
            'model': model,
            'family': FAMILY_MAPPING.get(model, 'Other'),
            'analysis': res
        }

    # Exploratory family-aware aggregations
    # Distinctly separating 12 Base Checkpoints, Qwen Instruct, and Pythia SFT
    family_aggregates = {}
    base_models = [m for m in per_model_results if m in BASE_CHECKPOINTS]
    
    # Stratum to aggregate: non_control_equal_utility across phase0b and phase1
    for bank in ('phase0b', 'phase1'):
        fam_groups = defaultdict(list)
        for m in base_models:
            fam = FAMILY_MAPPING[m]
            m_res = per_model_results[m]['analysis']['banks'][bank]['strata']['non_control_equal_utility']['forced_no_ties']
            fam_groups[fam].append({
                'model': m,
                'original_margin': m_res['original_margin'],
                'paraphrase_margin': m_res['paraphrase_margin'],
                'change_delta': m_res['change_delta'],
                'pairs': m_res['paired_presentations']
            })

        family_aggregates[bank] = {
            'base_checkpoints_count': len(base_models),
            'unique_base_families': len(fam_groups),
            'by_family': {
                fam: {
                    'models_count': len(items),
                    'models': [x['model'] for x in items],
                    'mean_orig_margin': sum(x['original_margin'] for x in items) / len(items),
                    'mean_para_margin': sum(x['paraphrase_margin'] for x in items) / len(items),
                    'mean_delta': sum(x['change_delta'] for x in items) / len(items)
                }
                for fam, items in fam_groups.items()
            }
        }

    return {
        'per_model_results': per_model_results,
        'family_aggregates': family_aggregates,
        'bootstrap_settings': {'resamples': bootstrap, 'seed': seed}
    }
