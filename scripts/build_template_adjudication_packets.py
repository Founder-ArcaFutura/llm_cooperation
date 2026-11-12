"""Restructure the 304-row queue into blinded, paired template review packets.

The reviewer exports omit bank, template, partner, context, utility-condition,
symmetry, triage, and original/paraphrase labels. An internal key preserves
those mappings for post-review analysis and disagreement resolution.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "reports" / "manuscript_readiness"
OUT = READINESS / "adjudication_template_packets"
SOURCE_JSON = READINESS / "blinded_human_adjudication_queue.json"
SEED = 20261111

SCENARIO_FIELDS = (
    "stem_scenario", "option_independent", "option_compete", "option_disengage",
    "blinded_variant_1", "blinded_variant_2",
)


def is_priority_template(rows):
    row = rows[0]
    return (
        row["bank"] in ("phase0b", "phase1")
        and row["utility_condition"] == "equal_utility"
        and str(row["is_symmetric_control"]).lower() != "true"
    )


def scenario_payload(row, rng):
    """Return only text needed to judge one partner version."""
    wordings = [row["blinded_variant_1"], row["blinded_variant_2"]]
    rng.shuffle(wordings)
    return {
        "scenario_stem": row["stem_scenario"],
        "independent_action": row["option_independent"],
        "competing_action": row["option_compete"],
        "disengaging_action": row["option_disengage"],
        "cooperative_wording_1": wordings[0],
        "cooperative_wording_2": wordings[1],
    }


def flatten_packet(packet):
    row = {"packet_id": packet["packet_id"]}
    for version in ("A", "B"):
        for field, value in packet[f"scenario_{version}"].items():
            row[f"scenario_{version}_{field}"] = value
    return row


def response_template(packet_ids):
    fields = ["packet_id", "reviewer_id"]
    for version in ("A", "B"):
        fields.extend([
            f"utility_judgment_{version}_wording_1",
            f"utility_judgment_{version}_wording_2",
            f"plausibility_{version}",
            f"wording_relation_{version}",
            f"notes_{version}",
        ])
    fields.extend([
        "partner_variant_equivalence", "confidence", "disagreement_or_followup_needed",
        "reviewer_overall_notes",
    ])
    return [{field: packet_id if field == "packet_id" else "" for field in fields} for packet_id in packet_ids], fields


def build_packets(seed=SEED):
    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8-sig"))
    grouped = defaultdict(list)
    for row in source:
        grouped[(row["bank"], row["template_id"])].append(row)

    rng = random.Random(seed)
    packets_internal = []
    for (bank, template), rows in grouped.items():
        if len(rows) != 2 or {r["partner_type"] for r in rows} != {"human", "ai"}:
            raise ValueError(f"Expected exactly one human and one AI scenario for {bank}/{template}")
        # Confirm each source row contains two distinct, recoverable wordings.
        for row in rows:
            pair = {row["blinded_variant_1"], row["blinded_variant_2"]}
            if pair != {row["original_cooperate"], row["paraphrased_cooperate"]}:
                raise ValueError(f"Wording pair cannot be unblinded for {row['scenario_id']}")
        ordered = list(rows)
        rng.shuffle(ordered)
        packets_internal.append({
            "bank": bank,
            "template_id": template,
            "priority": is_priority_template(rows),
            "rows_by_version": {"A": ordered[0], "B": ordered[1]},
        })

    rng.shuffle(packets_internal)
    used = set()
    for unit in packets_internal:
        while True:
            packet_id = f"RV-{rng.randrange(100000, 999999)}"
            if packet_id not in used:
                used.add(packet_id)
                break
        unit["packet_id"] = packet_id

    packets = []
    key = []
    for unit in packets_internal:
        packet_rng = random.Random(f"{seed}:{unit['packet_id']}:wordings")
        packet = {
            "packet_id": unit["packet_id"],
            "scenario_A": scenario_payload(unit["rows_by_version"]["A"], packet_rng),
            "scenario_B": scenario_payload(unit["rows_by_version"]["B"], packet_rng),
            "utility_judgment_options": ["EQUAL", "COOPERATIVE_BETTER", "INDEPENDENT_BETTER", "UNCLEAR"],
            "plausibility_options": ["ALL_PLAUSIBLE", "ONE_OR_MORE_FLAWED", "UNREALISTIC_OR_UNINTERPRETABLE"],
            "wording_relation_options": ["SEMANTICALLY_EQUIVALENT", "MEANING_SHIFT", "DESIRABILITY_SHIFT", "UNCLEAR"],
            "partner_equivalence_options": ["EQUIVALENT", "MATERIAL_DIFFERENCE", "UNCLEAR"],
        }
        packets.append(packet)
        key_rows = []
        packet_by_version = {"A": packet["scenario_A"], "B": packet["scenario_B"]}
        for version in ("A", "B"):
            row = unit["rows_by_version"][version]
            word_map = {
                "1": "original" if packet_by_version[version]["cooperative_wording_1"] == row["original_cooperate"] else "paraphrase",
                "2": "original" if packet_by_version[version]["cooperative_wording_2"] == row["original_cooperate"] else "paraphrase",
            }
            key_rows.append({
                "scenario_version": version,
                "scenario_id": row["scenario_id"],
                "partner_type": row["partner_type"],
                "wording_1_source": word_map["1"],
                "wording_2_source": word_map["2"],
                "automated_triage_flags": row["automated_triage_flags"],
                "utility_condition": row["utility_condition"],
                "context_type": row["context_type"],
                "is_symmetric_control": str(row["is_symmetric_control"]).lower() == "true",
            })
        key.append({
            "packet_id": unit["packet_id"],
            "source_bank": unit["bank"],
            "source_template_id": unit["template_id"],
            "review_priority": "priority_main_analysis" if unit["priority"] else "secondary_or_control",
            "priority_rule": "Phase 0B or Phase 1; equal_utility; non-symmetric control" if unit["priority"] else "Not in the 76-template primary review cohort",
            "source_rows": key_rows,
        })

    priority_ids = {item["packet_id"] for item in key if item["review_priority"] == "priority_main_analysis"}
    priority_packets = [p for p in packets if p["packet_id"] in priority_ids]
    response_rows, response_fields = response_template([p["packet_id"] for p in packets])
    priority_response_rows, priority_response_fields = response_template([p["packet_id"] for p in priority_packets])
    return packets, priority_packets, key, response_rows, response_fields, priority_response_rows, priority_response_fields


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    packets, priority, key, responses, response_fields, priority_responses, priority_response_fields = build_packets()
    # Derive a stable, explicit CSV schema from the first flattened packet.
    flattened = [flatten_packet(p) for p in packets]
    packet_fields = list(flattened[0])
    flattened_priority = [flatten_packet(p) for p in priority]

    (OUT / "all_152_blinded_packets.json").write_text(json.dumps(packets, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "priority_76_blinded_packets.json").write_text(json.dumps(priority, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(OUT / "all_152_blinded_packets.csv", flattened, packet_fields)
    write_csv(OUT / "priority_76_blinded_packets.csv", flattened_priority, packet_fields)
    write_csv(OUT / "review_response_template_152.csv", responses, response_fields)
    write_csv(OUT / "priority_review_response_template_76.csv", priority_responses, priority_response_fields)
    (OUT / "INTERNAL_UNBLINDING_KEY.json").write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "COORDINATOR_PRIORITY_MANIFEST.csv").write_text(
        "packet_id,review_priority\n" + "".join(f"{x['packet_id']},{x['review_priority']}\n" for x in key),
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(SOURCE_JSON.read_bytes()).hexdigest()
    builder_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    report = f"""# Template packet build record

- Source queue rows: 304
- Bank-specific templates: 152 (each has one human-partner and one AI-partner scenario)
- Priority templates: 76 (Phase 0B: 52; Phase 1: 24)
- Priority rule: Phase 0B or Phase 1, `equal_utility`, and not a symmetric control
- Packet and wording order seed: {SEED}
- Source queue SHA-256: `{source_hash}`
- Builder SHA-256: `{builder_hash}`
- Repository HEAD at build: `{revision}`
- Reviewer exports omit condition, partner, bank, template/scenario IDs, triage flags, wording-source labels, and model outcomes.
- Original queue files are read-only inputs; packet generation does not modify them.

Each priority template includes both partner variants and both cooperative wordings. Reviewers should score both partner variants separately; this package reduces repetitive navigation, not the number of substantive judgments. Use two independent reviewers and preserve first-pass responses before blind disagreement resolution.
"""
    (OUT / "PACKET_BUILD_RECORD.md").write_text(report, encoding="utf-8")
    print(f"Built {len(packets)} paired template packets; {len(priority)} priority packets; {len(key)} key records")


if __name__ == "__main__":
    main()
