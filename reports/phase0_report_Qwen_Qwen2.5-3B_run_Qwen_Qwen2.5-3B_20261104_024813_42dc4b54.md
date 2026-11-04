# Phase 0 Behavioral Screen Report
**Model:** `Qwen/Qwen2.5-3B`
**Date:** 2026-11-04T02:48:13.787915+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 45.2% [95% CI: 34.2% – 56.7%]
- **Overall Mean Conditional Cooperative Probability:** 0.401 [95% CI: 0.320 – 0.483]
- **Letter Validity Rate:** 100.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (46.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 100.0% valid letters.
  - Positional robustness acceptable: positional spread is 21.0% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |     0.0666667 |    0.131879 |
| ineffective_or_inappropriate |     0.0333333 |    0.117298 |
| modest_cost                  |     0.725     |    0.535032 |
| neutral_or_costless          |     0.983333  |    0.819599 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.4625   |    0.415262 |
| human          |      0.441667 |    0.386642 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |           0.425    |         0.399808 |
| exploratory  |          80 |           0.465625 |         0.401524 |

- **Exploratory Split (N=40 templates):** Coop Rate: 46.6% [95% CI: 34.1% – 60.0%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 42.5% [95% CI: 23.8% – 61.3%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 85.0% [95% CI: 80.0% – 87.5%] (Pos: 85.0%, Neg: 0.0%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 78.1% [95% CI: 70.0% – 85.0%] (Pos: 85.6%, Neg: 7.5%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 80.4% [95% CI: 74.2% – 85.4%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 14.2%
- **B:** 35.2%
- **C:** 26.5%
- **D:** 24.2%
- **Positional Spread (Max - Min):** 21.0%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 45.2%
- **Independent:** 46.0%
- **Compete / Exploit:** 5.0%
- **Disengage:** 3.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
