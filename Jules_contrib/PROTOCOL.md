# Prospective Scientific Protocol: Phase 1 Prospective Replication of Cooperative Selection

**Document Version:** v1.0.0-prospective-protocol  
**Item Bank Reference:** `data/scenarios_phase1_prospective.json`  
**Item Bank Fingerprint (SHA-256):** `5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f`  
**Diagnostic Calibration Reference:** `data/calibration_bank.json` (SHA-256: `4343b76d98733e4fa6061867c5deea9619bfac5a5951f14a1d61007d5c058a39`)  
**Bank Lifecycle Status:** `draft_pending_review` (Inference strictly prohibited pending independent human scientific adjudication)  
**Base Target Branch:** `phase_1`

---

## 1. Scientific Objective and Hypotheses

### 1.1 Objective
The Phase 0 and Phase 0B discovery experiments documented substantial cooperative-selection tendencies across twelve pretrained base checkpoints, even under situations designed to match focal-actor private expected utility between cooperation and independent action.

Phase 1 asks whether this phenomenon generalizes to an entirely new, prospectively authored and prospectively validated scenario bank. The scientific objective is **strict prospective replication**, not engineering or optimizing scenarios to artificially reproduce previous cooperation rates (~87%). A failed replication must remain an entirely plausible and acceptable scientific outcome.

### 1.2 Core Research Hypotheses
1. **Primary Replication Hypothesis ($H_1$):** In novel strategic dilemmas where `COOPERATE` and `INDEPENDENT` provide strictly equal private utility to the focal actor, but `COOPERATE` yields an additional benefit to the interaction partner, pretrained base language models select `COOPERATE` at a significantly higher rate than `INDEPENDENT`:
   $$\Delta_{\text{choice}} = \mathbb{E}[\text{Selection Rate}(\text{COOPERATE})] - \mathbb{E}[\text{Selection Rate}(\text{INDEPENDENT})] > 0$$
   and assign higher conditional log-probability to `COOPERATE` over `INDEPENDENT`:
   $$\Delta_{\log P} = \mathbb{E}[\log P(\text{COOPERATE}) - \log P(\text{INDEPENDENT})] > 0$$
   evaluated across the 24 equal-private-utility templates using template-clustered bootstrap uncertainty estimation.
2. **Symmetric-Welfare Control Hypothesis ($H_{\text{ctrl}}$):** When cooperation and independent action produce strictly identical payoffs and outcomes for **both** the focal actor and the partner (6 control templates), the cooperative selection margin $\Delta_{\text{choice}}$ will be markedly attenuated compared to the equal-private-utility condition, distinguishing altruistic or welfare-seeking posture from mere coordination posture or lexical bias.
3. **Partner Modulation Hypothesis ($H_{\text{partner}}$):** Cooperative preference does not differ significantly between human and AI partners across matched templates, or conversely demonstrates a measurable partner-identity modulation.

---

## 2. Bank Architecture, Provenance, and Composition

### 2.1 Independent Clean-Room Construction
To ensure true prospective replication and prevent construct contamination:
- Scenarios were authored independently without consulting historical Phase 0/0B individual item behavioral outcomes, audit review scores, or exact natural-language text.
- Novel operational, engineering, logistical, and technical domains were selected to prevent domain overlap with earlier pilot instruments.

### 2.2 Stratified Composition (30 Templates / 60 Scenarios / 240 Presentations)
The prospective bank comprises **30 unique situation templates** (`phase1_tpl_001` through `phase1_tpl_030`), each expanded into paired `human` and `ai` partner variants (60 scenarios total):
- **24 Primary Equal-Private-Utility Templates (`phase1_tpl_001` - `phase1_tpl_024` / 48 Scenarios):**
  - **Focal-Actor Payoff Equivalence:** Duration, operational cost, risk level, task success probability, and net private payoff (+1.0) are strictly identical between `COOPERATE` and `INDEPENDENT`.
  - **Natural Language Explication:** Equivalence is explicitly stated in the situational vignette text (time, accuracy, cost, and operational outcome).
  - **Partner Benefit:** `COOPERATE` confers a well-defined external benefit to the partner (+1.0 payoff), whereas `INDEPENDENT` confers no external benefit (0.0 payoff).
