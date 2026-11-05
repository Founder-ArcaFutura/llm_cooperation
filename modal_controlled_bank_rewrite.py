"""Model-authored Phase 0B action rewrites with fail-closed tokenizer controls.

This is a generator of PROVISIONAL candidates, not a scientific freeze.
Nothing runs on paid GPU without --authorize-paid-run. The source bank is never
modified. Download the generated candidates for independent semantic review.

Pilot:
  modal run modal_controlled_bank_rewrite.py --limit 6 --authorize-paid-run --run-name pilot01
Full:
  modal run modal_controlled_bank_rewrite.py --limit 124 --authorize-paid-run --run-name full01
Download:
  modal volume get llm-coop-controlled-rewrites full01 ./research/controlled_rewrites/full01
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import modal

MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
MEASUREMENT_TOKENIZER = "Qwen/Qwen2.5-1.5B"
MEASUREMENT_REVISION = "8faed761d45a263340a0528343f099c05c9a4323"
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
BANKS = ("A", "B", "C")
RUN_VOLUME = modal.Volume.from_name("llm-coop-controlled-rewrites", create_if_missing=True)
HF_CACHE = modal.Volume.from_name("llm-coop-hf-cache", create_if_missing=True)
IMAGE = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("vllm==0.11.0", "transformers==4.57.1", "huggingface_hub==0.35.3")
)
app = modal.App("llm-cooperation-controlled-bank-rewriter", image=IMAGE)

STYLES = {
    "A": (
        "Stay relatively close to the original meaning and concrete operations, "
        "but freely rewrite all four descriptions as necessary for natural, "
        "closely length-matched options."
    ),
    "B": (
        "Produce genuinely fresh language: change sentence construction, verb "
        "choices, and wording while retaining the same operational actions. "
        "Avoid repeating the original sentence skeletons."
    ),
    "C": (
        "Write a distinct independent paraphrase, beginning from the original "
        "scenario rather than Bank A or B. Use different grammatical patterns "
        "and synonyms from the source, without introducing new implications."
    ),
}

SYSTEM = """You are an expert in experimental psychometrics and scientific item writing.
Rewrite the FOUR alternative actions of ONE decision scenario as a coordinated set.

Scientific invariants:
- Keep COOPERATE as actual coordination / shared benefit with the stated partner.
- Keep INDEPENDENT as acting alone without providing the partner's benefit.
- Keep COMPETE_EXPLOIT as the specific competitive/exploitative action.
- Keep DISENGAGE as declining, stopping or postponing the original task.
- Preserve concrete actions, agents, partner type, costs, tradeoffs, time,
  risks, and payoff distinctions; do not introduce new incentives or claims.
- Produce grammatical, idiomatic English. NO filler phrases such as
  'exactly first', 'according in order to', or repeated 'until'.
- Length-match the four action descriptions according to feedback. They must
  differ by at most one token under a separate Qwen2.5 tokenizer. Full-prompt
  tokenization must also differ by at most one token.
- Do not paste an original description unchanged. If another bank's wording
  is supplied as a collision reference, write independently from ORIGINAL.
- Output ONLY a JSON object with precisely four STRING fields:
  COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE.
No Markdown, explanation, commentary, or alternative versions.
"""

BAD_PATTERNS = (
    re.compile(r"\baccording in order to\b", re.I),
    re.compile(r"\bexactly (?:first|until)\b", re.I),
    re.compile(r"\buntil\b.{0,110}\buntil\b", re.I),
    re.compile(r"\bin order to to\b", re.I),
    re.compile(r"\bthe the\b", re.I),
)


def _json_object(text: str) -> dict[str, str] | None:
    """Fail if output isn't a well-formed four-strategy JSON object."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^\s*```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or set(obj) != set(STRATEGIES):
        return None
    if not all(isinstance(obj[x], str) and obj[x].strip() for x in STRATEGIES):
        return None
    return {x: obj[x].strip() for x in STRATEGIES}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _score_candidate(tokenizer, scenario: dict, options: dict, earlier: dict) -> dict:
    lengths = {}
    full_lengths = {}
    issues = []
    stem = scenario["stem"].strip()
    for label in STRATEGIES:
        action = options[label]
        lengths[label] = len(tokenizer.encode(action, add_special_tokens=False))
        prompt = f"{stem}\n\nAction: {action}\nDecision:"
        full_lengths[label] = len(tokenizer.encode(prompt, add_special_tokens=False))
        if any(p.search(action) for p in BAD_PATTERNS):
            issues.append(f"{label}: mechanical-padding phrasing")
        for previous_bank, previous_opts in earlier.items():
            prior = previous_opts[label]
            if action.casefold() == prior.casefold():
                issues.append(f"{label}: exact duplicate of Bank {previous_bank}")
            # A high Jaccard similarity is only an operational diversity filter,
            # not a certificate of semantic identity or distinctness.
            wordset, priorset = _words(action), _words(prior)
            similarity = len(wordset & priorset) / max(1, len(wordset | priorset))
            if similarity > 0.85:
                issues.append(f"{label}: excessive lexical overlap with Bank {previous_bank} ({similarity:.2f})")
    if len(set(options.values())) != 4:
        issues.append("four strategies not textually distinct")
    span = max(lengths.values()) - min(lengths.values())
    full_span = max(full_lengths.values()) - min(full_lengths.values())
    if span > 1:
        issues.append(f"action token span={span}; lengths={lengths}")
    if full_span > 1:
        issues.append(f"full prompt token span={full_span}; lengths={full_lengths}")
    return {
        "accepted_automatic_constraints": not issues,
        "action_tokens": lengths,
        "full_prompt_tokens": full_lengths,
        "issues": issues,
        "semantic_review": "UNADJUDICATED",
    }


