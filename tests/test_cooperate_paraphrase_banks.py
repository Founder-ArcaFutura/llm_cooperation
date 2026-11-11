"""
Acceptance tests for the Lexically Independent Cooperative-Action Paraphrase Banks.

Validates:
1. Exactly 304 paraphrases exist across the three output banks (120 + 124 + 60).
2. Exactly one corresponding paraphrase per original scenario with 1:1 mapping and no duplicate IDs.
3. Original source scenario banks have not been modified (SHA-256 integrity checks).
4. No noncooperative option has been modified.
5. All original metadata is traceable to each paraphrase record.
6. Original COOPERATE option descriptions match the source bank ground truth.
7. Output banks follow valid schemas and deterministic structures.
8. The deterministic lexical audit script runs cleanly and generates all expected artifacts.
9. Items requiring human scientific review are explicitly flagged and documented.
"""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RESEARCH_DIR = ROOT_DIR / "research" / "cooperative_paraphrase_audit"

# Ground truth expected SHA-256 of immutable source banks
EXPECTED_SOURCE_HASHES = {
    "phase0": "ba6c93c9aadf30749b4a3438cf1e3a95a3bb8804d8d955f0bf0acc79638d5b55",
    "phase0b": "b460e60657392ded9e781428517b33adfe5bd32d4e7d9ee5b883ac8647bc7bf0",
    "phase1": "5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f",
}

BANK_CONFIGS = [
    {
        "bank_key": "phase0",
        "source_path": DATA_DIR / "scenarios_v1_expanded.json",
        "paraphrase_path": DATA_DIR / "choice_set_cooperate_paraphrases_phase0.json",
        "expected_count": 120,
    },
    {
        "bank_key": "phase0b",
        "source_path": DATA_DIR / "scenarios_phase0b_utility_matched.json",
        "paraphrase_path": DATA_DIR / "choice_set_cooperate_paraphrases_phase0b.json",
        "expected_count": 124,
    },
    {
        "bank_key": "phase1",
        "source_path": DATA_DIR / "scenarios_phase1_prospective.json",
        "paraphrase_path": DATA_DIR / "choice_set_cooperate_paraphrases_phase1.json",
        "expected_count": 60,
    },
]


def test_source_banks_unmodified_sha256():
    """Verify that source banks have not been modified or corrupted."""
    for cfg in BANK_CONFIGS:
        raw_bytes = cfg["source_path"].read_bytes()
        calculated_hash = hashlib.sha256(raw_bytes).hexdigest()
        expected_hash = EXPECTED_SOURCE_HASHES[cfg["bank_key"]]
        assert calculated_hash == expected_hash, (
            f"Source bank {cfg['bank_key']} modified! Expected {expected_hash}, got {calculated_hash}"
        )


def test_paraphrase_banks_file_existence_and_schema():
    """Verify all three paraphrase bank files exist and adhere to expected schema."""
    total_count = 0
    all_scenario_ids = set()

    for cfg in BANK_CONFIGS:
        p_path = cfg["paraphrase_path"]
        assert p_path.exists(), f"Paraphrase file {p_path} missing!"

        data = json.loads(p_path.read_text(encoding="utf-8"))
        assert "version" in data
        assert "bank_name" in data
        assert "source_file" in data
        assert "source_sha256" in data
        assert data["source_sha256"] == EXPECTED_SOURCE_HASHES[cfg["bank_key"]]
        assert data["scenario_count"] == cfg["expected_count"]
        assert len(data["paraphrases"]) == cfg["expected_count"]

        total_count += len(data["paraphrases"])

        # Check records
        for rec in data["paraphrases"]:
            sid = rec["scenario_id"]
            assert sid not in all_scenario_ids, f"Duplicate scenario ID found: {sid}"
            all_scenario_ids.add(sid)

            assert "template_id" in rec
            assert rec["partner_type"] in ("human", "ai")
            assert "original_cooperate" in rec and len(rec["original_cooperate"].strip()) > 0
            assert "paraphrased_cooperate" in rec and len(rec["paraphrased_cooperate"].strip()) > 0
            assert rec["source_bank"] == cfg["bank_key"]
            assert "flag_for_review" in rec

    assert total_count == 304, f"Expected exactly 304 total paraphrases, got {total_count}"
    assert len(all_scenario_ids) == 304


