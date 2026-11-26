"""Regression tests for manuscript-readiness audit, run accounting, parser, and statistics."""
import json
import pytest
from pathlib import Path

from llm_cooperation.response_parser import parse_strict, parse_generated_secondary
from llm_cooperation.statistical_audit import (
    analyze_stratum_pairs,
    compute_logprob_contrast,
    FAMILY_MAPPING,
    BASE_CHECKPOINTS
)
from scripts.audit_cooperate_rewording_results import audit_cohort_and_provenance

MANIFEST_PATH = Path('data/cooperate_rewording_model_manifest.json')
READOUT_PATH = Path('reports/manuscript_readiness/cohort_statistical_readout.json')
PROVENANCE_PATH = Path('reports/manuscript_readiness/cohort_provenance_manifest.json')


def test_manifest_coverage_and_provenance():
    """Verify that audit_cohort_and_provenance validates all 14 models without errors."""
    res = audit_cohort_and_provenance()
    assert res['expected_models'] == 14
    assert res['completed_unique_models'] == 14
    assert len(res['missing_models']) == 0
    assert res['total_run_directories'] == 17
    # 3 duplicate reruns must be documented
    assert set(res['duplicate_records'].keys()) == {
        'google/gemma-2-9b',
        'EleutherAI/pythia-12b-deduped',
        'Qwen/Qwen2.5-3B-Instruct'
    }
    for model, d_info in res['duplicate_records'].items():
        assert d_info['status'] == 'verified_identical_rerun'


def test_parser_edge_cases():
    """Verify response parsing across edge cases: strict, trailing explanations, multi-answer, contradictory."""
    mapping = {'A': 'COOPERATE', 'B': 'INDEPENDENT', 'C': 'COMPETE_EXPLOIT', 'D': 'DISENGAGE'}

    # 1. Clean strict single letter
    assert parse_strict(' A', mapping) == ('A', 'COOPERATE')
    assert parse_strict('D.', mapping) == ('D', 'DISENGAGE')
    assert parse_strict('[B]', mapping) == ('B', 'INDEPENDENT')

    # 2. Strict parser rejects explanations
    assert parse_strict('A\n\nExplanation: The reason...', mapping) == (None, None)
    assert parse_strict('A, B, C', mapping) == (None, None)

    # 3. Secondary parser accepts initial letter with explanation
    cat, let, strat = parse_generated_secondary('A\n\nExplanation: The reason is simple', mapping)
    assert cat == 'VALID_INITIAL_LETTER_WITH_TEXT'
    assert let == 'A'
    assert strat == 'COOPERATE'

    # 4. Multi-answer ambiguity
    cat, let, strat = parse_generated_secondary('A, B, C', mapping)
    assert cat == 'AMBIGUOUS_MULTI_ANSWER'
    assert let is None

    cat, let, strat = parse_generated_secondary('Choose A or B', mapping)
    assert cat == 'AMBIGUOUS_MULTI_ANSWER'

    # 5. Contradictory explanation
    cat, let, strat = parse_generated_secondary('A\n\nThe correct answer is B', mapping)
    assert cat == 'CONTRADICTORY_EXPLANATION'
    assert let is None

    # 6. Arbitrary mention without initial choice
    cat, let, strat = parse_generated_secondary('I think B is the best move here', mapping)
    assert cat == 'ARBITRARY_MENTION_WITHOUT_INITIAL'
    assert let is None

    # 7. Unparseable
    cat, let, strat = parse_generated_secondary('## 1\nSome header', mapping)
    assert cat == 'UNPARSEABLE'
    assert let is None


def test_pythia_instrument_failure_not_null_finding():
    """Verify Pythia 12B base and exploratory SFT exhibit extreme position bias (~100% A)."""
    assert READOUT_PATH.exists()
    data = json.loads(READOUT_PATH.read_text(encoding='utf-8-sig'))
    models = data['per_model_results']

    pythia_base = models['EleutherAI/pythia-12b-deduped']['analysis']['pythia_diagnostics']
    pythia_sft = models['founder-arcafutura/pythia-12b-exploratory-20261022']['analysis']['pythia_diagnostics']

    # Both must have >99% letter A selection
    assert pythia_base['rate_letter_A'] > 0.99
    assert pythia_sft['rate_letter_A'] > 0.99

    # Free generation for exploratory SFT must be overwhelmingly repetitive A, B, C
    sft_cats = models['founder-arcafutura/pythia-12b-exploratory-20261022']['analysis']['parser_audit']['overall']['category_counts']
    assert sft_cats.get('AMBIGUOUS_MULTI_ANSWER', 0) > 2300


def test_family_aware_mapping():
    """Verify family aggregation separates base models from instruct/exploratory variants."""
    assert len(BASE_CHECKPOINTS) == 12
    base_families = {FAMILY_MAPPING[m] for m in BASE_CHECKPOINTS}
    assert len(base_families) == 8
    assert FAMILY_MAPPING['Qwen/Qwen2.5-3B-Instruct'] == 'Qwen_Instruct'
    assert FAMILY_MAPPING['founder-arcafutura/pythia-12b-exploratory-20261022'] == 'Pythia_Exploratory'


def test_cluster_bootstrap_and_logprob_contrast():
    """Verify that clustered bootstrap handles repeated measures and computes logprob contrasts."""
    row_orig = {
        'scenario_id': 's1',
        'template_id': 'tpl_1',
        'triad_id': 'triad_1',
        'letter_to_strategy': {'A': 'COOPERATE', 'B': 'INDEPENDENT', 'C': 'COMPETE_EXPLOIT', 'D': 'DISENGAGE'},
        'forced_choice': {
            'letter': 'A',
            'strategy': 'COOPERATE',
            'tied_max_count': 1,
            'conditional_probabilities': {'A': 0.7, 'B': 0.1, 'C': 0.1, 'D': 0.1}
        }
    }
    row_para = {
        'scenario_id': 's1',
        'template_id': 'tpl_1',
        'triad_id': 'triad_1',
        'letter_to_strategy': {'A': 'COOPERATE', 'B': 'INDEPENDENT', 'C': 'COMPETE_EXPLOIT', 'D': 'DISENGAGE'},
        'forced_choice': {
            'letter': 'A',
            'strategy': 'COOPERATE',
            'tied_max_count': 1,
            'conditional_probabilities': {'A': 0.6, 'B': 0.2, 'C': 0.1, 'D': 0.1}
        }
    }
    lp_contrast = compute_logprob_contrast(row_orig)
    assert lp_contrast is not None
    assert pytest.approx(lp_contrast, 0.01) == 1.9459  # ln(0.7) - ln(0.1)

    pair = {'original': row_orig, 'paraphrase': row_para}
    res = analyze_stratum_pairs([pair], mode='forced_no_ties', bootstrap=100, seed=42)
    assert res['paired_presentations'] == 1
    assert res['clusters'] == 1
    assert res['original_margin'] == 1.0
    assert res['paraphrase_margin'] == 1.0
    assert res['change_delta'] == 0.0
