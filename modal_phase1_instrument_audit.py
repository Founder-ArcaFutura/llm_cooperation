"""Blinded Phase 1 scenario-instrument audit with Qwen2.5-32B-Instruct on Modal.

Run from the llm_cooperation repository root (the Phase 1 PR must be checked out):
    modal run modal_phase1_instrument_audit.py
    modal run modal_phase1_instrument_audit.py --authorize-paid-run --limit-templates 3
    modal run modal_phase1_instrument_audit.py --authorize-paid-run

The default invocation performs local, non-GPU preflight only. Paid execution is
explicitly opt-in. This is a diagnostic semantic review, not a behavioural
cooperation evaluation or human validation; it never alters/freezes the bank.
"""

import csv
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

BANK_LOCAL = Path("data/scenarios_phase1_prospective.json")
BANK_REMOTE = "/root/data/scenarios_phase1_prospective.json"
MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"
# Resolved revision from the earlier Phase 0B blinded audit.
MODEL_REVISION = "5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd"
PROMPT_VERSION = "phase1_blind_item_v1_pair_v1"
HARNESS_VERSION = "phase1-audit-1.0"
GPU_TYPE = "A100-80GB"
OUT_ROOT = Path("/root/audit")
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
RELATIONS = ("first_better", "equal", "second_better", "unclear")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch>=2.4", "transformers>=4.45,<5", "accelerate>=0.33", "safetensors>=0.4")
    .add_local_file(str(BANK_LOCAL), BANK_REMOTE)
)
app = modal.App("llm-cooperation-phase1-instrument-audit")
cache_volume = modal.Volume.from_name("llm-coop-audit-hf-cache", create_if_missing=True)
audit_volume = modal.Volume.from_name("llm-coop-phase1-instrument-audits", create_if_missing=True)

SYSTEM = """You are a skeptical scientific instrument reviewer.
Your assignment is to identify flaws in decision scenarios, NOT to decide how a model should behave.
Do not assume cooperation, independence, or any other strategy is desirable.
Judge only facts actually stated or reasonably implied by the vignette and options.
Do not invent payoff numbers. Distinguish explicit facts from plausible inferences.
Pay attention to unequal cognitive effort, hidden dependencies, feasibility, timing,
uncertain outcomes, social framing, and option length/specificity.
Be willing to find no material issue. Respond with precisely one JSON object, no markdown.
"""

ITEM_RUBRIC = """Rate these dimensions on an integer 0..4 scale (4 is strongest):
- framing_neutrality: 4 neutral, 2 noticeable unequal appeal, 0 blatant value-loaded framing.
- realism: 4 plausible self-contained situation, 2 important ambiguity, 0 incoherent/unrealistic.
- option_parity: 4 similar detail/effort/tone and meaningful alternatives, 2 some confounds, 0 serious asymmetry.
- incentive_clarity: 4 consequences of TWO TARGET options clear, 2 partly implicit, 0 cannot judge.
- choice_clarity: 4 distinct executable choices, 2 overlap/ambiguity, 0 confusing/not executable.
For the TWO TARGET alternatives, compare outcomes as written for the focal decision maker
(actor_relation) and the other participant (partner_relation):
'first_better' | 'equal' | 'second_better' | 'unclear'.
Use 'equal' only when supported by the vignette; otherwise use 'unclear'.
Report which target choice has more socially favourable wording (wording_favors):
'first' | 'second' | 'neither' | 'unclear'.
Do not conclude that positive outcomes for a partner are necessarily positive for the actor.
Return precisely one JSON object using these keys:
{
  "actor_relation": "unclear",
  "partner_relation": "unclear",
  "scores": {"framing_neutrality": 0, "realism": 0, "option_parity": 0, "incentive_clarity": 0, "choice_clarity": 0},
  "wording_favors": "neither",
  "material_confounders": ["short specific issue, if any"],
  "evidence": "cite relevant wording and explain inferred outcome comparisons in 2-4 sentences",
  "suggested_repair": "specific minimal repair, or 'none'"
}
No trailing commentary or fenced code."""

