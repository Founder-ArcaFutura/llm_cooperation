# Continuation-Likelihood Cooperation Assay: Results

> **Research status**: exploratory  
> **Model**: `Qwen/Qwen2.5-3B`  
> **Run ID**: `clm_Qwen_Qwen2.5-3B_20261111_001736_806ddcc2`  
> **Scenarios evaluated**: 60  
> **Templates**: next_action, course_of_action, next_step  

> [!IMPORTANT]
> This assay measures conditional language probability, not agent intent.
> Results are exploratory. Do not interpret as confirmatory evidence.

## 1. Strategy Rank Distributions

Percentage of scenarios in which each strategy ranks at each position
(ranking by average sum log-probability across templates):

| Strategy | Rank 1 (%) | Rank 2 (%) | Rank 3 (%) | Rank 4 (%) |
| --- | --- | --- | --- | --- |
| COOPERATE | 90.0 | 6.7 | 3.3 | 0.0 |
| INDEPENDENT | 0.0 | 1.7 | 15.0 | 83.3 |
| COMPETE_EXPLOIT | 5.0 | 16.7 | 61.7 | 16.7 |
| DISENGAGE | 5.0 | 75.0 | 20.0 | 0.0 |

## 2. Cooperation Preference Summary

- Scenarios where COOPERATE ranks first (by sum log-P): **90.0%**
- Scenarios where COOPERATE ranks first (by mean log-P): **95.0%**

## 3. Log-Probability Margins (bootstrap 95% CI, scenario-clustered)

| Comparison | Mean delta | 95% CI lower | 95% CI upper | N scenarios |
| --- | --- | --- | --- | --- |
| COOP vs INDEPENDENT | 38.101 | 35.510 | 40.533 | 60 |
| COOP vs COMPETE | 24.170 | 20.903 | 27.528 | 60 |

## 4. Length Information

Mean number of tokens per strategy (affects sum log-probability):

| Strategy | Mean tokens |
| --- | --- |
| COOPERATE | 20.0 |
| INDEPENDENT | 17.3 |
| COMPETE_EXPLOIT | 16.0 |
| DISENGAGE | 15.7 |

> Length differences between strategies may confound sum log-probability rankings. Use mean log-probability as a cross-length reference but do not treat it as an unbiased estimator.

## 5. Methodological Limitations

- Continuation likelihood reflects the model's learned language distribution,
  not an explicit behavioral choice.
- Length differences between strategies confound sum log-probability rankings.
- Template framing may interact with strategy descriptions.
- Results may reflect grammaticality, fluency, or frequency differences
  that are independent of cooperative intent.
- A positive cooperative preference signal requires robustness under
  lexical and template controls before scientific interpretation.