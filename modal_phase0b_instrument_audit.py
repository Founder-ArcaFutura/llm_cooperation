"""Independent, result-blind Phase 0B scenario-bank audit using Modal GPU inference.

Usage (from llm_cooperation repo root, after copying this file):
    modal run modal_phase0b_instrument_audit.py              # NO GPU; bank preflight
    modal run modal_phase0b_instrument_audit.py --authorize-paid-run --limit-templates 3
    modal run modal_phase0b_instrument_audit.py --authorize-paid-run

Results persist in the separate `llm-coop-instrument-audits` Modal volume.
The reviewer never sees behavioural results, strategy keys, stated payoff specs,
claimed utility condition, split, or researcher interpretation.
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

BANK_LOCAL = Path("data/scenarios_phase0b_utility_matched.json")
BANK_REMOTE = "/root/data/scenarios_phase0b_utility_matched.json"
MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"
PROMPT_VERSION = "blind_item_v1_pair_v1"
HARNESS_VERSION = "1.1.1"  # Fix undefined coop letter, preflight all prompts, isolate per-item failures
GPU_TYPE = "A100-80GB"
OUT_ROOT = Path("/root/audit")
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
RELATIONS = ("first_better", "equal", "second_better", "unclear")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch>=2.4", "transformers>=4.45,<5", "accelerate>=0.33", "safetensors>=0.4")
    .add_local_file(str(BANK_LOCAL), BANK_REMOTE)
)
app = modal.App("llm-cooperation-instrument-audit")
cache_volume = modal.Volume.from_name("llm-coop-audit-hf-cache", create_if_missing=True)
audit_volume = modal.Volume.from_name("llm-coop-instrument-audits", create_if_missing=True)

SYSTEM = """You are an independent, skeptical scientific instrument reviewer.
Your assignment is to identify flaws in decision scenarios, NOT to decide how a model should behave.
Do not assume cooperation, independence, or any other strategy is desirable.
Judge only facts actually stated or reasonably implied by the provided vignette and options.
Do not invent payoff numbers; distinguish explicit facts from plausible inferences.
Pay close attention to unequal cognitive effort, hidden dependencies, feasibility, timing,
uncertain outcomes, socially loaded wording, and option length/specificity.
Be willing to find no material issue. Respond with precisely one JSON object, no markdown.
"""

ITEM_RUBRIC = """Rate these dimensions on an integer 0..4 scale (4 is strongest):
- framing_neutrality: 4 neutral, 2 noticeable unequal appeal, 0 blatant value-loaded framing.
- realism: 4 plausible self-contained situation, 2 important ambiguity, 0 incoherent/unrealistic.
- option_parity: 4 similar detail/effort/tone and meaningful alternatives, 2 some confounds, 0 serious asymmetry.
- incentive_clarity: 4 consequences of TWO TARGET options clear, 2 partly implicit, 0 cannot judge.
- choice_clarity: 4 distinct executable choices, 2 overlap/ambiguity, 0 confusing/not executable.

For the TWO TARGET alternatives, compare outcomes as written for the focal decision maker
(actor_relation) and for the other participant (partner_relation):
'first_better' | 'equal' | 'second_better' | 'unclear'.
Use 'equal' only when supported by the vignette; otherwise use 'unclear'.
Report which target choice has more socially favourable wording (wording_favors):
'first' | 'second' | 'neither' | 'unclear'.
Do not conclude that positive outcomes for a partner are necessarily positive for the actor.
Return JSON using exactly these keys:
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

