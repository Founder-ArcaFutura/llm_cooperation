"""Bounded offline adjudication ledger; sidecar repair proposals, never a bank."""

import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_cooperation.mechanistic.lexical_pilot import (  # noqa: E402
    STRATEGIES,
    MeasurementTokenizer,
    family,
    measure,
    read_json,
    sha,
    verify_packet,
    write_json,
    SOURCE,
)

GROUPS = {
    "contextual_compression": "Shortened actor/resource names are defensible only when the unchanged stem uniquely resolves the same referent; never infer a new actor, resource or operation.",
    "ordinary_paraphrase": "Synonyms and clause reordering may preserve an action, but do not license changing commitments, exclusivity or utility. Same class label alone is insufficient.",
    "priority_to_schedule": "Reject first relative to others -> ahead of schedule. Restore relative ordering explicitly or reject.",
    "outcome_strengthening": "Reject equal yield -> full yield or new success guarantees. Inherited payoff metadata cannot repair the prose.",
    "deadline_or_duration": "Reject added filing deadlines and pluralized reservation durations. Temporal specificity must match the source.",
    "access_and_rights": "Reject logging out -> terminating access, omitted partner-cohort rights, or weakened/strengthened resource control unless exact equivalence is demonstrated.",
    "operational_scope": "Reject loss of alternation, explicit additional chambers, missing exclusive coverage, different equipment, and return -> landing substitutions without establishing the same operation.",
    "reference_or_allocation_boundary": "At an altitude boundary is not a band extent; changing that reference is not an ordinary shortening.",
}
FAMILY = {
    "template_015": {
        "category": "DEFENSIBLE_PENDING_HUMAN",
        "groups": [
            "contextual_compression",
            "ordinary_paraphrase",
            "operational_scope",
        ],
        "reason": "Restore explicit alternating in both cooperative short forms; restore holding-depot reference and remove added attempt wording. Remaining booking/no-coordination paraphrases follow standalone scheduling in the source.",
        "uncertainties": [
            "Human confirmation of the grouped contextual-reference rule and the same alternating-bay action; no separate decisions for each partner or repeated condition."
        ],
    },
    "template_031": {
        "category": "EXPLICIT_JUDGMENT_REQUIRED",
        "groups": [
            "contextual_compression",
            "priority_to_schedule",
            "operational_scope",
        ],
        "reason": "Restore first relative to other users in both competitive expanded forms; remove concurrent from human cooperation. All other options retain sensor, cartridge, sample, and deferral identities in the unchanged stem.",
        "uncertainties": [
            "Does taking/claiming all cartridges retain the source preemptive resource-control action (not merely obtaining enough cartridges)?",
            "Does collaboration through the same dual-channel sensor retain the original engineer/controller role, with focal osmolality profiling and partner metabolic monitoring?",
        ],
    },
    "template_016": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["operational_scope", "access_and_rights", "deadline_or_duration"],
        "reason": "Buckets become slots; joint loading becomes simultaneous sample preparation; immediate access becomes priority/exclusive access; full-day becomes full days. Several independent repairs and role judgments are required.",
        "uncertainties": [],
    },
    "template_022": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": [
            "reference_or_allocation_boundary",
            "operational_scope",
            "outcome_strengthening",
        ],
        "reason": "Altitude boundary becomes a band extent, corridor occupation becomes use, partner energy harm is newly made explicit, and weather premises change. Negative partner payoff in metadata does not establish the new mechanism.",
        "uncertainties": [],
    },
    "template_024": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["access_and_rights", "operational_scope"],
        "reason": "Multiple rights conditions omit partner cohorts; with-agent export becomes via-agent sharing; logout becomes access termination. Rejected as a complete family, not salvaged from individually plausible options.",
        "uncertainties": [],
    },
    "template_035": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["operational_scope", "access_and_rights"],
        "reason": "Venting an evacuated chamber is replaced by releasing pressure, scope is fixed to both chambers, dedicated bottles become a generic isolated supply, and relative priority is weakened. Physical/action equivalence is unresolved.",
        "uncertainties": [],
    },
    "template_046": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["outcome_strengthening", "access_and_rights", "operational_scope"],
        "reason": "Equal yield becomes full yield; successful timing is imported into cooperation; throughput is added to competition; booking all heads becomes allocation. Removing full yield alone would not validate the family.",
        "uncertainties": [],
    },
    "template_048": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["deadline_or_duration", "access_and_rights", "operational_scope"],
        "reason": "Adds a deadline, changes completed filing to initiating a process, weakens private-index specification, drops defensive scope, and adds later review/temporary suspension. Deleting the deadline alone is insufficient.",
        "uncertainties": [],
    },
    "template_053": {
        "category": "REJECT_CURRENT_FAMILY",
        "groups": ["operational_scope", "access_and_rights"],
        "reason": "Exclusive camera attention becomes prioritization, standalone recording becomes autonomous equipment, and landing becomes return/retraction. Multiple strategic constraints would need restoration. Curly apostrophes are valid Unicode, not a defect.",
        "uncertainties": [],
    },
}
# One explicit proposal per identified defect; no search loop or token-target retries.
REPAIRS = [
    (
        "phase0b_015_human",
        "COOPERATE",
        "concise",
        "Sync hopper bay use",
        "Alternate hopper delivery bays",
        "operational_scope",
    ),
    (
        "phase0b_015_ai",
        "COOPERATE",
        "concise",
        "Coordinate hopper usage",
        "Alternate hopper delivery bays",
        "operational_scope",
    ),
    (
        "phase0b_015_human",
        "DISENGAGE",
        "expanded",
        "regional storage depots",
        "regional holding depots",
        "operational_scope",
    ),
    (
        "phase0b_015_ai",
        "DISENGAGE",
        "concise",
        "without attempting unloading",
        "without unloading",
        "operational_scope",
    ),
    (
        "phase0b_031_human",
        "COMPETE_EXPLOIT",
        "expanded",
        "ahead of schedule",
        "before other users",
        "priority_to_schedule",
    ),
    (
        "phase0b_031_ai",
        "COMPETE_EXPLOIT",
        "expanded",
        "ahead of schedule",
        "before other users",
        "priority_to_schedule",
    ),
    (
        "phase0b_031_human",
        "COOPERATE",
        "expanded",
        "concurrent osmolality profiling",
        "osmolality profiling",
        "operational_scope",
    ),
]


