# Phase 0 Behavioral Screen Report
**Model:** `microsoft/phi-2`
**Date:** 2026-11-04T12:12:21.923873+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 124 (496 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 92.9% [95% CI: 87.5% – 97.6%]
- **Overall Mean Conditional Cooperative Probability:** 0.658 [95% CI: 0.620 – 0.693]
- **Letter Validity Rate:** 8.7%
- **Preferred Non-Cooperative Alternative:** `Independent` (3.6%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 6.0% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 8.7% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.375    |    0.343071 |
| neutral_or_costless |      0.967672 |    0.679675 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.951613 |    0.707142 |
| human          |      0.907258 |    0.608775 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          64 |           0.925781 |         0.645615 |
| exploratory  |          60 |           0.933333 |         0.671125 |

- **Exploratory Split (N=30 templates):** Coop Rate: 93.3% [95% CI: 85.8% – 99.2%]
- **Held-Out Confirmatory Split (N=32 templates):** Coop Rate: 92.6% [95% CI: 84.4% – 98.4%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=26 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **91.8%** [95% CI: 83.7% – 98.1%] (Coop: 94.7%, Indep: 2.9%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.713** [95% CI: 1.453 – 1.973]
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **97.6%** [95% CI: 93.3% – 100.0%] (Coop: 98.1%, Indep: 0.5%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.966** [95% CI: 1.784 – 2.157]
- **Pooled Bank Reference Contrast (All N=52 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **94.7%** [95% CI: 89.9% – 98.6%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.840** [95% CI: 1.673 – 2.001]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=4 Triads):**
  - Coop Rate Advantageous: 100.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 87.5%
  - Coop Rate Disadvantageous: 37.5%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 62.5% (Monotonic: True)

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=4 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 100.0%, Indep Rate: 0.0% (Diff: 100.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 1.328

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| control       |           4 |           1        |           0         |
| new           |          60 |           0.920833 |           0.0583333 |
| reused        |          60 |           0.933333 |           0.0166667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 496 counterbalanced presentations:
- **A:** 28.8%
- **B:** 24.4%
- **C:** 22.8%
- **D:** 24.0%
- **Positional Spread (Max - Min):** 6.0%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 92.9%
- **Independent:** 3.6%
- **Compete / Exploit:** 1.8%
- **Disengage:** 1.6%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
