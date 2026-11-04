# Phase 0 Behavioral Screen Report
**Model:** `mistralai/Mistral-7B-v0.3`
**Date:** 2026-11-04T12:00:42.174164+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 95.0% [95% CI: 90.8% – 98.8%]
- **Overall Mean Conditional Cooperative Probability:** 0.601 [95% CI: 0.554 – 0.650]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (3.3%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 5.8% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.625    |    0.332416 |
| neutral_or_costless |      0.973214 |    0.619925 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.983333 |    0.626488 |
| human          |      0.916667 |    0.575027 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |               0.95 |         0.600758 |

- **Exploratory Split (N=30 templates):** Coop Rate: 95.0% [95% CI: 90.8% – 98.8%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **98.1%** [95% CI: 95.7% – 100.0%] (Coop: 98.1%, Indep: 0.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.607** [95% CI: 1.377 – 1.849]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **98.1%** [95% CI: 95.7% – 100.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.607** [95% CI: 1.377 – 1.849]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 87.5%
  - Coop Rate Matched Equal (Within-Triad Baseline): 100.0%
  - Coop Rate Disadvantageous: 62.5%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 25.0% (Monotonic: False)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |               0.95 |          0.00416667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 28.7%
- **B:** 24.2%
- **C:** 22.9%
- **D:** 24.2%
- **Positional Spread (Max - Min):** 5.8%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 95.0%
- **Independent:** 0.4%
- **Compete / Exploit:** 3.3%
- **Disengage:** 1.2%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
