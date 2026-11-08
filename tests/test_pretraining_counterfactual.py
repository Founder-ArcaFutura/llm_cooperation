"""Offline synthetic invariants. No HF access, encoders, model training or cloud."""
import json
import sqlite3

import numpy as np
import pytest

from research.pretraining_counterfactual_v1.data import (
    CONDITIONS, census, connect, export, semantic_scores, set_meta, validate_config, weights,
)
from research.pretraining_counterfactual_v1.train import Sampler, projection, reserve_budget


@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / "corpus.sqlite"
    db = connect(path)
    for i, tokens in enumerate(([1, 2, 9], [3, 4, 5, 9], [1, 2, 9])):
        db.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?)",
                   (i, "duplicate" if i != 1 else "other", len(tokens), i/3, (2-i)/3,
                    "{}", f"story {i}", np.array(tokens, dtype="<u4").tobytes()))
    set_meta(db, "complete", True)
    set_meta(db, "identity", {"config": {"dataset": "fixture", "dataset_revision": "a"*40,
                                        "split": "train", "strengths": [0, 4],
                                        "tokenizer": "fixture", "tokenizer_revision": "b"*40}})
    db.commit(); db.close()
    return path


def test_continuous_weights_preserve_baseline_and_full_support():
    x = np.array([0., .5, 1.])
    assert np.array_equal(weights(x, x, "original", 8), np.ones(3))
    assert np.all(np.diff(weights(x, x, "cooperation_depleted", 8)) < 0)
    assert np.all(np.diff(weights(x, x, "competition_enriched", 8)) > 0)
    for c in CONDITIONS:
        assert np.all(weights(x, x, c, 20) > 0)
        assert np.array_equal(weights(x, x, c, 0), np.ones(3))
    with pytest.raises(ValueError):
        weights(x, x, "competition_enriched", float("nan"))


def test_success_competition_requires_in_window_valence_contrast():
    names = ["cooperation_success", "cooperation_failure", "competition_success", "competition_failure", "neutral"]
    # Competition followed by punishment must not become a positive-success score.
    bad = np.array([[.1, .1, .3, .9, .1]])
    _, score, _ = semantic_scores(bad, names, .05)
    assert score == 0
    good = np.array([[.1, .1, .9, .3, .1]])
    assert semantic_scores(good, names, .05)[1] > .99


def test_sampler_resume_preserves_partial_document_rng_and_exposures(corpus):
    a = Sampler(corpus, "competition_enriched", 4, 7)
    prefix = a.take(11)
    state = a.state()
    expected = a.take(73)
    b = Sampler(corpus, "competition_enriched", 4, 7)
    b.restore(state)
    assert b.take(73) == expected
    assert b.exposures == a.exposures
    assert sum(a.exposures.values()) == len(prefix) + len(expected)
    assert a.state()["pending"] == b.state()["pending"]


def test_baseline_preserves_duplicate_row_sampling(corpus):
    a = Sampler(corpus, "original", 8, 123)
    assert np.allclose(a.cdf, [1/3, 2/3, 1])
    assert len(a.ids) == 3  # never silently deduplicate original arm


def test_export_keeps_provenance_original_weights_and_rejects_partial(corpus, tmp_path):
    out = tmp_path / "export"
    export(corpus, out, "original", 8)
    rows = [json.loads(x) for x in (out / "distribution.jsonl").read_text().splitlines()]
    assert [x["source_index"] for x in rows] == [0, 1, 2]
    assert all(x["sampling_weight"] == 1 for x in rows)
    assert rows[0]["sha256"] == rows[2]["sha256"]
    db = connect(corpus); set_meta(db, "complete", False); db.commit(); db.close()
    with pytest.raises(ValueError, match="partial"):
        export(corpus, tmp_path / "partial", "competition_enriched", 4)


def test_budget_cumulative_and_resume_reservation(tmp_path):
    path = tmp_path / "ledger.sqlite"
    reserve_budget(path, "benchmark", 10, 5)
    reserve_budget(path, "benchmark", 10, 5)  # resume does not double charge
    reserve_budget(path, "original", 40, 5)
    reserve_budget(path, "depleted", 40, 5)
    reserve_budget(path, "enriched", 40, 5)
    with pytest.raises(ValueError, match="ceiling"):
        reserve_budget(path, "replication", 20, 5)
    with pytest.raises(ValueError, match="change"):
        reserve_budget(path, "original", 50, 5)
    # Lower prior input cannot erase earlier untracked spend.
    with pytest.raises(ValueError, match="ceiling"):
        reserve_budget(path, "another", 20, 0)


def test_projection_counts_three_arms_and_seeds():
    r = projection(360_000, 100, 2, seeds=3, overhead_hours=1, prior=5)
    assert r["training_gpu_hours"] == 9
    assert r["projected_usd"] == 25
    with pytest.raises(ValueError):
        projection(360_000, 0, 2)


def test_placeholder_revisions_fail_before_network():
    from pathlib import Path
    c = json.loads(Path("research/pretraining_counterfactual_v1/config.json").read_text())
    with pytest.raises(ValueError, match="immutable"):
        validate_config(c)


def test_census_unique_support_and_directional_token_shift(corpus, tmp_path):
    report = census(corpus, tmp_path / "census", draws=100)
    assert report["tokens_with_eos"] == 10
    assert report["unique_text_tokens_with_eos"] == 7
    base = report["conditions"]["original"][0]
    depleted = report["conditions"]["cooperation_depleted"][-1]
    enriched = report["conditions"]["competition_enriched"][-1]
    assert depleted["expected_coop_token_share_proxy"] < base["expected_coop_token_share_proxy"]
    assert enriched["expected_competition_token_share_proxy"] > base["expected_competition_token_share_proxy"]
    assert enriched["available_unique_text_tokens"] == 7
    assert enriched["expected_unique_text_tokens_after_draws"] <= 7
    assert (tmp_path / "census" / "histograms.png").exists()


def test_validation_excludes_train_duplicates_and_preserves_fixed_order(corpus, tmp_path):
    from research.pretraining_counterfactual_v1.train import validation_tokens
    validation = tmp_path / "validation.sqlite"
    training = connect(corpus)
    config = json.loads(training.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0])
    training.close()
    config["config"]["split"] = "validation"
    db = connect(validation); set_meta(db, "identity", config)
    for i, sha in enumerate(("duplicate", "validation-only")):
        db.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?)",
                   (i, sha, 3, 0., 0., "{}", "fixture", np.array([6, 7, 9], dtype="<u4").tobytes()))
    db.commit(); db.close()
    tokens, identity = validation_tokens(corpus, validation, 10)
    assert tokens == [6, 7, 9]
    assert identity["tokens"] == 3


def test_curve_report_refuses_unpaired_initialization(tmp_path):
    from research.pretraining_counterfactual_v1.report import report
    runs = []
    for i, condition in enumerate(CONDITIONS):
        root = tmp_path / condition; root.mkdir(); runs.append(root)
        (root / "run.json").write_text(json.dumps({"identity": {"condition": condition,
            "strength": i, "initial_weights": str(i)}}))
    with pytest.raises(ValueError, match="initialization"):
        report(runs, tmp_path / "report")
