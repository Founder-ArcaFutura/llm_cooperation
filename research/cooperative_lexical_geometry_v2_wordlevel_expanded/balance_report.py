"""Generate balance, length, morphological, and domain coverage report for expanded lexicon."""
import json, statistics
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent
lexicon_path = root / 'lexicon.json'
rows = json.loads(lexicon_path.read_text(encoding='utf-8'))
langs = ['en', 'fr', 'zh', 'ja', 'ar']
cats = sorted({r['category'] for r in rows})

stats = {}

for cat in cats:
    cat_rows = [r for r in rows if r['category'] == cat]
    subdomains = Counter(r['subdomain'] for r in cat_rows)
    lang_lens = {}
    for l in langs:
        lens = [len(r[l]) for r in cat_rows]
        lang_lens[l] = {
            'mean_chars': round(statistics.mean(lens), 2),
            'min_chars': min(lens),
            'max_chars': max(lens)
        }
    stats[cat] = {
        'total_items': len(cat_rows),
        'pilot_items': sum(1 for r in cat_rows if r['cohort'] == 'pilot'),
        'confirmatory_items': sum(1 for r in cat_rows if r['cohort'] == 'confirmatory'),
        'subdomains': dict(subdomains),
        'character_lengths': lang_lens
    }

summary = {
    'total_concepts': len(rows),
    'categories': stats,
    'cross_category_balance': {
        'equal_item_count': len({s['total_items'] for s in stats.values()}) == 1,
        'equal_pilot_count': len({s['pilot_items'] for s in stats.values()}) == 1,
        'equal_confirmatory_count': len({s['confirmatory_items'] for s in stats.values()}) == 1
    }
}

report_path = root / 'balance_summary.json'
report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
