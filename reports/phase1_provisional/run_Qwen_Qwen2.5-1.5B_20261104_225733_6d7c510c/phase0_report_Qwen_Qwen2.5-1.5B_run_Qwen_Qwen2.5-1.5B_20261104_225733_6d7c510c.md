# Phase 0 Behavioral Screen Report
**Model:** `Qwen/Qwen2.5-1.5B`
**Date:** 2026-11-04T22:57:33.838576+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 95.0% [95% CI: 90.8% – 98.8%]
- **Overall Mean Conditional Cooperative Probability:** 0.747 [95% CI: 0.693 – 0.798]
- **Letter Validity Rate:** 82.9%
- **Preferred Non-Cooperative Alternative:** `Disengage` (2.9%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 82.9% valid letters.
  - Positional robustness acceptable: positional spread is 4.2% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |          0.95 |    0.747305 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.991667 |    0.801504 |
| human          |      0.908333 |    0.693107 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |               0.95 |         0.747305 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 95.0% [95% CI: 90.8% – 98.8%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **97.9%** [95% CI: 95.3% – 100.0%] (Coop: 97.9%, Indep: 0.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **2.969** [95% CI: 2.622 – 3.281]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **97.9%** [95% CI: 95.3% – 100.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **2.969** [95% CI: 2.622 – 3.281]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 83.3%, Indep Rate: 2.1% (Diff: 81.2%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 1.331

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |               0.95 |          0.00416667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 27.5%
- **B:** 23.3%
- **C:** 23.3%
- **D:** 25.8%
- **Positional Spread (Max - Min):** 4.2%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 95.0%
- **Independent:** 0.4%
- **Compete / Exploit:** 1.7%
- **Disengage:** 2.9%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
