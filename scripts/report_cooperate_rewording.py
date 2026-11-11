"""Create a reproducible snapshot of available paired lexical assay results."""
import json
from pathlib import Path
ROOT=Path('results/cooperate_rewording')
rows=[]
for p in sorted(ROOT.glob('*/paired_analysis.json')):
 a=json.loads(p.read_text(encoding='utf-8-sig'))
 item={'model':a['model'],'run':a['run_id']}
 for bank in ('phase0b','phase1'):
  r=a['banks'][bank]['non_control_equal_utility']['positional_no_ties']
  item[bank]=r
 rows.append(item)
def value(r):
 if not r['paired_presentations']: return 'no usable pairs'
 orig=100*r['original_coop_minus_independent'];para=100*r['paraphrase_coop_minus_independent'];lo,hi=[100*x for x in r['paraphrase_margin_95pct_template_bootstrap_ci']]; delta=100*r['change_paraphrase_minus_original'];n=r['paired_presentations'];excluded=r['excluded_pairs']
 return f'{orig:.1f} → {para:.1f} [{lo:.1f}, {hi:.1f}]; Δ {delta:+.1f}; {n} pairs ({excluded} excluded)'
lines=['# Cooperative wording assay — partial paired results','',
'**Status: 9 of 14 checkpoints complete locally; 5 missing. Exploratory.** This report uses the nine complete, integrity-checked local runs. It does not infer completion status of the remaining remote runs. Percentages below are cooperative-minus-independent choice margins, in percentage points; brackets are 95% template/triad-cluster bootstrap intervals for the rewritten-wording margin. Δ is rewritten minus original. Intervals are exploratory and not adjusted for multiplicity. All four position rotations and both partner variants are repeated measures, not independent samples. Tied or unavailable positional scores on either side are excluded pairwise.', '',
'| Checkpoint | Phase 0B: original → rewrite [rewrite CI]; Δ; pairs | Phase 1: original → rewrite [rewrite CI]; Δ; pairs |','|---|---|---|']
for r in rows:lines.append(f"| {r['model']} | {value(r['phase0b'])} | {value(r['phase1'])} |")
lines += ['', 'Phase 0B and Phase 1 rows use non-symmetric-control equal-utility items only. Both actor payoff matching and interpretation remain conditional on the scenario descriptions; independent semantic equivalence of the rewrites is not established. These are individually estimated margins, not model-family-independent replications or a pooled test. Positive confidence intervals describe uncertainty under the sampled template/triad bootstrap, not a general population of prompts or a causal account of lexical overlap.', '',
'The saved `paired_analysis.json` files also contain strict generated-letter results and separate Phase 0, context, original split, utility, and control strata. Strict generation can exclude explanations following an initial letter; some models have very few or zero usable paired generations. Positional scores for checkpoints with extreme letter bias or many tied logits are instrument diagnostics rather than reliable behavioral choices. OLMo 7B scores are retained but its strict generated-letter measure has zero paired valid observations in these strata. Do not silently equate token coverage with valid behavioral choice.', '',
'The local integrity audit checks 21,888 rows against the source and paraphrase prompts, option-letter mappings, hashes, and model revisions; see `run_integrity.json`. An additional `semantic_equivalence_review_matrix_304.csv` exists and corresponds to the current wording; its 304 PASS labels use predominantly repeated boilerplate, and its reviewer provenance has not been established in this task. It is not treated here as independent verification. The previously prepared review queue remains applicable.', '',
'Missing locally: Mistral 7B, Gemma 9B, Pythia 12B base, Qwen 3B Instruct, and Pythia 12B SFT. Modal could not be contacted to establish whether remotely completed or partial results exist.', '',
'Regenerate using `python scripts/audit_cooperate_rewording_results.py`, `python scripts/analyze_cooperate_rewording.py <run-directory>` for each complete run, then `python scripts/report_cooperate_rewording.py`.']
out=Path('research/cooperative_paraphrase_current_audit/PAIRED_RESULTS_PARTIAL.md');out.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(out)
