import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from llm_cooperation import factorial_inference as f


def scored(row, target_logit=2.0):
    if callable(target_logit): target_logit = target_logit(row)
    values = {k: target_logit if a == 'target' else 0.0 for k, a in row['letter_to_action'].items()}
    denominator = sum(math.exp(v) for v in values.values())
    tied = [k for k, v in values.items() if v == max(values.values())]
    selected = tied[0] if len(tied) == 1 else None
    generated = next(k for k, a in row['letter_to_action'].items() if a == 'target')
    return {**row, 'prompt_sha256': f.sha(row['prompt'].encode()),
            'candidate_token_ids': {k: ord(k) for k in values}, 'raw_logits': values,
            'conditional_probs': {k: math.exp(v) / denominator for k, v in values.items()},
            'conditional_logprobs': {k: v - math.log(denominator) for k, v in values.items()},
            'full_vocab_logprobs': {k: v - 10 for k, v in values.items()},
            'tied_max_letters': tied, 'forced_letter': selected,
            'forced_action': row['letter_to_action'][selected] if selected else None, 'generated_raw_text': generated,
            'generated_letter': generated, 'generated_action': 'target'}


def test_preflight_preserves_schedule_and_smoke_is_representative():
    rows, manifest, raw, conditions = f.load_inputs()
    smoke, sm, _, _ = f.load_inputs(smoke=True)
    assert len(rows) == 4576 and len(smoke) == 44
    assert len({r['presentation_id'] for r in smoke}) == 44
    assert {r['choice_set'] for r in smoke} == {'binary', 'four_action'}
    assert {r['block'] for r in smoke} == {'mechanism_cost', 'return_cost', 'dependency_cost'}
    assert {r['identity'] for r in smoke} == {'human', 'embodied_automation'}
    assert sm['presentation_file_sha256'] == manifest['presentation_file_sha256'] == f.sha(raw)
    source = json.loads(raw.decode().splitlines()[0])
    assert rows[0]['stem'] == source['stem'] and rows[0]['options'] == source['options']
    assert rows[0]['prompt'].endswith('Answer with only A or B.\nAnswer:')
    broken = [json.loads(line) for line in raw.decode().splitlines()]
    broken[0]['options']['A'] = 'changed'
    with pytest.raises(ValueError, match='Option text'):
        f.prepare('\n'.join(json.dumps(r) for r in broken).encode(), conditions)
    with pytest.raises(ValueError, match='counterbalance'):
        f.prepare(b'\n'.join(raw.splitlines()[1:]), conditions)


def test_ties_mapping_and_resume_reject_corruption():
    rows, *_ = f.load_inputs(smoke=True)
    row = rows[0]
    result = scored(row, 0)
    assert result['forced_action'] is None
    assert f.validate_resume([result], rows) == {row['presentation_id']}
    with pytest.raises(ValueError, match='Duplicate'):
        f.validate_resume([result, result], rows)
    wrong = copy.deepcopy(result); wrong['conditional_probs']['A'] += .1
    with pytest.raises(ValueError, match='Probability'):
        f.validate_scored(wrong, row)


def test_adapter_scoring_uses_existing_boundary_and_restricts_candidates():
    torch = pytest.importorskip('torch')
    class Batch(dict):
        def to(self, device): return self
    class Tokenizer:
        pad_token_id = 0
        def encode(self, text, add_special_tokens=True): return [ord(c) % 128 for c in text]
        def __call__(self, text, return_tensors): return Batch(input_ids=torch.tensor([self.encode(text)]))
        def decode(self, ids, skip_special_tokens): return ''.join(chr(int(x)) for x in ids)
    class Model:
        device = 'cpu'
        def __call__(self, **inputs):
            logits = torch.zeros((1, 1, 128)); logits[0, 0, 67] = 100 # unpresented C must not win binary
            logits[0, 0, 65] = logits[0, 0, 66] = 3
            return SimpleNamespace(logits=logits)
        def generate(self, **inputs): return torch.cat([inputs['input_ids'], torch.tensor([[67]])], dim=1)
    rows, *_ = f.load_inputs(smoke=True)
    row = next(r for r in rows if r['choice_set'] == 'binary')
    result = f.score_row(SimpleNamespace(model=Model(), tokenizer=Tokenizer()), row)
    assert set(result['conditional_probs']) == {'A', 'B'}
    assert result['conditional_probs'] == {'A': .5, 'B': .5}
    assert result['forced_letter'] is None and result['tied_max_letters'] == ['A', 'B']
    assert result['generated_action'] is None  # C is invalid for the displayed binary set
    f.validate_scored(result, row)


