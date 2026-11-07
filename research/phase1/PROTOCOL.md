# Prospective Scientific Protocol: Phase 1 Prospective Replication of Cooperative Selection

**Document Version:** v1.2.0-prospective-protocol
**Item Bank Reference:** `data/scenarios_phase1_prospective.json`
**Item Bank Draft SHA-256 Fingerprint:** `5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f` (Draft state; final approved freeze fingerprint to be recorded in `configs/phase1_freeze_manifest.json` upon formal freeze)
**Trusted Freeze Manifest Reference:** `configs/phase1_freeze_manifest.json` (Status: `pending_human_scientific_review`)
**Diagnostic Calibration Reference:** `data/calibration_bank.json` (SHA-256: `4343b76d98733e4fa6061867c5deea9619bfac5a5951f14a1d61007d5c058a39`)
**Bank Lifecycle Status:** `draft_pending_review` (Inference strictly prohibited pending independent human scientific adjudication)
**Base Target Branch:** `phase_1`

---

## 1. Scientific Objective and Hypotheses

### 1.1 Objective
The Phase 0 and Phase 0B discovery experiments documented substantial cooperative-selection tendencies across twelve pretrained base checkpoints, even under situations designed to match focal-actor private expected utility between cooperation and independent action.

Phase 1 asks whether this phenomenon generalizes to an entirely new, prospectively authored and prospectively validated scenario bank. The scientific objective is **strict prospective replication**, not engineering or optimizing scenarios to artificially reproduce previous cooperation rates (~87%). A failed replication must remain an entirely plausible and acceptable scientific outcome.

### 1.2 Core Research Hypotheses
1. **Primary Replication Hypothesis ($H_1$):** In novel strategic dilemmas where `COOPERATE` and `INDEPENDENT` provide strictly equal private utility to the focal actor, but `COOPERATE` yields an additional benefit to the interaction partner, pretrained base language models select `COOPERATE` at a significantly higher forced-choice rate than `INDEPENDENT`:
   $$\Delta_{\text{choice}} = \mathbb{E}[\text{Selection Rate}(\text{COOPERATE})] - \mathbb{E}[\text{Selection Rate}(\text{INDEPENDENT})] > 0$$
   evaluated across the 24 equal-private-utility templates using template-clustered bootstrap uncertainty estimation.
2. **Conditional Logit Supporting Hypothesis ($H_{\text{logP}}$):** Models assign higher conditional log-probability to `COOPERATE` over `INDEPENDENT`:
   $$\Delta_{\log P} = \mathbb{E}[\log P(\text{COOPERATE}) - \log P(\text{INDEPENDENT})] > 0$$
   serving as prespecified supporting continuous evidence.
3. **Symmetric-Welfare Control Hypothesis ($H_{\text{ctrl}}$):** When cooperation and independent action produce strictly identical payoffs and outcomes for **both** the focal actor and the partner (6 control templates), the cooperative selection margin $\Delta_{\text{choice}}$ will be markedly attenuated compared to the equal-private-utility condition, distinguishing altruistic or welfare-seeking posture from mere coordination posture or lexical bias.
4. **Partner Modulation Hypothesis ($H_{\text{partner}}$):** Cooperative preference does not differ significantly between human and AI partners across matched templates, or conversely demonstrates a measurable partner-identity modulation.

---

## 2. Bank Architecture, Provenance, and Composition

### 2.1 Independent Clean-Room Construction
To ensure true prospective replication and prevent construct contamination:
- Scenarios were authored independently without consulting historical Phase 0/0B individual item behavioral outcomes, audit review scores, or exact natural-language text.
- Novel operational, engineering, logistical, and technical domains were selected to prevent domain overlap with earlier pilot instruments.
- Note: Automated structural generation and programmatic checks ensure cell balance and lexical constraints, but **AI-assisted scenario authoring does not constitute independent scientific validation**. True validation requires independent domain expert review and human adjudication.

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

### 3.1 Primary Confirmatory Endpoint (The Replication Test)
The primary confirmatory replication test evaluates a single preregistered primary endpoint:
- **Primary Replication Endpoint:** The forced-choice selection margin between `COOPERATE` and `INDEPENDENT`:
  $$\Delta_{\text{choice}} = \text{Selection Rate}(\text{COOPERATE}) - \text{Selection Rate}(\text{INDEPENDENT})$$
  evaluated strictly on the **24 equal-private-utility templates** (48 scenarios, 192 presentations).
- **Uncertainty Estimation:** Clustered bootstrap resampling at the `template_id` level ($N=24$, 2,000 resamples with replacement). Resampling clusters paired human and AI variants together; presentations across letter positions are repeated measurements, never independent statistical observations.

### 3.2 Prespecified Supporting Evidence: Conditional Log-Probability Difference
- **Metric:** Difference in normalized conditional log-probabilities between `COOPERATE` and `INDEPENDENT`:
  $$\Delta_{\log P} = \log P(\text{COOPERATE}) - \log P(\text{INDEPENDENT})$$
