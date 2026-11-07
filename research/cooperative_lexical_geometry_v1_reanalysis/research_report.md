# Reanalysis report

## Outcome

The committed cosine matrices support a completed matrix-only reanalysis; no new model inference was run. The original lexicon, matrices, plots, and result JSONs remain unchanged. The earlier cross-language point estimates and intervals did use different pair sets. This reanalysis fixes that mismatch.

Full within-language estimates now use all 11,175 unique concept pairs per category and language, not just the 1,050 pairs sharing a domain. Cross-language estimates use all 22,350 distinct-concept pairs per language pair, excluding identical concept IDs. Their intervals now use the same full-pair estimand. The bootstrap resamples domain and phrase-kernel clusters while counting shared-cluster pair contributions once. It preserves the full-pair estimator in expectation and its tests verify that unit weights reproduce the direct calculation.

## Centered cosine results

Each contrast is cooperation minus the average of competition/exploitation, independent action, and neutral activity. Intervals are 95% crossed-cluster bootstrap intervals. “Without repeated kernels” excludes pairs whose concept labels use the same one of the 15 category kernels across different domain frames.

| Model | Within all pairs | Within without repeated kernels | Cross-language all distinct concepts | Cross-language without repeated kernels |
|---|---:|---:|---:|---:|
| Multilingual E5 | +0.0047 [−0.0252, 0.0386] | +0.0075 [−0.0241, 0.0428] | +0.0044 [−0.0243, 0.0329] | +0.0062 [−0.0218, 0.0356] |
| BGE-M3 | +0.0150 [−0.0245, 0.0550] | +0.0186 [−0.0224, 0.0629] | +0.0168 [−0.0204, 0.0565] | +0.0187 [−0.0184, 0.0593] |
| LaBSE | +0.0060 [−0.0286, 0.0462] | +0.0090 [−0.0276, 0.0505] | +0.0078 [−0.0266, 0.0451] | +0.0088 [−0.0273, 0.0481] |

All centered cooperation-minus-controls intervals include zero. Kernel-level permutation tests, Holm-adjusted across 24 model × view × metric tests, also do not support a centered cooperation effect. The originally reported centered cooperation excess therefore does not survive the corrected all-pairs estimand and uncertainty analysis.

For raw cosine, cooperation-minus-controls is positive for all models and all four estimands. The 95% intervals are above zero for E5, BGE-M3, and LaBSE. Kernel-level permutation tests with Holm correction support raw effects for BGE-M3 and LaBSE, but not E5. These results are sensitive to centering and are exploratory; the categories were not randomized over independently validated lexical materials.

Independent action has the largest centered point estimate in all three models, both within language and cross language, including after repeated-kernel pairs are excluded. Its paired difference from cooperation is positive in every model, but the corresponding cluster-bootstrap intervals include zero. The data therefore do not establish that independent action is statistically more coherent than cooperation.

## Interpretation and remaining confounds

The narrow statistical issue is resolved: cross-language means and intervals now refer to the same pairs, and the reported intervals are centered around the corrected estimator. Excluding repeated-kernel pairs does not reverse the descriptive category ordering, but does not make the lexicon independent or semantically matched.

Cooperation-specific lexical geometry remains **unestablished**. The effect is not robust to per-language centering; all centered cooperation-versus-control intervals include zero. Raw effects remain, especially for BGE-M3 and LaBSE, but may reflect translation choices, lexical valence, frequency, semantic differences between the 15 kernels, and template reuse. The kernel permutation is an exploratory exchangeability check, not randomized causal evidence. No result here implies behavioral cooperation preferences in base language models.

Translation adjudication, valence/frequency matching, and a broader independently authored lexicon remain open scientific work. No paid inference or model reload was needed.

## Reproducibility

- Source lexicon hash: `4588047a7db09004f69505cb291ee739a4c20037a79ae75906e9924a3e691ba1`.
- Matrix hashes and analysis settings: `outputs/reanalysis_manifest.json`.
- Per-model raw and centered estimates, language breakdowns, bootstrap intervals, and permutation results: `outputs/*_reanalysis.json`.
- Tests: 4 passed.
