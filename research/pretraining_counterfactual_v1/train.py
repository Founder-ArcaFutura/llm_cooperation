"""Single-GPU, paired-initialization GPT-2 pretraining and representative benchmark.

Nothing runs on import. Explicit --execute required for init/benchmark/train/eval.
Run on a manually provisioned Lambda instance; this module never provisions one.
"""
import argparse
from collections import deque
import copy
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import time

import numpy as np

from .data import CONDITIONS, canonical, digest, file_hash, get_meta, weights, write_json


def checked_positive(value, name):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def projection(tokens, tps, hourly, seeds=1, overhead_hours=1, prior=0):
    for value, name in ((tokens, "tokens"), (tps, "throughput"), (hourly, "hourly"), (seeds, "seeds")):
        checked_positive(value, name)
    if not all(math.isfinite(x) for x in (overhead_hours, prior)) or min(overhead_hours, prior) < 0:
        raise ValueError("Negative overhead/prior cost")
    hours = 3 * seeds * tokens / tps / 3600
    total = (hours + overhead_hours) * hourly + prior
    return {"tokens_per_arm": tokens, "seeds": seeds, "training_gpu_hours": hours,
            "overhead_gpu_hours": overhead_hours, "prior_cost_usd": prior,
            "hourly_usd": hourly, "projected_usd": total,
            "within_target_100": total <= 100, "within_ceiling_150": total <= 150,
            "assumption": "Sequential single GPU; overhead includes evaluation, checkpoints, setup and idle time"}


