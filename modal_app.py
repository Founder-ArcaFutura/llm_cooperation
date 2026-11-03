"""Modal backend execution for LLM Cooperation Phase 0 behavioural screen.

Provides native Modal execution using:
- modal.App
- modal.Image
- modal.Volume
- @app.function
- @app.local_entrypoint

DO NOT launch paid GPU compute during testing/mock runs.
"""

import os
from pathlib import Path
from typing import Optional, List

# Ensure modal configuration resolution does not fail if ~/.modal.toml is unreadable
if "MODAL_CONFIG_PATH" not in os.environ:
    try:
        user_cfg = os.path.expanduser("~/.modal.toml")
        if os.path.exists(user_cfg):
            with open(user_cfg, "r") as _:
                pass
    except Exception:
        os.environ["MODAL_CONFIG_PATH"] = os.path.abspath(".modal.dummy.toml")

import modal

APP_NAME = "llm-cooperation-phase0"

# Modal persistent volumes:
# 1. Cache volume for Hugging Face model weights
# 2. Results volume for durable storage of experiment outputs
hf_cache_volume = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)
results_volume = modal.Volume.from_name("llm-coop-results", create_if_missing=True)

# Container image definition with all dependencies and package installation
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.2.0",
        "transformers>=4.40.0",
        "tokenizers>=0.19.0",
        "accelerate>=0.29.0",
        "pydantic>=2.7.0",
        "pandas>=2.2.0",
        "numpy>=1.26.0",
        "rich>=13.7.0",
        "click>=8.1.0",
        "pyyaml>=6.0.0",
        "tabulate>=0.9.0",
        "matplotlib>=3.8.0",
    )
    .add_local_python_source("llm_cooperation")
    .add_local_file("data/scenarios.json", "/root/data/scenarios.json")
    .add_local_file("configs/models.yaml", "/root/configs/models.yaml")
)

app = modal.App(name=APP_NAME, image=image)

# GPU profiles by model size:
# small (1B - 3B models): A10G (~24GB VRAM)
# medium (7B - 12B models / SFT comparator): L40S (~48GB VRAM)
# large (>12B models): A100-80GB (~80GB VRAM)
GPU_PROFILES = {
    "small": "A10G",       # ~24GB VRAM, ideal for 1B-3B
    "medium": "L40S",      # ~48GB VRAM, ideal for 7B-12B (including 12B Pythia models)
    "large": "A100-80GB",  # 80GB VRAM, high throughput
}


def resolve_model_gpu(model_name: str) -> str:
    """Select appropriate GPU hardware profile based on model manifest or size heuristic.

    Ensures 12B models (e.g. Pythia-12B base or SFT comparator) and 7B models select L40S
    or equivalent hardware profile.
    """
    clean_name = model_name.strip()
    norm = clean_name.lower()

    # 1. Check configs/models.yaml if available
    manifest_path = Path("configs/models.yaml")
    if manifest_path.exists():
        try:
            import yaml
            with open(manifest_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            for section in ["base_models", "optional_models", "post_trained_comparators"]:
                for item in cfg.get(section, {}).values():
                    if isinstance(item, dict):
                        if item.get("name", "").lower() == norm or item.get("hf_id", "").lower() == norm:
                            if item.get("recommended_gpu"):
                                return str(item["recommended_gpu"])
                            size = str(item.get("size", "")).upper()
                            if "12B" in size or "13B" in size or "14B" in size or "7B" in size or "8B" in size:
                                return GPU_PROFILES["medium"]  # L40S
                            mem = item.get("recommended_gpu_mem_gb", 0)
                            if mem >= 32:
                                return GPU_PROFILES["medium"]  # L40S
                            if mem >= 60:
                                return GPU_PROFILES["large"]
                            return GPU_PROFILES["small"]  # A10G
        except Exception:
            pass

    # 2. Heuristics based on model name string
    if any(s in norm for s in ["12b", "13b", "14b", "7b", "8b"]):
        return GPU_PROFILES["medium"]  # L40S
    if any(s in norm for s in ["70b", "34b", "32b"]):
        return GPU_PROFILES["large"]  # A100-80GB

    # Default for 1B-3B base models
    return GPU_PROFILES["small"]  # A10G


def _get_secrets() -> List[modal.Secret]:
    """Safely obtain Hugging Face secret if configured in environment."""
    secrets = []
    if os.environ.get("MODAL_USE_HF_SECRET", "").lower() in ("1", "true", "yes") or "HF_TOKEN" in os.environ or "HUGGING_FACE_HUB_TOKEN" in os.environ:
        try:
            secrets.append(modal.Secret.from_name("huggingface-secret"))
        except Exception:
            pass
    return secrets


def _execute_evaluation(
    model_name: str,
    revision: Optional[str],
    precision: str,
    device: str,
    seed: int,
    prompt_mode: str,
) -> str:
    """Internal helper to execute evaluation inside container and commit volumes."""
    os.environ["HF_HOME"] = "/root/hf_cache"
    from llm_cooperation.harness.runner import run_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    result_file = run_experiment(
        model_name=model_name,
        scenarios_path="/root/data/scenarios.json",
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=False,
        seed=seed,
        prompt_mode=prompt_mode,
    )

    # Durable commit to Modal persistent volume
    results_volume.commit()
    hf_cache_volume.commit()
    return str(result_file)


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/hf_cache": hf_cache_volume, "/root/results": results_volume},
    timeout=3600,
    secrets=_get_secrets(),
)
def run_evaluation_remote(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
) -> str:
    """Execute evaluation on standard A10G GPU (ideal for 1B-3B models)."""
    if mock:
        raise ValueError(
            "run_evaluation_remote provisions paid GPU resources (A10G). "
            "For zero-GPU mock runs, use run_evaluation_mock_remote."
        )
    return _execute_evaluation(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        seed=seed,
        prompt_mode=prompt_mode,
    )


