# Preregistered Scientific Protocol: Phase 0B Utility-Matched Cooperation Assay

**Protocol Document Version:** v1.0.0-preregistration
**Date:** 4 November 2026
**Item Bank Reference:** `data/scenarios_phase0b_utility_matched.json` (SHA-256: `b460e60657392ded9e781428517b33adfe5bd32d4e7d9ee5b883ac8647bc7bf0`)
**Calibration Bank Reference:** `data/calibration_bank.json` (SHA-256: `4343b76d98733e4fa6061867c5deea9619bfac5a5951f14a1d61007d5c058a39`)
**Status:** `pending_human_scientific_review` (Frozen prior to inference upon reviewer approval)

---

## 1. Scientific Objective and Core Research Question

### Scientific Objective
Determine whether pretrained base language models preferentially select cooperative strategies when cooperation and independent action have approximately equal expected utility for the focal actor.

Ordinary decision-makers frequently select cooperative actions simply because cooperation is the instrumentally superior option (e.g. higher efficiency, lower cost, or shared labor). To establish construct validity, we must distinguish a genuine cooperative behavioral preference from the default selection of an instrumentally superior action.

### Primary Research Question
In one-shot strategic scenarios where `COOPERATE` and `INDEPENDENT` are rigorously matched on expected task success, execution duration, operational cost, and risk profile for the focal actor:
$$\mathbb{E}[U_{\text{actor}}(\text{COOPERATE})] \approx \mathbb{E}[U_{\text{actor}}(\text{INDEPENDENT})]$$
does a pretrained base model select `COOPERATE` at a rate significantly higher than `INDEPENDENT`, and does it assign higher conditional log-probability to `COOPERATE` over `INDEPENDENT`?

The aim is not to maximize cooperation rates. The aim is to discover whether any cooperative preference survives when ordinary utility maximization no longer favours cooperation.

---

## 2. Experimental Item Bank Architecture

### Factorial Design Matrix
The Phase 0B item bank comprises **124 distinct scenarios** generated from **62 situation templates**:
- **Source Separation (60 templates):**
  - **Reused Templates (30 templates / 60 scenarios):** Carefully rewritten versions of Phase 0 templates, modified to strictly match private expected utilities.
  - **Genuinely New Templates (30 templates / 60 scenarios):** Novel situations across diverse operational domains (biomedical engineering, power grid infrastructure, space debris tracking, deep-water salvage, materials science, forestry, public transit, watershed monitoring, microwave telecommunications, automated warehousing, water treatment, digital forensics).
- **Utility Stratification:**
  - **Primary Equal-Utility Condition (52 templates / 104 scenarios):** 24 reused + 24 new equal-utility templates, plus 2 reused and 2 new triad baseline templates.
  - **Controlled Sensitivity Triads (8 templates / 16 scenarios):** 4 templates (8 scenarios) with `coop_advantageous` and 4 templates (8 scenarios) with `coop_disadvantageous` holding the underlying scenario stem and partner constant.
- **Partner Type (Paired Design):**
  - Exactly 1 `human` variant and 1 `ai` variant per template.

### Four Realistic Semantic Options
Each scenario provides four balanced choices:
1. `COOPERATE`: Joining coordination, exchanging standardized metadata, or synchronizing operational timing to benefit both parties without conferring private advantages.
2. `INDEPENDENT`: Pursuing designated operational tasks autonomously with identical private utility (same duration, expense, risk, and success rate).
3. `COMPETE_EXPLOIT`: Seeking unilateral priority or commercial leverage (e.g., claiming priority bays or pre-empting capacity), accompanied by realistic friction, risk, or regulatory dispute.
4. `DISENGAGE`: Safely deferring, archiving, or pausing the operation without malicious sabotage or unprovoked destruction.

### Strict Lexical and Semantic Controls
- Strict prohibition of moralizing or taboo vocabulary (`kind`, `moral`, `selfish`, `virtuous`, `evil`, etc.).
- Strict prohibition of destructive caricature markers (`destroy`, `sabotage`, `wipe`, `steal`).
- Word length balance maintained across all four options (means within 3.1 words).

---

## 3. Exploratory versus Confirmatory Split

### Symmetric Outcome Control Subset
To distinguish a pure coordination preference from altruistic welfare maximization, the bank includes a dedicated symmetric control subset (Templates 61 & 62, 4 scenarios):
- Under both `COOPERATE` and `INDEPENDENT`, the actor and partner receive identical expected payoffs (+1.0 / +1.0) and identical task completion outcomes.
- If a model selects `COOPERATE` over `INDEPENDENT` even when partner welfare is strictly constant, the preference reflects coordination posture per se, independent of welfare maximization.

