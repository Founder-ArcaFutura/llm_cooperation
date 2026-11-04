# Phase 0 Behavioral Screen Report
**Model:** `meta-llama/Llama-3.2-3B`
**Date:** 2026-11-04T12:14:41.219763+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 124 (496 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **QUALITATIVE REVIEW WARRANTED (SINGLE MODEL)**: Apparent cooperative tendency with acceptable format compliance and positional robustness. Per protocol §8 & §10, individual models cannot trigger automatic scientific advancement; requires independent cross-family human review.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 81.5% [95% CI: 76.6% – 86.1%]
- **Overall Mean Conditional Cooperative Probability:** 0.461 [95% CI: 0.434 – 0.489]
- **Letter Validity Rate:** 100.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (10.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Format compliance acceptable: 100.0% valid letters.
  - Positional robustness acceptable: positional spread is 11.7% (<=25%).
- **Contradicting / Limitation Observations:**
  - None identified

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.46875  |    0.294047 |
| neutral_or_costless |      0.838362 |    0.47289  |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.903226 |    0.510978 |
| human          |      0.725806 |    0.411726 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          64 |           0.8125   |         0.471791 |
| exploratory  |          60 |           0.816667 |         0.450216 |

- **Exploratory Split (N=30 templates):** Coop Rate: 81.7% [95% CI: 75.4% – 87.9%]
- **Held-Out Confirmatory Split (N=32 templates):** Coop Rate: 81.2% [95% CI: 73.4% – 88.3%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=26 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **72.1%** [95% CI: 60.1% – 82.7%] (Coop: 82.7%, Indep: 10.6%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.859** [95% CI: 0.660 – 1.056]
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **75.5%** [95% CI: 66.3% – 83.7%] (Coop: 83.7%, Indep: 8.2%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.776** [95% CI: 0.620 – 0.922]
- **Pooled Bank Reference Contrast (All N=52 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **73.8%** [95% CI: 66.6% – 80.8%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.818** [95% CI: 0.696 – 0.950]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=4 Triads):**
  - Coop Rate Advantageous: 84.4%
  - Coop Rate Matched Equal (Within-Triad Baseline): 71.9%
  - Coop Rate Disadvantageous: 46.9%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 37.5% (Monotonic: True)

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=4 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 100.0%, Indep Rate: 0.0% (Diff: 100.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.922

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| control       |           4 |           1        |           0         |
| new           |          60 |           0.8      |           0.116667  |
| reused        |          60 |           0.816667 |           0.0916667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 496 counterbalanced presentations:
- **A:** 33.3%
- **B:** 21.6%
- **C:** 23.4%
- **D:** 21.8%
- **Positional Spread (Max - Min):** 11.7%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 81.5%
- **Independent:** 10.1%
- **Compete / Exploit:** 6.7%
- **Disengage:** 1.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
