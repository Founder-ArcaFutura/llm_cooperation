"""Separate optional behavioral assay, gated by independently reviewed competence.

No competence is inferred from representation decoding. No inference on import.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import inspect
import json
from pathlib import Path
import re
import shutil

import numpy as np

from .lexical_pilot import (
    DEFAULT_MODEL_ID,
    DEFAULT_REVISION,
    MeasurementTokenizer,
    digest,
    sha,
    read_json,
    write_json,
)
from .lexical_pilot_run import verify_plan, behavior_text
from .lexical_pilot_analysis import interval


def format_hash():
    return digest(inspect.getsource(behavior_text))


def parse_answer(text):
    # Strict isolated generated letter, optional punctuation. Never forced-choice fallback.
    m = re.fullmatch(r"\s*([ABCD])[.)]?\s*", text)
    return m.group(1) if m else None


def competence_gate(receipt_path):
    """Receipt binds human-reviewed objective and strategic comprehension evidence.

    Raw samples: item_id, task (objective/strategic), rotation 0..3,
    correct_letter and generated_text. All four rotations of every item required.
    """
    receipt_path = Path(receipt_path)
    receipt = read_json(receipt_path)
    if (
        receipt.get("target_model") != DEFAULT_MODEL_ID
        or receipt.get("target_revision") != DEFAULT_REVISION
    ):
        raise ValueError("Competence evidence has wrong model/revision")
    if (
        receipt.get("prompt_format_sha256") != format_hash()
        or not receipt.get("reviewer")
        or receipt.get("approved") is not True
    ):
        raise ValueError(
            "Named independent competence review and exact prompt-format hash required"
        )
    evidence = receipt_path.parent / receipt["evidence_file"]
    if sha(evidence) != receipt["evidence_sha256"]:
        raise ValueError("Competence evidence hash mismatch")
    raw = read_json(evidence)
    if (
        raw.get("target_model") != DEFAULT_MODEL_ID
        or raw.get("target_revision") != DEFAULT_REVISION
        or raw.get("mock") is not False
    ):
        raise ValueError(
            "Competence raw evidence must identify actual model, revision and non-mock execution"
        )
    samples = raw["samples"]
    grouped = defaultdict(list)
    for s in samples:
        if (
            s["task"] not in ("objective", "strategic")
            or s["correct_letter"] not in "ABCD"
            or len(s["correct_letter"]) != 1
        ):
            raise ValueError("Invalid calibration item")
        grouped[(s["task"], s["item_id"])].append(s)
    for rs in grouped.values():
        if sorted(r["rotation"] for r in rs) != [0, 1, 2, 3] or sorted(
            r["correct_letter"] for r in rs
        ) != list("ABCD"):
            raise ValueError(
                "Each independent item must appear once at each correct-answer position"
            )
    counts = {
        task: sum(k[0] == task for k in grouped) for task in ("objective", "strategic")
    }
    if counts["objective"] < 24 or counts["strategic"] < 12:
        raise ValueError(
            "Need >=24 objective and >=12 independently reviewed strategic-comprehension items"
        )
    metrics = {}
    for task in ("objective", "strategic"):
        rows = [r for r in samples if r["task"] == task]
        validity = np.mean(
            [parse_answer(r["generated_text"]) is not None for r in rows]
        )
        accuracy = np.mean(
            [parse_answer(r["generated_text"]) == r["correct_letter"] for r in rows]
        )
        by_position = [
            np.mean(
                [
                    parse_answer(r["generated_text"]) == letter
                    for r in rows
                    if r["correct_letter"] == letter
                ]
            )
            for letter in "ABCD"
        ]
        spread = max(by_position) - min(by_position)
        metrics[task] = {
            "validity": float(validity),
            "accuracy": float(accuracy),
            "position_spread": float(spread),
            "n_items": counts[task],
        }
        if validity < 0.95 or accuracy < 0.80 or spread > 0.15:
            raise ValueError(f"Competence gate failed: {task}: {metrics[task]}")
    return metrics


def run_behavior(
    plan, receipt, output, authorize_inference=False, authorize_paid_run=False
):
    if not (authorize_inference and authorize_paid_run):
        raise PermissionError(
            "Both --authorize-inference and --authorize-paid-run are required"
        )
    plan, out = Path(plan), Path(output)
    manifest = verify_plan(plan)
    metrics = competence_gate(receipt)
    if sha(__file__) != manifest["behavior_script_sha256"]:
        raise ValueError("Behavior script changed since freeze")
    if out.exists():
        raise FileExistsError(out)
    rows = read_json(plan / "behavior_prompts.json")
    tok = MeasurementTokenizer()
    if tok.files != manifest["tokenizer_files_sha256"]:
        raise ValueError("Tokenizer files changed")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch

    tokenizer = AutoTokenizer.from_pretrained(str(tok.snapshot), local_files_only=True)
    for row in rows:
        if tokenizer.encode(row["prompt_text"]) != row["input_ids"]:
            raise ValueError("Behavior tokenization mismatch")
        for continuation, token in zip(row["letter_continuations"], row["letter_ids"]):
            if tokenizer.encode(row["prompt_text"] + continuation) != row[
                "input_ids"
            ] + [token]:
                raise ValueError("Behavior continuation boundary mismatch")
    model = AutoModelForCausalLM.from_pretrained(
        DEFAULT_MODEL_ID,
        revision=DEFAULT_REVISION,
        torch_dtype=torch.float32,
        device_map="auto",
    )
    model.eval()
    out.mkdir(parents=True)
    write_json(
        out / "manifest.json",
        {"status": "running", "plan_manifest_sha256": sha(plan / "manifest.json")},
    )
    results = []
    for row in rows:
        inputs = tokenizer(row["prompt_text"], return_tensors="pt").to(model.device)
        with torch.inference_mode():
            logits = model(**inputs, use_cache=False).logits[0, -1].float()
            letter_logits = logits[row["letter_ids"]]
            probability = torch.softmax(letter_logits, dim=0).cpu().numpy()
            top = torch.max(letter_logits)
            winners = torch.nonzero(letter_logits == top).flatten().cpu().tolist()
            generated = model.generate(
                **inputs,
                max_new_tokens=8,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(
            generated[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )
        letter = parse_answer(raw)
        results.append(
            {
                "id": row["id"],
                "generated_text": raw,
                "generated_letter": letter,
                "generated_strategy": row["order"]["ABCD".index(letter)]
                if letter
                else None,
                "letter_probabilities": probability.tolist(),
                "forced_unique_strategy": row["order"][winners[0]]
                if len(winners) == 1
                else None,
                "forced_tie": len(winners) != 1,
            }
        )
    write_json(out / "results.json", results)
    shutil.copyfile(receipt, out / "competence_receipt.json")
    write_json(
        out / "manifest.json",
        {
            "status": "completed",
            "mock": False,
            "target_model": DEFAULT_MODEL_ID,
            "target_revision": DEFAULT_REVISION,
            "dtype": "float32",
            "prompt_format_sha256": format_hash(),
            "plan_manifest_sha256": sha(plan / "manifest.json"),
            "results_sha256": sha(out / "results.json"),
            "competence_receipt_sha256": sha(receipt),
            "competence_metrics": metrics,
            "script_sha256": sha(__file__),
        },
    )
    return {"presentations": len(results), "status": "completed"}


def analyze_behavior(plan, run, output):
    plan, run, output = Path(plan), Path(run), Path(output)
    pm = verify_plan(plan)
    rm = read_json(run / "manifest.json")
    if (
        sha(__file__) != pm["behavior_script_sha256"]
        or rm.get("script_sha256") != pm["behavior_script_sha256"]
    ):
        raise ValueError("Behavior implementation changed since freeze/run")
    if output.exists():
        raise FileExistsError(output)
    if (
        rm.get("status") != "completed"
        or rm.get("mock") is not False
        or rm.get("target_model") != DEFAULT_MODEL_ID
        or rm.get("target_revision") != DEFAULT_REVISION
        or rm.get("plan_manifest_sha256") != sha(plan / "manifest.json")
        or rm.get("results_sha256") != sha(run / "results.json")
        or rm.get("prompt_format_sha256") != format_hash()
    ):
        raise ValueError("Behavior provenance mismatch")
    if sha(run / "competence_receipt.json") != rm["competence_receipt_sha256"]:
        raise ValueError("Competence receipt changed")
    expected = {r["id"]: r for r in read_json(plan / "behavior_prompts.json")}
    results = read_json(run / "results.json")
    if len(results) != len(expected) or {r["id"] for r in results} != set(expected):
        raise ValueError("Behavior inventory mismatch")
    grouped = defaultdict(list)
    for r in results:
        p = expected[r["id"]]
        letter = parse_answer(r["generated_text"])
        strategy = p["order"]["ABCD".index(letter)] if letter else None
        probabilities = np.asarray(r["letter_probabilities"], dtype=float)
        if (
            probabilities.shape != (4,)
            or not np.isfinite(probabilities).all()
            or (probabilities < 0).any()
            or abs(probabilities.sum() - 1) > 1e-5
        ):
            raise ValueError("Invalid forced letter probabilities")
        grouped[(p["family"], p["condition"])].append(
            {
                "valid": letter is not None,
                "coop": strategy == "COOPERATE",
                "forced_coop_probability": float(
                    probabilities[p["order"].index("COOPERATE")]
                ),
                "position": p["order"].index("COOPERATE"),
            }
        )
    families = sorted({g for g, c in grouped})
    conditions = sorted({c for g, c in grouped})
    per_family = {}
    for (g, c), rows in grouped.items():
        per_family[(g, c)] = {
            k: float(np.mean([r[k] for r in rows]))
            for k in ("valid", "coop", "forced_coop_probability")
        }
    summary = {}
    for c in conditions:
        summary[c] = {
            k: interval([per_family[(g, c)][k] for g in families])
            for k in ("valid", "coop", "forced_coop_probability")
        }
        summary[c]["paired_coop_change"] = interval(
            [
                per_family[(g, c)]["coop"] - per_family[(g, "original")]["coop"]
                for g in families
            ]
        )
        position_rates = [
            float(
                np.mean(
                    [
                        np.mean(
                            [r["coop"] for r in grouped[(g, c)] if r["position"] == p]
                        )
                        for g in families
                    ]
                )
            )
            for p in range(4)
        ]
        summary[c]["cooperation_by_position"] = position_rates
        summary[c]["position_spread"] = max(position_rates) - min(position_rates)
    report = {
        "status": "BEHAVIOR_ONLY",
        "summary": summary,
        "families": families,
        "competence_metrics": rm["competence_metrics"],
        "invalid_answers_remain_in_denominator": True,
        "forced_probabilities_are_not_generated_choices": True,
        "plan_manifest_sha256": sha(plan / "manifest.json"),
        "run_manifest_sha256": sha(run / "manifest.json"),
    }
    output.mkdir(parents=True)
    write_json(output / "behavior_analysis.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    r.add_argument("--competence-receipt", required=True)
    r.add_argument("--output", required=True)
    r.add_argument("--authorize-inference", action="store_true")
    r.add_argument("--authorize-paid-run", action="store_true")
    a = sub.add_parser("analyze")
    a.add_argument("--plan", required=True)
    a.add_argument("--run", required=True)
    a.add_argument("--output", required=True)
    sub.add_parser("format-hash")
    args = p.parse_args()
    if args.command == "format-hash":
        print(format_hash())
        return
    result = (
        run_behavior(
            args.plan,
            args.competence_receipt,
            args.output,
            args.authorize_inference,
            args.authorize_paid_run,
        )
        if args.command == "run"
        else analyze_behavior(args.plan, args.run, args.output)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
