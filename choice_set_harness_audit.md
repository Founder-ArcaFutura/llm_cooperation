# Choice-set intervention — Phase 1 harness and raw-record audit

Audit based on the two uploaded ZIP archives containing 14 complete runs (840 presentations each = 11,760 records), the original Phase 1 bank (60 scenarios), the 30-template neutral replacement file, and local launcher/harness files. Analysis carried out November 10–11, 2026 (Toronto local time).

## Main finding

The existing logs show a reproducible, position-robust preference for the original cooperative action descriptions in several base checkpoints. The matched four-option replacement intervention demonstrates this without changing answer-letter position, scenario, or competing noncooperative action texts. The exact cause of the effect is not identified; many neutral replacements fail task/payoff parity.

## Run provenance and quality

- All 14 runs have 840 rows each, the same Phase 1 bank hash (`5994103be281...`) and replacement-bank hash (`7a4234391db5...`), plus resolved model revisions and Transformers 4.57.6.
- Four-option order uses four cyclic permutations (each strategy in each letter once); three-option order uses all six permutations. This controls marginal position frequency but not full four-option adjacency order (which would require 24 permutations).
- `forced_choice_valid` is effectively token-scoring coverage. It does not verify behaviour or resolve extreme letter/token biases.
- Condition-specific answer-letter bias is material, especially for three-choice runs. Pythia is a clean position-only negative control.

## Aggregate measurement inventory

| Checkpoint | Strict four /240 | Unambiguous leading-letter four /240 | Original coop (logit) | Three-option leading (logit) | Neutral replacement leading (logit) | Ties in three /360 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5-3B | 240 | 240 | 94.2% | INDEPENDENT 58.1% | NEUTRAL_OTHER 45.0% | 42 |
| Qwen2.5-1.5B | 198 | 240 | 95.0% | COMPETE_EXPLOIT 44.2% | NEUTRAL_OTHER 52.5% | 30 |
| OLMo2-1B | 5 | 161 | 55.0% | COMPETE_EXPLOIT 45.0% | NEUTRAL_OTHER 34.6% | 37 |
| Llama3.2-3B | 240 | 240 | 85.4% | INDEPENDENT 57.2% | INDEPENDENT 38.8% | 52 |
| Gemma2-2B | 102 | 240 | 49.6% | COMPETE_EXPLOIT 34.7% | COMPETE_EXPLOIT 32.1% | 61 |
| Granite3.3-2B | 0 | 240 | 73.3% | COMPETE_EXPLOIT 38.3% | NEUTRAL_OTHER 27.1% | 18 |
| Qwen2.5-7B | 240 | 240 | 97.5% | INDEPENDENT 72.8% | NEUTRAL_OTHER 62.9% | 16 |
| OLMo2-7B | 0 | 240 | 82.9% | INDEPENDENT 50.8% | INDEPENDENT 38.8% | 0 |
| DeepSeek-7B | 17 | 230 | 69.6% | INDEPENDENT 37.5% | INDEPENDENT 28.3% | 60 |
| Mistral7B | 0 | 239 | 98.3% | COMPETE_EXPLOIT 38.9% | NEUTRAL_OTHER 37.1% | 16 |
| Gemma2-9B | 8 | 240 | 88.8% | INDEPENDENT 69.7% | INDEPENDENT 50.8% | 67 |
| Pythia12B base | 0 | 106 | 25.0% | INDEPENDENT 33.9% | NEUTRAL_OTHER 25.0% | 2 |
| Qwen3B Instruct | 28 | 240 | 87.1% | INDEPENDENT 67.8% | NEUTRAL_OTHER 50.4% | 3 |
| Pythia12B SFT | 0 | 0 | 25.0% | INDEPENDENT 33.3% | NEUTRAL_OTHER 25.0% | 0 |

### Parser issue

