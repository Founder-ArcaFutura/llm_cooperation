# Cross-model four-strategy replication v1

Status: implemented, local preflight only; pretrained-weight GPU work is unauthorized.
Corpus rewriting is stopped. This experiment uses the exact original Qwen prompt
inventory and frozen Phase 0B source, with no semantic edits or new scenarios.

## Plan and scientific question

Priority models are released base `allenai/OLMo-2-1124-7B` and
`mistralai/Mistral-7B-v0.3`. The OLMo endpoint is the released base, not the
ingredient-specific continuation used in longitudinal behavioral work. Qwen uses
the original pinned `8faed761d45a263340a0528343f099c05c9a4323` revision. New models'
official `main` refs must be resolved once to immutable 40-character SHAs before
any capture. No guessed SHAs, instruction models, alternate endpoints, or silent
precision substitutions are permitted.

Hypotheses:

1. Four-strategy decodability and all four OVR directions generalize to independent
   pretrained families on identical stimuli, across held-out families and domains.
2. Cooperation alignment attenuation after word/character adjustment recurs, or
   differs materially across model families. Evaluate attenuation directly, not a
   comparison of significant versus non-significant results.
3. Token counts and lexical information account for additional signal beyond
   word/character counts. Quantify conditional predictive gain and retain negative
   or inconclusive findings rather than adjusting the corpus to improve results.

This is a cross-model replication of an exploratory, previously inspected bank,
not a fresh semantic validation or a causal mechanism experiment. Architecture,
size, pretraining data and training recipe vary together; differences cannot be
attributed solely to architecture. No behavioral preference endpoint is measured.

## Fixed stimuli, splits and capture

Use all 124 scenarios / 496 single-action prompts / 54 families / 24 domains.
Copy `research/contrastive_full_v1/prompts.jsonl` byte-for-byte and verify every
stem/action against the source bank and legacy bank hash. Retain the original
27/27 family split and 12/12 domain split. Human/AI and triad relatives remain
together under `triad_id or template_id`. The original source split is not a new
confirmatory partition. No probe/activation outcomes influence selection.

Render the existing `{stem}\n\nAction: {action}\nDecision:` format. No strategy
labels or response letters are added. Tokenize separately for each model with
its native special-token behavior, recording actual full IDs, action/full-prompt
counts and final-text offsets. Native BOS can differ across families and is
recorded; added EOS at the capture boundary, truncation or unexpected offsets
block capture. Use native tokenizers without chat templates.

Sample post-block residuals at normalized depths
`1/8, 2/8, ..., 8/8`, choosing zero-based block `ceil(depth * num_blocks)-1`.
For 32-block models these are 3,7,11,15,19,23,27,31; Qwen's 28 blocks map to
3,6,10,13,17,20,24,27. Record realized depths as `(index+1)/num_blocks` as well
as target depths. These are coarse depth correspondences, not equivalent layers.
No embedding layer is sampled, and no origin/localization claim is made.

Use FP32 eval-mode forward passes, batch size one, no gradients, KV cache,
generation, quantization or padding. Hook decoder blocks and call the decoder
without allocating full vocabulary logits. OLMo2 and Mistral expose
`model.model.layers` in the installed Transformers API; tiny randomly initialized
CPU tests exercise that API. Actual pretrained-weight compatibility and GPU
memory/runtime remain subject to a separately authorized smoke test.

## Analysis and controls

Reuse existing `scenario_center`, `_layer_eval`, and `_fit_probe` from the Qwen
analyzer; retain that analyzer and its identity/dimension checks unchanged.
The new adapter validates model-specific shapes and exact evidence hashes.

For both fixed splits, all fitted directions, nuisance regressions, vocabularies
and probes use discovery data only. Grouped discovery folds select probe C from
`.01,.1,1,10`. Legacy raw/unit-normalized/word-character classifier calculations
are reused, including 100 within-scenario label permutations. They retain the
legacy unscaled probe feature convention for comparability.

