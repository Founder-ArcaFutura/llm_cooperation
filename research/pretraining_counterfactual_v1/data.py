"""Streaming semantic census. No network or model loading on import.

SQLite is the durable score/token cache, not a raw-dataset download. Transactions
allow restarting a scan; replay skips committed indices in the pinned HF stream.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CONDITIONS = ("original", "cooperation_depleted", "competition_enriched")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def provenance():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        commit = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        commit = None  # Slim scoring containers have source hashes but no Git binary.
    return {"git_commit": commit,
            "source_hashes": {p.name: file_hash(p) for p in HERE.glob("*.py")},
            "packages": {k: importlib.metadata.version(k) for k in
                         ("torch", "transformers", "datasets", "sentence-transformers", "numpy")}}


def validate_config(c):
    for k in ("dataset_revision", "encoder_revision", "tokenizer_revision"):
        if not re.fullmatch(r"[0-9a-f]{40}", c[k]):
            raise ValueError(f"{k} must be an immutable 40-character commit SHA")
    if not 0 < c["stride_tokens"] <= c["window_tokens"] <= 384:
        raise ValueError("Require 0 < stride <= window <= 384 (no silent encoder truncation)")
    if c["temperature"] <= 0 or c["batch_size"] <= 0:
        raise ValueError("Positive temperature and batch size required")
    expected = {"cooperation_success", "cooperation_failure", "competition_success",
                "competition_failure", "neutral"}
    if set(c["anchors"]) != expected or any(not x for x in c["anchors"].values()):
        raise ValueError("Five nonempty anchor groups required")


def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    db.execute("""CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY, sha TEXT NOT NULL, n INTEGER NOT NULL,
        coop REAL NOT NULL, compete REAL NOT NULL, detail TEXT NOT NULL,
        text TEXT NOT NULL, tokens BLOB NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS docs_sha ON docs(sha)")
    return db


def get_meta(db, key):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def set_meta(db, key, value):
    db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, canonical(value)))


def window_spans(text, tokenizer, window, stride):
    offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
    if not offsets:
        return [(0, len(text))]
    spans = []
    for start in range(0, len(offsets), stride):
        end = min(start + window, len(offsets))
        spans.append((offsets[start][0], offsets[end - 1][1]))
        if end == len(offsets):
            break
    return spans


def semantic_scores(similarity, names, temperature):
    """Soft semantic probabilities, NOT calibrated causal/outcome labels.

    Compare joint behavior/outcome anchors in the SAME window. Maximum across
    windows keeps relevant passages from being diluted by whole-story averaging.
    """
    logits = similarity / temperature
    p = np.exp(logits - logits.max(axis=1, keepdims=True))
    p /= p.sum(axis=1, keepdims=True)
    coop = p[:, names.index("cooperation_success")] + p[:, names.index("cooperation_failure")]
    # Successful competitive behavior must outrank failed competition in-window.
    success = p[:, names.index("competition_success")]
    failure = p[:, names.index("competition_failure")]
    return float(coop.max()), float(np.maximum(success - failure, 0).max()), p


def weights(coop, compete, condition, strength):
    if condition not in CONDITIONS or not math.isfinite(strength) or not 0 <= strength <= 20:
        raise ValueError("Unknown condition or strength outside [0,20]")
    if condition == "original":
        return np.ones_like(coop, dtype=float)
    score = -np.asarray(coop) if condition == "cooperation_depleted" else np.asarray(compete)
    return np.exp(strength * score)


def score(config, output, limit=0, device="cuda", max_seconds=3300):
    validate_config(config)
    from datasets import load_dataset
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer

    started = time.monotonic()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    db = connect(output / "corpus.sqlite")
    identity = {"config": config, "implementation": provenance()}
    old = get_meta(db, "identity")
    if old is not None and old != identity:
        raise ValueError("Cache identity mismatch: use a new version/output directory")
    set_meta(db, "identity", identity)
    if get_meta(db, "complete"):
        db.close()
        return
    db.commit()
    encoder = SentenceTransformer(config["encoder"], revision=config["encoder_revision"], device=device)
    encoder.max_seq_length = 512
    encoder_tok = encoder.tokenizer
    tok = AutoTokenizer.from_pretrained(config["tokenizer"], revision=config["tokenizer_revision"])
    tok.save_pretrained(output / "tokenizer")
    names = sorted(config["anchors"])
    centers = []
    for name in names:
        x = encoder.encode([config["prefix"] + s for s in config["anchors"][name]],
                           normalize_embeddings=True, show_progress_bar=False)
        center = np.mean(x, axis=0)
        centers.append(center / np.linalg.norm(center))
    centers = np.asarray(centers)
    next_id = db.execute("SELECT COALESCE(MAX(id)+1,0) FROM docs").fetchone()[0]
    stream = load_dataset(config["dataset"], revision=config["dataset_revision"],
                          split=config["split"], streaming=True)
    # skip does replay/transfer on restart but never re-embeds committed records.
    complete = True
    count = 0
    for index, row in enumerate(stream.skip(next_id), next_id):
        if (limit and index >= limit) or time.monotonic() - started >= max_seconds:
            complete = False
            break
        text = row["text"]
        spans = window_spans(text, encoder_tok, config["window_tokens"], config["stride_tokens"])
        passages = [config["prefix"] + text[a:b] for a, b in spans]
        if any(len(encoder_tok(s)["input_ids"]) > encoder.max_seq_length for s in passages):
            raise ValueError("Encoder input exceeds max_seq_length")
        vectors = encoder.encode(passages, batch_size=config["batch_size"],
                                 normalize_embeddings=True, show_progress_bar=False)
        sims = vectors @ centers.T
        coop, compete, probabilities = semantic_scores(sims, names, config["temperature"])
        tokens = tok.encode(text, add_special_tokens=False) + [tok.eos_token_id]
        detail = {"names": names, "spans": spans, "cosines": sims.tolist(),
                  "proxy_probabilities": probabilities.tolist()}
        db.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?)",
                   (index, hashlib.sha256(text.encode()).hexdigest(), len(tokens), coop,
                    compete, canonical(detail), text, np.array(tokens, dtype="<u4").tobytes()))
        count += 1
        if count % 100 == 0:
            db.commit()
            print(json.dumps({"documents": index + 1, "session_seconds": time.monotonic() - started}), flush=True)
    elapsed = time.monotonic() - started
    set_meta(db, "complete", complete)
    sessions = get_meta(db, "sessions") or []
    sessions.append({"documents": count, "wall_seconds": elapsed, "device": device})
    set_meta(db, "sessions", sessions)
    db.commit()
    db.close()
    write_json(output / "score_receipt.json", {"identity": identity, "complete": complete, "sessions": sessions})


