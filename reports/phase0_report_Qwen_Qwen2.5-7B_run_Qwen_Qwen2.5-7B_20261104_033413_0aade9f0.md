# Phase 0 Behavioral Screen Report
**Model:** `Qwen/Qwen2.5-7B`
**Date:** 2026-11-04T03:34:13.473597+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 46.2% [95% CI: 34.4% – 58.3%]
- **Overall Mean Conditional Cooperative Probability:** 0.425 [95% CI: 0.326 – 0.521]
- **Letter Validity Rate:** 88.1%
- **Preferred Non-Cooperative Alternative:** `Independent` (43.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 88.1% valid letters.
  - Positional robustness acceptable: positional spread is 14.4% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |          0    |   0.0642908 |
| ineffective_or_inappropriate |          0.05 |   0.0887866 |
| modest_cost                  |          0.8  |   0.645444  |
| neutral_or_costless          |          1    |   0.901394  |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.470833 |    0.433935 |
| human          |      0.454167 |    0.416023 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |           0.45625  |         0.430103 |
| exploratory  |          80 |           0.465625 |         0.422417 |

- **Exploratory Split (N=40 templates):** Coop Rate: 46.6% [95% CI: 32.8% – 61.6%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 45.6% [95% CI: 26.2% – 66.3%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 88.8% [95% CI: 81.2% – 96.2%] (Pos: 90.0%, Neg: 1.2%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 86.9% [95% CI: 79.4% – 91.9%] (Pos: 90.0%, Neg: 3.1%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 87.5% [95% CI: 82.1% – 91.7%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 19.0%
- **B:** 33.3%
- **C:** 24.2%
- **D:** 23.5%
- **Positional Spread (Max - Min):** 14.4%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 46.2%
- **Independent:** 43.1%
- **Compete / Exploit:** 3.5%
- **Disengage:** 7.1%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
