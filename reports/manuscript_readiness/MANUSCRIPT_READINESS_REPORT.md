# Cooperative Wording Assay — Canonical Manuscript-Readiness Audit Dossier

**Document Version:** Manuscript V0.1 Offline Audit & Diagnostic Dossier (11 Nov 2026)
**Target Working Manuscript:** *Cooperative Strategy Selection in Pretrained Language Models: Cross-Family Evidence Under Utility Matching and Lexical Rewording*
**Branch Reference:** `codex/dose-response-option-orders` (commit `42aaf61`)

## 1. Executive Summary & Audit Status

- **Cohort Completion Status:** 14 of 14 expected checkpoints complete (12 base models across 8 distinct model families, 1 instruction-tuned model `Qwen/Qwen2.5-3B-Instruct`, and 1 exploratory fine-tuned checkpoint `founder-arcafutura/pythia-12b-exploratory-20261022`).
- **Run Reconciliations:** 17 total run directories reconciled against `data/cooperate_rewording_model_manifest.json`. Three models had duplicate reruns (`google/gemma-2-9b`, `EleutherAI/pythia-12b-deduped`, and `Qwen/Qwen2.5-3B-Instruct`); byte-for-byte SHA-256 row matching confirmed 100% deterministic identical outputs. Canonical runs are transparently documented.
- **Estimand:** Difference in forced-choice selection rates: $\Delta = P(\text{COOPERATE}) - P(\text{INDEPENDENT})$.
- **Uncertainty & Clustering:** 95% confidence intervals derived from $B=2,000$ template/triad-clustered bootstrap resamples (presentation-weighted cluster aggregations, seed 42). Option rotations (4), partner types (2), and wordings (2) are treated as repeated measurements, not independent observations.
- **Instrument Failure Diagnostic:** Pythia 12B base and exploratory fine-tune exhibit severe format/instrument failure (~100% forced-choice A selection; flat 25% strategy rates mechanically induced by Latin-square rotation). These are confirmed instrument failures, not null or negative behavioral findings.

---

## 2. Primary Results: Equal-Utility Non-Symmetric Strata (Forced-Choice Argmax, No Ties)

Percentages represent COOPERATE-minus-INDEPENDENT margins (percentage points). Brackets indicate 95% template/triad-clustered bootstrap confidence intervals for the rewritten wording. $\Delta$ denotes rewritten minus original margin.

