"""Synthetic unit and end-to-end coverage for the four-strategy probe."""
import hashlib
import json

import numpy as np
import pytest

from llm_cooperation.mechanistic.four_strategy_probe import (
    analyze_four_strategy, load_dataset, scenario_center,
)
from llm_cooperation.mechanistic.contrastive_mapping import STRATEGIES, DEFAULT_MODEL_ID, DEFAULT_REVISION


def make_fixture(root, *, n_scenarios=12, layers=2, hidden=12):
    run = root / "run"
    acts = run / "activations"
    acts.mkdir(parents=True)
    rows, arrays = [], {}
    for si in range(n_scenarios):
        sid = f"s{si:03d}"
        fam_index = si
        domain_index = si // 2
        split = "discovery" if fam_index < n_scenarios // 2 else "evaluation"
        domain_split = "discovery" if domain_index < (n_scenarios // 4) else "evaluation"
        shared = np.random.default_rng(si).normal(0, .05, size=(layers, hidden))
        for yi, strategy in enumerate(STRATEGIES):
            p = {"prompt_id": f"{sid}_{strategy}", "scenario_id": sid, "strategy": strategy,
                 "group_key": f"f{fam_index}", "domain": f"d{domain_index}",
                 "split": split, "domain_split": domain_split,
                 "action_word_count": yi + 4, "action_char_count": yi * 3 + 12,
                 "action_text": f"A synthetic action description number {yi}."}
            rows.append(p)
            # Strategy vectors are deliberately linearly separated, with scenario nuisance removed by centering.
            center = np.zeros((layers, hidden)); center[:, yi] = 2.0
            arr = shared + center + np.random.default_rng(si * 17 + yi).normal(0, .1, size=(layers, hidden))
            path = acts / f"{p['prompt_id']}.npz"
            np.savez_compressed(path, residual=arr.astype(np.float32))
            arrays[f"activations/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    prompts_path = run / "prompts.jsonl"
    prompts_path.write_text("".join(json.dumps(p) + "\n" for p in rows), encoding="utf-8")
    prompt_sha = hashlib.sha256(prompts_path.read_bytes()).hexdigest()
    hashes = {"prompts.jsonl": prompt_sha, **arrays}
    hash_path = run / "evidence_hashes.json"
    hash_path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    manifest = {"status": "completed", "model_id": DEFAULT_MODEL_ID, "model_revision": DEFAULT_REVISION,
                "mock": True, "num_scenarios": n_scenarios, "num_prompts": len(rows),
                "num_layers": layers, "hidden_size": hidden, "prompts_sha256": prompt_sha,
                "evidence_hashes_sha256": hashlib.sha256(hash_path.read_bytes()).hexdigest()}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return run, prompts_path, rows


def test_scenario_centering_zeroes_each_scenario_mean(tmp_path):
    run, prompts, rows = make_fixture(tmp_path)
    _, loaded, arrays = load_dataset(run, prompts, allow_mock=True)
    sids, _, x = scenario_center(loaded, arrays)
    assert len(sids) == 12
    np.testing.assert_allclose(x.mean(axis=1), 0.0, atol=1e-12)


def test_loader_rejects_tampered_activation_hash(tmp_path):
    run, prompts, _ = make_fixture(tmp_path)
    target = next((run / "activations").glob("*.npz"))
    target.write_bytes(target.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="Evidence hash mismatch"):
        load_dataset(run, prompts, allow_mock=True)


def test_end_to_end_synthetic_analysis(tmp_path):
    run, prompts, _ = make_fixture(tmp_path)
    report = analyze_four_strategy(run, prompts, tmp_path / "analysis", expected_prompts_path=str(prompts),
                                   n_boot=50, permutations=3, allow_mock=True)
    assert len(report["family_held_out"]["layer_metrics"]) == 2
    assert len(report["domain_held_out"]["layer_metrics"]) == 2
    assert len(report["geometry"]["pairwise_direction_cosines"]) == 2
    assert len(report["geometry"]["effective_rank"]) == 2
    assert set(report["controls"]["lexical_length"]) == set(STRATEGIES)
    assert (tmp_path / "analysis" / "four_strategy_report.json").is_file()
    assert (tmp_path / "analysis" / "four_strategy_report.md").is_file()
    assert (tmp_path / "analysis" / "four_strategy_layerwise.png").is_file()
    assert (tmp_path / "analysis" / "four_strategy_geometry.png").is_file()
