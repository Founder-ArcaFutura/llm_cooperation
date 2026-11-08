"""Optional remote scoring. No app deployment or cloud call on import.

Run from repository root, AFTER approval:
modal run research/pretraining_counterfactual_v1/modal_score.py --help
"""
from pathlib import Path
import json
import modal

ROOT = Path(__file__).resolve().parents[2]
app = modal.App("cooperation-pretraining-census-v1")
volume = modal.Volume.from_name("cooperation-pretraining-census-v1", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install_from_requirements(str(Path(__file__).with_name("requirements.txt")))
         .add_local_dir(str(Path(__file__).parent), remote_path="/root/research/pretraining_counterfactual_v1",
                        ignore=["outputs", "__pycache__"]))


@app.function(image=image, gpu="T4", cpu=2, memory=8192, timeout=3600,
              volumes={"/work": volume}, max_containers=1, retries=0)
def score_remote(config: dict, run_name: str, limit: int, seconds: int):
    from research.pretraining_counterfactual_v1.data import score
    try:
        score(config, f"/work/{run_name}", limit=limit, device="cuda", max_seconds=seconds)
    finally:
        volume.commit()


@app.local_entrypoint()
def main(config: str, run_name: str, approve_cloud: bool = False,
         limit: int = 1000, seconds: int = 600):
    import re
    from research.pretraining_counterfactual_v1.data import validate_config
    if not approve_cloud:
        raise ValueError("Cloud launch requires --approve-cloud after explicit approval")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_name):
        raise ValueError("run-name must be a simple directory name")
    if not 30 <= seconds <= 3300 or limit < 0:
        raise ValueError("Require 30 <= seconds <= 3300 and limit >= 0")
    c = json.loads(Path(config).read_text()); validate_config(c)
    score_remote.remote(c, run_name, limit, seconds)
    print(f"Persisted to cooperation-pretraining-census-v1/{run_name}; download via modal volume get")