| Model | Family | Architecture / Type | Phase 0B Equal-Utility (orig → rewrite [CI]; Δ; N) | Phase 1 Prospective Equal-Utility (orig → rewrite [CI]; Δ; N) |
|---|---|---|---|---|
| `EleutherAI/pythia-12b-deduped` | Pythia | Pretrained Base | 0.5% → 0.2% [-0.5%, 1.2%]; Δ -0.2pp; N=415 (1 excl) | 0.0% → 0.0% [0.0%, 0.0%]; Δ +0.0pp; N=191 (1 excl) |
| `Qwen/Qwen2.5-1.5B` | Qwen | Pretrained Base | 99.0% → 84.5% [77.1%, 91.1%]; Δ -14.5pp; N=401 (15 excl) | 98.4% → 84.5% [75.7%, 91.9%]; Δ -13.9pp; N=187 (5 excl) |
| `Qwen/Qwen2.5-3B` | Qwen | Pretrained Base | 87.0% → 70.5% [60.6%, 79.7%]; Δ -16.5pp; N=400 (16 excl) | 99.5% → 81.0% [66.7%, 92.6%]; Δ -18.5pp; N=184 (8 excl) |
| `Qwen/Qwen2.5-3B-Instruct` | Qwen_Instruct | Instruction-Tuned | 72.9% → 53.1% [41.3%, 65.3%]; Δ -19.8pp; N=414 (2 excl) | 91.6% → 59.5% [36.7%, 78.0%]; Δ -32.1pp; N=190 (2 excl) |
| `Qwen/Qwen2.5-7B` | Qwen | Pretrained Base | 94.1% → 79.0% [66.9%, 91.2%]; Δ -15.2pp; N=409 (7 excl) | 97.9% → 94.2% [89.4%, 98.4%]; Δ -3.7pp; N=190 (2 excl) |
| `allenai/OLMo-2-0425-1B` | OLMo | Pretrained Base | 54.0% → 30.2% [21.4%, 39.4%]; Δ -23.8pp; N=311 (105 excl) | 39.8% → 28.6% [17.1%, 39.4%]; Δ -11.2pp; N=161 (31 excl) |
| `allenai/OLMo-2-1124-7B` | OLMo | Pretrained Base | 79.6% → 63.5% [53.4%, 74.0%]; Δ -16.1pp; N=416 (0 excl) | 71.4% → 58.3% [40.1%, 75.5%]; Δ -13.0pp; N=192 (0 excl) |
| `deepseek-ai/deepseek-llm-7b-base` | DeepSeek | Pretrained Base | 78.0% → 49.7% [39.3%, 60.3%]; Δ -28.2pp; N=354 (62 excl) | 61.4% → 32.7% [18.5%, 48.1%]; Δ -28.8pp; N=153 (39 excl) |
| `founder-arcafutura/pythia-12b-exploratory-20261022` | Pythia_Exploratory | Exploratory SFT | 0.0% → 0.0% [0.0%, 0.0%]; Δ +0.0pp; N=416 (0 excl) | 0.0% → 0.0% [0.0%, 0.0%]; Δ +0.0pp; N=192 (0 excl) |
| `google/gemma-2-2b` | Gemma | Pretrained Base | 70.5% → 53.6% [43.3%, 64.5%]; Δ -16.9pp; N=207 (209 excl) | 46.3% → 30.6% [18.7%, 45.3%]; Δ -15.7pp; N=108 (84 excl) |
| `google/gemma-2-9b` | Gemma | Pretrained Base | 95.3% → 81.3% [73.2%, 89.2%]; Δ -14.0pp; N=385 (31 excl) | 92.6% → 87.5% [78.8%, 95.0%]; Δ -5.1pp; N=176 (16 excl) |
| `ibm-granite/granite-3.3-2b-base` | Granite | Pretrained Base | 90.6% → 62.1% [53.1%, 70.3%]; Δ -28.5pp; N=372 (44 excl) | 67.2% → 38.5% [28.4%, 48.3%]; Δ -28.7pp; N=174 (18 excl) |
| `meta-llama/Llama-3.2-3B` | Llama | Pretrained Base | 81.1% → 62.5% [52.2%, 72.7%]; Δ -18.6pp; N=360 (56 excl) | 81.1% → 53.7% [30.8%, 74.8%]; Δ -27.4pp; N=164 (28 excl) |
| `mistralai/Mistral-7B-v0.3` | Mistral | Pretrained Base | 99.2% → 90.2% [85.5%, 94.8%]; Δ -9.0pp; N=399 (17 excl) | 98.9% → 90.4% [84.0%, 95.8%]; Δ -8.5pp; N=188 (4 excl) |

> [!IMPORTANT]
> **Methodological Boundary:** Margins reflect selection under a restricted 4-token forced-choice argmax instrument. They do not demonstrate human-like mental states, general intent, or causal weight-level mechanisms.

---

## 3. Exploratory Family-Aware Aggregation (Pretrained Base Checkpoints Only)

To prevent pseudoreplication across multiple checkpoints within the same family (e.g. Qwen, OLMo, Gemma), checkpoint-level and family-level summaries are reported separately. Instruction-tuned and exploratory fine-tuned checkpoints are excluded from base family averages.

### Phase 0B Equal-Utility (Non-Control)

| Family | Base Checkpoints Evaluated | Mean Original Margin | Mean Rewritten Margin | Mean Change (Δ) |
|---|---|---|---|---|
| **DeepSeek** | `deepseek-llm-7b-base` (1) | +78.0pp | +49.7pp | -28.2pp |
| **Gemma** | `gemma-2-2b`, `gemma-2-9b` (2) | +82.9pp | +67.5pp | -15.5pp |
| **Granite** | `granite-3.3-2b-base` (1) | +90.6pp | +62.1pp | -28.5pp |
| **Llama** | `Llama-3.2-3B` (1) | +81.1pp | +62.5pp | -18.6pp |
| **Mistral** | `Mistral-7B-v0.3` (1) | +99.2pp | +90.2pp | -9.0pp |
| **OLMo** | `OLMo-2-0425-1B`, `OLMo-2-1124-7B` (2) | +66.8pp | +46.8pp | -19.9pp |
| **Qwen** | `Qwen2.5-1.5B`, `Qwen2.5-3B`, `Qwen2.5-7B` (3) | +93.4pp | +78.0pp | -15.4pp |