def reserve_budget(path, key, amount, prior):
    """Conservative, cumulative reservation; retain full reservation after interruption.

    Use ONE shared file for all benchmark/arm/seed launches. Manual instance idle,
    scoring and untracked costs must be included in prior (a nondecreasing floor).
    """
    checked_positive(amount, "reservation")
    if not math.isfinite(prior) or prior < 0:
        raise ValueError("prior cost must be nonnegative")
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS reservations(key TEXT PRIMARY KEY, usd REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS prior(usd REAL)")
    db.commit()
    try:
        db.execute("BEGIN IMMEDIATE")
        old_prior = db.execute("SELECT COALESCE(MAX(usd),0) FROM prior").fetchone()[0]
        prior = max(prior, old_prior)
        row = db.execute("SELECT usd FROM reservations WHERE key=?", (key,)).fetchone()
        if row and abs(row[0] - amount) > 1e-8:
            raise ValueError("Cannot change an existing job's reservation")
        spent = db.execute("SELECT COALESCE(SUM(usd),0) FROM reservations").fetchone()[0]
        if prior + spent + (0 if row else amount) > 150:
            raise ValueError("Cumulative reservations exceed $150 hard ceiling")
        db.execute("INSERT INTO prior VALUES (?)", (prior,))
        db.execute("INSERT OR IGNORE INTO reservations VALUES (?,?)", (key, amount))
        db.commit()
    finally:
        db.close()


class Sampler:
    """Deterministic weighted document draws, then lossless EOS-separated packing.

    Uniform original document weights preserve source multiplicity. Cross-block
    next-token labels retain every consumed token; no discarded block boundaries.
    State includes partial document, RNG, and actual token exposures per source ID.
    """
    def __init__(self, source, condition, strength, seed):
        self.db = sqlite3.connect(f"file:{Path(source).resolve().as_posix()}?mode=ro", uri=True)
        rows = self.db.execute("SELECT id,coop,compete FROM docs ORDER BY id").fetchall()
        if not rows:
            raise ValueError("Empty training corpus")
        ids, coop, compete = zip(*rows)
        self.ids = np.asarray(ids)
        self.coop = np.asarray(coop); self.compete = np.asarray(compete)
        w = weights(self.coop, self.compete, condition, strength)
        self.cdf = np.cumsum(w / w.sum()); self.cdf[-1] = 1
        self.rng = np.random.default_rng(seed)
        self.pending = deque()
        self.exposures = {}
        self.draws = 0
        self.coop_sum = 0.0; self.compete_sum = 0.0

    def take(self, n):
        while len(self.pending) < n:
            pos = int(np.searchsorted(self.cdf, self.rng.random(), side="right"))
            doc_id = int(self.ids[pos])
            blob = self.db.execute("SELECT tokens FROM docs WHERE id=?", (doc_id,)).fetchone()[0]
            tokens = np.frombuffer(blob, dtype="<u4")
            self.pending.extend((int(t), doc_id, pos) for t in tokens)
            self.draws += 1
        result = []
        for _ in range(n):
            token, doc_id, pos = self.pending.popleft()
            result.append(token)
            self.exposures[doc_id] = self.exposures.get(doc_id, 0) + 1
            self.coop_sum += float(self.coop[pos]); self.compete_sum += float(self.compete[pos])
        return result

    def state(self):
        return copy.deepcopy({"rng": self.rng.bit_generator.state, "pending": list(self.pending),
                "exposures": self.exposures, "draws": self.draws,
                "coop_sum": self.coop_sum, "compete_sum": self.compete_sum})

    def restore(self, state):
        state = copy.deepcopy(state)
        self.rng.bit_generator.state = state["rng"]
        self.pending = deque(state["pending"]); self.exposures = state["exposures"]
        self.draws = state["draws"]; self.coop_sum = state["coop_sum"]; self.compete_sum = state["compete_sum"]


def seed_all(seed):
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # Identical initialization is exact. Bitwise training determinism still depends
    # on hardware/software kernels; record environment rather than promise it.


def init_model(source, output, seed):
    import torch
    from transformers import AutoTokenizer, GPT2Config, GPT2LMHeadModel
    output = Path(output)
    if output.exists():
        raise FileExistsError("Initialization is immutable; choose a new output")
    tok = AutoTokenizer.from_pretrained(Path(source).parent / "tokenizer", local_files_only=True)
    seed_all(seed)
    config = GPT2Config(vocab_size=len(tok), n_positions=1024, n_ctx=1024,
                        n_embd=512, n_layer=6, n_head=8, resid_pdrop=0,
                        embd_pdrop=0, attn_pdrop=0, bos_token_id=tok.eos_token_id,
                        eos_token_id=tok.eos_token_id, use_cache=False)
    model = GPT2LMHeadModel(config)  # Random weights. NEVER from pretrained weights.
    count = sum(p.numel() for p in model.parameters())
    if not 30_000_000 <= count <= 50_000_000:
        raise ValueError(f"Unexpected parameter count: {count}")
    output.mkdir(parents=True)
    model.save_pretrained(output); tok.save_pretrained(output)
    write_json(output / "initialization.json", {"seed": seed, "parameters": count,
               "weights_sha256": file_hash(output / "model.safetensors"),
               "torch": torch.__version__, "config": config.to_dict()})


def run(a):
    started = time.monotonic()
    for value, name in ((a.tokens, "tokens"), (a.batch, "batch"), (a.accumulation, "accumulation"),
                        (a.seconds, "seconds"), (a.hourly, "hourly"), (a.checkpoint_steps, "checkpoint steps")):
        checked_positive(value, name)
    if not 1 <= a.context <= 1024 or a.warmup_steps < 0 or a.lr <= 0:
        raise ValueError("Invalid context, warmup or learning rate")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no accidental CPU experiment")
    output = Path(a.output); output.mkdir(parents=True, exist_ok=True)
    initial = json.loads((Path(a.init) / "initialization.json").read_text())
    if initial["seed"] != a.seed:
        raise ValueError("Run seed must match paired initialization seed")
    if file_hash(Path(a.init) / "model.safetensors") != initial["weights_sha256"]:
        raise ValueError("Initial weights hash mismatch")
    source = Path(a.source)
    from .data import connect, provenance
    db = connect(source)
    if not get_meta(db, "complete") and not a.benchmark:
        raise ValueError("Full training requires a complete corpus census")
    dataset_identity = get_meta(db, "identity"); db.close()
    validation = None
    validation_identity = None
    if a.validation_source:
        validation, validation_identity = validation_tokens(source, a.validation_source, a.validation_tokens)
    elif not a.benchmark:
        raise ValueError("Training requires --validation-source (separate upstream validation split)")
    tokenizer = AutoTokenizer.from_pretrained(source.parent / "tokenizer", local_files_only=True)
    initial_tokenizer = AutoTokenizer.from_pretrained(a.init, local_files_only=True)
    if tokenizer.get_vocab() != initial_tokenizer.get_vocab() or tokenizer.backend_tokenizer.to_str() != initial_tokenizer.backend_tokenizer.to_str():
        raise ValueError("Initialization/corpus tokenizer mismatch")
    identity = {"initial": initial, "dataset_identity": dataset_identity, "database_sha256": file_hash(source),
                "condition": a.condition, "strength": a.strength, "seed": a.seed,
                "tokens": a.tokens, "batch": a.batch, "accumulation": a.accumulation,
                "context": a.context, "lr": a.lr, "warmup_steps": a.warmup_steps,
                "weight_decay": .1, "betas": [.9, .95], "epsilon": 1e-8, "gradient_clip": 1,
                "benchmark": a.benchmark, "seconds": a.seconds, "hourly": a.hourly,
                "validation": validation_identity,
                "implementation": provenance(), "gpu": torch.cuda.get_device_name(),
                "precision": "bfloat16", "cuda": torch.version.cuda}
    signature = digest(identity)
    manifest = output / "run.json"
    if manifest.exists() and json.loads(manifest.read_text())["signature"] != signature:
        raise ValueError("Run identity mismatch")
    latest_path = output / "latest.json"
    if manifest.exists() and not a.resume:
        raise ValueError("Existing run requires --resume")
    if a.resume and not latest_path.exists():
        raise ValueError("No committed checkpoint to resume")
    reserve_budget(a.ledger, str(output.resolve()), a.seconds * a.hourly / 3600, a.prior_cost)
    write_json(manifest, {"signature": signature, "identity": identity})
    seed_all(a.seed)
    model = AutoModelForCausalLM.from_pretrained(a.init, local_files_only=True).cuda().train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=a.lr, betas=(.9, .95), weight_decay=.1)
    sampler = Sampler(source, a.condition, a.strength, a.seed)
    step = consumed = 0; elapsed_before = 0.; rolling = None
    (output / "train.jsonl").touch(exist_ok=True)
    if a.resume:
        latest = json.loads(latest_path.read_text())
        checkpoint = output / latest["directory"]
        if any(file_hash(checkpoint / k) != v for k, v in latest["hashes"].items()):
            raise ValueError("Checkpoint hash mismatch")
        # Local trusted checkpoint only: optimizer and RNG require non-tensor objects.
        state = torch.load(checkpoint / "state.pt", map_location="cpu", weights_only=False)
        if state["signature"] != signature:
            raise ValueError("Checkpoint identity mismatch")
        model.load_state_dict(state["model"]); optimizer.load_state_dict(state["optimizer"])
        for opt_state in optimizer.state.values():
            for key, value in opt_state.items():
                if isinstance(value, torch.Tensor):
                    opt_state[key] = value.cuda()
        sampler.restore(state["sampler"])
        step = state["step"]; consumed = state["tokens"]; elapsed_before = state["wall_seconds"]
        rolling = state["rolling"]
        torch.set_rng_state(state["torch_rng"]); torch.cuda.set_rng_state_all(state["cuda_rng"])
        random.setstate(state["python_rng"]); np.random.set_state(state["numpy_rng"])
        # Remove only uncommitted log tail left by interruption.
        with (output / "train.jsonl").open("r+b") as f:
            f.truncate(state["log_bytes"])
        if (output / "validation.jsonl").exists():
            with (output / "validation.jsonl").open("r+b") as f:
                f.truncate(state["validation_log_bytes"])

    def elapsed():
        return elapsed_before + time.monotonic() - started

    def save():
        directory = f"checkpoint-{step:08d}"
        final = output / directory
        if final.exists():
            return
        temp = output / (directory + f".partial-{os.getpid()}-{time.time_ns()}")
        temp.mkdir()
        model.save_pretrained(temp); tokenizer.save_pretrained(temp)
        state = {"signature": signature, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                 "sampler": sampler.state(), "step": step, "tokens": consumed,
                 "wall_seconds": elapsed(), "rolling": rolling,
                 "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all(),
                 "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                 "validation_log_bytes": (output / "validation.jsonl").stat().st_size if (output / "validation.jsonl").exists() else 0,
                 "log_bytes": (output / "train.jsonl").stat().st_size if (output / "train.jsonl").exists() else 0}
        torch.save(state, temp / "state.pt")
        write_json(temp / "receipt.json", {"signature": signature, "step": step, "tokens": consumed,
                                           "gpu_hours": elapsed() / 3600, "projected_charge_usd": elapsed() * a.hourly / 3600})
        temp.rename(final)
        record = {"directory": directory, "hashes": {p.name: file_hash(p) for p in final.iterdir() if p.is_file()}}
        write_json(output / "latest.partial.json", record)
        os.replace(output / "latest.partial.json", latest_path)

    if not a.resume:
        save()  # Permit recovery even before the first optimizer checkpoint.
    target_steps = math.ceil(a.tokens / (a.batch * a.context * a.accumulation))
    measured_tokens = 0; measured_seconds = 0.; measurements = []
    last_duration = 1.
    while consumed < a.tokens and elapsed() + max(30., 2 * last_duration) < a.seconds:
        torch.cuda.synchronize(); tick = time.monotonic()
        optimizer.zero_grad(set_to_none=True)
        step_tokens = min(a.batch * a.context * a.accumulation, a.tokens - consumed)
        losses = []
        # Exact prediction-token budget, including final partial step.
        remaining = step_tokens
        while remaining:
            batch = min(a.batch, math.ceil(remaining / a.context))
            length = min(a.context, remaining // batch)
            count = batch * length
            if rolling is None:
                rolling = sampler.take(1)[0]
            seq = [rolling] + sampler.take(count)
            rolling = seq[-1]
            # Consecutive rows overlap by one token, preserving boundary targets.
            x = torch.tensor(seq[:-1], device="cuda").reshape(batch, length)
            y = torch.tensor(seq[1:], device="cuda").reshape(batch, length)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(input_ids=x).logits
                loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), y.reshape(-1))
            (loss * count / step_tokens).backward()
            losses.append((float(loss.detach()), count)); remaining -= count
        lr_scale = min(1., (step + 1) / max(1, a.warmup_steps))
        if step >= a.warmup_steps:
            lr_scale = .1 + .9 * .5 * (1 + math.cos(math.pi * min(1., (step - a.warmup_steps) / max(1, target_steps - a.warmup_steps))))
        for group in optimizer.param_groups:
            group["lr"] = a.lr * lr_scale
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        optimizer.step(); torch.cuda.synchronize()
        duration = time.monotonic() - tick
        last_duration = duration
        step += 1; consumed += step_tokens
        if step > 5:
            measured_tokens += step_tokens; measured_seconds += duration
            measurements.append(step_tokens / duration)
        record = {"step": step, "tokens": consumed, "loss": sum(l*n for l,n in losses)/step_tokens,
                  "lr": optimizer.param_groups[0]["lr"], "wall_seconds": elapsed(),
                  "gpu_hours": elapsed()/3600, "projected_charge_usd": elapsed()*a.hourly/3600,
                  "step_tokens_per_second": step_tokens/duration, "document_draws": sampler.draws,
                  "source_documents_seen": len(sampler.exposures),
                  "coop_exposure_proxy": sampler.coop_sum / sum(sampler.exposures.values()),
                  "competition_exposure_proxy": sampler.compete_sum / sum(sampler.exposures.values())}
        with (output / "train.jsonl").open("a", encoding="utf-8") as f:
            f.write(canonical(record)+"\n")
        print(canonical(record), flush=True)
        if step % a.checkpoint_steps == 0:
            if validation is not None:
                record["validation"] = validation_loss(model, validation, a.context)
                with (output / "validation.jsonl").open("a", encoding="utf-8") as f:
                    f.write(canonical({"step": step, "tokens": consumed, **record["validation"]}) + "\n")
            save()
    if validation is not None:
        with (output / "validation.jsonl").open("a", encoding="utf-8") as f:
            f.write(canonical({"step": step, "tokens": consumed, **validation_loss(model, validation, a.context)}) + "\n")
    save()
    write_json(output / "summary.json", {"signature": signature, "tokens": consumed, "step": step,
               "complete": consumed == a.tokens, "gpu_hours": elapsed()/3600,
               "projected_charge_usd": elapsed()*a.hourly/3600,
               "measured_tokens_per_second": measured_tokens / measured_seconds if measured_seconds else None,
               "p10_step_tokens_per_second": float(np.quantile(measurements, .1)) if measurements else None,
               "measurement_scope": "After 5 warmup steps; real SQLite sampling, forward/backward/optimizer; excludes checkpoints/evaluation",
               "document_token_exposures": sampler.exposures})


