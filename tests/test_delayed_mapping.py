import json
from collections import Counter

import numpy as np
import pytest

from llm_cooperation.mechanistic.delayed_mapping import (
    STRATEGIES, analyze, bank, continuation_ids, fit_probe, prepare, presentations, read_plan, run,
)


def test_crossed_order_and_label_design_and_prefix_isolation():
    rows = list(presentations(bank()[0]))
    assert len(rows) == 32
    for fmt in ('letters', 'numbers'):
        rs = [r for r in rows if r['format'] == fmt]
        for strategy in STRATEGIES:
            counts = Counter((r['order'].index(strategy), r['mapping'][strategy]) for r in rs)
            assert len(counts) == 16 and set(counts.values()) == {1}
    for pid in {r['prefix_id'] for r in rows}:
        rs = [r for r in rows if r['prefix_id'] == pid]
        assert len({r['prefix'] for r in rs}) == 1
        assert all('Response key' not in r['prefix'] and r['prompt'].startswith(r['prefix']) for r in rs)


def test_bank_split_and_control_integrity():
    items = bank()
    assert len({i['id'] for i in items}) == len(items)
    for family in {i['family'] for i in items}:
        assert len({i['split'] for i in items if i['family'] == family}) == 1
    for i in items:
        if i['task'] == 'payoff_check':
            scores = [o[0] for o in i['outcomes'].values()]
            assert len(set(scores)) == 4
        if i['regime'] == 'unavailable':
            assert i['outcomes']['joint'] == (0, 0)
        if i['regime'] == 'same_outcomes':
            assert i['outcomes']['joint'] == i['outcomes']['independent']
    assert {i['partner'] for i in items} == {'human', 'AI', 'non_social'}


def test_prepare_hashes_and_no_overwrite(tmp_path):
    out = tmp_path / 'plan'
    manifest = prepare(out, smoke=True)
    assert manifest['presentations'] == 9 * 32
    read_plan(out)
    with pytest.raises(FileExistsError):
        prepare(out)
    (out / 'bank.json').write_text('[]')
    with pytest.raises(ValueError, match='hash mismatch'):
        read_plan(out)


def test_authorization_before_model_loading(tmp_path):
    with pytest.raises(ValueError, match='authorize'):
        run('missing', tmp_path / 'out', 'Qwen/Qwen2.5-1.5B', 'a' * 40)
    assert not (tmp_path / 'out').exists()


def test_token_boundary_fail_closed():
    class Tokenizer:
        def encode(self, text, **kwargs):
            return [1] if text == 'prefix' else [2, 3]
    with pytest.raises(ValueError, match='tokenization'):
        continuation_ids(Tokenizer(), 'prefix', 'A')


def synthetic_run(out, smoke=True):
    prepare(out, smoke=smoke)
    m, rows = read_plan(out)
    m.update(status='completed', generate=False, layers=[1])
    (out / 'manifest.json').write_text(json.dumps(m))
    (out / 'activations').mkdir()
    observations = []
    for r in rows:
        # Deliberately biased response channel, independent of semantic action.
        favored = next(s for s in STRATEGIES if r['mapping'][s] in ('A', '1'))
        r.update(probabilities={s: .7 if s == favored else .1 for s in STRATEGIES},
                 unique_winner=favored)
        observations.append(r)
        np.savez(out / 'activations' / (r['prefix_id'] + '.npz'), residual=np.zeros((1, 3)))
    (out / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in observations))
    return observations


def test_report_exposes_label_bias_despite_balanced_aggregate(tmp_path):
    out = tmp_path / 'run'
    synthetic_run(out)
    report = analyze(out)
    cell = report['item_format'][0]
    assert cell['mean_joint_probability'] == pytest.approx(.25)
    assert cell['order_spread'] == pytest.approx(0)
    assert cell['label_spread'] == pytest.approx(.6)
    assert report['formats']['letters']['generated_invalid_fraction'] is None
    with pytest.raises(ValueError, match='Smoke'):
        fit_probe(out)


def test_duplicate_observations_rejected(tmp_path):
    out = tmp_path / 'run'
    rows = synthetic_run(out)
    rows[-1] = rows[0]
    (out / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError, match='duplicate'):
        analyze(out)


def test_constant_choices_refuse_probe(tmp_path, monkeypatch):
    monkeypatch.setattr("llm_cooperation.mechanistic.instrument_validity.assess", lambda _: {"status": "pass"})
    out = tmp_path / 'run'
    synthetic_run(out, smoke=False)
    with pytest.raises(ValueError, match='constant'):
        fit_probe(out)