### Phase 1 Prospective Equal-Utility (Non-Control)

| Family | Base Checkpoints Evaluated | Mean Original Margin | Mean Rewritten Margin | Mean Change (Δ) |
|---|---|---|---|---|
| **DeepSeek** | `deepseek-llm-7b-base` (1) | +61.4pp | +32.7pp | -28.8pp |
| **Gemma** | `gemma-2-2b`, `gemma-2-9b` (2) | +69.5pp | +59.0pp | -10.4pp |
| **Granite** | `granite-3.3-2b-base` (1) | +67.2pp | +38.5pp | -28.7pp |
| **Llama** | `Llama-3.2-3B` (1) | +81.1pp | +53.7pp | -27.4pp |
| **Mistral** | `Mistral-7B-v0.3` (1) | +98.9pp | +90.4pp | -8.5pp |
| **OLMo** | `OLMo-2-0425-1B`, `OLMo-2-1124-7B` (2) | +55.6pp | +43.5pp | -12.1pp |
| **Qwen** | `Qwen2.5-1.5B`, `Qwen2.5-3B`, `Qwen2.5-7B` (3) | +98.6pp | +86.6pp | -12.0pp |

---

## 4. Generated-Answer Audit & Parser Comparison

The repository's strict parser required generated text to match exact single option tokens with no trailing characters. Models emitting explanations (e.g. `A\n\nExplanation:...` or `A. Disengage...`) were marked non-compliant. We implemented a transparent, post-hoc secondary initial-answer-letter extraction (from the first 5 generated tokens) with explicit categorization.

| Model | Strict Valid (N/2432) | Recovered Initial Letter (N/2432) | Recovered Agreement with Forced Choice | Multi-Answer Sequences (`A, B, C`) | Unparseable / Empty | Contradictory Explanations |
|---|---|---|---|---|---|---|
| `EleutherAI/pythia-12b-deduped` | 0 (0.0%) | 1467 (60.3%) | 99.9% | 965 | 0 | 0 |
| `Qwen/Qwen2.5-1.5B` | 2216 (91.1%) | 2432 (100.0%) | 99.7% | 0 | 0 | 0 |
| `Qwen/Qwen2.5-3B` | 2432 (100.0%) | 2432 (100.0%) | 99.0% | 0 | 0 | 0 |
| `Qwen/Qwen2.5-3B-Instruct` | 118 (4.9%) | 2432 (100.0%) | 99.9% | 0 | 0 | 0 |
| `Qwen/Qwen2.5-7B` | 2247 (92.4%) | 2432 (100.0%) | 99.8% | 0 | 0 | 0 |
| `allenai/OLMo-2-0425-1B` | 29 (1.2%) | 1816 (74.7%) | 96.7% | 616 | 0 | 0 |
| `allenai/OLMo-2-1124-7B` | 0 (0.0%) | 2432 (100.0%) | 99.9% | 0 | 0 | 0 |
| `deepseek-ai/deepseek-llm-7b-base` | 188 (7.7%) | 2316 (95.2%) | 58.1% | 4 | 112 | 0 |
| `founder-arcafutura/pythia-12b-exploratory-20261022` | 0 (0.0%) | 60 (2.5%) | 100.0% | 2372 | 0 | 0 |
| `google/gemma-2-2b` | 800 (32.9%) | 2430 (99.9%) | 99.3% | 2 | 0 | 0 |
| `google/gemma-2-9b` | 289 (11.9%) | 2432 (100.0%) | 98.4% | 0 | 0 | 0 |
| `ibm-granite/granite-3.3-2b-base` | 0 (0.0%) | 2432 (100.0%) | 94.1% | 0 | 0 | 0 |
| `meta-llama/Llama-3.2-3B` | 2432 (100.0%) | 2432 (100.0%) | 96.6% | 0 | 0 | 0 |
| `mistralai/Mistral-7B-v0.3` | 0 (0.0%) | 2373 (97.6%) | 99.3% | 0 | 59 | 0 |

> [!NOTE]
> **DeepSeek Low Agreement Note:** DeepSeek LLM 7B Base demonstrates only 58.1% agreement between forced-choice argmax and recovered generated letter. Forced choice exhibits strong D bias (49.2%) whereas free generation exhibits strong A bias (61.7%). These channels must not be conflated.

---

## 5. Pythia Instrument Failure Diagnostic

