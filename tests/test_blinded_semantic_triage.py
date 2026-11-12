import json
from pathlib import Path

from scripts.run_blinded_semantic_triage import (
    compare_passes,
    evidence_warnings,
    sample_low,
    user_prompt,
    validate_judgment,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "reports" / "manuscript_readiness" / "adjudication_template_packets" / "priority_76_blinded_packets.json"


def valid_judgment(packet_id):
    return {
        "packet_id": packet_id,
        "overall_severity": "LOW",
        "overall_confidence": 0.8,
        "utility_judgments": [
            {"scenario_version": v, "cooperative_wording": w, "judgment": "UNCLEAR", "confidence": 0.5, "evidence_excerpt": "", "explanation": "Insufficient detail."}
            for v in ("A", "B") for w in (1, 2)
        ],
        "wording_assessments": [
            {"scenario_version": v, "wording_1_adds_material_advantage_cost_or_obligation": False,
             "wording_2_adds_material_advantage_cost_or_obligation": False, "wording_1_effect": "", "wording_2_effect": "",
             "judgment": "UNCLEAR", "evidence_excerpt": "", "explanation": "Cannot compare."}
            for v in ("A", "B")
        ],
        "noncooperative_alternatives": {"judgment": "UNCLEAR", "confidence": 0.5, "evidence_excerpt": "", "explanation": "Unclear."},
        "partner_variant_comparison": {"judgment": "UNCLEAR", "confidence": 0.5, "evidence_excerpt": "", "explanation": "Unclear."},
        "issues": [], "interpretation_limits": [], "main_claim_vulnerability_from_text_only": "UNCLEAR", "summary": "Unclear.",
    }


def test_prompt_contains_only_blinded_packet_material():
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))[0]
    prompt = user_prompt(packet)
    assert packet["packet_id"] in prompt
    for forbidden in ("utility_condition", "source_bank", "partner_type", "model_frequency", "unblinding", "hypothesis"):
        assert forbidden not in prompt


def test_structured_judgment_requires_all_four_utility_cells_and_both_pairs():
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))[0]
    j = valid_judgment(packet["packet_id"])
    validate_judgment(j, packet)
    j["utility_judgments"].pop()
    try:
        validate_judgment(j, packet)
        assert False, "expected missing cell to fail"
    except ValueError as exc:
        assert "A/B x wording" in str(exc)


def test_low_risk_sample_is_reproducible_and_pass_disagreements_escalate():
    first = {f"P{i}": {"judgment": {"overall_severity": "LOW" if i < 10 else "HIGH"}} for i in range(20)}
    assert sample_low(first, 0.2, 20261112) == sample_low(first, 0.2, 20261112)
    assert len(sample_low(first, 0.2, 20261112)) == 2
    a = {"P1": {"judgment": valid_judgment("P1")}}
    b_judgment = valid_judgment("P1")
    b_judgment["overall_severity"] = "MEDIUM"
    b = {"P1": {"judgment": b_judgment}}
    d = compare_passes(a, b)
    assert any(x["field"] == "overall_severity" and x["escalation"] == "HUMAN_REVIEW_WHILE_BLINDED" for x in d)


def test_nonverbatim_evidence_is_flagged_for_human_attention():
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))[0]
    judgment = valid_judgment(packet["packet_id"])
    judgment["utility_judgments"][0]["evidence_excerpt"] = "made-up phrase"
    warnings = evidence_warnings(judgment, packet)
    assert warnings[0]["path"] == "utility_judgments[0]"
    assert warnings[0]["reason"] == "not_an_exact_source_span"
