"""Offline regressions for frozen stimuli, leakage controls and authorization."""

import numpy as np
import pytest

from llm_cooperation.mechanistic import cross_model_replication as cm


def test_frozen_inventory_and_grouping():
    rows, audit = cm.original_prompts()
    assert (len(rows), audit["scenarios"], audit["families"], audit["domains"]) == (
        496,
        124,
        54,
        24,
    )
    assert audit["family_split_counts"] == {"discovery": 27, "evaluation": 27}
    assert audit["domain_split_counts"] == {"discovery": 12, "evaluation": 12}
    assert all(
        "Action:" in r["prompt_text"] and r["prompt_text"].endswith("\nDecision:")
        for r in rows
    )


def test_normalized_depth_indices():
    assert cm.depth_indices(32) == [3, 7, 11, 15, 19, 23, 27, 31]
    assert cm.depth_indices(28) == [3, 6, 10, 13, 17, 20, 24, 27]
    assert cm.depth_indices(16) == [1, 3, 5, 7, 9, 11, 13, 15]


@pytest.mark.parametrize("kind", ["olmo2", "mistral"])
def test_installed_architecture_hook_api_with_tiny_random_cpu_models(kind):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM

    torch.manual_seed(42)
    config = AutoConfig.for_model(
        kind,
        vocab_size=128,
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
        max_position_embeddings=64,
        pad_token_id=0,
        eos_token_id=2,
    )
    model = AutoModelForCausalLM.from_config(config).float().eval()
    arr = cm.capture_vector(model, [1, 8, 11, 4], [0, 1])
    assert arr.shape == (2, 16) and np.isfinite(arr).all()
    assert all(not layer._forward_hooks for layer in model.model.layers)


def test_authorization_fails_before_loading_or_output(tmp_path):
    with pytest.raises(PermissionError):
        cm.capture("missing", "olmo7b", tmp_path / "run", True, False)
    assert not (tmp_path / "run").exists()


class OffsetTokenizer:
    def __init__(self, eos=False):
        self.eos = eos

    def __call__(self, text, **kwargs):
        return {
            "input_ids": [1, 2] + ([3] if self.eos else []),
            "offset_mapping": [(0, 0), (0, len(text))] + ([(0, 0)] if self.eos else []),
        }

    def encode(self, text, **kwargs):
        return [2]


def test_native_bos_ok_eos_capture_rejected():
    rows = [{"prompt_id": "p", "prompt_text": "A.\nDecision:", "action_text": "A."}]
    assert cm.token_audit(OffsetTokenizer(), rows, 100)[0]["capture_index"] == 1
    with pytest.raises(ValueError, match="Final token"):
        cm.token_audit(OffsetTokenizer(True), rows, 100)
    with pytest.raises(ValueError, match="truncation"):
        cm.token_audit(OffsetTokenizer(), rows, 1)


def test_conditional_selection_does_not_use_evaluation_labels():
    rows = [
        {"action_text": text}
        for text in ["share logs", "work alone", "reserve tools", "defer work"] * 5
    ]
    groups = np.repeat(np.arange(5), 4)
    train = groups != 4
    test = ~train
    y = np.tile(np.arange(4), 5)
    changed = y.copy()
    changed[test] = changed[test][::-1]
    features = np.tile(np.arange(4), (20, 1))
    a, hp_a = cm.conditional_fit(rows, features, y, groups, train, test, "lexical")
    b, hp_b = cm.conditional_fit(
        rows, features, changed, groups, train, test, "lexical"
    )
    assert hp_a == hp_b
    np.testing.assert_allclose(a, b)


def test_cluster_bands_preserve_paired_constant_differences():
    rng = np.random.default_rng(13)
    values = rng.normal(size=(12, 24))
    band = cm.simultaneous_ci(values, n_boot=100)
    assert np.all(np.array(band["lower"]) <= values.mean(axis=0))
    assert np.all(np.array(band["upper"]) >= values.mean(axis=0))
    diff = cm.simultaneous_ci(np.full((12, 24), 0.2), n_boot=100)
    np.testing.assert_allclose(diff["lower"], 0.2)
    np.testing.assert_allclose(diff["upper"], 0.2)
    with pytest.raises(ValueError, match="Undefined"):
        cm.simultaneous_ci([[np.nan], [0]])


def test_compare_rejects_unpaired_plans(tmp_path):
    paths = []
    for i in range(2):
        p = tmp_path / str(i)
        p.mkdir()
        paths.append(p)
        cm.write(
            p / "replication_analysis.json",
            {
                "model": {"model_id": cm.MODELS[list(cm.MODELS)[i]]},
                "plan_sha256": str(i),
            },
        )
    with pytest.raises(ValueError, match="Different stimulus"):
        cm.compare(paths, tmp_path / "out")
    assert not (tmp_path / "out").exists()
