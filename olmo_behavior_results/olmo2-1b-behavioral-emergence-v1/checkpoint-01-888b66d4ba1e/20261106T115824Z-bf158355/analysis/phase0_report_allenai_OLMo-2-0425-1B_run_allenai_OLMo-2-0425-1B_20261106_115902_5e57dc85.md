# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-06T11:59:02.627586+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 24.6% [95% CI: 23.8% – 25.0%]
- **Overall Mean Conditional Cooperative Probability:** 0.255 [95% CI: 0.253 – 0.256]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Compete / Exploit` (26.2%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.
  - Severe positional sensitivity: positional spread is 74.2% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |      0.25     |    0.263126 |
| neutral_or_costless |      0.245536 |    0.253887 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.25     |    0.25421  |
| human          |      0.241667 |    0.254796 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |           0.245833 |         0.254503 |

- **Exploratory Split (N=30 templates):** Coop Rate: 24.6% [95% CI: 23.8% – 25.0%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **0.0%** [95% CI: -1.9% – 2.4%] (Coop: 24.5%, Indep: 24.5%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.000** [95% CI: -0.012 – 0.012]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **0.0%** [95% CI: -1.9% – 2.4%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.000** [95% CI: -0.012 – 0.012]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 25.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 25.0%
  - Coop Rate Disadvantageous: 25.0%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 0.0% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |           0.245833 |            0.245833 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 74.2%
- **B:** 0.0%
- **C:** 0.0%
- **D:** 25.8%
- **Positional Spread (Max - Min):** 74.2%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 24.6%
- **Independent:** 24.6%
- **Compete / Exploit:** 26.2%
- **Disengage:** 24.6%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