@app.function(
    image=image,
    gpu="L40S",
    volumes={"/root/hf_cache": hf_cache_volume, "/root/results": results_volume},
    timeout=3600,
    secrets=_get_secrets(),
)
def run_evaluation_remote_l40s(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
) -> str:
    """Execute evaluation on high-VRAM L40S GPU (ideal for 7B-12B models, e.g. Pythia-12B)."""
    if mock:
        raise ValueError(
            "run_evaluation_remote_l40s provisions paid GPU resources (L40S). "
            "For zero-GPU mock runs, use run_evaluation_mock_remote."
        )
    return _execute_evaluation(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        seed=seed,
        prompt_mode=prompt_mode,
    )


@app.function(
    image=image,
    volumes={"/root/results": results_volume},
    timeout=600,  # 10 minutes max runtime for CPU mock execution
)
def run_evaluation_mock_remote(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
) -> str:
    """Execute synthetic mock validation in a zero-GPU CPU container and persist outputs to volume."""
    from llm_cooperation.harness.runner import run_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    result_file = run_experiment(
        model_name=model_name,
        scenarios_path="/root/data/scenarios.json",
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device="cpu",
        mock=True,
        seed=seed,
        prompt_mode=prompt_mode,
    )

    # Commit changes to durable volume
    results_volume.commit()
    return str(result_file)


@app.local_entrypoint()
def main(
    model: str = "Qwen/Qwen2.5-3B",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    mock: bool = True,
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
    authorize_paid_run: bool = False,
):
    """Local CLI entrypoint for invoking Modal run.

    Safety:
    To launch real-model inference on paid cloud GPU hardware, you MUST pass
    `--authorize-paid-run True` or set environment variable `ALLOW_PAID_RUN=true`.
    Otherwise, real evaluation will fail fast with an authorization guard error.
    """
    if mock:
        print(f"[modal_app] Launching Phase 0 mock validation for {model} (zero-GPU CPU container)...")
        remote_path = run_evaluation_mock_remote.remote(
            model_name=model,
            revision=revision,
            precision=precision,
            seed=seed,
            prompt_mode=prompt_mode,
        )
    else:
        # Explicit paid-run authorization guard
        env_auth = os.environ.get("ALLOW_PAID_RUN", "").lower() in ("1", "true", "yes")
        if not (authorize_paid_run or env_auth):
            raise PermissionError(
                "PAID RUN GUARD TRIGGERED: Real-model inference on cloud GPUs incurs financial cost. "
                "To authorize this run, explicitly specify `--authorize-paid-run True` or "
                "set the environment variable `ALLOW_PAID_RUN=true`."
            )

        selected_gpu = resolve_model_gpu(model)
        print(f"[modal_app] Selected GPU hardware profile for {model}: {selected_gpu}")

        if selected_gpu == "L40S":
            print(f"[modal_app] Dispatching to L40S high-memory GPU container (precision={precision})...")
            remote_path = run_evaluation_remote_l40s.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                mock=False,
                seed=seed,
                prompt_mode=prompt_mode,
            )
        else:
            print(f"[modal_app] Dispatching to A10G GPU container (precision={precision})...")
            remote_path = run_evaluation_remote.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                mock=False,
                seed=seed,
                prompt_mode=prompt_mode,
            )

    print(f"[modal_app] Successfully finished run! Output persisted on Modal Volume at: {remote_path}")
    print("To download results to your local workspace:")
    print(f"  modal volume get llm-coop-results {Path(remote_path).name} results/")
