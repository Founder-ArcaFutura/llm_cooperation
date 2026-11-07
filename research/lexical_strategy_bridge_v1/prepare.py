"""Prepare a reproducible lexical inventory and audit locally available evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'research/cooperative_lexical_geometry_v2_wordlevel_expanded'
LANGUAGES = ('en', 'fr', 'zh', 'ja', 'ar')
MODELS = {
    'qwen': ('Qwen/Qwen2.5-1.5B', '8faed761d45a263340a0528343f099c05c9a4323'),
    'olmo7b': ('allenai/OLMo-2-1124-7B', '7df9a82518afdecae4e8c026b27adccc8c1f0032'),
    'mistral7b': ('mistralai/Mistral-7B-v0.3', 'caa1feb0e54d415e2df31207e5f4e273e33509b1'),
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def prepare():
    raw = (CORPUS / 'lexicon.json').read_bytes()
    canonical = raw.replace(b'\r\n', b'\n')
    freeze = json.loads((CORPUS / 'frozen_manifest.json').read_text(encoding='utf-8'))
    if digest(canonical) != freeze['file_hashes']['lexicon.json']:
        raise ValueError('Corpus differs from frozen Git-LF source')
    rows = json.loads(raw)
    if len(rows) != 200 or len({r['id'] for r in rows}) != 200:
        raise ValueError('Corpus inventory mismatch')
    if Counter(r['category'] for r in rows) != {x: 50 for x in ('cooperation','competition','independent','neutral')}:
        raise ValueError('Category inventory mismatch')
    if Counter(r['cohort'] for r in rows) != {'pilot': 24, 'confirmatory': 176}:
        raise ValueError('Cohort inventory mismatch')
    entries = []
    for row in rows:
        for lang in LANGUAGES:
            word = row[lang]
            if not isinstance(word, str) or not word:
                raise ValueError('Empty lexical item')
            for condition in ('isolated', 'neutral'):
                # Brackets are shared across languages and contain no strategic cue.
                text = word if condition == 'isolated' else '[ ' + word + ' ]'
                start = 0 if condition == 'isolated' else 2
                entries.append({'id': row['id'], 'category': row['category'],
                    'cohort': row['cohort'], 'subdomain': row['subdomain'],
                    'language': lang, 'word': word, 'condition': condition,
                    'text': text, 'lexical_chars': [start, start + len(word)]})
    return raw, canonical, entries

def audit_embeddings(raw, canonical, directory):
    result = {}
    for name in ('e5', 'bge-m3', 'labse'):
        summary = json.loads((directory / f'{name}_summary.json').read_text(encoding='utf-8'))
        emb = np.load(directory / f'{name}_embeddings.npy', mmap_mode='r', allow_pickle=False)
        if emb.ndim != 2 or emb.shape[0] != 1000 or not np.isfinite(emb).all():
            raise ValueError(f'Invalid {name} embeddings')
        if not np.allclose(np.linalg.norm(emb, axis=1), 1, atol=1e-4):
            raise ValueError(f'{name} is not normalized')
        files = {}
        for suffix in ('embeddings.npy', 'raw_cosine.npy', 'centered_cosine.npy', 'summary.json'):
            path = directory / f'{name}_{suffix}'
            files[path.name] = digest(path.read_bytes())
        for view in ('raw', 'centered'):
            matrix = np.load(directory / f'{name}_{view}_cosine.npy', mmap_mode='r', allow_pickle=False)
            if matrix.shape != (1000, 1000) or not np.isfinite(matrix).all():
                raise ValueError(f'Invalid {name} {view} matrix')
            x = np.array(emb, copy=True)
            if view == 'centered':
                for i in range(5):
                    x[i::5] -= x[i::5].mean(axis=0)
                    x[i::5] /= np.linalg.norm(x[i::5], axis=1, keepdims=True)
            if not np.allclose(matrix, x @ x.T, atol=3e-5):
                raise ValueError(f'{name} {view} matrix differs from embeddings')
        result[name] = {'model': summary['model'], 'revision': summary['revision'],
            'recorded_input_sha256': summary['lexicon_sha256'],
            'input_hash_matches_current_bytes': summary['lexicon_sha256'] == digest(raw),
            'input_hash_matches_git_lf': summary['lexicon_sha256'] == digest(canonical),
            'shape': list(emb.shape), 'files_sha256': files,
            'ordering': 'concept-major, language en/fr/zh/ja/ar as defined by producer; not independently recorded in artifacts'}
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    ap.add_argument('--embeddings', type=Path, default=CORPUS / 'exploratory_results_20261106')
    args = ap.parse_args()
    raw, canonical, entries = prepare()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    payload = ''.join(json.dumps(x, ensure_ascii=False, sort_keys=True) + '\n' for x in entries).encode('utf-8')
    plan = json.loads((ROOT / 'research/cross_model_ready_v1/manifest.json').read_text(encoding='utf-8'))
    for key, (model, revision) in MODELS.items():
        if (plan['models'][key]['model_id'], plan['models'][key]['revision']) != (model, revision):
            raise ValueError('Historical model plan differs')
    manifest = {'status': 'PREPARED_NO_LEXICAL_INFERENCE', 'exploratory': True,
        'linguistic_review': 'pending', 'source_actual_sha256': digest(raw),
        'source_canonical_lf_sha256': digest(canonical), 'inventory_sha256': digest(payload),
        'entries': len(entries), 'models': {k: plan['models'][k] for k in MODELS},
        'embedding_audit': audit_embeddings(raw, canonical, args.embeddings) if args.embeddings.exists() else 'not available'}
    (out / 'inventory.jsonl').write_bytes(payload)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'output': str(out), 'entries': len(entries), 'source_actual_sha256': digest(raw), 'source_canonical_lf_sha256': digest(canonical)}, indent=2))

if __name__ == '__main__':
    main()
