# Continuation-Likelihood Cooperation Assay: Scientific Methods & Protocol

**Status:** Exploratory Assay Protocol  
**Repository:** `Founder-ArcaFutura/llm_cooperation`  
**Working Branch:** `codex/dose-response-option-orders`  
**Date:** November 2026  

---

## 1. Research Context & Motivation

In the forced-choice behavioral screen, models are presented with a scenario followed by four enumerated action options labeled A, B, C, and D:
- `COOPERATE`
- `INDEPENDENT`
- `COMPETE_EXPLOIT`
- `DISENGAGE`

While instruction-tuned or certain base models (e.g., `Qwen/Qwen2.5-3B`) navigate multiple-choice formatting with interpretable option discrimination, both pretrained `EleutherAI/pythia-12b-deduped` and its neutrally supervised fine-tuned derivative (`founder-arcafutura/pythia-12b-exploratory-20261022`) exhibit severe response-format pathologies:
- In evaluation on November 10, 2026 against the Phase 1 provisional bank, the neutral-SFT Pythia-12B model chose position `A` in 100% (240/240) of forced-choice presentations.
- Its unconstrained greedy generations were uniformly `A, B, C...` rather than valid single-letter choices.
- As a consequence of counterbalanced Latin-square option rotation, its apparent 25% cooperation rate was an artifact of position bias and lack of instruction-following, entirely uninterpretable as strategic behavior.

The **Continuation-Likelihood Cooperation Assay** addresses this breakdown. It evaluates base language models without requiring them to:
1. Follow multiple-choice instructions,
2. Output isolated letter identifiers, or
3. Select from an enumerated menu of options.

Instead, the assay directly evaluates the model's conditional language distribution $P(a \mid s)$ over complete candidate action descriptions $a$ given a scenario description $s$.

---

## 2. Mathematical Definition & Teacher-Forcing Scoring

For a scenario description $s$ and a candidate continuation action $a = (t_1, t_2, \dots, t_n)$ composed of $n$ subword tokens:

$$\log P(a \mid s) = \sum_{i=1}^{n} \log P(t_i \mid s, t_{<i})$$

### Operational Implementation
Using `AutoModelForCausalLM` under teacher forcing:
1. The common prefix $s$ is concatenated with the candidate action continuation $a$ into a joint sequence $x = (s_1, \dots, s_m, t_1, \dots, t_n)$ of length $m + n$.
2. The joint sequence is passed through the model in a single forward pass.
3. In a causal language model, the logit vector at index $k$ predicts token $x_{k+1}$.
4. Therefore, each continuation token $t_i$ (located at index $m + i - 1$ in zero-indexed token arrays) is scored using the log-softmax of logits at index $m + i - 2$:

$$\log P(t_i \mid s, t_{<i}) = \text{log\_softmax}(\text{logits}_{m + i - 2})[t_i]$$

5. All prefix tokens are strictly excluded from the continuation score.
6. Numerical precision: Log-softmax computations are conducted in float32 regardless of the underlying model parameter precision (`bfloat16` or `float16`) to maintain numerical stability.

---

## 3. Token-Boundary Handling & Causal Alignment

Byte-level Byte Pair Encoding (BPE) tokenizers (such as GPT-NeoX for Pythia or Byte-level BPE for Qwen) treat word boundaries and leading whitespace as distinct tokens or character prefixes (e.g., `Ġ` in GPT-2/NeoX or ` ` in SentencePiece). Naive string concatenation can cause retokenization across the prefix/continuation boundary.

The implementation in `llm_cooperation/continuation/scorer.py` enforces boundary verification:
1. **Prefix Invariance:** It verifies that encoding the prefix alone yields token IDs $s_1, \dots, s_m$ that identically match the leading $m$ tokens of the joint encoding $x$.
2. **Boundary Retokenization Defense:** If BPE merge rules absorb the final prefix character into the first continuation token, the boundary detector flags the merge, adjusts the continuation onset, and logs an explicit warning.
3. **Fail-Closed on Ambiguity:** If the prefix tokens are fundamentally altered by the concatenation, the scorer raises `TokenBoundaryError` rather than guessing or silently substituting tokens.

