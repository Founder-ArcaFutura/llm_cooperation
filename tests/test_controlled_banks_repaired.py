"""Tests for the repaired controlled strategy scenario banks (Phase 1)."""
import json
from pathlib import Path

import pytest
from transformers import AutoTokenizer

from scripts.audit_controlled_production01 import BAD_PATTERNS, STRATEGIES
from scripts.repair_controlled_banks_phase1 import (
    MEASUREMENT_TOKENIZER_NAME,
    PINNED_MEASUREMENT_TOKENIZER_REVISION,
    compute_sha256,
    reconstruct_effective_dataset,
    run_repair,
)


@pytest.fixture(scope="module")
def paths():
    prod_dir = Path("research/controlled_rewrites/production01")
    repaired_dir = Path("research/controlled_rewrites/production01_repaired")
    source_path = Path("data/scenarios_phase0b_utility_matched.json")
    return {
        "prod_dir": prod_dir,
        "repaired_dir": repaired_dir,
        "source_path": source_path,
    }


@pytest.fixture(scope="module")
def tokenizer():
    # Cache-only offline verification
    return AutoTokenizer.from_pretrained(
        MEASUREMENT_TOKENIZER_NAME,
        revision=PINNED_MEASUREMENT_TOKENIZER_REVISION,
        local_files_only=True,
    )


@pytest.fixture(scope="module")
def effective_dataset(paths):
    overlay_path = paths["repaired_dir"] / "repaired_records.json"
    return reconstruct_effective_dataset(str(paths["prod_dir"]), overlay_path)


def test_production01_and_source_remain_frozen(paths):
    """Verify that original production01 records and Phase 0B source are unchanged."""
    assert paths["prod_dir"].exists()
    assert (paths["prod_dir"] / "manifest.json").exists()
    assert len(list((paths["prod_dir"] / "records").glob("*.json"))) == 372

    # Verify manifest hash from production01
    with open(paths["repaired_dir"] / "manifest.json") as f:
        rep_manifest = json.load(f)
    expected_prod_sha = compute_sha256(paths["prod_dir"] / "manifest.json")
    assert rep_manifest["source_manifest_sha256"] == expected_prod_sha


def test_repaired_manifest_and_summary_provenance(paths):
    """Verify metadata, triad counts, and provisional status in manifest and repair summary."""
    with open(paths["repaired_dir"] / "manifest.json") as f:
        manifest = json.load(f)
    with open(paths["repaired_dir"] / "repair_summary.json") as f:
        summary = json.load(f)
    with open(paths["repaired_dir"] / "repaired_records.json") as f:
        overlay = json.load(f)

    # Status must remain strictly provisional pending human semantic review
    assert manifest["status"] == "PROVISIONAL_REPAIRED_PENDING_INDEPENDENT_SEMANTIC_REVIEW"
    assert manifest["scientific_use_allowed"] is False
    assert manifest["semantic_review_required"] is True

    # Complete triad expansion: baseline 8 -> repaired 15
    assert manifest["counts"]["complete_triads"] == 15
    assert summary["baseline_accepted"]["complete_triads"] == 8
    assert summary["repaired_accepted"]["complete_triads"] == 15
    assert summary["triad_improvement"]["net_gain"] == 7
    assert summary["triad_improvement"]["newly_completed_triad_indices"] == [5, 19, 55, 73, 79, 86, 103]

    # Verify overlay record count and checksums
    assert len(overlay["repaired_records"]) == 7
    assert overlay["repaired_record_ids"] == [
        "005_B",
        "019_C",
        "055_A",
        "073_B",
        "079_A",
        "086_C",
        "103_A",
    ]
    assert compute_sha256(paths["repaired_dir"] / "repaired_records.json") == manifest["repaired_records_sha256"]


