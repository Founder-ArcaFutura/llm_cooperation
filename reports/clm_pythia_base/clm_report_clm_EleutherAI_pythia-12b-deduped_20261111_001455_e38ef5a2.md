# Continuation-Likelihood Cooperation Assay: Results

> **Research status**: exploratory  
> **Model**: `EleutherAI/pythia-12b-deduped`  
> **Run ID**: `clm_EleutherAI_pythia-12b-deduped_20261111_001455_e38ef5a2`  
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
| COOPERATE | 86.7 | 8.3 | 5.0 | 0.0 |
| INDEPENDENT | 0.0 | 0.0 | 11.7 | 88.3 |
| COMPETE_EXPLOIT | 5.0 | 15.0 | 68.3 | 11.7 |
| DISENGAGE | 8.3 | 76.7 | 15.0 | 0.0 |

## 2. Cooperation Preference Summary

- Scenarios where COOPERATE ranks first (by sum log-P): **86.7%**
- Scenarios where COOPERATE ranks first (by mean log-P): **95.0%**

## 3. Log-Probability Margins (bootstrap 95% CI, scenario-clustered)

| Comparison | Mean delta | 95% CI lower | 95% CI upper | N scenarios |
| --- | --- | --- | --- | --- |
| COOP vs INDEPENDENT | 34.172 | 31.855 | 36.432 | 60 |
| COOP vs COMPETE | 21.189 | 17.653 | 24.748 | 60 |

## 4. Length Information

Mean number of tokens per strategy (affects sum log-probability):

| Strategy | Mean tokens |
| --- | --- |
| COOPERATE | 20.7 |
| INDEPENDENT | 17.8 |
| COMPETE_EXPLOIT | 16.3 |
| DISENGAGE | 15.8 |

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