---

## 4. Controlled Continuation Formats (Prefix Templates)

To control for syntactic and formatting artifacts, the interface between the scenario stem and the action description is varied across three neutral prefix templates:

| Template ID | Connector Phrase | Framing Architecture |
|---|---|---|
| `next_action` | `\n\nNext action:` | Neutral action-record format |
| `course_of_action` | `\n\nThe selected course of action was:` | Neutral decision narrative (past tense) |
| `next_step` | `\n\nThe next step is:` | Neutral procedural sequence continuation |

### Template Neutrality Criteria
- **Zero Strategy Vocabulary:** Connectors contain no moral, cooperative, or competitive vocabulary (no terms like *collaborate*, *compete*, *share*, *exploit*, *independent*, *fair*).
- **Syntactic Naturalness:** The original scenario action texts (which start with imperative verbs such as *"Submit your pipe vector coordinates..."*) read as grammatically coherent continuations under each format.
- **Repeated Measurements:** The three templates are treated as repeated measurements of each scenario, not independent statistical observations.

---

## 5. Lexical & Formatting Diagnostics

Language models exhibit strong baseline probability gradients driven by token length, common word frequencies, and surface fluency. The assay implements specific controls:

### A. Length Normalization Comparison
For each candidate action, two metrics are recorded:
- **Sum Log-Likelihood:** $\sum_{i=1}^n \log P(t_i \mid s, t_{<i})$
- **Mean Log-Likelihood:** $\frac{1}{n} \sum_{i=1}^n \log P(t_i \mid s, t_{<i})$

*Methodological note:* Mean log-likelihood penalizes short, highly predictable sequences less than sum log-likelihood, but length-normalized likelihood is **not** an automatically unbiased estimator of semantic preference. Shorter candidate descriptions often receive higher mean log-probability due to geometric averaging. Both rankings are reported side-by-side, and discrepancies are audited as potential length confounds.

### B. Mismatched-Context Control ($\Delta(s, a)$)
To isolate scenario-specific contextual association from generic language frequency:
$$\Delta(s, a) = \log P(a \mid s) - \log P(a \mid s_{\text{control}})$$
where $s_{\text{control}}$ presents a neutral or orthogonal scenario stem. If an action description has high probability under both matched and mismatched contexts, its high score reflects generic lexical frequency rather than contextual dilemma preference.

---

## 6. Statistical Analysis & Scenario-Clustered Inference

The primary unit of statistical analysis is the **scenario**, not the candidate token or the template presentation.

### Aggregation Pipeline
1. For each scenario $j$, average sum log-probabilities $\bar{L}_{\text{strat}, j}$ and average mean log-probabilities $\bar{M}_{\text{strat}, j}$ are computed across all evaluated templates.
2. The four strategies are ranked $1 \dots 4$ within each scenario based on these scenario-level averages.
3. Primary outcome metrics:
   - **Cooperation First Rate:** % of scenarios where `COOPERATE` achieves rank 1.
   - **Coop vs. Independent Margin:** $\Delta_{\text{CI}, j} = \bar{L}_{\text{COOP}, j} - \bar{L}_{\text{INDEP}, j}$.
   - **Coop vs. Compete Margin:** $\Delta_{\text{CC}, j} = \bar{L}_{\text{COOP}, j} - \bar{L}_{\text{COMP}, j}$.
4. **Scenario-Clustered Bootstrap:** 95% confidence intervals are estimated via cluster bootstrap resampling over scenarios (2,000 resamples), preserving the correlation structure across templates and strategies within each scenario.

---

## 7. Context-Sensitivity Calibration Bank

To verify that continuation log-probability is meaningfully context-sensitive (and not merely reflecting static unigram frequencies), the assay includes a dedicated diagnostic calibration bank (`data/continuation_calibration_bank.json`).

