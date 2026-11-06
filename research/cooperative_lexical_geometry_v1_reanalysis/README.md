# Cooperative lexical geometry v1 reanalysis

This is a **non-destructive, matrix-only** reanalysis. It consumes the committed normalized-embedding cosine matrices and frozen lexicon from `research/cooperative_lexical_geometry_v1/`; it does not load models, change the lexicon, or overwrite original outputs.

## Run

From the repository root in PowerShell:

```powershell
$env:SSLKEYLOGFILE = ''
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest research\cooperative_lexical_geometry_v1_reanalysis\tests -q
python research\cooperative_lexical_geometry_v1_reanalysis\reanalyze.py `
  --bootstrap-draws 2000 `
  --permutation-draws 2000
```

Outputs are written under `outputs/`. The analysis loads existing `.npy` cosine matrices only.

## Corrections

- Recomputes within-language coherence over all 11,175 distinct-concept pairs per category and language. Reports the prior 1,050 same-domain pairs separately.
- Recomputes cross-language distinct-concept coherence over all 22,350 ordered concept pairs per language pair, excluding exact concept matches. Bootstrap intervals use this same estimator.
- Uses a crossed domain × phrase-kernel pair bootstrap. Pair contributions sharing a sampled domain or phrase kernel count that cluster once, avoiding artificial inflation of within-cluster pair mass. Category contrasts share domain draws and draw phrase kernels independently by category.
- Adds sensitivity estimates excluding pairs that reuse the same phrase kernel across domain frames (10,500 within-language and 21,000 cross-language pairs per category/language or language pair).
- Repeats category-label permutations at the phrase-kernel cluster level, keeps all domain renderings together, and Holm-adjusts the 24 model × view × metric tests. These remain exploratory because lexical category assignments were not randomized.

## Limits

The lexicon still reuses 15 kernels in ten domains, and translations are unreviewed drafts. Frequency and positive emotional valence were not measured; shared morphology is only partly probed by the repeated-kernel exclusion. This repairs the statistical estimands and tests sensitivity to template reuse, but does not establish a cooperation-specific representation.
