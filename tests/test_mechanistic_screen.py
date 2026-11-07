import json
import numpy as np
import pytest
from llm_cooperation.mechanistic.screen import select_items, rank_candidates, control_candidates
from llm_cooperation.mechanistic.analyze import summarize


def test_split_keeps_partners_and_triads_together():
    selected = select_items()
    assert len(selected) == 60
    groups = {}
    for s, split in selected:
        groups.setdefault(s.triad_id or s.template_id, set()).add(split)
    assert all(len(v) == 1 for v in groups.values())
    assert {v.pop() for v in groups.values()} == {'discovery', 'evaluation'}


def test_ranking_and_same_layer_random_control():
    x = np.zeros((5, 2, 8))
    x[:, 1, 3] = np.arange(5)
    ranked = rank_candidates(x, np.arange(5), 1)
    assert (ranked[0]['layer'], ranked[0]['neuron']) == (1, 3)
    control = control_candidates(ranked, 8)
    assert control[0]['layer'] == 1 and control[0]['neuron'] != 3
    assert control == control_candidates(ranked, 8)


def test_summary_pairs_and_rejects_incomplete(tmp_path):
    (tmp_path / 'manifest.json').write_text(json.dumps({'status':'completed'}))
    rows = []
    for condition, margin in [('baseline', 1), ('candidate_zero', 0.5), ('random_zero', 0.9)]:
        for n in range(3):
            rows.append({'stage':'evaluation', 'condition':condition, 'presentation_id':str(n),
                'template_id':str(n), 'triad_id':None, 'margin':margin, 'partner_type':'human', 'utility_condition':'equal_utility', 'argmax_letter':'A', 'cooperate_letter':'A'})
        rows.append({'stage':'calibration', 'condition':condition, 'correct':True, 'greedy_single_token_letter':True})
    (tmp_path / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report = summarize(tmp_path, samples=100)
    assert report['effects']['candidate_zero']['mean_margin_change'] == pytest.approx(-0.5)
    rows.pop(0)
    (tmp_path / 'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError, match='unmatched'):
        summarize(tmp_path, samples=100)


def test_end_to_end_with_tiny_synthetic_model(tmp_path, monkeypatch):
    """Exercise hooks and artifacts without downloads or paid/model evidence."""
    import sys
    import types
    import torch
    import llm_cooperation.mechanistic.screen as screen

    items = screen.select_items()
    chosen = []
    seen = set()
    for s, _ in items:
        if s.template_id not in seen and not s.triad_id:
            seen.add(s.template_id)
            chosen.append((s, 'discovery' if len(chosen) < 4 else 'evaluation'))
        if len(chosen) == 5:
            break
    monkeypatch.setattr(screen, 'select_items', lambda: chosen)
    cal = json.loads(screen.CALIBRATION.read_text(encoding='utf8'))
    cal['items'] = cal['items'][:1]
    cal_path = tmp_path / 'cal.json'
    cal_path.write_text(json.dumps(cal), encoding='utf8')
    monkeypatch.setattr(screen, 'CALIBRATION', cal_path)
    class Tokenizer:
        def encode(self, text, add_special_tokens=False):
            if text in (' A', ' B', ' C', ' D'):
                return [ord(text[-1])]
            if text in ('A', 'B', 'C', 'D'):
                return [ord(text)]
            if text.endswith((' A', ' B', ' C', ' D')):
                return self.encode(text[:-2]) + [ord(text[-1])]
            return [1 + sum(text.encode()) % 30]
        def __call__(self, text, return_tensors=None):
            class Inputs(dict):
                def to(self, device):
                    return self
            coop = next((s.options[screen.StrategyType.COOPERATE] for s, _ in chosen if s.options[screen.StrategyType.COOPERATE] in text), None)
            letter = next((i for i, l in enumerate('ABCD') if coop and (l + '. ' + coop) in text), 0)
            return Inputs(input_ids=torch.tensor([[self.encode(text)[0] * 4 + letter]]))
        def decode(self, ids):
            return chr(ids[0]) if ids[0] < 128 else '?'
    class Layer(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.mlp = torch.nn.Module()
            self.mlp.down_proj = torch.nn.Linear(4, 4, bias=False)
            with torch.no_grad():
                self.mlp.down_proj.weight.copy_(torch.eye(4))
        def forward(self, x):
            return self.mlp.down_proj(x)
    class FakeModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList([Layer()])
            self.config = types.SimpleNamespace(model_type='qwen2', intermediate_size=4)
            self.device = torch.device('cpu')
            self.dtype = torch.float32
        def forward(self, input_ids):
            v = input_ids.float()
            x = torch.stack([v, v * v, v * 0 + 1, -v], dim=-1)
            x = self.model.layers[0](x)
            logits = torch.zeros((*v.shape, 128))
            logits.scatter_(-1, (65 + input_ids % 4).unsqueeze(-1), x[..., 0:1])
            return types.SimpleNamespace(logits=logits)
    fake = types.ModuleType('transformers')
    fake.__version__ = 'synthetic'
    fake.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *a, **k: Tokenizer())
    fake.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *a, **k: FakeModel())
    monkeypatch.setitem(sys.modules, 'transformers', fake)
    target = tmp_path / 'run'
    screen.run('Qwen/Qwen2.5-1.5B', 'a' * 40, target, top_k=1)
    report = summarize(target, samples=20)
    assert json.loads((target / 'manifest.json').read_text())['status'] == 'completed'
    assert report['effects']['candidate_zero']['presentations'] == 4
    assert report['calibration']['baseline']['n'] == 4
