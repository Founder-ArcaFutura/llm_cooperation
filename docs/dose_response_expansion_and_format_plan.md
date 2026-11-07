# Dose-response expansion and base-model measurement plan

Prepared 2026-11-07. Exploratory continuation; no confirmatory holdout use.

## Execution and scope

The completed batch is `results/dose_response_batch/20261107_132150/batch_manifest.json`.
Reuse Qwen2.5-3B, Mistral-7B-v0.3 and OLMo-2-1124-7B from that batch.
The expansion adds ten previously screened checkpoints, giving thirteen checkpoints
across ten model families. Qwen sizes are related checkpoints, not independent families.
Selection is based on prior instrument behavior, never the direction of cooperation.
Pythia is excluded because the observed instrument response was invariant A; this
does not establish that the model lacks semantic ability under every elicitation.

| Additional checkpoint | Prior dominant-letter share | Prior position spread | Prior valid generated letters | Access |
|---|---:|---:|---:|---|
| SmolLM2-1.7B | 49.8% | 42.1 pp | 0.0% | Public |
| Granite-3.3-2B-base | 31.9% | 15.0 pp | 0.0% | Public |
| Falcon3-3B-Base | 32.5% | 12.7 pp | 0.0% | Public |
| Qwen2.5-1.5B | 29.4% | 8.5 pp | 94.6% | Public |
| Qwen2.5-7B | 33.3% | 14.4 pp | 88.1% | Public |
| DeepSeek-LLM-7B-base | 47.9% | 32.7 pp | 1.5% | Public |
| Phi-2 | 28.8% | 6.0 pp | 8.7% | Public |
| Llama-3.2-3B | 33.3% | 11.7 pp | 100.0% | Gated |
| Gemma-2-2B | 38.1% | 32.1 pp | 33.5% | Gated |
| Gemma-2-9B | 26.0% | 1.8 pp | 6.5% | Gated |

These rounded diagnostics come from the most recent complete 480/496-presentation
root `results/run_<model>_*.jsonl` screen, excluding provisional 240-presentation runs.
Exact source paths and recomputed values are in `configs/dose_response_expansion_inventory.json`.
SmolLM is a position-bias diagnostic, not an already validated instrument success.
DeepSeek and Gemma-2B also require position sensitivity analyses. Exclude severe
position failures from competence-qualified estimates without deleting their results.
OLMo-1B and Llama-3-8B have no complete 480/496 screen in this inventory and are
deferred rather than silently added to this cohort.

```powershell
# Offline inventory; no model calls or network access
.\scripts\run_dose_response_expansion.ps1 -IncludeGated -ListOnly

# Seven additional public checkpoints, sequentially
.\scripts\run_dose_response_expansion.ps1 -AuthorizePaidRun

# All ten additional checkpoints, including the three gated models
.\scripts\run_dose_response_expansion.ps1 -IncludeGated -AuthorizePaidRun
```

The last command authorizes ten paid model jobs (6,000 presentations including
calibration). Use one of the paid commands, not both. The completed three models
are never selected by this wrapper. Model revisions are resolved before the first
GPU job and written to the batch manifest; the frozen bank remains unchanged.
Outputs use `results/dose_response_batch/<UTC timestamp>/` and
`reports/dose_response_batch/<UTC timestamp>/`. Jobs stop at the first execution
failure; no automatic retries occur. A failed diagnostic calibration still produces
a report, because execution completion and scientific qualification are separate.
For a later failure, use the existing generic runner's `-Models` argument with only
the uncompleted models; a full expansion restart would duplicate paid work.

The gated path requires accepted licenses and the existing Modal secret named
`huggingface-secret` with an authorized `HF_TOKEN`. This wrapper selects that secret;
it does not create credentials or grant access. Gated access has not been verified
by a new cloud call. No expanded inference was launched during preparation.

## What failed, and what to measure

