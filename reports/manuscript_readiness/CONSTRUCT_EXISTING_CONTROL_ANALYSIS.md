# Existing-result audit: symmetric controls

This exploratory descriptive analysis reuses the existing paired, no-ties cohort analysis. It does not recode individual cases or use new model calls. The original and rewritten margins are percentages of retained matched presentations: COOPERATE minus INDEPENDENT. The two strata differ in scenario content as well as the stated control property; differences are not causal effects of interaction structure.

The Phase 1 symmetric controls comprise six templates (025–030): separate activities explicitly described as having no additional operational benefit from synchronization. Simultaneity does not by itself establish interdependence. The Phase 0B symmetric stratum has only two templates. Neither stratum is a validated coordination or helping category. Non-control equal-utility is an author-defined comparison, not its conceptual opposite.

| Model | Bank | Symmetric templates / retained pairs | Original margin | Reworded margin | Non-control templates / retained pairs | Original margin | Reworded margin |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-1.5B | phase0b | 2 / 16 | 100.0% | 100.0% | 52 / 401 | 99.0% | 84.5% |
| Qwen/Qwen2.5-1.5B | phase1 | 6 / 41 | 85.4% | 87.8% | 24 / 187 | 98.4% | 84.5% |
| Qwen/Qwen2.5-3B | phase0b | 2 / 15 | 73.3% | 73.3% | 52 / 400 | 87.0% | 70.5% |
| Qwen/Qwen2.5-3B | phase1 | 6 / 43 | 48.8% | 39.5% | 24 / 184 | 99.5% | 81.0% |
| Qwen/Qwen2.5-7B | phase0b | 2 / 15 | 86.7% | 73.3% | 52 / 409 | 94.1% | 79.0% |
| Qwen/Qwen2.5-7B | phase1 | 6 / 45 | 88.9% | 91.1% | 24 / 190 | 97.9% | 94.2% |
| allenai/OLMo-2-0425-1B | phase0b | 2 / 11 | 45.5% | 54.5% | 52 / 311 | 54.0% | 30.2% |
| allenai/OLMo-2-0425-1B | phase1 | 6 / 38 | 28.9% | 21.1% | 24 / 161 | 39.8% | 28.6% |
| allenai/OLMo-2-1124-7B | phase0b | 2 / 16 | 100.0% | 87.5% | 52 / 416 | 79.6% | 63.5% |
| allenai/OLMo-2-1124-7B | phase1 | 6 / 48 | 56.2% | 41.7% | 24 / 192 | 71.4% | 58.3% |
| deepseek-ai/deepseek-llm-7b-base | phase0b | 2 / 12 | 100.0% | 83.3% | 52 / 354 | 78.0% | 49.7% |
| deepseek-ai/deepseek-llm-7b-base | phase1 | 6 / 33 | 63.6% | 45.5% | 24 / 153 | 61.4% | 32.7% |
| google/gemma-2-2b | phase0b | 2 / 6 | 0.0% | 0.0% | 51 / 207 | 70.5% | 53.6% |
| google/gemma-2-2b | phase1 | 6 / 28 | 35.7% | 14.3% | 24 / 108 | 46.3% | 30.6% |
| google/gemma-2-9b | phase0b | 2 / 13 | 100.0% | 69.2% | 52 / 385 | 95.3% | 81.3% |
| google/gemma-2-9b | phase1 | 6 / 37 | 29.7% | 8.1% | 24 / 176 | 92.6% | 87.5% |
| ibm-granite/granite-3.3-2b-base | phase0b | 2 / 16 | 100.0% | 93.8% | 52 / 372 | 90.6% | 62.1% |
| ibm-granite/granite-3.3-2b-base | phase1 | 6 / 45 | 100.0% | 77.8% | 24 / 174 | 67.2% | 38.5% |
| meta-llama/Llama-3.2-3B | phase0b | 2 / 16 | 100.0% | 100.0% | 52 / 360 | 81.1% | 62.5% |
| meta-llama/Llama-3.2-3B | phase1 | 6 / 40 | 67.5% | 42.5% | 24 / 164 | 81.1% | 53.7% |
| mistralai/Mistral-7B-v0.3 | phase0b | 2 / 16 | 100.0% | 100.0% | 52 / 399 | 99.2% | 90.2% |
| mistralai/Mistral-7B-v0.3 | phase1 | 6 / 44 | 93.2% | 86.4% | 24 / 188 | 98.9% | 90.4% |

Percentages are percentage-point differences in selection rates, not percentages of templates. Pair counts vary with tie exclusions; repeated rotations and partner variants are not independent templates. Model sizes from one family are not independent replications. No statistical test of the between-stratum contrast is reported here. Pythia is excluded for position-A failure; instruct and fine-tuned comparators are excluded from the base cohort.

Source: `cohort_statistical_readout.json`, specifically `per_model_results.*.analysis.banks.*.strata`. Its original analysis provenance and hashes remain in that file. This output is a first readout using existing strata; option-level coding and adjudication remain outstanding.
