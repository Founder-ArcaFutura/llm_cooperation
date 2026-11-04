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
    .add_local_file("data/scenarios_v1_expanded.json", "/root/data/scenarios_v1_expanded.json")
    .add_local_file("data/scenarios_phase0b_utility_matched.json", "/root/data/scenarios_phase0b_utility_matched.json")
    .add_local_file("data/scenarios_phase1_prospective.json", "/root/data/scenarios_phase1_prospective.json")
    .add_local_file("data/calibration_bank.json", "/root/data/calibration_bank.json")
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


def parse_parameter_count_b(name_or_size: str) -> Optional[float]:
    """Parse numeric parameter count in billions (e.g. '2.8B' -> 2.8, '12b' -> 12.0)."""
    import re
    m = re.search(r'(?:^|[^0-9.])([0-9]+(?:\.[0-9]+)?)\s*[Bb](?:$|[^0-9a-zA-Z])', name_or_size)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def resolve_model_gpu(model_name: str) -> str:
    """Select appropriate GPU hardware profile based on model manifest or numeric size.

    - 1B - 3B models: A10G (small)
    - 7B - 14B models (e.g. Pythia-12B base or SFT comparator, OLMo-7B): L40S (medium)
    - Large / unsupported models: A100-80GB (large)
    Never confuses '2.8B' with '8B'.
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
                            size_str = str(item.get("size", ""))
                            param_b = parse_parameter_count_b(size_str)
                            mem = item.get("recommended_gpu_mem_gb", 0)

                            if mem >= 60 or (param_b is not None and param_b > 14.0):
                                return GPU_PROFILES["large"]
                            if mem >= 32 or (param_b is not None and 6.0 <= param_b <= 14.0):
                                return GPU_PROFILES["medium"]
                            if (param_b is not None and param_b <= 4.0) or mem <= 16:
                                return GPU_PROFILES["small"]
        except Exception:
            pass

    # 2. Heuristics based on parsed parameter count from model name
    param_b = parse_parameter_count_b(clean_name)
    if param_b is not None:
        if param_b > 14.0:
            return GPU_PROFILES["large"]
        elif param_b >= 6.0:
            return GPU_PROFILES["medium"]
        else:
            return GPU_PROFILES["small"]

    # Default for unknown small models
    return GPU_PROFILES["small"]


def _get_secrets() -> List[modal.Secret]:
    """Safely obtain Hugging Face secret if configured in environment."""
    secrets = []
    if os.environ.get("MODAL_USE_HF_SECRET", "").lower() in ("1", "true", "yes") or "HF_TOKEN" in os.environ or "HUGGING_FACE_HUB_TOKEN" in os.environ:
        try:
            secrets.append(modal.Secret.from_name("huggingface-secret"))
        except Exception:
            pass
    return secrets


SUPPORTED_BANKS = {
    "pilot": "/root/data/scenarios.json",
    "expanded": "/root/data/scenarios_v1_expanded.json",
    "phase0b": "/root/data/scenarios_phase0b_utility_matched.json",
    "utility-matched": "/root/data/scenarios_phase0b_utility_matched.json",
    "phase1": "/root/data/scenarios_phase1_prospective.json",
}


def resolve_bank_and_split(
    bank: str,
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
) -> tuple[str, Optional[str]]:
    """Validate bank identifier and enforce Phase 0B split defaults & Phase 1 holdout guard.

    Fails explicitly if bank is unsupported rather than silently choosing another instrument.
    """
    bank_clean = (bank or "").strip().lower()
    if bank_clean not in SUPPORTED_BANKS:
        raise ValueError(
            f"Unsupported bank '{bank}'. Supported banks: {sorted(list(SUPPORTED_BANKS.keys()))}. "
            "Failing explicitly rather than silently falling back."
        )

    scenarios_path = SUPPORTED_BANKS[bank_clean]
    is_phase0b = bank_clean in ("phase0b", "utility-matched")
    is_phase1 = bank_clean == "phase1"

    # Fail-closed Phase 1 holdout protection guard
    if is_phase1:
        # Check draft status fail-closed
        import json
        from pathlib import Path
        local_p = Path("data/scenarios_phase1_prospective.json")
        target_check = local_p if local_p.exists() else Path(scenarios_path)
        if target_check.exists():
            with open(target_check, "r", encoding="utf-8") as f:
                bdata = json.load(f)
            if bdata.get("status") == "draft_pending_review":
                raise PermissionError(
                    "PHASE 1 HOLDOUT PROTECTION TRIGGERED: The Phase 1 prospective replication bank is currently in "
                    "status 'draft_pending_review'. Phase 1 scenarios must remain held out and unexecuted while in draft "
                    "status. No inference (real or mock) is permitted until independent review and protocol approval are complete."
                )

        env_p1_auth = os.environ.get("ALLOW_PHASE1_RUN", "").lower() in ("1", "true", "yes")
        if not (authorize_phase1_run or env_p1_auth):
            raise PermissionError(
                "PHASE 1 INFERENCE AUTHORIZATION GUARD: Executing inference on the Phase 1 prospective replication bank "
                "requires explicit scientific authorization (--authorize-phase1-run or ALLOW_PHASE1_RUN=true)."
            )

    effective_split = split
    if is_phase0b and effective_split is None:
        effective_split = "exploratory"

    # Confirmatory split authorization guard for Phase 0B
    if is_phase0b and effective_split in ("confirmatory", "all"):
        env_auth = os.environ.get("ALLOW_CONFIRMATORY_RUN", "").lower() in ("1", "true", "yes")
        if not (authorize_confirmatory or env_auth):
            raise PermissionError(
                f"CONFIRMATORY SPLIT GUARD: Executing held-out confirmatory partition in Phase 0B "
                f"requires explicit scientific authorization (--authorize-confirmatory or ALLOW_CONFIRMATORY_RUN=true). "
                f"Phase 0B defaults to 'exploratory' to protect confirmatory held-out isolation."
            )

    return scenarios_path, effective_split


def _execute_evaluation(
    model_name: str,
    revision: Optional[str],
    precision: str,
    device: str,
    seed: int,
    prompt_mode: str,
    bank: str = "pilot",
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
) -> str:
    """Internal helper to execute evaluation inside container and commit volumes."""
    os.environ["HF_HOME"] = "/root/hf_cache"
    from llm_cooperation.harness.runner import run_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    scenarios_path, effective_split = resolve_bank_and_split(
        bank=bank,
        split=split,
        authorize_confirmatory=authorize_confirmatory,
        authorize_phase1_run=authorize_phase1_run,
    )

    result_file = run_experiment(
        model_name=model_name,
        scenarios_path=scenarios_path,
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=False,
        seed=seed,
        prompt_mode=prompt_mode,
        split_filter=effective_split if effective_split != "all" else None,
        authorize_phase1_run=authorize_phase1_run,
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
    bank: str = "pilot",
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
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
        bank=bank,
        split=split,
        authorize_confirmatory=authorize_confirmatory,
        authorize_phase1_run=authorize_phase1_run,
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
    bank: str = "pilot",
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
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
        bank=bank,
        split=split,
        authorize_confirmatory=authorize_confirmatory,
        authorize_phase1_run=authorize_phase1_run,
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
    bank: str = "pilot",
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
) -> str:
    """Execute synthetic mock validation in a zero-GPU CPU container and persist outputs to volume."""
    from llm_cooperation.harness.runner import run_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    scenarios_path, effective_split = resolve_bank_and_split(
        bank=bank,
        split=split,
        authorize_confirmatory=authorize_confirmatory,
        authorize_phase1_run=authorize_phase1_run,
    )

    result_file = run_experiment(
        model_name=model_name,
        scenarios_path=scenarios_path,
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device="cpu",
        mock=True,
        seed=seed,
        prompt_mode=prompt_mode,
        split_filter=effective_split if effective_split != "all" else None,
        authorize_phase1_run=authorize_phase1_run,
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
    bank: str = "pilot",
    split: Optional[str] = None,
    authorize_confirmatory: bool = False,
    authorize_phase1_run: bool = False,
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
            bank=bank,
            split=split,
            authorize_confirmatory=authorize_confirmatory,
            authorize_phase1_run=authorize_phase1_run,
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

        if selected_gpu == GPU_PROFILES["medium"]:  # L40S
            print(f"[modal_app] Dispatching to L40S high-memory GPU container (precision={precision})...")
            remote_path = run_evaluation_remote_l40s.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                mock=False,
                seed=seed,
                prompt_mode=prompt_mode,
                bank=bank,
                split=split,
                authorize_confirmatory=authorize_confirmatory,
                authorize_phase1_run=authorize_phase1_run,
            )
        elif selected_gpu == GPU_PROFILES["small"]:  # A10G
            print(f"[modal_app] Dispatching to A10G GPU container (precision={precision})...")
            remote_path = run_evaluation_remote.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                mock=False,
                seed=seed,
                prompt_mode=prompt_mode,
                bank=bank,
                split=split,
                authorize_confirmatory=authorize_confirmatory,
                authorize_phase1_run=authorize_phase1_run,
            )
        else:
            # If large or unsupported GPU profile is selected, fail fast before provisioning
            raise NotImplementedError(
                f"Selected GPU profile '{selected_gpu}' for model '{model}' is not currently provisioned. "
                "Phase 0 compute is constrained to small/medium base models (<= 12B). "
                "Failing immediately before provisioning paid resources."
            )

    print(f"[modal_app] Successfully finished run! Output persisted on Modal Volume at: {remote_path}")
    print("To download results to your local workspace:")
    print(f"  modal volume get llm-coop-results {Path(remote_path).name} results/")
