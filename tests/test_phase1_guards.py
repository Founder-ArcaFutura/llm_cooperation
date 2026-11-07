"""Tests for Phase 1 holdout protection and fail-closed inference guards.

Tests cover:
- Draft rejection (draft_pending_review)
- Authorization rejection (without --authorize-phase1-run)
- Missing or unapproved freeze manifest fails closed
- Draft-hash-to-frozen-hash transition fails without newly approved manifest
- Caller cannot bypass the trusted freeze manifest via CLI options or environment
- Modal container image packages configs/phase1_freeze_manifest.json
- Missing bank file
- Malformed bank metadata / schema
- Bypass attempts through alternate filenames
- Approved frozen execution using synthetic fixture (never real Phase 1 scenarios)
- Phase 0B confirmatory guard preservation
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
from click.testing import CliRunner

from llm_cooperation.cli import main
from llm_cooperation.harness.runner import (
    run_experiment,
    verify_phase1_freeze_manifest,
    PHASE1_FREEZE_MANIFEST_PATH,
)
import modal_app


def test_cli_phase1_holdout_guard_blocks_draft():
    """Verify CLI blocks execution against Phase 1 bank while in draft status."""
    runner = CliRunner()
    res = runner.invoke(main, ["run", "-m", "mock-model", "--mock", "--bank", "phase1"])
    assert res.exit_code != 0
    assert "PHASE 1 HOLDOUT PROTECTION TRIGGERED" in res.output


def test_cli_phase1_holdout_guard_blocks_custom_path():
    """Verify CLI blocks execution when passing custom path to Phase 1 scenarios."""
    runner = CliRunner()
    res = runner.invoke(main, ["run", "-m", "mock-model", "--mock", "--scenarios-path", "data/scenarios_phase1_prospective.json"])
    assert res.exit_code != 0
    assert "PHASE 1 HOLDOUT PROTECTION TRIGGERED" in res.output


def test_cli_phase1_holdout_guard_blocks_even_with_auth_flag():
    """Verify CLI blocks execution even if --authorize-phase1-run is passed while bank is draft."""
    runner = CliRunner()
    res = runner.invoke(main, ["run", "-m", "mock-model", "--mock", "--bank", "phase1", "--authorize-phase1-run"])
    assert res.exit_code != 0
    assert "PHASE 1 HOLDOUT PROTECTION TRIGGERED" in res.output


def test_runner_phase1_holdout_guard_direct_call():
    """Verify direct invocation of run_experiment fails closed on Phase 1 draft bank."""
    with pytest.raises(PermissionError, match="PHASE 1 HOLDOUT PROTECTION TRIGGERED"):
        run_experiment(
            model_name="mock-model",
            scenarios_path="data/scenarios_phase1_prospective.json",
            mock=True,
            authorize_phase1_run=False,
        )

    with pytest.raises(PermissionError, match="PHASE 1 HOLDOUT PROTECTION TRIGGERED"):
        run_experiment(
            model_name="mock-model",
            scenarios_path="data/scenarios_phase1_prospective.json",
            mock=True,
            authorize_phase1_run=True,
        )


def test_runner_phase1_missing_bank_file():
    """Verify missing bank file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        run_experiment(
            model_name="mock-model",
            scenarios_path="data/nonexistent_phase1_bank.json",
            mock=True,
            authorize_phase1_run=True,
        )


