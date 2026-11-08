"""Bounded LOCAL TinyStories classifier validation, independent of training/census.

Raw source, text and token cache live under ignored outputs/. Only 10,000 random
stories are embedded, including a nested 500-story smoke. No Modal/cloud APIs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time

import numpy as np

from .data import HERE, canonical, digest, file_hash, semantic_scores, validate_config, window_spans, write_json

DEFAULT_CACHE = HERE / "outputs" / "semantic_pilot"
DEFAULT_REPORT = HERE / "pilot_artifacts"
SEED = 20261107
SAMPLE_SIZE = 10000
SMOKE_SIZE = 500


def download(url, path, expected_size=None):
    """Verified HTTPS public downloads; no HF credentials or unrelated files."""
    import httpx
    path = Path(path)
    if path.exists() and (expected_size is None or path.stat().st_size == expected_size):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with httpx.Client(follow_redirects=True, timeout=180) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with temporary.open("wb") as f:
                for chunk in response.iter_bytes(1024 * 1024):
                    f.write(chunk)
    if expected_size is not None and temporary.stat().st_size != expected_size:
        raise ValueError("Download size mismatch")
    temporary.replace(path)


def prepare(cache, report_dir):
    import httpx
    import pyarrow.parquet as pq
    cache = Path(cache); report_dir = Path(report_dir)
    cache.mkdir(parents=True, exist_ok=True); report_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads((HERE / "config.json").read_text())
    validate_config(config)
    url = f"https://huggingface.co/api/datasets/{config['dataset']}/revision/{config['dataset_revision']}"
    response = httpx.get(url, params={"blobs": "true"}, timeout=60)
    response.raise_for_status(); info = response.json()
    if info["sha"] != config["dataset_revision"]:
        raise ValueError("Pinned metadata mismatch")
    files = sorted((x for x in info["siblings"] if x["rfilename"].startswith("data/train-")
                    and x["rfilename"].endswith(".parquet")), key=lambda x: x["rfilename"])
    if len(files) != 4:
        raise ValueError("Expected the four pinned train parquet shards")
    shards = []
    offset = 0
    for item in files:
        name = item["rfilename"]
        path = cache / Path(name).name
        print("Downloading/validating", name, flush=True)
        download(f"https://huggingface.co/datasets/{config['dataset']}/resolve/{config['dataset_revision']}/{name}",
                 path, item.get("size"))
        sha = file_hash(path)
        expected = item.get("lfs", {}).get("sha256")
        if expected and sha != expected:
            raise ValueError("Source LFS hash mismatch")
        count = pq.ParquetFile(path).metadata.num_rows
        shards.append({"file": name, "sha256": sha, "size": path.stat().st_size,
                       "rows": count, "source_offset": offset})
        offset += count
    # Python random.sample: simple random sample WITHOUT replacement from all rows.
    selected = random.Random(SEED).sample(range(offset), SAMPLE_SIZE)
    smoke = set(selected[:SMOKE_SIZE])
    wanted = set(selected)
    records = []
    for shard in shards:
        file = pq.ParquetFile(cache / Path(shard["file"]).name)
        start = shard["source_offset"]
        for group in range(file.num_row_groups):
            size = file.metadata.row_group(group).num_rows
            local = sorted(i - start for i in wanted if start <= i < start + size)
            if local:
                texts = file.read_row_group(group, columns=["text"]).column("text")
                for i in local:
                    text = texts[i].as_py()
                    records.append({"source_index": start+i, "source_shard": shard["file"],
                                    "shard_row": start+i-shard["source_offset"],
                                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                    "smoke": start+i in smoke, "text": text})
            start += size
    records.sort(key=lambda x: x["source_index"])
    if len(records) != SAMPLE_SIZE:
        raise ValueError("Sample incomplete")
    with (cache / "sample.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(canonical(record)+"\n")
    manifest = {"config": config, "source_rows": offset, "shards": shards,
                "sample_size": SAMPLE_SIZE, "smoke_size": SMOKE_SIZE,
                "sampling": "Python random.Random(seed).sample(range(source_rows), 10000), without replacement",
                "seed": SEED, "smoke_selection": "first 500 elements of seeded random draw, not source prefix",
                "sample_text_cache_sha256": file_hash(cache / "sample.jsonl"),
                "sample_identity_sha256": digest([{k: v for k, v in r.items() if k != "text"} for r in records])}
    write_json(report_dir / "sample_manifest.json", manifest)
    with (report_dir / "sample_index.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(canonical({k: v for k, v in r.items() if k != "text"}) + "\n")
    # Tokenizer files only: never download GPT-2 model weights.
    tok_dir = cache / "tokenizer"
    for name in ("config.json", "tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt"):
        download(f"https://huggingface.co/{config['tokenizer']}/resolve/{config['tokenizer_revision']}/{name}", tok_dir / name)
    write_json(report_dir / "tokenizer_manifest.json", {
        "repo": config["tokenizer"], "revision": config["tokenizer_revision"],
        "files": {p.name: file_hash(p) for p in tok_dir.iterdir() if p.is_file()}})
    write_json(report_dir / "config.json", config)
    print(canonical({"source_rows": offset, "sample_size": len(records), "smoke": len(smoke)}), flush=True)


def score_sample(cache, report_dir, encoder_path, threads=4, smoke_only=False):
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer
    from .data import provenance
    cache = Path(cache); report_dir = Path(report_dir)
    config = json.loads((report_dir / "config.json").read_text())
    validate_config(config)
    manifest = json.loads((report_dir / "sample_manifest.json").read_text())
    if file_hash(cache / "sample.jsonl") != manifest["sample_text_cache_sha256"]:
        raise ValueError("Sample cache changed")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    records = [json.loads(line) for line in (cache / "sample.jsonl").read_text(encoding="utf-8").splitlines()]
    if smoke_only:
        records = [r for r in records if r["smoke"]]
    # Exact cached encoder, no network/model weight download.
    encoder_path = Path(encoder_path)
    if encoder_path.name != config["encoder_revision"]:
        raise ValueError("Encoder cache path must name pinned revision")
    encoder = SentenceTransformer(str(encoder_path), device="cpu", local_files_only=True)
    encoder.max_seq_length = 512
    tok = AutoTokenizer.from_pretrained(cache / "tokenizer", local_files_only=True)
    names = sorted(config["anchors"])
    centers = []
    for name in names:
        vectors = encoder.encode([config["prefix"]+s for s in config["anchors"][name]],
                                  normalize_embeddings=True, show_progress_bar=False)
        center = vectors.mean(axis=0); centers.append(center / np.linalg.norm(center))
    centers = np.asarray(centers)
    score_path = report_dir / "scores.jsonl"
    existing = {}
    if score_path.exists():
        existing = {r["source_index"]: r for r in map(json.loads, score_path.read_text().splitlines())}
    identity = {"config_sha256": digest(config), "sample_identity_sha256": manifest["sample_identity_sha256"],
                "implementation": provenance(), "device": "cpu", "threads": threads,
                "encoder_weights_sha256": file_hash(encoder_path / "model.safetensors"),
                "batching": "32 stories at a time; flattened windows, encoder batch_size=32"}
    identity_path = report_dir / "scorer_identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError("Scorer identity changed; do not mix runs")
    write_json(identity_path, identity)
    pending = [r for r in records if r["source_index"] not in existing]
    started = time.monotonic(); windows_done = 0; done = 0
    with score_path.open("a", encoding="utf-8") as out:
        for start in range(0, len(pending), 32):
            batch = pending[start:start+32]
            texts = []; spans_by_doc = []; lengths = []
            for row in batch:
                spans = window_spans(row["text"], encoder.tokenizer, config["window_tokens"], config["stride_tokens"])
                spans_by_doc.append(spans); lengths.append(len(spans))
                texts.extend(config["prefix"]+row["text"][a:b] for a,b in spans)
            if any(len(encoder.tokenizer(t)["input_ids"]) > 512 for t in texts):
                raise ValueError("Encoder input truncation")
            embeddings = encoder.encode(texts, batch_size=config["batch_size"],
                                         normalize_embeddings=True, show_progress_bar=False)
            sims = embeddings @ centers.T
            offset = 0
            for row, spans, length in zip(batch, spans_by_doc, lengths):
                s = sims[offset:offset+length]; offset += length
                coop, compete, p = semantic_scores(s, names, config["temperature"])
                result = {k: v for k,v in row.items() if k != "text"}
                result.update({"tokens_with_eos": len(tok.encode(row["text"], add_special_tokens=False))+1,
                               "coop_present": coop, "competition_success_margin": compete,
                               "names": names, "spans": spans, "cosines": s.tolist(),
                               "proxy_probabilities": p.tolist(),
                               "max_cosines": {name: float(s[:,i].max()) for i,name in enumerate(names)},
                               "max_probabilities": {name: float(p[:,i].max()) for i,name in enumerate(names)}})
                # Reward-versus-failure contrast within each identical window.
                result["cooperation_reward_margin"] = float(np.maximum(
                    p[:,names.index("cooperation_success")]-p[:,names.index("cooperation_failure")], 0).max())
                out.write(canonical(result)+"\n")
            out.flush(); os.fsync(out.fileno())
            done += len(batch); windows_done += len(texts)
            print(canonical({"new_stories": done, "windows": windows_done,
                              "seconds": time.monotonic()-started}), flush=True)
    elapsed = time.monotonic()-started
    receipt_path = report_dir / ("smoke_receipt.json" if smoke_only else "sample_receipt.json")
    write_json(receipt_path, {"requested": len(records), "newly_scored": done,
                             "previously_scored": len(records)-len(pending), "seconds": elapsed,
                             "windows": windows_done, "stories_per_second": done/elapsed if done else None,
                             "scope": "Embedding inference only; no LM training; no full corpus embeddings"})


def sentences(text):
    return [{"start": m.start(), "end": m.end(), "text": m.group()} for m in
            re.finditer(r'[^.!?]+(?:[.!?]+|$)', text) if m.group().strip()]


def review_sample(cache, report_dir):
    cache = Path(cache); report_dir = Path(report_dir)
    rows = sorted([json.loads(line) for line in (report_dir / "scores.jsonl").read_text().splitlines()],
                  key=lambda r: r["source_index"])
    if len(rows) != SAMPLE_SIZE or len({r["source_index"] for r in rows}) != SAMPLE_SIZE:
        raise ValueError("Review selection requires the complete 10,000-story sample")
    rng = random.Random(SEED+1)
    selected = {}; available = {r["source_index"] for r in rows}
    by_id = {r["source_index"]: r for r in rows}
    # Draw independent random review first; strata cannot contaminate its prevalence estimate.
    for i in rng.sample(sorted(available), 40):
        selected[i] = "independent_random"; available.remove(i)
    rankings = [
        ("high_cooperation", lambda r: r["coop_present"], True),
        ("low_cooperation", lambda r: r["coop_present"], False),
        ("high_successful_competition", lambda r: r["competition_success_margin"], True),
        ("low_successful_competition", lambda r: r["competition_success_margin"], False),
        ("ambiguous", lambda r: sorted(r["max_probabilities"].values(), reverse=True)[0]-
         sorted(r["max_probabilities"].values(), reverse=True)[1], False)]
    for name, key, reverse in rankings:
        ordered = sorted((by_id[i] for i in sorted(available)), key=key, reverse=reverse)[:20]
        for r in ordered:
            selected[r["source_index"]] = name; available.remove(r["source_index"])
    raw = {r["source_index"]:r for r in map(json.loads, (cache / "sample.jsonl").read_text(encoding="utf-8").splitlines())}
    index = []
    with (cache / "review_full.jsonl").open("w", encoding="utf-8") as f:
        for i in sorted(selected):
            r = by_id[i]; text = raw[i]["text"]
            evidence = [s for s in sentences(text) if re.search(
                r'\b(help\w*|shar\w*|togeth\w*|team\w*|selfish\w*|win\w*|won|prize|race|trick\w*|steal|stole|kept|happy|sad|lost|learn\w*)\b',
                s["text"], re.I)]
            entry = {"source_index":i, "sha256":r["sha256"], "stratum":selected[i],
                     "text":text, "evidence_candidates":evidence,
                     "review_status":"unreviewed", "label_authority":"LLM-assisted judgments must remain provisional"}
            f.write(canonical(entry)+"\n")
            index.append({k:v for k,v in entry.items() if k not in ("text","evidence_candidates")})
    write_json(report_dir / "review_selection.json", {
        "seed":SEED+1, "size":len(index), "selection_order":"random40 then five disjoint score strata20",
        "rows":index, "raw_review_cache_sha256":file_hash(cache / "review_full.jsonl")})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "smoke", "score", "review"))
    p.add_argument("--cache", default=str(DEFAULT_CACHE)); p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--encoder-path", default=str(Path.home()/".cache/huggingface/hub/models--intfloat--multilingual-e5-base/snapshots/d13f1b27baf31030b7fd040960d60d909913633f"))
    p.add_argument("--threads", type=int, default=4); p.add_argument("--system-trust", action="store_true")
    a = p.parse_args()
    if a.system_trust:
        import pip._vendor.truststore as truststore
        truststore.inject_into_ssl()
    if a.command == "prepare":
        prepare(a.cache, a.report)
    elif a.command in ("smoke", "score"):
        score_sample(a.cache, a.report, a.encoder_path, a.threads, smoke_only=a.command=="smoke")
    else:
        review_sample(a.cache, a.report)


if __name__ == "__main__":
    main()
