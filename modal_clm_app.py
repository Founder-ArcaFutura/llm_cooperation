"""Modal backend for the continuation-likelihood cooperation assay (CLM).

Provides a dedicated Modal app for scoring continuation log-probabilities,
separate from the forced-choice app in modal_app.py.

GPU selection:
  - Qwen2.5-3B: A10G (small)
  - Pythia-12B, neutral-SFT: L40S (medium)

Paid GPU compute requires explicit authorization via --authorize-paid-run.
DO NOT launch paid GPU compute during testing/mock runs.
"""

import os
from pathlib import Path
from typing import List, Optional, Union

if "MODAL_CONFIG_PATH" not in os.environ:
    try:
        user_cfg = os.path.expanduser("~/.modal.toml")
        if os.path.exists(user_cfg):
            with open(user_cfg, "r") as _:
                pass
    except Exception:
        os.environ["MODAL_CONFIG_PATH"] = os.path.abspath(".modal.dummy.toml")

import modal

CLM_APP_NAME = "llm-cooperation-clm"

hf_cache_volume = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)
results_volume = modal.Volume.from_name("llm-coop-results", create_if_missing=True)

clm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.2.0",
        "transformers>=4.40.0",
        "tokenizers>=0.19.0",
        "accelerate>=0.29.0",
        "pydantic>=2.7.0",
        "numpy>=1.26.0",
        "click>=8.1.0",
        "pyyaml>=6.0.0",
    )
    .add_local_python_source("llm_cooperation")
    .add_local_file("data/scenarios.json", "/root/data/scenarios.json")
    .add_local_file("data/scenarios_v1_expanded.json", "/root/data/scenarios_v1_expanded.json")
    .add_local_file(
        "data/scenarios_phase0b_utility_matched.json",
        "/root/data/scenarios_phase0b_utility_matched.json",
    )
    .add_local_file(
        "data/scenarios_phase1_prospective.json",
        "/root/data/scenarios_phase1_prospective.json",
    )
    .add_local_file(
        "data/scenarios_dose_response_exploratory.json",
        "/root/data/scenarios_dose_response_exploratory.json",
    )
    .add_local_file(
        "data/continuation_calibration_bank.json",
        "/root/data/continuation_calibration_bank.json",
    )
)

clm_app = modal.App(name=CLM_APP_NAME, image=clm_image)

GPU_PROFILES = {
    "small": "A10G",   # 1B–3B models
    "medium": "L40S",  # 7B–12B models
}

CLM_SUPPORTED_BANKS = {
    "pilot": "/root/data/scenarios.json",
    "expanded": "/root/data/scenarios_v1_expanded.json",
    "phase0b": "/root/data/scenarios_phase0b_utility_matched.json",
    "utility-matched": "/root/data/scenarios_phase0b_utility_matched.json",
    "phase1": "/root/data/scenarios_phase1_prospective.json",
    "dose-response": "/root/data/scenarios_dose_response_exploratory.json",
}


def _clm_get_secrets() -> List[modal.Secret]:
    secrets = []
    if (
        os.environ.get("MODAL_USE_HF_SECRET", "").lower() in ("1", "true", "yes")
        or "HF_TOKEN" in os.environ
        or "HUGGING_FACE_HUB_TOKEN" in os.environ
    ):
        try:
            secrets.append(modal.Secret.from_name("huggingface-secret"))
        except Exception:
            pass
    return secrets


def _clm_resolve_gpu(model_name: str) -> str:
    """Select GPU tier based on model name heuristic."""
    name_lower = model_name.lower()
    # Pythia-12B and neutral-SFT need L40S
    if "12b" in name_lower or "exploratory" in name_lower:
        return GPU_PROFILES["medium"]
    # Qwen2.5-3B and similar small models
    return GPU_PROFILES["small"]


