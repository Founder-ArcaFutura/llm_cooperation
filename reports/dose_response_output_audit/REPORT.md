# Retrospective Output Audit: Decoupling Format Compliance, Token Geometry, and Decision Competence

## Executive Summary

This audit examines all **23,400 recorded model generations** (19,656 behavioural presentations and 3,744 factual calibration presentations) across **13 pretrained checkpoints** and **3 counterbalanced option schedules** (Latin-Square baseline, Order Replication 1, and Order Replication 2) from the exploratory Dose-Response cohort.

The central finding is that **free-generation format failures do not imply failure of content tracking, factual knowledge, or social dilemma evaluation**.
Crucially, models fall along a continuous multidimensional diagnostic space rather than binary competence tiers:

1. **Format-Masked Trackers (e.g., Mistral 7B-v0.3)**: Achieves **87.8% factual calibration accuracy** and **85.9% agreement** between identifiable generated choices and forced-choice scoring, yet scores **1.7% strict calibration validity** and **0.0% strict behavioural validity** because it systematically outputs explanations (`C\n\nExplan`) or verbal preambles (`\n\nThe correct answer`). The model knows the answers and expresses them clearly, but the strict parser rejects them.
2. **Compliant Geometric Focusers (e.g., Qwen 2.5-3B, Llama 3.2-3B)**: In behavioural dilemma presentations, Qwen 2.5-3B concentrates **96.5% of next-token unconditional probability mass** on `{A, B, C, D}` and achieves **100.0% strict behavioural validity** (with **50.0% strict calibration validity**). Similarly, Llama 3.2-3B concentrates **90.9% mass** and achieves **100.0% strict behavioural validity** and **95.5% strict calibration validity**.
3. **Option Echoers & Preamblers (e.g., OLMo-2 7B, Granite 2B, DeepSeek 7B)**: Emit valid option letters followed immediately by action labels (`B. Synchronize...`) or formatting newlines (`\n\nC. Process`), reflecting natural text continuation rather than multiple-choice stopping.
4. **Format-Disregarding / Weak-Mass Responders (e.g., DeepSeek 7B)**: Assigns only **44.4% unconditional mass** to `{A, B, C, D}`. Despite this, recoverable identifiable-answer extraction reaches **100.0% in behavioural dilemmas** and **93.8% in calibration**, while exhibiting pronounced positional bias (normalized entropy **0.637**).

---

## Multidimensional Diagnostic Space: Cross-Model Comparison

The table below reports mean values across all three counterbalanced schedules for each model.

| Model | Calib Acc (FC) | Calib Strict Valid | Calib Id. Rate | Calib Cond Id. Acc | Calib Joint Id. Acc | Behav Strict Valid | Behav Id. Rate | Behav Id. Agree | Uncond ABCD Mass | Positional Entropy | Payoff Slope (Mean) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `HuggingFaceTB/SmolLM2-1.7B` | 69.4% | 0.0% | 100.0% | 69.4% | 69.4% | 0.0% | 99.2% | 98.2% | 0.641 | 0.764 | +0.0534 |
| `Qwen/Qwen2.5-1.5B` | 94.1% | 100.0% | 100.0% | 94.1% | 94.1% | 74.9% | 100.0% | 99.1% | 0.984 | 0.997 | +0.0635 |
| `Qwen/Qwen2.5-3B` | 92.7% | 50.0% | 100.0% | 92.7% | 92.7% | 100.0% | 100.0% | 97.0% | 0.965 | 0.950 | +0.1103 |
| `Qwen/Qwen2.5-7B` | 92.0% | 51.4% | 100.0% | 92.4% | 92.4% | 80.5% | 92.7% | 99.1% | 0.971 | 0.980 | +0.0580 |
| `allenai/OLMo-2-1124-7B` | 83.7% | 0.0% | 93.4% | 83.3% | 77.8% | 0.0% | 100.0% | 99.9% | 0.751 | 0.992 | +0.2026 |
| `deepseek-ai/deepseek-llm-7b-base` | 70.5% | 4.5% | 93.8% | 70.4% | 66.0% | 17.7% | 100.0% | 79.2% | 0.444 | 0.637 | +0.0461 |
| `google/gemma-2-2b` | 29.5% | 0.0% | 89.6% | 29.8% | 26.7% | 40.0% | 100.0% | 99.9% | 0.661 | 0.501 | +0.0287 |
| `google/gemma-2-9b` | 90.6% | 0.0% | 96.2% | 90.6% | 87.2% | 29.2% | 99.9% | 97.8% | 0.742 | 0.985 | +0.1756 |
| `ibm-granite/granite-3.3-2b-base` | 76.4% | 26.7% | 96.9% | 67.0% | 64.9% | 0.0% | 99.8% | 89.7% | 0.651 | 0.989 | +0.1535 |
| `meta-llama/Llama-3.2-3B` | 73.3% | 95.5% | 100.0% | 75.0% | 75.0% | 100.0% | 100.0% | 97.0% | 0.909 | 0.980 | +0.1392 |
| `microsoft/phi-2` | 87.5% | 42.4% | 100.0% | 87.2% | 87.2% | 5.6% | 87.8% | 99.7% | 0.746 | 0.941 | +0.0467 |
| `mistralai/Mistral-7B-v0.3` | 87.8% | 1.7% | 85.1% | 98.8% | 84.0% | 0.0% | 90.0% | 85.9% | 0.579 | 0.993 | +0.0139 |
| `tiiuae/Falcon3-3B-Base` | 92.4% | 0.0% | 100.0% | 92.4% | 92.4% | 0.0% | 100.0% | 98.1% | 0.674 | 0.906 | +0.0992 |

