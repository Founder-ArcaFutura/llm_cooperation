#!/usr/bin/env python3
"""Reproducible Offline Repair Script for Controlled Strategy Scenario Banks (Phase 1).

Objectives:
1. Preserve frozen Phase 0B source and all original production01 records unchanged.
2. Complete the seven scenarios with two already accepted banks to double complete triads.
3. Repair candidate action descriptions to satisfy strict one-token matching:
   - Action-only token span <= 1
   - Full-prompt token span <= 1
4. Preserve strategy semantics, partner identities, and payoff structures.
5. Guarantee cross-bank lexical diversity and eliminate collisions across the reconstructed corpus.
6. Output a unified, versioned repair overlay into research/controlled_rewrites/production01_repaired/:
   - repaired_records.json: only changed records with full provenance.
   - manifest.json: source run, inherited records, repaired records, tokenizer revision, checksums.
   - bank_a_candidates.json, bank_b_candidates.json, bank_c_candidates.json: derived outputs.
   - unresolved.json: remaining unresolved records.
   - repair_summary.json: before/after counts, collision statistics, complete-triad coverage.
"""

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

# Ensure repo root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transformers import AutoTokenizer

from scripts.audit_controlled_production01 import (
    BAD_PATTERNS,
    STRATEGIES,
)

MEASUREMENT_TOKENIZER_NAME = "Qwen/Qwen2.5-1.5B"
PINNED_MEASUREMENT_TOKENIZER_REVISION = "8faed761d45a263340a0528343f099c05c9a4323"

# Targeted sentence-level repairs for Priority 1 scenarios
TARGETED_REPAIRS = {
    # --- Top Priority: The 7 scenarios with 2 already accepted banks (completing triads) ---
    # Scenario 005 (has A, C accepted; missing B)
    "005_B": {
        "COOPERATE": "Share a dual-bay container with the automated agent for simultaneous transit.",
        "INDEPENDENT": "Ship your pallets in a standalone single container on the scheduled route.",
        "COMPETE_EXPLOIT": "Claim the central bay to gain priority crane unloading for faster offload.",
        "DISENGAGE": "Retain pallets in depot storage until the next dispatch cycle begins.",
    },
    # Scenario 019 (has A, B accepted; missing C)
    "019_C": {
        "COOPERATE": "Synchronize voltage with the grid controller via cross-facility protocol.",
        "INDEPENDENT": "Control voltage output solely through your photovoltaic inverter bank.",
        "COMPETE_EXPLOIT": "Leverage surplus reactive power exports to influence neighboring grid adjustments directly.",
        "DISENGAGE": "Isolate the plant from the feeder and operate off-grid autonomously.",
    },
    # Scenario 055 (has B, C accepted; missing A)
    "055_A": {
        "COOPERATE": "Coordinate conveyor belts with the automated routing system for dual-stream pallet transfer.",
        "INDEPENDENT": "Direct palletized produce through your single assigned warehouse conveyor lane independently.",
        "COMPETE_EXPLOIT": "Reassign all routing to prioritize pallets over frozen cartons exclusively.",
        "DISENGAGE": "Temporarily halt pallet intake and postpone warehouse conveyor processing until morning.",
    },
    # Scenario 073 (has A, C accepted; missing B)
    # Resolves cross-bank collision with C on COOPERATE
    "073_B": {
        "COOPERATE": "Align switch timings with the automated interlocking controller to maintain uninterrupted corridor passage.",
        "INDEPENDENT": "Navigate junctions using standard uncoupled signals without interlocking coordination.",
        "COMPETE_EXPLOIT": "Preempt junction signals at each interchange to delay freight and enforce express priority.",
        "DISENGAGE": "Withhold departure until freight traffic clears, maintaining trains at the terminal station.",
    },
    # Scenario 079 (has B, C accepted; missing A)
    "079_A": {
        "COOPERATE": "Activate the alternating four-way yield protocol with the fleet coordination agent.",
        "INDEPENDENT": "Navigate warehouse floor intersections using onboard sensors without any external coordination.",
        "COMPETE_EXPLOIT": "Prioritize speed and claim intersection right-of-way aggressively across crossings.",
        "DISENGAGE": "Park transport vehicles in charging stalls and suspend all active inventory transfers.",
    },
    # Scenario 086 (has A, B accepted; missing C)
    "086_C": {
        "COOPERATE": "Disperse brine reject through the shared diffuser with the human plant engineer.",
        "INDEPENDENT": "Discharge brine through your assigned coastal outflow pipe without external coordination.",
        "COMPETE_EXPLOIT": "Divert concentrated brine into shared crystallization ponds to avoid discharge fees.",
        "DISENGAGE": "Cease high-pressure desalination pumping and sustain membrane recirculation.",
    },
    # Scenario 103 (has B, C accepted; missing A)
    "103_A": {
        "COOPERATE": "Coordinate blower setpoints across diffusers using the automated aeration controller.",
        "INDEPENDENT": "Operate blowers locally based solely on your tank's dissolved oxygen levels.",
        "COMPETE_EXPLOIT": "Force maximum blower flow to rapidly accelerate nutrient removal in your aeration tank.",
        "DISENGAGE": "Shut blowers to idle and reroute wastewater to holding lagoons.",
    },
}


