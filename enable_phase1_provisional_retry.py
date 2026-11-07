#!/usr/bin/env python3
"""Enable explicitly labeled, hash-pinned provisional Phase 1 evaluation.

Apply at the root of the llm_cooperation repository. This does not alter the
Phase 1 scenario bank or its scientific freeze manifest. It adds a distinct,
opt-in provisional pathway to the existing Modal inference stack.

Produces *.pre_provisional_backup files once; idempotent after initial patch.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
# The script can be run from any location; prefer the caller's repository root.
if not (ROOT / "modal_app.py").exists():
    ROOT = Path.cwd()

RUNNER = ROOT / "llm_cooperation" / "harness" / "runner.py"
MODAL = ROOT / "modal_app.py"
BANK = ROOT / "data" / "scenarios_phase1_prospective.json"
EXPECTED_BANK_SHA256 = "5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f"

if not (RUNNER.is_file() and MODAL.is_file() and BANK.is_file()):
    sys.exit("Run this script from the llm_cooperation repository root; required files are missing.")

actual = hashlib.sha256(BANK.read_bytes()).hexdigest()
if actual != EXPECTED_BANK_SHA256:
    sys.exit(f"Bank SHA-256 unexpected: {actual}\nExpected original draft: {EXPECTED_BANK_SHA256}. NO FILES CHANGED.")

runner = RUNNER.read_text(encoding="utf-8")
modal = MODAL.read_text(encoding="utf-8")
if "PHASE1_PROVISIONAL_SHA256" in runner:
    print("Provisional mode already installed; nothing changed.")
    print("Bank hash:", actual)
    sys.exit(0)


def exactly(s: str, needle: str, replacement: str, label: str) -> str:
    count = s.count(needle)
    if count != 1:
        sys.exit(f"Expected exactly one {label} patch location; found {count}. NO FILES CHANGED.")
    return s.replace(needle, replacement)

runner = exactly(
    runner,
    'PHASE1_FREEZE_MANIFEST_PATH = "configs/phase1_freeze_manifest.json"',
    '''PHASE1_FREEZE_MANIFEST_PATH = "configs/phase1_freeze_manifest.json"

# The original (unadjudicated) draft corpus is pinned independently of the
# approved freeze manifest. This is an exploratory/provisional workflow only.
PHASE1_PROVISIONAL_SHA256 = "5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f"


def verify_provisional_phase1_bank(scenarios_path: str) -> str:
    """Authorize original draft *only* for an explicitly labeled provisional assay."""
    with open(scenarios_path, "r", encoding="utf-8") as fh:
        bank_dict = json.load(fh)
    if bank_dict.get("status") != "draft_pending_review":
        raise PermissionError("PROVISIONAL PHASE 1 requires the original draft bank, not a frozen or unknown status")
    actual = compute_file_hash(scenarios_path)
    if actual != PHASE1_PROVISIONAL_SHA256:
        raise ValueError(f"PROVISIONAL PHASE 1 BANK HASH MISMATCH: {actual}; expected {PHASE1_PROVISIONAL_SHA256}")
    return actual''',
    "runner manifest marker",
)
runner = exactly(
    runner,
    '    authorize_phase1_run: bool = False,\n    _freeze_manifest_override: Optional[str] = None,',
    '    authorize_phase1_run: bool = False,\n    provisional_phase1: bool = False,\n    _freeze_manifest_override: Optional[str] = None,',
    "runner signature",
)
runner = exactly(
    runner,
    '    if is_phase1:\n        # Require bank status to be exactly \'frozen\'',
    '''    if provisional_phase1 and not is_phase1:
        raise PermissionError("Provisional Phase 1 mode may only be used with the Phase 1 scenario bank")

    if is_phase1 and provisional_phase1:
        verify_provisional_phase1_bank(scenarios_path)
        print("[PHASE 1 PROVISIONAL] Exploratory evaluation of unadjudicated draft corpus; NOT a confirmatory replication")

    if is_phase1 and not provisional_phase1:
        # Require bank status to be exactly 'frozen' ''',
    "runner phase1 guard",
)
# Use the first metadata header written by run_experiment, not the other helpers.

def replace_first_checked(s: str, needle: str, replacement: str, label: str) -> str:
    # The same JSON header statement occurs again in run_calibration; modify only
    # the first occurrence, which belongs to run_experiment.
    count = s.count(needle)
    if count != 2:
        sys.exit(f"Expected two {label} statements, got {count}. NO FILES CHANGED.")
    return s.replace(needle, replacement, 1)

runner = replace_first_checked(
    runner,
    '        f.write(json.dumps(run_record.model_dump(exclude={"records"})) + "\\n")',
    '''        metadata = run_record.model_dump(exclude={"records"})
        if provisional_phase1:
            metadata["research_status"] = "phase1_provisional_exploratory_not_human_adjudicated"
            metadata["formal_confirmatory_freeze"] = False
            metadata["draft_bank_sha256"] = PHASE1_PROVISIONAL_SHA256
        f.write(json.dumps(metadata) + "\\n")''',
    "runner metadata header",
)
# Modal: add a real, deliberate flag to all six function signatures.
occ = modal.count('    authorize_phase1_run: bool = False,')
if occ != 6:
    sys.exit(f"Expected 6 Modal function signatures, got {occ}. NO FILES CHANGED.")
modal = modal.replace(
    '    authorize_phase1_run: bool = False,',
    '    authorize_phase1_run: bool = False,\n    provisional_phase1: bool = False,',
)
# Propagate flag through local -> remote -> runner for all paths.
call_pattern = re.compile(r'(?m)^([ \t]*)authorize_phase1_run=authorize_phase1_run,[ \t]*$')
call_count = len(call_pattern.findall(modal))
if call_count != 10:
    sys.exit(f"Expected 10 Modal authorization call sites, got {call_count}. NO FILES CHANGED.")
modal = call_pattern.sub(lambda m: f'{m.group(1)}authorize_phase1_run=authorize_phase1_run,\n{m.group(1)}provisional_phase1=provisional_phase1,',modal)
modal = exactly(
    modal,
    '    if is_phase1:\n        import json\n        from pathlib import Path',
    '''    if is_phase1:
        if provisional_phase1:
            from pathlib import Path
            from llm_cooperation.harness.runner import verify_provisional_phase1_bank
            local_p = Path("data/scenarios_phase1_prospective.json")
            target_check = local_p if local_p.exists() else Path(scenarios_path)
            verify_provisional_phase1_bank(str(target_check))
            return scenarios_path, split
        import json
        from pathlib import Path''',
    "Modal local and remote routing",
)
# Make sure no provisional switch can reach Phase0B or another bank.
modal = exactly(
    modal,
    '    is_phase1 = bank_clean == "phase1"',
    '''    is_phase1 = bank_clean == "phase1"
    if provisional_phase1 and not is_phase1:
        raise PermissionError("--provisional-phase1 may only be used with --bank phase1")''',
    "Modal bank selector",
)
# Confirm the patch generated valid source *before* writing.
ast.parse(runner, filename="runner.py")
ast.parse(modal, filename="modal_app.py")
for path, content in ((RUNNER, runner), (MODAL, modal)):
    backup = path.with_suffix(path.suffix + ".pre_provisional_backup")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text(content, encoding="utf-8")
print("INSTALLED: --provisional-phase1 (distinct from confirmatory freeze)")
print("PINNED DRAFT SHA-256:", actual)
print("Backups:", RUNNER.name + ".pre_provisional_backup,", MODAL.name + ".pre_provisional_backup")
print("Scenario bank and freeze manifest are UNCHANGED.")
print("NEXT: modal run modal_app.py --model Qwen/Qwen2.5-3B --bank phase1 --provisional-phase1 --no-mock --authorize-paid-run")
