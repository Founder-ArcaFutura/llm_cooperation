# Phase 0 Behavioral Screen Report
**Model:** `ibm-granite/granite-3.3-2b-base`
**Date:** 2026-11-04T22:59:23.478822+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 73.3% [95% CI: 66.2% – 79.6%]
- **Overall Mean Conditional Cooperative Probability:** 0.538 [95% CI: 0.499 – 0.574]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (13.8%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.
  - Severe positional sensitivity: positional spread is 40.4% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |      0.733333 |     0.53777 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.833333 |    0.611579 |
| human          |      0.633333 |    0.46396  |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |           0.733333 |          0.53777 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 73.3% [95% CI: 66.2% – 79.6%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **65.1%** [95% CI: 57.8% – 72.9%] (Coop: 67.7%, Indep: 2.6%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.706** [95% CI: 1.469 – 1.947]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **65.1%** [95% CI: 57.8% – 72.9%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.706** [95% CI: 1.469 – 1.947]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 95.8%, Indep Rate: 0.0% (Diff: 95.8%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 1.128

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |           0.733333 |           0.0208333 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 50.0%
- **B:** 17.5%
- **C:** 9.6%
- **D:** 22.9%
- **Positional Spread (Max - Min):** 40.4%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 73.3%
- **Independent:** 2.1%
- **Compete / Exploit:** 13.8%
- **Disengage:** 10.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
