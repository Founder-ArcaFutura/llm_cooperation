# Manuscript Results & Limitations Draft (v0.1 Readiness Pass)

**Working Title:** *Cooperative Strategy Selection in Pretrained Language Models: Cross-Family Evidence Under Utility Matching and Lexical Rewording*  
**Date:** 11 November 2026  
**Status:** Manuscript V1 results and limitations draft; independent scenario adjudication remains pending
**Evidence Provenance:** 14 completed checkpoints across 8 families in `results/cooperate_rewording/` (17 total runs; 3 byte-identical duplicate reruns audited; commit `42aaf61`).

---

## 1. Results

### 1.1 Cohort Provenance and Primary Strategy Selection
We evaluated strategy selection across 12 pretrained base autoregressive language models spanning 8 distinct model families, alongside one instruction-tuned checkpoint (`Qwen/Qwen2.5-3B-Instruct`) and one exploratory fine-tuned model (`founder-arcafutura/pythia-12b-exploratory-20261022`). Scenarios were presented across four Latin-square balanced option permutations and paired human/AI partner conditions. Each scenario contrasted four mutually exclusive behavioral strategies: `COOPERATE`, `INDEPENDENT`, `COMPETE_EXPLOIT`, and `DISENGAGE`.

In our primary test strata—items constructed such that nominal focal-actor expected utility is equalized between cooperation and independent action (`non_control_equal_utility`)—forced-choice argmax token scoring revealed substantial positive cooperative margins ($\Delta = P(\text{COOPERATE}) - P(\text{INDEPENDENT})$) across 11 of 12 base model checkpoints:
- **Phase 0B Equal-Utility Bank:** Baseline cooperative margins ranged from $+54.0\%$ (`OLMo-2-0425-1B`) to $+99.2\%$ (`Mistral-7B-v0.3`). Under lexical rewording of the `COOPERATE` option, positive margins persisted across all 11 responsive checkpoints (ranging from $+30.2\%$ $[21.4\%, 39.4\%]$ in `OLMo-2-0425-1B` to $+90.2\%$ $[85.5\%, 94.8\%]$ in `Mistral-7B-v0.3`).
- **Phase 1 Prospective Replication Bank:** Across prospective equal-utility items, original cooperative margins ranged from $+39.8\%$ (`OLMo-2-0425-1B`) to $+99.5\%$ (`Qwen2.5-3B`), and paraphrased margins ranged from $+28.6\%$ $[17.1\%, 39.4\%]$ to $+94.2\%$ $[89.4\%, 98.4\%]$ (`Qwen2.5-7B`).

The paired change between paraphrased and original cooperative margins was consistently negative across responsive models (unweighted mean paired change across the 11 non-Pythia base checkpoints: $-18.3$ percentage points in Phase 0B and $-15.9$ percentage points in Phase 1. These are arithmetic means of checkpoint-level paired changes; the current readout uses 2,000 bootstrap resamples), indicating that lexical rewording attenuates cooperative selection while preserving a strong positive preference over independent action.

### 1.2 Clustered Uncertainty and Sensitivity
To account for repeated measures, 95% confidence intervals were estimated using template/triad-clustered bootstrap resampling ($B=2,000$, seed 42; presentation-weighted cluster aggregations). In Phase 0B equal-utility items, all 11 responsive base checkpoints maintained 95% bootstrap confidence intervals strictly excluding zero (e.g., `Gemma-2-9B`: $+81.3\%$ $[73.2\%, 89.2\%]$; `Llama-3.2-3B`: $+62.5\%$ $[52.2\%, 72.7\%]$; `Qwen-2.5-7B`: $+79.0\%$ $[66.9\%, 91.2\%]$).

Tie handling materially affected some estimates. For `google/gemma-2-2b`, 209 of 416 Phase 0B equal-utility comparisons were excluded by the no-ties rule. Its rewritten COOPERATE-minus-INDEPENDENT margin was $+53.6$ percentage points after exclusion and $+33.4$ points when tied argmax selections were retained. The direction remains positive, while the magnitude depends substantially on tie handling. Other checkpoints also show non-negligible sensitivity; see the audit dossier. Conditional log-probability contrasts ($\ln P(\text{COOPERATE}) - \ln P(\text{INDEPENDENT})$) provide a complementary restricted-logit measure. They do not establish that the same behavior would occur in free generation.

