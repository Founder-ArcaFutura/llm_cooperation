"""Structural validation only; no automatic claim of lexical or translation validity."""
import hashlib, json, unicodedata
from collections import Counter
from pathlib import Path

root=Path(__file__).resolve().parent
path=root/'lexicon.json'
rows=json.loads(path.read_text(encoding='utf-8'))
langs=['en','fr','zh','ja','ar']
errors=[]
for row in rows:
    for lang in langs:
        word=row.get(lang,'')
        if not word or any(c.isspace() or unicodedata.category(c)[0] in 'PZS' for c in word):
            errors.append(f"{row['id']} {lang}: not a single unpunctuated orthographic token")
for lang in langs:
    counts=Counter(r[lang] for r in rows)
    errors += [f'{lang}: duplicate {word}' for word,count in counts.items() if count>1]
print(json.dumps({'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'candidate_counts':dict(Counter(r['category'] for r in rows)),
                  'structural_errors':errors,'human_validated_counts':{c:0 for c in sorted({r['category'] for r in rows})},
                  'review_status':'All translations require independent dictionary-backed lexical and sense review. No-space checks do not establish wordhood in Chinese or Japanese.'},ensure_ascii=False,indent=2))
if errors: raise SystemExit(1)
