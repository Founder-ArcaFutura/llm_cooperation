"""Audit paired experiment artifacts against source text, provenance, and run manifests.

Audits:
- Model manifest conformance (14 total: 12 base checkpoints in 8 families, Qwen 3B Instruct, exploratory fine-tuned Pythia 12B).
- Distinguishes unique checkpoints from completed run directories.
- Detects duplicate/multiple runs, verifies byte and SHA-256 hashes, and documents canonical runs.
- Validates row-level integrity against source/paraphrase scenarios and option mappings.
- Rejects conflicting, incomplete, or misidentified observations.
"""
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

from llm_cooperation.cooperate_rewording_assay import BANKS, load_items, paired_presentations

ROOT = Path('results/cooperate_rewording')
MANIFEST_PATH = Path('data/cooperate_rewording_model_manifest.json')
OUT_DIR = Path('reports/manuscript_readiness')


def audit_cohort_and_provenance(root: Path = ROOT, manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    expected_models = {v['model']: v['revision'] for v in manifest['models']}
    banks = {b: load_items('data', b) for b in BANKS}

    expected = {}
    for bank, (scenarios, rewrites, hashes) in banks.items():
        for s in scenarios:
            for p in paired_presentations(s, rewrites[s['id']]):
                expected[(bank, s['id'], p['permutation_index'], p['wording'])] = p

    runs_by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    summary_files = sorted(root.glob('*/summary.json'))

    for summary in summary_files:
        run_dir = summary.parent
        meta = json.loads(summary.read_text(encoding='utf-8-sig'))
        model = meta.get('model')
        if not model or model not in expected_models:
            raise ValueError(f"Unexpected model {model} in run {run_dir.name}")

        # Check revisions
        req_rev = meta.get('requested_model_revision')
        res_rev = meta.get('resolved_model_revision')
        if req_rev != expected_models[model] or res_rev != expected_models[model]:
            raise ValueError(f"Revision mismatch for {model} in {run_dir.name}: {res_rev} vs expected {expected_models[model]}")

        # Check bank provenance hashes
        for bank in BANKS:
            if meta['banks'][bank] != banks[bank][2]:
                raise ValueError(f"Bank provenance mismatch for {model} {bank} in {run_dir.name}")

        # Check rows.jsonl
        rows_file = run_dir / 'rows.jsonl'
        if not rows_file.exists():
            raise ValueError(f"Missing rows.jsonl in {run_dir.name}")

        raw_bytes = rows_file.read_bytes()
        file_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        rows = []
        seen = set()
        counts = Counter()
        with rows_file.open(encoding='utf-8-sig') as f:
            for line_idx, line in enumerate(f, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                key = (row['bank'], row['scenario_id'], row['permutation_index'], row['wording'])
                if key in seen or key not in expected:
                    raise ValueError(f"Unexpected/duplicate row {key} at line {line_idx} in {run_dir.name}")
                seen.add(key)
                ref = expected[key]

                for field in ('prompt', 'letter_to_strategy', 'template_id', 'partner_type',
                              'context_type', 'utility_condition', 'split', 'triad_id'):
                    if row.get(field) != ref.get(field):
                        raise ValueError(f"Mismatch {model} {key} field '{field}' in {run_dir.name}")

                choice = row.get('forced_choice')
                if choice:
                    probs = choice['conditional_probabilities']
                    if set(probs) != set(row['letter_to_strategy']) or not math.isclose(sum(probs.values()), 1.0, abs_tol=1e-5):
                        raise ValueError(f"Probability mismatch in {key} for {run_dir.name}")
                    if choice['strategy'] != row['letter_to_strategy'][choice['letter']]:
                        raise ValueError(f"Strategy mismatch in {key} for {run_dir.name}")
                    counts['tie' if choice['tied_max_count'] > 1 else 'untied'] += 1
                else:
                    counts['no_token_score'] += 1

                counts['valid_generated' if row.get('generated_strategy') else 'invalid_generated'] += 1
                rows.append(row)

        if seen != set(expected):
            raise ValueError(f"Incomplete rows for {model} in {run_dir.name}: saw {len(seen)} of {len(expected)}")
        if len(rows) != 2432:
            raise ValueError(f"Incorrect row count for {model} in {run_dir.name}: {len(rows)}")

        runs_by_model[model].append({
            'run_id': meta['run_id'],
            'directory': run_dir.name,
            'model': model,
            'rows_count': len(rows),
            'rows_sha256': file_sha256,
            'counts': dict(counts),
            'summary_meta': meta
        })

    # Reconcile duplicates and canonicalize
    canonical_runs = {}
    duplicate_records = {}

    for model in sorted(expected_models):
        if model not in runs_by_model:
            raise ValueError(f"Missing completed run for required model: {model}")

        model_runs = runs_by_model[model]
        # Check if multiple runs exist
        if len(model_runs) > 1:
            first_hash = model_runs[0]['rows_sha256']
            divergences = [r for r in model_runs[1:] if r['rows_sha256'] != first_hash]
            if divergences:
                raise ValueError(f"Divergent duplicate runs detected for {model}: hashes do not match!")
            
            # Record duplicates
            duplicate_records[model] = {
                'run_count': len(model_runs),
                'runs': [r['directory'] for r in model_runs],
                'rows_sha256': first_hash,
                'status': 'verified_identical_rerun',
                'canonical_choice': model_runs[-1]['directory'],  # newest completed run
                'rationale': 'Byte-for-byte identical rows.jsonl; newest completed run selected as canonical.'
            }
            # Select the newest run as canonical
            canonical_runs[model] = model_runs[-1]
        else:
            canonical_runs[model] = model_runs[0]

    out_result = {
        'expected_models': len(expected_models),
        'completed_unique_models': len(canonical_runs),
        'total_run_directories': len(summary_files),
        'duplicate_runs_count': len(summary_files) - len(canonical_runs),
        'expected_rows_per_model': len(expected),
        'total_validated_canonical_rows': sum(x['rows_count'] for x in canonical_runs.values()),
        'missing_models': sorted(set(expected_models) - set(canonical_runs)),
        'canonical_runs': canonical_runs,
        'duplicate_records': duplicate_records
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / 'cohort_provenance_manifest.json'
    out_file.write_text(json.dumps(out_result, indent=2) + '\n', encoding='utf-8')

    # Also keep backward-compatible path
    compat_file = Path('research/cooperative_paraphrase_current_audit/run_integrity.json')
    compat_file.parent.mkdir(parents=True, exist_ok=True)
    compat_runs = list(canonical_runs.values())
    compat_result = {
        'expected_models': len(expected_models),
        'completed_local_models': len(compat_runs),
        'expected_rows_per_model': len(expected),
        'total_validated_rows': sum(x['rows_count'] for x in compat_runs),
        'missing_models': sorted(set(expected_models) - set(canonical_runs)),
        'runs': compat_runs,
        'duplicate_reruns_documented': duplicate_records
    }
    compat_file.write_text(json.dumps(compat_result, indent=2) + '\n', encoding='utf-8')

    return out_result


def main():
    res = audit_cohort_and_provenance()
    print(f"Audit completed: {res['completed_unique_models']}/{res['expected_models']} unique models verified across {res['total_run_directories']} run directories.")
    print(f"Duplicate reruns detected and verified identical: {list(res['duplicate_records'].keys())}")


if __name__ == '__main__':
    main()