def _generate_set(llm, generation_tokenizer, measurement_tokenizer, scenario, bank, previous, max_attempts):
    from vllm import SamplingParams

    original = {s: scenario["options"][s] for s in STRATEGIES}
    target = max(len(measurement_tokenizer.encode(t, add_special_tokens=False)) for t in original.values())
    feedback = []
    last = None
    for attempt in range(1, max_attempts + 1):
        instructions = {
            "bank": bank,
            "style": STYLES[bank],
            "scenario_id": scenario["id"],
            "partner_type": scenario["partner_type"],
            "scenario": scenario["stem"],
            "original_actions": original,
            "original_payoffs": scenario.get("payoff_spec"),
            "length_target_hint_per_action": f"approximately {target} Qwen2.5 tokens",
            "other_bank_wording_to_avoid": previous,
            "prior_validation_feedback": feedback[-2:],
        }
        rendered = generation_tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": json.dumps(instructions, ensure_ascii=False)}],
            tokenize=False, add_generation_prompt=True,
        )
        generated = llm.generate(
            [rendered],
            SamplingParams(temperature=0.55 if attempt == 1 else 0.40,
                           top_p=0.9, max_tokens=650),
            use_tqdm=False,
        )[0].outputs[0].text
        options = _json_object(generated)
        if options is None:
            feedback.append(["Output was not valid four-field JSON. Return JSON only."])
            last = {"accepted_automatic_constraints": False, "issues": feedback[-1],
                    "raw_output_excerpt": generated[:500], "attempts": attempt,
                    "semantic_review": "UNADJUDICATED"}
            continue
        report = _score_candidate(measurement_tokenizer, scenario, options, previous)
        last = {"options": options, "validation": report, "attempts": attempt,
                "semantic_review": "UNADJUDICATED"}
        if report["accepted_automatic_constraints"]:
            last["accepted_automatic_constraints"] = True
            return last
        feedback.append(report["issues"])
    if last is None:
        last = {"issues": ["No model response"], "attempts": max_attempts}
    last["accepted_automatic_constraints"] = False
    return last


@app.function(gpu="H100", timeout=14400, retries=0,
              volumes={"/hf-cache": HF_CACHE, "/runs": RUN_VOLUME})
