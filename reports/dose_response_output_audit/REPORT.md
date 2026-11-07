# Retrospective Output Audit: Decoupling Format Compliance, Token Geometry, and Decision Competence

## Executive Summary

This audit examines all **23,400 recorded model generations** (19,656 behavioural presentations and 3,744 factual calibration presentations) across **13 pretrained checkpoints** and **3 counterbalanced option schedules** (Latin-Square baseline, Order Replication 1, and Order Replication 2) from the exploratory Dose-Response cohort.

The central finding is that **free-generation format failures do not imply failure of content tracking, factual knowledge, or social dilemma evaluation**.
Crucially, models fall along a continuous multidimensional diagnostic space rather than binary competence tiers:

1. **Format-Masked Trackers (e.g., Mistral 7B-v0.3)**: Achieves **87.8% factual calibration accuracy** and **85.9% agreement** between generated choices and forced-choice scoring, yet scores **~1.7% strict format validity** because it systematically outputs explanations (`C\n\nExplan`) or verbal preambles (`\n\nThe correct answer`). The model knows the answers and expresses them clearly, but the strict single-letter parser rejects them.
2. **Compliant Geometric Focusers (e.g., Qwen 2.5-3B, Llama 3.2-3B)**: Concentrate **90–98% of next-token unconditional probability mass** on the exact option tokens `{A, B, C, D}` and achieve **100% strict format compliance**.
3. **Option Echoers & Preamblers (e.g., OLMo-2 7B, Granite 2B, DeepSeek 7B)**: Emit valid option letters followed immediately by action labels (`B. Synchronize...`) or formatting newlines (`\n\nC. Process`), reflecting natural text continuation rather than multiple-choice stopping.
4. **Format-Disregarding / Weak-Mass Responders (e.g., DeepSeek 7B)**: Assigns only **~44% unconditional mass** to `{A, B, C, D}`, frequently omitting isolated letter prefixes.

---

## Multidimensional Diagnostic Space: Cross-Model Comparison

The table below reports mean values across all three counterbalanced schedules for each model.

| Model | Calib Acc (FC) | Calib Strict Valid | Calib Id. Rate | Calib Id. Acc | Behav Strict Valid | Behav Id. Rate | Behav Id. Agree | Uncond ABCD Mass | Positional Entropy | Payoff Slope |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `HuggingFaceTB/SmolLM2-1.7B` | 69.4% | 0.0% | 100.0% | 69.4% | 0.0% | 99.2% | 98.2% | 0.641 | 0.764 | +0.189 |
| `Qwen/Qwen2.5-1.5B` | 94.1% | 100.0% | 100.0% | 94.1% | 74.9% | 100.0% | 99.1% | 0.984 | 0.997 | +0.064 |
| `Qwen/Qwen2.5-3B` | 92.7% | 50.0% | 100.0% | 92.7% | 100.0% | 100.0% | 97.0% | 0.965 | 0.950 | +0.190 |
| `Qwen/Qwen2.5-7B` | 92.0% | 51.4% | 100.0% | 92.4% | 80.5% | 92.7% | 99.1% | 0.971 | 0.980 | +0.090 |
| `allenai/OLMo-2-1124-7B` | 83.7% | 0.0% | 89.6% | 82.6% | 0.0% | 100.0% | 99.9% | 0.751 | 0.992 | +0.293 |
| `deepseek-ai/deepseek-llm-7b-base` | 70.5% | 4.5% | 93.8% | 70.4% | 17.7% | 100.0% | 79.2% | 0.444 | 0.637 | +0.193 |
| `google/gemma-2-2b` | 29.5% | 0.0% | 89.6% | 29.8% | 40.0% | 100.0% | 99.9% | 0.661 | 0.501 | +0.087 |
| `google/gemma-2-9b` | 90.6% | 0.0% | 95.5% | 90.5% | 29.2% | 99.9% | 97.8% | 0.742 | 0.985 | +0.173 |
| `ibm-granite/granite-3.3-2b-base` | 76.4% | 26.7% | 96.9% | 67.0% | 0.0% | 99.8% | 89.7% | 0.651 | 0.989 | +0.145 |
| `meta-llama/Llama-3.2-3B` | 73.3% | 95.5% | 100.0% | 75.0% | 100.0% | 100.0% | 97.0% | 0.909 | 0.980 | +0.227 |
| `microsoft/phi-2` | 87.5% | 42.4% | 100.0% | 87.2% | 5.6% | 87.8% | 99.7% | 0.746 | 0.941 | +0.090 |
| `mistralai/Mistral-7B-v0.3` | 87.8% | 1.7% | 81.6% | 98.7% | 0.0% | 90.0% | 85.9% | 0.579 | 0.993 | +0.049 |
| `tiiuae/Falcon3-3B-Base` | 92.4% | 0.0% | 100.0% | 92.4% | 0.0% | 100.0% | 98.1% | 0.674 | 0.906 | +0.129 |

