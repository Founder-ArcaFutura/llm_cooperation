"""Modal remote execution script for EleutherAI Pythia pretraining emergence assay.

Evaluates the frozen Phase A dose-response instrument and calibration bank across
the pinned intermediate Pythia checkpoints (step0 through step143000).

Enforces fail-closed compute protection:
Requires --authorize-paid-run True to launch real GPU inference.
Without authorization, prints configuration plan and exits cleanly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import modal

APP_NAME = "llm-cooperation-pythia-emergence-v1"
VOLUME_NAME = "llm-coop-pythia-emergence"

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
hf_cache = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "transformers==4.53.2",
        "accelerate==1.1.1",
        "numpy==1.26.4",
        "scipy==1.14.1",
        "scikit-learn==1.5.2",
        "pandas==2.2.3",
        "pydantic==2.9.2",
    )
    .add_local_python_source("llm_cooperation")
)

app = modal.App(APP_NAME, image=image)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@app.function(
    gpu="A10G",
    timeout=7200,
    volumes={"/runs": volume, "/hf-cache": hf_cache},
)
def evaluate_pythia_checkpoint_remote(
    model_id: str,
    revision: str,
    step: int,
    bank_bytes: bytes,
    bank_sha256: str,
    calibration_bytes: bytes,
    calibration_sha256: str,
    mock: bool = False,
) -> Dict:
    """Run dose-response evaluation and calibration on a single Pythia checkpoint."""
    os.environ["HF_HOME"] = "/hf-cache"
    from llm_cooperation.harness.runner import run_experiment, run_calibration
    from llm_cooperation.analysis.metrics import load_run_results, aggregate_by_scenario
    from llm_cooperation.analysis.dose_response import analyze_payoff_dose_response

    out_dir = Path("/runs") / f"{model_id.replace('/', '_')}_{revision}"
    out_dir.mkdir(parents=True, exist_ok=True)
    if hashlib.sha256(bank_bytes).hexdigest() != bank_sha256:
        raise ValueError("Dose-response bank SHA-256 mismatch")
    if hashlib.sha256(calibration_bytes).hexdigest() != calibration_sha256:
        raise ValueError("Calibration bank SHA-256 mismatch")

    bank_path = out_dir / "dose_response_bank.json"
    bank_path.write_bytes(bank_bytes)
    calibration_path = out_dir / "calibration_bank.json"
    calibration_path.write_bytes(calibration_bytes)
    calibration_file, calibration = run_calibration(
        model_name=model_id,
        calibration_path=str(calibration_path),
        output_dir=str(out_dir),
        revision=revision,
        precision="bfloat16",
        device="cuda" if not mock else "cpu",
        mock=mock,
        seed=42,
    )

    raw_file = run_experiment(
        model_name=model_id,
        scenarios_path=str(bank_path),
        output_dir=str(out_dir),
        mock=mock,
        revision=revision,
        precision="bfloat16",
        device="cuda" if not mock else "cpu",
        seed=42,
    )

    metadata, records = load_run_results(str(raw_file), validate=False)
    agg_df = aggregate_by_scenario(records)
    analysis = analyze_payoff_dose_response(agg_df, n_bootstraps=500, seed=42)

    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps({"dose_response": analysis, "calibration": calibration, "calibration_file": str(calibration_file)}, indent=2), encoding="utf-8")
    report_file = out_dir / "dose_response_report.md"
    report_file.write_text(
        "# Payoff dose-response pilot\n\n"
        f"- Model: `{model_id}`\n- Revision: `{revision}`\n- Step: `{step}`\n"
        f"- Calibration status: `{calibration['status']}`\n"
        f"- Equal-utility choice difference: {analysis['equal_utility_baseline']['choice_diff_mean']:.4f}\n"
        f"- Crossover delta U: {analysis['payoff_sensitivity']['crossover_threshold_delta_u']}\n",
        encoding="utf-8",
    )
    volume.commit()

    return {
        "model_id": model_id,
        "revision": revision,
        "step": step,
        "equal_utility_log_prob_diff": analysis["equal_utility_baseline"]["log_prob_diff_mean"],
        "equal_utility_choice_diff": analysis["equal_utility_baseline"]["choice_diff_mean"],
        "payoff_sensitivity_slope": analysis["payoff_sensitivity"]["choice_slope"],
        "crossover_threshold": analysis["payoff_sensitivity"]["crossover_threshold_delta_u"],
        "calibration_status": calibration["status"],
        "output_dir": str(out_dir),
    }


@app.local_entrypoint()
def main(
    model: str = "EleutherAI/pythia-1.4b",
    checkpoint_step: int = 143000,
    mock: bool = True,
    authorize_paid_run: bool = False,
):
    """Entrypoint for Pythia emergence evaluation."""
    from llm_cooperation.harness.emergence import PYTHIA_1_4B_CHECKPOINTS

    if not mock and not authorize_paid_run:
        print("ERROR: Real GPU inference requires explicit --authorize-paid-run True guard.", file=sys.stderr)
        print("Executing in preflight plan validation mode only.", file=sys.stderr)
        return

    bank_path = Path("data/scenarios_dose_response_exploratory.json")
    if not bank_path.exists():
        raise FileNotFoundError(f"Missing scenario bank at {bank_path}")

    bank_bytes = bank_path.read_bytes()
    bank_hash = sha256_file(bank_path)
    calibration_path = Path("data/calibration_bank.json")
    if not calibration_path.exists():
        raise FileNotFoundError(f"Missing calibration bank at {calibration_path}")
    calibration_bytes = calibration_path.read_bytes()
    calibration_hash = sha256_file(calibration_path)

    model_checkpoints = [c for c in PYTHIA_1_4B_CHECKPOINTS if c.model_id == model]
    if not model_checkpoints:
        raise ValueError(f"Model {model!r} is not in the configured Pythia checkpoint schedule")
    checkpoints_to_run = model_checkpoints
    if checkpoint_step != -1:
        checkpoints_to_run = [c for c in model_checkpoints if c.step == checkpoint_step]
        if not checkpoints_to_run:
            raise ValueError(f"Checkpoint step {checkpoint_step} not in {[c.step for c in model_checkpoints]}")

    print(f"Launching Pythia emergence sweep: {len(checkpoints_to_run)} checkpoint(s), mock={mock}")
    for ckpt in checkpoints_to_run:
        print(f"Evaluating {ckpt.model_id} @ {ckpt.revision} (step {ckpt.step})...")
        if not mock and authorize_paid_run:
            res = evaluate_pythia_checkpoint_remote.remote(
                model_id=ckpt.model_id,
                revision=ckpt.revision,
                step=ckpt.step,
                bank_bytes=bank_bytes,
                bank_sha256=bank_hash,
                calibration_bytes=calibration_bytes,
                calibration_sha256=calibration_hash,
                mock=False,
            )
            print("Checkpoint output:", res)
        else:
            print("Mock dry-run: preflight verified without remote GPU invocation.")
