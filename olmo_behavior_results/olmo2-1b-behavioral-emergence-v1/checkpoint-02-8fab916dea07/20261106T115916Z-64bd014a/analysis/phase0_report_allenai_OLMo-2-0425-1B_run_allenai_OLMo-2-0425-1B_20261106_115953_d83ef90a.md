# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-06T11:59:53.852784+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 25.4% [95% CI: 23.3% – 27.9%]
- **Overall Mean Conditional Cooperative Probability:** 0.250 [95% CI: 0.248 – 0.251]
- **Letter Validity Rate:** 3.8%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (28.3%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 3.8% is below 50%.
  - Severe positional sensitivity: positional spread is 72.1% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |        0.3125 |     0.24989 |
| neutral_or_costless |        0.25   |     0.24979 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.266667 |    0.250475 |
| human          |      0.241667 |    0.249119 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.254167 |         0.249797 |

- **Exploratory Split (N=30 templates):** Coop Rate: 25.4% [95% CI: 23.3% – 27.9%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **-3.8%** [95% CI: -7.2% – -1.0%] (Coop: 24.5%, Indep: 28.4%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.020** [95% CI: -0.034 – -0.006]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **-3.8%** [95% CI: -7.2% – -1.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.020** [95% CI: -0.034 – -0.006]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 31.2%
  - Coop Rate Matched Equal (Within-Triad Baseline): 25.0%
  - Coop Rate Disadvantageous: 31.2%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 0.0% (Monotonic: False)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.254167 |               0.275 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 72.1%
- **B:** 0.0%
- **C:** 0.0%
- **D:** 27.9%
- **Positional Spread (Max - Min):** 72.1%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 25.4%
- **Independent:** 27.5%
- **Compete / Exploit:** 28.3%
- **Disengage:** 18.8%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
