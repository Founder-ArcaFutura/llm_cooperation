"""Repair OLMo-2 7B checkpoint 781B tokenizer resolution, without changing model weights.

Run from G:\\llm_cooperation (repository root):
    python .\\patch_olmo7b_781B_tokenizer.py

The patch is opt-in and only activates in the 7B behavior-only Modal worker for
checkpoint_order 1. The pinned model revision SHA is never changed. No jobs run.
"""
from pathlib import Path
import ast
import shutil
import sys

ROOT = Path.cwd()
HARNESS = ROOT / "llm_cooperation" / "harness" / "runner.py"
MODAL = ROOT / "modal_olmo7b_behavior_only.py"
TOKENIZER_SHA = "7ab0c1550af1be0a0ceca046aa453b9463fa7116"
ENV = "OLMO_7B_TOKENIZER_REVISION"

for p in (HARNESS, MODAL):
    if not p.is_file():
        sys.exit(f"ERROR: Missing {p}; run from G:\\llm_cooperation")

harness = HARNESS.read_text(encoding="utf-8")
modal = MODAL.read_text(encoding="utf-8")

old_harness = '''        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            revision=self.revision,
            trust_remote_code=True,
        )'''
new_harness = '''        # Opt-in tokenizer-only override for an older OLMo-2 checkpoint whose
        # revision lacks a usable fast-tokenizer artifact. Model weights remain
        # loaded from the original immutable self.revision below.
        tokenizer_revision = os.environ.get("OLMO_7B_TOKENIZER_REVISION") or self.revision
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            revision=tokenizer_revision,
            trust_remote_code=True,
        )'''

old_modal = '''    order = checkpoint["checkpoint_order"]'''
new_modal = '''    order = checkpoint["checkpoint_order"]
    # Only 781B needs a tokenizer artifact from a verified working OLMo 7B revision.
    # Do not modify the model's immutable checkpoint SHA.
    if order == 1:
        os.environ["OLMO_7B_TOKENIZER_REVISION"] = "7ab0c1550af1be0a0ceca046aa453b9463fa7116"
        print("OLMo 7B checkpoint 1: tokenizer artifact override=" + os.environ["OLMO_7B_TOKENIZER_REVISION"], flush=True)
    else:
        os.environ.pop("OLMO_7B_TOKENIZER_REVISION", None)'''

old_provenance = '''        "model_id": MODEL_ID,
        "checkpoint": checkpoint,'''
new_provenance = '''        "model_id": MODEL_ID,
        "checkpoint": checkpoint,
        "tokenizer_revision_actual": os.environ.get("OLMO_7B_TOKENIZER_REVISION") or revision,
        "tokenizer_override_reason": ("Missing/invalid tokenizer assets at 781B checkpoint; single-lineage 7B tokenizer fallback" if order == 1 else None),'''

if old_harness in harness:
    harness_new = harness.replace(old_harness, new_harness, 1)
elif new_harness in harness:
    harness_new = harness
else:
    sys.exit("ERROR: runner.py has unexpected content. Nothing changed.")

if old_modal in modal:
    modal_new = modal.replace(old_modal, new_modal, 1)
elif new_modal in modal:
    modal_new = modal
else:
    sys.exit("ERROR: Modal runner has unexpected checkpoint-order logic. Nothing changed.")

if old_provenance in modal_new:
    modal_new = modal_new.replace(old_provenance, new_provenance, 1)
elif new_provenance not in modal_new:
    sys.exit("ERROR: Modal runner has unexpected provenance structure. Nothing changed.")

# Check both final sources before any files are written.
ast.parse(harness_new, filename=str(HARNESS))
ast.parse(modal_new, filename=str(MODAL))
for target, previous, new_text in ((HARNESS,harness,harness_new),(MODAL,modal,modal_new)):
    if previous != new_text:
        backup = target.with_suffix(target.suffix + ".before-781b-tokenizer-fix.bak")
        if not backup.exists():
            shutil.copy2(target, backup)
            print("Backup:", backup)
        target.write_text(new_text, encoding="utf-8")
        print("Patched:", target)
    else:
        print("Already patched:", target)

print("Verified syntax. No model downloads or Modal jobs started.")
print("Model SHA (checkpoint 1) is unchanged: 840cb881c55ca19e859cf5857b29d921a58838a4")
print("Tokenizer SHA (checkpoint 1 only):", TOKENIZER_SHA)
print("Next: modal run --env main .\\modal_olmo7b_behavior_only.py --checkpoint-order 1 --split exploratory --authorize-paid-run")
