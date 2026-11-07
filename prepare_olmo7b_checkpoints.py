"""Non-GPU checkpoint selection for OLMo-2-1124-7B behavioral emergence.

Requires: pip install huggingface_hub
From repo root: python prepare_olmo7b_checkpoints.py
No paid inference is executed by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "allenai/OLMo-2-1124-7B"
FROZEN_PHASE0B_SHA256 = "a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b"
STAGE1_RE = re.compile(r"(?:stage1-)?step(\d+)-tokens(\d+)B$")
STAGE2_RE = re.compile(r"stage2-ingredient3-step(\d+)-tokens(\d+)B$")
FRACTIONS = (0.0, 0.2, 0.6, 1.0)


def select_revisions(refs):
    branches = {r.name: r.target_commit for r in (*refs.branches, *refs.tags)}
    stage1_by_key = {}
    stage2 = []
    for name, sha in branches.items():
        match = STAGE1_RE.fullmatch(name)
        if match:
            step, tokens = map(int, match.groups())
            key = (step, tokens, sha)
            if key not in stage1_by_key or name.startswith("stage1-"):
                stage1_by_key[key] = name
        match = STAGE2_RE.fullmatch(name)
        if match:
            step, tokens = map(int, match.groups())
            stage2.append((tokens, step, name, sha))
    stage1 = [(k[1], k[0], name, k[2]) for k, name in stage1_by_key.items()]
    if len(stage1) < 4:
        raise RuntimeError(f"Fewer than four official Stage-1 checkpoints found ({len(stage1)}).")
    if not stage2:
        raise RuntimeError("No ingredient-3 Stage-2 checkpoint found; refusing to select a merged final model.")
    maximum_tokens = max(x[0] for x in stage1)
    selected = []
    taken = set()
    for frac in FRACTIONS:
        target = maximum_tokens * frac
        available = [x for x in stage1 if x[3] not in taken]
        tokens, step, name, sha = min(available, key=lambda x: (abs(x[0] - target), x[0], x[1]))
        taken.add(sha)
        selected.append({
            "checkpoint_order": len(selected),
            "model_id": MODEL_ID, "revision": name, "commit_sha": sha,
            "training_stage": "stage1_pretraining", "training_step": step,
            "stage_tokens_billions": tokens, "cumulative_tokens_billions": tokens,
            "training_stage_label": "initialization" if not selected and tokens == 0 else (
                "earliest_available_pretraining" if not selected else
                "early_stage1" if len(selected) == 1 else
                "intermediate_stage1" if len(selected) == 2 else "stage1_endpoint"
            ),
            "trajectory_lineage": "official_1124_7b_stage1_then_ingredient3_stage2",
        })
    stage2_tokens, stage2_step, stage2_name, stage2_sha = max(stage2)
    selected.append({
        "checkpoint_order": 4, "model_id": MODEL_ID,
        "revision": stage2_name, "commit_sha": stage2_sha,
        "training_stage": "stage2_ingredient3_continuation", "training_step": stage2_step,
        "stage_tokens_billions": stage2_tokens,
        "cumulative_tokens_billions": maximum_tokens + stage2_tokens,
        "training_stage_label": "ingredient3_stage2_endpoint_NOT_SOUPED_BASE",
        "trajectory_lineage": "official_1124_7b_stage1_then_ingredient3_stage2",
    })
    if len({r['commit_sha'] for r in selected}) != 5:
        raise RuntimeError("Selected revisions are not five distinct immutable commits.")
    for row in selected:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", row["commit_sha"]):
            raise ValueError(f"Unresolved or malformed immutable SHA for {row['revision']}.")
    return selected, maximum_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="research/olmo2_7b_behavior/checkpoint_selection.json")
    parser.add_argument("--bank", default="data/scenarios_phase0b_utility_matched.json")
    args = parser.parse_args()
    bank = Path(args.bank)
    if not bank.exists():
        raise FileNotFoundError(f"Frozen Phase 0B bank not found: {bank}")
    payload = bank.read_bytes()
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != FROZEN_PHASE0B_SHA256:
        raise ValueError(f"Unexpected Phase 0B bank hash: {actual_sha}")
    if len(json.loads(payload)["scenarios"]) != 124:
        raise ValueError("Expected exactly 124 Phase 0B scenarios")
    from huggingface_hub import HfApi
    refs = HfApi().list_repo_refs(MODEL_ID, repo_type="model")
    selected, stage1_max = select_revisions(refs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "version": "olmo2-7b-behavioral-selection-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "selection_method": "live official Hugging Face branches/tags nearest Stage1 0/20/60/100%, followed by ingredient3 Stage2 endpoint",
        "bank_sha256": actual_sha, "bank_path": str(bank),
        "stage1_max_tokens_billions": stage1_max,
        "stage2_merged_main_used": False,
        "checkpoint_count": 5,
        "checkpoints": selected,
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Selection saved:", output)
    print("Frozen bank SHA256:", actual_sha)
    for row in selected:
        print(f"{row['checkpoint_order']}: {row['training_stage_label']:45s} "
              f"{row['cumulative_tokens_billions']:5d}B  {row['revision']}  {row['commit_sha']}")
    if selected[0]["cumulative_tokens_billions"] != 0:
        print("WARNING: Zero-token initialization not found in official 7B refs. "
              "Earliest selected point is trained; do NOT interpret as random initialization.")
    print("No paid Modal jobs or model-weight downloads were launched by this selector.")


if __name__ == "__main__":
    main()
