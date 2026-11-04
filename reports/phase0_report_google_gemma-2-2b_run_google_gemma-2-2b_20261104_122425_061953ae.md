# Phase 0 Behavioral Screen Report
**Model:** `google/gemma-2-2b`
**Date:** 2026-11-04T12:24:25.115865+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 124 (496 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 67.9% [95% CI: 62.5% – 73.4%]
- **Overall Mean Conditional Cooperative Probability:** 0.327 [95% CI: 0.315 – 0.341]
- **Letter Validity Rate:** 33.5%
- **Preferred Non-Cooperative Alternative:** `Disengage` (14.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 33.5% is below 50%.
  - Moderate positional bias: positional spread is 32.1% (>25%).

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.78125  |    0.341528 |
| neutral_or_costless |      0.672414 |    0.32638  |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.717742 |    0.33648  |
| human          |      0.641129 |    0.318234 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          64 |             0.625  |         0.31373  |
| exploratory  |          60 |             0.7375 |         0.341892 |

- **Exploratory Split (N=30 templates):** Coop Rate: 73.8% [95% CI: 65.8% – 81.2%]
- **Held-Out Confirmatory Split (N=32 templates):** Coop Rate: 62.5% [95% CI: 55.1% – 69.5%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=26 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **55.8%** [95% CI: 46.6% – 64.4%] (Coop: 63.5%, Indep: 7.7%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.329** [95% CI: 0.264 – 0.403]
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **64.4%** [95% CI: 54.8% – 74.5%] (Coop: 70.2%, Indep: 5.8%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.400** [95% CI: 0.307 – 0.498]
- **Pooled Bank Reference Contrast (All N=52 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **60.1%** [95% CI: 53.6% – 66.8%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.364** [95% CI: 0.307 – 0.429]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=4 Triads):**
  - Coop Rate Advantageous: 93.8%
  - Coop Rate Matched Equal (Within-Triad Baseline): 81.2%
  - Coop Rate Disadvantageous: 78.1%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 15.6% (Monotonic: True)

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=4 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 25.0%, Indep Rate: 37.5% (Diff: -12.5%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.039

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| control       |           4 |             0.25   |           0.375     |
| new           |          60 |             0.65   |           0.0833333 |
| reused        |          60 |             0.7375 |           0.0541667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 496 counterbalanced presentations:
- **A:** 38.1%
- **B:** 28.8%
- **C:** 6.0%
- **D:** 27.0%
- **Positional Spread (Max - Min):** 32.1%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 67.9%
- **Independent:** 7.9%
- **Compete / Exploit:** 10.1%
- **Disengage:** 14.1%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
