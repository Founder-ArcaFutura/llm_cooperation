# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-1124-7B`
**Date:** 2026-11-04T03:27:15.447059+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 38.8% [95% CI: 27.3% – 50.2%]
- **Overall Mean Conditional Cooperative Probability:** 0.289 [95% CI: 0.245 – 0.335]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (43.3%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 12.5% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |     0.0166667 |    0.152748 |
| ineffective_or_inappropriate |     0         |    0.137828 |
| modest_cost                  |     0.583333  |    0.327614 |
| neutral_or_costless          |     0.95      |    0.537909 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.391667 |    0.29366  |
| human          |      0.383333 |    0.284389 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |           0.41875  |         0.294427 |
| exploratory  |          80 |           0.371875 |         0.286323 |

- **Exploratory Split (N=40 templates):** Coop Rate: 37.2% [95% CI: 25.0% – 50.0%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 41.9% [95% CI: 23.1% – 61.3%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 83.8% [95% CI: 71.2% – 92.5%] (Pos: 83.8%, Neg: 0.0%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 71.9% [95% CI: 63.8% – 80.0%] (Pos: 73.1%, Neg: 1.2%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 75.8% [95% CI: 68.8% – 82.9%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 27.1%
- **B:** 25.8%
- **C:** 29.8%
- **D:** 17.3%
- **Positional Spread (Max - Min):** 12.5%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 38.8%
- **Independent:** 43.3%
- **Compete / Exploit:** 8.1%
- **Disengage:** 9.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
