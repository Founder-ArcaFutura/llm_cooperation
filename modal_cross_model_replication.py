"""Bounded Modal staging and explicitly authorized cross-model smoke captures.

No full capture follows a smoke automatically. Run `stage` first, then authorize
one four-prompt smoke at a time with both flags on that model invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import time
from datetime import datetime, timezone

import modal


ROOT = Path(__file__).resolve().parent
PLAN_DIR = ROOT / "research" / "cross_model_ready_v1"
VOLUME_NAME = "llm-cooperation-cross-model-v1"
VOLUME_ROOT = "/cross_model_four_strategy_v1"
PLAN_ROOT = f"{VOLUME_ROOT}/plan"
ARTIFACT_ROOT = f"{VOLUME_ROOT}/artifacts"
GPU_RATE_USD_PER_SECOND = 0.000694  # Modal A100 80 GB list-price snapshot, 2026-11-06.
MODEL_KEYS = ("olmo7b", "mistral7b")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_bytes(value: bytes) -> dict:
    return json.loads(value.decode("utf-8"))


def plan_payload(plan_dir: Path = PLAN_DIR) -> dict[str, bytes]:
    """Read and locally validate the complete frozen plan before staging."""
    manifest_bytes = (plan_dir / "manifest.json").read_bytes()
    manifest = _read_json_bytes(manifest_bytes)
    if manifest.get("status") != "PREFLIGHT_ONLY_NO_INFERENCE":
        raise ValueError("Expected the frozen preflight-only cross-model plan")
    if set(manifest.get("models", {})) != {"olmo7b", "mistral7b", "qwen"}:
        raise ValueError("Plan model inventory changed")
    for key in MODEL_KEYS:
        model = manifest["models"][key]
        if len(model.get("revision", "")) != 40 or model.get("status") != "TOKENIZER_PREFLIGHT_PASSED_WEIGHTS_UNTESTED":
            raise ValueError(f"Plan is not ready for {key} capture")
    payload = {p.name: p.read_bytes() for p in sorted(plan_dir.iterdir()) if p.is_file()}
    expected = manifest.get("files", {})
    if set(payload) != set(expected) | {"manifest.json"}:
        raise ValueError("Plan file inventory differs from its manifest")
    for name, digest in expected.items():
        if _sha_bytes(payload[name]) != digest:
            raise ValueError(f"Frozen plan hash mismatch: {name}")
    return payload


def _verify_payload(payload: dict[str, bytes]) -> dict:
    if "manifest.json" not in payload:
        raise ValueError("Plan payload has no manifest")
    manifest = _read_json_bytes(payload["manifest.json"])
    expected = manifest.get("files", {})
    if set(payload) != set(expected) | {"manifest.json"} or any(
        _sha_bytes(payload[name]) != digest for name, digest in expected.items()
    ):
        raise ValueError("Staged payload is incomplete or has changed bytes")
    return manifest


def runtime_payload(root: Path = ROOT) -> dict[str, bytes]:
    """Capture only immutable source files needed by the existing loader."""
    paths = (
        "data/scenarios_phase0b_utility_matched.json",
        "research/contrastive_full_v1/prompts.jsonl",
        "research/contrastive_full_v1/manifest.json",
    )
    payload = {name: (root / name).read_bytes() for name in paths}
    manifest = _read_json_bytes((PLAN_DIR / "manifest.json").read_bytes())
    if _sha_bytes(payload["data/scenarios_phase0b_utility_matched.json"]) != manifest["integrity"]["bank_sha256"]:
        raise ValueError("Frozen stimulus bank does not match plan fingerprint")
    if _sha_bytes(payload["research/contrastive_full_v1/prompts.jsonl"]) != manifest["integrity"]["inventory_bytes_sha256"]:
        raise ValueError("Frozen prompt inventory does not match plan fingerprint")
    return payload


def require_smoke_authorization(inference: bool, paid: bool) -> None:
    if not (inference and paid):
        raise PermissionError("Both smoke-specific inference and paid-run authorization are required")


def require_full_capture_authorization(inference: bool, paid: bool, full: bool) -> None:
    require_smoke_authorization(inference, paid)
    if not full:
        raise PermissionError("Full capture requires its separate full-capture authorization")


def _tokenizer_identity(tokenizer) -> dict:
    vocab = tokenizer.get_vocab()
    canonical = json.dumps(vocab, sort_keys=True, separators=(",", ":")).encode("utf8")
    special = {
        key: ([str(item) for item in value] if isinstance(value, (tuple, list)) else str(value))
        for key, value in tokenizer.special_tokens_map.items()
    }
    return {
        "class": type(tokenizer).__name__,
        "name_or_path": str(getattr(tokenizer, "name_or_path", "")),
        "vocab_size": len(vocab),
        "vocab_sha256": _sha_bytes(canonical),
        "special_tokens_map": special,
        "commit_hash": getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
    }


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf8")


app = modal.App("llm-cooperation-cross-model-v1")
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=False)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "numpy==2.3.1",
        "scipy==1.16.0",
        "scikit-learn==1.7.0",
        "transformers==5.5.4",
        "torch==2.10.0",
        "tokenizers==0.22.1",
        "huggingface-hub==1.33.0",
        "accelerate>=1.0",
    )
    .add_local_python_source("llm_cooperation")
)


@app.function(image=modal.Image.debian_slim(python_version="3.12"), volumes={"/mnt/cross_model": volume}, timeout=900)
def stage_plan(payload: dict[str, bytes], runtime: dict[str, bytes]) -> dict:
    """Persist the original plan bytes to the named volume after hash checks."""
    manifest = _verify_payload(payload)
    if (
        _sha_bytes(runtime.get("data/scenarios_phase0b_utility_matched.json", b""))
        != manifest["integrity"]["bank_sha256"]
        or _sha_bytes(runtime.get("research/contrastive_full_v1/prompts.jsonl", b""))
        != manifest["integrity"]["inventory_bytes_sha256"]
    ):
        raise ValueError("Runtime source hashes do not match the frozen plan")
    if set(runtime) != {
        "data/scenarios_phase0b_utility_matched.json",
        "research/contrastive_full_v1/prompts.jsonl",
        "research/contrastive_full_v1/manifest.json",
    }:
        raise ValueError("Runtime source inventory differs")
    root = Path("/mnt/cross_model") / "cross_model_four_strategy_v1"
    plan_root = root / "plan"
    runtime_root = root / "runtime"
    if plan_root.exists() or runtime_root.exists():
        existing = {p.name: p.read_bytes() for p in plan_root.iterdir() if p.is_file()}
        if existing != payload:
            raise FileExistsError("A different frozen plan is already staged; refusing overwrite")
        _verify_payload(existing)
        existing_runtime = {
            str(p.relative_to(runtime_root)).replace("\\", "/"): p.read_bytes()
            for p in runtime_root.rglob("*") if p.is_file()
        } if runtime_root.exists() else {}
        if existing_runtime != runtime:
            raise FileExistsError("A different source context is already staged; refusing overwrite")
        return {"status": "already_staged_verified", "files": len(existing), "manifest_sha256": _sha_bytes(payload["manifest.json"])}
    root.mkdir(parents=True)
    for name, content in payload.items():
        (plan_root / name).parent.mkdir(parents=True, exist_ok=True)
        (plan_root / name).write_bytes(content)
    for name, content in runtime.items():
        target = runtime_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    written = {p.name: p.read_bytes() for p in plan_root.iterdir() if p.is_file()}
    _verify_payload(written)
    written_runtime = {
        str(p.relative_to(runtime_root)).replace("\\", "/"): p.read_bytes()
        for p in runtime_root.rglob("*") if p.is_file()
    }
    if written_runtime != runtime:
        raise ValueError("Runtime source bytes changed while staging")
    volume.commit()
    return {"status": "staged_verified", "plan_files": len(written), "runtime_files": len(written_runtime), "manifest_sha256": _sha_bytes(payload["manifest.json"]), "plan_status": manifest["status"]}


@app.function(image=image, gpu="A100-80GB", volumes={"/mnt/cross_model": volume}, timeout=21600, memory=65536, cpu=8)
def capture_run(
    model_key: str,
    capture_kind: str,
    authorize_inference: bool,
    authorize_paid_run: bool,
    authorize_full_capture: bool,
    run_tag: str,
    gpu_rate_usd_per_second: float = GPU_RATE_USD_PER_SECOND,
) -> dict:
    """Run a smoke or separately authorized full capture with a fixed upper bound."""
    if capture_kind == "full":
        require_full_capture_authorization(authorize_inference, authorize_paid_run, authorize_full_capture)
    else:
        require_smoke_authorization(authorize_inference, authorize_paid_run)
    if model_key not in MODEL_KEYS:
        raise ValueError("Choose olmo7b or mistral7b")
    if capture_kind not in ("smoke", "full"):
        raise ValueError("capture_kind must be smoke or full")
    if capture_kind == "full" and not authorize_full_capture:
        raise PermissionError("Full capture requires separate full-capture authorization")
    if not run_tag or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_tag):
        raise ValueError("run_tag may contain only letters, numbers, hyphen and underscore")
    if not math.isfinite(gpu_rate_usd_per_second) or gpu_rate_usd_per_second <= 0:
        raise ValueError("GPU rate must be a positive finite USD/second value")

    import torch
    from transformers import AutoTokenizer

    mounted = Path("/mnt/cross_model") / "cross_model_four_strategy_v1"
    plan = mounted / "plan"
    manifest = json.loads((plan / "manifest.json").read_text(encoding="utf8"))
    plan_bytes = {p.name: p.read_bytes() for p in plan.iterdir() if p.is_file()}
    _verify_payload(plan_bytes)
    state = manifest["models"][model_key]
    if state.get("status") != "TOKENIZER_PREFLIGHT_PASSED_WEIGHTS_UNTESTED":
        raise ValueError("Selected model did not pass frozen tokenizer preflight")
    artifact = mounted / "artifacts" / f"{model_key}_{capture_kind}_{run_tag}"
    if artifact.exists():
        raise FileExistsError(f"Capture artifact exists: {artifact}")

    # Supply the exact source/bank context needed by the existing verified loader.
    with tempfile.TemporaryDirectory(prefix="cross-model-smoke-") as tmp:
        work = Path(tmp)
        for rel in ("data/scenarios_phase0b_utility_matched.json", "research/contrastive_full_v1/prompts.jsonl", "research/contrastive_full_v1/manifest.json"):
            source = mounted / "runtime" / rel
            target = work / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (work / "research").mkdir(exist_ok=True)
        (work / "research" / "cross_model_ready_v1").symlink_to(plan, target_is_directory=True)
        loaded_at = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(state["model_id"], revision=state["revision"], trust_remote_code=False)
        tokenizer_identity = _tokenizer_identity(tokenizer)
        from llm_cooperation.mechanistic import cross_model_replication as core
        from transformers import AutoModelForCausalLM

        # Observe the object returned by the existing loader without modifying its
        # hash-pinned source or changing capture settings.
        previous_descriptor = AutoModelForCausalLM.__dict__.get("from_pretrained")
        original_loader = AutoModelForCausalLM.from_pretrained
        loaded_revision = {}

        def observed_loader(cls, *args, **kwargs):
            model = original_loader(*args, **kwargs)
            loaded_revision["value"] = getattr(model.config, "_commit_hash", None)
            return model

        AutoModelForCausalLM.from_pretrained = classmethod(observed_loader)
        original_cwd = Path.cwd()
        os.chdir(work)
        try:
            torch.cuda.reset_peak_memory_stats()
            core.capture(
                "research/cross_model_ready_v1",
                model_key,
                artifact,
                authorize_inference=True,
                authorize_paid_run=True,
                smoke=(capture_kind == "smoke"),
            )
        finally:
            os.chdir(original_cwd)
            if previous_descriptor is None:
                delattr(AutoModelForCausalLM, "from_pretrained")
            else:
                setattr(AutoModelForCausalLM, "from_pretrained", previous_descriptor)
        elapsed = time.perf_counter() - loaded_at
        run_manifest_path = artifact / "manifest.json"
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf8"))
        seconds = run_manifest.get("seconds_per_prompt", [])
        expected_count = 4 if capture_kind == "smoke" else 496
        if len(seconds) != expected_count:
            raise ValueError(f"Capture produced {len(seconds)} prompt timings, expected {expected_count}")
        peak = {
            "allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "reserved_bytes": int(torch.cuda.max_memory_reserved()),
            "device_name": torch.cuda.get_device_name(),
            "device_total_bytes": int(torch.cuda.get_device_properties(0).total_memory),
        }
        actual_revision = loaded_revision.get("value")
        if actual_revision != state["revision"]:
            raise ValueError("Loaded model revision differs from immutable plan pin")
        inference_seconds = sum(seconds)
        load_and_setup_seconds = max(0.0, elapsed - inference_seconds)
        estimated_full_gpu_seconds = (
            load_and_setup_seconds + (496.0 / 4.0) * inference_seconds
            if capture_kind == "smoke" else elapsed
        )
        metadata = {
            "schema_version": "cross-model-modal-capture-v1",
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "capture_kind": capture_kind,
            "model_key": model_key,
            "model_id": state["model_id"],
            "planned_revision": state["revision"],
            "actual_model_revision": actual_revision,
            "tokenizer_identity": tokenizer_identity,
            "hook_validity": {"valid": True, "captured_prompts": len(seconds), "expected_depths": 8, "finite_vectors_verified_by_capture": True, "hook_removal_verified_by_core": True},
            "elapsed_seconds_including_tokenizer_and_model_load": elapsed,
            "seconds_per_prompt": seconds,
            "peak_gpu_memory": peak,
            "full_run_estimate": ({
                "prompts": 496,
                "gpu_seconds": estimated_full_gpu_seconds,
                "a100_80gb_list_price_usd_per_second": gpu_rate_usd_per_second,
                "gpu_compute_usd": estimated_full_gpu_seconds * gpu_rate_usd_per_second,
                "excludes": ["CPU and RAM metering", "startup variance", "cache/network/storage charges"],
                "method": "observed load/setup time plus 124 times the four-prompt smoke forward time; GPU compute only",
            } if capture_kind == "smoke" else None),
            "observed_gpu_compute_usd_estimate": elapsed * gpu_rate_usd_per_second,
            "automatic_full_capture": False,
            "plan_manifest_sha256": _sha_bytes(plan_bytes["manifest.json"]),
            "original_plan_file_hashes": manifest["files"],
        }
        metadata_path = artifact / "modal_capture_metadata.json"
        _write_json(metadata_path, metadata)
        run_manifest["modal_capture_metadata_sha256"] = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
        _write_json(run_manifest_path, run_manifest)
    volume.commit()
    return {"status": f"{capture_kind}_completed", "artifact_path": str(artifact), "metadata": metadata}


@app.local_entrypoint()
def main(
    action: str = "stage",
    model_key: str = "",
    authorize_inference: bool = False,
    authorize_paid_run: bool = False,
    authorize_full_capture: bool = False,
    run_tag: str = "",
    gpu_rate_usd_per_second: float = GPU_RATE_USD_PER_SECOND,
):
    """CLI entry point; authorization is checked before any GPU function call."""
    if action == "stage":
        payload = plan_payload()
        result = stage_plan.remote(payload, runtime_payload())
        print(json.dumps(result, indent=2))
    elif action == "smoke":
        require_smoke_authorization(authorize_inference, authorize_paid_run)
        if model_key not in MODEL_KEYS:
            raise ValueError("--model-key must be olmo7b or mistral7b")
        if not run_tag:
            raise ValueError("--run-tag is required to keep smoke artifact paths unique")
        result = capture_run.remote(model_key, "smoke", True, True, False, run_tag, gpu_rate_usd_per_second)
        print(json.dumps(result, indent=2))
    elif action == "full":
        require_full_capture_authorization(authorize_inference, authorize_paid_run, authorize_full_capture)
        if model_key not in MODEL_KEYS or not run_tag:
            raise ValueError("--model-key and a unique --run-tag are required")
        result = capture_run.remote(model_key, "full", True, True, True, run_tag, gpu_rate_usd_per_second)
        print(json.dumps(result, indent=2))
    else:
        raise ValueError("action must be stage, smoke, or separately authorized full")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("stage", "smoke", "full"))
    # Modal CLI normally invokes the local entrypoint; argparse here offers a safe local plan check.
    parser.parse_args()
    print(json.dumps({"local_plan_files": len(plan_payload()), "local_only": True}, indent=2))
