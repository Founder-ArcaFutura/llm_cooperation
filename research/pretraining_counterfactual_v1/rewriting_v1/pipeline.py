"""Lambda-ready, resumable paired TinyStories rewriting and validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
DEFAULT_SAMPLE = PILOT / "outputs" / "semantic_pilot" / "sample.jsonl"
DEFAULT_INDEX = PILOT / "pilot_artifacts" / "sample_index.jsonl"
DEFAULT_REVIEW = PILOT / "pilot_artifacts" / "integrity_reviews.json"
DEFAULT_SUBTYPES = PILOT / "pilot_artifacts" / "review_subtypes.json"
SUBTYPES = {"fair_competition", "unilateral_self_advantage", "exploitative_success"}
NARRATIVE_TERMS = {
    "resource_sharing": re.compile(r"\b(share|shared|sharing|trade|traded|borrow|borrowed|last|only|both|basket|food|apple|toy|paint|water|prize|resource)\b", re.I),
    "help_reciprocity": re.compile(r"\b(help|helped|helping|together|team|work together|take turns|took turns|thank|thanks|return the favor|fix|carry)\b", re.I),
    "rivalry_fair_competition": re.compile(r"\b(race|raced|racing|contest|competition|compete|competed|rival|opponent|winner|won|trophy|prize|first place|beat)\b", re.I),
    "defection_self_advantage": re.compile(r"\b(kept? (?:it|the|all|everything|for himself|for herself)|took (?:it|the|all)|without (?:telling|asking|helping)|refused|instead of helping|left (?:him|her|them)|own advantage|for himself|for herself)\b", re.I),
}
SLOGANS = re.compile(r"\b(the moral of the story|always be kind|always share|sharing is caring|cooperation is best|selfishness is bad)\b", re.I)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name): os.unlink(tmp_name)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict): raise ValueError(f"{path}:{line_no}: expected JSON object")
                rows.append(row)
    return rows


def load_sample(sample_path: Path, index_path: Path) -> list[dict[str, Any]]:
    sample = {int(r["source_index"]): r for r in read_jsonl(sample_path)}
    index = {int(r["source_index"]): r for r in read_jsonl(index_path)}
    if sample.keys() != index.keys():
        raise ValueError("sample.jsonl and sample_index.jsonl have different source ID sets")
    for sid, row in sample.items():
        text = row["text"]
        actual = sha256_text(text)
        if actual != row.get("sha256") or actual != index[sid].get("sha256"):
            raise ValueError(f"source hash mismatch for source_index={sid}")
        row["sha256"] = actual
        row["source_shard"] = index[sid].get("source_shard")
    return [sample[k] for k in sorted(sample)]


def social_features(text: str) -> list[str]:
    return [name for name, pattern in NARRATIVE_TERMS.items() if pattern.search(text)]


def load_provisional_tags(review_path: Path | None, subtype_path: Path | None) -> dict[int, list[str]]:
    tags: dict[int, list[str]] = {}
    if review_path and review_path.exists():
        raw = json.loads(review_path.read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else raw.get("reviews", list(raw.values()))
        for entry in entries:
            if not isinstance(entry, dict) or "source_index" not in entry: continue
            sid = int(entry["source_index"])
            labs = entry.get("labels", entry.get("categories", []))
            if isinstance(labs, dict): labs = [k for k, v in labs.items() if v]
            if not isinstance(labs, list): labs = []
            tags.setdefault(sid, []).extend(f"provisional:{x}" for x in labs)
    if subtype_path and subtype_path.exists():
        raw = json.loads(subtype_path.read_text(encoding="utf-8"))
        mapping = {"fair_or_performance_competition_success": "provisional:fair_competition", "selfish_appropriation_or_exploitation_success": "provisional:exploitative_success"}
        for key, tag in mapping.items():
            for sid in raw.get(key, []): tags.setdefault(int(sid), []).append(tag)
    return {sid: sorted(set(v)) for sid, v in tags.items()}


def select_candidates(rows: list[dict[str, Any]], n: int, seed: int,
                      review_path: Path | None = DEFAULT_REVIEW,
                      subtype_path: Path | None = DEFAULT_SUBTYPES) -> list[dict[str, Any]]:
    """Deterministic theme-balanced selection; features are retrieval cues, not labels."""
    provisional = load_provisional_tags(review_path, subtype_path)
    groups = list(NARRATIVE_TERMS)
    buckets: dict[str, list[dict[str, Any]]] = {g: [] for g in groups}
    candidates: dict[int, dict[str, Any]] = {}
    for row in rows:
        feats = social_features(row["text"])
        if not feats: continue
        item = {**row, "candidate_features": feats,
                "provisional_pilot_tags": provisional.get(int(row["source_index"]), []),
                "selection_note": "lexical retrieval cues only; not a semantic class label"}
        candidates[int(row["source_index"])] = item
        for group in feats: buckets[group].append(item)
    if len(candidates) < n:
        counts = {k: len(v) for k, v in buckets.items()}
        raise ValueError(f"requested {n} stories but only {len(candidates)} have social-decision retrieval cues; category counts={counts}")
    rng = random.Random(seed)
    order = {sid: rng.random() for sid in candidates}
    chosen: dict[int, dict[str, Any]] = {}
    # Round-robin over theme buckets protects smaller groups from being crowded out.
    cursors = {g: 0 for g in groups}
    ranked = {g: sorted(buckets[g], key=lambda x: (order[int(x["source_index"])], int(x["source_index"]))) for g in groups}
    while len(chosen) < n:
        progress = False
        for group in groups:
            bucket = ranked[group]
            while cursors[group] < len(bucket):
                item = bucket[cursors[group]]; cursors[group] += 1
                sid = int(item["source_index"])
                if sid not in chosen:
                    chosen[sid] = item; progress = True; break
            if len(chosen) >= n: break
        if not progress:
            for sid in sorted(candidates, key=lambda x: (order[x], x)):
                if sid not in chosen:
                    chosen[sid] = candidates[sid]
                    if len(chosen) >= n: break
    return sorted(chosen.values(), key=lambda x: int(x["source_index"]))


def prepare(args: argparse.Namespace) -> None:
    rows = load_sample(args.sample, args.index)
    selected = select_candidates(rows, args.count, args.seed, args.review, args.subtypes)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    payload = {"selection_version": "social-cue-balanced-v1", "source_manifest": str(args.index),
               "sample_file_sha256": hashlib.sha256(args.sample.read_bytes()).hexdigest(),
               "sample_index_file_sha256": hashlib.sha256(args.index.read_bytes()).hexdigest(),
               "pilot_sample_manifest_sha256": hashlib.sha256((PILOT/"pilot_artifacts"/"sample_manifest.json").read_bytes()).hexdigest(),
               "source_sample": str(args.sample), "requested": args.count, "selected": len(selected),
               "seed": args.seed, "source_rows": len(rows), "selected_rows": selected,
               "features_are_semantic_labels": False,
               "provisional_labels_warning": "Pilot labels were single-reader, provisional; included only for strata context."}
    atomic_json(output / "selection.json", payload)
    coverage = Counter(g for row in selected for g in row["candidate_features"])
    summary = {"selected": len(selected), "source_rows": len(rows), "seed": args.seed,
               "feature_coverage_overlapping": dict(coverage),
               "stories_with_provisional_pilot_tags": sum(bool(r["provisional_pilot_tags"]) for r in selected)}
    atomic_json(output / "selection_summary.json", summary)
    print(json.dumps(summary, indent=2))


def load_contracts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return tuple(json.loads((HERE / p).read_text(encoding="utf-8")) for p in
                 ("prompt_v1.json", "demonstrations_v1.json", "generation_config.json", "validation_prompt_v1.json"))  # type: ignore[return-value]


def build_prompt(row: dict[str, Any], prompt_doc: dict[str, Any], demos_doc: dict[str, Any],
                 error: str | None = None) -> str:
    demos = []
    for i, d in enumerate(demos_doc["examples"], 1):
        demos.append(json.dumps({"example": i, **d}, ensure_ascii=False, separators=(",", ":")))
    user = prompt_doc["user_template"].format(demonstrations="\n".join(demos), source_id=row["source_index"],
                                                 source_sha256=row["sha256"], story=row["text"])
    if error:
        user += "\n\nThe previous attempt failed deterministic validation: " + error + ". Return a complete corrected JSON object only."
    return user


def extract_json_object(text: str) -> dict[str, Any]:
    # Strict JSON decode, allowing a single surrounding Markdown fence or model preamble.
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if fence: candidates.insert(0, fence.group(1).strip())
    start = text.find("{"); end = text.rfind("}")
    if start >= 0 and end > start: candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict): return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("malformed_json")


def validate_generation(obj: dict[str, Any], source: str) -> str | None:
    expected = {"cooperative_story", "non_cooperative_story", "non_cooperative_subtype", "metadata"}
    if set(obj) != expected: return "missing_or_extra_keys"
    for key in ("cooperative_story", "non_cooperative_story"):
        if not isinstance(obj[key], str) or len(obj[key].strip()) < 24: return f"incomplete_{key}"
    if obj["non_cooperative_subtype"] not in SUBTYPES: return "invalid_non_cooperative_subtype"
    if not isinstance(obj["metadata"], dict) or not all(isinstance(obj["metadata"].get(k), str) and obj["metadata"][k].strip()
        for k in ("source_setting", "retained_characters", "changed_social_choice", "causal_outcome")):
        return "incomplete_metadata"
    a, b, orig = obj["cooperative_story"].strip(), obj["non_cooperative_story"].strip(), source.strip()
    if a == b or sha256_text(a) == sha256_text(b): return "treatments_identical"
    original_words = max(1, len(re.findall(r"\b\w+\b", orig)))
    for key, text in (("cooperative_story", a), ("non_cooperative_story", b)):
        ratio = len(re.findall(r"\b\w+\b", text)) / original_words
        if not 0.5 <= ratio <= 1.6: return f"length_ratio_{key}"
        if SLOGANS.search(text): return "moral_slogan"
    return None


def model_tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)


def model_generate(model_id: str, revision: str, config: dict[str, Any], prompts: list[str]):
    from vllm import LLM, SamplingParams
    llm = LLM(model=model_id, revision=revision, tokenizer_revision=revision,
              dtype=config["dtype"], tensor_parallel_size=config["tensor_parallel_size"],
              gpu_memory_utilization=config["gpu_memory_utilization"], max_model_len=config["max_model_len"],
              seed=config["seed"], trust_remote_code=False, generation_config="vllm")
    sampling = SamplingParams(temperature=config["temperature"], top_p=config["top_p"],
                              max_tokens=config["max_new_tokens"], seed=config["seed"])
    return llm, sampling


def runtime_environment() -> dict[str, Any]:
    from importlib.metadata import PackageNotFoundError, version
    packages={}
    for package in ("vllm","transformers","torch","tokenizers","huggingface-hub"):
        try: packages[package]=version(package)
        except PackageNotFoundError: packages[package]=None
    info={"python":os.sys.version,"platform":os.sys.platform,"packages":packages}
    try:
        import torch
        info["torch_cuda_version"]=torch.version.cuda
        info["cuda_available"]=torch.cuda.is_available()
        if torch.cuda.is_available():
            prop=torch.cuda.get_device_properties(0)
            info["gpu"]={"name":prop.name,"total_memory_gib":prop.total_memory/(1024**3),
                         "compute_capability":list(torch.cuda.get_device_capability(0))}
    except Exception as exc:
        info["gpu_probe_error"]=f"{type(exc).__name__}: {exc}"
    return info


def chat_prompt(tokenizer: Any, system: str, user: str) -> str:
    return tokenizer.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                         tokenize=False, add_generation_prompt=True, enable_thinking=False)


def record_paths(root: Path, sid: int) -> tuple[Path, Path]:
    return root / "records" / f"{sid:07d}.json", root / "validation" / f"{sid:07d}.json"


def run_generation(args: argparse.Namespace) -> None:
    # Fail before importing/initializing vLLM unless the operator states their current account quote.
    if not args.approve_paid_inference:
        raise ValueError("paid inference requires explicit --approve-paid-inference authorization")
    if args.hourly_rate_usd is None or args.hourly_rate_usd <= 0:
        raise ValueError("--hourly-rate-usd is required and must be the actual Lambda account rate")
    if not args.lambda_instance_id.strip(): raise ValueError("--lambda-instance-id must identify the manually provisioned Lambda instance")
    if args.benchmark:
        if args.count != 100: raise ValueError("benchmark mode processes exactly 100 stories")
    elif args.count != 1000:
        raise ValueError("use --benchmark for exactly 100 sources; non-benchmark generation is reserved for the 1,000-story pilot")
    elif not args.approve_1000_pilot:
        raise ValueError("the 1,000-story pilot requires --approve-1000-pilot after benchmark review")
    selection_path = args.selection
    selected = json.loads(selection_path.read_text(encoding="utf-8"))["selected_rows"][:args.count]
    prompt_doc, demos_doc, config, _ = load_contracts()
    model_id, revision = args.model_id or config["model_id"], args.model_revision or config["model_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision): raise ValueError("model revision must be a full 40-character immutable commit hash")
    output = args.output; output.mkdir(parents=True, exist_ok=True)
    manifest = {"run_version": "lambda-rewrite-run-v1", "mode": "benchmark_100" if args.benchmark else "pilot",
                "requested_stories": args.count, "selection_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                "prompt_sha256": sha256_text(json.dumps(prompt_doc, sort_keys=True)),
                "demonstrations_sha256": sha256_text(json.dumps(demos_doc, sort_keys=True)),
                "generation_config_sha256": sha256_text(json.dumps(config, sort_keys=True)),
                "model_id": model_id, "model_revision": revision, "hourly_rate_usd": args.hourly_rate_usd,
                "lambda_instance_id_attestation": args.lambda_instance_id,
                "account_rate_attestation": "operator supplied current account rate; no account API was queried",
                "lambda_instance_sessions": [],
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runtime_environment": runtime_environment()}
    manifest_path = output / "run_manifest.json"
    current_environment=runtime_environment()
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("selection_sha256", "requested_stories", "mode", "prompt_sha256", "demonstrations_sha256", "generation_config_sha256", "model_id", "model_revision", "hourly_rate_usd"):
            if old.get(key) != manifest[key]: raise ValueError(f"resume identity mismatch: {key}")
        prior_sessions=old.get("lambda_instance_sessions",[])
        if prior_sessions and prior_sessions[-1].get("runtime_environment") != current_environment:
            raise ValueError("resume runtime environment differs from the last Lambda session")
        manifest = old
    else: atomic_json(manifest_path, manifest)
    todo = []
    for row in selected:
        sid = int(row["source_index"]); record, _ = record_paths(output, sid)
        if record.exists():
            existing = json.loads(record.read_text(encoding="utf-8"))
            if existing.get("source_sha256") != row["sha256"]: raise ValueError(f"existing record source hash mismatch: {sid}")
            continue
        todo.append(row)
    if not todo:
        print("All selected records already exist; nothing to generate."); return
    session={"lambda_instance_id_attestation":args.lambda_instance_id,"hourly_rate_usd":args.hourly_rate_usd,
             "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"runtime_environment":current_environment}
    manifest.setdefault("lambda_instance_sessions",[]).append(session)
    atomic_json(manifest_path,manifest)
    run_started = time.perf_counter()
    tokenizer = model_tokenizer(model_id, revision)
    llm, sampling = model_generate(model_id, revision, config, [])
    model_load_seconds = time.perf_counter() - run_started
    if os.name != "nt":
        import torch
        torch.cuda.reset_peak_memory_stats()
    generation_seconds = 0.0
    remaining = list(todo)
    attempts_by_id: dict[int, list[dict[str, Any]]] = {int(r["source_index"]): [] for r in remaining}
    last_error: dict[int, str | None] = {int(r["source_index"]): None for r in remaining}
    finals: dict[int, tuple[dict[str, Any], int, int]] = {}
    for attempt in range(1, config["max_attempts"] + 1):
        for offset in range(0, len(remaining), config["batch_size"]):
            batch = remaining[offset:offset + config["batch_size"]]
            users = [build_prompt(r, prompt_doc, demos_doc, last_error[int(r["source_index"])]) for r in batch]
            prompts = [chat_prompt(tokenizer, prompt_doc["system"], u) for u in users]
            t0 = time.perf_counter(); generated = llm.generate(prompts, sampling, use_tqdm=False); elapsed = time.perf_counter() - t0
            generation_seconds += elapsed
            for row, user, result in zip(batch, users, generated):
                sid = int(row["source_index"]); completion = result.outputs[0]
                raw = completion.text; p_tokens = len(result.prompt_token_ids or [])
                o_tokens = len(completion.token_ids or [])
                attempt_data = {"attempt": attempt, "prompt_tokens": p_tokens, "output_tokens": o_tokens,
                                "raw_output": raw, "elapsed_seconds_batch": elapsed}
                try:
                    obj = extract_json_object(raw)
                    error = validate_generation(obj, row["text"])
                except ValueError as exc:
                    obj, error = None, str(exc)
                attempt_data["parse_status"] = "accepted" if error is None else "rejected"
                attempt_data["error"] = error
                attempts_by_id[sid].append(attempt_data); last_error[sid] = error
                if error is None and obj is not None: finals[sid] = (obj, sum(a["prompt_tokens"] for a in attempts_by_id[sid]), sum(a["output_tokens"] for a in attempts_by_id[sid]))
        remaining = [r for r in remaining if int(r["source_index"]) not in finals]
        if not remaining: break
    for row in todo:
        sid = int(row["source_index"]); record_path, _ = record_paths(output, sid)
        obj_tuple = finals.get(sid)
        if obj_tuple:
            obj, in_tok, out_tok = obj_tuple
            status = "schema_and_integrity_accepted"
            rewrite = {"cooperative_story": obj["cooperative_story"].strip(),
                      "non_cooperative_story": obj["non_cooperative_story"].strip(),
                      "non_cooperative_subtype": obj["non_cooperative_subtype"], "metadata": obj["metadata"]}
            story_token_ids = {"source_story": tokenizer.encode(row["text"], add_special_tokens=False),
                               "cooperative_story": tokenizer.encode(rewrite["cooperative_story"], add_special_tokens=False),
                               "non_cooperative_story": tokenizer.encode(rewrite["non_cooperative_story"], add_special_tokens=False)}
        else:
            in_tok = sum(a["prompt_tokens"] for a in attempts_by_id[sid]); out_tok = sum(a["output_tokens"] for a in attempts_by_id[sid])
            status = "generation_failed_after_retries"; rewrite = None; story_token_ids = None
        rec = {"record_version": "paired-story-record-v1", "source_index": sid, "source_sha256": row["sha256"],
               "source_shard": row.get("source_shard"), "source_story": row["text"], "candidate_features": row["candidate_features"],
               "provisional_pilot_tags": row.get("provisional_pilot_tags", []), "selection_note": row["selection_note"],
               "rewrite": rewrite, "generation_status": status, "generation_retry_history": attempts_by_id[sid],
               "generation_input_tokens_total": in_tok, "generation_output_tokens_total": out_tok,
               "story_token_ids": story_token_ids,
               "output_hashes": {"cooperative_story": sha256_text(rewrite["cooperative_story"]) if rewrite else None,
                                 "non_cooperative_story": sha256_text(rewrite["non_cooperative_story"]) if rewrite else None},
               "model": {"id": model_id, "revision": revision}, "generation_config": config,
               "prompt_version": prompt_doc["prompt_version"], "demonstration_version": demos_doc["demonstration_version"],
               "runtime": {"hourly_rate_usd": args.hourly_rate_usd, "generation_wall_seconds": round(generation_seconds, 6)}}
        atomic_json(record_path, rec)
    elapsed = time.perf_counter() - run_started
    accepted = len(finals)
    if os.name != "nt":
        import torch
        peak_memory = torch.cuda.max_memory_allocated() / (1024**3)
        reserved_memory = torch.cuda.max_memory_reserved() / (1024**3)
    else: peak_memory = reserved_memory = None
    newly = len(todo); input_tokens = sum(sum(a["prompt_tokens"] for a in attempts_by_id[int(r["source_index"])]) for r in todo)
    output_tokens = sum(sum(a["output_tokens"] for a in attempts_by_id[int(r["source_index"])]) for r in todo)
    benchmark = {"benchmark_version": "inference-benchmark-v1", "stories_processed": newly,
                 "generation_accepted": accepted, "generation_acceptance_rate": accepted / newly if newly else 0,
                 "attempts": sum(len(v) for v in attempts_by_id.values()), "retry_count": sum(max(0, len(v)-1) for v in attempts_by_id.values()),
                 "stories_per_second_inference": newly / generation_seconds if generation_seconds else 0,
                 "stories_per_second_wall_including_model_load": newly / elapsed if elapsed else 0,
                 "input_tokens_total_including_retries": input_tokens, "output_tokens_total_including_retries": output_tokens,
                 "input_tokens_per_second": input_tokens / generation_seconds if generation_seconds else 0,
                 "output_tokens_per_second": output_tokens / generation_seconds if generation_seconds else 0,
                 "mean_output_tokens_per_source_including_retries": output_tokens / newly if newly else 0,
                 "generation_seconds": generation_seconds, "model_load_seconds_including_tokenizer": model_load_seconds,
                 "wall_seconds_including_model_load": elapsed,
                 "gpu_peak_allocated_gib": peak_memory, "gpu_peak_reserved_gib": reserved_memory,
                 "hourly_rate_usd": args.hourly_rate_usd, "actual_gpu_cost_usd_excluding_instance_setup_and_idle": generation_seconds / 3600 * args.hourly_rate_usd,
                 "command_wall_cost_estimate_usd_excluding_instance_boot_and_idle": elapsed / 3600 * args.hourly_rate_usd,
                 "estimated_cost_formula": "(N / measured_stories_per_second_inference / 3600 + startup_and_validation_hours) * account_hourly_rate_usd",
                 "source_scope": "100-story benchmark" if args.benchmark else "pilot scope"}
    atomic_json(output / "benchmark.json", benchmark)
    atomic_json(output / "checkpoint.json", {"completed_source_indices": sorted(int(json.loads(p.read_text(encoding="utf-8"))["source_index"]) for p in (output/"records").glob("*.json")),
                                                 "last_checkpoint_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    manifest["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); atomic_json(manifest_path, manifest)
    session.update({"ended_utc":manifest["finished_utc"],"command_wall_seconds":elapsed,"inference_seconds":generation_seconds,
                    "command_wall_cost_estimate_usd_excluding_instance_boot_and_idle":elapsed/3600*args.hourly_rate_usd})
    atomic_json(manifest_path,manifest)
    print(json.dumps(benchmark, indent=2))


def validation_prompt(rec: dict[str, Any], validator: dict[str, Any], validation_doc: dict[str, Any]) -> str:
    return json.dumps({"task": "validate paired narrative counterfactual", "criteria": validation_doc,
        "source_story": rec["source_story"], "claimed_subtype": rec["rewrite"]["non_cooperative_subtype"],
        "cooperative_story": rec["rewrite"]["cooperative_story"],
        "non_cooperative_story": rec["rewrite"]["non_cooperative_story"]}, ensure_ascii=False)


def parse_validation(raw: str) -> dict[str, Any]:
    obj = extract_json_object(raw)
    required = {"cooperative", "non_cooperative", "opposing_strategies_distinct", "source_preservation", "quality", "validity", "confidence", "notes"}
    if set(obj) != required: raise ValueError("invalid_validation_top_level_keys")
    for key in ("cooperative", "non_cooperative"):
        if not isinstance(obj.get(key), dict): raise ValueError("invalid_validation_shape")
        keys=("behavior_identifiable", "actor_favorable_outcome", "causal_link", "ending_consistent")
        if key=="non_cooperative": keys += ("subtype_matches_behavior", "no_automatic_punishment_or_repentance")
        if set(obj[key]) != set(keys) | {"evidence"} or not isinstance(obj[key]["evidence"],str): raise ValueError("invalid_validation_shape")
        for criterion in keys:
            value = obj[key].get(criterion)
            if not (isinstance(value, bool) or value is None): raise ValueError("invalid_validation_criterion")
    for key in ("opposing_strategies_distinct", "source_preservation", "quality"):
        value = obj.get(key)
        if not (isinstance(value, bool) or value is None): raise ValueError("invalid_validation_criterion")
    if obj.get("validity") not in {"pass", "uncertain", "fail"}: raise ValueError("invalid_validation_status")
    if not isinstance(obj.get("confidence"), (int, float)) or not 0 <= obj["confidence"] <= 1: raise ValueError("invalid_validation_confidence")
    if not isinstance(obj.get("notes"), str): raise ValueError("invalid_validation_notes")
    return obj


def run_validation(args: argparse.Namespace) -> None:
    if not args.approve_paid_inference:
        raise ValueError("paid validation inference requires explicit --approve-paid-inference authorization")
    if args.hourly_rate_usd is None or args.hourly_rate_usd <= 0:
        raise ValueError("--hourly-rate-usd is required and must be the actual Lambda account rate")
    if not args.lambda_instance_id.strip(): raise ValueError("--lambda-instance-id must identify the manually provisioned Lambda instance")
    _, _, config, validation_doc = load_contracts()
    model_id, revision = args.model_id or config["model_id"], args.model_revision or config["model_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision): raise ValueError("model revision must be a full immutable commit hash")
    source_records = sorted((args.run / "records").glob("*.json"))
    todo = []
    for path in source_records:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec["generation_status"] != "schema_and_integrity_accepted": continue
        if sha256_text(rec["source_story"]) != rec["source_sha256"]: raise ValueError(f"source hash mismatch for {rec['source_index']}")
        for arm in ("cooperative_story","non_cooperative_story"):
            if sha256_text(rec["rewrite"][arm]) != rec["output_hashes"].get(arm): raise ValueError(f"output hash mismatch for {rec['source_index']}:{arm}")
        dst = args.run / "validation" / path.name
        if not dst.exists(): todo.append((rec, dst))
    if not todo: print("No unvalidated accepted records found."); return
    run_started = time.perf_counter()
    tokenizer = model_tokenizer(model_id, revision); llm, sampling = model_generate(model_id, revision, config, [])
    model_load_seconds = time.perf_counter()-run_started
    started = time.perf_counter(); accepted = 0
    for rec, dst in todo:
        history = []; last_error = None; result = None; input_tokens = output_tokens = 0
        for attempt in range(1, config["max_attempts"] + 1):
            user = validation_prompt(rec, validation_doc, validation_doc)
            if last_error: user += " Previous output failed: " + last_error + ". Return corrected JSON only."
            prompt = chat_prompt(tokenizer, validation_doc["system"], user)
            t0 = time.perf_counter(); generated = llm.generate([prompt], sampling, use_tqdm=False); duration = time.perf_counter()-t0
            out = generated[0].outputs[0]; pcount=len(generated[0].prompt_token_ids or []); ocount=len(out.token_ids or [])
            input_tokens += pcount; output_tokens += ocount
            try: result = parse_validation(out.text); err = None
            except ValueError as e: err = str(e)
            history.append({"attempt":attempt,"status":"accepted" if err is None else "rejected","error":err,
                            "raw_output":out.text,"input_tokens":pcount,"output_tokens":ocount,"elapsed_seconds":duration})
            last_error=err
            if err is None: break
        if result:
            accepted += 1
            # Reconcile the validator's status with its fields; never let a claimed pass override failures.
            vals = [value for t in ("cooperative", "non_cooperative") for key,value in result[t].items() if key!="evidence"]
            vals += [result[k] for k in ("opposing_strategies_distinct", "source_preservation", "quality")]
            if False in vals: status = "fail"
            elif None in vals: status = "uncertain"
            else: status = result["validity"]
            result["validity"] = status
        else: status = "validation_parse_failed"
        atomic_json(dst, {"source_index":rec["source_index"],"source_sha256":rec["source_sha256"],
            "validation_version":validation_doc["validation_version"],"validator_model":{"id":model_id,"revision":revision},
            "validation_prompt_sha256":sha256_text(json.dumps(validation_doc,sort_keys=True)),
            "validation_generation_config_sha256":sha256_text(json.dumps(config,sort_keys=True)),
            "lambda_instance_id_attestation":args.lambda_instance_id,
            "validation_status":status,"validation":result,"retry_history":history,
            "input_tokens_total":input_tokens,"output_tokens_total":output_tokens,"hourly_rate_usd":args.hourly_rate_usd})
    seconds = time.perf_counter()-started
    validation_receipt={"validation_run_version":"semantic-validation-run-v1","validated":len(todo),
                      "structured_output_accepted":accepted,"acceptance_rate":accepted/len(todo),
                      "generation_seconds":seconds,"model_load_seconds_including_tokenizer":model_load_seconds,
                      "hourly_rate_usd":args.hourly_rate_usd,"lambda_instance_id_attestation":args.lambda_instance_id,
                      "model_id":model_id,"model_revision":revision,"validation_prompt_sha256":sha256_text(json.dumps(validation_doc,sort_keys=True)),
                      "runtime_environment":runtime_environment(),"command_wall_seconds":seconds+model_load_seconds,
                      "command_wall_cost_estimate_usd_excluding_instance_boot_and_idle":(seconds+model_load_seconds)/3600*args.hourly_rate_usd}
    receipt_path=args.run/"validation"/f"validation_run_{time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())}_{time.time_ns()}.json"
    atomic_json(receipt_path,validation_receipt)
    print(json.dumps(validation_receipt,indent=2))


def report(args: argparse.Namespace) -> None:
    if args.minimum_human_review_rows < 1: raise ValueError("--minimum-human-review-rows must be positive")
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((args.run/"records").glob("*.json"))]
    validation_files = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((args.run/"validation").glob("*.json"))]
    validations = [v for v in validation_files if "source_index" in v]
    validation_receipts = [v for v in validation_files if "source_index" not in v]
    human_review = None
    if args.human_review and not args.human_review.exists(): raise ValueError(f"human review file not found: {args.human_review}")
    if args.human_review_key and not args.human_review_key.exists(): raise ValueError(f"human review key not found: {args.human_review_key}")
    if args.human_review_key and not args.human_review: raise ValueError("--human-review-key requires --human-review")
    if args.human_review:
        human_rows = read_jsonl(args.human_review)
        fields=("behavior_a_identifiable","behavior_b_identifiable","actor_favorable_outcome_a","actor_favorable_outcome_b",
                "causal_link_a","causal_link_b","strategies_distinct","source_content_preserved",
                "language_age_appropriate_a","language_age_appropriate_b","ending_consistent_a","ending_consistent_b","uncertain")
        completed=[]
        for row in human_rows:
            answers=row.get("review_fields",{})
            is_complete=bool(row.get("reviewer_id")) and bool(row.get("review_date")) and all(isinstance(answers.get(k),bool) for k in fields)
            completed.append(is_complete)
        human_key={}
        if args.human_review_key and args.human_review_key.exists():
            human_key={row["review_id"]:row for row in read_jsonl(args.human_review_key)}
        treatment_counts={"cooperative_success":Counter(),"non_cooperative_success":Counter()}
        for row in human_rows:
            answers=row.get("review_fields",{}); key=human_key.get(row.get("review_id"),{})
            for arm,strategy_field in (("cooperative_success","side_a_strategy"),("non_cooperative_success","side_b_strategy")):
                side=next((s for s in ("a","b") if key.get(f"side_{s}_strategy")==arm),None)
                if side:
                    for name in ("behavior_identifiable","actor_favorable_outcome","causal_link","language_age_appropriate","ending_consistent"):
                        value=answers.get(f"{name}_{side}")
                        treatment_counts[arm][f"{name}:{value}"]+=1
        field_counts={field:dict(Counter(str(row.get("review_fields",{}).get(field)) for row in human_rows)) for field in fields}
        human_review={"rows":len(human_rows),"minimum_rows_for_scale_gate":args.minimum_human_review_rows,
                      "fully_annotated_rows":sum(completed),"complete":len(human_rows)>=args.minimum_human_review_rows and bool(human_rows) and all(completed),
                      "completed_rows_with_uncertainty":sum(1 for row in human_rows if row.get("review_fields",{}).get("uncertain") is True),
                      "field_counts":field_counts,"treatment_counts":{k:dict(v) for k,v in treatment_counts.items()},
                      "joined_with_separate_key":bool(human_key),"reviewer_ids":sorted({r.get("reviewer_id") for r in human_rows if r.get("reviewer_id")}),
                      "stratification_key_must_be_kept_separate":True}
    generated = [r for r in records if r["generation_status"] == "schema_and_integrity_accepted"]
    word_source=[]; word_a=[]; word_b=[]; subtype=Counter(); quality=Counter(); unique_tokens=set()
    edit_stats={"cooperative_added_word_tokens":[],"cooperative_removed_word_tokens":[],"cooperative_word_type_jaccard":[],
                "non_cooperative_added_word_tokens":[],"non_cooperative_removed_word_tokens":[],"non_cooperative_word_type_jaccard":[]}
    for rec in generated:
        rw=rec["rewrite"]; subtype[rw["non_cooperative_subtype"]]+=1
        src=set(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",rec["source_story"].lower()))
        for key, out in (("source",rec["source_story"]),("coop",rw["cooperative_story"]),("noncoop",rw["non_cooperative_story"])):
            words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",out.lower()); unique_tokens.update(words)
            if key=="source": word_source.append(len(words))
            elif key=="coop":
                word_a.append(len(words)); types=set(words)
                edit_stats["cooperative_added_word_tokens"].append(len(types-src)); edit_stats["cooperative_removed_word_tokens"].append(len(src-types))
                edit_stats["cooperative_word_type_jaccard"].append(len(types&src)/len(types|src) if types|src else 1)
            else:
                word_b.append(len(words)); types=set(words)
                edit_stats["non_cooperative_added_word_tokens"].append(len(types-src)); edit_stats["non_cooperative_removed_word_tokens"].append(len(src-types))
                edit_stats["non_cooperative_word_type_jaccard"].append(len(types&src)/len(types|src) if types|src else 1)
    for v in validations: quality[v.get("validation_status","missing")]+=1
    error_patterns=Counter(a.get("error") for r in records for a in r.get("generation_retry_history",[]) if a.get("error"))
    coop_semantics=Counter(); noncoop_semantics=Counter(); quality_review=Counter()
    for v in validations:
        result=v.get("validation") or {}
        for arm,counts in (("cooperative",coop_semantics),("non_cooperative",noncoop_semantics)):
            if isinstance(result.get(arm),dict):
                vals=[x for k,x in result[arm].items() if k!="evidence"]
                counts["pass" if vals and all(x is True for x in vals) else "fail" if False in vals else "uncertain"]+=1
        if "quality" in result: quality_review[str(result["quality"])]+=1
    benchmark_path=args.run/"benchmark.json"; bench=json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else {}
    run_manifest_path=args.run/"run_manifest.json"
    run_manifest=json.loads(run_manifest_path.read_text(encoding="utf-8")) if run_manifest_path.exists() else {}
    rate=args.hourly_rate_usd if args.hourly_rate_usd is not None else bench.get("hourly_rate_usd")
    tps=bench.get("stories_per_second_inference",0)
    validation_seconds=sum(v.get("generation_seconds",sum(a.get("elapsed_seconds",0) for a in v.get("retry_history",[]))) for v in validation_receipts)
    validation_rate=next((v.get("hourly_rate_usd") for v in validation_receipts if v.get("hourly_rate_usd")),None)
    scale={}
    for n in (1000,100000,300000):
        hours=(n/tps/3600) if tps else None
        scale[str(n)]={"estimated_gpu_hours_inference_only":hours,
                       "estimated_usd_inference_only":hours*rate if hours is not None and rate else None,
                       "formula":"(N / measured stories_per_second / 3600 + startup/validation hours) x actual Lambda hourly rate"}
    report_obj={"report_version":"paired-counterfactual-pilot-report-v1","scope":"generation evidence only; not model-training evidence",
        "source_stories_selected":len(records),"generation_accepted":len(generated),"generation_acceptance_rate":len(generated)/len(records) if records else 0,
        "cooperative_generation_acceptance_rate":len(generated)/len(records) if records else 0,
        "non_cooperative_generation_acceptance_rate":len(generated)/len(records) if records else 0,
        "failed_generation_records":len(records)-len(generated),"generation_error_patterns":dict(error_patterns),
        "non_cooperative_subtype_composition":dict(subtype),
        "semantic_validation_pair_status_composition":dict(quality),"semantic_validation_cooperative_composition":dict(coop_semantics),
        "semantic_validation_non_cooperative_composition":dict(noncoop_semantics),"separate_textual_quality_review_composition":dict(quality_review),
        "validated_count":len(validations),
        "unique_word_types_casefolded_across_source_and_rewrites":len(unique_tokens),
        "model_token_supply":{"tokenizer_id":run_manifest.get("model_id","see per-run manifest"),
            "tokenizer_revision":run_manifest.get("model_revision"),
            "source_story_tokens":sum(len(r["story_token_ids"]["source_story"]) for r in generated if r.get("story_token_ids")),
            "cooperative_story_tokens":sum(len(r["story_token_ids"]["cooperative_story"]) for r in generated if r.get("story_token_ids")),
            "non_cooperative_story_tokens":sum(len(r["story_token_ids"]["non_cooperative_story"]) for r in generated if r.get("story_token_ids")),
            "unique_cooperative_token_ids":len({i for r in generated if r.get("story_token_ids") for i in r["story_token_ids"]["cooperative_story"]}),
            "unique_non_cooperative_token_ids":len({i for r in generated if r.get("story_token_ids") for i in r["story_token_ids"]["non_cooperative_story"]}),
            "unique_token_ids_across_both_rewrite_arms":len({i for r in generated if r.get("story_token_ids") for k in ("cooperative_story","non_cooperative_story") for i in r["story_token_ids"][k]}),
            "method":"exact token ID sequences from the pinned generation tokenizer; special tokens excluded"},
        "average_rewrite_story_token_length":{"cooperative_mean":statistics.mean(len(r["story_token_ids"]["cooperative_story"]) for r in generated if r.get("story_token_ids")) if generated else None,
            "non_cooperative_mean":statistics.mean(len(r["story_token_ids"]["non_cooperative_story"]) for r in generated if r.get("story_token_ids")) if generated else None},
        "length_words":{"source_mean":statistics.mean(word_source) if word_source else None,"cooperative_mean":statistics.mean(word_a) if word_a else None,
                        "non_cooperative_mean":statistics.mean(word_b) if word_b else None,
                        "source_p10_p50_p90":quantiles(word_source),"cooperative_p10_p50_p90":quantiles(word_a),"non_cooperative_p10_p50_p90":quantiles(word_b)},
        "lexical_changes_unique_casefolded_word_types":{k:{"mean":statistics.mean(v) if v else None,"values":v} for k,v in edit_stats.items()},
        "benchmark":bench,"validation_compute":{"generation_seconds_sum":validation_seconds,
             "gpu_hours_estimated":validation_seconds/3600,"cost_usd_at_validator_account_rate":validation_seconds/3600*validation_rate if validation_rate else None,
             "account_hourly_rate_usd":validation_rate},"projected_scale":scale,
        "representative_pairs": [{"source_index":r["source_index"],"source_story":r["source_story"],"cooperative_story":r["rewrite"]["cooperative_story"],
                                   "non_cooperative_story":r["rewrite"]["non_cooperative_story"],"subtype":r["rewrite"]["non_cooperative_subtype"]}
                                  for r in generated[:min(args.examples,5)]],
        "independent_human_review":human_review,
        "scale_readiness":"AWAITING_INDEPENDENT_HUMAN_REVIEW" if not human_review or not human_review.get("complete") or not human_review.get("joined_with_separate_key") else "INDEPENDENT_REVIEW_COMPLETE_REQUIRES_EXPLICIT_DECISION",
        "limitations":["Lexical selector features are retrieval cues, not semantic labels.","The pilot review tags are provisional single-reader annotations.",
                       "A model-as-judge pass is not independent human validation.","Only completed benchmark measurements support runtime projection.",
                       "Scale readiness cannot be passed by automated validation alone."]}
    atomic_json(args.output,report_obj)
    print(json.dumps({k:v for k,v in report_obj.items() if k not in ("representative_pairs","length_words")},indent=2))


def quantiles(values: list[int]) -> dict[str, float | None]:
    if not values: return {"p10":None,"p50":None,"p90":None}
    ordered=sorted(values)
    def q(p: float) -> float:
        index=(len(ordered)-1)*p; lo=int(index); hi=min(lo+1,len(ordered)-1); frac=index-lo
        return ordered[lo]*(1-frac)+ordered[hi]*frac
    return {"p10":q(.1),"p50":q(.5),"p90":q(.9)}


def review_sample(args: argparse.Namespace) -> None:
    """Export a stratified, side-randomized human review pack; no labels are inferred."""
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((args.run/"records").glob("*.json"))]
    valid = [r for r in records if r.get("rewrite")]
    if not valid: raise ValueError("no successfully generated stories to review")
    by_subtype: dict[str, list[dict[str, Any]]] = {}
    for r in valid: by_subtype.setdefault(r["rewrite"]["non_cooperative_subtype"], []).append(r)
    rng = random.Random(args.seed); selected: dict[int, dict[str, Any]] = {}
    # Round-robin subtype coverage, then fill the remainder from any subtype.
    for group in sorted(by_subtype): rng.shuffle(by_subtype[group])
    while len(selected) < min(args.count, len(valid)):
        moved = False
        for group in sorted(by_subtype):
            while by_subtype[group]:
                item = by_subtype[group].pop()
                if item["source_index"] not in selected:
                    selected[item["source_index"]] = item; moved = True; break
            if len(selected) >= min(args.count, len(valid)): break
        if not moved: break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    key_path = args.output.with_suffix(args.output.suffix + ".key.jsonl")
    with args.output.open("w", encoding="utf-8", newline="\n") as f:
        with key_path.open("w", encoding="utf-8", newline="\n") as key_file:
          for r in sorted(selected.values(), key=lambda x:x["source_index"]):
            rw=r["rewrite"]; sides=[("A",rw["cooperative_story"]),("B",rw["non_cooperative_story"])]; rng.shuffle(sides)
            review_id="review-"+sha256_text(f"{args.seed}:{r['source_index']}")[:12]
            row={"review_id":review_id,"reviewer_id":"","review_date":"","source_story":r["source_story"],
                 "story_a":sides[0][1],"story_b":sides[1][1],
                 "review_fields":{"behavior_a_identifiable":None,"behavior_b_identifiable":None,
                 "actor_favorable_outcome_a":None,"actor_favorable_outcome_b":None,"causal_link_a":None,"causal_link_b":None,
                 "strategies_distinct":None,"source_content_preserved":None,"language_age_appropriate_a":None,
                 "language_age_appropriate_b":None,"ending_consistent_a":None,"ending_consistent_b":None,
                 "uncertain":None,"reviewer_notes":""}}
            f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
            key_file.write(json.dumps({"review_id":row["review_id"],"source_index":r["source_index"],
                "source_sha256":r["source_sha256"],"candidate_features":r["candidate_features"],
                "side_a_strategy":"cooperative_success" if sides[0][0]=="A" else "non_cooperative_success",
                "side_b_strategy":"cooperative_success" if sides[1][0]=="A" else "non_cooperative_success",
                "non_cooperative_subtype":rw["non_cooperative_subtype"]},ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps({"review_rows":len(selected),"seed":args.seed,"output":str(args.output),
                      "answer_key":str(key_path),"subtype_coverage":{k:sum(1 for x in selected.values() if x["rewrite"]["non_cooperative_subtype"]==k) for k in sorted(by_subtype)}},indent=2))


def cost(args: argparse.Namespace) -> None:
    if args.hourly_rate_usd <= 0 or args.stories_per_second <= 0: raise ValueError("rate and measured stories/s must be positive")
    data={str(n):{"gpu_hours":n/args.stories_per_second/3600,
                  "usd_inference_only":n/args.stories_per_second/3600*args.hourly_rate_usd,
                  "usd_with_startup_hours":(n/args.stories_per_second/3600+args.startup_hours)*args.hourly_rate_usd}
          for n in (1000,100000,300000)}
    print(json.dumps({"stories_per_second":args.stories_per_second,"hourly_rate_usd":args.hourly_rate_usd,
                      "startup_hours_included_each_projection":args.startup_hours,"scenarios":data},indent=2))


def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description=__doc__); sp=p.add_subparsers(dest="command",required=True)
    prep=sp.add_parser("prepare",help="verify source hashes and create deterministic theme-balanced selection")
    prep.add_argument("--sample",type=Path,default=DEFAULT_SAMPLE); prep.add_argument("--index",type=Path,default=DEFAULT_INDEX)
    prep.add_argument("--review",type=Path,default=DEFAULT_REVIEW); prep.add_argument("--subtypes",type=Path,default=DEFAULT_SUBTYPES)
    prep.add_argument("--count",type=int,choices=(100,1000),default=100); prep.add_argument("--seed",type=int,default=20261107)
    prep.add_argument("--output",type=Path,required=True); prep.set_defaults(func=prepare)
    run=sp.add_parser("run",help="run resumable vLLM generation on manually provisioned GPU")
    run.add_argument("--selection",type=Path,required=True); run.add_argument("--output",type=Path,required=True)
    run.add_argument("--count",type=int,choices=(100,1000),default=100); run.add_argument("--benchmark",action="store_true")
    run.add_argument("--approve-1000-pilot",action="store_true"); run.add_argument("--hourly-rate-usd",type=float,required=True)
    run.add_argument("--approve-paid-inference",action="store_true",help="explicitly authorize billable model inference")
    run.add_argument("--lambda-instance-id",required=True,help="operator attestation of the manually provisioned Lambda instance")
    run.add_argument("--model-id"); run.add_argument("--model-revision"); run.set_defaults(func=run_generation)
    val=sp.add_parser("validate",help="run separate semantic-validation inference on accepted rewrites")
    val.add_argument("--run",type=Path,required=True); val.add_argument("--hourly-rate-usd",type=float,required=True)
    val.add_argument("--approve-paid-inference",action="store_true",help="explicitly authorize billable model inference")
    val.add_argument("--lambda-instance-id",required=True,help="operator attestation of the manually provisioned Lambda instance")
    val.add_argument("--model-id"); val.add_argument("--model-revision"); val.set_defaults(func=run_validation)
    rep=sp.add_parser("report",help="summarize generation, subtype, validation, lengths, throughput, and costs")
    rep.add_argument("--run",type=Path,required=True); rep.add_argument("--output",type=Path,required=True)
    rep.add_argument("--human-review",type=Path); rep.add_argument("--human-review-key",type=Path)
    rep.add_argument("--minimum-human-review-rows",type=int,default=50)
    rep.add_argument("--hourly-rate-usd",type=float); rep.add_argument("--examples",type=int,default=3); rep.set_defaults(func=report)
    review=sp.add_parser("review-sample",help="export a blinded, subtype-stratified human review pack")
    review.add_argument("--run",type=Path,required=True); review.add_argument("--output",type=Path,required=True)
    review.add_argument("--count",type=int,default=50); review.add_argument("--seed",type=int,default=20261109); review.set_defaults(func=review_sample)
    co=sp.add_parser("cost",help="project scale cost from measured throughput and actual account rate")
    co.add_argument("--stories-per-second",type=float,required=True); co.add_argument("--hourly-rate-usd",type=float,required=True)
    co.add_argument("--startup-hours",type=float,default=0.5); co.set_defaults(func=cost)
    return p


def main() -> None:
    args=parser().parse_args()
    try: args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__": main()