def validation_tokens(training_source, source, limit):
    """Fixed original validation prefix; reject exact-text train overlap."""
    if limit < 2:
        raise ValueError("Validation token limit must be >= 2")
    db = sqlite3.connect(source)
    identity = get_meta(db, "identity")
    db.execute("ATTACH DATABASE ? AS training", (str(training_source),))
    train_db = sqlite3.connect(training_source)
    train_identity = get_meta(train_db, "identity"); train_db.close()
    keys = ("dataset", "dataset_revision", "tokenizer", "tokenizer_revision")
    if any(identity["config"][k] != train_identity["config"][k] for k in keys):
        raise ValueError("Validation must use same pinned dataset/tokenizer")
    if identity["config"]["split"] != "validation" or train_identity["config"]["split"] != "train":
        raise ValueError("Require distinct upstream train/validation splits")
    result = []
    for doc_id, blob in db.execute("SELECT id,tokens FROM docs ORDER BY id"):
        if db.execute("SELECT 1 FROM training.docs WHERE sha=(SELECT sha FROM docs WHERE id=?) LIMIT 1", (doc_id,)).fetchone():
            continue  # fixed held-out set excludes upstream exact-text leakage
        result.extend(np.frombuffer(blob, dtype="<u4").tolist())
        if len(result) >= limit:
            break
    db.close()
    result = result[:limit]
    if len(result) < 2:
        raise ValueError("No nonoverlapping validation tokens")
    return result, {"database_sha256": file_hash(source), "identity": identity, "tokens": len(result),
                    "token_sha256": digest(result), "selection": "original source order; exclude exact train duplicates"}


