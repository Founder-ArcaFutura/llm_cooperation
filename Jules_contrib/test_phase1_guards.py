"""Tests for Phase 1 holdout protection and fail-closed inference guards."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from llm_cooperation.cli import main
from llm_cooperation.harness.runner import run_experiment
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
    """Verify direct invocation of run_experiment fails closed on Phase 1 bank."""
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