def census(source, output, draws=1_000_000, audit_size=40):
    if draws <= 0:
        raise ValueError("Positive document-draw count required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    db = connect(source)
    rows = db.execute("SELECT id,sha,n,coop,compete FROM docs ORDER BY id").fetchall()
    if not rows:
        raise ValueError("Empty corpus")
    ids, hashes, n, coop, compete = zip(*rows)
    n, coop, compete = map(lambda x: np.asarray(x, dtype=float), (n, coop, compete))
    unique = {}
    for h, length in zip(hashes, n):
        unique.setdefault(h, length)
    identity = get_meta(db, "identity")
    report = {"identity": identity, "complete": bool(get_meta(db, "complete")),
              "documents": len(rows), "tokens_with_eos": int(n.sum()),
              "unique_texts": len(unique), "unique_text_tokens_with_eos": int(sum(unique.values())),
              "unique_definition": "exact UTF-8 text SHA256; not unique token types or deduplicated training",
              "scores": {}, "conditions": {}, "sessions": get_meta(db, "sessions")}
    for name, x in (("coop", coop), ("successful_competition", compete)):
        counts, edges = np.histogram(x, bins=np.linspace(0, 1, 41))
        report["scores"][name] = {"quantiles": np.quantile(x, [0, .1, .5, .9, .99, 1]).tolist(),
                                   "histogram": counts.tolist(), "edges": edges.tolist()}
    for condition in CONDITIONS:
        report["conditions"][condition] = []
        for strength in identity["config"]["strengths"]:
            w = weights(coop, compete, condition, strength)
            p = w / w.sum()
            token_p = p * n / (p @ n)
            # Aggregate duplicate mass for actual unique-text coverage.
            mass = {}
            for h, prob in zip(hashes, p):
                mass[h] = mass.get(h, 0.0) + prob
            expected_unique_tokens = sum(unique[h] * (-math.expm1(draws * math.log1p(-min(prob, 1-1e-16))))
                                         for h, prob in mass.items())
            report["conditions"][condition].append({
                "strength": strength, "document_ess": float(1 / (p @ p)),
                "max_document_probability": float(p.max()), "mean_document_tokens": float(p @ n),
                "expected_coop_token_share_proxy": float(token_p @ coop),
                "expected_competition_token_share_proxy": float(token_p @ compete),
                "expected_unique_text_tokens_after_draws": expected_unique_tokens,
                "document_draws": draws, "available_unique_text_tokens": int(sum(unique.values()))})
    write_json(output / "census.json", report)
    # Stratified extremes plus deterministic random middle; no model label asserted.
    chosen = set()
    rng = np.random.default_rng(20261107)
    for x in (coop, compete):
        for bucket in np.array_split(np.argsort(x), 10):
            if len(bucket):
                chosen.update(rng.choice(bucket, min(len(bucket), max(1, audit_size // 20)), replace=False).tolist())
    with (output / "audit.jsonl").open("w", encoding="utf-8") as f:
        for i in sorted(chosen):
            row = db.execute("SELECT text,detail FROM docs WHERE id=?", (ids[i],)).fetchone()
            f.write(canonical({"id": ids[i], "sha": hashes[i], "text": row[0], "detail": json.loads(row[1]),
                               "coop": coop[i], "compete": compete[i],
                               "review": {"behavior": None, "actor": None, "outcome": None,
                                          "causal_link_supported": None, "notes": None}}) + "\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, x, title in zip(axes, (coop, compete), ("Cooperation proxy", "Successful competition proxy")):
        ax.hist(x, bins=np.linspace(0, 1, 41)); ax.set(title=title, xlabel="Semantic score", ylabel="Documents")
    fig.tight_layout(); fig.savefig(output / "histograms.png"); plt.close(fig)
    write_json(output / "manifest.json", {"identity": identity, "database_sha256": file_hash(source),
                                         "complete": report["complete"],
                                         "files": {p.name: file_hash(p) for p in output.iterdir()
                                                   if p.name in ("census.json", "audit.jsonl", "histograms.png")}})
    (output / "feasibility.md").write_text(
        f"# Census feasibility\n\nComplete source scan: {report['complete']}. "
        f"{len(rows):,} documents; {int(n.sum()):,} tokens including EOS; "
        f"{int(sum(unique.values())):,} tokens across exact-unique texts.\n\n"
        "See census.json for the strength sweep, token-weighted shifts, ESS and expected unique coverage. "
        "All positive weights retain full support: enrichment increases repetition, not unique evidence. "
        "Review audit.jsonl for actor/outcome linkage and confounds before selecting a strength. "
        "Partial scans are prefix diagnostics and cannot establish full-corpus feasibility.\n",
        encoding="utf-8")
    db.close()
    return report


def export(source, output, condition, strength):
    """Versioned weighted distribution: preserve each original row, including duplicates."""
    db = connect(source)
    if not get_meta(db, "complete"):
        raise ValueError("Cannot freeze a partial census")
    weights(np.zeros(1), np.zeros(1), condition, strength)
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    identity = get_meta(db, "identity")
    target = output / "distribution.jsonl"
    with target.open("w", encoding="utf-8") as f:
        for i, sha, n, coop, compete, detail, text in db.execute(
                "SELECT id,sha,n,coop,compete,detail,text FROM docs ORDER BY id"):
            weight = float(weights(np.array([coop]), np.array([compete]), condition, strength)[0])
            f.write(canonical({"source_dataset": identity["config"]["dataset"],
                               "source_revision": identity["config"]["dataset_revision"],
                               "source_split": identity["config"]["split"], "source_index": i,
                               "sha256": sha, "text": text, "tokens_with_eos": n,
                               "coop": coop, "successful_competition": compete,
                               "sampling_weight": weight, "condition": condition}) + "\n")
    write_json(output / "manifest.json", {"identity": identity, "condition": condition,
                                         "strength": strength, "distribution_sha256": file_hash(target),
                                         "database_sha256": file_hash(source)})
    (output / "README.md").write_text(
        "---\nlicense: cdla-sharing-1.0\n---\n# TinyStories semantic reweighting\n\n"
        "Derived from https://huggingface.co/datasets/roneneldan/TinyStories. "
        "Synthetic stories, unchanged text. Keep upstream attribution and license terms. "
        "sampling_weight defines document draws with replacement; it is not a class label. "
        "Scores are unvalidated semantic proxies. See manifest.json for pinned sources and intervention.\n",
        encoding="utf-8")
    db.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score")
    s.add_argument("--config", default=str(HERE / "config.json")); s.add_argument("--output", required=True)
    s.add_argument("--limit", type=int, default=0); s.add_argument("--device", default="cuda")
    s.add_argument("--max-seconds", type=float, default=3300)
    s = sub.add_parser("census"); s.add_argument("--source", required=True); s.add_argument("--output", required=True)
    s.add_argument("--draws", type=int, default=1_000_000)
    s = sub.add_parser("export"); s.add_argument("--source", required=True); s.add_argument("--output", required=True)
    s.add_argument("--condition", choices=CONDITIONS, required=True); s.add_argument("--strength", type=float, required=True)
    s = sub.add_parser("publish"); s.add_argument("--folder", required=True); s.add_argument("--repo", required=True)
    s.add_argument("--tag", required=True); s.add_argument("--approve-publish", action="store_true")
    a = p.parse_args()
    if a.command == "score":
        if a.limit < 0 or a.max_seconds <= 0:
            p.error("Nonnegative limit and positive max-seconds required")
        score(json.loads(Path(a.config).read_text()), a.output, a.limit, a.device, a.max_seconds)
    elif a.command == "census":
        census(a.source, a.output, a.draws)
    elif a.command == "export":
        export(a.source, a.output, a.condition, a.strength)
    else:
        if not a.approve_publish:
            p.error("Publication requires --approve-publish after explicit user approval")
        from huggingface_hub import HfApi
        api = HfApi(); api.whoami()
        folder = Path(a.folder)
        manifest = json.loads((folder / "manifest.json").read_text())
        if file_hash(folder / "distribution.jsonl") != manifest["distribution_sha256"]:
            raise ValueError("Export hash mismatch")
        api.create_repo(a.repo, repo_type="dataset", private=True, exist_ok=True)
        commit = api.upload_folder(repo_id=a.repo, repo_type="dataset", folder_path=str(folder),
                                   commit_message=f"Frozen distribution {a.tag}")
        api.create_tag(a.repo, tag=a.tag, revision=commit.oid, repo_type="dataset")
        print(commit)


if __name__ == "__main__":
    main()