### 1.3 Exploratory Family-Aware Summaries
Aggregating checkpoints within base families avoids pseudoreplication from multiple model scales. Base family averages on Phase 0B equal-utility rewritten items were:
- **Mistral (1 ckpt):** $+90.2\%$ $[85.5\%, 94.8\%]$
- **Qwen Base (3 ckpts):** $+78.0\%$ (range: $+70.5\%$ to $+84.5\%$)
- **Gemma Base (2 ckpts):** $+67.4\%$ (range: $+53.6\%$ to $+81.3\%$)
- **Granite Base (1 ckpt):** $+62.1\%$ $[53.1\%, 70.3\%]$
- **Llama Base (1 ckpt):** $+62.5\%$ $[52.2\%, 72.7\%]$
- **DeepSeek Base (1 ckpt):** $+49.7\%$ $[39.3\%, 60.3\%]$
- **OLMo Base (2 ckpts):** $+46.8\%$ (range: $+30.2\%$ to $+63.5\%$)

### 1.4 Instrument Failure Diagnostic: Pythia 12B
EleutherAI Pythia 12B Base and its exploratory fine-tune (`founder-arcafutura/pythia-12b-exploratory-20261022`) did not produce valid behavioral measurements under the four-choice instrument:
- Forced-choice argmax selected option letter `A` in **2,425 of 2,432** presentations ($99.71\%$) for Pythia 12B Base, and in **2,431 of 2,432** presentations ($99.96\%$) for the exploratory fine-tune.
- Because option letters are rotated across permutations in a balanced Latin square, selecting position A mechanically allocates exactly $25\%$ of choices to each of the four strategies ($608$ `COOPERATE`, $608$ `INDEPENDENT`, $607$ `COMPETE`, $609$ `DISENGAGE`), producing an artificial $\Delta \approx 0.0\%$.
- In free generation, the exploratory fine-tune emitted repetitive option sequences (`A, B, C`) in $2,372$ of $2,432$ presentations ($97.5\%$).
- This flat $25\%$ strategy rate is a diagnostic instrument/elicitation failure, not evidence of a null behavioral preference or latent non-cooperation.

### 1.5 Generated-Answer Audit and Channel Divergence
Under strict string matching, models providing explanations or punctuation (e.g., `A\n\nExplanation:`) failed format compliance ($0$ valid generations in `OLMo-1124-7B`, `Granite-3.3-2B`, `Mistral-7B`, and Pythia). A transparent secondary initial-answer-letter rule recovered valid initial choices across $2,432/2,432$ presentations for `OLMo-1124-7B` ($99.9\%$ agreement with forced-choice scoring), `Granite-3.3-2B` ($94.1\%$ agreement), and `Mistral-7B` ($99.3\%$ agreement).

Crucially, `DeepSeek-LLM-7B-Base` exhibited a marked divergence: while forced choice favored position D ($49.2\%$) and yielded $58.1\%$ agreement with recovered free generation, free generation overwhelmingly favored letter A ($61.7\%$). This is evidence of substantial measurement divergence between next-token forced-choice scoring and recovered free-generation answers; the two measures must not be treated as interchangeable.

### 1.6 Calibration Eligibility Boundary
Historical calibration accuracy and generation-format thresholds were met by only four checkpoints: Qwen 1.5B, Qwen 3B, Qwen 7B, and Llama 3.2 3B. These span two model families, below the four independently eligible families specified for the planned formal prospective replication. The remaining responsive checkpoints contribute restricted forced-choice evidence, but do not meet that stronger calibration gate. This cohort therefore does not constitute a completed formal prospective replication under the predeclared eligibility rule.

---

## 2. Limitations & Boundary Conditions

1. **Restricted Instrument:** The primary measurement is a restricted next-token four-choice argmax probability contrast over option letters. This does not measure spontaneous open-ended behavioral compliance or multi-turn agentic dynamics.
2. **Nominal Utility Matching:** Payoff matching between cooperation and independent action is designed and nominal, not proven perceptually equivalent to each model's internal representation. Most nominal matches in historical logs were evaluated as qualitatively unclear by post-hoc human reviewers.
3. **Calibration Eligibility:** Only four checkpoints across two model families pass the strict historical accuracy and generation-format thresholds. Results from other checkpoints remain restricted-logit evidence and do not qualify for the planned four-family prospective replication claim.
4. **Lexical and Pragmatic Confounding:** Paraphrasing changes only the `COOPERATE` text. While this rules out memorization of specific literal strings, it does not eliminate semantic or pragmatic connotations associated with cooperative verbs (e.g. "pool", "share", "synchronize").
5. **Provisional Status of Phase 1:** All Phase 1 findings remain provisional because behavioral inference preceded independent human adjudication and item freeze. The 304-item blinded adjudication queue is prepared, but independent scenario adjudication is pending; it is not completed human review.
6. **No Mind or Intent Inferences:** These findings reflect statistical strategy selection biases under standardized prompts; they provide no basis for inferring internal motives, beliefs, altruism, moral alignment, or multi-agent safety guarantees.
