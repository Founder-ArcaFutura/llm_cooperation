# Phase 0 Behavioral Screen Report
**Model:** `google/gemma-2-2b`
**Date:** 2026-11-04T23:08:41.661766+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 49.2% [95% CI: 41.7% – 57.1%]
- **Overall Mean Conditional Cooperative Probability:** 0.292 [95% CI: 0.283 – 0.304]
- **Letter Validity Rate:** 42.5%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (20.4%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 42.5% is below 50%.
  - Severe positional sensitivity: positional spread is 60.4% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| neutral_or_costless |      0.491667 |    0.292495 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.541667 |    0.302092 |
| human          |      0.441667 |    0.282897 |

### Dataset Split & Confirmatory Isolation (§3)
| split        |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:-------------|------------:|-------------------:|-----------------:|
| confirmatory |          60 |           0.491667 |         0.292495 |

- **Held-Out Confirmatory Split (N=30 templates):** Coop Rate: 49.2% [95% CI: 41.7% – 57.1%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Preregistered Primary Utility-Matched Contrast (Held-Out Confirmatory Partition, N=24 New Templates) [FORMAL REPLICATION TEST]:**
  - Choice Rate Difference (COOP - INDEP): **38.5%** [95% CI: 27.6% – 50.0%] (Coop: 49.5%, Indep: 10.9%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.203** [95% CI: 0.162 – 0.243]
- **Pooled Bank Reference Contrast (All N=24 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **38.5%** [95% CI: 27.6% – 50.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.203** [95% CI: 0.162 – 0.243]

- **Symmetric Outcome Control Subset (Coordination vs Welfare Maximization, N=12 Scenarios):**
  *(Actor and partner outcomes identical under both COOPERATE and INDEPENDENT)*
  - Coop Choice Rate: 47.9%, Indep Rate: 20.8% (Diff: 27.1%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: 0.227

#### Source Type Breakdown (Reused vs New Templates)
| source_type             |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:------------------------|------------:|-------------------:|--------------------:|
| prospective_replication |          60 |           0.491667 |            0.129167 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 61.7%
- **B:** 17.9%
- **C:** 1.2%
- **D:** 19.2%
- **Positional Spread (Max - Min):** 60.4%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 49.2%
- **Independent:** 12.9%
- **Compete / Exploit:** 20.4%
- **Disengage:** 17.5%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
