"""Tests for Phase 1 holdout protection and fail-closed inference guards.

Tests cover:
- Draft rejection (draft_pending_review)
- Authorization rejection (without --authorize-phase1-run)
- Tampered hash / fingerprint mismatch
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
from llm_cooperation.harness.runner import run_experiment, APPROVED_PHASE1_FREEZE_HASH
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


def test_synthetic_frozen_phase1_lifecycle(tmp_path):
    """Verify approved frozen execution, authorization rejection, and tampered hash on synthetic fixture.

    Uses a synthetic toy fixture with phase1_ template IDs to verify runner logic without
    evaluating real Phase 1 scenarios.
    """
    synthetic_scenario = {
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
    }

    synthetic_bank = {
        "version": "1.0.0-synthetic",
        "status": "frozen",
        "description": "Synthetic frozen bank for guard validation",
        "scenarios": [synthetic_scenario],
    }

    syn_path = tmp_path / "synthetic_phase1_frozen.json"
    with open(syn_path, "w", encoding="utf-8") as f:
        json.dump(synthetic_bank, f, indent=2)

    # Compute hash of synthetic file
    syn_hash = hashlib.sha256(syn_path.read_bytes()).hexdigest()

    # 1. Without authorization: must fail with authorization guard
    with pytest.raises(PermissionError, match="PHASE 1 INFERENCE AUTHORIZATION GUARD"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(syn_path),
            mock=True,
            authorize_phase1_run=False,
            expected_phase1_bank_hash=syn_hash,
            output_dir=str(tmp_path / "results"),
        )

    # 2. With authorization but tampered hash: must fail with hash mismatch
    with pytest.raises(ValueError, match="PHASE 1 BANK INTEGRITY ERROR: Bank fingerprint mismatch"):
        run_experiment(
            model_name="mock-model",
            scenarios_path=str(syn_path),
            mock=True,
            authorize_phase1_run=True,
            expected_phase1_bank_hash="0000000000000000000000000000000000000000000000000000000000000000",
            output_dir=str(tmp_path / "results"),
        )

    # 3. With authorization and matching expected hash on mock runner: successfully executes synthetic fixture
    out_file = run_experiment(
        model_name="mock-model",
        scenarios_path=str(syn_path),
        mock=True,
        authorize_phase1_run=True,
        expected_phase1_bank_hash=syn_hash,
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
    # Exploratory defaults
    path, split = modal_app.resolve_bank_and_split(bank="phase0b")
    assert "phase0b" in path
    assert split == "exploratory"

    # Confirmatory requires auth
    with pytest.raises(PermissionError, match="CONFIRMATORY SPLIT GUARD"):
        modal_app.resolve_bank_and_split(bank="phase0b", split="confirmatory", authorize_confirmatory=False)

    # With auth passes
    path, split = modal_app.resolve_bank_and_split(bank="phase0b", split="confirmatory", authorize_confirmatory=True)
    assert split == "confirmatory"