Measure balanced accuracy, macro-F1, confusion matrices, AUROC and normalized-vector
accuracy through the legacy path. Independently report all four strategy OVR
directions, held-out-cluster direction alignment and positive-minus-other projection
margins under four views:

| View | Discovery-fitted adjustment |
|---|---|
| Raw | No nuisance regression |
| Word/character | Original scenario-centered word/character Ridge(alpha=1) |
| Token length | Add centered action/full-prompt tokenizer counts to word/character features |
| Lexical | Token-length features plus discovery-fitted L2-normalized unigram/bigram TF-IDF, at most 2,048 features; Ridge(alpha=1) |

Nuisance-adjusted vectors are recentered within scenario. Nuisance fitting precedes
legacy discovery C selection to preserve the original convention; it never sees
evaluation data. This is not fully nested nuisance fitting inside the inner C
folds. Report it as a legacy sensitivity analysis, not unbiased confound removal.
Aggressive lexical adjustment can remove authentic strategic meaning.

Separate baselines use quadratic action/prompt token, word and character features,
or L2-normalized word/bigram TF-IDF alone. Fit each model's baselines separately
even though identical text can yield identical lexical-only baselines. Conditional
controls compare held-out cross-entropy of length-only versus length+activation,
and lexical-only versus lexical+activation. These controls nest vocabulary/scaling
and C selection in discovery grouped folds, minimizing cluster-macro log loss.
Report gains in bits/action. They measure finite-model predictive accessibility,
not universal mutual information or semantic specificity. Numeric scaling/feature
selection differs from the legacy probe; compare within each control method.

For directions, discovery cluster means have equal weight. Held-out family or
domain summaries are the resampling units. Raw-unit margins are retained but only
dimensionless alignment, accuracy, attenuation and margins divided by discovery
RMS vector norm enter cross-model contrasts. Never compute a cosine between
different models' hidden-space directions or directly compare their raw margins.

Primary descriptive contrast: raw minus adjusted cooperation alignment, paired
within the same held-out clusters. Report all other strategy directions alongside
it, and compare those attenuation estimates between models on paired clusters.
Shared clusters/stimuli mean model estimates are not independent samples.

Multiplicity: 10,000 paired cluster bootstrap draws, fixed seed 42. Within each
model/split/view, max-standardized-deviation bands jointly cover the sampled
depths, all four strategies and recorded metrics. Allocate .0125 across 24 such
families, .0125 across 12 conditional-gain families, and .025 across at most 24
paired model/split/view comparisons (three model pairs). Legacy 95% pointwise
intervals and 100-permutation nulls remain descriptive, not multiplicity-controlled
discovery claims. Bootstrap bands are approximate, conditional on fitted discovery
models; 12 held-out domains and extreme adjusted tails limit precision. Zero-norm
directions block that analysis rather than being reported as zero cosine.

Positive alignment and classification above chance with simultaneous bounds
support detection in the sampled representation. Positive raw-minus-adjusted
attenuation bounds support sensitivity under that adjustment. Model differences
require paired contrast bounds excluding zero; no significance-disagreement rule.
Near-zero results are inconclusive, not equivalence. No effect size margin for
architecture equivalence is asserted. Behavior remains a separate instrument and
competence-gated study.

## Expected resources and decision gates