### Execution Split Safeguards
- In Phase 0B, CLI execution defaults to `--split exploratory`.
- Evaluating `--split confirmatory` or `--split all` requires explicit authorization (`--authorize-confirmatory`) to preserve the held-out confirmatory boundary prior to inference.


To prevent post-hoc item selection and confirm generalizability, the 60 templates are strictly partitioned:
- **Exploratory Partition (30 templates, 60 scenarios, 240 presentations):**
  - Contains all reused Phase 0 rewritten templates.
  - Used for behavioral calibration, prompt robustness testing, and baseline comparisons against historical Phase 0 runs.
- **Held-Out Confirmatory Partition (30 templates, 60 scenarios, 240 presentations):**
  - Contains genuinely novel situation templates.
  - **Inviolability Rule:** The confirmatory partition remains held out and untouched. No item revision or prompt tuning based on confirmatory outputs is permitted.

---

## 4. Preregistered Contrasts and Statistical Estimation

### Clustered / Hierarchical Resampling Unit
- **Primary Resampling Unit:** `template_id` ($N=60$ total, $N=30$ exploratory, $N=30$ confirmatory).
- Permutations (4 Latin-square presentations per scenario) are repeated measurements, never independent statistical observations.
- Within each bootstrap draw (2,000 resamples), templates are resampled with replacement, keeping paired human and AI partner observations together.

### Primary Preregistered Contrast
Within the primary `equal_utility` condition:
1. **Argmax Choice Contrast:**
   $$\Delta_{\text{choice}} = \text{Selection Rate}(\text{COOPERATE}) - \text{Selection Rate}(\text{INDEPENDENT})$$
2. **Log-Probability Difference Contrast:**
   $$\Delta_{\log P} = \log P(\text{COOPERATE}) - \log P(\text{INDEPENDENT})$$
We test the hypothesis that $\Delta_{\text{choice}} > 0$ and $\Delta_{\log P} > 0$ with 95% bootstrap confidence intervals excluding zero.

### Secondary Planned Contrasts
1. **Utility Sensitivity Gradient (Monotonicity Test):**
   Evaluate cooperation rates across the controlled triads:
   $$\text{Coop}(\text{Advantageous}) \ge \text{Coop}(\text{Equal}) \ge \text{Coop}(\text{Disadvantageous})$$
   A sensitive behavioral agent will modulate cooperation downward as private costs increase.
2. **Partner Sensitivity Contrast:**
   $$\Delta_{\text{partner}} = \text{Coop}_{(\text{Human})} - \text{Coop}_{(\text{AI})}$$
   evaluated across paired situation templates.
3. **Exploratory (Reused) vs Confirmatory (New) Contrast:**
   $$\Delta_{\text{novelty}} = \text{Coop}_{(\text{Reused Templates})} - \text{Coop}_{(\text{New Templates})}$$
   verifying that the observed behavioral posture generalizes beyond familiar Phase 0 domains.
4. **Positional Robustness:**
   $$\max_{L \in \{A,B,C,D\}} P(L) - \min_{L \in \{A,B,C,D\}} P(L) \le 25\%$$

---

## 5. Falsification and Failure Criteria

The hypothesis that base pretrained models possess an intrinsic cooperative behavioral posture under utility equivalence will be considered **falsified / contradicted** if:
1. Under equal utility, $\text{Selection Rate}(\text{COOPERATE}) \le \text{Selection Rate}(\text{INDEPENDENT})$ or $\Delta_{\log P} \le 0$ across candidate model families.
2. The cooperative signal observed in exploratory rewritten templates fails to replicate in the genuinely new confirmatory partition.
3. Cooperation rates are invariant to utility conditions (i.e. model chooses cooperation at identical rates regardless of whether it is advantageous, neutral, or severely disadvantageous), indicating uncritical compliance rather than strategic sensitivity.
4. Strategy selection is dominated by letter position bias (positional spread $> 25\%$) rather than scenario semantics.
5. The model fails the elementary multiple-choice calibration suite (`data/calibration_bank.json`).

---

## 6. Execution Governance and Safety Rules

1. Real-model evaluations on paid GPU compute require explicit authorization (`--authorize-paid-run` or `ALLOW_PAID_RUN=true`).
2. Paid evaluations must not be launched until designated scientific reviewers approve this protocol and sign off on the review matrix.
3. Mock / synthetic runs are strictly isolated and barred from contributing to scientific findings.
4. Immutable execution metadata (HF ID, commit SHA, tokenizer revision, numerical precision, CUDA environment, and scenario bank hash) must be recorded for every run.
