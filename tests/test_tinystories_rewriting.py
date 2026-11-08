import json
from pathlib import Path

import pytest

from research.pretraining_counterfactual_v1.rewriting_v1 import pipeline as p


def test_json_parser_and_schema_integrity():
    payload = {
        "cooperative_story": "Mia shared the ball, and they played together all afternoon.",
        "non_cooperative_story": "Mia kept the ball and won the game before the rain came.",
        "non_cooperative_subtype": "unilateral_self_advantage",
        "metadata": {"source_setting": "park", "retained_characters": "Mia", "changed_social_choice": "kept ball", "causal_outcome": "won game"},
    }
    raw = "```json\n" + json.dumps(payload) + "\n```"
    parsed = p.extract_json_object(raw)
    assert p.validate_generation(parsed, "Mia and Lee found a ball in the park.") is None
    parsed["non_cooperative_subtype"] = "independent_achievement"
    assert p.validate_generation(parsed, "Mia and Lee found a ball in the park.") == "invalid_non_cooperative_subtype"


def test_parser_rejects_malformed_json_and_slogans():
    with pytest.raises(ValueError, match="malformed_json"):
        p.extract_json_object("not json")
    obj = {"cooperative_story": "Sharing is caring and everyone should share every day.",
           "non_cooperative_story": "Jo kept the prize and finished first before anyone else.",
           "non_cooperative_subtype": "fair_competition",
           "metadata": {k: "x" for k in ("source_setting", "retained_characters", "changed_social_choice", "causal_outcome")}}
    assert p.validate_generation(obj, "Jo and Pat saw a prize at the fair.") == "moral_slogan"


def test_theme_balanced_selection_reproducible_and_preserves_hashes(tmp_path):
    rows = []
    texts = ["Mia shared the last apple with Lee.", "Tom raced his rival to win the trophy.",
             "June helped her friend carry the basket.", "Rae kept the prize instead of helping Kim."]
    for i in range(4):
        rows.append({"source_index": i, "sha256": p.sha256_text(texts[i]), "text": texts[i]})
    a = p.select_candidates(rows, 4, 19, review_path=None, subtype_path=None)
    b = p.select_candidates(rows, 4, 19, review_path=None, subtype_path=None)
    assert [x["source_index"] for x in a] == [x["source_index"] for x in b]
    assert all(x["selection_note"].startswith("lexical retrieval cues") for x in a)
    groups = {g for x in a for g in x["candidate_features"]}
    assert set(p.NARRATIVE_TERMS) <= groups


def test_sample_hash_crosscheck_and_pilot_selector():
    sample = p.DEFAULT_SAMPLE
    index = p.DEFAULT_INDEX
    if not sample.exists(): pytest.skip("ignored local TinyStories pilot story cache is unavailable")
    rows = p.load_sample(sample, index)
    assert len(rows) == 10_000
    chosen = p.select_candidates(rows, 100, 20261107)
    assert len(chosen) == 100
    assert len({r["source_index"] for r in chosen}) == 100
    assert all(len(r["sha256"]) == 64 for r in chosen)
    coverage = {g for r in chosen for g in r["candidate_features"]}
    assert coverage == set(p.NARRATIVE_TERMS)


def test_validation_parser_keeps_uncertainty():
    value = {
        "cooperative": {k: True for k in ("behavior_identifiable", "actor_favorable_outcome", "causal_link", "ending_consistent")},
        "non_cooperative": {**{k: None for k in ("behavior_identifiable", "actor_favorable_outcome", "causal_link", "ending_consistent", "subtype_matches_behavior", "no_automatic_punishment_or_repentance")}, "evidence": "unclear"},
        "opposing_strategies_distinct": True, "source_preservation": True, "quality": None,
        "validity": "uncertain", "confidence": 0.55, "notes": "The ending is unclear."}
    value["cooperative"]["evidence"] = "Both cooperate."
    assert p.parse_validation(json.dumps(value)) == value
    invalid = json.loads(json.dumps(value)); invalid["quality"] = 1
    with pytest.raises(ValueError, match="invalid_validation_criterion"):
        p.parse_validation(json.dumps(invalid))


def test_cost_formula_and_no_cloud_without_rate(tmp_path):
    with pytest.raises(ValueError, match="actual Lambda account rate"):
        p.run_generation(type("Args", (), {"hourly_rate_usd": None, "benchmark": True, "count": 100,
                                           "approve_paid_inference": True})())
    with pytest.raises(ValueError, match="explicit --approve-paid-inference"):
        p.run_generation(type("Args", (), {"hourly_rate_usd": 1.0, "benchmark": True, "count": 100,
                                           "approve_paid_inference": False})())


def test_atomic_json(tmp_path):
    target = tmp_path / "record.json"
    p.atomic_json(target, {"source_index": 3, "status": "checkpoint"})
    assert json.loads(target.read_text()) == {"source_index": 3, "status": "checkpoint"}
    assert not list(tmp_path.glob("*.tmp"))


def test_human_review_pack_blinds_strategy_and_separates_answer_key(tmp_path):
    run = tmp_path / "run"; records = run / "records"; records.mkdir(parents=True)
    for sid, subtype in ((1,"fair_competition"),(2,"exploitative_success"),(3,"unilateral_self_advantage")):
        p.atomic_json(records / f"{sid:07d}.json", {
            "source_index":sid,"source_sha256":"a"*64,"candidate_features":["rivalry_fair_competition"],
            "source_story":f"Source story {sid} in the garden.",
            "rewrite":{"cooperative_story":f"Shared story {sid}.","non_cooperative_story":f"Kept story {sid}.",
                       "non_cooperative_subtype":subtype}})
    out=tmp_path/"review.jsonl"
    p.review_sample(type("Args",(),{"run":run,"count":3,"seed":7,"output":out})())
    reviewer=[json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    key=[json.loads(line) for line in Path(str(out)+".key.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(reviewer)==len(key)==3
    assert all("non_cooperative_subtype" not in row and "source_index" not in row for row in reviewer)
    assert all("source_story" in row and row["reviewer_id"] == "" for row in reviewer)
    assert {row["non_cooperative_subtype"] for row in key} == {"fair_competition","exploitative_success","unilateral_self_advantage"}


def test_report_exact_token_supply_and_scale_gate(tmp_path):
    run=tmp_path/"run"; records=run/"records"; records.mkdir(parents=True)
    rec={"source_index":5,"source_story":"A child saw a red ball.","generation_status":"schema_and_integrity_accepted",
         "story_token_ids":{"source_story":[1,2],"cooperative_story":[3,4,5],"non_cooperative_story":[4,6]},
         "rewrite":{"cooperative_story":"A child shared the red ball.","non_cooperative_story":"A child kept the red ball.",
                    "non_cooperative_subtype":"unilateral_self_advantage"}}
    p.atomic_json(records/"0000005.json",rec)
    out=tmp_path/"report.json"
    p.report(type("Args",(),{"run":run,"output":out,"hourly_rate_usd":None,"examples":1,
                               "human_review":None,"human_review_key":None,"minimum_human_review_rows":50})())
    result=json.loads(out.read_text(encoding="utf-8"))
    assert result["model_token_supply"]["unique_token_ids_across_both_rewrite_arms"]==4
    assert result["scale_readiness"]=="AWAITING_INDEPENDENT_HUMAN_REVIEW"
