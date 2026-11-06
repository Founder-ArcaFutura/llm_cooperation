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
import time
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


def _candidate_pool_solution(tokenizer, scenario, pool, earlier):
    """Find a four-action combination whose *measured* lengths satisfy both
    constraints. Every sentence comes from model-authored output: no padding.
    Pooling avoids throwing away three useful sentences because the fourth
    missed its target. The final combination still requires semantic review.
    """
    from itertools import product

    stem = scenario["stem"].strip()
    eligible = {}
    for strategy in STRATEGIES:
        candidates = []
        for action in dict.fromkeys(pool[strategy]):  # preserve order, dedupe
            if any(pattern.search(action) for pattern in BAD_PATTERNS):
                continue
            if any(
                action.casefold() == prev[strategy].casefold()
                or len(_words(action) & _words(prev[strategy]))
                   / max(1, len(_words(action) | _words(prev[strategy]))) > 0.85
                for prev in earlier.values()
            ):
                continue
            action_length = len(tokenizer.encode(action, add_special_tokens=False))
            prompt_length = len(tokenizer.encode(
                f"{stem}\n\nAction: {action}\nDecision:", add_special_tokens=False
            ))
            candidates.append((action, action_length, prompt_length))
        eligible[strategy] = candidates
        if not candidates:
            return None

    all_targets = sorted({count for candidates in eligible.values()
                          for _, count, _ in candidates})
    for action_target in all_targets:
        # Restrict combinatorial search using measured action and full-prompt
        # lengths before attempting any cross-bank/structural checks.
        active = {
            strategy: [c for c in eligible[strategy]
                       if action_target <= c[1] <= action_target + 1]
            for strategy in STRATEGIES
        }
        if any(not active[s] for s in STRATEGIES):
            continue
        prompt_targets = sorted({c[2] for s in STRATEGIES for c in active[s]})
        for prompt_target in prompt_targets:
            choices = [
                [c[0] for c in active[strategy]
                 if prompt_target <= c[2] <= prompt_target + 1]
                for strategy in STRATEGIES
            ]
            if any(not choice for choice in choices):
                continue
            # Prefer earlier successful generations; cap per-strategy search.
            for combination in product(*(choice[:12] for choice in choices)):
                options = dict(zip(STRATEGIES, combination))
                report = _score_candidate(tokenizer, scenario, options, earlier)
                if report["accepted_automatic_constraints"]:
                    return options, report
    return None


