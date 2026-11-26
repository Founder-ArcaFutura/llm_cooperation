import hashlib
import json
from pathlib import Path

from scripts.build_manuscript_v1 import build
from scripts.analyze_posthoc_significance import holm

OUT = Path("reports/manuscript_readiness")


def test_manuscript_is_regenerated_from_canonical_outputs():
    text = (OUT / "MANUSCRIPT_V1.md").read_text(encoding="utf-8")
    assert text == build()
    assert "2,000 draws using seed 42" in text
    assert "post-hoc exploratory" in text
    assert "four of six" in text
    assert "held out and unexecuted" in text
    assert "30 templates" in text and "60 scenarios" in text
    assert "inherent second preference" in text
    assert "AI-assisted" in text


def test_posthoc_denominators_correction_and_hash_provenance():
    d = json.loads((OUT / "posthoc_significance_results.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUT / "cohort_provenance_manifest.json").read_text(encoding="utf-8-sig"))
    qualification = json.loads((OUT / "canonical_evidence_qualification.json").read_text(encoding="utf-8-sig"))
    assert len(d["four_option"]) == 22
    assert len(d["three_option"]) == 6
    assert all(x["presentations"] > 0 and x["clusters"] > 0 for x in d["four_option"])
    assert all(x["uniform_test"]["p_holm"] < .05 for x in d["four_option"])
    assert all(x["contrast_test"]["p_holm"] < .05 for x in d["four_option"])
    assert all(len(x["uniform_test"]["exceedance_probability_mc_95pct_ci"]) == 2 for x in d["four_option"])
    assert all(x["uniform_test"]["exceedance_probability_mc_95pct_ci"][1] > x["uniform_test"]["p_mc"] for x in d["four_option"])
    assert sum(x["contrast_test"]["p_holm"] < .05 for x in d["three_option"]) == 4
    assert sum(x["tie_inclusive_sensitivity"]["contrast_test"]["p_holm"] < .05 for x in d["three_option"]) == 4
    assert next(x["excluded_tied_maxima"] for x in d["three_option"] if x["model"] == "google/gemma-2-9b") == 143
    assert next(x["presentations"] for x in d["three_option"] if x["model"] == "google/gemma-2-9b") == 601
    assert all(x["bank_status"] == "pending_human_scientific_review" for x in d["three_option"])
    assert all(x["bank_sha256"] == "a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b" for x in d["three_option"])
    assert d["source_revision"] == qualification["posthoc_reproduction"]["source_revision"]
    assert d["worktree_dirty_at_analysis"] is False
    assert d["analysis_code_sha256"] == hashlib.sha256(Path("scripts/analyze_posthoc_significance.py").read_bytes()).hexdigest()
    assert len(d["analysis_code_sha256"]) == 64
    for x in d["four_option"]:
        assert x["data_sha256"] == manifest["canonical_runs"][x["model"]]["rows_sha256"]


def test_holm_monotonic_adjustment():
    adjusted = holm([.01, .04, .03])
    assert adjusted == [.03, .06, .06]