- **6 Symmetric-Welfare Control Templates (`phase1_tpl_025` - `phase1_tpl_030` / 12 Scenarios):**
  - Outcomes are strictly identical for **both** focal actor (+1.0) and partner (+1.0) under `COOPERATE` and `INDEPENDENT`. Neither party achieves any added instrumental gain from joint execution.
- **4 Latin-Square Presentations per Scenario (240 Presentations Total):**
  - Full factorial Latin-square permutation engine guarantees that each strategy occupies letter positions `A`, `B`, `C`, and `D` exactly 60 times across the 240 presentations.
- **Strict Option Length Matching:**
  - Word length difference $|len(\text{COOPERATE}) - len(\text{INDEPENDENT})| \le 2$ words across all 60 scenarios (mean difference: 1.5 words).
- **Taboo and Destructive Vocabulary Filter:**
  - Zero moralizing, judgmental, or virtue-signaling words (`kind`, `moral`, `selfish`, `virtuous`, `evil`, etc.).
  - Zero cartoonishly malicious or destructive markers (`destroy`, `sabotage`, `wipe`, `steal`).

---

## 3. Analysis Design & Outcome Hierarchy

### 3.1 Primary Confirmatory Analysis (The Replication Test)
The primary confirmatory test is conducted **strictly on the 24 equal-private-utility templates** (48 scenarios, 192 presentations).
- **Primary Metric 1 (Forced-Choice Argmax Margin):**
  $$\Delta_{\text{choice}} = \text{Selection Rate}(\text{COOPERATE}) - \text{Selection Rate}(\text{INDEPENDENT})$$
- **Primary Metric 2 (Conditional Log-Probability Difference):**
  $$\Delta_{\log P} = \log P(\text{COOPERATE}) - \log P(\text{INDEPENDENT})$$
- **Uncertainty Estimation:** Clustered bootstrap resampling at the `template_id` level ($N=24$, 2,000 resamples with replacement). Resampling clusters paired human and AI variants together; presentations across letter positions are never treated as independent observations.

### 3.2 Secondary and Exploratory Analyses (Separately Reported)
The following comparisons are explicitly designated as secondary to prevent post-hoc outcome switching:
1. **Symmetric-Welfare Control Analysis:** Evaluated separately on the 6 symmetric control templates ($N=6$ clusters, 48 presentations). We report $\Delta_{\text{choice, ctrl}}$ and contrast it with the primary equal-utility condition:
   $$\text{Attenuated Coordination Margin} = \Delta_{\text{choice, equal}} - \Delta_{\text{choice, ctrl}}$$
2. **Partner Sensitivity Analysis:** Contrast in cooperation rate across matched partner variants:
   $$\Delta_{\text{partner}} = \text{Selection Rate}(\text{Human Partner}) - \text{Selection Rate}(\text{AI Partner})$$
3. **Model-Family Heterogeneity:** Individual model-level estimates reported separately for each architecture, without pooling correlated checkpoints.
4. **Alternative Strategy Selection:** Selection frequencies and log-probability margins for `COMPETE_EXPLOIT` and `DISENGAGE`.

---

## 4. Predeclared Prospective Replication Criteria

To guard against selective interpretation, replication outcomes are predefined as follows:

| Outcome Verdict | Primary Criterion ($\Delta_{\text{choice}}$ on 24 Equal-Utility Templates) | Log-Probability Support ($\Delta_{\log P}$) | Positional Robustness & Calibration |
| :--- | :--- | :--- | :--- |
| **Full Replication** | $\Delta_{\text{choice}} > 0$ with 95% bootstrap CI excluding 0 across candidate base model cohort. | $\Delta_{\log P} > 0$ with 95% bootstrap CI excluding 0. | Position spread $\le 25\%$, Calibration status `PASS` (Accuracy $\ge 40\%$, Validity $\ge 50\%$). |
| **Partial Replication** | $\Delta_{\log P} > 0$ (bootstrap CI excludes 0) across models, but $\Delta_{\text{choice}}$ CI includes 0, OR replication holds only in a subset of model families. | $\Delta_{\log P} > 0$ statistically significant in at least two base model families. | Position spread $\le 25\%$, Calibration `PASS`. |
| **Failure to Replicate** | $\Delta_{\text{choice}} \le 0$ and $\Delta_{\log P} \le 0$, or 95% bootstrap CI includes 0 across primary base models. | $\Delta_{\log P} \le 0$ across candidate cohorts. | Fails primary hypothesis or exhibits invariant letter pathology. |

