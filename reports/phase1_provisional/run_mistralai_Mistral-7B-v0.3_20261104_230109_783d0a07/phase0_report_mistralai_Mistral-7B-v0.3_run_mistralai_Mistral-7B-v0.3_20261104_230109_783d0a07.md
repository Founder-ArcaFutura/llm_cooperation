# Phase 0 Behavioral Screen Report
**Model:** `mistralai/Mistral-7B-v0.3`
**Date:** 2026-11-04T23:01:09.286789+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 98.3% [95% CI: 96.7% – 99.6%]
- **Overall Mean Conditional Cooperative Probability:** 0.620 [95% CI: 0.568 – 0.666]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Disengage` (0.8%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 1.3% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |      0.983333 |    0.620183 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      1        |    0.652165 |
| human          |      0.966667 |    0.5882   |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |           0.983333 |         0.620183 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 98.3% [95% CI: 96.7% – 99.6%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **99.0%** [95% CI: 97.4% – 100.0%] (Coop: 99.0%, Indep: 0.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.758** [95% CI: 1.500 – 1.995]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **99.0%** [95% CI: 97.4% – 100.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **1.758** [95% CI: 1.500 – 1.995]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 95.8%, Indep Rate: 2.1% (Diff: 93.8%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.690

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |           0.983333 |          0.00416667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 25.8%
- **B:** 24.6%
- **C:** 24.6%
- **D:** 25.0%
- **Positional Spread (Max - Min):** 1.3%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 98.3%
- **Independent:** 0.4%
- **Compete / Exploit:** 0.4%
- **Disengage:** 0.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
