# Cooperative wording assay — partial paired results

**Status: 9 of 14 checkpoints complete locally; 5 missing. Exploratory.** This report uses the nine complete, integrity-checked local runs. It does not infer completion status of the remaining remote runs. Percentages below are cooperative-minus-independent choice margins, in percentage points; brackets are 95% template/triad-cluster bootstrap intervals for the rewritten-wording margin. Δ is rewritten minus original. Intervals are exploratory and not adjusted for multiplicity. All four position rotations and both partner variants are repeated measures, not independent samples. Tied or unavailable positional scores on either side are excluded pairwise.

| Checkpoint | Phase 0B: original → rewrite [rewrite CI]; Δ; pairs | Phase 1: original → rewrite [rewrite CI]; Δ; pairs |
|---|---|---|
| Qwen/Qwen2.5-3B | 87.0 → 70.5 [60.2, 79.5]; Δ -16.5; 400 pairs (16 excluded) | 99.5 → 81.0 [67.4, 92.6]; Δ -18.5; 184 pairs (8 excluded) |
| Qwen/Qwen2.5-1.5B | 99.0 → 84.5 [76.6, 91.1]; Δ -14.5; 401 pairs (15 excluded) | 98.4 → 84.5 [76.3, 91.9]; Δ -13.9; 187 pairs (5 excluded) |
| allenai/OLMo-2-0425-1B | 54.0 → 30.2 [21.5, 39.1]; Δ -23.8; 311 pairs (105 excluded) | 39.8 → 28.6 [17.4, 39.8]; Δ -11.2; 161 pairs (31 excluded) |
| meta-llama/Llama-3.2-3B | 81.1 → 62.5 [51.6, 73.0]; Δ -18.6; 360 pairs (56 excluded) | 81.1 → 53.7 [31.2, 75.0]; Δ -27.4; 164 pairs (28 excluded) |
| google/gemma-2-2b | 70.5 → 53.6 [43.3, 64.4]; Δ -16.9; 207 pairs (209 excluded) | 46.3 → 30.6 [18.6, 45.3]; Δ -15.7; 108 pairs (84 excluded) |
| ibm-granite/granite-3.3-2b-base | 90.6 → 62.1 [52.6, 70.1]; Δ -28.5; 372 pairs (44 excluded) | 67.2 → 38.5 [28.8, 48.5]; Δ -28.7; 174 pairs (18 excluded) |
| Qwen/Qwen2.5-7B | 94.1 → 79.0 [66.0, 90.7]; Δ -15.2; 409 pairs (7 excluded) | 97.9 → 94.2 [89.1, 98.4]; Δ -3.7; 190 pairs (2 excluded) |
| allenai/OLMo-2-1124-7B | 79.6 → 63.5 [52.9, 74.0]; Δ -16.1; 416 pairs (0 excluded) | 71.4 → 58.3 [40.1, 75.5]; Δ -13.0; 192 pairs (0 excluded) |
| deepseek-ai/deepseek-llm-7b-base | 78.0 → 49.7 [39.3, 60.4]; Δ -28.2; 354 pairs (62 excluded) | 61.4 → 32.7 [18.8, 48.4]; Δ -28.8; 153 pairs (39 excluded) |

Phase 0B and Phase 1 rows use non-symmetric-control equal-utility items only. Both actor payoff matching and interpretation remain conditional on the scenario descriptions; independent semantic equivalence of the rewrites is not established. These are individually estimated margins, not model-family-independent replications or a pooled test. Positive confidence intervals describe uncertainty under the sampled template/triad bootstrap, not a general population of prompts or a causal account of lexical overlap.

The saved `paired_analysis.json` files also contain strict generated-letter results and separate Phase 0, context, original split, utility, and control strata. Strict generation can exclude explanations following an initial letter; some models have very few or zero usable paired generations. Positional scores for checkpoints with extreme letter bias or many tied logits are instrument diagnostics rather than reliable behavioral choices. OLMo 7B scores are retained but its strict generated-letter measure has zero paired valid observations in these strata. Do not silently equate token coverage with valid behavioral choice.

The local integrity audit checks 21,888 rows against the source and paraphrase prompts, option-letter mappings, hashes, and model revisions; see `run_integrity.json`. An additional `semantic_equivalence_review_matrix_304.csv` exists and corresponds to the current wording; its 304 PASS labels use predominantly repeated boilerplate, and its reviewer provenance has not been established in this task. It is not treated here as independent verification. The previously prepared review queue remains applicable.

Missing locally: Mistral 7B, Gemma 9B, Pythia 12B base, Qwen 3B Instruct, and Pythia 12B SFT. Modal could not be contacted to establish whether remotely completed or partial results exist.

Regenerate using `python scripts/audit_cooperate_rewording_results.py`, `python scripts/analyze_cooperate_rewording.py <run-directory>` for each complete run, then `python scripts/report_cooperate_rewording.py`.