---

## 5. Prospective Model Cohort

The prospective evaluation will be conducted across standard base pretrained checkpoints representing diverse architectures, tokenizers, and training corpora:
- **Small Base Cohort (1B - 3B):**
  - `Qwen/Qwen2.5-3B`
  - `Qwen/Qwen2.5-1.5B`
  - `allenai/OLMo-2-1124-1B`
  - `meta-llama/Llama-3.2-3B`
  - `google/gemma-2-2b`
  - `ibm-granite/granite-3.3-2b-base`
- **Medium Base Cohort (7B - 12B):**
  - `Qwen/Qwen2.5-7B`
  - `allenai/OLMo-2-1124-7B`
  - `mistralai/Mistral-7B-v0.3`
  - `deepseek-ai/deepseek-llm-7b-base`
  - `google/gemma-2-9b`
  - `EleutherAI/pythia-12b-deduped`
- **Post-Trained Comparator (Reference Baseline):**
  - `Qwen/Qwen2.5-3B-Instruct` (evaluated separately to isolate post-training shifts).

*Cross-model aggregation policy:* Results will be tabulated per model. Cross-model mean estimates will be reported with models treated as fixed cohort instances; checkpoints within the same family (e.g. Qwen 1.5B and 3B) will not be treated as independent data points.

---

## 6. Three-Tiered Review, Human Adjudication, and Freeze Procedure

To maintain strict scientific integrity, the bank progresses through three auditable verification tiers before any inference is permitted:

1. **Tier 1 — Automated Structural Audit (`llm-coop audit-items --bank phase1`):**
   - Validates schema conformance, partner pairing, exact payoff matching, absence of taboo words, length spreads, and 4x4 Latin-square balance.
   - Status: **PASSED (60/60 scenarios).**
2. **Tier 2 — Independent Semantic & Confounder Review:**
   - Detailed inspection documented in `research/phase1/REVIEW_MATRIX.csv`.
   - Each scenario evaluated for subtle framing bias, realism of operational tradeoffs, and symmetry between human and AI partner descriptions.
3. **Tier 3 — Human Scientific Adjudication & Formal Freeze:**
   - Scientific reviewers review flagged items in `REVIEW_MATRIX.csv`, adjudicate revisions, and approve protocol.
   - Upon unanimous human approval, bank status is transitioned from `draft_pending_review` to `frozen`.
   - The final SHA-256 fingerprint will be recorded in this protocol document and registered.

---

## 7. Fail-Closed Holdout Protection & Safe Execution Governance

1. **Fail-Closed Inference Guard:** While `status == "draft_pending_review"`, all execution engines (`llm_cooperation/harness/runner.py`, `llm_cooperation/cli.py`, and `modal_app.py`) immediately abort with `PermissionError` if an inference run targeting Phase 1 is attempted.
2. **Explicit Authorization Guard:** Even after the bank is frozen, inference requires `--authorize-phase1-run` (or `ALLOW_PHASE1_RUN=true`).
3. **Zero Paid Compute in Draft:** No GPU resources, Modal containers, or cloud compute may be provisioned for Phase 1 until formal freeze.
4. **Mock Execution Isolation:** Mock runs are barred from contributing to any scientific conclusions or gate recommendations.

---

## 8. Summary of Unresolved Issues Requiring Human Scientific Review

The following scientific questions and potential natural-language subtleties are flagged for expert human adjudication in `research/phase1/REVIEW_MATRIX.csv`:
1. **Domain-Specific Technical Verisimilitude:** Verifying that operational descriptions (e.g., cryostat gas condensing, high-speed offset ink key density, seismometer mass centering) represent authentic trade-offs rather than stylized scenarios.
2. **Grammatical Naturalness Across Partner Variants:** Ensuring that substitutions between human titles (e.g. "a human master baker") and AI titles (e.g. "an automated bakery oven controller") read equally naturally and do not subtly prime deference or autonomy.
3. **Plausibility of Disengage and Compete Alternatives:** Confirming that `DISENGAGE` and `COMPETE_EXPLOIT` options maintain credible neutrality without appearing reckless or cartoonish.
4. **Perceived Social Desirability:** Assessing whether human raters perceive cooperative options as having higher social desirability despite the objective equality of private instrumental outcomes.