Current diagnostic calibration: Qwen accuracy 91.7%, generated validity 50.0%;
Mistral accuracy 90.6%, generated validity 2.1%; OLMo accuracy 82.3%, generated
validity 0.0%. The latter two show substantial factual discrimination in candidate
logits despite invalid free completions. Format failure alone is not invariant-A
degeneracy. Conversely, calibration accuracy alone does not validate the social
payoff construct. Qwen's PASS sits exactly on the current format cutoff.

1. **Finish the unchanged instrument comparison first.** Collect the ten additional
   runs as exploratory candidate-logit evidence. Analyze COOPERATE versus INDEPENDENT
   log probability contrasts separately from conditional argmax share. Record raw
   free completions, validity, calibration accuracy, letter distributions and
   numerical-control accuracy. Keep failed-format models visible and labelled.
2. **Audit outputs before changing prompts.** Inspect raw invalid completions for
   whitespace, punctuation, multi-token labels, explanations, or unrelated text.
   Evaluate a fixed retrospective parser separately while retaining the strict
   original metric. Do not search parser rules for maximal cooperation.
3. **Prepare a separate calibration-only elicitation pilot.** Compare unchanged
   plaintext with a fixed completion scaffold and four neutral factual examples
   whose correct letters balance A/B/C/D. Examples must contain no cooperation,
   partner identities or social payoffs. Use a discovery calibration bank and a
   disjoint validation calibration bank; the existing 24-item bank has already
   been observed and cannot serve as a new untouched validation set. Choose the
   format on calibration accuracy, label balance and stability, never cooperation.
4. **Freeze acceptance criteria before this pilot.** Proposed thresholds: >=70%
   factual forced-choice accuracy, <=25 pp position spread and no >=95% dominant
   letter; assess these on the independent validation calibration set. >=90%
   generated-letter validity is a separate requirement for claims about free
   generation. These proposed gates are future validation rules, not retrospective
   claims that the existing instrument passed. Report threshold sensitivity.
5. **Cross-check the label channel.** Compare candidate-letter likelihood with
   likelihood of each full option continuation, reporting both summed and
   length-normalized scores. Neither is automatically unbiased: long answers,
   surface plausibility and shared wording can dominate. Revalidate boundaries
   and label permutations for each tokenizer. Constrained decoding can produce
   valid letters by construction and must not count as improved understanding.
   Candidate likelihood scoring is a standard base-model evaluation mechanism;
   see the [EleutherAI task guide](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md).
6. **Run the revised elicitation as a separate version.** Preserve current bank,
   prompts and captures. Freeze the pilot-selected scaffold, then compare old and
   revised modes within model on paired exploratory families. Few-shot examples
   can change preferences; do not pool elicitation versions or describe instruction
   tuning as a repair that preserves the base-model estimand. Any matched instruct
   comparison is an explicitly separate training-stage comparator.

## Interpretation and deliverables

Prepare a model-by-dose table for choice share, log-probability contrast, and all
four strategy rates; show human and AI partners separately. Retain the six-family
cluster bootstrap across all payoff tiers, and report family-level curves. Treat
benefit/horizon effects as limited to two families and two payoff levels. Do not
count model sizes or repeat Qwen runs as independent model-family replications.

The measured private-payoff range is [-0.60, +0.20]. Qwen's existing linear
crossover estimate near -0.825 is extrapolated: report 'no observed crossover in
tested range', with the fitted number clearly labelled extrapolation. Do the same
for out-of-range fitted roots and intervals in other models. Saturation, positional
bias and non-monotonicity are substantive failure/sensitivity outcomes, not reasons
to silently remove a model. Absence of an in-range crossover is not evidence of an
unlimited willingness to incur costs.

Unresolved before stronger claims: calibration generation failures, position bias
in several candidates, six-family sampling uncertainty, narrow interaction coverage,
possible lexical preference, and new gated-model access. The historical full-repo
test suite also has unrelated frozen-artifact/tokenizer-cache failures; focused
dose-response checks and complete current raw files passed. Keep confirmatory
holdouts untouched throughout this expansion and elicitation pilot.