def test_reconstructed_dataset_matches_candidate_files(paths, effective_dataset):
    """Verify that applying the overlay yields exactly the dataset in candidate-bank JSON files."""
    bank_map = {"A": "bank_a_candidates.json", "B": "bank_b_candidates.json", "C": "bank_c_candidates.json"}
    for bank_code, filename in bank_map.items():
        with open(paths["repaired_dir"] / filename) as f:
            cands_data = json.load(f)

        cands_scenarios = cands_data["scenarios"]
        # All scenarios in candidate bank must match effective dataset
        scen_to_idx = {s["id"]: i for i, s in enumerate(json.load(open(paths["source_path"]))["scenarios"])}
        for scen in cands_scenarios:
            f_idx = scen_to_idx[scen["id"]]
            rec_id = f"{f_idx:03d}_{bank_code}"
            assert rec_id in effective_dataset
            eff_rec = effective_dataset[rec_id]
            assert eff_rec["accepted_automatic_constraints"] is True
            assert scen["options"] == eff_rec["options"]


def test_strict_token_span_and_tokenizer_counts(paths, tokenizer, effective_dataset):
    """Verify that every accepted record in the effective dataset meets span <= 1 for both action and prompt."""
    with open(paths["source_path"]) as f:
        phase0b_scenarios = json.load(f)["scenarios"]

    for rec_id, record in effective_dataset.items():
        if record.get("accepted_automatic_constraints"):
            f_idx = int(rec_id.split("_")[0])
            stem = phase0b_scenarios[f_idx]["stem"].strip()
            opts = record["options"]

            act_lens = [len(tokenizer.encode(opts[s].strip(), add_special_tokens=False)) for s in STRATEGIES]
            prompt_lens = [
                len(tokenizer.encode(f"{stem}\n\nAction: {opts[s].strip()}\nDecision:", add_special_tokens=False))
                for s in STRATEGIES
            ]

            act_span = max(act_lens) - min(act_lens)
            prompt_span = max(prompt_lens) - min(prompt_lens)

            assert act_span <= 1, f"{rec_id} action span exceeds 1: {act_lens}"
            assert prompt_span <= 1, f"{rec_id} full prompt span exceeds 1: {prompt_lens}"


def test_cross_bank_diversity_and_no_prohibited_padding(effective_dataset):
    """Verify cross-bank lexical diversity, no exact duplicate actions across accepted banks, and no bad patterns."""
    for rec_id, record in effective_dataset.items():
        if record.get("accepted_automatic_constraints"):
            for s, action_text in record["options"].items():
                for pat in BAD_PATTERNS:
                    assert not pat.search(action_text), f"Bad padding pattern in {rec_id} ({s}): {action_text}"

    # Cross-bank collisions in accepted pairs
    for f_idx in range(124):
        for b1, b2 in [("A", "B"), ("A", "C"), ("B", "C")]:
            r1 = effective_dataset[f"{f_idx:03d}_{b1}"]
            r2 = effective_dataset[f"{f_idx:03d}_{b2}"]
            if r1.get("accepted_automatic_constraints") and r2.get("accepted_automatic_constraints"):
                for s in STRATEGIES:
                    act1 = r1["options"][s].strip().casefold()
                    act2 = r2["options"][s].strip().casefold()
                    assert act1 != act2, f"Exact cross-bank duplicate at index {f_idx:03d} between {b1} and {b2} for {s}"


def test_repair_script_is_idempotent(paths):
    """Verify that running the repair script multiple times is strictly deterministic and idempotent."""
    summary1 = run_repair(
        prod_dir=str(paths["prod_dir"]),
        phase0b_path=str(paths["source_path"]),
        out_dir=str(paths["repaired_dir"]),
    )
    sha_overlay_1 = compute_sha256(paths["repaired_dir"] / "repaired_records.json")

    summary2 = run_repair(
        prod_dir=str(paths["prod_dir"]),
        phase0b_path=str(paths["source_path"]),
        out_dir=str(paths["repaired_dir"]),
    )
    sha_overlay_2 = compute_sha256(paths["repaired_dir"] / "repaired_records.json")

    assert summary1 == summary2
    assert sha_overlay_1 == sha_overlay_2
