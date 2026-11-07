"""Prepare a read-only, annotated semantic-review handoff; never approves candidates."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm_cooperation.mechanistic.lexical_pilot import (  # noqa: E402
    MeasurementTokenizer,
    STRATEGIES,
    family,
    read_json,
    write_json,
    sha,
    verify_packet,
    measure,
    SOURCE,
)
from llm_cooperation.mechanistic.lexical_pilot_run import behavior_text  # noqa: E402

# Offline reading judgments: review cues, not automatic semantic approval/rejection.
NOTES = {
    "template_015": {
        "COOPERATE": "Sync/coordinate hopper usage omits explicit alternating of bays. Confirm that timing synchronization still commits to the same alternating allocation, and that the shortened partner reference resolves unambiguously.",
        "INDEPENDENT": "Without coordination is consistent with standalone booking, but strictly/individual delivery window may strengthen the scheduling constraint.",
        "COMPETE_EXPLOIT": "Priority access versus early unloading is plausibly consistent; verify the entire fleet remains reserved and ownership is unchanged.",
        "DISENGAGE": "Storage versus holding depots and without attempting unloading versus without unloading may alter location or the distinction between attempted and completed unloading.",
    },
    "template_016": {
        "COOPERATE": "Opposite/opposing rotor buckets is plausibly preserved. Slots versus buckets and as the robot readies samples may weaken explicit shared loading/coordination.",
        "INDEPENDENT": "Verify water-filled opposing counterweights are the same independent method and do not introduce coordination or a new obligation.",
        "COMPETE_EXPLOIT": "Full days (plural) can broaden a full-day reservation; exclusive/ahead of others strengthens an implication of reserving all instruments. Check duration and access guarantees.",
        "DISENGAGE": "Cold storage and deferred spinning appear aligned; later/subsequent processing must not add a binding resumption commitment.",
    },
    "template_022": {
        "COOPERATE": "Splitting at three thousand meters specifies a boundary; splitting the three-thousand-meter band/zone can instead specify an extent. Check the exact partition.",
        "INDEPENDENT": "Full elevation coverage is retained; solo/no coordination should not imply a different aircraft capability.",
        "COMPETE_EXPLOIT": "Human expanded wording explicitly increases the partner energy cost. Source payoff metadata already encodes a negative partner payoff, but the energy-cost mechanism is newly explicit and can change salience or interpretation. AI concise/expanded wording should also retain occupation of the corridor rather than mere use.",
        "DISENGAGE": "Hazardous weather is newly asserted in AI expanded wording; source only waits until conditions clear. Verify weather premise and recovery condition.",
    },
    "template_024": {
        "COOPERATE": "AI expanded wording changes export with an agent into using the agent to share data. Confirm collaboration, direction of data flow, and same schema/security scope.",
        "INDEPENDENT": "Local/native/private schema references are plausible paraphrases; preserve strict local confinement.",
        "COMPETE_EXPLOIT": "Several revisions omit that publication rights concern partner cohorts. Prior to releasing access also changes an acquisition condition into a temporal prerequisite unless interpreted equivalently.",
        "DISENGAGE": "Lock and log out is a specific action; isolate records and terminate access may imply revoking access for others rather than ending the actor session.",
    },
    "template_031": {
        "COOPERATE": "Concurrent profiling and coordination should preserve the same dual-channel sensor and partner contribution, without asserting a new result.",
        "INDEPENDENT": "Single-channel independent profiling is retained; concise versions rely on stem context for sample identity.",
        "COMPETE_EXPLOIT": "Ahead of schedule differs from processing before other users. Both expanded variants can remove relative priority while adding a timetable benefit.",
        "DISENGAGE": "Pause versus postpone and a subsequent cycle may imply different resumption timing; verify no new constraint.",
    },
    "template_035": {
        "COOPERATE": "Synchronization/shared manifold references appear aligned; verify connection versus coordination describes the same gas circuit.",
        "INDEPENDENT": "Standalone tanks/isolated supply must denote the original dedicated argon bottles, not a different source or isolation requirement.",
        "COMPETE_EXPLOIT": "Maximize vacuum and accelerate your purge can omit explicit priority over others. Evacuation and purge are not automatically identical physical operations.",
        "DISENGAGE": "Human expanded wording vents BOTH furnace chambers, potentially including the partner zone. This newly fixes the scope of an ambiguous plural source. Release chamber pressure may describe a different operation from venting an evacuated furnace to ambient atmosphere.",
    },
    "template_046": {
        "COOPERATE": "Human variants import 16-minute success/full yield into the action. Source promises equality to private yield, not absolute full yield. AI expanded wording adds an explicit result guarantee; verify conditional versus guaranteed outcomes.",
        "INDEPENDENT": "No data exchange/synchronization makes independence explicit; check that defaults and same wafer lot remain unchanged.",
        "COMPETE_EXPLOIT": "Human concise wording adds maximizing personal throughput, while source books heads for exploratory test wafers. AI allocation phrasing may obscure the actor monopolizing all heads.",
        "DISENGAGE": "Completely/all activities may broaden stopping scope beyond the actor planarization operation; preserve nitrogen storage and suspension.",
    },
    "template_048": {
        "COOPERATE": "AI expanded wording adds meeting a filing deadline absent from the stem/source. Re-index versus index is supported by the stem but partner/ontology identity must remain clear.",
        "INDEPENDENT": "AI expanded wording initiates a process rather than filing claims; absence of sharing alone may not preserve the exact private-index method.",
        "COMPETE_EXPLOIT": "AI concise wording drops defensive qualification; retaining intentional obscuring may preserve exploitation but requires classification review.",
        "DISENGAGE": "Human concise wording is a gerund fragment (Halting...). AI wording adds temporary/later review, which can change the resumption commitment.",
    },
    "template_053": {
        "COOPERATE": "Share via modem is less directional than transmit to the partner; shortened aircraft identity and shared modem reference need contextual equivalence review.",
        "INDEPENDENT": "Stored curly apostrophes were verified as valid U+2019 characters, not encoding damage. Autonomous recording/data capture versus a standalone recorder may change method or equipment; verify independence and instrument identity.",
        "COMPETE_EXPLOIT": "Prioritize does not entail exclusively. Some revised actions allow ordinary coverage of other fires, whereas the source restricts cameras exclusively to high-profile perimeters.",
        "DISENGAGE": "Return/retract to base does not explicitly land at the helipad. Preserve landing, location, and suspension scope.",
    },
}


def prepare_review(packet, output):
    packet, output = Path(packet), Path(output)
    if output.exists():
        raise FileExistsError(output)
    manifest = verify_packet(packet)
    original_sha = sha(SOURCE)
    tok = MeasurementTokenizer()
    assert tok.files == manifest["tokenizer_files_sha256"]
    cohort = read_json(packet / "paired_coverage.json")["length"]
    scenarios = [
        s for s in read_json(packet / "selected_scenarios.json") if family(s) in cohort
    ]
    all_source = read_json(packet / "source_snapshot.json")["scenarios"]
    candidates = {c["candidate_id"]: c for c in read_json(packet / "candidates.json")}
    conditions = ("original", "concise", "expanded", "inversion", "reverse")
    panels = {
        (p["scenario_id"], p["condition"]): p for p in read_json(packet / "panels.json")
    }
    used = {
        cid
        for s in scenarios
        for cond in conditions
        for cid in panels[(s["id"], cond)]["candidates"].values()
    }
    assert len(cohort) == 9 and len(scenarios) == 18 and len(used) == 198
    source_members = {
        g: sorted(s["id"] for s in all_source if family(s) == g) for g in cohort
    }
    cohort_members = {
        g: sorted(s["id"] for s in scenarios if family(s) == g) for g in cohort
    }
    assert source_members == cohort_members
    assert len({s["domain"] for s in scenarios}) == 9
    assert len({s["stem"] for s in scenarios}) == 18
    assert all(
        {s["partner_type"] for s in scenarios if family(s) == g} == {"human", "ai"}
        for g in cohort
    )
    order_checks = []
    review_rows = []
    inversion_checks = []
    cards = [
        "# Nine-family inversion semantic review",
        "",
        "Status: OFFLINE ANNOTATION ONLY. Every candidate remains QUARANTINED / PENDING semantic approval.",
        "No revised wording has been accepted. Notes identify plausible equivalence and suspected meaning changes; they are not independent expert certification.",
        "",
        "Each action row gives action / full-prompt tokens. Inversion uses concise cooperation and expanded alternatives; reverse uses the opposite.",
        "Full structured payoffs are included per scenario. Source payoff metadata is inherited, not a validation of revised wording.",
        "",
    ]
    for s in scenarios:
        sid, g = s["id"], family(s)
        cards += [
            f"## {sid} — {g} — {s['domain']}",
            "",
            s["stem"],
            "",
            f"Partner: {s['partner_type']}. Utility condition: {s['utility_condition']}. Original source split: {s['split']}.",
            "",
            "```json",
            json.dumps(s.get("payoff_spec"), indent=2, ensure_ascii=False),
            "```",
            "",
        ]
        for st in STRATEGIES:
            cards += [
                f"### {st}",
                "",
                f"Original: {s['options'][st]}",
                "",
                "| Condition | Candidate ID | Action / prompt tokens | Wording |",
                "|---|---|---:|---|",
            ]
            for cond in conditions:
                c = candidates[panels[(sid, cond)]["candidates"][st]]
                assert measure(tok, s["stem"], c["text"]) == c["measurement"]
                m = c["measurement"]
                cards.append(
                    f"| {cond} | `{c['candidate_id']}` | {m['action_tokens']} / {m['prompt_tokens']} | {c['text']} |"
                )
            cards += ["", "**Semantic review cue:** " + NOTES[g][st], ""]
        for cond, sign in [("inversion", -1), ("reverse", 1)]:
            cs = {
                st: candidates[panels[(sid, cond)]["candidates"][st]]
                for st in STRATEGIES
            }
            gaps = {
                f: [
                    sign
                    * (cs["COOPERATE"]["measurement"][f] - cs[st]["measurement"][f])
                    for st in STRATEGIES[1:]
                ]
                for f in ("action_tokens", "prompt_tokens")
            }
            assert all(v > 0 for vs in gaps.values() for v in vs)
            inversion_checks.append(
                {
                    "scenario_id": sid,
                    "condition": cond,
                    "positive_ordering_margins": gaps,
                }
            )
        for cond in conditions:
            actions = {
                st: candidates[panels[(sid, cond)]["candidates"][st]]["text"]
                for st in STRATEGIES
            }
            positions = {st: [] for st in STRATEGIES}
            for r in range(4):
                order = STRATEGIES[r:] + STRATEGIES[:r]
                text = behavior_text(s["stem"], actions, order)
                prefix = tok.encode(text)
                assert all(
                    tok.encode(text + " " + letter)[:-1] == prefix for letter in "ABCD"
                )
                for pos, st in enumerate(order):
                    positions[st].append(pos)
                order_checks.append(
                    {
                        "scenario_id": sid,
                        "condition": cond,
                        "rotation": r,
                        "order": order,
                        "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    }
                )
            assert all(sorted(v) == list(range(4)) for v in positions.values())
    for cid in sorted(used):
        c = candidates[cid]
        review_rows.append(
            {
                **c,
                "offline_review_note": NOTES[c["family"]][c["strategy"]],
                "encoding_replacement_character": "\ufffd" in c["text"],
                "semantic_decision": "PENDING",
                "approval": False,
            }
        )
    # Verify actual split implementation, not only declared grouping.
    import numpy as np
    from sklearn.model_selection import LeaveOneGroupOut, GroupKFold

    groups = np.array([family(s) for s in scenarios])
    outer = []
    for tr, te in LeaveOneGroupOut().split(np.zeros(len(groups)), groups=groups):
        assert not set(groups[tr]) & set(groups[te])
        for a, b in GroupKFold(4).split(np.zeros(len(tr)), groups=groups[tr]):
            assert not set(groups[tr][a]) & set(groups[tr][b])
        outer.append(
            {
                "training_families": sorted(set(groups[tr])),
                "heldout_families": sorted(set(groups[te])),
            }
        )
    selection_code = (ROOT / "llm_cooperation/mechanistic/lexical_pilot.py").read_text(
        encoding="utf8"
    )
    selection = read_json(packet / "selection.json")
    evidence = {
        "source_packet_manifest_sha256": sha(packet / "manifest.json"),
        "source_sha256": original_sha,
        "source_snapshot_matches_original": manifest["source_sha256"] == original_sha,
        "families": cohort_members,
        "outer_folds": outer,
        "domain_count": 9,
        "source_split_counts": dict(Counter(s["split"] for s in scenarios)),
        "utility_counts": dict(Counter(s["utility_condition"] for s in scenarios)),
        "counterbalanced_presentations_checked": len(order_checks),
        "counterbalancing_scope": "four cyclic orders: each strategy once per position; not all 24 orderings or balanced pairwise adjacency",
        "selection_method": selection["method"],
        "selection_provenance": "Reviewed prepare(), candidate_pools(), select_families(): selection consumes source metadata, tokenized source/candidates, deterministic seed; no activation/result input. Text feasibility enrichment remains a selection limitation.",
        "selection_code_sha256": sha(
            ROOT / "llm_cooperation/mechanistic/lexical_pilot.py"
        ),
        "statistical_independence_limit": "Metadata grouping and distinct domains verified. Independence of conceptual content or authoring effects is not established.",
        "semantic_approval_count": 0,
        "gpu_inference": False,
        "script_sha256": sha(__file__),
    }
    assert "def select_families" in selection_code and len(outer) == 9
    output.mkdir(parents=True)
    (output / "review.md").write_text(
        "\n".join(cards) + "\n", encoding="utf8", newline="\n"
    )
    write_json(output / "annotated_candidates.json", review_rows)
    write_json(output / "design_verification.json", evidence)
    write_json(output / "counterbalancing_checks.json", order_checks)
    write_json(output / "length_ordering_checks.json", inversion_checks)
    template = read_json(packet / "review_length_decisions.template.json")
    assert all(d["decision"] == "PENDING" for d in template["decisions"])
    write_json(output / "semantic_decisions.PENDING.json", template)
    assert sha(SOURCE) == original_sha
    write_json(
        output / "manifest.json",
        {
            "status": "QUARANTINED_OFFLINE_REVIEW",
            "files": {p.name: sha(p) for p in sorted(output.iterdir())},
            "source_packet_manifest_sha256": sha(packet / "manifest.json"),
        },
    )
    print(
        json.dumps(
            {
                "families": 9,
                "scenarios": 18,
                "candidates": len(review_rows),
                "encoding_flagged_candidate_ids": [
                    r["candidate_id"]
                    for r in review_rows
                    if r["encoding_replacement_character"]
                ],
                "counterbalanced_presentations": len(order_checks),
                "approved": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet", default="research/lexical_confound_pilot_20261106_r2"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare_review(args.packet, args.output)