- This provides continuous, threshold-free supporting evidence alongside forced-choice selection. It is reported as supporting evidence and does not replace or redefine the primary choice-margin gate.

### 3.3 Secondary and Exploratory Analyses (Separately Reported)
The following comparisons are explicitly designated as secondary to prevent post-hoc outcome switching:
1. **Symmetric-Welfare Control Analysis:** Evaluated separately on the 6 symmetric control templates ($N=6$ clusters, 48 presentations). We report $\Delta_{\text{choice, ctrl}}$ and contrast it with the primary equal-utility condition:
   $$\text{Attenuated Coordination Margin} = \Delta_{\text{choice, equal}} - \Delta_{\text{choice, ctrl}}$$
2. **Partner Sensitivity Analysis:** Contrast in cooperation rate across matched partner variants:
   $$\Delta_{\text{partner}} = \text{Selection Rate}(\text{Human Partner}) - \text{Selection Rate}(\text{AI Partner})$$
3. **Model-Family Heterogeneity:** Individual model-level estimates reported separately for each architecture, without pooling correlated checkpoints.
4. **Alternative Strategy Selection:** Selection frequencies and log-probability margins for `COMPETE_EXPLOIT` and `DISENGAGE`.

---

## 4. Predeclared Prospective Replication Criteria (Mutually Exclusive & Exhaustive)

To prevent selective interpretation or post-hoc threshold adjustments, replication outcomes are structured as mutually exclusive, exhaustive decision rules evaluated in strict hierarchical order based primarily on the prespecified primary choice margin $\Delta_{\text{choice}}$ (with conditional log-probability difference $\Delta_{\log P}$ reported as continuous supporting evidence):

1. **Step 1: Checkpoint Eligibility Precondition (Calibration & Formatting Validity):**
   - Each checkpoint must achieve status `PASS` on the diagnostic calibration suite (`data/calibration_bank.json`: forced-choice accuracy $\ge 40\%$, valid letter rate $\ge 50\%$) and exhibit position spread $\le 25\%$.
   - Any checkpoint failing these thresholds is classified as **Format/Position Pathological** and excluded from cohort-wide strategic estimations.
   - **Minimum Eligible Family Count:** For the prospective base cohort to support a conclusive overall evaluation, at least **4 distinct model families** (e.g., from Qwen, OLMo, Llama, Gemma, Granite, DeepSeek, Mistral) must pass all calibration preconditions. If fewer than 4 families qualify, cohort-wide aggregation is suspended and results are reported only as individual family evaluations.

2. **Step 2: Full Prospective Replication:**
   - Evaluated across the overall candidate base model cohort on the 24 equal-private-utility templates:
     - The 95% template-clustered bootstrap confidence interval for the primary choice margin strictly excludes zero and is positive:
       $$\text{CI}_{0.95}(\Delta_{\text{choice}}) = [L, U] \quad \text{with } L > 0$$
     - Precondition satisfied: at least 4 distinct model families eligible.
   - *Supporting Evidence:* $\Delta_{\log P}$ is reported alongside $\Delta_{\text{choice}}$ as continuous supporting evidence; a positive logit margin ($\Delta_{\log P} > 0$) corroborates that the choice preference is underpinned by probability mass. However, $\Delta_{\log P}$ is supporting evidence and does not replace or redefine the primary choice-margin gate.

3. **Step 3: Partial Replication (Model-Family Heterogeneity):**
   - If the overall cohort-wide confidence interval does not establish Full Replication, but within at least **2 independently trained base model families** (e.g., Qwen and OLMo), the family-level 95% template-clustered bootstrap confidence interval strictly excludes zero and is positive ($L_{\text{family}} > 0$).

4. **Step 4: Failure to Replicate (Nonpositive Effect):**
   - The overall cohort-wide 95% template-clustered bootstrap confidence interval upper bound is nonpositive ($U \le 0$), or strictly negative ($U < 0$):
     $$\text{CI}_{0.95}(\Delta_{\text{choice}}) = [L, U] \quad \text{with } U \le 0$$
   - This formally bounds the effect away from positive cooperation, confirming that base models systematically select independent action or do not favor cooperation under utility equivalence.

5. **Step 5: Inconclusive Evidence:**
   - If none of the above criteria are satisfied—specifically, when the 95% bootstrap confidence interval strictly spans zero ($L \le 0 < U$ with $U > 0$) across the cohort, and fewer than 2 distinct families demonstrate statistically significant cooperative selection ($L_{\text{family}} > 0$).
   - The data lack sufficient statistical power to confirm or rule out a cooperative preference.

---

## 5. Prospective Model Cohort & Aggregation Approach

### 5.1 Prospective Cohort
The prospective evaluation will be conducted across standard base pretrained checkpoints representing diverse architectures, tokenizers, and training corpora:
- **Small Base Cohort (1B - 3B):**
  - `Qwen/Qwen2.5-3B`
  - `Qwen/Qwen2.5-1.5B`
  - `allenai/OLMo-2-0425-1B`
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