*Methodological Note on Metrics:*
- **Calib Cond Id. Acc**: Accuracy conditioned exclusively on presentations where an identifiable letter was extracted (denominator = identifiable answers).
- **Calib Joint Id. Acc**: Joint accuracy across the entire task (denominator = total presentations, scoring unextracted answers as 0).
- **Strict Validity Note**: The harness strict validator accepts minor whitespace and closing punctuation like `'A.'`, `'(A)'`, or `'A)'`. Thus, 'strict validity' represents compliance with clean answer-marking rather than an exact single-token boundary constraint.
- **Payoff Slope**: Reconciled exactly with `reports/dose_response_order_comparison/comparison.json`. Represents the family-averaged linear slope of COOPERATE selection rate across the 8 payoff tiers ($[-0.60, +0.20]$) in the 6 main exploratory sweep families.
- **Positional Entropy**: Normalized Shannon entropy over forced-choice letters (1.0 indicates perfect balance of 0.25 on A/B/C/D; 0.0 indicates a 100% fixed-letter responder).

---

## Methodological Inquiries and Empirical Reconciliations

### 1. Investigation of Discrepancies Between Greedy Free Generation and Forced-Choice Argmax
Under greedy decoding (`do_sample=False`), does free generation always match the candidate argmax? Across the cohort, discrepancies between the identifiable generated letter and `forced_choice_argmax_letter` occur across multiple models, reflecting two distinct phenomena:

1. **Exact FP16 Candidate Logit Ties (Verified in Qwen, SmolLM2, Gemma, Llama)**:
   - For models with near-100% unconditional candidate mass (e.g. Qwen 2.5-3B, where 69 of 69 discrepancies in run records involve exact ties between candidate logits), options B and C or other pairs share identical half-precision logits (e.g., exactly `22.2500`).
   - In forced-choice scoring, Python evaluates `max(cond_probs, key=cond_probs.get)`. When keys have identical float values, Python returns the first key encountered in iteration order, breaking ties toward the earlier letter alphabetically (e.g., `'B'`).
   - In greedy `generate()`, HuggingFace runs `torch.argmax(next_token_logits, dim=-1)` over the vocabulary tensor. PyTorch breaks ties by returning the smaller token index in the vocabulary (for instance, in Qwen, candidate token `' C'` has ID `356`, while `' B'` has ID `425`, so token `356` is emitted).
   - This confirms that when candidate mass is high and generation emits an isolated letter immediately, candidate discrepancies are exact logit tie-breaking artifacts between dictionary key order and vocabulary ID order.

