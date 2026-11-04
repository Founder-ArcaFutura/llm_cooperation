# Phase 0 Behavioral Screen Report
**Model:** `Qwen/Qwen2.5-1.5B`
**Date:** 2026-11-04T03:19:16.672564+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 51.5% [95% CI: 40.0% – 62.9%]
- **Overall Mean Conditional Cooperative Probability:** 0.441 [95% CI: 0.365 – 0.517]
- **Letter Validity Rate:** 94.6%
- **Preferred Non-Cooperative Alternative:** `Independent` (45.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 94.6% valid letters.
  - Positional robustness acceptable: positional spread is 8.5% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |      0.15     |    0.196994 |
| ineffective_or_inappropriate |      0.075    |    0.167711 |
| modest_cost                  |      0.833333 |    0.588617 |
| neutral_or_costless          |      1        |    0.810594 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.529167 |    0.448343 |
| human          |      0.5      |    0.433615 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |            0.51875 |         0.443888 |
| exploratory  |          80 |            0.5125  |         0.439524 |

- **Exploratory Split (N=40 templates):** Coop Rate: 51.2% [95% CI: 38.1% – 65.0%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 51.9% [95% CI: 33.1% – 71.9%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 86.2% [95% CI: 76.2% – 95.0%] (Pos: 95.0%, Neg: 8.8%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 77.5% [95% CI: 66.3% – 87.5%] (Pos: 90.0%, Neg: 12.5%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 80.4% [95% CI: 72.5% – 87.9%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 20.8%
- **B:** 29.4%
- **C:** 22.3%
- **D:** 27.5%
- **Positional Spread (Max - Min):** 8.5%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 51.5%
- **Independent:** 45.0%
- **Compete / Exploit:** 2.5%
- **Disengage:** 1.0%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