def run(packet, output):
    packet, output = Path(packet), Path(output)
    if output.exists():
        raise FileExistsError(output)
    pm = verify_packet(packet)
    source_sha = sha(SOURCE)
    tok = MeasurementTokenizer()
    assert tok.files == pm["tokenizer_files_sha256"]
    selected = read_json(packet / "paired_coverage.json")["length"]
    assert set(selected) == set(FAMILY)
    scenarios = [
        s
        for s in read_json(packet / "selected_scenarios.json")
        if family(s) in selected
    ]
    by_sid = {s["id"]: s for s in scenarios}
    cs = {c["candidate_id"]: c for c in read_json(packet / "candidates.json")}
    ps = {
        (p["scenario_id"], p["condition"]): p for p in read_json(packet / "panels.json")
    }
    conditions = ("original", "concise", "expanded", "inversion", "reverse")
    used = {
        cid
        for s in scenarios
        for cond in conditions
        for cid in ps[(s["id"], cond)]["candidates"].values()
    }
    proposed = {}
    repairs = []
    for sid, strategy, cond, old, new, group in REPAIRS:
        cid = ps[(sid, cond)]["candidates"][strategy]
        c = cs[cid]
        assert c["text"].count(old) == 1
        text = c["text"].replace(old, new)
        proposed[cid] = text
        repairs.append(
            {
                "source_candidate_id": cid,
                "scenario_id": sid,
                "strategy": strategy,
                "group": group,
                "source_wording": by_sid[sid]["options"][strategy],
                "rejected_wording": c["text"],
                "proposed_wording": text,
                "before": c["measurement"],
                "after": measure(tok, by_sid[sid]["stem"], text),
                "status": "QUARANTINED_HYPOTHETICAL_REPAIR_NOT_BANK_ENTRY",
            }
        )

    def measurement(sid, cid):
        return measure(tok, by_sid[sid]["stem"], proposed.get(cid, cs[cid]["text"]))

    checks = []
    for g in selected:
        rows = [s for s in scenarios if family(s) == g]
        assert sorted(s["id"] for s in rows) == sorted(
            s["id"]
            for s in read_json(packet / "source_snapshot.json")["scenarios"]
            if family(s) == g
        )
        issues = []
        for s in rows:
            sid = s["id"]
            for st in STRATEGIES:
                short = measurement(sid, ps[(sid, "concise")]["candidates"][st])
                long = measurement(sid, ps[(sid, "expanded")]["candidates"][st])
                if not all(
                    short[f] < long[f] for f in ("action_tokens", "prompt_tokens")
                ):
                    issues.append(
                        f"{sid}/{st}: concise not strictly shorter in both counts"
                    )
            for cond, sign in [("inversion", -1), ("reverse", 1)]:
                ms = {
                    st: measurement(sid, ps[(sid, cond)]["candidates"][st])
                    for st in STRATEGIES
                }
                if not all(
                    sign * (ms["COOPERATE"][f] - ms[st][f]) > 0
                    for st in STRATEGIES[1:]
                    for f in ("action_tokens", "prompt_tokens")
                ):
                    issues.append(f"{sid}/{cond}: ordering failed")
            for cond in conditions:
                for cid in ps[(sid, cond)]["candidates"].values():
                    if not measurement(sid, cid)["boundary_ok"]:
                        issues.append(f"{sid}/{cond}: boundary failed")
        status = FAMILY[g]["category"]
        if issues and status != "REJECT_CURRENT_FAMILY":
            status = "REJECT_CURRENT_FAMILY_REPAIR_BROKE_LENGTH"
        checks.append(
            {
                "family": g,
                "scenarios": [s["id"] for s in rows],
                **FAMILY[g],
                "category": status,
                "structural_failures": issues,
                "repair_count": sum(
                    family(by_sid[r["scenario_id"]]) == g for r in repairs
                ),
                "semantic_approval": False,
                "extraction_eligible": False,
            }
        )
    ledger = []
    for cid in sorted(used):
        c = cs[cid]
        text = c["text"].lower()
        rejected_transformations = []
        if c["text"] != c["original"]:
            if "ahead of schedule" in text:
                rejected_transformations.append("priority_to_schedule")
            if "full yield" in text:
                rejected_transformations.append("outcome_strengthening")
            if "filing deadline" in text or "full days" in text:
                rejected_transformations.append("deadline_or_duration")
            if (
                "terminate access" in text
                or ("publication rights" in text and "partner cohorts" not in text)
                or (
                    c["family"] == "template_016"
                    and ("priority access" in text or "exclusive access ahead" in text)
                )
            ):
                rejected_transformations.append("access_and_rights")
            if "both furnace chambers" in text or (
                c["family"] == "template_053"
                and c["strategy"] == "COMPETE_EXPLOIT"
                and "exclusiv" not in text
            ):
                rejected_transformations.append("operational_scope")
        category = next(r["category"] for r in checks if r["family"] == c["family"])
        ledger.append(
            {
                "candidate_id": cid,
                "family": c["family"],
                "strategy": c["strategy"],
                "changed_from_original": c["text"] != c["original"],
                "transformation_groups": rejected_transformations
                or (
                    ["unchanged_source"]
                    if c["text"] == c["original"]
                    else ["contextual_compression", "ordinary_paraphrase"]
                ),
                "family_level_review_groups": FAMILY[c["family"]]["groups"],
                "rejected_transformations": rejected_transformations,
                "disposition": "REJECT_EXISTING_WORDING_REPAIR_PROPOSED"
                if cid in proposed
                else (
                    "REJECT_NON_EQUIVALENT_TRANSFORMATION"
                    if rejected_transformations
                    else "WITHHOLD_INCOMPLETE_FAMILY"
                    if category.startswith("REJECT")
                    else "PENDING_FAMILY_APPROVAL"
                ),
                "approved": False,
            }
        )
    output.mkdir(parents=True)
    write_json(output / "transformation_groups.json", GROUPS)
    write_json(output / "bounded_repair_proposals.json", repairs)
    write_json(output / "family_decisions.json", checks)
    write_json(output / "record_ledger.json", ledger)
    summary = {
        "family_count": 9,
        "categories": dict(Counter(r["category"] for r in checks)),
        "complete_provisional_survivors": sum(
            not r["category"].startswith("REJECT") for r in checks
        ),
        "complete_human_approved_families": 0,
        "repair_proposals": len(repairs),
        "minimum_required_families": 6,
        "current_scope_feasible_for_extraction": False,
        "status": "QUARANTINED_ADJUDICATION_SIDECAR_NO_PROMOTION",
    }
    write_json(output / "summary.json", summary)
    assert sha(SOURCE) == source_sha
    write_json(
        output / "manifest.json",
        {
            "source_bank_sha256": source_sha,
            "source_packet_sha256": sha(packet / "manifest.json"),
            "script_sha256": sha(__file__),
            "files": {p.name: sha(p) for p in sorted(output.iterdir())},
        },
    )
    print(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet", default="research/lexical_confound_pilot_20261106_r2"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.packet, args.output)
