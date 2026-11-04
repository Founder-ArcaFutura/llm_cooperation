# Phase 0 Behavioral Screen Report
**Model:** `allenai/OLMo-2-0425-1B`
**Date:** 2026-11-04T01:42:21.337826+00:00
**Git Commit:** `None`
**Scenarios Evaluated (N):** 24 (96 total counterbalanced presentations)

---

## 1. Executive Summary & Diagnostic Assessment
- **Gate Recommendation (§4A.4):** **STOP / REVISE ELICITATION**: Format compliance failure (<50% valid letters). Model completion format failed.
- **Overall Cooperative Selection Rate (Forced-Choice Argmax):** 46.9% [95% CI: 37.5% – 56.2%]
- **Overall Mean Conditional Cooperative Probability:** 0.275 [95% CI: 0.263 – 0.287]
- **Letter Validity Rate:** 2.1%
- **Preferred Non-Cooperative Alternative:** `Independent` (24.0%)
- **Execution Mode:** `REAL`

### Evidence Summary
- **Supporting Observations:**
  - None identified
- **Contradicting / Limitation Observations:**
  - Format compliance failure: valid letter rate 2.1% is below 50%.
  - Severe positional sensitivity: positional spread is 41.7% (>40%). Order artifact dominates choice.

*(Note: 25.0% is shown as a mathematical uniform reference for 4 alternatives, not a presumed naturalistic null.)*

---

## 2. Subgroup Strata Breakdown

### Context / Cost Strata Breakdown
| context_type                 |   mean_argmax |   mean_prob |
|:-----------------------------|--------------:|------------:|
| conflict_with_objective      |      0.291667 |    0.23928  |
| ineffective_or_inappropriate |      0.458333 |    0.269072 |
| modest_cost                  |      0.541667 |    0.303761 |
| neutral_or_costless          |      0.583333 |    0.287367 |

### Partner Type Breakdown (Human vs AI)
| partner_type   |   mean_argmax |   mean_prob |
|:---------------|--------------:|------------:|
| ai             |      0.479167 |    0.279087 |
| human          |      0.458333 |    0.270652 |

---

## 3. Position Bias Audit (§4A.3)
Presentation frequency of chosen letters across all 96 counterbalanced presentations:
- **A:** 39.6%
- **B:** 3.1%
- **C:** 44.8%
- **D:** 12.5%
- **Positional Spread (Max - Min):** 41.7%

---

## 4. Alternative Strategies Distribution
- **Cooperate:** 46.9%
- **Independent:** 24.0%
- **Compete / Exploit:** 14.6%
- **Disengage:** 14.6%

---

## 5. Scientific Claim Boundary (§13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