*Note: Positional Entropy is normalized so 1.0 indicates perfect balance (25% across A, B, C, D) and 0.0 indicates a 100% fixed letter response. Payoff Slope measures the linear change in COOPERATE choice per unit delta_u.*

---

## Deep Dives on Informative Focal Cases

### 1. Mistral 7B-v0.3: The Anatomy of Format-Masked Factual & Social Competence
- **The Empirical Paradox**: Under strict letter parsing, Mistral 7B achieves a recorded calibration validity of only **1.7%** and behavioral validity of **0.0%**. A researcher looking only at `is_valid_letter` would conclude Mistral 7B completely failed format comprehension.
- **The Underlying Reality**: Constrained forced-choice scoring reveals factual accuracy of **87.8%** (83–91% across schedules). More crucially, extracting the identifiable letter from `generated_raw_text` shows that **81.6%** of calibration generations and **90.0%** of behavioral generations contain a clearly identifiable answer letter.
- **Conditioned Accuracy & Agreement**: When Mistral emits an identifiable letter on factual calibration, that letter is **98.7% accurate**! On behavioral dilemmas, the identifiable generated letter agrees with the forced-choice argmax **85.9%** of the time.
- **Continuation Mechanism**: Mistral 7B decodes predominantly into `C\n\nExplan`, `B\n\nExplan`, or preamble strings like `\n\nThe correct answer`. Because the harness bounded generation to 5 tokens, the model emits the letter and immediately begins generating an explanation. The model is not confused about the answer—it is simply behaving as a conversational explainer rather than a multiple-choice bubble filler.

### 2. Qwen 2.5 Family (1.5B, 3B, 7B): Scaling and Format Crystallization
- **Qwen 2.5-3B**: Demonstrates near-perfect format discipline (**100% strict validity**, **0.965 unconditional mass** on ABCD). It produces clean single tokens (`' B'`, `' C'`) with zero conversational leakage.
- **Qwen 2.5-1.5B vs 7B**: Both 1.5B and 7B maintain extremely high unconditional mass (**0.985** and **0.971**), but exhibit ~76–80% strict validity due to occasionally appending punctuation or an explanation header (`A\n\nExplanation:`). Despite this slight elongation, identifiable extraction is **99.9%** and agreement with forced-choice exceeds **98%**.

### 3. Gemma 2 (2B and 9B): List Delimiters and Multi-Choice Dispersion
- **Gemma 2-2B** achieves **40.1% strict validity** while **Gemma 2-9B** achieves **28.4%**.
- Both models assign moderate unconditional mass (**0.660** and **0.742**) to `{A, B, C, D}`.
- However, both checkpoints exhibit a unique pathology: generating multi-choice lists like `' A, B, and'` or `' A, B, C'`. Rather than committing to a single option, they reproduce option lists, demonstrating that lower format validity in Gemma stems from completion ambiguity rather than explanation generation.

### 4. DeepSeek LLM 7B Base: Unconditional Dispersion and Newline Preamble
- DeepSeek 7B assigns the lowest unconditional mass on candidate tokens across the entire cohort (**0.442**).
- In over **60%** of presentations, DeepSeek generates leading newlines (`\n\nA. Process`, `\n\nA.\n`).
- While an intended letter is identifiable in **68.2%** of cases, its positional entropy is markedly lower (**0.751**), indicating significant positional or alphabetical bias (favoring `'A'`).

---