def make_run(folder, smoke=False, target_logit=2):
    rows, manifest, *_ = f.load_inputs(smoke=smoke)
    manifest.update({'model': 'fixture', 'run_id': folder.name})
    folder.mkdir()
    f.write_json(folder / 'manifest.json', manifest)
    f.write_json(folder / 'summary.json', {'status': 'complete', 'fingerprint_sha256': f.sha(f.canonical(manifest))})
    (folder / 'rows.jsonl').write_text(''.join(json.dumps(scored(r, target_logit)) + '\n' for r in rows), encoding='utf-8')
    return rows


def test_analysis_complete_factorials_and_no_false_cost_effect(tmp_path):
    run = tmp_path / 'full'
    make_run(run)
    f.analyze([run], tmp_path / 'analysis')
    import csv
    contrasts = list(csv.DictReader((tmp_path / 'analysis/family_contrasts.csv').open()))
    assert contrasts and all(abs(float(r['estimate'])) < 1e-12 for r in contrasts)
    assert {'cost_20_minus_0', 'return_x_cost', 'dependency_x_cost', 'mechanism_x_cost', 'mechanism_package'} <= {r['contrast'] for r in contrasts}
    # Analysis must not silently accept incomplete result sets, even with a complete summary.
    path = run / 'rows.jsonl'
    path.write_text('\n'.join(path.read_text(encoding='utf-8').splitlines()[1:]) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Missing presentations'):
        f.analyze([run], tmp_path / 'bad')


def test_analysis_interaction_sign_and_probability_scale(tmp_path):
    grid = {(0, 0): .4, (0, 20): .2, (1, 0): .7, (1, 20): .8}
    def logit(row):
        p = grid[(row['factors']['return'], row['factors']['cost'])] if row['block'] == 'return_cost' else .6
        return math.log(p * (len(row['options']) - 1) / (1 - p))
    run = tmp_path / 'interaction'
    make_run(run, target_logit=logit)
    f.analyze([run], tmp_path / 'analysis')
    import csv
    with (tmp_path / 'analysis/family_contrasts.csv').open() as handle:
        contrasts = list(csv.DictReader(handle))
    interaction = [r for r in contrasts if r['contrast'] == 'return_x_cost' and r['metric'] == 'mean_target_probability']
    assert len(interaction) == 4
    assert all(float(r['estimate']) == pytest.approx(.3) for r in interaction)


def test_smoke_requires_explicit_diagnostic_mode(tmp_path):
    run = tmp_path / 'smoke'
    make_run(run, smoke=True)
    with pytest.raises(ValueError, match='Smoke results'):
        f.analyze([run], tmp_path / 'bad')
    f.analyze([run], tmp_path / 'analysis', allow_smoke=True)
    assert json.loads((tmp_path / 'analysis/analysis_manifest.json').read_text())['contrasts'] == 0


def test_resume_preserves_interrupted_append(tmp_path):
    pytest.importorskip('modal')
    from modal_factorial_cooperation import read_existing
    path = tmp_path / 'rows.jsonl'
    path.write_bytes(b'{"complete": true}\n{"interrupted":')
    assert read_existing(path) == [{'complete': True}]
    assert path.read_bytes() == b'{"complete": true}\n'
    assert next(tmp_path.glob('interrupted_tail_*.bin')).read_bytes() == b'{"interrupted":'
    path.write_bytes(b'{"bad complete row"}\n')
    with pytest.raises(json.JSONDecodeError): read_existing(path)