2. **Unconstrained Step-0 Continuation Divergence (DeepSeek, Granite, Mistral)**:
   - In models with lower candidate mass or leading preamble tendencies, the global winning token across the full vocabulary at step 0 is not necessarily in `{A, B, C, D}` (e.g. emitting leading newlines `\n\n` or words).
   - Because the harness records only candidate logits rather than full-vocabulary logits at every generation step, we cannot trace the global argmax path across arbitrary vocabulary tokens for every completion. However, once unconstrained generation branches into a preamble or list format, subsequent tokens are conditioned on new context and may settle on a different letter than the step-0 constrained candidate scores.

### 2. High Agreement vs Demonstrated Semantic Competence in Position-Biased Models
A critical scientific caveat: **high agreement between forced-choice and generated choice does not establish dilemma comprehension**.
- For example, SmolLM2 1.7B exhibits **98.2% agreement** between its generated choices and forced-choice scoring.
- However, SmolLM2 is a strongly position-biased model (positional entropy **0.764**), selecting option `'A'` in over 62% of presentations regardless of whether option `'A'` is COOPERATE, INDEPENDENT, or COMPETE.
- Because the model strongly favors token `'A'`, both its forced-choice argmax and its free generation output `'A'`. Their 98%+ agreement merely reflects an invariant token/positional preference, not strategic reasoning.
- Researchers must evaluate agreement in conjunction with positional entropy and payoff sensitivity slopes.

### 3. Heuristic Truncation Diagnostics Under 5-Token Horizon
- The 5-token budget captured answers successfully for models that emit letter-first continuations (`A\n\nExplan`), but frequently cut off completions that began with conversational preambles.
- In total, **8,608 presentations** were flagged by the heuristic truncation detector as ending in unfinished preambles, explanation stems, or incomplete words.
- In particular, **203 calibration presentations** from Mistral 7B ended abruptly in `\n\nThe correct answer` without reaching a letter token. While extending the token horizon would allow inspecting whether the model eventually states the letter, under the fixed 5-token budget these records remain unextracted preambles.

---

## Deep Dives on Informative Focal Cases

### 1. Mistral 7B-v0.3: Format-Masked Factual & Social Competence
- **The Empirical Paradox**: Under strict letter parsing, Mistral 7B achieves a recorded calibration validity of **1.7%** and behavioural validity of **0.0%**.
- **The Underlying Reality**: Constrained forced-choice scoring reveals factual accuracy of **87.8%**. Extracting the identifiable letter from `generated_raw_text` reveals an identifiable answer in **85.1%** of calibration and **90.0%** of behavioural presentations.
- **Conditioned Accuracy & Agreement**: When Mistral emits an identifiable letter on calibration, that letter is **98.8% accurate**! On behavioural dilemmas, the identifiable generated letter agrees with the forced-choice argmax **85.9%** of the time.
- **Continuation Mechanism**: Mistral 7B decodes predominantly into `C\n\nExplan`, `B\n\nExplan`, or preamble strings like `\n\nThe correct answer`. Because the harness bounded generation to 5 tokens, the model emits the letter and immediately begins generating an explanation.

### 2. DeepSeek LLM 7B Base: Reconciled Cohort Profile
- **Audited Recovery Rates**: In behavioural dilemmas, DeepSeek achieves **100.0% identifiable-answer recovery** across all three schedules. In calibration, it achieves **93.8% identifiable-answer recovery** with **70.4% accuracy**.
- **Positional Bias & Low Mass**: DeepSeek assigns the lowest unconditional candidate mass in the cohort (**0.444**), and exhibits substantial positional bias (normalized entropy **0.637**), frequently emitting leading newlines (`\n\nA. Process`, `\n\nA.\n`). Its forced-choice/generated agreement is **79.2%**.

### 3. Gemma 2 (2B and 9B): Scaling and Multi-Choice Dispersion
- **Gemma 2-2B** achieves **29.5% calibration accuracy** and normalized entropy of **0.501**, exhibiting severe alphabetical bias toward option A.
- **Gemma 2-9B** dramatically improves to **90.6% calibration accuracy**, with normalized entropy of **0.985** and payoff slope of **+0.1756**.
- Both checkpoints exhibit multi-choice list generation (`' A, B, and'`), demonstrating that format non-compliance in Gemma stems from list dispersion rather than conversational preambles.

---

## Continuation Taxonomy Breakdown

Across all 23,400 audited presentations, the refined deterministic classification yields:

| Continuation Category | Total Occurrences | Frequency (%) | Description & Implication |
| :--- | :---: | :---: | :--- |
| `strict_single_letter` | 7,844 | 33.52% | Strict single letter token matching exact instructions (with standard punctuation wrapper). |
| `letter_first_explanation` | 7,014 | 29.97% | Valid letter emitted first, followed by explanation (`A\n\nExplanation:`, `C\n\nExplan`). |
| `letter_first_option_echo` | 3,486 | 14.90% | Valid letter emitted first, followed by action snippet (`B. Synchronize your...`, `D\n\nChlor`). |
| `letter_first_other` | 2,701 | 11.54% | Valid letter emitted first, followed by whitespace, punctuation, or generic tokens. |
| `letter_first_question_echo` | 1,760 | 7.52% | Valid letter emitted first, followed by question repetition (`A\n\nWhich of the...`). |
| `ambiguous_multi_choice` | 378 | 1.62% | Multiple letters listed as conjunctions/disjunctions (`A, B, and`). |
| `preamble_without_letter` | 203 | 0.87% | Conversational preamble (`\n\nThe correct answer`) truncated before letter emission. |
| `unrelated_or_degenerate` | 12 | 0.05% | Markdown formatting headers (`### 1`) or degenerate tokens. |
| `preamble_with_letter` | 2 | 0.01% | Conversational phrase identifying letter (`The correct answer is A`). |
| `empty_or_whitespace` | 0 | 0.00% | Zero generated tokens or pure whitespace. |
| `unresolved_or_truncated` | 0 | 0.00% | Unclassified or truncated continuations. |

---

## Curated Representative Examples & Anomalies

The table below surfaces 26 curated examples illustrating distinct failure and compliance mechanisms across models.