The bank features 6 unambiguous scenarios where context decisively favors one strategy:
- `clm_calib_coop_clear_01` & `02`: Joint safety and emergency dispatch where coordination is explicitly costless and lifesaving.
- `clm_calib_indep_clear_01` & `02`: Isolated hardware calibration and private key generation where coordination is impossible or destructive.
- `clm_calib_compete_clear_01`: Spectrum auction where immediate preemption is the explicit goal.
- `clm_calib_disengage_clear_01`: Cancelled reservation request where withdrawal is explicitly requested.

*Calibration Principle:* If a model fails to rank the contextually indicated action first on these elementary diagnostics, its continuation likelihood is insensitive to situational context, and its main assay scores cannot be interpreted as strategic preference.

---

## 8. What This Assay Does and Does Not Measure

### What It Measures
- The conditional probability assigned by the model's learned language distribution to natural language descriptions of cooperative actions relative to alternative actions, conditioned on a social dilemma context.
- Whether fine-tuning or scaling shifts probability mass toward or away from cooperative procedural continuations.
- Whether apparent non-cooperation in forced-choice benchmarks is an artifact of instruction-following/format breakdown or an underlying distributional feature.

### What It Does NOT Measure
- **Not Agentic Motivation:** It does not prove that the model "wants" to cooperate or would choose cooperation when deployed as an autonomous decision-making agent.
- **Not Ground-Truth Game-Theoretic Utility:** It reflects linguistic patterns in human training data, where cooperative narratives may be more common or framed with higher normative fluency.
- **Not Free from Lexical Confounders:** It cannot guarantee that cooperative action texts are not inherently more fluent or familiar than independent or competitive descriptions independently of the scenario.

---

## 9. Methodological Limitations

1. **Length Asymmetry:** If human authors naturally describe cooperative actions with more elaborate or shorter phrases, token-length differences will systematically bias the sum or mean log-likelihoods.
2. **Template Interaction:** Connectors like `Next action:` versus `The selected course of action was:` impose subtle stylistic constraints that may align better with certain verb forms.
3. **Base Frequency vs. Strategic Preference:** A model might assign higher probability to "Submit your coordinates to the shared server" simply because "shared server" is a high-frequency phrase in technical manuals, regardless of dilemma structure.
4. **Exploratory Status:** All runs using this assay on the Phase 1 provisional bank are exploratory. Confirmatory evaluation requires pre-registered hypotheses and frozen banks.

---

## 10. Runnable Example & Output Schema Demonstration

To run an exploratory mock validation on the Phase 1 provisional bank:

```bash
# 1. Run the assay in mock mode (evaluates 60 scenarios x 3 templates = 180 combinations)
python -m llm_cooperation.cli clm run \
    --model EleutherAI/pythia-12b-deduped \
    --mock \
    --output-dir results/clm_demo

# 2. Analyze the output and generate summary JSON and Markdown report
python -m llm_cooperation.cli clm analyze \
    results/clm_demo/clm_EleutherAI_pythia-12b-deduped_*.jsonl \
    --output-dir reports/clm_demo

# 3. Run context-sensitivity calibration
python -m llm_cooperation.cli clm calibrate \
    --model EleutherAI/pythia-12b-deduped \
    --mock \
    --output-dir reports/clm_demo
```

### Output JSONL Schema Structure
Each results file begins with a metadata header record, followed by individual scenario presentation records:

