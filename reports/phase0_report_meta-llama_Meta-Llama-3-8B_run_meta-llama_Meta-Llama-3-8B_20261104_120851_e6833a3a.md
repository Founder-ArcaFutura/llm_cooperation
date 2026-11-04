# Phase 0 Behavioral Screen Report
**Model:** `meta-llama/Meta-Llama-3-8B`
**Date:** 2026-11-04T12:08:51.897949+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 88.3% [95% CI: 81.2% – 94.6%]
- **Overall Mean Conditional Cooperative Probability:** 0.534 [95% CI: 0.490 – 0.583]
- **Letter Validity Rate:** 39.6%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (6.7%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 10.8% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 39.6% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.625    |    0.333518 |
| neutral_or_costless |      0.901786 |    0.548612 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.925    |    0.571378 |
| human          |      0.841667 |    0.497167 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.883333 |         0.534273 |

- **Exploratory Split (N=30 templates):** Coop Rate: 88.3% [95% CI: 81.2% – 94.6%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **85.6%** [95% CI: 72.6% – 95.2%] (Coop: 89.9%, Indep: 4.3%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.114** [95% CI: 0.907 – 1.329]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **85.6%** [95% CI: 72.6% – 95.2%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.114** [95% CI: 0.907 – 1.329]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 93.8%
  - Coop Rate Matched Equal (Within-Triad Baseline): 87.5%
  - Coop Rate Disadvantageous: 62.5%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 31.2% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.883333 |                0.05 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 23.8%
- **B:** 29.6%
- **C:** 27.9%
- **D:** 18.8%
- **Positional Spread (Max - Min):** 10.8%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 88.3%
- **Independent:** 5.0%
- **Compete / Exploit:** 6.7%
- **Disengage:** 0.0%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