def test_real_tiny_random_model_end_to_end_without_downloads(tmp_path, monkeypatch):
    # Real architecture/forward hooks/scoring; random local weights are harness evidence only.
    import torch
    import transformers
    from transformers import Qwen2Config, Qwen2ForCausalLM
    torch.set_num_threads(1)
    torch.manual_seed(19)
    model = Qwen2ForCausalLM(Qwen2Config(vocab_size=257, hidden_size=8,
        intermediate_size=16, num_hidden_layers=3, num_attention_heads=2,
        num_key_value_heads=2, max_position_embeddings=4096))
    class ByteTokenizer:
        eos_token_id = 0
        def encode(self, text, **kwargs):
            return [b+1 for b in text.encode('utf-8')]
        def decode(self, ids, **kwargs):
            return bytes([int(i)-1 for i in ids if int(i) > 0]).decode('utf-8', errors='replace')
    monkeypatch.setattr(transformers.AutoTokenizer, 'from_pretrained', lambda *a, **k: ByteTokenizer())
    monkeypatch.setattr(transformers.AutoModelForCausalLM, 'from_pretrained', lambda *a, **k: model)
    # Exercise raw full-response recording without an expensive generation loop.
    monkeypatch.setattr(model, 'generate', lambda tensor, **kwargs: torch.cat(
        [tensor, torch.tensor([[33, 66]], device=tensor.device)], dim=1))
    plan = tmp_path / 'plan'
    prepare(plan, smoke=True)
    m, rows = read_plan(plan)
    first_item = rows[0]['item_id']
    rows = [r for r in rows if r['item_id'] == first_item and r['format'] == 'letters' and r['rotation'] < 2]
    (plan / 'presentations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
    from llm_cooperation.mechanistic.delayed_mapping import sha
    m['presentations_sha256'] = sha(plan / 'presentations.jsonl')
    m['presentations'] = len(rows); m['prefixes'] = 4
    (plan / 'manifest.json').write_text(json.dumps(m), encoding='utf-8')
    out = tmp_path / 'run'
    result = run(plan, out, 'Qwen/Qwen2.5-1.5B', 'a'*40, authorize=True, generate=True)
    assert result['scenarios'] == 1
    saved = json.loads((out / 'manifest.json').read_text())
    assert saved['status'] == 'completed'
    observations = [json.loads(x) for x in (out / 'observations.jsonl').read_text().splitlines()]
    assert len(observations) == 8
    for row in observations:
        assert sum(row['probabilities'].values()) == pytest.approx(1)
        assert row['generated_text'] == ' A'
        assert row['generated_valid'] is True
        arr = np.load(out / 'activations' / (row['id'] + '.npz'))['residual']
        assert arr.shape == (2, 8) and np.isfinite(arr).all()


def test_fit_probe_and_baselines_on_synthetic_signal(tmp_path, monkeypatch):
    monkeypatch.setattr("llm_cooperation.mechanistic.instrument_validity.assess", lambda _: {"status": "pass"})
    out = tmp_path / 'run'
    rows = synthetic_run(out, smoke=False)
    regime_score = {'mutual_gain': .8, 'actor_cost': .3, 'same_outcomes': .6, 'unavailable': .1}
    for row in rows:
        target = regime_score[row['regime']] + (.02 if row['partner'] == 'AI' else 0)
        row['probabilities'] = {s: target if s == 'joint' else (1-target)/3 for s in STRATEGIES}
        np.savez(out / 'activations' / (row['prefix_id'] + '.npz'), residual=np.array([[target, target*2, 1]]))
    (out / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report = fit_probe(out)
    letters = report['heldout_format_transfer']['letters']
    assert letters['mse'] < letters['discovery_mean_baseline_mse']
    assert 'payoff_only_baseline_mse' in letters
    assert len(report['family_permuted_training_target_control_mse']) == 5
    assert (out / 'probe.npz').exists()


def test_model_load_failure_is_preserved(tmp_path, monkeypatch):
    import transformers
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic load failure')
    monkeypatch.setattr(transformers.AutoTokenizer, 'from_pretrained', fail)
    plan = tmp_path / 'plan'
    prepare(plan, smoke=True)
    out = tmp_path / 'run'
    with pytest.raises(RuntimeError, match='synthetic load failure'):
        run(plan, out, 'Qwen/Qwen2.5-1.5B', 'a'*40, authorize=True)
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['status'] == 'failed'
    assert manifest['error_type'] == 'RuntimeError'
    with pytest.raises(ValueError, match='Incomplete'):
        analyze(out)


def test_validity_rejects_biased_and_missing_evidence(tmp_path):
    from llm_cooperation.mechanistic.instrument_validity import assess
    out = tmp_path / 'run'
    synthetic_run(out)
    result = assess(out)
    assert result['status'] == 'fail'
    assert result['checks']['complete_crossing']
    assert not result['checks']['evidence_integrity']
    assert not result['checks']['max_label_spread']
    assert not result['checks']['letters_generation']


def test_validity_detects_observation_mapping_mismatch(tmp_path):
    from llm_cooperation.mechanistic.instrument_validity import assess
    out = tmp_path / 'run'
    rows = synthetic_run(out)
    rows[0]['mapping']['joint'] = 'wrong'
    (out / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError, match='metadata'):
        assess(out)


def test_analyze_does_not_overwrite_report(tmp_path):
    out = tmp_path / 'run'
    synthetic_run(out)
    report = out / 'instrument_report.json'
    report.write_text('preserved')
    analyze(out)
    assert report.read_text() == 'preserved'

def test_validity_detects_score_normalization_mismatch(tmp_path):
    from llm_cooperation.mechanistic.instrument_validity import assess
    out = tmp_path / 'run'
    rows = synthetic_run(out)
    rows[0]['scores'] = {s: 0.0 for s in STRATEGIES}
    (out / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError, match='normalization'):
        assess(out)
