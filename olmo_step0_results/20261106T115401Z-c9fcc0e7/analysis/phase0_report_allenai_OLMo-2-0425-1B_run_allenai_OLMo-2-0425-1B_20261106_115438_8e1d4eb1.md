# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-06T11:54:38.098381+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 23.8% [95% CI: 20.0% – 27.5%]
- **Overall Mean Conditional Cooperative Probability:** 0.251 [95% CI: 0.241 – 0.260]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (30.8%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - Positional robustness acceptable: positional spread is 18.8% (<=25%).
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.25     |    0.256791 |
| neutral_or_costless |      0.236607 |    0.250233 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |         0.25  |     0.25059 |
| human          |         0.225 |     0.25075 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |             0.2375 |          0.25067 |

- **Exploratory Split (N=30 templates):** Coop Rate: 23.8% [95% CI: 20.0% – 27.5%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **0.5%** [95% CI: -7.2% – 8.2%] (Coop: 23.6%, Indep: 23.1%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.001** [95% CI: -0.072 – 0.067]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **0.5%** [95% CI: -7.2% – 8.2%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.001** [95% CI: -0.072 – 0.067]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 25.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 31.2%
  - Coop Rate Disadvantageous: 25.0%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 0.0% (Monotonic: False)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |             0.2375 |               0.225 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 32.1%
- **B:** 15.4%
- **C:** 18.3%
- **D:** 34.2%
- **Positional Spread (Max - Min):** 18.8%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 23.8%
- **Independent:** 22.5%
- **Compete / Exploit:** 30.8%
- **Disengage:** 22.9%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
