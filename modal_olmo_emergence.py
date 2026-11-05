"""Paid, explicit-authorization Modal runner for the five-checkpoint OLMo study."""
from __future__ import annotations

import json
import os
from pathlib import Path

import modal

volume = modal.Volume.from_name("llm-coop-olmo-emergence", create_if_missing=True)
cache = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("torch==2.5.1", "transformers==4.53.2", "accelerate==1.1.1", "numpy==1.26.4",
                      "scikit-learn==1.5.2", "scipy==1.14.1", "matplotlib==3.9.2", "pandas==2.2.3",
                      "seaborn==0.13.2", "pydantic==2.9.2", "rich==13.9.4", "tabulate==0.9.0")
         .add_local_python_source("llm_cooperation"))
app = modal.App("llm-cooperation-olmo-emergence-v1", image=image)


@app.function(gpu="A10G", timeout=86400, retries=0, volumes={"/runs": volume, "/hf-cache": cache})
def run_checkpoint(model_id: str, revision: str, order: int, plan_files: dict[str, bytes],
                   run_behavior: bool = False, authorize_behavioral_confirmatory: bool = False,
                   technical_smoke: bool = False) -> str:
    os.environ["HF_HOME"] = "/hf-cache"
    from llm_cooperation.mechanistic.contrastive_mapping import run_inference
    from llm_cooperation.mechanistic.four_strategy_probe import analyze_four_strategy
    from llm_cooperation.mechanistic.contrastive_mapping import sha256_file
    plan = Path("/tmp") / f"olmo-emergence-plan-{order}"
    plan.mkdir(parents=True, exist_ok=False)
    for name, content in plan_files.items():
        if not isinstance(content, bytes):
            raise ValueError(f"Plan transport for {name} must be bytes")
        (plan / name).write_bytes(content)
    manifest = json.loads((plan / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("target_model") != model_id or manifest.get("target_revision") != revision:
        raise ValueError("Checkpoint plan identity does not match requested model revision")
    checkpoint_file = plan / "checkpoint.json"
    if not checkpoint_file.is_file():
        raise FileNotFoundError("Checkpoint provenance record missing from plan")
    checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
    if checkpoint.get("model_id") != model_id or checkpoint.get("commit_sha") != revision or checkpoint.get("checkpoint_order") != order:
        raise ValueError("Checkpoint provenance does not match requested model revision/order")
    if manifest.get("prompts_sha256") != sha256_file(plan / "prompts.jsonl"):
        raise ValueError("Checkpoint plan prompt hash mismatch")
    bank_path = plan / "scenarios_phase0b_utility_matched.json"
    if bank_path.exists() and sha256_file(bank_path) != manifest.get("bank_sha256"):
        raise ValueError("Transported frozen scenario bank hash mismatch")
    output_prefix = "olmo2-1b-emergence-smoke" if technical_smoke else "olmo2-1b-emergence"
    run = Path("/runs") / output_prefix / f"checkpoint-{order:02d}-{revision[:12]}"
    analysis = run / "analysis"
    try:
        run_inference(plan, run, model_id=model_id, revision=revision, authorize=True, device="cuda")
        (run / "checkpoint.json").write_bytes(checkpoint_file.read_bytes())
        run_manifest_path = run / "manifest.json"
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        run_manifest["checkpoint_provenance"] = checkpoint
        run_manifest["checkpoint_provenance_sha256"] = sha256_file(run / "checkpoint.json")
        run_manifest_path.write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
        if technical_smoke:
            import numpy as np
            audit = json.loads((run / "tokenization_audit.json").read_text(encoding="utf-8"))
            if run_manifest.get("status") != "completed" or len(audit) != manifest["num_prompts"]:
                raise RuntimeError("Technical smoke failed completion or tokenization audit checks")
            for activation_path in (run / "activations").glob("*.npz"):
                with np.load(activation_path, allow_pickle=False) as saved:
                    residual = saved["residual"]
                if residual.shape != (run_manifest["num_layers"], run_manifest["hidden_size"]) or not np.isfinite(residual).all():
                    raise RuntimeError(f"Activation shape or numerical check failed: {activation_path.name}")
        else:
            analyze_four_strategy(run, run / "prompts.jsonl", analysis, expected_prompts_path=plan / "prompts.jsonl",
                                  expected_manifest_path=plan / "manifest.json", expected_model_id=model_id,
                                  expected_revision=revision, n_boot=1000, permutations=100, progress=True)
        if run_behavior:
            from llm_cooperation.harness.runner import run_experiment
            from llm_cooperation.analysis.pipeline import analyze_results
            if not authorize_behavioral_confirmatory:
                raise ValueError("The full 124-scenario behavioral protocol includes confirmatory scenarios; explicitly enable --authorize-behavioral-confirmatory")
            behavior_root = run / "behavior"
            behavior_root.mkdir(parents=True, exist_ok=False)
            if not bank_path.is_file():
                raise FileNotFoundError("Frozen Phase 0B bank was not transported with the plan")
            raw = run_experiment(model_id, scenarios_path=str(bank_path),
                                 output_dir=str(behavior_root / "raw"), revision=revision,
                                 precision="bfloat16", device="cuda", split_filter=None)
            summary = analyze_results(str(raw), output_dir=str(behavior_root / "analysis"), num_bootstraps=5000)
            (behavior_root / "behavioral_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        volume.commit()
    except Exception:
        volume.commit()
        raise
    return str(run)


@app.local_entrypoint()
def main(plans: str, authorize_paid_run: bool = False, run_behavior: bool = False,
         authorize_behavioral_confirmatory: bool = False, technical_smoke: bool = False):
    if not authorize_paid_run:
        raise ValueError("PAID RUN GUARD: use --authorize-paid-run to explicitly authorize OLMo GPU inference")
    if run_behavior and not authorize_behavioral_confirmatory:
        raise ValueError("Behavior on the full frozen bank includes its confirmatory split; use --authorize-behavioral-confirmatory")
    source = Path(plans)
    if not source.is_dir() or not (source / "selection_and_plans.json").is_file():
        raise FileNotFoundError("Expected plan root with selection_and_plans.json")
    selection = json.loads((source / "selection_and_plans.json").read_text(encoding="utf-8"))
    expected_count = 1 if technical_smoke else 5
    if len(selection.get("plans", [])) != expected_count or bool(selection.get("technical_smoke")) != technical_smoke:
        raise ValueError(f"Expected {expected_count} checkpoint plan(s) matching technical_smoke={technical_smoke}")
    if technical_smoke and run_behavior:
        raise ValueError("Technical smoke is capture-only; behavioral evaluation belongs to the full checkpoint run")
    for row in selection["plans"]:
        plan = Path(row["plan_dir"])
        files = {"manifest.json": (plan / "manifest.json").read_bytes(),
                 "prompts.jsonl": (plan / "prompts.jsonl").read_bytes(),
                 "checkpoint.json": (plan / "checkpoint.json").read_bytes(),
                 "scenarios_phase0b_utility_matched.json": Path(selection["bank_path"]).read_bytes()}
        print(f"Submitting checkpoint {row['checkpoint_order']}: {row['revision']} ({row['commit_sha']})")
        path = run_checkpoint.remote(row["model_id"], row["commit_sha"], row["checkpoint_order"], files,
                                    run_behavior, authorize_behavioral_confirmatory, technical_smoke)
        print(f"Completed checkpoint {row['checkpoint_order']}: {path}")