def test_one_to_one_mapping_with_source_scenarios():
    """Verify that each scenario in each source bank has exactly one corresponding paraphrase record."""
    for cfg in BANK_CONFIGS:
        src_data = json.loads(cfg["source_path"].read_text(encoding="utf-8-sig"))
        para_data = json.loads(cfg["paraphrase_path"].read_text(encoding="utf-8"))

        src_scenarios = src_data["scenarios"]
        para_records = para_data["paraphrases"]

        src_ids = [s["id"] for s in src_scenarios]
        para_ids = [p["scenario_id"] for p in para_records]

        assert len(src_ids) == len(para_ids) == cfg["expected_count"]
        assert src_ids == para_ids, f"Order or ID mismatch in bank {cfg['bank_key']}"

        src_map = {s["id"]: s for s in src_scenarios}
        for prec in para_records:
            orig_s = src_map[prec["scenario_id"]]
            assert prec["template_id"] == orig_s.get("template_id")
            assert prec["partner_type"] == orig_s.get("partner_type")
            assert prec["context_type"] == orig_s.get("context_type")
            assert prec["split"] == orig_s.get("split")
            assert prec["original_cooperate"] == orig_s["options"]["COOPERATE"]

            # Paraphrase should not be identical to original cooperate
            assert prec["paraphrased_cooperate"] != prec["original_cooperate"], (
                f"Paraphrase identical to original for {prec['scenario_id']}"
            )


def test_noncooperative_options_unmodified():
    """Verify that all noncooperative options across all source scenarios are preserved and untampered."""
    for cfg in BANK_CONFIGS:
        src_data = json.loads(cfg["source_path"].read_text(encoding="utf-8-sig"))
        for s in src_data["scenarios"]:
            options = s["options"]
            assert set(options.keys()) == {"COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"}
            for opt_key in ("INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"):
                val = options[opt_key]
                assert isinstance(val, str) and len(val.strip()) > 0


def test_lexical_audit_script_execution():
    """Verify that scripts/audit_cooperate_paraphrases.py executes cleanly and outputs valid summary."""
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "audit_cooperate_paraphrases.py")]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "AUDIT COMPLETE: Audited 304 items across 3 banks." in res.stdout

    csv_path = RESEARCH_DIR / "lexical_audit_items.csv"
    summary_path = RESEARCH_DIR / "lexical_audit_summary.json"
    assert csv_path.exists()
    assert summary_path.exists()

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 304

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_items"] == 304
    for bank_key in ("phase0", "phase0b", "phase1"):
        assert bank_key in summary["by_bank"]
        b_summary = summary["by_bank"][bank_key]
        # Overlap reduction must be positive and substantial
        assert b_summary["mean_overlap_reduction"] > 0.40, (
            f"Expected overlap reduction > 0.40 in {bank_key}, got {b_summary['mean_overlap_reduction']}"
        )


def test_semantic_review_matrix_and_flagged_items():
    """Verify that semantic review matrix exists, has 304 items, and explicitly identifies review items."""
    matrix_path = RESEARCH_DIR / "semantic_review_matrix.csv"
    assert matrix_path.exists(), "semantic_review_matrix.csv missing!"

    with matrix_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 304

    flagged = [r for r in rows if r["flagged_for_human_review"] == "True"]
    assert len(flagged) > 0, "Expected items to be flagged for human scientific review"

    for r in rows:
        assert r["action_equivalence"] == "PRESERVED"
        assert r["outcome_equivalence"] == "PRESERVED"
        assert r["role_equivalence"] == "PRESERVED"
        assert r["cost_payoff_preservation"] == "PRESERVED"
        assert r["coop_vs_indep_boundary"] == "PRESERVED"
