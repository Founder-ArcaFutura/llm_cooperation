# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-1124-7B`
**Date:** 2026-11-06T12:34:25.435351+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 60 (240 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 25.0% [95% CI: 25.0% – 25.0%]
- **Overall Mean Conditional Cooperative Probability:** 0.248 [95% CI: 0.246 – 0.250]
- **Letter Validity Rate:** 0.0%
- **Preferred Non-Cooperative Alternative:** `Independent` (25.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 0.0% is below 50%.
  - Severe positional sensitivity: positional spread is 100.0% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type        |   mean_argmax |   mean_prob |
|:--------------------|--------------:|------------:|
| modest_cost         |          0.25 |    0.249558 |
| neutral_or_costless |          0.25 |    0.247909 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |          0.25 |    0.247577 |
| human          |          0.25 |    0.248461 |

### Dataset Split & Confirmatory Isolation (§3)
| split       |   scenarios |   mean_coop_argmax |   mean_coop_prob |
|:------------|------------:|-------------------:|-----------------:|
| exploratory |          60 |               0.25 |         0.248019 |

- **Exploratory Split (N=30 templates):** Coop Rate: 25.0% [95% CI: 25.0% – 25.0%]

*(Note: Confirmatory split is held-out and isolated from item optimization or prompt tuning. The confirmatory contrast is the preregistered test.)*


### Phase 0B: Utility-Matched Construct Validation Contrasts
- **Exploratory Utility-Matched Contrast (Rewritten Existing Templates, N=26) [Descriptive / Baseline]:**
  - Choice Rate Difference (COOP - INDEP): **0.0%** [95% CI: 0.0% – 0.0%] (Coop: 25.0%, Indep: 25.0%)
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.016** [95% CI: -0.031 – 0.000]
- **Pooled Bank Reference Contrast (All N=26 Utility-Matched Templates) [Combined Reference]:**
  - Choice Rate Difference (COOP - INDEP): **0.0%** [95% CI: 0.0% – 0.0%]
  - Log-Probability Difference [log P(COOP) - log P(INDEP)]: **-0.016** [95% CI: -0.031 – 0.000]

- **Controlled Utility Sensitivity Triad (Within-Triad Paired Effects, N=2 Triads):**
  - Coop Rate Advantageous: 25.0%
  - Coop Rate Matched Equal (Within-Triad Baseline): 25.0%
  - Coop Rate Disadvantageous: 25.0%
  - Mean Paired Sensitivity Spread (Adv - Disadv): 0.0% (Monotonic: True)

#### Source Type Breakdown (Reused vs New Templates)
| source_type   |   scenarios |   mean_coop_argmax |   mean_indep_argmax |
|:--------------|------------:|-------------------:|--------------------:|
| reused        |          60 |               0.25 |                0.25 |


---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 240 counterbalanced presentations:
- **A:** 100.0%
- **B:** 0.0%
- **C:** 0.0%
- **D:** 0.0%
- **Positional Spread (Max - Min):** 100.0%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 25.0%
- **Independent:** 25.0%
- **Compete / Exploit:** 25.0%
- **Disengage:** 25.0%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