def _execute_clm(
    model_name: str,
    revision: Optional[str],
    precision: str,
    device: str,
    seed: int,
    bank: str,
    template_ids: Optional[List[str]],
    split_filter: Optional[str],
    include_calibration: bool,
) -> Union[str, tuple]:
    """Core CLM execution inside Modal container."""
    os.environ["HF_HOME"] = "/root/hf_cache"

    if bank not in CLM_SUPPORTED_BANKS:
        raise ValueError(f"Unsupported bank '{bank}'. Supported: {sorted(CLM_SUPPORTED_BANKS)}")
    scenarios_path = CLM_SUPPORTED_BANKS[bank]

    from llm_cooperation.continuation.runner import run_continuation_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    result_path = run_continuation_experiment(
        model_name=model_name,
        scenarios_path=scenarios_path,
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=False,
        seed=seed,
        template_ids=template_ids,
        split_filter=split_filter,
    )

    results_volume.commit()
    hf_cache_volume.commit()

    if not include_calibration:
        return str(result_path)

    # Run calibration on the continuation calibration bank
    calib_path = run_continuation_experiment(
        model_name=model_name,
        scenarios_path="/root/data/continuation_calibration_bank.json",
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device=device,
        mock=False,
        seed=seed,
        template_ids=template_ids,
    )
    results_volume.commit()
    hf_cache_volume.commit()
    return str(result_path), str(calib_path)


# ---------------------------------------------------------------------------
# GPU function: A10G (small models: Qwen2.5-3B, Pythia-2.8B, etc.)
# ---------------------------------------------------------------------------


@clm_app.function(
    image=clm_image,
    gpu="A10G",
    volumes={"/root/hf_cache": hf_cache_volume, "/root/results": results_volume},
    timeout=5400,
    secrets=_clm_get_secrets(),
)
def run_clm_remote_a10g(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    seed: int = 42,
    bank: str = "phase1",
    template_ids: Optional[List[str]] = None,
    split_filter: Optional[str] = None,
    include_calibration: bool = False,
) -> Union[str, tuple]:
    """Execute CLM assay on A10G GPU (ideal for 1B-3B models)."""
    return _execute_clm(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        seed=seed,
        bank=bank,
        template_ids=template_ids,
        split_filter=split_filter,
        include_calibration=include_calibration,
    )


# ---------------------------------------------------------------------------
# GPU function: L40S (medium models: Pythia-12B, neutral-SFT)
# ---------------------------------------------------------------------------


@clm_app.function(
    image=clm_image,
    gpu="L40S",
    volumes={"/root/hf_cache": hf_cache_volume, "/root/results": results_volume},
    timeout=7200,
    secrets=_clm_get_secrets(),
)
def run_clm_remote_l40s(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    seed: int = 42,
    bank: str = "phase1",
    template_ids: Optional[List[str]] = None,
    split_filter: Optional[str] = None,
    include_calibration: bool = False,
) -> Union[str, tuple]:
    """Execute CLM assay on L40S GPU (ideal for 7B-12B models)."""
    return _execute_clm(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        seed=seed,
        bank=bank,
        template_ids=template_ids,
        split_filter=split_filter,
        include_calibration=include_calibration,
    )


# ---------------------------------------------------------------------------
# CPU container: mock validation (no GPU, no paid compute)
# ---------------------------------------------------------------------------


@clm_app.function(
    image=clm_image,
    volumes={"/root/results": results_volume},
    timeout=600,
)
def run_clm_mock_remote(
    model_name: str,
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    seed: int = 42,
    bank: str = "phase1",
    template_ids: Optional[List[str]] = None,
    split_filter: Optional[str] = None,
    include_calibration: bool = False,
) -> Union[str, tuple]:
    """Execute mock CLM validation in a zero-GPU CPU container."""
    if bank not in CLM_SUPPORTED_BANKS:
        raise ValueError(f"Unsupported bank '{bank}'. Supported: {sorted(CLM_SUPPORTED_BANKS)}")
    scenarios_path = CLM_SUPPORTED_BANKS[bank]

    from llm_cooperation.continuation.runner import run_continuation_experiment

    out_dir = "/root/results"
    os.makedirs(out_dir, exist_ok=True)

    result_path = run_continuation_experiment(
        model_name=model_name,
        scenarios_path=scenarios_path,
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device="cpu",
        mock=True,
        seed=seed,
        template_ids=template_ids,
        split_filter=split_filter,
    )

    results_volume.commit()

    if not include_calibration:
        return str(result_path)

    calib_path = run_continuation_experiment(
        model_name=model_name,
        scenarios_path="/root/data/continuation_calibration_bank.json",
        output_dir=out_dir,
        revision=revision,
        precision=precision,
        device="cpu",
        mock=True,
        seed=seed,
        template_ids=template_ids,
    )
    results_volume.commit()
    return str(result_path), str(calib_path)


