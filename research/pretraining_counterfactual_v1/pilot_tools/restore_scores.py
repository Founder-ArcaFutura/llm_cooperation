"""Restore ignored score JSONL from the frozen archive without overwriting a capture."""
import gzip
import hashlib
import json
from pathlib import Path
from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT


def restore(root=DEFAULT_REPORT):
    root=Path(root)
    manifest=json.loads((root/'artifact_manifest.json').read_text())
    expected=manifest['uncompressed_scores_sha256']
    target=root/'scores.jsonl'
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise ValueError('Existing score capture differs; preserve it and use a separate output directory')
        return
    packed=(root/'scores.jsonl.gz').read_bytes()
    if hashlib.sha256(packed).hexdigest()!=manifest['files']['scores.jsonl.gz']:
        raise ValueError('Compressed artifact hash mismatch')
    contents=gzip.decompress(packed)
    if hashlib.sha256(contents).hexdigest()!=expected:
        raise ValueError('Decompressed artifact hash mismatch')
    target.write_bytes(contents)


if __name__=='__main__':
    restore()