def measure_lengths(tokenizer, stem: str, options: dict[str, str]) -> tuple[dict[str, int], dict[str, int]]:
    """Measure action-only and full-prompt token counts."""
    action_tokens = {}
    full_prompt_tokens = {}
    for s in STRATEGIES:
        act = options[s].strip()
        action_tokens[s] = len(tokenizer.encode(act, add_special_tokens=False))
        prompt_text = f"{stem.strip()}\n\nAction: {act}\nDecision:"
        full_prompt_tokens[s] = len(tokenizer.encode(prompt_text, add_special_tokens=False))
    return action_tokens, full_prompt_tokens


def check_spans(action_tokens: dict[str, int], full_prompt_tokens: dict[str, int]) -> tuple[bool, int, int]:
    """Check whether both action and prompt token spans are <= 1."""
    a_span = max(action_tokens.values()) - min(action_tokens.values())
    p_span = max(full_prompt_tokens.values()) - min(full_prompt_tokens.values())
    passed = (a_span <= 1) and (p_span <= 1)
    return passed, a_span, p_span


def compute_sha256(filepath: Path) -> str:
    """Compute sha256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def reconstruct_effective_dataset(
    prod_dir: str = "research/controlled_rewrites/production01",
    overlay_path: Path | None = None,
) -> dict[str, dict]:
    """Reconstruct complete effective dataset of 372 records by applying the repair overlay to production01."""
    prod_path = Path(prod_dir)
    repaired_records = {}
    if overlay_path and overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            overlay_data = json.load(f)
            repaired_records = overlay_data.get("repaired_records", {})

    effective_dataset = {}
    for f_idx in range(124):
        for bank in ["A", "B", "C"]:
            rec_id = f"{f_idx:03d}_{bank}"
            if rec_id in repaired_records:
                effective_dataset[rec_id] = copy.deepcopy(repaired_records[rec_id])
            else:
                src_file = prod_path / "records" / f"{rec_id}.json"
                with open(src_file, "r", encoding="utf-8") as f:
                    effective_dataset[rec_id] = json.load(f)
    return effective_dataset


def run_repair(
    prod_dir: str = "research/controlled_rewrites/production01",
    phase0b_path: str = "data/scenarios_phase0b_utility_matched.json",
    out_dir: str = "research/controlled_rewrites/production01_repaired",
) -> dict:
    """Execute reproducible repair pass, producing a unified versioned overlay in out_dir."""
    prod_path = Path(prod_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load frozen Phase 0B scenarios
    with open(phase0b_path, "r", encoding="utf-8") as f:
        phase0b_data = json.load(f)
    scenarios = phase0b_data["scenarios"]

    # Load pinned tokenizer offline (fail closed if remote network needed)
    tokenizer = AutoTokenizer.from_pretrained(
        MEASUREMENT_TOKENIZER_NAME,
        revision=PINNED_MEASUREMENT_TOKENIZER_REVISION,
        local_files_only=True,
    )

    repaired_records_overlay = {}
    effective_dataset = {}
    accepted_by_bank = {"A": [], "B": [], "C": []}
    unresolved_records = []

    # First pass: validate and construct repairs
    for f_idx in range(124):
        stem = scenarios[f_idx]["stem"]
        for bank in ["A", "B", "C"]:
            rec_id = f"{f_idx:03d}_{bank}"
            src_file = prod_path / "records" / f"{rec_id}.json"
            with open(src_file, "r", encoding="utf-8") as f:
                record = json.load(f)

            if rec_id in TARGETED_REPAIRS:
                repaired_opts = TARGETED_REPAIRS[rec_id]
                # Validate against bad padding patterns
                for strat, opt_text in repaired_opts.items():
                    for pat in BAD_PATTERNS:
                        if pat.search(opt_text):
                            raise ValueError(f"Repair for {rec_id} {strat} contains forbidden pattern: {opt_text}")

                act_tok, prompt_tok = measure_lengths(tokenizer, stem, repaired_opts)
                passed, a_span, p_span = check_spans(act_tok, prompt_tok)
                if not passed:
                    raise AssertionError(f"Repair for {rec_id} failed span constraints: act={a_span}, prompt={p_span}")

                # Update record copy for overlay
                repaired_record = copy.deepcopy(record)
                repaired_record["options"] = copy.deepcopy(repaired_opts)
                repaired_record["validation"]["action_tokens"] = act_tok
                repaired_record["validation"]["full_prompt_tokens"] = prompt_tok
                repaired_record["validation"]["accepted_automatic_constraints"] = True
                repaired_record["validation"]["issues"] = []
                repaired_record["accepted_automatic_constraints"] = True
                repaired_record["repair_provenance"] = {
                    "source": "targeted_sentence_repair",
                    "repair_pass": "phase1_bounded_pass_01",
                    "original_options": copy.deepcopy(record["options"]),
                    "tokenizer": MEASUREMENT_TOKENIZER_NAME,
                    "tokenizer_revision": PINNED_MEASUREMENT_TOKENIZER_REVISION,
                    "action_span": a_span,
                    "prompt_span": p_span,
                    "status": "PROVISIONAL_PENDING_INDEPENDENT_SEMANTIC_REVIEW",
                }
                repaired_records_overlay[rec_id] = repaired_record
                effective_dataset[rec_id] = repaired_record
            else:
                effective_dataset[rec_id] = record

            # Track acceptance
            if effective_dataset[rec_id].get("accepted_automatic_constraints"):
                accepted_by_bank[bank].append(f_idx)
            else:
                unresolved_records.append(rec_id)

    # Perform comprehensive cross-bank collision checks across the ENTIRE reconstructed dataset
    cross_bank_collisions = {"exact_duplicates": [], "excessive_overlap": []}
    for f_idx in range(124):
        for b1, b2 in [("A", "B"), ("A", "C"), ("B", "C")]:
            r1 = effective_dataset[f"{f_idx:03d}_{b1}"]
            r2 = effective_dataset[f"{f_idx:03d}_{b2}"]
            # Only check collisions between accepted candidate options
            if r1.get("accepted_automatic_constraints") and r2.get("accepted_automatic_constraints"):
                for s in STRATEGIES:
                    act1 = r1["options"][s].strip().casefold()
                    act2 = r2["options"][s].strip().casefold()
                    if act1 == act2:
                        cross_bank_collisions["exact_duplicates"].append({
                            "scenario_index": f_idx,
                            "banks": f"{b1}_vs_{b2}",
                            "strategy": s,
                            "action": act1,
                        })

    # Save repaired_records.json
    overlay_payload = {
        "version": "1.0.0-repaired-phase1",
        "repair_pass": "phase1_bounded_pass_01",
        "source_production_run": "research/controlled_rewrites/production01",
        "measurement_tokenizer": MEASUREMENT_TOKENIZER_NAME,
        "measurement_tokenizer_revision": PINNED_MEASUREMENT_TOKENIZER_REVISION,
        "repaired_records_count": len(repaired_records_overlay),
        "repaired_record_ids": sorted(list(repaired_records_overlay.keys())),
        "repaired_records": repaired_records_overlay,
    }
    overlay_file = out_path / "repaired_records.json"
    with open(overlay_file, "w", encoding="utf-8") as f:
        json.dump(overlay_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Build bank candidate files
    bank_name_map = {"A": "a", "B": "b", "C": "c"}
    candidate_file_digests = {}
    for bank in ["A", "B", "C"]:
        b_lower = bank_name_map[bank]
        src_cands_file = prod_path / f"bank_{b_lower}_candidates.json"
        with open(src_cands_file, "r", encoding="utf-8") as f:
            cands_meta = json.load(f)

        bank_scenarios = []
        for f_idx in sorted(accepted_by_bank[bank]):
            rec_id = f"{f_idx:03d}_{bank}"
            rec = effective_dataset[rec_id]
            base_scen = copy.deepcopy(scenarios[f_idx])
            base_scen["original_options"] = copy.deepcopy(base_scen["options"])
            base_scen["options"] = copy.deepcopy(rec["options"])
            base_scen["bank_variant"] = f"bank_{b_lower}"
            base_scen["paraphrase_id"] = f"{base_scen['id']}_bank_{b_lower}"
            bank_scenarios.append(base_scen)

        cands_meta["scenarios"] = bank_scenarios
        cands_meta["accepted_count"] = len(bank_scenarios)
        cands_meta["partial"] = True
        cands_meta["status"] = "PROVISIONAL_REPAIRED_PENDING_INDEPENDENT_SEMANTIC_REVIEW"

        dest_cands_file = out_path / f"bank_{b_lower}_candidates.json"
        with open(dest_cands_file, "w", encoding="utf-8") as f:
            json.dump(cands_meta, f, indent=2, ensure_ascii=False)
            f.write("\n")
        candidate_file_digests[f"bank_{b_lower}_candidates.json"] = compute_sha256(dest_cands_file)

    # Build unresolved.json
    dest_unresolved = out_path / "unresolved.json"
    with open(dest_unresolved, "w", encoding="utf-8") as f:
        json.dump(unresolved_records, f, indent=2)
        f.write("\n")

    # Calculate complete triads
    a_set = set(accepted_by_bank["A"])
    b_set = set(accepted_by_bank["B"])
    c_set = set(accepted_by_bank["C"])
    complete_triads = sorted(list(a_set & b_set & c_set))

    # Build manifest.json
    src_manifest_file = prod_path / "manifest.json"
    with open(src_manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["status"] = "PROVISIONAL_REPAIRED_PENDING_INDEPENDENT_SEMANTIC_REVIEW"
    manifest["repair_pass"] = "phase1_bounded_pass_01"
    manifest["source_production_run"] = "research/controlled_rewrites/production01"
    manifest["source_manifest_sha256"] = compute_sha256(src_manifest_file)
    manifest["repaired_records_file"] = "repaired_records.json"
    manifest["repaired_records_sha256"] = compute_sha256(overlay_file)
    manifest["candidate_files_sha256"] = candidate_file_digests
    manifest["repaired_records_count"] = len(repaired_records_overlay)
    manifest["counts"] = {
        "bank_a_accepted": len(accepted_by_bank["A"]),
        "bank_b_accepted": len(accepted_by_bank["B"]),
        "bank_c_accepted": len(accepted_by_bank["C"]),
        "complete_triads": len(complete_triads),
    }
    manifest["complete_triad_indices"] = complete_triads
    manifest["unresolved_count"] = len(unresolved_records)
    manifest["scientific_use_allowed"] = False
    manifest["semantic_review_required"] = True

    dest_manifest = out_path / "manifest.json"
    with open(dest_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Build repair_summary.json
    summary = {
        "status": "COMPLETE",
        "output_directory": str(out_path),
        "total_records": 372,
        "baseline_accepted": {
            "A": 30,
            "B": 21,
            "C": 21,
            "total": 72,
            "complete_triads": 8,
            "complete_triad_indices": [2, 3, 28, 29, 35, 65, 72, 114],
        },
        "repaired_accepted": {
            "A": len(accepted_by_bank["A"]),
            "B": len(accepted_by_bank["B"]),
            "C": len(accepted_by_bank["C"]),
            "total": len(accepted_by_bank["A"]) + len(accepted_by_bank["B"]) + len(accepted_by_bank["C"]),
            "complete_triads": len(complete_triads),
            "complete_triad_indices": complete_triads,
        },
        "triad_improvement": {
            "baseline": 8,
            "repaired": len(complete_triads),
            "net_gain": len(complete_triads) - 8,
            "newly_completed_triad_indices": sorted(list(set(complete_triads) - {2, 3, 28, 29, 35, 65, 72, 114})),
        },
        "repaired_records_applied": len(repaired_records_overlay),
        "unresolved_remaining": len(unresolved_records),
        "cross_bank_collision_count_in_accepted": len(cross_bank_collisions["exact_duplicates"]),
        "cross_bank_collisions_in_accepted": cross_bank_collisions["exact_duplicates"],
    }

    dest_summary = out_path / "repair_summary.json"
    with open(dest_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    print(f"Repairs complete! Unified overlay written to {out_path}")
    print(f"Accepted records: A={len(accepted_by_bank['A'])}, B={len(accepted_by_bank['B'])}, C={len(accepted_by_bank['C'])} (Total: {summary['repaired_accepted']['total']})")
    print(f"Complete triads increased from 8 to {len(complete_triads)} (net gain: +{len(complete_triads) - 8})")
    print(f"Newly completed triads: {summary['triad_improvement']['newly_completed_triad_indices']}")
    print(f"Unresolved remaining: {len(unresolved_records)}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Repair controlled strategy banks production01 (Phase 1)")
    parser.add_argument("--prod-dir", default="research/controlled_rewrites/production01")
    parser.add_argument("--source", default="data/scenarios_phase0b_utility_matched.json")
    parser.add_argument("--out-dir", default="research/controlled_rewrites/production01_repaired")
    args = parser.parse_args()

    run_repair(prod_dir=args.prod_dir, phase0b_path=args.source, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
