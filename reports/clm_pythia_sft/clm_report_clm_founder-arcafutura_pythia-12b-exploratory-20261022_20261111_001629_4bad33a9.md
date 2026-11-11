# Continuation-Likelihood Cooperation Assay: Results

> **Research status**: exploratory  
> **Model**: `founder-arcafutura/pythia-12b-exploratory-20261022`  
> **Run ID**: `clm_founder-arcafutura_pythia-12b-exploratory-20261022_20261111_001629_4bad33a9`  
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
| COOPERATE | 91.7 | 5.0 | 3.3 | 0.0 |
| INDEPENDENT | 0.0 | 0.0 | 21.7 | 78.3 |
| COMPETE_EXPLOIT | 3.3 | 13.3 | 61.7 | 21.7 |
| DISENGAGE | 5.0 | 81.7 | 13.3 | 0.0 |

## 2. Cooperation Preference Summary

- Scenarios where COOPERATE ranks first (by sum log-P): **91.7%**
- Scenarios where COOPERATE ranks first (by mean log-P): **96.7%**

## 3. Log-Probability Margins (bootstrap 95% CI, scenario-clustered)

| Comparison | Mean delta | 95% CI lower | 95% CI upper | N scenarios |
| --- | --- | --- | --- | --- |
| COOP vs INDEPENDENT | 37.119 | 34.630 | 39.571 | 60 |
| COOP vs COMPETE | 25.177 | 21.576 | 28.750 | 60 |

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