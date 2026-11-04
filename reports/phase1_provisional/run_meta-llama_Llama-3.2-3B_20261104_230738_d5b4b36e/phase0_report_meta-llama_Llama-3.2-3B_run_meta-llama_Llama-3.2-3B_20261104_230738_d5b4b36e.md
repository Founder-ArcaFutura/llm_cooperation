# Phase 0 Behavioral Screen Report
**Model:** `meta-llama/Llama-3.2-3B`
**Date:** 2026-11-04T23:07:38.069724+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 85.4% [95% CI: 79.2% – 90.8%]
- **Overall Mean Conditional Cooperative Probability:** 0.459 [95% CI: 0.426 – 0.489]
- **Letter Validity Rate:** 100.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (10.4%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 100.0% valid letters.
  - Positional robustness acceptable: positional spread is 9.6% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |      0.854167 |    0.458538 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.975    |    0.514547 |
| human          |      0.733333 |    0.402529 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |           0.854167 |         0.458538 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 85.4% [95% CI: 79.2% – 90.8%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **77.1%** [95% CI: 65.6% – 88.0%] (Coop: 86.5%, Indep: 9.4%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.827** [95% CI: 0.670 – 0.987]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **77.1%** [95% CI: 65.6% – 88.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.827** [95% CI: 0.670 – 0.987]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 81.2%, Indep Rate: 14.6% (Diff: 66.7%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.456

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |           0.854167 |            0.104167 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 30.0%
- **B:** 20.4%
- **C:** 26.7%
- **D:** 22.9%
- **Positional Spread (Max - Min):** 9.6%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 85.4%
- **Independent:** 10.4%
- **Compete / Exploit:** 3.8%
- **Disengage:** 0.4%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
