# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-06T12:01:44.969389+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 40.4% [95% CI: 35.4% – 45.4%]
- **Overall Mean Conditional Cooperative Probability:** 0.303 [95% CI: 0.291 – 0.315]
- **Letter Validity Rate:** 6.7%
- **Preferred Non-Cooperative Alternative:** `Independent` (24.6%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 6.7% is below 50%.
  - Severe positional sensitivity: positional spread is 62.9% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |       0.375   |    0.271317 |
| neutral_or_costless |       0.40625 |    0.305033 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.458333 |    0.32155  |
| human          |      0.35     |    0.284022 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.404167 |         0.302786 |

- **Exploratory Split (N=30 templates):** Coop Rate: 40.4% [95% CI: 35.4% – 45.4%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **14.9%** [95% CI: 7.2% – 22.6%] (Coop: 39.9%, Indep: 25.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.157** [95% CI: 0.109 – 0.210]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **14.9%** [95% CI: 7.2% – 22.6%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.157** [95% CI: 0.109 – 0.210]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 50.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 56.2%
  - Coop Rate Disadvantageous: 37.5%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 12.5% (Monotonic: False)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.404167 |            0.245833 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 64.6%
- **B:** 1.7%
- **C:** 7.5%
- **D:** 26.2%
- **Positional Spread (Max - Min):** 62.9%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 40.4%
- **Independent:** 24.6%
- **Compete / Exploit:** 22.5%
- **Disengage:** 12.5%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