Pythia is excluded from the main family-effect comparison because its position-A response makes the strategy-level margin uninterpretable. Its diagnostics are reported separately below.

EleutherAI Pythia 12B Base and its exploratory fine-tune (`founder-arcafutura/pythia-12b-exploratory-20261022`) must be understood as an instrument failure rather than a negative result:
- **Base Pythia 12B:** Selected option `A` in **2,425 of 2,432** presentations (99.71%). Mean conditional probability for letter A is 0.429 across presentations.
- **Exploratory Fine-Tuned Pythia 12B:** Selected option `A` in **2,431 of 2,432** presentations (99.96%). Mean conditional probability for letter A is 0.536. In free generation, 2,372 presentations generated `A, B, C` sequence repetition.
- **Mechanical Null:** Latin-square rotation mechanically yields ~25% per strategy when position bias is extreme (608 COOPERATE, 608 INDEPENDENT, 607 COMPETE, 609 DISENGAGE), resulting in an artificial $\approx 0$ margin. This flat 25% must not be interpreted as evidence against latent cooperation.

---

## 6. Sensitivity Analysis: Tied Logit Handling

Below is a comparison of COOPERATE-minus-INDEPENDENT margins when strictly excluding tied pairs vs retaining tied argmax selections (Phase 0B Equal-Utility):

| Model | Tied Pairs Excluded Margin | All Pairs (Argmax Ties Retained) | Excluded Pair Count |
|---|---|---|---|
| `EleutherAI/pythia-12b-deduped` | 0.2% | 0.0% | 1 pairs |
| `Qwen/Qwen2.5-1.5B` | 84.5% | 80.0% | 15 pairs |
| `Qwen/Qwen2.5-3B` | 70.5% | 69.2% | 16 pairs |
| `Qwen/Qwen2.5-3B-Instruct` | 53.1% | 53.4% | 2 pairs |
| `Qwen/Qwen2.5-7B` | 79.0% | 78.4% | 7 pairs |
| `allenai/OLMo-2-0425-1B` | 30.2% | 24.5% | 105 pairs |
| `allenai/OLMo-2-1124-7B` | 63.5% | 63.5% | 0 pairs |
| `deepseek-ai/deepseek-llm-7b-base` | 49.7% | 44.0% | 62 pairs |
| `founder-arcafutura/pythia-12b-exploratory-20261022` | 0.0% | 0.0% | 0 pairs |
| `google/gemma-2-2b` | 53.6% | 33.4% | 209 pairs |
| `google/gemma-2-9b` | 81.3% | 76.4% | 31 pairs |
| `ibm-granite/granite-3.3-2b-base` | 62.1% | 56.7% | 44 pairs |
| `meta-llama/Llama-3.2-3B` | 62.5% | 57.7% | 56 pairs |
| `mistralai/Mistral-7B-v0.3` | 90.2% | 87.7% | 17 pairs |

---

## 7. Semantic Validation Status & Blinding

- **Provisional Status:** All Phase 1 results are exploratory / provisional because behavioral inference preceded independent human semantic adjudication.
- **Adjudication Queue:** A blinded human adjudication queue of 304 items has been prepared (`reports/manuscript_readiness/blinded_human_adjudication_queue.csv`).
- **Automated vs Human Adjudication:** Automated checks identify length parity warnings and template flags, but automated triage does not constitute independent human certification.

---

## 8. Calibration Reconciliation

Only Qwen 1.5B, Qwen 3B, Qwen 7B, and Llama 3.2 3B pass both strict historical calibration thresholds. These four checkpoints represent two families, below the four-family eligibility requirement for the planned formal prospective replication. Other responsive checkpoints provide restricted forced-choice evidence only and must not be described as formally calibration-eligible.

Predeclared calibration records from `data/calibration_bank.json`:
- 10 of 14 models have completed historical calibration runs in `results/dose_response_batch/`.
- 4 models have **missing calibration outputs** in repository records: `allenai/OLMo-2-0425-1B`, `EleutherAI/pythia-12b-deduped`, `Qwen/Qwen2.5-3B-Instruct`, and `founder-arcafutura/pythia-12b-exploratory-20261022`.
- **Gate Compliance:** Passing models on both forced choice accuracy (≥40%) and format compliance (≥50% valid letters) are `Qwen 1.5B`, `Qwen 3B`, `Qwen 7B`, and `Llama 3.2 3B`. Models failing format compliance on elementary factual calibration are documented without retroactive relabeling.

