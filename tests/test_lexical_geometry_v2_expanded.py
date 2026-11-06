"""Automated test suite for cooperative lexical geometry v2 expanded corpus."""
import hashlib, json, unicodedata
from collections import Counter
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPANDED_DIR = REPO_ROOT / "research" / "cooperative_lexical_geometry_v2_wordlevel_expanded"
PILOT_DIR = REPO_ROOT / "research" / "cooperative_lexical_geometry_v2_wordlevel"

LANGUAGES = ["en", "fr", "zh", "ja", "ar"]
CATEGORIES = ["cooperation", "competition", "independent", "neutral"]


@pytest.fixture(scope="module")
def lexicon():
    lex_file = EXPANDED_DIR / "lexicon.json"
    assert lex_file.exists(), f"lexicon.json not found at {lex_file}"
    return json.loads(lex_file.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verification_records():
    vr_file = EXPANDED_DIR / "verification_records.json"
    assert vr_file.exists(), f"verification_records.json not found at {vr_file}"
    return json.loads(vr_file.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rejected_candidates():
    rc_file = EXPANDED_DIR / "rejected_candidates.json"
    assert rc_file.exists(), f"rejected_candidates.json not found at {rc_file}"
    return json.loads(rc_file.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    m_file = EXPANDED_DIR / "frozen_manifest.json"
    assert m_file.exists(), f"frozen_manifest.json not found at {m_file}"
    return json.loads(m_file.read_text(encoding="utf-8"))


def test_pilot_corpus_unmodified():
    pilot_lex = PILOT_DIR / "lexicon.json"
    assert pilot_lex.exists()
    rows = json.loads(pilot_lex.read_text(encoding="utf-8"))
    assert len(rows) == 24
    pilot_sha = hashlib.sha256(pilot_lex.read_bytes()).hexdigest()
    assert pilot_sha == "d4394eb4f3ae5859333c90abdb3c1f3008d4d8cf3d6c771c4cbc4ebada54373a"


def test_expanded_lexicon_size_and_balance(lexicon):
    assert len(lexicon) == 200
    cats = Counter(r["category"] for r in lexicon)
    assert set(cats.keys()) == set(CATEGORIES)
    for cat in CATEGORIES:
        assert cats[cat] == 50


def test_pilot_and_confirmatory_cohort_split(lexicon):
    cohorts = Counter(r["cohort"] for r in lexicon)
    assert cohorts["pilot"] == 24
    assert cohorts["confirmatory"] == 176

    pilot_rows = json.loads((PILOT_DIR / "lexicon.json").read_text(encoding="utf-8"))
    pilot_map = {r["id"]: r for r in pilot_rows}

    for row in lexicon:
        if row["cohort"] == "pilot":
            orig = pilot_map[row["id"]]
            assert row["category"] == orig["category"]
            for lang in LANGUAGES:
                assert row[lang] == orig[lang]


def test_wordhood_single_unpunctuated_token(lexicon):
    for r in lexicon:
        for lang in LANGUAGES:
            word = r[lang]
            assert word, f"Concept {r['id']} has empty {lang} word"
            for c in word:
                cat = unicodedata.category(c)
                assert not c.isspace(), f"Concept {r['id']} {lang} '{word}' contains space"
                assert cat[0] not in "PZS", f"Concept {r['id']} {lang} '{word}' contains punctuation/symbol '{c}' ({cat})"


def test_zero_duplicates_within_language(lexicon):
    for lang in LANGUAGES:
        counts = Counter(r[lang] for r in lexicon)
        duplicates = {w: c for w, c in counts.items() if c > 1}
        assert not duplicates, f"Language {lang} has duplicate words: {duplicates}"


def test_verification_records_coverage(lexicon, verification_records):
    assert len(verification_records) == len(lexicon)
    vr_by_id = {vr["concept_id"]: vr for vr in verification_records}
    for r in lexicon:
        assert r["id"] in vr_by_id
        vr = vr_by_id[r["id"]]
        assert vr["category"] == r["category"]
        assert vr["cohort"] == r["cohort"]
        assert vr["human_native_review_performed"] is False
        for lang in LANGUAGES:
            lang_rec = vr["languages"][lang]
            assert lang_rec["word"] == r[lang]
            assert "lexical_reference" in lang_rec
            assert "pos" in lang_rec
            assert "verification_status" in lang_rec


def test_rejected_candidates_register(rejected_candidates):
    assert len(rejected_candidates) >= 10
    for rc in rejected_candidates:
        assert "candidate_concept" in rc
        assert "intended_category" in rc
        assert "candidate_words" in rc
        assert "rejection_reason" in rc


def test_frozen_manifest_hash_integrity(manifest):
    file_hashes = manifest["file_hashes"]
    assert len(file_hashes) >= 6
    for fname, expected_hash in file_hashes.items():
        fpath = EXPANDED_DIR / fname
        assert fpath.exists(), f"Manifest file missing: {fname}"
        actual_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {fname}: expected {expected_hash}, got {actual_hash}"


def test_validator_fails_closed_when_verification_records_missing(tmp_path):
    import subprocess, shutil
    shutil.copy(EXPANDED_DIR / "lexicon.json", tmp_path / "lexicon.json")
    shutil.copy(EXPANDED_DIR / "validate.py", tmp_path / "validate.py")
    res = subprocess.run(["python3", str(tmp_path / "validate.py")], capture_output=True, text=True)
    assert res.returncode != 0
    assert "Missing required verification records file" in res.stdout


def test_validator_fails_when_record_count_mismatches(tmp_path):
    import subprocess, shutil
    shutil.copy(EXPANDED_DIR / "lexicon.json", tmp_path / "lexicon.json")
    shutil.copy(EXPANDED_DIR / "validate.py", tmp_path / "validate.py")
    # Write incomplete verification records
    (tmp_path / "verification_records.json").write_text("[]", encoding="utf-8")
    res = subprocess.run(["python3", str(tmp_path / "validate.py")], capture_output=True, text=True)
    assert res.returncode != 0
    assert "does not match lexicon count" in res.stdout