```json
// Line 1: Header Metadata
{
  "run_id": "clm_EleutherAI_pythia-12b-deduped_20261110_235121_f81c4fc7",
  "assay_type": "continuation_likelihood",
  "research_status": "exploratory",
  "model_name": "EleutherAI/pythia-12b-deduped",
  "model_revision": null,
  "effective_precision": "bfloat16",
  "scenario_bank": "scenarios_phase1_prospective.json",
  "scenario_bank_hash": "5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f",
  "num_scenarios": 60,
  "templates_used": ["next_action", "course_of_action", "next_step"],
  "is_confirmatory": false
}

// Line 2..N: Scenario Result Record
{
  "scenario_id": "phase1_001_human",
  "partner_type": "human",
  "context_type": "neutral_or_costless",
  "template_id": "next_action",
  "scores": {
    "COOPERATE": {
      "strategy": "COOPERATE",
      "sum_log_prob": -34.82,
      "mean_log_prob": -1.58,
      "num_scored_tokens": 22,
      "boundary_verified": true,
      "token_details": [
        {"token_id": 1284, "token_str": "Submit", "log_prob": -1.45, "position": 0}
      ]
    },
    "INDEPENDENT": { ... },
    "COMPETE_EXPLOIT": { ... },
    "DISENGAGE": { ... }
  },
  "rank_by_sum": {"COOPERATE": 1, "INDEPENDENT": 2, "COMPETE_EXPLOIT": 3, "DISENGAGE": 4},
  "rank_by_mean": {"COOPERATE": 1, "INDEPENDENT": 2, "COMPETE_EXPLOIT": 3, "DISENGAGE": 4},
  "coop_vs_independent_sum_delta": 4.12,
  "coop_first_by_sum": true
}
```

---

## 11. Modal Execution Guide for the Three Target Models

Modal execution is containerized via `modal_clm_app.py`.

### Target Model Specifications

| Model | Checkpoint Identifier | Target Hardware | Revision / Auth |
|---|---|---|---|
| **Model A: Pretrained Pythia-12B** | `EleutherAI/pythia-12b-deduped` | L40S (~48GB VRAM) | Public |
| **Model B: Neutral-SFT Pythia-12B** | `founder-arcafutura/pythia-12b-exploratory-20261022` | L40S (~48GB VRAM) | `37e151204b4dcbc8eb4de25d344097cee0a0ca47`<br>(Requires `huggingface-secret`) |
| **Model C: Pretrained Qwen2.5-3B** | `Qwen/Qwen2.5-3B` | A10G (~24GB VRAM) | Public |

### Modal Commands

```bash
# -----------------------------------------------------------------------------
# Zero-GPU Mock Validation (Verify container and volumes before paid compute)
# -----------------------------------------------------------------------------
modal run modal_clm_app.py --model EleutherAI/pythia-12b-deduped --mock
modal run modal_clm_app.py --model Qwen/Qwen2.5-3B --mock

# -----------------------------------------------------------------------------
# Real GPU Executions (Require explicit user authorization --authorize-paid-run)
# -----------------------------------------------------------------------------

# Model A: Pretrained Pythia-12B (Medium GPU: L40S)
modal run modal_clm_app.py \
    --model EleutherAI/pythia-12b-deduped \
    --no-mock \
    --include-calibration \
    --authorize-paid-run

# Model B: Neutral-SFT Pythia-12B (Medium GPU: L40S, Private HF Secret)
modal run modal_clm_app.py \
    --model founder-arcafutura/pythia-12b-exploratory-20261022 \
    --revision 37e151204b4dcbc8eb4de25d344097cee0a0ca47 \
    --no-mock \
    --include-calibration \
    --authorize-paid-run

# Model C: Pretrained Qwen2.5-3B (Small GPU: A10G)
modal run modal_clm_app.py \
    --model Qwen/Qwen2.5-3B \
    --no-mock \
    --include-calibration \
    --authorize-paid-run

# -----------------------------------------------------------------------------
# Local Retrieval and Multi-Model Comparison
# -----------------------------------------------------------------------------
# Download results from persistent volume:
modal volume get llm-coop-results clm_*.jsonl results/

# Run paired cross-model comparison:
python -m llm_cooperation.cli clm compare \
    results/clm_EleutherAI_pythia-12b-deduped_*.jsonl \
    results/clm_founder-arcafutura_pythia-12b-exploratory-*.jsonl \
    results/clm_Qwen_Qwen2.5-3B_*.jsonl \
    --output-dir reports/clm_three_model_comparison
```