The current parser uses `re.fullmatch` against the entire five-token generation. This rejects unambiguous initial letters followed by explanations or another question. OLMo2-7B has 0 strict-valid responses, but 840/840 start with a valid answer letter and every letter matches the forced-choice logit argmax. Mistral and Gemma2-9B likewise show many leading choices. By contrast, Pythia often emits enumerations such as `A, B, C`; these should not be reclassified as clean choices.

A revised analysis should retain **strict-validity** separately and add a **first-selection** parser with outcome categories: exact single answer, unambiguous first answer with continuation, explicit multi-answer enumeration, nonchoice/other. Compare each category with forced-choice scores and report counts per condition. Do not overwrite original metrics.

## Same-position four-choice intervention

The `four` and `four_neutral` prompts differ at exactly one answer-option text in each of the 240 matched scenario×permutation pairs. The three alternatives and the letter position are identical. This permits a direct comparison of conditional letter-token probability for COOPERATE versus its same-position NEUTRAL_OTHER replacement.

| Checkpoint | Mean P(coop letter), original | Mean P(replacement letter), neutral | Difference (pp) | Template-cluster bootstrap 95% CI (pp) | Positive pairs |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-3B | 68.1% | 34.4% | +33.7 | [27.5, 39.8] | 228/240 |
| Qwen2.5-1.5B | 74.7% | 37.0% | +37.8 | [31.6, 43.7] | 230/240 |
| OLMo2-1B | 29.6% | 26.1% | +3.5 | [2.8, 4.2] | 216/240 |
| Llama3.2-3B | 45.9% | 29.4% | +16.4 | [12.7, 20.2] | 208/240 |
| Gemma2-2B | 29.4% | 25.0% | +4.4 | [3.5, 5.5] | 211/240 |
| Granite3.3-2B | 53.8% | 27.1% | +26.8 | [22.9, 30.5] | 230/240 |
| Qwen2.5-7B | 80.9% | 46.2% | +34.6 | [27.3, 42.5] | 232/240 |
| OLMo2-7B | 49.5% | 29.9% | +19.6 | [15.7, 23.1] | 219/240 |
| DeepSeek-7B | 38.2% | 25.5% | +12.7 | [10.3, 15.0] | 230/240 |
| Mistral7B | 62.0% | 28.3% | +33.7 | [28.0, 39.4] | 234/240 |
| Gemma2-9B | 54.0% | 27.3% | +26.7 | [22.7, 30.9] | 232/240 |
| Pythia12B base | 26.5% | 25.1% | +1.4 | [1.1, 1.8] | 157/240 |
| Qwen3B Instruct | 85.8% | 48.6% | +37.2 | [24.5, 50.3] | 209/240 |
| Pythia12B SFT | 26.3% | 25.0% | +1.3 | [0.7, 1.9] | 164/240 |

The bootstrap resamples **30 matched template families**, preserving the two human/AI scenario variants and four order rotations as clustered observations. Its intervals quantify the observed Phase 1 bank, not population-wide replication, and should not be treated as preregistered confirmatory inference.

### Interpretation

This check weakens an explanation based on a *fixed answer-letter preference alone*. It does not distinguish the strategic meaning of cooperation from task-specific lexical/contextual fit, because the substituted action text changes and the replacements do not have established utility parity. It also does not show that *all* pretrained models have the preference (Pythia is an observed counterexample under this interface).

## Critical methodological problems in the harness

