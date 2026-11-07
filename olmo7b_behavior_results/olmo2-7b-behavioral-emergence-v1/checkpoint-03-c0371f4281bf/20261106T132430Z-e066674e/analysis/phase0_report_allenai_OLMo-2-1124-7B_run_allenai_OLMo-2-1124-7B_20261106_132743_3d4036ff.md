# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-1124-7B`
**Date:** 2026-11-06T13:27:43.098142+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 73.3% [95% CI: 65.4% – 81.2%]
- **Overall Mean Conditional Cooperative Probability:** 0.404 [95% CI: 0.371 – 0.438]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (10.4%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 22.9% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.3125   |    0.239912 |
| neutral_or_costless |      0.763393 |    0.41576  |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.816667 |    0.431878 |
| human          |      0.65     |    0.376196 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.733333 |         0.404037 |

- **Exploratory Split (N=30 templates):** Coop Rate: 73.3% [95% CI: 65.4% – 81.2%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **67.8%** [95% CI: 56.7% – 77.9%] (Coop: 75.0%, Indep: 7.2%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.790** [95% CI: 0.633 – 0.966]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **67.8%** [95% CI: 56.7% – 77.9%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.790** [95% CI: 0.633 – 0.966]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 93.8%
  - Coop Rate Matched Equal (Within-Triad Baseline): 81.2%
  - Coop Rate Disadvantageous: 31.2%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 62.5% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.733333 |           0.0791667 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 40.4%
- **B:** 17.9%
- **C:** 17.5%
- **D:** 24.2%
- **Positional Spread (Max - Min):** 22.9%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 73.3%
- **Independent:** 7.9%
- **Compete / Exploit:** 10.4%
- **Disengage:** 8.3%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
