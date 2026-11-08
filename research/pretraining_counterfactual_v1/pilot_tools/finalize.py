"""Compact, verify and inventory the report without putting raw stories in Git."""
import gzip
import json
from pathlib import Path

from research.pretraining_counterfactual_v1.data import file_hash, write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT


def finalize():
    root=DEFAULT_REPORT
    scores=root/"scores.jsonl"
    rows=[json.loads(x) for x in scores.read_text().splitlines()]
    if len(rows)!=10000 or len({r["source_index"] for r in rows})!=10000:
        raise ValueError("Only finalize a complete bounded sample")
    if any("text" in r for r in rows):
        raise ValueError("Full story text must not be in score artifacts")
    # Fixed gzip timestamp, preserving original complete capture locally.
    (root/"scores.jsonl.gz").write_bytes(gzip.compress(scores.read_bytes(),mtime=0))
    # Canonicalize derived report text BEFORE hashing. Keep the original score
    # capture untouched; its exact bytes remain in the gzip and its recorded hash.
    for path in root.iterdir():
        if path.is_file() and path.suffix in ('.json','.jsonl','.md') and path.name!='scores.jsonl':
            path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    write_json(root/"artifact_manifest.json",{
        "files":{p.name:file_hash(p) for p in sorted(root.iterdir()) if p.is_file()
                 and p.name not in ("artifact_manifest.json","scores.jsonl")},
        "uncompressed_scores_sha256":file_hash(scores),
        "raw_data_policy":"Source parquet, full sampled stories and review text remain in ignored outputs/; score artifact has no full story text",
        "review_authority":"Single Codex-assisted reading, provisional; not independent human gold labels",
        "scope":"500 nested smoke stories + 10,000 total random stories; no LM training/cloud/publication"})
    manifest=root/'artifact_manifest.json'
    manifest.write_bytes(manifest.read_bytes().replace(b'\r\n',b'\n'))


if __name__=="__main__":
    finalize()
