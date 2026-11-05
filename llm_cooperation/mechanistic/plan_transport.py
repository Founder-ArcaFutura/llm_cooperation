"""Byte-preserving transport for hash-bound delayed-mapping plans."""
from pathlib import Path

from .delayed_mapping import read_plan

PLAN_FILES = ('manifest.json', 'bank.json', 'presentations.jsonl')


def pack_plan(directory):
    """Validate locally and retain exact bytes, including CRLF line endings."""
    read_plan(directory)
    return {name: (Path(directory) / name).read_bytes() for name in PLAN_FILES}


def unpack_plan(directory, files):
    """Restore exact bytes. Reject legacy text payloads and unexpected paths."""
    if set(files) != set(PLAN_FILES) or any(not isinstance(v, bytes) for v in files.values()):
        raise ValueError('Expected exactly three binary plan files')
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    for name in PLAN_FILES:
        (target / name).write_bytes(files[name])
    read_plan(target)
    return target
