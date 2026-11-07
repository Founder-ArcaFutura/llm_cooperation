"""Regression coverage for the Modal dose-response bank integration.

These checks are intentionally static: they never connect to Modal or provision a GPU.
"""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODAL_FILE = ROOT / "modal_app.py"
BANK_FILE = ROOT / "data" / "scenarios_dose_response_exploratory.json"


def test_modal_image_packages_dose_response_bank():
    source = MODAL_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    # Confirm that image construction explicitly ships the frozen exploratory bank.
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_local_file"
    ]
    paths = [tuple(ast.literal_eval(a) for a in c.args) for c in calls]
    assert (
        "data/scenarios_dose_response_exploratory.json",
        "/root/data/scenarios_dose_response_exploratory.json",
    ) in paths
    assert BANK_FILE.is_file()


def test_modal_bank_mapping_points_to_packaged_file():
    tree = ast.parse(MODAL_FILE.read_text(encoding="utf-8"))
    assignments = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SUPPORTED_BANKS" for t in n.targets)
    ]
    assert len(assignments) == 1
    banks = ast.literal_eval(assignments[0].value)
    assert banks["dose-response"] == "/root/data/scenarios_dose_response_exploratory.json"


def test_modal_dose_response_can_run_calibration_in_same_model_job():
    source = MODAL_FILE.read_text(encoding="utf-8")
    assert "include_calibration: bool = False" in source
    assert "run_calibration(" in source
    assert "Path(str(calibration_file) + \".summary.json\")" in source
    script = (ROOT / "scripts" / "run_dose_response_models.ps1").read_text(encoding="utf-8")
    assert "--include-calibration" in script
    assert "--authorize-confirmatory" not in script
    assert "--authorize-phase1-run" not in script
    ast.parse(source)


def test_modal_evaluation_executes_and_persists_optional_calibration(tmp_path, monkeypatch):
    import modal_app
    from types import SimpleNamespace

    calls = []
    calibration_path = tmp_path / "calibration.jsonl"
    monkeypatch.setattr(modal_app.os, "makedirs", lambda *args, **kwargs: None)
    monkeypatch.setattr(modal_app, "results_volume", SimpleNamespace(commit=lambda: None))
    monkeypatch.setattr(modal_app, "hf_cache_volume", SimpleNamespace(commit=lambda: None))
    monkeypatch.setattr(
        "llm_cooperation.harness.runner.run_experiment",
        lambda **kwargs: tmp_path / "behavior.jsonl",
    )

    def fake_calibration(**kwargs):
        calls.append(kwargs)
        return calibration_path, {"status": "PASS", "forced_choice_accuracy": 1.0}

    monkeypatch.setattr("llm_cooperation.harness.runner.run_calibration", fake_calibration)
    result = modal_app._execute_evaluation(
        model_name="mock-dose-response",
        revision="a" * 40,
        precision="bfloat16",
        device="cpu",
        seed=42,
        prompt_mode="standard_plaintext",
        bank="dose-response",
        include_calibration=True,
    )
    assert result == (str(tmp_path / "behavior.jsonl"), str(calibration_path))
    assert len(calls) == 1
    assert calls[0]["mock"] is False
    assert calls[0]["revision"] == "a" * 40
    assert (tmp_path / "calibration.jsonl.summary.json").is_file()
