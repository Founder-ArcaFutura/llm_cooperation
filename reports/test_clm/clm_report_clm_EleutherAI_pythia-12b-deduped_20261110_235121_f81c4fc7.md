# Continuation-Likelihood Cooperation Assay: Results

> **Research status**: exploratory  
> **Model**: `EleutherAI/pythia-12b-deduped`  
> **Run ID**: `clm_EleutherAI_pythia-12b-deduped_20261110_235121_f81c4fc7`  
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
| COOPERATE | 23.3 | 41.7 | 20.0 | 15.0 |
| INDEPENDENT | 20.0 | 30.0 | 35.0 | 15.0 |
| COMPETE_EXPLOIT | 41.7 | 15.0 | 23.3 | 20.0 |
| DISENGAGE | 15.0 | 13.3 | 21.7 | 50.0 |

## 2. Cooperation Preference Summary

- Scenarios where COOPERATE ranks first (by sum log-P): **21.7%**
- Scenarios where COOPERATE ranks first (by mean log-P): **100.0%**

## 3. Log-Probability Margins (bootstrap 95% CI, scenario-clustered)

| Comparison | Mean delta | 95% CI lower | 95% CI upper | N scenarios |
| --- | --- | --- | --- | --- |
| COOP vs INDEPENDENT | 0.299 | -0.196 | 0.787 | 60 |
| COOP vs COMPETE | 0.340 | -0.566 | 1.316 | 60 |

## 4. Length Information

Mean number of tokens per strategy (affects sum log-probability):

| Strategy | Mean tokens |
| --- | --- |
| COOPERATE | 20.9 |
| INDEPENDENT | 18.9 |
| COMPETE_EXPLOIT | 16.1 |
| DISENGAGE | 15.2 |

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