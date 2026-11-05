"""Modal remote execution app for contrastive representation-mapping experiment.

Enforces fail-closed authorization check (--authorize-paid-run) and exact model revision.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Dict

import modal

from llm_cooperation.mechanistic.contrastive_mapping import DEFAULT_MODEL_ID, DEFAULT_REVISION

volume = modal.Volume.from_name("llm-coop-mechanistic", create_if_missing=True)
cache = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", "transformers==4.46.3", "accelerate==1.1.1", "numpy==1.26.4")
    .add_local_python_source("llm_cooperation")
)
app = modal.App("llm-cooperation-contrastive-mapping-v1", image=image)


@app.function(
    gpu="A10G",
    timeout=14400,
    retries=0,
    volumes={"/runs": volume, "/hf-cache": cache},
)
def run_remote_inference(
    model: str,
    revision: str,
    run_id: str,
    plan_files: Dict[str, str],
) -> str:
    os.environ["HF_HOME"] = "/hf-cache"
    from llm_cooperation.mechanistic.contrastive_mapping import run_inference, analyze_contrastive_mapping

    plan_dir = Path("/tmp") / f"{run_id}-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    for name, content in plan_files.items():
        (plan_dir / name).write_text(content, encoding="utf-8")

    out_run_dir = Path("/runs") / run_id
    out_analysis_dir = out_run_dir / "analysis"

    try:
        run_inference(
            plan_dir=plan_dir,
            output_dir=out_run_dir,
            model_id=model,
            revision=revision,
            authorize=True,
            mock=False,
            device="cuda",
        )
        analyze_contrastive_mapping(
            run_dir=out_run_dir,
            prompts_path=plan_dir / "prompts.jsonl",
            output_dir=out_analysis_dir,
        )
    finally:
        volume.commit()

    return str(out_run_dir)


@app.local_entrypoint()
def main(
    plan: str,
    revision: str = DEFAULT_REVISION,
    model: str = DEFAULT_MODEL_ID,
    authorize_paid_run: bool = False,
):
    if not authorize_paid_run:
        raise ValueError(
            "PAID RUN GUARD: Execution requires explicit authorization via --authorize-paid-run. "
            "Real-model inference and paid GPU resources must never be launched without confirmation."
        )

    if model != DEFAULT_MODEL_ID:
        raise ValueError(f"Contrastive mapping experiment strictly targets {DEFAULT_MODEL_ID}, got {model}")

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"Supply immutable 40-character revision SHA, got {revision}")

    plan_path = Path(plan)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan directory not found: {plan}")

    plan_files = {
        "manifest.json": (plan_path / "manifest.json").read_text(encoding="utf-8"),
        "prompts.jsonl": (plan_path / "prompts.jsonl").read_text(encoding="utf-8"),
    }

    run_id = f"contrastive-mapping-{uuid.uuid4().hex}"
    print(f"Submitting contrastive mapping run {run_id} to Modal...")
    print(f"Model: {model} (rev: {revision}) on A10G GPU.")
    out_path = run_remote_inference.remote(model, revision, run_id, plan_files)
    print(f"Completed run stored at {out_path}")