The official [OLMo card](https://huggingface.co/allenai/OLMo-2-1124-7B) and
[Mistral configuration](https://huggingface.co/mistralai/Mistral-7B-v0.3/blob/main/config.json)
describe 32 blocks and width 4,096. Configs must still be downloaded and pinned.
For each new model: 496 sequential forward passes, saving eight vectors per prompt.
Uncompressed vector payload is 65,011,712 bytes (62 MiB), plus small inventories;
both new models total 124 MiB. Original Qwen vectors can be imported at the eight
depths without new inference (about 23.25 MiB). NPZ overhead/compression varies.

FP32 parameter memory for roughly 7B parameters alone is roughly 28–30 GB decimal;
token embeddings/vocabulary, runtime workspace and allocator overhead matter.
Provision one >=48-GB GPU, preferably 80 GB for headroom, and roughly 64 GB host
RAM. Reserve 30–40 GB weights/cache disk per 7B model and allow temporary loading
overhead. These are engineering estimates, not actual-weight measurements. CPU
analysis should have at least 8 GB free RAM and may take hours because of nested
fits and permutation controls. Do not use the behavioral configuration's BF16
16-GB recommendation as an FP32 memory estimate.

No credible full-run duration or dollar quote exists before an actual GPU smoke
measurement and a provider rate. After separate authorization, run four prompts
(one fixed complete scenario) per model, verify hooks/finite tensors, record model
load time, warm forward latency and peak VRAM. Estimate 496-prompt time from the
smoke with overhead, obtain a bounded cost ceiling, then seek authorization for
full runs. No automatic smoke-to-full progression. Use an external job timeout
and spend limit in the execution environment; this local module provisions no
cloud resources and does not enforce a billing cap.

Current blocker: local Hub metadata/tokenizer retrieval failed on sandbox DNS and
then external certificate verification. Qwen cached tokenization works. Do not
disable TLS verification or substitute longitudinal ingredient SHAs. New-model
revision pins, token audits, per-tokenizer baselines and max sequence lengths remain
unverified until metadata preflight succeeds in a correctly configured environment.
Installed tiny-model API tests do not establish actual-weight parity.

The preparation records installed package versions. Reproduce that environment
for capture and retain original Qwen runtime provenance when importing evidence.
The historical Qwen run may use a different Transformers/attention backend than a
new model run; post-block hook parity is not a numerical framework-equivalence
test. Inspect this difference at smoke review rather than silently treating every
runtime as interchangeable.

## Executable workflow

Metadata/preflight only, in an environment with working Hub certificate trust:

```powershell
python -m llm_cooperation.mechanistic.cross_model_replication prepare --output research/cross_model_ready_v1 --download-metadata
```

This downloads only configurations/tokenizers into workspace `.local` cache, not
model weights. It resolves immutable SHAs, audits all prompts and fits CPU baselines.
Any missing dependency is recorded as BLOCKED. Plans bind script/library versions,
code hashes, frozen bank bytes, prompt bytes, tokenizer metadata and config hashes.

Reuse verified saved Qwen evidence (CPU, no pretrained model forward):

```powershell
python -m llm_cooperation.mechanistic.cross_model_replication import-qwen --plan research/cross_model_ready_v1 --source-run mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9 --output mechanistic_artifacts/cross_model_qwen_v1
```

Future smoke command, **only after explicit authorization**:

```powershell
python -m llm_cooperation.mechanistic.cross_model_replication capture --plan research/cross_model_ready_v1 --model olmo7b --output mechanistic_artifacts/cross_model_olmo_smoke_v1 --smoke --authorize-inference --authorize-paid-run
```

Repeat separately for `mistral7b`. Smoke evidence cannot enter the scientific
analyzer. Full runs require subsequent authorization, a new output path and omission
of `--smoke`. Existing output directories are never overwritten. No model downloads
or initialization occur if either authorization flag is absent.

```powershell
python -m llm_cooperation.mechanistic.cross_model_replication analyze --plan research/cross_model_ready_v1 --run mechanistic_artifacts/cross_model_olmo_full_v1 --output reports/cross_model_olmo_v1
python -m llm_cooperation.mechanistic.cross_model_replication compare --analyses reports/cross_model_qwen_v1 reports/cross_model_olmo_v1 reports/cross_model_mistral_v1 --output reports/cross_model_comparison_v1
```

Analyze each full model separately, including imported Qwen, using the same new
controls. Comparison rejects different plans, grids or cluster inventories. All
original reports remain historical evidence; the new Qwen analysis is additive.