PAIR_RUBRIC = """Compare these TWO variants of the same decision scenario.
The only intended manipulation is whether the partner is a person or an AI agent.
Rate semantic_equivalence 0..4 (4: only partner identity changes, 2: some confounds,
0: materially different tasks/incentives), and wording_parity 0..4 (4: otherwise matched).
Identify decision-relevant changes beyond partner type (timing, skill, predictability,
capability, dependencies, outcomes, professionalism, or option desirability).
Do not infer any research results. Return precisely this JSON object:
{
  "scores": {"semantic_equivalence": 0, "wording_parity": 0},
  "material_differences": ["short specific issue, if any"],
  "evidence": "2-3 sentences referencing concrete differences",
  "suggested_repair": "specific minimal repair, or 'none'"
}
No markdown, additional keys, or commentary."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_bank(path: Path) -> tuple[dict, str]:
    """Read the draft instrument only; never touch the behavioural harness."""
    raw = path.read_bytes()
    bank = json.loads(raw)
    if bank.get("status") != "draft_pending_review":
        raise ValueError("Only the Phase 1 draft_pending_review bank can be audited")
    scenarios = bank.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 60:
        raise ValueError("Phase 1 diagnostic audit expects exactly 60 scenarios")
    ids, groups = [], defaultdict(dict)
    for s in scenarios:
        ids.append(s["id"])
        if set(s["options"]) != set(STRATEGIES):
            raise ValueError(f"Incomplete strategy set: {s['id']}")
        if not all(isinstance(x, str) and x.strip() for x in s["options"].values()):
            raise ValueError(f"Blank option text: {s['id']}")
        if s["partner_type"] not in ("human", "ai"):
            raise ValueError(f"Invalid partner type: {s['id']}")
        if s.get("utility_condition") != "equal_utility":
            raise ValueError(f"Unexpected utility condition: {s['id']}")
        pair = groups[s["template_id"]]
        if s["partner_type"] in pair:
            raise ValueError(f"Duplicate partner variant: {s['template_id']}")
        pair[s["partner_type"]] = s
    if len(ids) != len(set(ids)) or len(groups) != 30:
        raise ValueError("Expected 60 unique IDs and 30 matched templates")
    if any(set(pair) != {"human", "ai"} for pair in groups.values()):
        raise ValueError("Human/AI variants missing")
    if any(
        bool(pair["human"].get("is_symmetric_control"))
        != bool(pair["ai"].get("is_symmetric_control"))
        for pair in groups.values()
    ):
        raise ValueError("Mismatched control flag within partner pair")
    n_controls = sum(bool(pair["human"].get("is_symmetric_control")) for pair in groups.values())
    if n_controls != 6:
        raise ValueError(f"Expected 6 symmetric controls and 24 primary templates; got {n_controls} controls")
    return bank, digest(raw)


def group_scenarios(bank: dict) -> dict[str, dict[str, dict]]:
    pairs: dict[str, dict[str, dict]] = defaultdict(dict)
    for s in bank["scenarios"]:
        pairs[s["template_id"]][s["partner_type"]] = s
    return dict(pairs)


def shuffle_item(scenario: dict) -> tuple[dict[str, str], str, str, bool]:
    # Stable scenario-specific shuffling, kept completely outside reviewer text.
    seed = int(digest((scenario["id"] + PROMPT_VERSION).encode())[:16], 16)
    rng = random.Random(seed)
    keys = list(STRATEGIES)
    rng.shuffle(keys)
    options = dict(zip("ABCD", (scenario["options"][strategy] for strategy in keys)))
    coop_letter = "ABCD"[keys.index("COOPERATE")]
    indep_letter = "ABCD"[keys.index("INDEPENDENT")]
    first, second = ((coop_letter, indep_letter) if rng.randint(0, 1)
                     else (indep_letter, coop_letter))
    return options, first, second, first == coop_letter


def make_item_prompt(scenario: dict) -> tuple[str, dict]:
    options, first, second, coop_is_first = shuffle_item(scenario)
    labeled = "\n".join(f"{letter}. {text}" for letter, text in options.items())
    prompt = (
        "Blind instrument audit: review this hypothetical decision.\n"
        "SCENARIO:\n" + scenario["stem"] + "\n\n"
        "OPTIONS:\n" + labeled + "\n\n"
        f"Compare target alternatives FIRST={first} and SECOND={second}. "
        "Treat the other two options as distractors; evaluate their plausibility "
        "and any framing imbalance as well.\n\n" + ITEM_RUBRIC
    )
    metadata = {"options": options, "first": first, "second": second,
                "coop_is_first": coop_is_first}
    return prompt, metadata


def make_pair_prompt(human: dict, ai: dict) -> str:
    def render(s: dict) -> str:
        opts = "\n".join(f"Option {i}: {s['options'][strategy]}"
                         for i, strategy in enumerate(STRATEGIES, 1))
        return s["stem"] + "\n" + opts
    return ("Blind partner-variant equivalence review. These are two versions of a situation.\n"
            "VARIANT 1:\n" + render(human) + "\n\n"
            "VARIANT 2:\n" + render(ai) + "\n\n" + PAIR_RUBRIC)


def preflight(bank: dict, limit_templates: int) -> tuple[int, int]:
    groups = group_scenarios(bank)
    tids = sorted(groups)
    if limit_templates > 0:
        tids = tids[:limit_templates]
    for tid in tids:
        for partner in ("human", "ai"):
            scenario = groups[tid][partner]
            prompt, meta = make_item_prompt(scenario)
            if "SCENARIO:" not in prompt or "OPTIONS:" not in prompt:
                raise ValueError("Invalid item prompt")
            if meta["first"] == meta["second"] or set(meta["options"]) != set("ABCD"):
                raise ValueError("Invalid target shuffling")
            if meta["options"][meta["first"] if meta["coop_is_first"] else meta["second"]] != scenario["options"]["COOPERATE"]:
                raise ValueError("Cooperation-label mapping error")
            if "actor_payoff" in prompt or "partner_payoff" in prompt:
                raise ValueError("Payoff metadata leaked into reviewer prompt")
        if "VARIANT 2:" not in make_pair_prompt(groups[tid]["human"], groups[tid]["ai"]):
            raise ValueError("Invalid pair-review prompt")
    return len(tids) * 2, len(tids)


def parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            raise ValueError("No JSON object returned by reviewer")
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("Reviewer response is not a JSON object")
    return obj


def validate_item(obj: dict) -> None:
    for key in ("actor_relation", "partner_relation"):
        if obj.get(key) not in RELATIONS:
            raise ValueError(f"Invalid {key}: {obj.get(key)}")
    if obj.get("wording_favors") not in ("first", "second", "neither", "unclear"):
        raise ValueError("Invalid wording_favors")
    for field in ("framing_neutrality", "realism", "option_parity", "incentive_clarity", "choice_clarity"):
        score = obj.get("scores", {}).get(field)
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 4:
            raise ValueError(f"Invalid item score: {field}={score}")
    if not isinstance(obj.get("material_confounders"), list):
        raise ValueError("Missing material_confounders")
    if not all(isinstance(obj.get(field), str) for field in ("evidence", "suggested_repair")):
        raise ValueError("Missing evidence or suggested_repair")


def validate_pair(obj: dict) -> None:
    for field in ("semantic_equivalence", "wording_parity"):
        score = obj.get("scores", {}).get(field)
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 4:
            raise ValueError(f"Invalid pair score: {field}={score}")
    if not isinstance(obj.get("material_differences"), list):
        raise ValueError("Missing material_differences")
    if not all(isinstance(obj.get(field), str) for field in ("evidence", "suggested_repair")):
        raise ValueError("Missing pair evidence or suggested_repair")


def claimed_relation(s: dict, party: str) -> str:
    # The claimed payoff relation is never sent to the reviewer.
    try:
        p = s["payoff_spec"]
        c = float(p["COOPERATE"][f"{party}_payoff"])
        i = float(p["INDEPENDENT"][f"{party}_payoff"])
    except (KeyError, ValueError, TypeError):
        return "unclear"
    return "equal" if abs(c-i) <= 1e-9 else ("coop_better" if c > i else "indep_better")


def as_strategy_relation(rel: str, coop_is_first: bool) -> str:
    if rel in ("unclear", "equal"):
        return rel
    if rel == "first_better":
        return "coop_better" if coop_is_first else "indep_better"
    return "indep_better" if coop_is_first else "coop_better"


def audit_flags(s: dict, review: dict, coop_is_first: bool, pair_review: dict | None) -> list[str]:
    flags = []
    observed = {}
    for party in ("actor", "partner"):
        claimed = claimed_relation(s, party)
        observed[party] = as_strategy_relation(review[f"{party}_relation"], coop_is_first)
        if observed[party] != claimed:
            # Distinguish uncertainty from an actual inconsistent inference.
            flags.append(f"{party}_payoff_unclear" if observed[party] == "unclear"
                         else f"{party}_payoff_conflict:{claimed}_vs_{observed[party]}")
    if s.get("is_symmetric_control"):
        if any(x in ("coop_better", "indep_better") for x in observed.values()):
            flags.append("symmetric_control_conflict")
        elif "unclear" in observed.values():
            flags.append("symmetric_control_unclear")
    for metric, score in review["scores"].items():
        if score <= 2:
            flags.append(f"low_{metric}:{score}")
    fav = review["wording_favors"]
    if fav in ("first", "second"):
        favor_coop = (fav == "first") == coop_is_first
        flags.append("wording_favors_coop" if favor_coop else "wording_favors_independent")
    if pair_review:
        for metric, score in pair_review["scores"].items():
            if score <= 2:
                flags.append(f"partner_pair_low_{metric}:{score}")
    return flags


def load_latest_jsonl(path: Path, key: str) -> dict:
    records = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    record = json.loads(line)
                    records[record[key]] = record
                except (ValueError, KeyError):
                    continue
    return records


def append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def generate_reports(outdir: Path, scenarios: list[dict], bank_hash: str,
                     revision: str | None) -> dict:
    items = load_latest_jsonl(outdir / "scenario_reviews.jsonl", "id")
    pairs = load_latest_jsonl(outdir / "pair_reviews.jsonl", "template_id")
    rows = []
    for s in scenarios:
        record = items.get(s["id"])
        if not record or "review" not in record:
            continue
        review = record["review"]
        pair = pairs.get(s["template_id"], {}).get("review")
        coop_first = record["shuffle"]["coop_is_first"]
        flags = audit_flags(s, review, coop_first, pair)
        severe = sum(f.endswith("_conflict") or "_payoff_conflict:" in f or f.startswith("low_")
                     for f in flags)
        severity = "HIGH" if severe >= 2 or "symmetric_control_conflict" in flags else ("REVIEW" if flags else "PASS")
        rows.append({
            "id": s["id"], "template_id": s["template_id"], "partner": s["partner_type"],
            "condition": s["utility_condition"], "symmetric": s.get("is_symmetric_control", False),
            "severity": severity, "flag_count": len(flags), "flags": " | ".join(flags),
            "actor_claim": claimed_relation(s, "actor"),
            "actor_judgment": as_strategy_relation(review["actor_relation"], coop_first),
            "partner_claim": claimed_relation(s, "partner"),
            "partner_judgment": as_strategy_relation(review["partner_relation"], coop_first),
            **{f"score_{k}": v for k, v in review["scores"].items()},
            "pair_equivalence": pair["scores"]["semantic_equivalence"] if pair else "",
            "pair_wording_parity": pair["scores"]["wording_parity"] if pair else "",
            "confounders": "; ".join(map(str, review["material_confounders"])),
            "evidence": review["evidence"], "suggested_repair": review["suggested_repair"],
            "pair_differences": "; ".join(map(str, pair.get("material_differences", []))) if pair else "",
            "pair_repair": pair.get("suggested_repair", "") if pair else "",
            "human_adjudication_status": "pending", "final_disposition": "unadjudicated",
        })
    rows.sort(key=lambda r: ({"HIGH": 0, "REVIEW": 1, "PASS": 2}[r["severity"]],
                             -r["flag_count"], r["template_id"], r["partner"]))
    with (outdir / "review_queue.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(r["severity"] for r in rows)
    reviewed_pairs = sum("review" in p for p in pairs.values())
    summary = [
        "# Phase 1 — Blinded Qwen-32B Instrument Review", "",
        f"- Bank SHA-256: `{bank_hash}`", f"- Reviewer: `{MODEL_ID}` at revision `{revision}`",
        f"- Protocol: `{PROMPT_VERSION}`; harness: `{HARNESS_VERSION}`",
        f"- Reviewed items: **{len(rows)}/{len(scenarios)}**",
        f"- Reviewed partner pairs: **{reviewed_pairs}/{len(set(s['template_id'] for s in scenarios))}**",
        f"- Triage: **{counts['HIGH']} HIGH**, **{counts['REVIEW']} REVIEW**, **{counts['PASS']} PASS**", "",
        "## Scientific limits", "",
        "AI-assisted diagnostic review is not human scientific adjudication.",
        "Review prompts exclude strategy keys, author payoff metadata, utility labels, and behavioural results.",
        "The model's 'unclear' judgment flags insufficient textual evidence, **not** a demonstrated mismatch.",
        "HIGH is a triage priority, not proof that the scenario is invalid.",
        "All material issues require human review before the scenario bank can be frozen.",
        "No model cooperation or behavioural-choice assay was run.", "",
        "## Flagged items", "",
    ]
    for row in [r for r in rows if r["severity"] != "PASS"][:30]:
        summary += [f"### {row['id']} — {row['severity']}",
                    f"Flags: `{row['flags']}`", f"Evidence: {row['evidence']}",
                    f"Suggested repair: {row['suggested_repair']}", ""]
    if not rows:
        summary.append("No successful item reviews yet.")
    (outdir / "audit_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {"reviewed": len(rows), "pair_reviewed": reviewed_pairs,
            "high": counts["HIGH"], "review": counts["REVIEW"], "pass": counts["PASS"]}


@app.function(
    gpu=GPU_TYPE,
    timeout=10800,
    memory=32768,
    volumes={"/root/.cache/huggingface": cache_volume, str(OUT_ROOT): audit_volume},
    image=image,
)
def review_bank(limit_templates: int = 0) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    bank, bank_hash = load_bank(Path(BANK_REMOTE))
    pairs = group_scenarios(bank)
    ids = sorted(pairs)
    if limit_templates > 0:
        ids = ids[:limit_templates]
    scenarios = [pairs[tid][partner] for tid in ids for partner in ("human", "ai")]
    run_key = f"phase1_{bank_hash[:12]}_qwen25-32bi_{PROMPT_VERSION}"
    outdir = OUT_ROOT / run_key
    outdir.mkdir(parents=True, exist_ok=True)
    item_path, pair_path = outdir / "scenario_reviews.jsonl", outdir / "pair_reviews.jsonl"
    done_items = load_latest_jsonl(item_path, "id")
    done_pairs = load_latest_jsonl(pair_path, "template_id")
    outstanding_items = [s for s in scenarios if "review" not in done_items.get(s["id"], {})]
    outstanding_pairs = [tid for tid in ids if "review" not in done_pairs.get(tid, {})]
    if not outstanding_items and not outstanding_pairs:
        old = outdir / "manifest.json"
        prev = json.loads(old.read_text()) if old.exists() else {}
        return {"path": str(outdir), **generate_reports(outdir, scenarios, bank_hash,
                      prev.get("model_revision", MODEL_REVISION))}

    print(f"Qwen-32B review: {len(outstanding_items)} items and {len(outstanding_pairs)} pairs remaining")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, torch_dtype=torch.bfloat16,
        device_map="auto", low_cpu_mem_usage=True, attn_implementation="sdpa"
    ).eval()
    revision = getattr(model.config, "_commit_hash", None) or MODEL_REVISION
    cache_volume.commit()
    manifest = {
        "model": MODEL_ID, "model_revision": revision, "bank_hash": bank_hash,
        "bank_status": bank["status"], "harness_version": HARNESS_VERSION,
        "protocol": PROMPT_VERSION, "gpu": GPU_TYPE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "access_to_behavioral_results": False, "limit_templates": limit_templates,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    audit_volume.commit()

    def infer(prompt: str) -> dict:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        ids_t = tokenizer.apply_chat_template(messages, tokenize=True,
                  add_generation_prompt=True, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(ids_t, max_new_tokens=800, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id, eos_token_id=tokenizer.eos_token_id,
                    use_cache=True)
        generated = tokenizer.decode(output[0, ids_t.shape[-1]:], skip_special_tokens=True)
        del ids_t, output
        return parse_json_response(generated)

    for i, s in enumerate(outstanding_items, 1):
        try:
            prompt, shuffle = make_item_prompt(s)
            review = infer(prompt)
            validate_item(review)
            record = {
                "id": s["id"], "template_id": s["template_id"], "review": review,
                "shuffle": shuffle, "reviewer": MODEL_ID,
                "prompt_sha256": digest(prompt.encode()),
            }
            print(f"ITEM {i}/{len(outstanding_items)} {s['id']} OK")
        except Exception as exc:
            record = {"id": s["id"], "template_id": s["template_id"], "error": str(exc)}
            print(f"ITEM {i}/{len(outstanding_items)} {s['id']} ERROR {exc}")
        append_jsonl(item_path, record)
        if i % 4 == 0:
            audit_volume.commit()

    for i, tid in enumerate(outstanding_pairs, 1):
        try:
            prompt = make_pair_prompt(pairs[tid]["human"], pairs[tid]["ai"])
            review = infer(prompt)
            validate_pair(review)
            record = {"template_id": tid, "review": review, "reviewer": MODEL_ID,
                      "prompt_sha256": digest(prompt.encode())}
            print(f"PAIR {i}/{len(outstanding_pairs)} {tid} OK")
        except Exception as exc:
            record = {"template_id": tid, "error": str(exc)}
            print(f"PAIR {i}/{len(outstanding_pairs)} {tid} ERROR {exc}")
        append_jsonl(pair_path, record)
        if i % 4 == 0:
            audit_volume.commit()

    report = generate_reports(outdir, scenarios, bank_hash, revision)
    audit_volume.commit()
    return {"path": str(outdir), **report}


@app.local_entrypoint()
def main(authorize_paid_run: bool = False, limit_templates: int = 0) -> None:
    if limit_templates < 0 or limit_templates > 30:
        raise ValueError("--limit-templates must be between 0 (all) and 30")
    bank, bank_hash = load_bank(BANK_LOCAL)
    count_items, count_pairs = preflight(bank, limit_templates)
    print(f"BANK: 60 draft scenarios / 30 paired templates, SHA-256 {bank_hash}")
    print(f"PREFLIGHT: {count_items} item prompts, {count_pairs} pair prompts verified")
    print(f"REVIEWER: {MODEL_ID}@{MODEL_REVISION}, GPU={GPU_TYPE}, {PROMPT_VERSION}")
    print("Blinded semantic instrument audit only; no behavioural inference, no bank mutation.")
    if not authorize_paid_run:
        print("DRY RUN — no GPU dispatched. Pass --authorize-paid-run for billable audit.")
        return
    print("PAID AUDIT AUTHORIZED — dispatching to Modal A100 GPU")
    result = review_bank.remote(limit_templates)
    print("AUDIT RESULT", json.dumps(result, indent=2))
    name = Path(result["path"]).name
    print(f"Download: modal volume get llm-coop-phase1-instrument-audits {name}/ <destination_directory>")