# ---------------------------------------------------------------------------
# Local entrypoint
# ---------------------------------------------------------------------------


@clm_app.local_entrypoint()
def main(
    model: str = "Qwen/Qwen2.5-3B",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    mock: bool = True,
    seed: int = 42,
    bank: str = "phase1",
    templates: Optional[str] = None,
    split: Optional[str] = None,
    include_calibration: bool = False,
    authorize_paid_run: bool = False,
):
    """Local CLI entrypoint for the CLM assay Modal app.

    Safety:
    - Defaults to mock=True to prevent accidental paid GPU provisioning.
    - Set --authorize-paid-run or ALLOW_PAID_RUN=true for real inference.
    - Use --mock for zero-GPU testing before authorizing paid runs.

    Three-model comparison example (after authorization):

    \b
      # Pretrained Pythia-12B (L40S)
      modal run modal_clm_app.py --model EleutherAI/pythia-12b-deduped --no-mock --authorize-paid-run

      # Neutral-SFT Pythia-12B (L40S)
      modal run modal_clm_app.py \\
          --model founder-arcafutura/pythia-12b-exploratory-20261022 \\
          --revision 37e151204b4dcbc8eb4de25d344097cee0a0ca47 \\
          --no-mock --authorize-paid-run

      # Pretrained Qwen2.5-3B (A10G)
      modal run modal_clm_app.py --model Qwen/Qwen2.5-3B --no-mock --authorize-paid-run

    DO NOT launch paid GPU compute during implementation or testing.
    """
    template_ids = [t.strip() for t in templates.split(",")] if templates else None

    if bank not in CLM_SUPPORTED_BANKS:
        raise ValueError(f"Unsupported bank '{bank}'. Supported: {sorted(CLM_SUPPORTED_BANKS)}")

    if mock:
        print(f"[modal_clm_app] Launching mock CLM validation for {model} (CPU container)...")
        remote_result = run_clm_mock_remote.remote(
            model_name=model,
            revision=revision,
            precision=precision,
            seed=seed,
            bank=bank,
            template_ids=template_ids,
            split_filter=split,
            include_calibration=include_calibration,
        )
    else:
        env_auth = os.environ.get("ALLOW_PAID_RUN", "").lower() in ("1", "true", "yes")
        if not (authorize_paid_run or env_auth):
            raise PermissionError(
                "PAID RUN GUARD: CLM GPU inference incurs cost. "
                "Pass --authorize-paid-run or set ALLOW_PAID_RUN=true to proceed."
            )

        gpu = _clm_resolve_gpu(model)
        print(f"[modal_clm_app] GPU profile for {model}: {gpu}")

        if gpu == GPU_PROFILES["medium"]:
            print("[modal_clm_app] Dispatching to L40S container...")
            remote_result = run_clm_remote_l40s.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                seed=seed,
                bank=bank,
                template_ids=template_ids,
                split_filter=split,
                include_calibration=include_calibration,
            )
        else:
            print("[modal_clm_app] Dispatching to A10G container...")
            remote_result = run_clm_remote_a10g.remote(
                model_name=model,
                revision=revision,
                precision=precision,
                seed=seed,
                bank=bank,
                template_ids=template_ids,
                split_filter=split,
                include_calibration=include_calibration,
            )

    if isinstance(remote_result, tuple):
        result_path, calib_path = remote_result
        print(f"[modal_clm_app] CLM results at: {result_path}")
        print(f"[modal_clm_app] Calibration results at: {calib_path}")
        print(f"  modal volume get llm-coop-results {Path(result_path).name} results/")
        print(f"  modal volume get llm-coop-results {Path(calib_path).name} results/")
    else:
        result_path = remote_result
        print(f"[modal_clm_app] CLM results at: {result_path}")
        print(f"  modal volume get llm-coop-results {Path(result_path).name} results/")
