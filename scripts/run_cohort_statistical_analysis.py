"""Update paired wording analysis for all complete canonical runs."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from llm_cooperation.statistical_audit import run_full_cohort_analysis

MANIFEST_AUDIT = Path('reports/manuscript_readiness/cohort_provenance_manifest.json')
OUT_DIR = Path('reports/manuscript_readiness')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    if not MANIFEST_AUDIT.exists():
        from scripts.audit_cooperate_rewording_results import audit_cohort_and_provenance
        manifest_info = audit_cohort_and_provenance()
    else:
        manifest_info = json.loads(MANIFEST_AUDIT.read_text(encoding='utf-8-sig'))

    print(f"Running full cohort statistical analysis (bootstrap={args.bootstrap}, seed={args.seed})...")
    results = run_full_cohort_analysis(manifest_info, bootstrap=args.bootstrap, seed=args.seed)

    def sha256(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
    results["analysis_provenance"] = {
        "source_revision": revision,
        "worktree_dirty_at_analysis": dirty,
        "runner_sha256": sha256(__file__),
        "analysis_engine_sha256": sha256("llm_cooperation/statistical_audit.py"),
        "input_rows_sha256": {
            model: info["rows_sha256"]
            for model, info in manifest_info["canonical_runs"].items()
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / 'cohort_statistical_readout.json'
    out_file.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(f"Saved full cohort analysis to {out_file}")

    # Also update paired_analysis.json in each individual run directory for consistency
    for model, m_data in results['per_model_results'].items():
        run_dir = Path('results/cooperate_rewording') / m_data['directory']
        run_paired_file = run_dir / 'paired_analysis.json'
        run_meta = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8-sig'))
        run_res = {
            'model': run_meta['model'],
            'run_id': run_meta['run_id'],
            'warning': 'Template/triad-cluster bootstrap. Repeated measures across 4 rotations, 2 partners, 2 wordings. Paired exclusions transparently reported.',
            'banks': {
                b_name: b_info['strata']
                for b_name, b_info in m_data['analysis']['banks'].items()
            },
            'parser_audit': m_data['analysis']['parser_audit'],
            'pythia_diagnostics': m_data['analysis']['pythia_diagnostics']
        }
        run_paired_file.write_text(json.dumps(run_res, indent=2) + '\n', encoding='utf-8')
        print(f"Updated {run_paired_file}")


if __name__ == '__main__':
    main()
