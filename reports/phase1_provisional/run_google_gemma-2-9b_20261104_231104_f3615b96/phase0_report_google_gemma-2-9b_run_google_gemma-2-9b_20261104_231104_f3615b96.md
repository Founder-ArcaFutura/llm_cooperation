# Phase 0 Behavioral Screen Report
**Model:** `google/gemma-2-9b`
**Date:** 2026-11-04T23:11:04.676211+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 89.2% [95% CI: 81.7% – 95.0%]
- **Overall Mean Conditional Cooperative Probability:** 0.533 [95% CI: 0.494 – 0.569]
- **Letter Validity Rate:** 4.2%
- **Preferred Non-Cooperative Alternative:** `Independent` (8.8%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 7.9% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 4.2% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |      0.891667 |    0.532504 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.941667 |    0.571346 |
| human          |      0.841667 |    0.493662 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |           0.891667 |         0.532504 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 89.2% [95% CI: 81.7% – 95.0%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **90.1%** [95% CI: 84.4% – 95.3%] (Coop: 93.8%, Indep: 3.6%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.146** [95% CI: 0.974 – 1.322]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **90.1%** [95% CI: 84.4% – 95.3%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.146** [95% CI: 0.974 – 1.322]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 70.8%, Indep Rate: 29.2% (Diff: 41.7%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.487

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |           0.891667 |              0.0875 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 25.0%
- **B:** 23.8%
- **C:** 21.7%
- **D:** 29.6%
- **Positional Spread (Max - Min):** 7.9%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 89.2%
- **Independent:** 8.8%
- **Compete / Exploit:** 0.8%
- **Disengage:** 1.2%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
