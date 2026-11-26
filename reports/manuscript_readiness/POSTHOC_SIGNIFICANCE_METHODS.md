# Post-hoc clustered significance analysis

The inferential analyses below were formulated after inspecting the experimental results. They are exploratory, not preregistered confirmatory tests.

## Four-option forced-choice results

The test set is 11 responsive pretrained base checkpoints × two banks, pooling original and reworded presentations while retaining them inside the same template cluster. Pythia is excluded because near-invariant position-A responding makes strategy labels uninterpretable. Complete wording pairs are kept only when both argmax results are untied.

| Model | Bank | N | Clusters | COOP rate | COOP−INDEP | p uniform (Holm) | p contrast (Holm) |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-3B | phase0b | 800 | 52 | 0.881 | 0.787 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| Qwen/Qwen2.5-3B | phase1 | 368 | 24 | 0.943 | 0.902 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| Qwen/Qwen2.5-1.5B | phase0b | 802 | 52 | 0.949 | 0.918 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| Qwen/Qwen2.5-1.5B | phase1 | 374 | 24 | 0.939 | 0.914 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| meta-llama/Llama-3.2-3B | phase0b | 720 | 52 | 0.821 | 0.718 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| meta-llama/Llama-3.2-3B | phase1 | 328 | 24 | 0.817 | 0.674 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| Qwen/Qwen2.5-7B | phase0b | 818 | 52 | 0.933 | 0.866 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| Qwen/Qwen2.5-7B | phase1 | 380 | 24 | 0.976 | 0.961 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| allenai/OLMo-2-1124-7B | phase0b | 832 | 52 | 0.799 | 0.715 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| allenai/OLMo-2-1124-7B | phase1 | 384 | 24 | 0.807 | 0.648 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| google/gemma-2-9b | phase0b | 770 | 52 | 0.935 | 0.883 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| google/gemma-2-9b | phase1 | 352 | 24 | 0.940 | 0.901 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| allenai/OLMo-2-0425-1B | phase0b | 622 | 52 | 0.588 | 0.421 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| allenai/OLMo-2-0425-1B | phase1 | 322 | 24 | 0.506 | 0.342 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| google/gemma-2-2b | phase0b | 414 | 51 | 0.727 | 0.621 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| google/gemma-2-2b | phase1 | 216 | 24 | 0.519 | 0.384 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| ibm-granite/granite-3.3-2b-base | phase0b | 744 | 52 | 0.816 | 0.763 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| ibm-granite/granite-3.3-2b-base | phase1 | 348 | 24 | 0.609 | 0.529 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| mistralai/Mistral-7B-v0.3 | phase0b | 798 | 52 | 0.967 | 0.947 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| mistralai/Mistral-7B-v0.3 | phase1 | 376 | 24 | 0.955 | 0.947 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| deepseek-ai/deepseek-llm-7b-base | phase0b | 708 | 52 | 0.729 | 0.638 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |
| deepseek-ai/deepseek-llm-7b-base | phase1 | 306 | 24 | 0.614 | 0.471 | 1.99996e-05 (0.000879982) | 1.99996e-05 (0.000879982) |

## Three-option choice-set removal

Six pretrained checkpoints were selected for this follow-up; the six were not six independent training-history replications. The primary denominator excludes rows with tied top logits, so only unique argmax outcomes count. The tie-broken legacy outcome is analyzed as a Holm-adjusted sensitivity in the JSON. The main comparison uses template-block label exchangeability for independence above a 1/3 uniform-choice reference and template-block swaps for independence versus competition. Position-letter counts are calculated on unique-argmax rows.

| Model | N unique / ties excluded | Clusters | INDEP rate | INDEP−COMPETE | p uniform (Holm) | p contrast (Holm) | Position A/B/C |
|---|---:|---:|---:|---:|---:|---:|---|
| Qwen/Qwen2.5-3B | 686 / 58 | 54 | 0.644 | 0.354 | 1.99996e-05 (0.000119998) | 0.000539989 (0.00215996) | 0.24/0.39/0.37 |
| Qwen/Qwen2.5-1.5B | 686 / 58 | 54 | 0.551 | 0.197 | 1.99996e-05 (0.000119998) | 0.00357993 (0.0107398) | 0.58/0.10/0.32 |
| meta-llama/Llama-3.2-3B | 652 / 92 | 54 | 0.561 | 0.189 | 1.99996e-05 (0.000119998) | 0.0349193 (0.0698386) | 0.40/0.14/0.46 |
| Qwen/Qwen2.5-7B | 707 / 37 | 54 | 0.734 | 0.526 | 1.99996e-05 (0.000119998) | 1.99996e-05 (0.000119998) | 0.41/0.37/0.22 |
| allenai/OLMo-2-1124-7B | 744 / 0 | 54 | 0.434 | 0.071 | 0.000959981 (0.000959981) | 0.200216 (0.200216) | 0.43/0.11/0.46 |
| google/gemma-2-9b | 601 / 143 | 54 | 0.707 | 0.451 | 1.99996e-05 (0.000119998) | 1.99996e-05 (0.000119998) | 0.31/0.31/0.38 |

## Methods and assumptions

Each test uses 50,000 Monte Carlo randomizations, a fixed seed, and the plus-one p-value estimator. The smallest reportable Monte Carlo p is 1/(B+1); each test stores a Monte Carlo standard error and an exact binomial 95% interval for its exceedance probability. Holm adjustment is applied jointly to the 44 four-option tests and separately within each six-test three-option hypothesis family.

The 25% and 33.3% references are uniform-choice benchmarks. Randomization constructs test exchangeability of strategy labels within template clusters while preserving the observed response pattern and repeated measures; they do not prove that a model literally samples uniformly under the null. The cooperation–independence contrast is a selection-rate contrast. Cluster-level label exchangeability is a substantive assumption, particularly because templates are deliberately heterogeneous. Results are sensitivity evidence, not estimates of population behavior across model training histories.

Rewording is paired by scenario and option permutation, and both wordings remain within the same randomized cluster. The intervention is analyzed separately because removing an option changes the choice set. It is conditional substitution, not evidence that independence is an intrinsic second choice.

Three-option runs use the phase0b bank hash marked `pending_human_scientific_review`; semantic validity and utility properties therefore remain provisional. See the JSON for input SHA-256 values, denominators, counts, position-specific selection rates, and Monte Carlo exceedances.