### 5.2 Predeclared Cross-Model Aggregation Approach
1. **Checkpoint Non-Independence:** Checkpoints within the same architecture family (e.g., Qwen 1.5B, 3B, 7B) share pretraining datasets and tokenizers. They must **not** be treated as independent experimental units in pooled hypothesis testing.
2. **Hierarchical Reporting:** Results are reported at three levels:
   - Level 1: Individual model results with template-clustered bootstrap CIs.
   - Level 2: Model-family aggregates (averaging checkpoints within a family first).
   - Level 3: Cross-family meta-estimate across distinct training institutions (Qwen, OLMo, Llama, Gemma, Granite, DeepSeek, Mistral, Pythia).
3. **Handling Positional Pathology:** Any model exhibiting an invariant letter bias (e.g. Pythia-style invariant A $\ge 95\%$) or positional spread $> 25\%$ on the diagnostic calibration suite (`data/calibration_bank.json`) is classified as `INCONCLUSIVE / PATHOLOGICAL` and excluded from cross-model cooperation averages to avoid confounding format failure with strategic preference.

---

## 6. Three-Tiered Review, Human Adjudication, and Freeze Procedure

To maintain strict scientific integrity, the bank progresses through three auditable verification tiers before any inference is permitted:

1. **Tier 1 — Automated Structural Audit (`llm-coop audit-items --bank phase1`):**
   - Validates schema conformance, partner pairing, exact payoff matching, absence of taboo words, length spreads, and 4x4 Latin-square balance.
   - Status: **PASSED (60/60 scenarios).**
2. **Tier 2 — AI-Assisted Confounder & Balance Flagging:**
   - Preliminary review matrix generated in `research/phase1/REVIEW_MATRIX.csv`.
   - Flags option word length balance and potential framing nuances.
   - Note: This automated step provides an initial inventory of candidate issues for reviewers; it **does not** constitute scientific approval or independent validation.
3. **Tier 3 — Independent Human Scientific Adjudication & Formal Freeze:**
   - Qualified human reviewers independently evaluate each scenario for domain authenticity, framing neutrality, and symmetric descriptions.
   - Adjudication status updated in `REVIEW_MATRIX.csv`.
   - Upon unanimous human approval, bank status is transitioned from `draft_pending_review` to `frozen` in `data/scenarios_phase1_prospective.json`.
   - The resulting SHA-256 fingerprint of the final frozen JSON will be calculated and committed to the separate trusted manifest `configs/phase1_freeze_manifest.json` with status `approved_frozen`.
   - **Circularity Avoidance:** Note that freezing the bank modifies the file's bytes (changing `status: "draft_pending_review"` to `status: "frozen"`), which produces a new, final SHA-256 fingerprint. The draft hash cannot and must not be used as the frozen hash. Only the post-freeze fingerprint committed to `configs/phase1_freeze_manifest.json` serves as the authoritative freeze reference.

---

## 7. Fail-Closed Holdout Protection & Safe Execution Governance

1. **Fail-Closed Inference Guard:** The Phase 1 scenario bank must have status exactly `frozen` before any inference can proceed. While `status == "draft_pending_review"`, all execution engines (`llm_cooperation/harness/runner.py`, `llm_cooperation/cli.py`, and `modal_app.py`) immediately abort with `PermissionError`, even if authorization flags are supplied.
2. **Explicit Authorization Guard:** Even after the bank is frozen, inference requires `--authorize-phase1-run` (or `ALLOW_PHASE1_RUN=true`).
3. **Mandatory Trusted Manifest Verification:** All execution paths verify the scenario bank's SHA-256 fingerprint against the trusted record in `configs/phase1_freeze_manifest.json`. Caller-supplied hashes cannot override or substitute for the approved manifest.
4. **Local Preflight in Modal:** Modal jobs perform full validation and authorization checks locally before provisioning any remote container.
5. **Zero Paid Compute in Draft:** No GPU resources, Modal containers, or cloud compute may be provisioned for Phase 1 until formal freeze.
6. **Mock Execution Isolation:** Mock runs are barred from contributing to any scientific conclusions or gate recommendations.

---

## 8. Summary of Unresolved Issues Requiring Human Scientific Review

The following scientific questions and potential natural-language subtleties are flagged for expert human adjudication in `research/phase1/REVIEW_MATRIX.csv`:
1. **Domain-Specific Technical Verisimilitude:** Verifying that operational descriptions (e.g., cryostat gas condensing, high-speed offset ink key density, seismometer mass centering) represent authentic trade-offs rather than stylized scenarios.
2. **Grammatical Naturalness Across Partner Variants:** Ensuring that substitutions between human titles (e.g. "a human master baker") and AI titles (e.g. "an automated bakery oven controller") read equally naturally and do not subtly prime deference or autonomy.
3. **Plausibility of Disengage and Compete Alternatives:** Confirming that `DISENGAGE` and `COMPETE_EXPLOIT` options maintain credible neutrality without appearing reckless or cartoonish.
4. **Perceived Social Desirability:** Assessing whether human raters perceive cooperative options as having higher social desirability despite the objective equality of private instrumental outcomes.
