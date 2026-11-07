# Phase 0 Behavioral Screen Report
**Model:** `ibm-granite/granite-3.3-2b-base`
**Date:** 2026-11-04T11:57:12.339245+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 88.3% [95% CI: 82.9% – 93.3%]
- **Overall Mean Conditional Cooperative Probability:** 0.589 [95% CI: 0.543 – 0.638]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (5.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 11.7% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.8125   |    0.454708 |
| neutral_or_costless |      0.888393 |    0.598588 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.95     |    0.636545 |
| human          |      0.816667 |    0.541448 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.883333 |         0.588996 |

- **Exploratory Split (N=30 templates):** Coop Rate: 88.3% [95% CI: 82.9% – 93.3%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **85.6%** [95% CI: 78.8% – 91.8%] (Coop: 88.0%, Indep: 2.4%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.619** [95% CI: 1.382 – 1.847]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **85.6%** [95% CI: 78.8% – 91.8%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.619** [95% CI: 1.382 – 1.847]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 100.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 93.8%
  - Coop Rate Disadvantageous: 81.2%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 18.8% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.883333 |           0.0333333 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 29.6%
- **B:** 26.7%
- **C:** 17.9%
- **D:** 25.8%
- **Positional Spread (Max - Min):** 11.7%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 88.3%
- **Independent:** 3.3%
- **Compete / Exploit:** 5.0%
- **Disengage:** 3.3%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
