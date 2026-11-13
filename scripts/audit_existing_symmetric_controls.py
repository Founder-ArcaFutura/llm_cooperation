"""Describe existing author-designated control strata; does not classify constructs."""
import json
from pathlib import Path

source = Path('reports/manuscript_readiness/cohort_statistical_readout.json')
data = json.loads(source.read_text(encoding='utf-8'))['per_model_results']
out = Path('reports/manuscript_readiness/CONSTRUCT_EXISTING_CONTROL_ANALYSIS.md')
lines = [
    '# Existing-result audit: symmetric controls', '',
    'This exploratory descriptive analysis reuses the existing paired, no-ties cohort analysis. It does not recode individual cases or use new model calls. The original and rewritten margins are percentages of retained matched presentations: COOPERATE minus INDEPENDENT. The two strata differ in scenario content as well as the stated control property; differences are not causal effects of interaction structure.', '',
    'The Phase 1 symmetric controls comprise six templates (025–030): separate activities explicitly described as having no additional operational benefit from synchronization. Simultaneity does not by itself establish interdependence. The Phase 0B symmetric stratum has only two templates. Neither stratum is a validated coordination or helping category. Non-control equal-utility is an author-defined comparison, not its conceptual opposite.', '',
    '| Model | Bank | Symmetric templates / retained pairs | Original margin | Reworded margin | Non-control templates / retained pairs | Original margin | Reworded margin |',
    '|---|---|---:|---:|---:|---:|---:|---:|',
]
for model, record in sorted(data.items()):
    if 'pythia' in model.lower() or 'instruct' in model.lower() or model.startswith('founder-'):
        continue
    for bank in ('phase0b', 'phase1'):
        strata = record['analysis']['banks'][bank]['strata']
        a = strata['symmetric_control']['forced_no_ties']
        b = strata['non_control_equal_utility']['forced_no_ties']
        lines.append(f"| {model} | {bank} | {a['clusters']} / {a['paired_presentations']} | {a['original_margin']*100:.1f}% | {a['paraphrase_margin']*100:.1f}% | {b['clusters']} / {b['paired_presentations']} | {b['original_margin']*100:.1f}% | {b['paraphrase_margin']*100:.1f}% |")
lines += ['', 'Percentages are percentage-point differences in selection rates, not percentages of templates. Pair counts vary with tie exclusions; repeated rotations and partner variants are not independent templates. Model sizes from one family are not independent replications. No statistical test of the between-stratum contrast is reported here. Pythia is excluded for position-A failure; instruct and fine-tuned comparators are excluded from the base cohort.', '', 'Source: `cohort_statistical_readout.json`, specifically `per_model_results.*.analysis.banks.*.strata`. Its original analysis provenance and hashes remain in that file. This output is a first readout using existing strata; option-level coding and adjudication remain outstanding.']
out.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(f'Wrote {out}')
