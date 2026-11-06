"""Structural, lexical, and balance validation for cooperative lexical geometry v2 expanded corpus."""
import hashlib, json, unicodedata
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'lexicon.json'
v_path = root / 'verification_records.json'
r_path = root / 'rejected_candidates.json'

if not path.exists():
    raise FileNotFoundError(f"Missing lexicon file: {path}")

rows = json.loads(path.read_text(encoding='utf-8'))
langs = ['en', 'fr', 'zh', 'ja', 'ar']
errors = []

# 1. Total row count and category balance
cats = Counter(r['category'] for r in rows)
target_count = len(rows) // len(cats)
for cat, count in cats.items():
    if count != target_count:
        errors.append(f"Category imbalance: '{cat}' has {count} items, expected {target_count}")

# 2. Tokenhood and unpunctuated single-word constraint
for row in rows:
    for lang in langs:
        word = row.get(lang, '')
        if not word:
            errors.append(f"{row['id']} {lang}: empty word entry")
            continue
        # Check whitespace or punctuation/symbol characters
        bad_chars = [c for c in word if c.isspace() or unicodedata.category(c)[0] in 'PZS']
        if bad_chars:
            errors.append(f"{row['id']} {lang} '{word}': contains illegal characters {bad_chars}")

# 3. Duplicate checks within each language
for lang in langs:
    counts = Counter(r[lang] for r in rows)
    for word, count in counts.items():
        if count > 1:
            matched_ids = [r['id'] for r in rows if r[lang] == word]
            errors.append(f"{lang}: duplicate word '{word}' in concepts {matched_ids}")

# 4. Cohort integrity: pilot vs confirmatory
cohorts = Counter(r.get('cohort') for r in rows)
if cohorts.get('pilot', 0) != 24:
    errors.append(f"Expected exactly 24 pilot cohort concepts, found {cohorts.get('pilot')}")

# 5. Verification records consistency
if not v_path.exists():
    errors.append(f"Missing required verification records file: {v_path}")
else:
    v_rows = json.loads(v_path.read_text(encoding='utf-8'))
    if len(v_rows) != len(rows):
        errors.append(f"Verification records count ({len(v_rows)}) does not match lexicon count ({len(rows)})")
    v_ids = {v['concept_id'] for v in v_rows}
    lex_ids = {r['id'] for r in rows}
    if v_ids != lex_ids:
        errors.append("Verification records IDs do not match lexicon IDs")

sha256_hash = hashlib.sha256(path.read_bytes()).hexdigest()

report = {
    'sha256': sha256_hash,
    'total_concepts': len(rows),
    'category_counts': dict(cats),
    'cohort_counts': dict(cohorts),
    'structural_errors': errors,
    'languages_verified': langs,
    'independent_human_review_status': 'Dictionary-backed reference established; native fluent human speaker review remains pending before confirmatory inference.',
    'status': 'passed' if not errors else 'failed'
}

print(json.dumps(report, ensure_ascii=False, indent=2))
if errors:
    raise SystemExit(1)
