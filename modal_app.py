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
from typing import Optional
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

# GPU profiles by model size
# 1B - 3B models: A10G or T4 (ample memory for 1B-3B)
# 7B - 12B models / SFT comparator: L40S or A100 (48GB-80GB VRAM headroom)
GPU_PROFILES = {
    "small": "A10G",       # ~24GB VRAM, ideal for 1B-3B
    "medium": "L40S",      # ~48GB VRAM, ideal for 7B-12B
    "large": "A100-80GB",  # 80GB VRAM, high throughput
}


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/hf_cache": hf_cache_volume, "/root/results": results_volume},
    timeout=3600,  # 1 hour max runtime
    secrets=[modal.Secret.from_name("huggingface-secret")] if "huggingface-secret" in os.environ else [],
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
    """Execute evaluation inside Modal GPU environment and persist outputs to volume."""
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
        mock=mock,
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
):
    """Local CLI entrypoint for invoking Modal run."""
    print(f"[modal_app] Launching Phase 0 run for {model} (mock={mock}, precision={precision})...")
    remote_path = run_evaluation_remote.remote(
        model_name=model,
        revision=revision,
        precision=precision,
        mock=mock,
        seed=seed,
        prompt_mode=prompt_mode,
    )
    print(f"[modal_app] Successfully finished run! Output persisted on Modal Volume at: {remote_path}")
    print("To download results to your local workspace:")
    print(f"  modal volume get llm-coop-results {Path(remote_path).name} results/")
