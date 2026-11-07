# Phase 0 Behavioral Screen Report
**Model:** `deepseek-ai/deepseek-llm-7b-base`
**Date:** 2026-11-04T12:03:34.579535+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 84.6% [95% CI: 77.5% – 91.2%]
- **Overall Mean Conditional Cooperative Probability:** 0.433 [95% CI: 0.407 – 0.460]
- **Letter Validity Rate:** 5.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (6.2%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 12.5% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 5.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.5625   |    0.317359 |
| neutral_or_costless |      0.866071 |    0.441455 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.883333 |    0.452729 |
| human          |      0.808333 |    0.413636 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.845833 |         0.433182 |

- **Exploratory Split (N=30 templates):** Coop Rate: 84.6% [95% CI: 77.5% – 91.2%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **79.3%** [95% CI: 68.8% – 88.9%] (Coop: 85.6%, Indep: 6.2%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.779** [95% CI: 0.655 – 0.904]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **79.3%** [95% CI: 68.8% – 88.9%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **0.779** [95% CI: 0.655 – 0.904]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 100.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 100.0%
  - Coop Rate Disadvantageous: 56.2%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 43.8% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.845833 |              0.0625 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 30.4%
- **B:** 20.4%
- **C:** 18.3%
- **D:** 30.8%
- **Positional Spread (Max - Min):** 12.5%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 84.6%
- **Independent:** 6.2%
- **Compete / Exploit:** 5.8%
- **Disengage:** 3.3%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
