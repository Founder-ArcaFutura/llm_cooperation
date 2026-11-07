# Phase 0 Behavioral Screen Report
**Model:** `google/gemma-2-9b`
**Date:** 2026-11-04T12:20:55.616736+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 124 (496 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 94.6% [95% CI: 90.5% – 97.8%]
- **Overall Mean Conditional Cooperative Probability:** 0.540 [95% CI: 0.514 – 0.566]
- **Letter Validity Rate:** 6.5%
- **Preferred Non-Cooperative Alternative:** `Independent` (4.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 1.8% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 6.5% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.59375  |    0.350923 |
| neutral_or_costless |      0.969828 |    0.552506 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.979839 |    0.570154 |
| human          |      0.91129  |    0.508846 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          64 |           0.9375   |         0.529053 |
| exploratory  |          60 |           0.954167 |         0.550644 |

- **Exploratory Split (N=30 templates):** Coop Rate: 95.4% [95% CI: 91.2% – 98.3%]
- **Held-Out Confirmatory Split (N=32 templates):** Coop Rate: 93.8% [95% CI: 87.1% – 98.8%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=26 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **92.8%** [95% CI: 80.8% – 100.0%] (Coop: 95.7%, Indep: 2.9%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.099** [95% CI: 0.931 – 1.252]
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **96.2%** [95% CI: 92.8% – 99.0%] (Coop: 97.6%, Indep: 1.4%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.219** [95% CI: 1.067 – 1.374]
- **Pooled Bank Reference Contrast (All N=52 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **94.5%** [95% CI: 88.7% – 98.6%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.159** [95% CI: 1.044 – 1.270]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=4 Triads):**
  - Coop Rate Advantageous: 100.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 93.8%
  - Coop Rate Disadvantageous: 59.4%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 40.6% (Monotonic: True)

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=4 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 100.0%, Indep Rate: 0.0% (Diff: 100.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.789

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| control       |           4 |           1        |           0         |
| new           |          60 |           0.933333 |           0.0541667 |
| reused        |          60 |           0.954167 |           0.0291667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 496 counterbalanced presentations:
- **A:** 25.0%
- **B:** 24.8%
- **C:** 24.2%
- **D:** 26.0%
- **Positional Spread (Max - Min):** 1.8%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 94.6%
- **Independent:** 4.0%
- **Compete / Exploit:** 0.6%
- **Disengage:** 0.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