def validation_loss(model, tokens, context):
    import torch
    model.eval()
    total = 0.; count = 0
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for start in range(0, len(tokens)-1, context):
            seq = tokens[start:start+context+1]
            x = torch.tensor([seq[:-1]], device="cuda")
            y = torch.tensor(seq[1:], device="cuda")
            logits = model(input_ids=x).logits
            loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), y, reduction="sum")
            total += float(loss); count += len(seq)-1
    model.train()
    return {"loss": total/count, "perplexity": math.exp(min(50, total/count)), "prediction_tokens": count}


def evaluate(checkpoint, output):
    from llm_cooperation.harness.runner import run_experiment, run_calibration
    from llm_cooperation.analysis.pipeline import analyze_results
    output = Path(output)
    if output.exists():
        raise FileExistsError("Choose a new evaluation output")
    output.mkdir(parents=True)
    identity = {"checkpoint": str(Path(checkpoint).resolve()),
                "weights_sha256": file_hash(Path(checkpoint)/"model.safetensors"),
                "instruments": {p: file_hash(p) for p in ("data/scenarios.json", "data/calibration_bank.json")}}
    receipt = Path(checkpoint) / "receipt.json"
    identity["training_checkpoint"] = json.loads(receipt.read_text()) if receipt.exists() else None
    write_json(output / "identity.json", identity)
    for order in (0, 1, 2):
        root = output / f"order-{order}"
        _, calibration = run_calibration(str(checkpoint), output_dir=str(root / "calibration"),
                                         device="cuda", order_replication=order)
        result = run_experiment(str(checkpoint), scenarios_path="data/scenarios.json",
                                output_dir=str(root / "cpi"), device="cuda", order_replication=order)
        analysis = analyze_results(str(result), output_dir=str(root / "analysis"))
        write_json(root / "cooperation_metrics.json", {
            "choice_rate": analysis["overall_boot"], "conditional_probability": analysis["prob_boot"],
            "calibration_pass": calibration["status"] == "PASS",
            "interpretation": "Exploratory; calibration failure limits interpretation as cooperation propensity"})
        write_json(root / "calibration_status.json", calibration)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("init"); s.add_argument("--source", required=True); s.add_argument("--output", required=True)
    s.add_argument("--seed", type=int, default=1); s.add_argument("--execute", action="store_true")
    s = sub.add_parser("project")
    s.add_argument("--tokens", type=int, required=True); s.add_argument("--tps", type=float, required=True)
    s.add_argument("--hourly", type=float, required=True); s.add_argument("--seeds", type=int, default=1)
    s.add_argument("--overhead-hours", type=float, default=1); s.add_argument("--prior-cost", type=float, default=0)
    s = sub.add_parser("eval"); s.add_argument("--checkpoint", required=True); s.add_argument("--output", required=True)
    s.add_argument("--execute", action="store_true")
    s = sub.add_parser("train")
    for flag in ("source", "init", "output", "ledger"):
        s.add_argument("--"+flag, required=True)
    s.add_argument("--condition", choices=CONDITIONS, required=True)
    s.add_argument("--strength", type=float, required=True); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--tokens", type=int, required=True); s.add_argument("--context", type=int, default=512)
    s.add_argument("--batch", type=int, default=8); s.add_argument("--accumulation", type=int, default=4)
    s.add_argument("--lr", type=float, default=.0006); s.add_argument("--warmup-steps", type=int, default=100)
    s.add_argument("--checkpoint-steps", type=int, default=500); s.add_argument("--seconds", type=float, required=True)
    s.add_argument("--hourly", type=float, required=True); s.add_argument("--prior-cost", type=float, default=0)
    s.add_argument("--resume", action="store_true"); s.add_argument("--benchmark", action="store_true")
    s.add_argument("--validation-source"); s.add_argument("--validation-tokens", type=int, default=32768)
    s.add_argument("--execute", action="store_true")
    a = p.parse_args()
    if a.command == "project":
        print(json.dumps(projection(a.tokens, a.tps, a.hourly, a.seeds, a.overhead_hours, a.prior_cost), indent=2))
        return
    if not a.execute:
        p.error("Execution is opt-in: add --execute only when you intend to run this stage")
    if a.command == "init":
        init_model(a.source, a.output, a.seed)
    elif a.command == "eval":
        evaluate(a.checkpoint, a.output)
    else:
        run(a)


if __name__ == "__main__":
    main()