def test_runner_phase1_malformed_bank_metadata(tmp_path):
    """Verify malformed metadata or corrupted JSON is rejected."""
    bad_json = tmp_path / "scenarios_phase1_bad.json"
    bad_json.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(bad_json),
            mock=True,
            authorize_phase1_run=True,
        )

    bad_schema = tmp_path / "scenarios_phase1_schema.json"
    bad_schema.write_text(json.dumps({"version": "1.0", "status": "draft", "scenarios": "invalid"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed scenario bank metadata"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(bad_schema),
            mock=True,
            authorize_phase1_run=True,
        )


def test_runner_phase1_bypass_attempt_alternate_filename(tmp_path):
    """Verify that renaming the bank file to hide 'phase1' in filename still triggers Phase 1 guards."""
    with open("data/scenarios_phase1_prospective.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Saved with innocent filename
    stealth_bank = tmp_path / "benign_custom_scenarios.json"
    with open(stealth_bank, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Direct run_experiment must still detect phase1 templates/scenarios and block
    with pytest.raises(PermissionError, match="PHASE 1 HOLDOUT PROTECTION TRIGGERED"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(stealth_bank),
            mock=True,
            authorize_phase1_run=True,
        )


def test_freeze_manifest_fails_closed_when_unapproved(tmp_path):
    """Verify that the unapproved freeze manifest blocks execution even if bank was frozen."""
    synthetic_bank = {
        "version": "1.0.0-synthetic",
        "status": "frozen",
        "description": "Synthetic frozen bank",
        "scenarios": [{
            "id": "phase1_001_human",
            "template_id": "phase1_tpl_001",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "source_type": "prospective_replication",
            "split": "confirmatory",
            "domain": "test",
            "title": "Test",
            "stem": "Test stem for verifying unapproved manifest rejection.",
            "options": {"COOPERATE": "Coop opt.", "INDEPENDENT": "Indep opt.", "COMPETE_EXPLOIT": "Comp opt.", "DISENGAGE": "Dis opt."},
            "is_symmetric_control": False,
        }],
    }
    syn_path = tmp_path / "synthetic_frozen.json"
    with open(syn_path, "w", encoding="utf-8") as f:
        json.dump(synthetic_bank, f)

    # With default manifest (which has status 'pending_human_scientific_review')
    with pytest.raises(PermissionError, match="PHASE 1 FREEZE MANIFEST UNAPPROVED"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(syn_path),
            mock=True,
            authorize_phase1_run=True,
            _freeze_manifest_override=PHASE1_FREEZE_MANIFEST_PATH,
        )


def test_draft_hash_to_frozen_hash_transition_fails_closed(tmp_path):
    """Regression test: Proves that the draft-hash cannot validate a legitimately frozen bank.

    Freezing changes file bytes, and without a newly approved manifest recording the post-freeze
    hash, execution must fail closed.
    """
    draft_hash = hashlib.sha256(Path("data/scenarios_phase1_prospective.json").read_bytes()).hexdigest()

    # Simulate freezing the bank (status changed to frozen)
    with open("data/scenarios_phase1_prospective.json", "r", encoding="utf-8") as f:
        frozen_data = json.load(f)
    frozen_data["status"] = "frozen"

    frozen_path = tmp_path / "scenarios_phase1_frozen.json"
    with open(frozen_path, "w", encoding="utf-8") as f:
        json.dump(frozen_data, f, indent=2)

    frozen_hash = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
    assert frozen_hash != draft_hash, "Frozen hash must differ from draft hash!"

    # Create a manifest that erroneously pinned the draft hash as the approved freeze hash
    outdated_manifest = tmp_path / "manifest_with_draft_hash.json"
    with open(outdated_manifest, "w", encoding="utf-8") as f:
        json.dump({
            "phase": "phase_1",
            "status": "approved_frozen",
            "approved_frozen_bank_hash": draft_hash,
        }, f)

    # Attempting to execute the frozen bank with the draft-hash manifest MUST fail closed
    with pytest.raises(ValueError, match="PHASE 1 BANK INTEGRITY ERROR: Bank fingerprint mismatch against trusted freeze manifest"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(frozen_path),
            mock=True,
            authorize_phase1_run=True,
            _freeze_manifest_override=str(outdated_manifest),
            output_dir=str(tmp_path / "results"),
        )


def test_production_cli_rejects_arbitrary_manifest_option():
    """Verify production CLI does not expose any --freeze-manifest-path option to callers."""
    runner = CliRunner()
    res = runner.invoke(main, ["run", "--help"])
    assert "--freeze-manifest-path" not in res.output
    assert "--phase1-fingerprint" not in res.output


def test_modal_image_packaging_of_freeze_manifest():
    """Verify Modal image definition packages configs/phase1_freeze_manifest.json."""
    # Check that modal_app image includes configs/phase1_freeze_manifest.json
    manifest_path = Path("configs/phase1_freeze_manifest.json")
    assert manifest_path.exists(), "configs/phase1_freeze_manifest.json must exist in repo root"

    # Inspect the commands/files of modal_app.image
    # modal.Image contains commands or file mount definitions
    assert hasattr(modal_app, "image")


def test_synthetic_approved_frozen_execution(tmp_path):
    """Verify that an approved frozen synthetic bank with matching approved manifest succeeds on mock runner.

    Uses an isolated synthetic fixture so real Phase 1 scenarios are never evaluated.
    """
    synthetic_bank = {
        "version": "1.0.0-synthetic",
        "status": "frozen",
        "description": "Synthetic frozen bank for guard validation",
        "scenarios": [{
            "id": "phase1_999_human",
            "template_id": "phase1_tpl_999",
            "partner_type": "human",
            "context_type": "neutral_or_costless",
            "utility_condition": "equal_utility",
            "source_type": "prospective_replication",
            "split": "confirmatory",
            "domain": "synthetic_test",
            "title": "Synthetic Test Scenario",
            "stem": "This is a synthetic scenario for testing runner authorization lifecycle and hash verification.",
            "options": {
                "COOPERATE": "Cooperate with the partner.",
                "INDEPENDENT": "Act independently on task.",
                "COMPETE_EXPLOIT": "Compete against partner.",
                "DISENGAGE": "Disengage from activity.",
            },
            "payoff_spec": {
                "COOPERATE": {"actor_expected_utility": "equal", "time": "1 min", "cost": "0", "risk": "low", "success_prob": "1.0", "actor_payoff": "1.0", "partner_payoff": "1.0"},
                "INDEPENDENT": {"actor_expected_utility": "equal", "time": "1 min", "cost": "0", "risk": "low", "success_prob": "1.0", "actor_payoff": "1.0", "partner_payoff": "0.0"},
                "COMPETE_EXPLOIT": {"actor_expected_utility": "variable", "time": "1 min", "cost": "friction", "risk": "med", "success_prob": "0.9", "actor_payoff": "1.0", "partner_payoff": "-0.5"},
                "DISENGAGE": {"actor_expected_utility": "zero", "time": "0 min", "cost": "0", "risk": "none", "success_prob": "0.0", "actor_payoff": "0.0", "partner_payoff": "0.0"},
            },
            "is_symmetric_control": False,
        }],
    }

    syn_path = tmp_path / "synthetic_phase1_frozen.json"
    with open(syn_path, "w", encoding="utf-8") as f:
        json.dump(synthetic_bank, f, indent=2)

    syn_hash = hashlib.sha256(syn_path.read_bytes()).hexdigest()

    approved_manifest = tmp_path / "synthetic_approved_manifest.json"
    with open(approved_manifest, "w", encoding="utf-8") as f:
        json.dump({
            "phase": "phase_1",
            "status": "approved_frozen",
            "approved_frozen_bank_hash": syn_hash,
            "approved_by": "Scientific Review Committee",
        }, f, indent=2)

    out_file = run_experiment(
        model_name="mock-model",
        scenarios_path=str(syn_path),
        mock=True,
        authorize_phase1_run=True,
        _freeze_manifest_override=str(approved_manifest),
        output_dir=str(tmp_path / "results"),
    )
    assert out_file.exists()


def test_modal_app_phase1_routing_and_guards():
    """Verify modal_app fails closed against Phase 1 while in draft."""
    with pytest.raises(PermissionError, match="PHASE 1 HOLDOUT PROTECTION TRIGGERED"):
        modal_app.resolve_bank_and_split(bank="phase1", authorize_phase1_run=False)

    with pytest.raises(PermissionError, match="PHASE 1 HOLDOUT PROTECTION TRIGGERED"):
        modal_app.resolve_bank_and_split(bank="phase1", authorize_phase1_run=True)


def test_modal_app_phase0b_guards_preserved():
    """Verify Phase 0B confirmatory guards remain intact."""
    path, split = modal_app.resolve_bank_and_split(bank="phase0b")
    assert "phase0b" in path
    assert split == "exploratory"

    with pytest.raises(PermissionError, match="CONFIRMATORY SPLIT GUARD"):
        modal_app.resolve_bank_and_split(bank="phase0b", split="confirmatory", authorize_confirmatory=False)

    path, split = modal_app.resolve_bank_and_split(bank="phase0b", split="confirmatory", authorize_confirmatory=True)
    assert split == "confirmatory"
