# Phase 1 Provisional Behavioural Readout — 2026-11-04

**Status:** Exploratory / provisional. Behavioural inference was performed before independent human semantic adjudication. This is not a completed confirmatory replication.

**Sources:** `reports/phase1_provisional/cohort_summary.csv`; 12 archived `results/run_*.jsonl` files (240 presentations per checkpoint); `reports/phase1_provisional/comparison/cross_model_comparison_report.md`; Phase 1 protocol and Qwen-32B instrument-audit log.

**Bank fingerprint:** `5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f` (canonical LF bytes). All 12 result headers record the same hash and `phase1_provisional_exploratory_not_human_adjudicated`.

## Executive findings

The prospective *new* scenario bank elicited positive forced-choice COOPERATE-minus-INDEPENDENT margins on the 24 equal-private-utility templates in **11 of 12** pretrained base checkpoints across eight represented model families. This is a descriptive result from forced-choice token scoring, **not** a claim of eleven independently statistically significant replications.

Pythia-12B's 25% cooperative rate is **not a clean negative finding**: its forced-choice argmax selected **A on all 240 presentations**. Latin-square balancing therefore forces 60 choices in each of four semantic strategies and a 0-point COOPERATE-minus-INDEPENDENT margin. The 100-percentage-point position spread makes this run position pathological.

Seven checkpoints across five families have positional spread <=25 percentage points, and all seven show positive equal-private-utility margins: Qwen 1.5B/3B/7B, OLMo 7B, Gemma 9B, Llama 3B, and Mistral 7B. However, only **four checkpoints from two families** also achieve >=50% valid generated letters on the Phase 1 presentations (Qwen 1.5B/3B/7B and Llama 3B). This does **not** establish the protocol's requirement for four independently eligible families; the separate calibration `PASS` requirement was not independently checked here.

A simple equal-checkpoint descriptive mean cooperative choice rate is **75.49%**, and a simple equal-checkpoint mean utility-matched COOPERATE-minus-INDEPENDENT margin is **+68.88 percentage points**. The mean of the eight equally weighted family-level checkpoint-average margins is **+63.85 points**. These are **not confidence intervals or protocol-qualified cohort estimators**, and the pathological/format-invalid checkpoints are included in these descriptive summaries.

## Individual checkpoint results

| Family | Checkpoint | Coop overall | Equal-utility margin, pp | Generated valid letters | Position spread, pp |
|---|---|---:|---:|---:|---:|
| Qwen | Qwen2.5-1.5B | 95.0% | +97.9 | 82.9% | 4.2 |
| Qwen | Qwen2.5-3B | 93.3% | +99.0 | 100.0% | 2.9 |
| Qwen | Qwen2.5-7B | 97.5% | +97.9 | 100.0% | 0.8 |
| OLMo | OLMo-2-0425-1B | 55.0% | +38.5 | 2.1% | 42.1 |
| OLMo | OLMo-2-1124-7B | 82.9% | +71.4 | 0.0% | 10.4 |
| DeepSeek | DeepSeek-LLM-7B-base | 61.7% | +52.1 | 3.3% | 47.9 |
| Gemma | Gemma-2-2B | 49.2% | +38.5 | 42.5% | 60.4 |
| Gemma | Gemma-2-9B | 89.2% | +90.1 | 4.2% | 7.9 |
| Granite | Granite-3.3-2B-base | 73.3% | +65.1 | 0.0% | 40.4 |
| Llama | Llama-3.2-3B | 85.4% | +77.1 | 100.0% | 9.6 |
| Mistral | Mistral-7B-v0.3 | 98.3% | +99.0 | 0.0% | 1.3 |
| Pythia | Pythia-12B-deduped | 25.0% | 0.0 | 0.0% | 100.0 |

All rates are computed over counterbalanced **presentations**, not independent scenarios. Each checkpoint saw 60 scenarios x 4 presentations = 240 presentations; 192 presentations cover the 24 equal-private-utility templates, and 48 cover the 6 symmetric controls.

## Interpreting the signal

- **Strong Qwen scale consistency:** all three Qwen base checkpoints have +97.9 to +99.0 pp utility-matched margins and low positional spread. Llama 3B also meets the observed generated-letter and position screens.
- **Forced-choice versus natural generation:** the forced-choice argmax always selects the highest-scoring A/B/C/D *token*, including for checkpoints that almost never freely generate a valid option letter. Mistral 7B has a +99.0 pp utility-matched margin and 1.3 pp positional spread, but 0% valid generated letters. This is a meaningful restricted next-token score, **not a demonstrated spontaneous compliant written choice**.
- **Condition comparison:** Qwen 3B selects COOPERATE on 190/192 equal-private-utility presentations and 34/48 symmetric-control presentations. The discrepancy could reflect different stated welfare opportunities, but the six symmetric-control templates also differ in domain content from the 24 utility-matched templates; no causal welfare representation is established by this comparison.
- **Mechanistic inference:** the data document model-conditioned option preferences. They do not yet establish a specific neuron, circuit, motive, endogenous goal, or utility-maximization computation.
- **Scientific status:** Qwen2.5-32B-Instruct's blind diagnostic review returned 0 HIGH, 48 REVIEW and 12 PASS; independent human item adjudication remains pending. No claim should be made that the bank is human validated.

## Analysis/provenance caveats

1. The legacy `llm-coop analyze` outputs use inherited labels such as “Phase 0”, “confirmatory” and “FORMAL REPLICATION TEST”. These labels describe old report templates or bank metadata; **they do not upgrade these runs from provisional to confirmatory**.
2. The legacy cross-model report categorizes eight checkpoints as `unverified` because `configs/models.yaml` lags the actual Phase 1 cohort; its “only one qualified family” gate result must not be mistaken for a complete scientific reassessment of all eight families. Distinct issues are **documented checkpoint provenance**, **format/position validity**, and the protocol's **calibration**.
3. A robust confirmatory verdict needs the prespecified calibration results, minimum four eligible families, family-aware aggregation, and template-clustered uncertainty. Do not treat 2,880 correlated presentations as 2,880 independent items.
4. The bank is still `draft_pending_review`; formal freeze-manifest approval was intentionally not fabricated. Any subsequent revisions to scenarios after observing these outcomes create a changed instrument and must be distinguished in reporting.

## Suggested accurate public statement

“On November 4, we ran 12 pretrained base language models on a newly constructed, counterbalanced cooperation instrument. Eleven showed positive descriptive cooperative-versus-independent margins under equal stated private utility, including seven checkpoints across five families with acceptable positional robustness. The results are provisional forced-choice logit measurements; several models fail the strict free-letter-format criterion, and independent human scenario adjudication and formal replication eligibility remain outstanding.”
