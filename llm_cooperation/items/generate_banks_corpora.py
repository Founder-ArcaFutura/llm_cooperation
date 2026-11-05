"""Generate Bank A, Bank B, and Bank C for all 124 scenarios.

Bank A: Length-matched variant (tight length matching targeting <= 1 token diff within scenario).
Bank B: Lexically diversified variant (varying syntax, verbs, vocabulary, and sentence structures).
Bank C: Independent paraphrase replication (independently phrased for cross-bank evaluation).
"""
import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from transformers import AutoTokenizer

from llm_cooperation.items.controlled_banks import (
    DEFAULT_TOKENIZER_ID,
    STRATEGIES,
    TRAILING_MARKER,
    get_tokenizer,
)
from llm_cooperation.items.semantic_validator import validate_scenario_actions

tok = get_tokenizer()

def L(text: str) -> int:
    return len(tok.encode(text.strip()))

def pad_or_trim(text: str, target: int, strat: str) -> str:
    """Tweak words without altering strategic meaning to hit target token count."""
    text = text.strip()
    cur = L(text)
    if cur == target:
        return text

    # Try insertions if too short
    if cur < target:
        insertions = [
            ("your ", "your own "),
            ("the ", "the assigned "),
            ("the ", "the specified "),
            ("to ", "in order to "),
            ("for ", "specifically for "),
            ("with ", "jointly with "),
            ("into ", "directly into "),
            ("from ", "directly from "),
            ("on ", "directly on "),
            ("through ", "directly through "),
            ("using ", "actively using "),
            ("across ", "straight across "),
            ("until ", "safely until "),
            ("without ", "strictly without "),
        ]
        for src, repl in insertions:
            if src in text:
                cand = text.replace(src, repl, 1)
                if L(cand) == target:
                    return cand
        qualifiers = {
            "COOPERATE": [" as scheduled.", " for the run.", " on schedule.", " during the shift."],
            "INDEPENDENT": [" as planned.", " on schedule.", " for your lot.", " during the shift."],
            "COMPETE_EXPLOIT": [" ahead of others.", " before other teams.", " for your own batch.", " first."],
            "DISENGAGE": [" until next shift.", " for the day.", " until later.", " until morning."],
        }
        for q in qualifiers.get(strat, [" as scheduled."]):
            base = text.rstrip(".")
            cand = f"{base}{q}"
            if L(cand) == target:
                return cand
            if L(cand) < target and (target - L(cand) == 1):
                cand2 = f"{base} exactly{q}"
                if L(cand2) == target:
                    return cand2

    # Try deletions if too long
    if cur > target:
        deletions = [
            ("automated synchronization pipeline", "pipeline"),
            ("automated synchronization", "pipeline"),
            ("automated ", ""),
            ("synchronization ", ""),
            ("prescribed ", ""),
            ("industrial ", ""),
            ("pharmaceutical ", ""),
            ("agricultural ", ""),
            ("surveillance ", ""),
            ("geological ", ""),
            ("observation ", ""),
            ("your own ", "your "),
            ("directly ", ""),
            ("strictly ", ""),
            ("completely ", ""),
            ("scheduled ", ""),
            ("standard ", ""),
            ("assigned ", ""),
            ("dedicated ", ""),
            ("current ", ""),
            ("forthcoming ", ""),
            ("regular ", ""),
        ]
        for src, repl in deletions:
            if src in text:
                cand = text.replace(src, repl, 1)
                cand = " ".join(cand.split())
                if L(cand) == target:
                    return cand
                if L(cand) < cur:
                    res = pad_or_trim(cand, target, strat)
                    if L(res) == target:
                        return res

    return text