| Model | Task | Category | Raw Generated Continuation | Extracted | Strict Valid | Truncated? | Forced Argmax / Correct | Uncond Mass | Scientific Interpretation |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `mistralai/Mistral-7B-v0.3` | calibration | `letter_first_explanation` | `'A\n\nExplan'` | **A** | False | True | True | 0.6496 | Model knows correct answer and emits it first, but strict parser rejects due to subsequent explanatory tokens. |
| `mistralai/Mistral-7B-v0.3` | behavioral | `letter_first_explanation` | `'A\n\nExplan'` | **A** | False | True | COOPERATE | 0.5972 | Model prefers COOPERATE strategy and emits corresponding letter, but appends newline and explanation prefix. |
| `mistralai/Mistral-7B-v0.3` | calibration | `preamble_without_letter` | `'\n\nThe correct answer'` | **None** | False | True | True | 0.5348 | Model emits '\n\nThe correct answer' but 5-token limit truncates generation before the letter token is reached. |
| `allenai/OLMo-2-1124-7B` | calibration | `letter_first_option_echo` | `' B\n\nChloroph'` | **B** | False | True | True | 0.8094 | Model generates option letter followed immediately by option text ('B. Synchronize...'), violating letter-only rule. |
| `ibm-granite/granite-3.3-2b-base` | behavioral | `letter_first_option_echo` | `' D. Route your sky'` | **D** | False | False | COOPERATE | 0.6131 | Granite prefixes continuation with '\n\n' followed by letter and option snippet ('\n\nC. Process'). |
| `HuggingFaceTB/SmolLM2-1.7B` | behavioral | `letter_first_question_echo` | `' A\n\nQuestion '` | **A** | False | False | COOPERATE | 0.6488 | Model generates letter followed by question prompt echo ('A\n\nWhich of the...'), treating decision token as sentence break. |
| `google/gemma-2-2b` | calibration | `ambiguous_multi_choice` | `'\n\nA.\nB'` | **None** | False | False | False | 0.4500 | Model lists multiple options (' A, B, and') without selecting a unique single answer letter. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' A'` | **A** | True | False | COOPERATE | 0.9593 | Model generates isolated single letter token exactly obeying harness instructions with 0.96+ candidate probability mass. |
| `meta-llama/Llama-3.2-3B` | calibration | `strict_single_letter` | `' A'` | **A** | True | False | True | 0.9286 | Clean single-letter output matching ground-truth factual letter with high unconditional next-token mass. |
| `deepseek-ai/deepseek-llm-7b-base` | behavioral | `strict_single_letter` | `'\n\nA.\n'` | **A** | True | False | COOPERATE | 0.3458 | Model assigns under 35% probability mass to the option tokens {A,B,C,D}, showing weak adherence to the multiple-choice format. |
| `mistralai/Mistral-7B-v0.3` | behavioral | `unrelated_or_degenerate` | `'\n\n### "Get'` | **None** | False | True | DISENGAGE | 0.5417 | Model emits markdown formatting ('\n\n### "Get') rather than entering question response mode. |
| `microsoft/phi-2` | calibration | `preamble_with_letter` | `' The correct answer is A'` | **A** | False | False | False | 0.4989 | Model emits full phrase 'The correct answer is A', identifiable to human auditors but rejected by single-token letter parser. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' C'` | **C** | True | False | COOPERATE | 0.9753 | B and C share identical top FP16 logits (22.25). Python max() on cond_probs breaks ties by alphabetical key 'B', whereas greedy generate() breaks ties by vocabulary ID order (token 356 ' C' before token 425 ' B'). |
| `ibm-granite/granite-3.3-2b-base` | behavioral | `letter_first_option_echo` | `'\n\nA. Reser'` | **A** | False | True | COOPERATE | 0.4516 | Under unconstrained decoding, newline token '\n' wins global argmax, and the subsequent line begins with letter 'A', whereas constrained candidate scoring evaluates only {A,B,C,D} at token position 0 where 'B' was slightly higher. |
| `mistralai/Mistral-7B-v0.3` | calibration | `letter_first_option_echo` | `'A\n\nChlor'` | **A** | False | True | True | 0.6871 | Model emits 'D\n\nChlor'. The refined parser recognizes 'D' as the isolated option letter and 'Chlor' as the action echo prefix, avoiding false multi-choice ambiguity. |
| `Qwen/Qwen2.5-1.5B` | behavioral | `letter_first_question_echo` | `' A\n\nWhich of the'` | **A** | False | True | COOPERATE | 0.9875 | Characteristic continuation for Qwen/Qwen2.5-1.5B (Category: letter_first_question_echo). |
| `Qwen/Qwen2.5-7B` | behavioral | `letter_first_question_echo` | `' B\n\nWhich of the'` | **B** | False | True | COOPERATE | 0.9683 | Characteristic continuation for Qwen/Qwen2.5-7B (Category: letter_first_question_echo). |
| `google/gemma-2-9b` | behavioral | `letter_first_other` | `' A\n\nYou are a'` | **A** | False | False | COOPERATE | 0.7402 | Characteristic continuation for google/gemma-2-9b (Category: letter_first_other). |
| `tiiuae/Falcon3-3B-Base` | behavioral | `letter_first_explanation` | `' A\n\nExplanation:'` | **A** | False | True | COOPERATE | 0.6773 | Characteristic continuation for tiiuae/Falcon3-3B-Base (Category: letter_first_explanation). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Mercury'` | **D** | False | False | True | 0.9763 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' C. Mercury'` | **C** | False | False | True | 0.9680 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Mercury'` | **B** | False | False | True | 0.9541 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Oxygen'` | **B** | False | False | True | 0.9785 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Chlorophyll'` | **B** | False | False | True | 0.9828 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Chlorophyll'` | **D** | False | False | True | 0.9783 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Honeybee'` | **D** | False | False | True | 0.9921 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |

---

## Methodological Appendix & Recommendations

1. **Decouple format compliance from content tracking**: Constrained log-probability scoring and open-ended generation evaluate orthogonal capabilities. Format failure does not indicate lack of factual knowledge or strategic representations.
2. **Report unconditional candidate mass as standard pre-flight diagnostic**: Models with $\sum P(t) < 0.50$ (such as DeepSeek 7B) require different decoding or prompt formatting than models with mass >0.95 (Qwen, Llama).
3. **Token budget awareness**: The 5-token generation budget correctly captured answers for letter-first continuations (`A\n\nExplan`), but truncated conversational preambles (`\n\nThe correct answer is...`). Future free-generation audits should allocate 15–20 tokens.
4. **Preserve strict metrics while reporting identifiable recovery**: While scientific reports should record strict validity for protocol reproducibility, analyses of underlying competence should report identifiable-answer recovery alongside conditional accuracy denominators.
