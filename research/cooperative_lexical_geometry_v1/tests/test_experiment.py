import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_lexicon", ROOT / "build_lexicon.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

def test_lexicon_is_balanced_and_concept_ids_are_stable():
    rows = builder.build()
    assert len(rows) == 600
    assert {c: sum(r["category"] == c for r in rows) for c in builder.KERNELS} == {c: 150 for c in builder.KERNELS}
    assert len({r["concept_id"] for r in rows}) == 600
    assert {r["part_of_speech"] for r in rows} == {"noun_phrase"}
    assert {r["domain"] for r in rows} == set(builder.DOMAINS)

def test_every_concept_has_five_review_tracked_terms():
    for row in builder.build():
        assert set(row["terms"]) == set(builder.LANGS)
        assert set(row["translation_review"]) == set(builder.LANGS)
        assert row["translation_review"]["en"] == "source"
        assert all(row["translation_review"][l] == "human_review_required" for l in builder.LANGS if l != "en")
        assert row["translation_provenance"]

def test_model_revisions_and_encoding_conventions_are_pinned():
    spec2 = importlib.util.spec_from_file_location("runner", ROOT / "run_experiment.py")
    runner = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(runner)
    assert len(runner.MODELS) == 3
    assert all(revision for _, revision, _ in runner.MODELS.values())
    assert runner.MODELS["multilingual-e5-base"][2] == "query: "

def test_zero_norm_embedding_fails_closed(monkeypatch):
    spec2 = importlib.util.spec_from_file_location("runner", ROOT / "run_experiment.py")
    runner = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(runner)
    class FakeModel:
        def __init__(self, *a, **kw): pass
        def eval(self): pass
        def encode(self, texts, **kwargs): return np.zeros((len(texts), 3), dtype=np.float32)
    monkeypatch.setattr(runner, "SentenceTransformer", FakeModel)
    with pytest.raises(ValueError, match="zero embedding"):
        runner.encode("local/fake", "abc123", "", ["x"], 1, True)

