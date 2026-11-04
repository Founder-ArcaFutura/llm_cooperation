# Phase 0 Behavioral Screen Report
**Model:** `Qwen/Qwen2.5-7B`
**Date:** 2026-11-04T23:05:07.271225+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 97.5% [95% CI: 95.0% – 99.6%]
- **Overall Mean Conditional Cooperative Probability:** 0.809 [95% CI: 0.759 – 0.852]
- **Letter Validity Rate:** 100.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (2.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 100.0% valid letters.
  - Positional robustness acceptable: positional spread is 0.8% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |         0.975 |     0.80867 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |          1    |    0.845538 |
| human          |          0.95 |    0.771803 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |              0.975 |          0.80867 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 97.5% [95% CI: 95.0% – 99.6%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **97.9%** [95% CI: 93.8% – 100.0%] (Coop: 99.0%, Indep: 1.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **2.676** [95% CI: 2.378 – 2.962]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **97.9%** [95% CI: 93.8% – 100.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **2.676** [95% CI: 2.378 – 2.962]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 91.7%, Indep Rate: 6.2% (Diff: 85.4%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 1.234

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |              0.975 |           0.0208333 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 24.6%
- **B:** 25.4%
- **C:** 25.4%
- **D:** 24.6%
- **Positional Spread (Max - Min):** 0.8%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 97.5%
- **Independent:** 2.1%
- **Compete / Exploit:** 0.0%
- **Disengage:** 0.4%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