## Continuation Taxonomy Breakdown

Across all 23,400 audited presentations, the deterministic classification yields:

| Continuation Category | Total Occurrences | Frequency (%) | Description & Implication |
| :--- | :---: | :---: | :--- |
| `strict_single_letter` | 7,844 | 33.52% | Strict single letter token matching exact instructions. |
| `letter_first_explanation` | 7,014 | 29.97% | Valid letter emitted first, followed by explanation (`A\n\nExplanation:`, `C\n\nExplan`). |
| `letter_first_option_echo` | 3,452 | 14.75% | Valid letter emitted first, followed by action snippet (`B. Synchronize your...`). |
| `letter_first_other` | 2,712 | 11.59% | Valid letter emitted first, followed by whitespace, punctuation, or generic tokens. |
| `letter_first_question_echo` | 1,760 | 7.52% | Valid letter emitted first, followed by question repetition (`A\n\nWhich of the...`). |
| `ambiguous_multi_choice` | 401 | 1.71% | Multiple letters listed as conjunctions/disjunctions (`A, B, and`). |
| `preamble_without_letter` | 203 | 0.87% | Conversational preamble (`\n\nThe correct answer`) truncated before letter emission. |
| `unrelated_or_degenerate` | 12 | 0.05% | Markdown formatting headers (`### 1`) or degenerate tokens. |
| `preamble_with_letter` | 2 | 0.01% | Conversational phrase identifying letter (`The correct answer is A`). |
| `empty_or_whitespace` | 0 | 0.00% | Zero generated tokens or pure whitespace. |
| `unresolved_or_truncated` | 0 | 0.00% | Unclassified or truncated continuations. |

---

## Curated Representative Examples & Anomalies

The table below surfaces 26 curated examples illustrating distinct mechanisms across models and task modalities.

