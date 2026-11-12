import json
from pathlib import Path

from scripts.build_template_adjudication_packets import build_packets

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "reports" / "manuscript_readiness"


def test_packet_build_preserves_pairs_and_priority_counts():
    packets, priority, key, responses, fields, priority_responses, priority_fields = build_packets()
    assert len(packets) == 152
    assert len(priority) == 76
    assert len(key) == 152
    assert len(responses) == 152
    assert len(priority_responses) == 76
    assert [x["packet_id"] for x in priority_responses] == [x["packet_id"] for x in priority]
    assert len({x["packet_id"] for x in packets}) == 152

    priority_key = [x for x in key if x["review_priority"] == "priority_main_analysis"]
    by_bank = {}
    for item in priority_key:
        by_bank[item["source_bank"]] = by_bank.get(item["source_bank"], 0) + 1
    assert by_bank == {"phase0b": 52, "phase1": 24}
    assert sum(len(item["source_rows"]) for item in key) == 304


def test_reviewer_view_omits_sensitive_metadata_and_key_maps_randomized_wordings():
    packets, _, key, _, _, _, _ = build_packets()
    key_by_id = {item["packet_id"]: item for item in key}
    forbidden = {"bank", "template_id", "scenario_id", "partner_type", "utility_condition",
                 "context_type", "is_symmetric_control", "automated_triage_flags",
                 "true_variant_1_label", "original_cooperate", "paraphrased_cooperate"}
    for packet in packets:
        keys = set(packet)
        for version in ("scenario_A", "scenario_B"):
            keys |= set(packet[version])
        assert not forbidden.intersection(keys)
        assert set(packet["scenario_A"]) == set(packet["scenario_B"])
        assert packet["scenario_A"]["cooperative_wording_1"] != packet["scenario_A"]["cooperative_wording_2"]
        assert packet["scenario_B"]["cooperative_wording_1"] != packet["scenario_B"]["cooperative_wording_2"]
        key_item = key_by_id[packet["packet_id"]]
        for version in ("A", "B"):
            source = next(x for x in key_item["source_rows"] if x["scenario_version"] == version)
            assert {source["wording_1_source"], source["wording_2_source"]} == {"original", "paraphrase"}


def test_source_queue_is_read_only_and_outputs_are_blinded():
    source = json.loads((READINESS / "blinded_human_adjudication_queue.json").read_text(encoding="utf-8-sig"))
    packets, _, key, _, _, _, _ = build_packets()
    assert len(source) == 304
    source_ids = {row["scenario_id"] for item in key for row in item["source_rows"]}
    assert source_ids == {row["scenario_id"] for row in source}
    assert all("partner_type" not in packet and "source_bank" not in packet for packet in packets)