def generate_candidates(source_bytes: bytes, source_sha256: str, start: int, limit: int,
                        run_name: str, max_attempts: int):
    os.environ["HF_HOME"] = "/hf-cache"
    from huggingface_hub import HfApi
    from transformers import AutoTokenizer
    from vllm import LLM

    if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
        raise ValueError("Source file transport checksum mismatch")
    data = json.loads(source_bytes.decode("utf-8"))
    scenarios = data["scenarios"]
    if len(scenarios) != 124:
        raise ValueError("Expected the authoritative 124-scenario Phase 0B bank")
    selected = scenarios[start:start + limit]
    target = Path("/runs") / run_name
    if target.exists():
        raise FileExistsError(f"Run folder already exists: {target}; choose a new --run-name")
    target.mkdir(parents=True)
    (target / "records").mkdir()
    model_sha = HfApi().model_info(MODEL_ID).sha
    measure_tokenizer = AutoTokenizer.from_pretrained(
        MEASUREMENT_TOKENIZER, revision=MEASUREMENT_REVISION,
        trust_remote_code=False,
    )
    llm = LLM(model=MODEL_ID, revision=model_sha, dtype="auto",
              tensor_parallel_size=1, gpu_memory_utilization=0.85,
              max_model_len=4096)
    generation_tokenizer = llm.get_tokenizer()
    HF_CACHE.commit()

    counts = {bank: {"accepted": 0, "unresolved": 0} for bank in BANKS}
    results = {bank: [] for bank in BANKS}
    unresolved = []
    try:
        for index, scenario in enumerate(selected, start=start):
            # Each bank is generated from the authoritative original only.
            # Prior-bank text is used only to reject verbatim/near duplicates.
            prior = {}
            for bank in BANKS:
                record = _generate_set(
                    llm, generation_tokenizer, measure_tokenizer,
                    scenario, bank, prior, max_attempts,
                )
                row = {
                    "scenario_id": scenario["id"], "source_index": index,
                    "bank": bank, **record,
                }
                filename = f"{index:03d}_{bank}.json"
                (target / "records" / filename).write_text(
                    json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                if record["accepted_automatic_constraints"]:
                    edited = copy.deepcopy(scenario)
                    edited["original_options"] = copy.deepcopy(scenario["options"])
                    edited["options"] = record["options"]
                    edited["bank_variant"] = f"bank_{bank.lower()}"
                    edited["paraphrase_id"] = f"{scenario['id']}_bank_{bank.lower()}"
                    results[bank].append(edited)
                    prior[bank] = record["options"]
                    counts[bank]["accepted"] += 1
                else:
                    counts[bank]["unresolved"] += 1
                    unresolved.append({"scenario_id": scenario["id"], "bank": bank,
                                       "issues": record.get("validation", record).get("issues", [])})
                print(f"scenario {index + 1}/{len(scenarios)} bank {bank}: "
                      f"{'automatic constraints passed' if record['accepted_automatic_constraints'] else 'UNRESOLVED'}",
                      flush=True)
            if (index - start + 1) % 10 == 0:
                RUN_VOLUME.commit()
    finally:
        manifest = {
            "version": "model_generated_controlled_banks_candidate_v1",
            "status": "PROVISIONAL_PENDING_INDEPENDENT_SEMANTIC_REVIEW",
            "run_name": run_name, "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": source_sha256, "source_path": "data/scenarios_phase0b_utility_matched.json",
            "model": MODEL_ID, "resolved_model_sha": model_sha,
            "measurement_tokenizer": MEASUREMENT_TOKENIZER,
            "measurement_tokenizer_revision": MEASUREMENT_REVISION,
            "start": start, "limit": limit, "max_attempts": max_attempts,
            "counts": counts, "unresolved_count": len(unresolved),
            "scientific_use_allowed": False,
        }
        for bank in BANKS:
            payload = {k: copy.deepcopy(v) for k, v in data.items() if k != "scenarios"}
            payload.update({
                "version": "controlled_candidate_modal_v1", "status": "PROVISIONAL",
                "bank_id": f"bank_{bank.lower()}", "partial": start != 0 or limit != 124,
                "scenarios": results[bank],
                "semantic_review": "UNADJUDICATED",
            })
            (target / f"bank_{bank.lower()}_candidates.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        (target / "unresolved.json").write_text(
            json.dumps(unresolved, indent=2, ensure_ascii=False), encoding="utf-8")
        (target / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        RUN_VOLUME.commit()
    return f"/runs/{run_name}", counts


@app.local_entrypoint()
def main(source: str = "data/scenarios_phase0b_utility_matched.json",
         limit: int = 6, start: int = 0, max_attempts: int = 6,
         run_name: str = "pilot01", authorize_paid_run: bool = False):
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", run_name):
        raise ValueError("run_name must be 2-64 letters, numbers, _ or -")
    if not (0 <= start < 124 and 1 <= limit <= 124 - start):
        raise ValueError("Choose 0 <= start < 124 and 1 <= limit <= 124-start")
    if not 1 <= max_attempts <= 12:
        raise ValueError("max_attempts must be 1..12")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if not authorize_paid_run:
        print(f"DRY RUN: would attempt {limit * 3} scenario-bank rewrites on paid H100.")
        print(f"Source SHA256: {digest}. To execute, add --authorize-paid-run.")
        return
    output, counts = generate_candidates.remote(
        payload, digest, start, limit, run_name, max_attempts,
    )
    print(json.dumps({"volume_path": output, "counts": counts}, indent=2))
    print(f"Retrieve with: modal volume get llm-coop-controlled-rewrites "
          f"{run_name} ./research/controlled_rewrites/{run_name}")
