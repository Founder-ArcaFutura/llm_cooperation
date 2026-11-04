# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-04T22:58:17.867932+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 55.0% [95% CI: 47.9% – 61.7%]
- **Overall Mean Conditional Cooperative Probability:** 0.296 [95% CI: 0.287 – 0.305]
- **Letter Validity Rate:** 2.1%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (22.1%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 2.1% is below 50%.
  - Severe positional sensitivity: positional spread is 42.1% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |          0.55 |    0.296328 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.616667 |    0.303562 |
| human          |      0.483333 |    0.289095 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |               0.55 |         0.296328 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 55.0% [95% CI: 47.9% – 61.7%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **38.5%** [95% CI: 27.1% – 50.0%] (Coop: 55.7%, Indep: 17.2%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.214** [95% CI: 0.171 – 0.257]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **38.5%** [95% CI: 27.1% – 50.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.214** [95% CI: 0.171 – 0.257]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 52.1%, Indep Rate: 14.6% (Diff: 37.5%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.206

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |               0.55 |            0.166667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 33.3%
- **B:** 8.8%
- **C:** 7.9%
- **D:** 50.0%
- **Positional Spread (Max - Min):** 42.1%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 55.0%
- **Independent:** 16.7%
- **Compete / Exploit:** 22.1%
- **Disengage:** 6.2%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
