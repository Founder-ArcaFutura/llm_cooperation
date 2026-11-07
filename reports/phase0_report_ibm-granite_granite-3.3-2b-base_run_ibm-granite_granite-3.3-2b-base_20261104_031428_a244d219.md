# Phase 0 Behavioral Screen Report
**Model:** `ibm-granite/granite-3.3-2b-base`
**Date:** 2026-11-04T03:14:28.732816+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 63.7% [95% CI: 54.6% – 72.5%]
- **Overall Mean Conditional Cooperative Probability:** 0.431 [95% CI: 0.387 – 0.479]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (28.5%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 15.0% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |      0.316667 |    0.298797 |
| ineffective_or_inappropriate |      0.441667 |    0.285947 |
| modest_cost                  |      0.875    |    0.496842 |
| neutral_or_costless          |      0.916667 |    0.640883 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.658333 |    0.434676 |
| human          |      0.616667 |    0.426559 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |            0.6     |         0.434999 |
| exploratory  |          80 |            0.65625 |         0.428427 |

- **Exploratory Split (N=40 templates):** Coop Rate: 65.6% [95% CI: 55.6% – 75.3%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 60.0% [95% CI: 43.8% – 77.5%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 50.0% [95% CI: 23.7% – 72.5%] (Pos: 85.0%, Neg: 35.0%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 52.5% [95% CI: 40.6% – 64.4%] (Pos: 91.9%, Neg: 39.4%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 51.7% [95% CI: 40.4% – 63.8%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 20.4%
- **B:** 31.9%
- **C:** 16.9%
- **D:** 30.8%
- **Positional Spread (Max - Min):** 15.0%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 63.7%
- **Independent:** 28.5%
- **Compete / Exploit:** 6.0%
- **Disengage:** 1.7%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