1. **Strict generated-answer parser:** `choice_set_intervention.py:63-66` and `choice_set_followup.py:65-68` use a full-string regex, turning valid-looking first selections followed by text into 0% valid models. See above.
2. **Deterministic argmax on ties:** `modal_choice_set.py:46-50` uses `max` after a candidate-letter softmax; it always gives ties to the first inserted letter. For Qwen3B three-option runs 42/360 forced-choice maxima are tied; Llama3B has 52/360. Preserve ties / report fractional or exclude them in sensitivity analysis rather than hard-coding the winning first letter.
3. **Reduced tokenization target:** `answer_token_ids` scores whitespace-prefixed letter tokens (`" A"`, etc.) for every run. It is internally consistent at that boundary, but should be compared to actual generated first-token IDs and tested with alternate answer-format prompts.
4. **Choice-set prompt change:** The three-option condition changes both the number of options and the footer (“A, B, or C” instead of “A, B, C, or D”). The four-neutral matched condition is the best control for fixed option count and matched positions.
5. **Four-option permutation coverage:** 4 cyclic rotations balance answer positions but not all 24 orderings / adjacency relations. All 6 three-way permutations are used.
6. **Neutral replacement utility parity:** `choice_set_neutral_replacements.json` covers 30 templates but some options do not accomplish the same task. E.g. storing GIS results becomes printing coordinates; calibrating an instrument becomes checking a status indicator; applying a mass-centering pulse becomes reading an indicator. Thus four-neutral is a well-controlled *text substitution*, not a certified equal-payoff strategic alternative.
7. **Outcome validity metadata:** `forced_choice_valid = 840` describes candidate token-scoring availability, not evidence that a model can produce or act on a valid selection. Please rename as token coverage in the analysis report.
8. **Independent units:** 60 scenarios comprise 30 matched template families × human/AI partners. Four or six permutations are repeated measures, not independent trials. Use template-family clustered estimates and preserve model/condition-specific performance.
9. **Revision/provenance:** current result files include resolved model hashes, bank/replacement hashes, transformer version, precision. Follow-up should also record exact harness commit, prompt constructor version, parser-version tag, and any revised replacements.

## Large Phase 0/0B follow-up: what was and was not audited

- The ZIP contains `run_choice_set_phase0_followup.ps1` and `choice_set_followup.py`; its default five-model cohort is Qwen1.5B, Qwen3B, Qwen7B, Llama3B, OLMo7B.
- The referenced `modal_choice_set_followup.py`, the two expanded scenario banks, and their expanded replacement banks were **not included** in the uploaded harness ZIP. Therefore the actual Modal follow-up implementation, all 244 neutral replacements and the 244-scenario integrity cannot be independently certified from these uploads.
- Do not replace the primary summary with first-letter counts silently; conduct a labeled retrospective parser audit and freeze the original results.
- Before launching the follow-up: audit/repair neutral replacements for task feasibility, utility equivalence and partner conditions; fix or report parser categories and ties; test a small real-model remote run per model family; verify prompt and bank SHA-256 hashes in the output; then run the full selected cohort.
- Preserve both the 3-option ablation and same-size 4-option substitution; they answer complementary questions.

## Suggested cohort classification from Phase 1

| Cohort | Models | Interpretation |
|---|---|---|
| Primary generated-choice | Qwen2.5-3B, Qwen2.5-7B, Llama3.2-3B | High strict validity and strong original cooperation, but monitor condition-specific letter bias and tied logits. |
| Provisional generated / logit | Qwen2.5-1.5B, OLMo2-7B, Gemma2-9B | First-selection analysis may recover valid data; recheck position effects and prompt decoding. |
| Original-condition logit evidence / position-problematic ablation | Mistral7B, Granite3.3-2B, DeepSeek7B | Original cooperative logits can be strong; 3-option letter bias or low first-letter agreement limits residual ranking interpretation. |
| Low reliability under this instrument | OLMo2-1B, Gemma2-2B, both Pythia12B checkpoints | Letter bias, ambiguous enumeration and/or weak scoring validity. Do not count balanced strategy outputs as semantic flattening. |
| Non-pretrained comparison only | Qwen2.5-3B-Instruct | Analyze separately to avoid conflating pretraining and instruction-tuning origin. |

## Recommended bottom line

**The evidence supports unusually concentrated preference for the cooperative action descriptions in several base checkpoints under the tested prompts, including robust same-letter-position substitution effects.** The strict full-response parser has substantially underestimated answer recoverability. The key unresolved protocol risk for the expensive expanded follow-up is *replacement-action utility parity*, followed by condition-specific position dependence and tie handling. These are addressable without discarding the existing 11,760 saved presentations.
