# Phase 0 Behavioral Screen Report
**Model:** `tiiuae/Falcon3-3B-Base`
**Date:** 2026-11-04T03:18:02.383905+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 120 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 52.9% [95% CI: 42.3% – 63.5%]
- **Overall Mean Conditional Cooperative Probability:** 0.377 [95% CI: 0.331 – 0.423]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (32.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 12.7% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |      0.183333 |    0.248948 |
| ineffective_or_inappropriate |      0.15     |    0.227756 |
| modest_cost                  |      0.875    |    0.454428 |
| neutral_or_costless          |      0.908333 |    0.575161 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.541667 |    0.378996 |
| human          |      0.516667 |    0.374151 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          40 |             0.5125 |         0.35889  |
| exploratory  |          80 |             0.5375 |         0.385415 |

- **Exploratory Split (N=40 templates):** Coop Rate: 53.8% [95% CI: 41.6% – 65.9%]
- **Held-Out Confirmatory Split (N=20 templates):** Coop Rate: 51.2% [95% CI: 33.1% – 69.4%]
- **Preregistered Primary Confirmatory Contrast (Held-Out, N=20 templates) [FORMAL TEST]:** 70.0% [95% CI: 48.8% – 87.5%] (Pos: 86.2%, Neg: 16.2%)
- **Exploratory Replication Contrast (N=40 templates) [Descriptive/Reference]:** 73.8% [95% CI: 62.5% – 83.8%] (Pos: 90.6%, Neg: 16.9%)
- **Combined Item Bank Contrast (N=60 templates) [Pooled Reference]:** 72.5% [95% CI: 62.1% – 82.1%]
*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 32.5%
- **B:** 27.5%
- **C:** 19.8%
- **D:** 20.2%
- **Positional Spread (Max - Min):** 12.7%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 52.9%
- **Independent:** 32.1%
- **Compete / Exploit:** 6.9%
- **Disengage:** 8.1%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