def build_controlled_banks(
    source_bank_path: str = "data/scenarios_phase0b_utility_matched.json",
    output_dir: str = "data/controlled_strategy_banks_v1",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Build Bank A, Bank B, and Bank C from authoritative Phase 0B scenarios."""
    with open(source_bank_path, "r", encoding="utf-8") as f:
        orig_data = json.load(f)

    scenarios = orig_data["scenarios"]
    bank_a_scenarios = []
    bank_b_scenarios = []
    bank_c_scenarios = []

    review_queue = []

    for s in scenarios:
        sid = s["id"]
        partner_type = s["partner_type"]
        orig_opts = s["options"]

        target_len = 15

        # --- Bank A (Length-matched) ---
        opts_a = {}
        for st in STRATEGIES:
            text = orig_opts[st]
            matched_text = pad_or_trim(text, target_len, st)
            opts_a[st] = matched_text

        sa = copy.deepcopy(s)
        sa["bank_variant"] = "bank_a"
        sa["paraphrase_id"] = f"{sid}_bank_a"
        sa["original_options"] = orig_opts
        sa["options"] = opts_a
        bank_a_scenarios.append(sa)

        val_a = validate_scenario_actions(sa, opts_a, bank_id="bank_a", tokenizer=tok)
        if not val_a.passed or val_a.requires_human_review:
            review_queue.append({
                "scenario_id": sid,
                "bank": "bank_a",
                "passed": val_a.passed,
                "issues": [asdict(iss) for iss in val_a.summary_issues] + [
                    asdict(iss) for act_res in val_a.action_results.values() for iss in act_res.issues
                ],
                "options": opts_a,
            })

        # --- Bank B (Lexically diversified) ---
        opts_b = {}
        for st in STRATEGIES:
            text = orig_opts[st]
            if st == "COOPERATE":
                t = text.replace("Route your ", "Coordinate ").replace("Synchronize your ", "Harmonize ").replace("Couple ", "Interlink ")
                t = t.replace("Merge ", "Pool ").replace("Configure an ", "Set up a ").replace("Adopt the ", "Utilize the ")
                t = t.replace("Broadcast ", "Announce ").replace("Transmit ", "Relay ").replace("Upload ", "Share ")
                t = t.replace("Book a shared ", "Secure a joint ").replace("Sort ", "Classify ").replace("Enable ", "Activate ")
                t = t.replace("Interleave ", "Stagger ").replace("Exchange ", "Trade ").replace("Divide ", "Split ")
                t = t.replace("Connect ", "Hook up ").replace("Align ", "Match ").replace("Hold ", "Keep ")
            elif st == "INDEPENDENT":
                t = text.replace("Process your ", "Handle ").replace("Operate your ", "Run ").replace("Dispatch your ", "Send ")
                t = t.replace("Classify your ", "Categorize ").replace("Run your ", "Execute ").replace("Evaluate your ", "Assess ")
                t = t.replace("Navigate the ", "Steer through the ").replace("File your ", "Submit ").replace("Record ", "Log ")
                t = t.replace("Stack ", "Store ").replace("Discharge ", "Unload ").replace("Spin ", "Centrifuge ")
                t = t.replace("Equip ", "Fit ").replace("Maintain ", "Keep ").replace("Conduct ", "Perform ")
            elif st == "COMPETE_EXPLOIT":
                t = text.replace("Reserve ", "Monopolize ").replace("Schedule early ", "Fast-track ").replace("Preempt the ", "Seize the ")
                t = t.replace("Claim exclusive ", "Lock out ").replace("Submit benchmark ", "Feature benchmark ").replace("Accelerate into ", "Rush into ")
                t = t.replace("Withhold ", "Retain ").replace("Secure commercial ", "Corner commercial ").replace("Export surplus ", "Dump surplus ")
                t = t.replace("Command ", "Direct ").replace("Harvest ", "Fell ").replace("Deposit ", "Log ")
                t = t.replace("Occupancy ", "Take ").replace("Position ", "Place ").replace("Divert ", "Reroute ")
            else:  # DISENGAGE
                t = text.replace("Defer ", "Postpone ").replace("Keep canal gates locked at base levels and defer ", "Pause ")
                t = t.replace("Hold cargo pallets ", "Keep cargo pallets ").replace("Package core specimens in field crates and postpone ", "Delay ")
                t = t.replace("Halt sensor data recording and store ", "Pause data recording and stow ").replace("Withdraw your ", "Remove your ")
                t = t.replace("Anchor in outer harbor staging waters until ", "Stand by until ").replace("Place incoming alloy consignments into bonded storage without ", "Store incoming alloy lots without ")
                t = t.replace("Suspend ", "Pause ").replace("Disconnect from ", "Separate from ")
                t = t.replace("Archive ", "Shelve ").replace("Leave ", "Abandon ").replace("Turn ", "Redirect ")
                t = t.replace("Dismiss ", "Release ").replace("Cancel ", "Drop ").replace("Cover ", "Protect ")

            matched_b = pad_or_trim(t, target_len, st)
            opts_b[st] = matched_b

        sb = copy.deepcopy(s)
        sb["bank_variant"] = "bank_b"
        sb["paraphrase_id"] = f"{sid}_bank_b"
        sb["original_options"] = orig_opts
        sb["options"] = opts_b
        bank_b_scenarios.append(sb)

        val_b = validate_scenario_actions(sb, opts_b, bank_id="bank_b", tokenizer=tok)
        if not val_b.passed or val_b.requires_human_review:
            review_queue.append({
                "scenario_id": sid,
                "bank": "bank_b",
                "passed": val_b.passed,
                "issues": [asdict(iss) for iss in val_b.summary_issues] + [
                    asdict(iss) for act_res in val_b.action_results.values() for iss in act_res.issues
                ],
                "options": opts_b,
            })

        # --- Bank C (Independent paraphrase replication) ---
        opts_c = {}
        for st in STRATEGIES:
            text = orig_opts[st]
            if st == "COOPERATE":
                t = text.replace("Route your ", "Stream ").replace("Synchronize your ", "Align ").replace("Couple ", "Join ")
                t = t.replace("Merge ", "Combine ").replace("Configure an ", "Establish an ").replace("Adopt the ", "Apply the ")
                t = t.replace("Broadcast ", "Disclose ").replace("Transmit ", "Convey ").replace("Upload ", "Transfer ")
                t = t.replace("Book a shared ", "Reserve a shared ").replace("Sort ", "Separate ").replace("Enable ", "Initiate ")
                t = t.replace("Interleave ", "Alternate ").replace("Exchange ", "Swap ").replace("Divide ", "Apportion ")
                t = t.replace("Connect ", "Attach ").replace("Align ", "Coordinate ").replace("Hold ", "Maintain ")
            elif st == "INDEPENDENT":
                t = text.replace("Process your ", "Analyze ").replace("Operate your ", "Manage ").replace("Dispatch your ", "Route ")
                t = t.replace("Classify your ", "Examine ").replace("Run your ", "Conduct ").replace("Evaluate your ", "Benchmark ")
                t = t.replace("Navigate the ", "Traverse the ").replace("File your ", "Archive ").replace("Record ", "Store ")
                t = t.replace("Stack ", "Arrange ").replace("Discharge ", "Empty ").replace("Spin ", "Process ")
                t = t.replace("Equip ", "Load ").replace("Maintain ", "Retain ").replace("Conduct ", "Undertake ")
            elif st == "COMPETE_EXPLOIT":
                t = text.replace("Reserve ", "Capture ").replace("Schedule early ", "Trigger early ").replace("Preempt the ", "Commandeer the ")
                t = t.replace("Claim exclusive ", "Take sole ").replace("Submit benchmark ", "Publish favorable ").replace("Accelerate into ", "Move into ")
                t = t.replace("Withhold ", "Stall ").replace("Secure commercial ", "Buy up commercial ").replace("Export surplus ", "Push surplus ")
                t = t.replace("Command ", "Order ").replace("Harvest ", "Cut ").replace("Deposit ", "Submit ")
                t = t.replace("Occupancy ", "Occupy ").replace("Position ", "Station ").replace("Divert ", "Channel ")
            else:  # DISENGAGE
                t = text.replace("Defer ", "Delay ").replace("Keep canal gates locked at base levels and defer ", "Postpone ")
                t = t.replace("Hold cargo pallets ", "Shelve cargo pallets ").replace("Package core specimens in field crates and postpone ", "Box up samples and delay ")
                t = t.replace("Halt sensor data recording and store ", "Shut down sensors and store ").replace("Withdraw your ", "Cancel your ")
                t = t.replace("Anchor in outer harbor staging waters until ", "Wait at anchor until ").replace("Place incoming alloy consignments into bonded storage without ", "Hold alloy shipments in bonded storage without ")
                t = t.replace("Suspend ", "Decline ").replace("Disconnect from ", "Stand down from ")
                t = t.replace("Archive ", "Store away ").replace("Leave ", "Retain ").replace("Turn ", "Send back ")
                t = t.replace("Dismiss ", "Stand down ").replace("Cancel ", "Call off ").replace("Cover ", "Tarp over ")

            matched_c = pad_or_trim(t, target_len, st)
            opts_c[st] = matched_c

        sc_obj = copy.deepcopy(s)
        sc_obj["bank_variant"] = "bank_c"
        sc_obj["paraphrase_id"] = f"{sid}_bank_c"
        sc_obj["original_options"] = orig_opts
        sc_obj["options"] = opts_c
        bank_c_scenarios.append(sc_obj)

        val_c = validate_scenario_actions(sc_obj, opts_c, bank_id="bank_c", tokenizer=tok)
        if not val_c.passed or val_c.requires_human_review:
            review_queue.append({
                "scenario_id": sid,
                "bank": "bank_c",
                "passed": val_c.passed,
                "issues": [asdict(iss) for iss in val_c.summary_issues] + [
                    asdict(iss) for act_res in val_c.action_results.values() for iss in act_res.issues
                ],
                "options": opts_c,
            })

    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    # Save Bank A
    data_a = copy.deepcopy(orig_data)
    data_a["version"] = "controlled_v1"
    data_a["bank_id"] = "bank_a_length_matched"
    data_a["description"] = "Length-matched strategy bank derived from Phase 0B"
    data_a["scenarios"] = bank_a_scenarios
    (out_p / "bank_a_length_matched.json").write_text(json.dumps(data_a, indent=2), encoding="utf-8")

    # Save Bank B
    data_b = copy.deepcopy(orig_data)
    data_b["version"] = "controlled_v1"
    data_b["bank_id"] = "bank_b_lexically_diversified"
    data_b["description"] = "Lexically diversified strategy bank derived from Phase 0B"
    data_b["scenarios"] = bank_b_scenarios
    (out_p / "bank_b_lexically_diversified.json").write_text(json.dumps(data_b, indent=2), encoding="utf-8")

    # Save Bank C
    data_c = copy.deepcopy(orig_data)
    data_c["version"] = "controlled_v1"
    data_c["bank_id"] = "bank_c_independent_replication"
    data_c["description"] = "Independently paraphrased strategy replication bank derived from Phase 0B"
    data_c["scenarios"] = bank_c_scenarios
    (out_p / "bank_c_independent_replication.json").write_text(json.dumps(data_c, indent=2), encoding="utf-8")

    # Save human review queue
    review_file = out_p / "human_review_queue.json"
    review_file.write_text(json.dumps(review_queue, indent=2), encoding="utf-8")

    return bank_a_scenarios, bank_b_scenarios, bank_c_scenarios, {"total_items_in_review": len(review_queue)}

if __name__ == "__main__":
    build_controlled_banks()
    print("Controlled banks generation complete!")