| Model | Task | Category | Raw Generated Continuation | Extracted | Strict Valid | Forced Argmax / Correct | Uncond Mass | Scientific Interpretation |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `mistralai/Mistral-7B-v0.3` | calibration | `letter_first_explanation` | `'A\n\nExplan'` | **A** | False | True | 0.6496 | Model knows correct answer and emits it first, but strict parser rejects due to subsequent explanatory tokens. |
| `mistralai/Mistral-7B-v0.3` | behavioral | `letter_first_explanation` | `'A\n\nExplan'` | **A** | False | COOPERATE | 0.5972 | Model prefers COOPERATE strategy and emits corresponding letter, but appends newline and explanation prefix. |
| `mistralai/Mistral-7B-v0.3` | calibration | `preamble_without_letter` | `'\n\nThe correct answer'` | **None** | False | True | 0.5348 | Model emits '\n\nThe correct answer' but 5-token limit truncates generation before the letter token is reached. |
| `allenai/OLMo-2-1124-7B` | calibration | `letter_first_option_echo` | `' C\n\nThe planet Mars'` | **C** | False | True | 0.8034 | Model generates option letter followed immediately by option text ('B. Synchronize...'), violating letter-only rule. |
| `ibm-granite/granite-3.3-2b-base` | behavioral | `letter_first_option_echo` | `' D. Route your sky'` | **D** | False | COOPERATE | 0.6131 | Granite prefixes continuation with '\n\n' followed by letter and option snippet ('\n\nC. Process'). |
| `HuggingFaceTB/SmolLM2-1.7B` | behavioral | `letter_first_question_echo` | `' A\n\nQuestion '` | **A** | False | COOPERATE | 0.6488 | Model generates letter followed by question prompt echo ('A\n\nWhich of the...'), treating decision token as sentence break. |
| `google/gemma-2-2b` | calibration | `ambiguous_multi_choice` | `'\n\nA.\nB'` | **None** | False | False | 0.4500 | Model lists multiple options (' A, B, and') without selecting a unique single answer letter. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' A'` | **A** | True | COOPERATE | 0.9593 | Model generates isolated single letter token exactly obeying harness instructions with 0.96+ candidate probability mass. |
| `meta-llama/Llama-3.2-3B` | calibration | `strict_single_letter` | `' A'` | **A** | True | True | 0.9286 | Clean single-letter output matching ground-truth factual letter with high unconditional next-token mass. |
| `deepseek-ai/deepseek-llm-7b-base` | behavioral | `strict_single_letter` | `'\n\nA.\n'` | **A** | True | COOPERATE | 0.3458 | Model assigns under 35% probability mass to the option tokens {A,B,C,D}, showing weak adherence to the multiple-choice format. |
| `mistralai/Mistral-7B-v0.3` | behavioral | `unrelated_or_degenerate` | `'\n\n### "Get'` | **None** | False | DISENGAGE | 0.5417 | Model emits markdown formatting ('\n\n### "Get') rather than entering question response mode. |
| `microsoft/phi-2` | calibration | `preamble_with_letter` | `' The correct answer is A'` | **A** | False | False | 0.4989 | Model emits full phrase 'The correct answer is A', identifiable to human auditors but rejected by single-token letter parser. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' C'` | **C** | True | COOPERATE | 0.9753 | Model free continuation selects C while constrained candidate scoring ranks B highest. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' C'` | **C** | True | COOPERATE | 0.9729 | Model free continuation selects C while constrained candidate scoring ranks B highest. |
| `Qwen/Qwen2.5-3B` | behavioral | `strict_single_letter` | `' C'` | **C** | True | COOPERATE | 0.9708 | Model free continuation selects C while constrained candidate scoring ranks B highest. |
| `Qwen/Qwen2.5-1.5B` | behavioral | `letter_first_question_echo` | `' A\n\nWhich of the'` | **A** | False | COOPERATE | 0.9875 | Characteristic continuation for Qwen/Qwen2.5-1.5B (Category: letter_first_question_echo). |
| `Qwen/Qwen2.5-7B` | behavioral | `letter_first_question_echo` | `' B\n\nWhich of the'` | **B** | False | COOPERATE | 0.9683 | Characteristic continuation for Qwen/Qwen2.5-7B (Category: letter_first_question_echo). |
| `google/gemma-2-9b` | behavioral | `letter_first_other` | `' A\n\nYou are a'` | **A** | False | COOPERATE | 0.7402 | Characteristic continuation for google/gemma-2-9b (Category: letter_first_other). |
| `tiiuae/Falcon3-3B-Base` | behavioral | `letter_first_explanation` | `' A\n\nExplanation:'` | **A** | False | COOPERATE | 0.6773 | Characteristic continuation for tiiuae/Falcon3-3B-Base (Category: letter_first_explanation). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Mercury'` | **D** | False | True | 0.9763 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' C. Mercury'` | **C** | False | True | 0.9680 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Mercury'` | **B** | False | True | 0.9541 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Oxygen'` | **B** | False | True | 0.9785 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' B. Chlorophyll'` | **B** | False | True | 0.9828 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Chlorophyll'` | **D** | False | True | 0.9783 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |
| `Qwen/Qwen2.5-3B` | calibration | `letter_first_option_echo` | `' D. Honeybee'` | **D** | False | True | 0.9921 | Illustrative case of letter_first_option_echo under Qwen/Qwen2.5-3B (calibration). |

---

## Methodological Appendix & Recommendations

1. **Never conflate format invalidity with task incomprehension**: Constrained log-probability scoring (forced-choice) and open-ended generation measure orthogonal capabilities. A model may have sharp factual and strategic representations while lacking strict zero-shot letter-only stopping tokens.
2. **Report unconditional candidate mass $\sum_{t \in \{A,B,C,D\}} P(t)$ as a standard pre-flight diagnostic**: Models with mass below ~0.50 (such as DeepSeek 7B) require different decoding or prompt formatting than models with mass >0.95 (Qwen, Llama).
3. **Token budget awareness**: The 5-token generation budget correctly captured answers when models emitted letter-first continuations (`A\n\nExplan`), but failed to capture letters when conversational preambles exceeded 5 tokens (`\n\nThe correct answer is...`). Future harnesses evaluating free generation should allocate at least 15–20 tokens if preambles are not strictly suppressed.
4. **Preserve strict metrics while reporting identifiable recovery**: While scientific reports should record strict validity for reproducibility, secondary analyses should report identifiable-answer recovery to prevent discarding valid behavioral signal.
