"""OLMo-specific revision, capture and trajectory guard tests."""
import json

import numpy as np
import pytest
import torch

from llm_cooperation.mechanistic.contrastive_mapping import capture_final_token_residuals
from llm_cooperation.mechanistic.olmo_emergence import (MODEL_ID, resolve_checkpoints, prepare_plans,
    prepare_smoke_plan, analyze_trajectory, BANK)
from llm_cooperation.mechanistic.four_strategy_probe import analyze_four_strategy
from test_four_strategy_probe import make_fixture


class Block(torch.nn.Module):
    def __init__(self, scale):
        super().__init__()
        self.scale = scale

    def forward(self, x):
        return (x * self.scale,)


class OlmoLayout(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.model = torch.nn.Module()
        self.model.layers = torch.nn.ModuleList([Block(2), Block(3), Block(4)])

    def forward(self, input_ids, use_cache=False):
        x = input_ids.float().unsqueeze(-1).repeat(1, 1, 5)
        for layer in self.model.layers:
            x = layer(x)[0]
        return x


def test_olmo_layout_hooks_capture_final_token_and_remove_hooks():
    model = OlmoLayout()
    inputs = {"input_ids": torch.tensor([[1, 2, 3]])}
    residual = capture_final_token_residuals(model, inputs)
    assert residual.shape == (3, 5)
    np.testing.assert_allclose(residual[:, 0], [3 * 2, 3 * 2 * 3, 3 * 2 * 3 * 4])
    assert all(len(layer._forward_hooks) == 0 for layer in model.model.layers)


def test_live_revision_resolution_records_exact_commit_and_stage_order():
    class Ref:
        def __init__(self, name, sha):
            self.name, self.target_commit = name, sha

    class API:
        def list_repo_refs(self, repo_id, repo_type):
            assert repo_id == MODEL_ID and repo_type == "model"
            tags = [Ref(f"stage1-step{s}-tokens{t}B", f"{s:040x}") for s, t in
                    [(0, 0), (390000, 818), (1150000, 2412), (1530000, 3209), (1907359, 4001)]]
            tags.append(Ref("stage2-ingredient3-step23852-tokens51B", "f" * 40))
            return type("Refs", (), {"branches": [], "tags": tags})()

    selection = resolve_checkpoints(api=API())
    assert len(selection["checkpoints"]) == 5
    assert [r["training_stage_label"] for r in selection["checkpoints"]] == [
        "initialization", "early_stage1", "intermediate_stage1", "late_stage1_endpoint", "completed_pretrained_base"]
    assert [r["cumulative_tokens_billions"] for r in selection["checkpoints"]] == sorted(
        r["cumulative_tokens_billions"] for r in selection["checkpoints"])
    assert all(len(r["commit_sha"]) == 40 for r in selection["checkpoints"])
    assert selection["early_training_reconstruction_used"] is False


def test_revision_resolver_fails_when_official_trajectory_refs_are_missing():
    class API:
        def list_repo_refs(self, repo_id, repo_type):
            return type("Refs", (), {"branches": [], "tags": []})()

    with pytest.raises(RuntimeError, match="stage-one refs"):
        resolve_checkpoints(api=API())


def test_frozen_bank_plan_integration_keeps_checkpoint_prompts_identical(tmp_path):
    selection = {"version": "test", "model_id": MODEL_ID, "checkpoints": [
        {"model_id": MODEL_ID, "revision": f"stage1-step{s}-tokens{t}B", "commit_sha": f"{i + 1:040x}",
         "checkpoint_order": i, "training_stage": "stage1_pretraining", "training_step": s,
         "cumulative_tokens_billions": t, "training_stage_label": f"sample_{i}"}
        for i, (s, t) in enumerate([(0, 0), (390000, 818), (1150000, 2412), (1530000, 3209), (1907359, 4001)])]}
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    result = prepare_plans(selection_path, tmp_path / "plans", bank_path=BANK)
    assert len(result["plans"]) == 5
    assert len({row["prompts_sha256"] for row in result["plans"]}) == 1
    for row in result["plans"]:
        plan = json.loads((tmp_path / "plans" / f"checkpoint-{row['checkpoint_order']:02d}" / "manifest.json").read_text())
        assert plan["num_scenarios"] == 124 and plan["num_prompts"] == 496
        assert plan["target_model"] == MODEL_ID and plan["target_revision"] == row["commit_sha"]


def test_smoke_plan_is_capture_only_subset_of_frozen_bank(tmp_path):
    selection = {"model_id": MODEL_ID, "checkpoints": [
        {"model_id": MODEL_ID, "revision": "stage1-step0-tokens0B", "commit_sha": "a" * 40,
         "checkpoint_order": 0, "training_stage": "stage1_pretraining", "training_step": 0,
         "cumulative_tokens_billions": 0, "training_stage_label": "initialization"}] * 5}
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    prepared = prepare_smoke_plan(selection_path, tmp_path / "smoke", bank_path=BANK)
    plan = json.loads((tmp_path / "smoke" / "checkpoint-00" / "manifest.json").read_text())
    assert prepared["technical_smoke"] is True
    assert plan["smoke"] is True and 0 < plan["num_scenarios"] < 124
    assert plan["num_prompts"] == plan["num_scenarios"] * 4


def test_four_strategy_analysis_accepts_checkpoint_specific_model_and_dimensions(tmp_path):
    run, prompts, _ = make_fixture(tmp_path, layers=3, hidden=10)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["model_id"] = MODEL_ID
    manifest["model_revision"] = "a" * 40
    manifest["num_layers"] = 3
    manifest["hidden_size"] = 10
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = analyze_four_strategy(run, prompts, tmp_path / "olmo-analysis", n_boot=20,
        permutations=2, allow_mock=True, expected_model_id=MODEL_ID, expected_revision="a" * 40)
    assert report["model_id"] == MODEL_ID
    assert report["tensor_shape"] == [3, 10]
    assert len(report["domain_held_out"]["directional_consistency_primary_outcome"]) == 3


def test_trajectory_outputs_normalized_depth_and_checkpoint_layer_figures(tmp_path):
    run, prompts, _ = make_fixture(tmp_path, layers=2, hidden=8)
    analysis = analyze_four_strategy(run, prompts, tmp_path / "one-analysis", n_boot=10,
                                     permutations=1, allow_mock=True)
    analysis_path = tmp_path / "one-analysis" / "four_strategy_report.json"
    inputs = [{"checkpoint": {"checkpoint_order": i, "revision": f"rev{i}",
               "training_stage_label": f"stage{i}", "cumulative_tokens_billions": i * 100},
               "analysis_json": str(analysis_path)} for i in range(5)]
    report = analyze_trajectory(inputs, tmp_path / "trajectory", n_boot=10)
    assert report["statistical_criterion"]["bonferroni_tests"] == 40
    assert all(row["normalized_depth"] in (0.0, 1.0)
               for strategy in report["strategy_layer_trajectories"].values() for row in strategy)
    assert (tmp_path / "trajectory" / "olmo_emergence_layer_by_checkpoint.png").is_file()
    assert (tmp_path / "trajectory" / "olmo_emergence_separability_layer_by_checkpoint.png").is_file()