def _one_action_json(text: str) -> str | None:
    """Parse only a single nonempty model-written replacement sentence."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^\s*```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or set(obj) != {"action"}:
        return None
    candidate = obj["action"]
    return candidate.strip() if isinstance(candidate, str) and candidate.strip() else None


def _repair_target(tokenizer, candidate_pool: dict[str, list[str]]) -> int:
    """Prefer a feasible shared token count based on the *actual* sentences
    the model has written. Shortening is penalized more than expansion to
    discourage deleting necessary actors or operational details.
    """
    lengths = {
        strategy: sorted({
            len(tokenizer.encode(action, add_special_tokens=False))
            for action in candidate_pool[strategy]
        })
        for strategy in STRATEGIES
    }
    values = [n for counts in lengths.values() for n in counts]
    if not values:
        return 14

    def cost(target):
        total = 0.0
        for strategy in STRATEGIES:
            if not lengths[strategy]:
                total += 8
                continue
            total += min(
                (n - target - 1) * 1.7 if n > target + 1
                else (target - n) if n < target else 0
                for n in lengths[strategy]
            )
        return total

    middle = sorted(values)[len(values) // 2]
    return min(range(min(values), max(values) + 1),
               key=lambda t: (cost(t), abs(t - middle), t))


def _generate_set(llm, generation_tokenizer, measurement_tokenizer, scenario,
                  bank, previous, max_attempts, seed_pool=None):
    """Create one joint draft, then *targeted single-action repairs*.

    Earlier attempts are not erased: all valid single-sentence candidates are
    pooled and can form a compliant four-action set. A previous unsuccessful
    run may provide the seed pool. Every resulting set still requires human
    semantic adjudication.
    """
    from vllm import SamplingParams

    original = {strategy: scenario["options"][strategy] for strategy in STRATEGIES}
    candidate_pool = {strategy: [] for strategy in STRATEGIES}
    if seed_pool:
        for strategy in STRATEGIES:
            for action in seed_pool.get(strategy, []):
                if isinstance(action, str) and action.strip() and action not in candidate_pool[strategy]:
                    candidate_pool[strategy].append(action.strip())

    total_model_requests = 0
    attempts = 0
    last_raw = None

    def add_options(options):
        for strategy in STRATEGIES:
            action = options.get(strategy)
            if isinstance(action, str) and action.strip() and action.strip() not in candidate_pool[strategy]:
                candidate_pool[strategy].append(action.strip())

    def accepted(assembly):
        solution = _candidate_pool_solution(
            measurement_tokenizer, scenario, candidate_pool, previous
        )
        if solution is None:
            return None
        options, report = solution
        return {
            "options": options, "validation": report, "attempts": attempts,
            "model_requests": total_model_requests, "assembly": assembly,
            "accepted_automatic_constraints": True,
            "semantic_review": "UNADJUDICATED",
            "candidate_pool": candidate_pool,
        }

    existing = accepted("pooled_previous_candidates")
    if existing is not None:
        return existing

    # Only make a joint draft when a previous failed run has not already
    # supplied at least one usable candidate for each strategy.
    if any(not candidate_pool[strategy] for strategy in STRATEGIES):
        original_lengths = [
            len(measurement_tokenizer.encode(original[strategy], add_special_tokens=False))
            for strategy in STRATEGIES
        ]
        target = sorted(original_lengths)[len(original_lengths) // 2]
        instructions = {
            "bank": bank, "style": STYLES[bank],
            "scenario_id": scenario["id"], "partner_type": scenario["partner_type"],
            "scenario": scenario["stem"], "original_actions": original,
            "original_payoffs": scenario.get("payoff_spec"),
            "token_count_target": target,
            "constraints": "Four actions, each within one Qwen2.5 token of the others.",
            "other_bank_wording_to_avoid": previous,
        }
        rendered = generation_tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": json.dumps(instructions, ensure_ascii=False)}],
            tokenize=False, add_generation_prompt=True,
        )
        generated = llm.generate(
            [rendered], SamplingParams(temperature=0.45, top_p=0.9, max_tokens=650),
            use_tqdm=False
        )[0].outputs[0].text
        total_model_requests += 1
        attempts += 1
        last_raw = generated[:500]
        quartet = _json_object(generated)
        if quartet is not None:
            add_options(quartet)
            result = accepted("joint_model_generation")
            if result is not None:
                return result

    # One round handles *only* actions whose current candidates do not meet
    # the measured common target, so successful individual sentences survive.
    for _ in range(max(0, max_attempts - attempts)):
        attempts += 1
        target = _repair_target(measurement_tokenizer, candidate_pool)
        requests = []
        labels = []
        for strategy in STRATEGIES:
            scored = [
                (len(measurement_tokenizer.encode(action, add_special_tokens=False)), action)
                for action in candidate_pool[strategy]
            ]
            if scored:
                # Prefer an existing candidate inside the target window;
                # otherwise choose closest text to repair.
                closest_length, closest = min(
                    scored, key=lambda x: (
                        max(target - x[0], x[0] - (target + 1), 0),
                        abs(x[0] - target), len(x[1])
                    )
                )
                if target <= closest_length <= target + 1:
                    continue
            else:
                closest_length, closest = None, original[strategy]
            instructions = {
                "strategy": strategy,
                "bank": bank,
                "style": STYLES[bank],
                "scenario_id": scenario["id"],
                "partner_type": scenario["partner_type"],
                "scenario": scenario["stem"],
                "all_original_actions_for_semantic_context": original,
                "payoff_spec": scenario.get("payoff_spec"),
                "original_meaning_to_preserve": original[strategy],
                "current_sentence": closest,
                "current_exact_qwen25_token_count": closest_length,
                "target_qwen25_action_token_count": target,
                "acceptable_token_counts": [target, target + 1],
                "other_bank_wording_to_avoid": {
                    key: value[strategy] for key, value in previous.items()
                },
                "instruction": (
                    "Rewrite ONLY this action sentence. Fix its token length, "
                    "preserve the agent, action, partner type and strategic "
                    "payoff. Do not insert meaningless filler or change "
                    "incentives. Respond with a JSON object containing one "
                    "field, 'action', whose value is the revised sentence."
                ),
            }
            prompt = generation_tokenizer.apply_chat_template(
                [{"role": "system", "content": (
                    "You are an expert psychometric item editor. Repair one "
                    "action description without changing its semantic role. "
                    'Return ONLY valid JSON of the form {"action":"..."}.'  )},
                 {"role": "user", "content": json.dumps(instructions, ensure_ascii=False)}],
                tokenize=False, add_generation_prompt=True,
            )
            requests.append(prompt)
            labels.append(strategy)

        if not requests:
            # A full prompt may tokenize differently at the action boundary,
            # even when all stand-alone action counts are within one token.
            # Change one candidate to seek another tokenization.
            strategy = STRATEGIES[-1]
            action = candidate_pool[strategy][-1]
            instructions = {
                "strategy": strategy, "scenario": scenario["stem"],
                "original": original[strategy], "current_sentence": action,
                "target_action_tokens": target,
                "instruction": (
                    "Give a different natural paraphrase with the same meaning "
                    "and nearly the same Qwen2.5 token length. Return only "
                    'JSON {"action":"..."}'
                ),
            }
            requests.append(generation_tokenizer.apply_chat_template(
                [{"role": "system", "content": 'Return only JSON {"action":"..."}. Preserve meaning.'},
                 {"role": "user", "content": json.dumps(instructions, ensure_ascii=False)}],
                tokenize=False, add_generation_prompt=True,
            ))
            labels.append(strategy)

        generations = llm.generate(
            requests,
            SamplingParams(temperature=0.35, top_p=0.9, max_tokens=180),
            use_tqdm=False,
        )
        total_model_requests += len(requests)
        for strategy, result in zip(labels, generations):
            raw = result.outputs[0].text
            last_raw = raw[:500]
            new_action = _one_action_json(raw)
            if new_action and new_action not in candidate_pool[strategy]:
                candidate_pool[strategy].append(new_action)

        result = accepted("pooled_targeted_repairs")
        if result is not None:
            return result

    # Preserve *all* good individual sentences and report the best overall
    # near-miss. A subsequent run can reuse this pool and focus remaining
    # effort on whichever actions still fail.
    best_options = {}
    target = _repair_target(measurement_tokenizer, candidate_pool)
    for strategy in STRATEGIES:
        if candidate_pool[strategy]:
            best_options[strategy] = min(
                candidate_pool[strategy],
                key=lambda action: abs(
                    len(measurement_tokenizer.encode(action, add_special_tokens=False))
                    - target
                )
            )
        else:
            best_options[strategy] = original[strategy]
    report = _score_candidate(measurement_tokenizer, scenario, best_options, previous)
    return {
        "options": best_options, "validation": report,
        "attempts": attempts, "model_requests": total_model_requests,
        "accepted_automatic_constraints": False,
        "semantic_review": "UNADJUDICATED",
        "candidate_pool": candidate_pool, "last_raw_excerpt": last_raw,
        "repair_target": target,
        "candidate_counts": {strategy: len(candidate_pool[strategy])
                             for strategy in STRATEGIES},
    }

@app.function(gpu="H100", timeout=14400, retries=0,
              volumes={"/hf-cache": HF_CACHE, "/runs": RUN_VOLUME})
def generate_candidates(source_bytes: bytes, source_sha256: str, start: int, limit: int,
                        run_name: str, max_attempts: int, reuse_run: str = "",
                        max_runtime_minutes: int = 60):
    launched_at = time.monotonic()
    deadline = launched_at + max_runtime_minutes * 60
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
    if reuse_run and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", reuse_run):
        raise ValueError("Invalid --reuse-run name")
    if reuse_run == run_name:
        raise ValueError("reuse_run must differ from run_name; existing runs are immutable")
    reuse_root = Path("/runs") / reuse_run if reuse_run else None
    if reuse_root is not None:
        old_manifest_path = reuse_root / "manifest.json"
        if not old_manifest_path.is_file():
            raise FileNotFoundError(f"Resume manifest not found: {old_manifest_path}")
        old = json.loads(old_manifest_path.read_text(encoding="utf-8"))
        if (old.get("source_sha256") != source_sha256
                or old.get("measurement_tokenizer_revision") != MEASUREMENT_REVISION
                or old.get("measurement_tokenizer") != MEASUREMENT_TOKENIZER
                or old.get("model") != MODEL_ID):
            raise ValueError("Reuse run has incompatible source, tokenizer, or writer model")
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

    counts = {bank: {"accepted": 0, "newly_accepted": 0, "reused": 0,
                     "unresolved": 0, "errors": 0, "not_attempted": 0}
              for bank in BANKS}
    if not 15 <= max_runtime_minutes <= 180:
        raise ValueError("max_runtime_minutes must be between 15 and 180")
    stop_reason = None
    error_streak = 0
    completed_keys = set()
    results = {bank: [] for bank in BANKS}
    unresolved = []
    try:
        for index, scenario in enumerate(selected, start=start):
            if time.monotonic() + 45 >= deadline:
                stop_reason = "runtime_budget_reached"
                break
            # Keep successful four-action sets from a previous run. Load the
            # *records* rather than a candidate-bank file, retaining exact
            # scenario/index identity and audit metadata.
            retained = {}
            if reuse_root is not None:
                for bank in BANKS:
                    old_file = reuse_root / "records" / f"{index:03d}_{bank}.json"
                    if not old_file.is_file():
                        continue
                    old_record = json.loads(old_file.read_text(encoding="utf-8"))
                    if not old_record.get("accepted_automatic_constraints"):
                        continue
                    if (old_record.get("source_index") != index
                            or old_record.get("scenario_id") != scenario["id"]
                            or old_record.get("bank") != bank):
                        raise ValueError(f"Reuse record identity mismatch: {old_file}")
                    opts = old_record.get("options")
                    if not isinstance(opts, dict) or set(opts) != set(STRATEGIES):
                        raise ValueError(f"Malformed accepted reuse record: {old_file}")
                    retained[bank] = old_record

                # Revalidate every retained set against the exact pinned
                # tokenizer and all other retained banks; do not blindly
                # trust a historical accepted flag or corrupt the output.
                for bank, old_record in retained.items():
                    others = {
                        other: record["options"]
                        for other, record in retained.items() if other != bank
                    }
                    check = _score_candidate(
                        measure_tokenizer, scenario, old_record["options"], others
                    )
                    if not check["accepted_automatic_constraints"]:
                        raise ValueError(
                            f"Previous accepted record no longer passes: "
                            f"{scenario['id']} Bank {bank}: {check['issues']}"
                        )

            prior = {}
            for bank in BANKS:
                if time.monotonic() + 45 >= deadline:
                    stop_reason = "runtime_budget_reached"
                    break
                if bank in retained:
                    record = {
                        key: copy.deepcopy(value)
                        for key, value in retained[bank].items()
                        if key not in ("scenario_id", "source_index", "bank")
                    }
                    record["reused_from_run"] = reuse_run
                    record["validation"] = _score_candidate(
                        measure_tokenizer, scenario, record["options"],
                        {other: opts for other, opts in prior.items()}
                    )
                    counts[bank]["reused"] += 1
                else:
                    # Even if a later bank is already accepted, a new earlier
                    # bank must avoid colliding with it.
                    avoid = dict(prior)
                    avoid.update({
                        other: old_record["options"]
                        for other, old_record in retained.items() if other != bank
                    })
                    # Failed runs can still contain useful model-authored
                    # individual sentences. Reuse them instead of resetting
                    # the candidate pool to a single last/nearest quartet.
                    seed_pool = None
                    if reuse_root is not None:
                        old_file = reuse_root / "records" / f"{index:03d}_{bank}.json"
                        if old_file.is_file():
                            old_record = json.loads(old_file.read_text(encoding="utf-8"))
                            if (old_record.get("source_index") != index
                                    or old_record.get("scenario_id") != scenario["id"]
                                    or old_record.get("bank") != bank):
                                raise ValueError(f"Previous record identity mismatch: {old_file}")
                            if isinstance(old_record.get("candidate_pool"), dict):
                                seed_pool = old_record["candidate_pool"]
                            elif isinstance(old_record.get("options"), dict):
                                seed_pool = {
                                    strategy: [old_record["options"][strategy]]
                                    for strategy in STRATEGIES
                                    if isinstance(old_record["options"].get(strategy), str)
                                }
                    try:
                        record = _generate_set(
                            llm, generation_tokenizer, measure_tokenizer,
                            scenario, bank, avoid, max_attempts,
                            seed_pool=seed_pool,
                        )
                    except Exception as exc:
                        # An inference/parse/validation exception affects
                        # this candidate, not the whole production batch.
                        # A streak of systemic exceptions trips a circuit
                        # breaker instead of consuming more paid GPU time.
                        record = {
                            "accepted_automatic_constraints": False,
                            "status": "error",
                            "issues": [f"{type(exc).__name__}: {str(exc)[:500]}"],
                            "error_type": type(exc).__name__,
                            "semantic_review": "UNADJUDICATED",
                            "candidate_pool": seed_pool or {},
                        }
                        counts[bank]["errors"] += 1
                        error_streak += 1
                        print(f"ERROR {scenario['id']} bank {bank}: "
                              f"{type(exc).__name__}: {str(exc)[:300]}", flush=True)
                    else:
                        error_streak = 0
                        if record["accepted_automatic_constraints"]:
                            counts[bank]["newly_accepted"] += 1

                row = {
                    "scenario_id": scenario["id"], "source_index": index,
                    "bank": bank, **record,
                }
                filename = f"{index:03d}_{bank}.json"
                (target / "records" / filename).write_text(
                    json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                completed_keys.add((index, bank))
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
                status = ("REUSED" if bank in retained else
                          "automatic constraints passed"
                          if record["accepted_automatic_constraints"] else "UNRESOLVED")
                print(f"scenario {index + 1}/{len(scenarios)} bank {bank}: {status}",
                      flush=True)
                if error_streak >= 5:
                    stop_reason = "circuit_breaker_five_consecutive_errors"
                    print(f"Stopping gracefully: {stop_reason}", flush=True)
                    break
            # Checkpoint every scenario so even an external termination loses
            # at most the currently executing scenario-bank work.
            RUN_VOLUME.commit()
            if stop_reason:
                break
    finally:
        # Write an explicit record for each unattempted item, so a stopped
        # production run never masquerades as a complete three-bank corpus.
        for index, scenario in enumerate(selected, start=start):
            for bank in BANKS:
                if (index, bank) in completed_keys:
                    continue
                counts[bank]["not_attempted"] += 1
                row = {
                    "scenario_id": scenario["id"], "source_index": index,
                    "bank": bank, "status": "not_attempted",
                    "accepted_automatic_constraints": False,
                    "issues": [stop_reason or "interrupted_before_generation"],
                    "semantic_review": "UNADJUDICATED",
                }
                (target / "records" / f"{index:03d}_{bank}.json").write_text(
                    json.dumps(row, indent=2), encoding="utf-8"
                )
                unresolved.append({
                    "scenario_id": scenario["id"], "bank": bank,
                    "status": "not_attempted", "issues": row["issues"],
                })
        run_status = (
            "STOPPED_EARLY_WITH_CHECKPOINT" if stop_reason
            else "FINISHED_WITH_UNRESOLVED"
            if any(counts[b]["unresolved"] for b in BANKS)
            else "FINISHED_AUTOMATIC_CHECKS_ONLY"
        )
        manifest = {
            "version": "model_generated_controlled_banks_candidate_v1",
            "status": "PROVISIONAL_PENDING_INDEPENDENT_SEMANTIC_REVIEW",
            "run_name": run_name, "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": source_sha256, "source_path": "data/scenarios_phase0b_utility_matched.json",
            "model": MODEL_ID, "resolved_model_sha": model_sha,
            "measurement_tokenizer": MEASUREMENT_TOKENIZER,
            "measurement_tokenizer_revision": MEASUREMENT_REVISION,
            "start": start, "limit": limit, "max_attempts": max_attempts,
            "reuse_run": reuse_run or None,
            "max_runtime_minutes": max_runtime_minutes,
            "elapsed_minutes": round((time.monotonic() - launched_at) / 60, 2),
            "run_status": run_status,
            "stop_reason": stop_reason,
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
         run_name: str = "pilot01", reuse_run: str = "",
         max_runtime_minutes: int = 60,
         authorize_paid_run: bool = False):
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", run_name):
        raise ValueError("run_name must be 2-64 letters, numbers, _ or -")
    if reuse_run and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", reuse_run):
        raise ValueError("reuse_run must be a previously recorded run name")
    if reuse_run == run_name:
        raise ValueError("Cannot overwrite the run used for reuse")
    if not (0 <= start < 124 and 1 <= limit <= 124 - start):
        raise ValueError("Choose 0 <= start < 124 and 1 <= limit <= 124-start")
    if not 1 <= max_attempts <= 12:
        raise ValueError("max_attempts must be 1..12")
    if not 15 <= max_runtime_minutes <= 180:
        raise ValueError("max_runtime_minutes must be 15..180")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if not authorize_paid_run:
        print(f"DRY RUN: would attempt up to {limit * 3} scenario-bank rewrites on paid H100.")
        if reuse_run:
            print(f"Previously accepted scenario-bank variants from {reuse_run} will be reused; no GPU inference on those.")
        print(f"Maximum target runtime: {max_runtime_minutes} minutes, including model initialization.")
        print(f"Maximum repair rounds per unresolved set: {max_attempts}.")
        print("Unresolved sets are recorded, never silently accepted.")
        print(f"Source SHA256: {digest}. To execute, add --authorize-paid-run.")
        return
    output, counts = generate_candidates.remote(
        payload, digest, start, limit, run_name, max_attempts, reuse_run,
        max_runtime_minutes,
    )
    print(json.dumps({"volume_path": output, "counts": counts}, indent=2))
    print(f"Retrieve with: modal volume get llm-coop-controlled-rewrites "
          f"{run_name} ./research/controlled_rewrites/{run_name}")