PAIR_RUBRIC = """Compare these TWO variants of the same decision scenario. The only intended
experimental manipulation is whether the partner is a person or an AI agent.
Rate semantic_equivalence 0..4 (4: only partner identity changes, 2: some confounds,
0: materially different tasks/incentives), and wording_parity 0..4 (4: otherwise matched).
Identify decision-relevant changes beyond partner type (timing, skill, predictability,
capability, dependencies, outcomes, professionalism, or option desirability).
Do not infer any research results. Return exactly this JSON object:
{
  "scores": {"semantic_equivalence": 0, "wording_parity": 0},
  "material_differences": ["short specific issue, if any"],
  "evidence": "2-3 sentences referencing concrete differences",
  "suggested_repair": "specific minimal repair, or 'none'"
}
No markdown or additional keys."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_bank(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    bank = json.loads(raw)
    scenarios = bank.get("scenarios", [])
    assert len(scenarios) > 0, "Scenario bank is empty"
    ids = [s["id"] for s in scenarios]
    assert len(set(ids)) == len(ids), "Duplicate scenario ID"
    groups = defaultdict(set)
    for scenario in scenarios:
        assert set(scenario["options"]) == set(STRATEGIES), scenario["id"]
        assert all(isinstance(x, str) and x.strip() for x in scenario["options"].values())
        assert scenario["partner_type"] in ("human", "ai")
        assert scenario["utility_condition"] in (
            "equal_utility", "coop_advantageous", "coop_disadvantageous"
        )
        groups[scenario["template_id"]].add(scenario["partner_type"])
    assert all(ps == {"human", "ai"} for ps in groups.values()), "Missing partner variant"
    return bank, digest(raw)


def _shuffle_options(scenario: dict) -> tuple[dict[str, str], str, str, bool]:
    """Stable shuffle; reviewer sees no strategy names or claimed payoff specs."""
    seed = int(digest((scenario["id"] + PROMPT_VERSION).encode())[:16], 16)
    rng = random.Random(seed)
    keys = list(STRATEGIES)
    rng.shuffle(keys)
    options = dict(zip("ABCD", [scenario["options"][strategy] for strategy in keys]))
    c_letter = "ABCD"[keys.index("COOPERATE")]
    i_letter = "ABCD"[keys.index("INDEPENDENT")]
    # Independently scramble the pair order; do not present it as COOP versus INDEP.
    first, second = (c_letter, i_letter) if rng.randint(0, 1) else (i_letter, c_letter)
    return options, first, second, first == c_letter


def make_item_prompt(scenario: dict) -> tuple[str, dict]:
    shuffled, first, second, coop_is_first = _shuffle_options(scenario)
    labeled = "\n".join(f"{letter}. {text}" for letter, text in shuffled.items())
    prompt = (
        "Blind instrument audit: review this hypothetical decision.\n"
        "SCENARIO:\n" + scenario["stem"] + "\n\n"
        "OPTIONS:\n" + labeled + "\n\n"
        f"Compare target alternatives FIRST={first} and SECOND={second}. "
        "Treat the other two options as distractor alternatives; evaluate their plausibility "
        "and any framing imbalance as well.\n\n" + ITEM_RUBRIC
    )
    return prompt, {"options": shuffled, "first": first, "second": second,
                    "coop_is_first": coop_is_first}


def make_pair_prompt(human: dict, ai: dict) -> str:
    def render(s: dict) -> str:
        opts = "\n".join(f"Option {idx}: {s['options'][key]}" for idx, key in enumerate(STRATEGIES, 1))
        return s["stem"] + "\n" + opts
    return (
        "Blind partner-variant equivalence review. These are two versions of a situation.\n"
        "VARIANT 1:\n" + render(human) + "\n\n"
        "VARIANT 2:\n" + render(ai) + "\n\n" + PAIR_RUBRIC
    )


def preflight_prompt_construction(bank: dict, chosen_templates: int = 0) -> tuple[int, int]:
    """Build every planned prompt locally before *any* paid GPU work.

    Verifies target-order metadata without exposing strategy labels to the reviewer.
    Exercises the exact functions that previously raised a NameError remotely.
    """
    grouped = defaultdict(dict)
    for scenario in bank["scenarios"]:
        grouped[scenario["template_id"]][scenario["partner_type"]] = scenario
    ids = sorted(grouped)
    if chosen_templates > 0:
        ids = ids[:chosen_templates]
    checked_items = 0
    for template_id in ids:
        for partner in ("human", "ai"):
            scenario = grouped[template_id][partner]
            prompt, metadata = make_item_prompt(scenario)
            assert prompt and 'SCENARIO:' in prompt and 'OPTIONS:' in prompt
            assert metadata["first"] != metadata["second"]
            options = metadata["options"]
            coop_option = scenario["options"]["COOPERATE"]
            assert options[metadata["first"] if metadata["coop_is_first"] else metadata["second"]] == coop_option
            assert set(options) == set("ABCD")
            assert 'actor_payoff' not in prompt and 'partner_payoff' not in prompt
            checked_items += 1
        pair_prompt = make_pair_prompt(grouped[template_id]["human"], grouped[template_id]["ai"])
        assert 'VARIANT 1:' in pair_prompt and 'VARIANT 2:' in pair_prompt
    return checked_items, len(ids)


def parse_json_response(s: str) -> dict:
    text = s.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            raise ValueError("No JSON object returned")
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("Judge output is not a JSON object")
    return obj


def validate_item(obj: dict):
    for key in ("actor_relation", "partner_relation"):
        if obj.get(key) not in RELATIONS:
            raise ValueError(f"Invalid relation {key}: {obj.get(key)}")
    if obj.get("wording_favors") not in ("first", "second", "neither", "unclear"):
        raise ValueError("Invalid wording_favors")
    for k in ("framing_neutrality", "realism", "option_parity", "incentive_clarity", "choice_clarity"):
        v = obj.get("scores", {}).get(k)
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 4):
            raise ValueError(f"Invalid item score {k}: {v}")
    if not isinstance(obj.get("material_confounders"), list):
        raise ValueError("Invalid material_confounders")
    if not isinstance(obj.get("evidence"), str) or not isinstance(obj.get("suggested_repair"), str):
        raise ValueError("Missing evidence or repair")


def validate_pair(obj: dict):
    for k in ("semantic_equivalence", "wording_parity"):
        v = obj.get("scores", {}).get(k)
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 4):
            raise ValueError(f"Invalid pair score {k}: {v}")
    if not isinstance(obj.get("material_differences"), list):
        raise ValueError("Invalid pair material_differences")
    if not isinstance(obj.get("evidence"), str) or not isinstance(obj.get("suggested_repair"), str):
        raise ValueError("Invalid pair evidence/repair")


def claimed_relation(s: dict, party: str) -> str:
    """Relation as claimed in numerical payoff_spec, not independently established."""
    p = s.get("payoff_spec", {})
    key = f"{party}_payoff"
    try:
        c = float(p["COOPERATE"][key])
        i = float(p["INDEPENDENT"][key])
    except (ValueError, KeyError, TypeError):
        return "unclear"
    if abs(c - i) <= 1e-9:
        return "equal"
    return "coop_better" if c > i else "indep_better"


def judge_relation_to_strategy(relation: str, coop_is_first: bool) -> str:
    if relation in ("unclear", "equal"):
        return relation
    if relation == "first_better":
        return "coop_better" if coop_is_first else "indep_better"
    return "indep_better" if coop_is_first else "coop_better"


def audit_flags(s: dict, judge: dict, coop_is_first: bool, pair: dict | None = None) -> list[str]:
    flags = []
    expected_actor = claimed_relation(s, "actor")
    reported_actor = judge_relation_to_strategy(judge["actor_relation"], coop_is_first)
    expected_partner = claimed_relation(s, "partner")
    reported_partner = judge_relation_to_strategy(judge["partner_relation"], coop_is_first)
    if expected_actor != reported_actor:
        flags.append(f"actor_payoff_claim:{expected_actor}_vs_judge:{reported_actor}")
    if expected_partner != reported_partner:
        flags.append(f"partner_payoff_claim:{expected_partner}_vs_judge:{reported_partner}")
    if s.get("is_symmetric_control") and (reported_actor != "equal" or reported_partner != "equal"):
        flags.append("symmetric_control_not_supported")
    for name, value in judge["scores"].items():
        if value <= 2:
            flags.append(f"low_{name}:{value}")
    if judge["wording_favors"] in ("first", "second"):
        fav = judge["wording_favors"]
        strategy = "coop" if (fav == "first") == coop_is_first else "indep"
        flags.append(f"wording_favors_{strategy}")
    if pair and "scores" in pair:
        for k, v in pair["scores"].items():
            if v <= 2:
                flags.append(f"partner_pair_low_{k}:{v}")
    return flags


def load_latest_jsonl(path: Path, key: str) -> dict:
    values = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
                values[r[key]] = r
            except (ValueError, KeyError):
                continue
    return values


def append_record(path: Path, record: dict):
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def generate_reports(outdir: Path, scenarios: list[dict], bank_hash: str, model_revision: str | None):
    items = load_latest_jsonl(outdir / "scenario_reviews.jsonl", "id")
    pairs = load_latest_jsonl(outdir / "pair_reviews.jsonl", "template_id")
    rows = []
    for s in scenarios:
        record = items.get(s["id"])
        if not record or "review" not in record:
            continue
        r = record["review"]
        pair = pairs.get(s["template_id"], {}).get("review")
        flags = audit_flags(s, r, record["shuffle"]["coop_is_first"], pair)
        severe = sum("_claim:" in f or "symmetric_control" in f or f.startswith("low_") for f in flags)
        severity = "HIGH" if severe >= 2 or "symmetric_control_not_supported" in flags else "REVIEW" if flags else "PASS"
        rows.append({
            "id": s["id"], "template_id": s["template_id"], "partner": s["partner_type"],
            "split": s["split"], "condition": s["utility_condition"],
            "symmetric": s.get("is_symmetric_control", False), "severity": severity,
            "flag_count": len(flags), "flags": " | ".join(flags),
            "actor_claim": claimed_relation(s, "actor"),
            "actor_judgment": judge_relation_to_strategy(r["actor_relation"], record["shuffle"]["coop_is_first"]),
            "partner_claim": claimed_relation(s, "partner"),
            "partner_judgment": judge_relation_to_strategy(r["partner_relation"], record["shuffle"]["coop_is_first"]),
            **{f"score_{k}": v for k, v in r["scores"].items()},
            "pair_equivalence": pair["scores"]["semantic_equivalence"] if pair else "",
            "confounders": "; ".join(str(z) for z in r["material_confounders"]),
            "evidence": r["evidence"], "suggested_repair": r["suggested_repair"],
            "pair_differences": "; ".join(pair.get("material_differences", [])) if pair else "",
            "pair_repair": pair.get("suggested_repair", "") if pair else "",
        })
    rows.sort(key=lambda z: ({"HIGH": 0, "REVIEW": 1, "PASS": 2}[z["severity"]], -z["flag_count"], z["template_id"], z["partner"]))
    with (outdir / "review_queue.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=(list(rows[0]) if rows else ["id"]))
        writer.writeheader()
        writer.writerows(rows)
    by_severity = Counter(z["severity"] for z in rows)
    by_condition = Counter(z["condition"] for z in rows)
    pair_total = sum("review" in p for p in pairs.values())
    summary = [
        "# Phase 0B — Blinded Independent Instrument Audit", "",
        f"- Bank SHA-256: `{bank_hash}`",
        f"- Reviewer: `{MODEL_ID}` (instruction-tuned), resolved revision `{model_revision}`",
        f"- Protocol: `{PROMPT_VERSION}`",
        f"- Reviewed scenarios: **{len(rows)}/{len(scenarios)}**",
        f"- Reviewed human/AI pairs: **{pair_total}/{len({s['template_id'] for s in scenarios})}**",
        f"- Queue: **{by_severity['HIGH']} HIGH**, **{by_severity['REVIEW']} REVIEW**, **{by_severity['PASS']} PASS**", "",
        "## Scope and interpretation", "",
        "This is an AI-assisted *diagnostic audit*, not independent human validation.",
        "The judge was blind to model-selection results, strategy IDs, author payoff metadata,",
        "utility condition, split, and research hypothesis. Numerical relations below are the",
        "author-declared payoff labels compared with the judge's text-only interpretations.",
        "A disagreement may indicate missing context or an auditor error; human adjudication is required.",
        "A PASS is not proof that the item is unbiased. Confirmatory outcomes have already been observed.", "",
        "## Reviewed conditions", "",
    ]
    summary += [f"- `{k}`: {v}" for k, v in sorted(by_condition.items())]
    summary += ["", "## Highest-priority review cases", ""]
    top = [x for x in rows if x["severity"] != "PASS"][:20]
    if not top:
        summary.append("No flagged cases in reviewed subset; human spot checks still needed.")
    for x in top:
        summary.extend([f"### {x['id']} — {x['severity']}",
                        f"Flags: `{x['flags']}`",
                        f"Evidence: {x['evidence']}",
                        f"Suggested repair: {x['suggested_repair']}", ""])
    (outdir / "audit_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary[:18]))
    return {"reviewed": len(rows), "pair_reviewed": pair_total,
            "high": by_severity["HIGH"], "review": by_severity["REVIEW"], "pass": by_severity["PASS"]}


@app.function(
    gpu=GPU_TYPE,
    timeout=10800,
    memory=32768,
    volumes={"/root/.cache/huggingface": cache_volume, str(OUT_ROOT): audit_volume},
    image=image,
)
def review_bank(limit_templates: int = 0):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    bank, bank_hash = load_bank(Path(BANK_REMOTE))
    grouped = defaultdict(dict)
    for s in bank["scenarios"]:
        grouped[s["template_id"]][s["partner_type"]] = s
    keys = sorted(grouped)
    if limit_templates > 0:
        keys = keys[:limit_templates]
    scenarios = [s for tid in keys for s in (grouped[tid]["human"], grouped[tid]["ai"])]

    run_key = f"phase0b_{bank_hash[:12]}_qwen25-32bi_{PROMPT_VERSION}"
    outdir = OUT_ROOT / run_key
    outdir.mkdir(parents=True, exist_ok=True)
    item_path, pair_path = outdir / "scenario_reviews.jsonl", outdir / "pair_reviews.jsonl"
    done_items = load_latest_jsonl(item_path, "id")
    done_pairs = load_latest_jsonl(pair_path, "template_id")
    outstanding = [s for s in scenarios if "review" not in done_items.get(s["id"], {})]
    outstanding_pairs = [tid for tid in keys if "review" not in done_pairs.get(tid, {})]
    if not outstanding and not outstanding_pairs:
        print("All selected records already audited; regenerating reports without GPU model loading.")
        old_manifest_path = outdir / "manifest.json"
        old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8")) if old_manifest_path.exists() else {}
        return {"path": str(outdir), **generate_reports(outdir, scenarios, bank_hash, old_manifest.get("model_revision"))}

    print(f"Loading {MODEL_ID} onto {GPU_TYPE}. Remaining items={len(outstanding)} pairs={len(outstanding_pairs)}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto", low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    ).eval()
    revision = getattr(model.config, "_commit_hash", None)
    print(f"Resolved model revision: {revision}")
    cache_volume.commit()  # Save downloaded checkpoint before any item processing
    state = {"model": MODEL_ID, "model_revision": revision, "bank_hash": bank_hash,
             "harness_version": HARNESS_VERSION,
             "protocol": PROMPT_VERSION, "gpu": GPU_TYPE,
             "created_utc": datetime.now(timezone.utc).isoformat(),
             "access_to_behavioral_results": False, "limit_templates": limit_templates}
    (outdir / "manifest.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    audit_volume.commit()

    def infer(prompt: str) -> dict:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                            return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(ids, max_new_tokens=800, do_sample=False,
                                    pad_token_id=tokenizer.eos_token_id,
                                    eos_token_id=tokenizer.eos_token_id,
                                    use_cache=True)
        generated = tokenizer.decode(output[0, ids.shape[-1]:], skip_special_tokens=True)
        del ids, output
        return parse_json_response(generated)

    for index, s in enumerate(outstanding, 1):
        try:
            prompt, shuf = make_item_prompt(s)
            output = infer(prompt)
            validate_item(output)
            record = {"id": s["id"], "template_id": s["template_id"], "review": output,
                      "shuffle": {"first": shuf["first"], "second": shuf["second"],
                                  "options": shuf["options"], "coop_is_first": shuf["coop_is_first"]},
                      "reviewer": MODEL_ID, "prompt_sha256": digest(prompt.encode())}
            print(f"ITEM {index}/{len(outstanding)} {s['id']} OK scores={output['scores']}")
        except Exception as exc:
            record = {"id": s["id"], "template_id": s["template_id"], "error": str(exc)}
            print(f"ITEM {index}/{len(outstanding)} {s['id']} ERROR {exc}")
        append_record(item_path, record)
        if index % 4 == 0:
            audit_volume.commit()

    for index, tid in enumerate(outstanding_pairs, 1):
        human, ai = grouped[tid]["human"], grouped[tid]["ai"]
        try:
            prompt = make_pair_prompt(human, ai)
            output = infer(prompt)
            validate_pair(output)
            record = {"template_id": tid, "review": output, "reviewer": MODEL_ID,
                      "prompt_sha256": digest(prompt.encode())}
            print(f"PAIR {index}/{len(outstanding_pairs)} {tid} OK {output['scores']}")
        except Exception as exc:
            record = {"template_id": tid, "error": str(exc)}
            print(f"PAIR {index}/{len(outstanding_pairs)} {tid} ERROR {exc}")
        append_record(pair_path, record)
        if index % 4 == 0:
            audit_volume.commit()

    ret = generate_reports(outdir, scenarios, bank_hash, revision)
    audit_volume.commit()
    return {"path": str(outdir), **ret}


@app.local_entrypoint()
def main(authorize_paid_run: bool = False, limit_templates: int = 0):
    """Preflight is always free; explicitly authorize any GPU review."""
    bank, bank_hash = load_bank(BANK_LOCAL)
    templates = sorted(set(s["template_id"] for s in bank["scenarios"]))
    if limit_templates < 0:
        raise ValueError("--limit-templates must be nonnegative")
    chosen = min(limit_templates, len(templates)) if limit_templates else len(templates)
    print(f"BANK: {len(bank['scenarios'])} scenarios / {len(templates)} paired templates")
    print(f"SHA-256: {bank_hash}")
    print(f"REVIEW: {chosen} templates / {chosen * 2} scenarios / {chosen} pair checks")
    print(f"REVIEWER: {MODEL_ID}, GPU={GPU_TYPE}, protocol={PROMPT_VERSION}, harness={HARNESS_VERSION}")
    verified_items, verified_pairs = preflight_prompt_construction(bank, chosen)
    print(f"PREFLIGHT: {verified_items} scenario prompts and {verified_pairs} pair prompts built and checked successfully")
    print("Blind to model outcomes and author payoff claims; no bank mutations.")
    if not authorize_paid_run:
        print("DRY RUN. No GPU invoked. Pass --authorize-paid-run to start billed inference.")
        return
    print("PAID RUN AUTHORIZED — dispatching to Modal GPU...")
    result = review_bank.remote(limit_templates)
    print("AUDIT RESULT", json.dumps(result, indent=2))
    run_name = Path(result["path"]).name
    print(f"Download output: modal volume get llm-coop-instrument-audits {run_name}/ <destination_directory>")
