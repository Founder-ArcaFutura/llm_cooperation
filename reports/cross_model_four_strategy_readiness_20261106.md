# Cross-model four-strategy replication: plan and local readiness

**Implemented and locally checked; no pretrained-weight inference or paid GPU
execution launched.** Corpus rewriting remains stopped. This replication tests
whether Qwen's representation and its length sensitivity recur across independent
base-model families, while preserving the original semantic stimuli.

The [protocol and executable commands](../docs/cross_model_four_strategy_replication.md)
describe the complete prospective study. The
[implementation](../llm_cooperation/mechanistic/cross_model_replication.py) provides
`prepare`, `import-qwen`, separately authorized `capture --smoke` / full capture,
`analyze`, and paired cross-model `compare` commands.

## Experimental plan

- Prioritize released OLMo-2-1124-7B base and Mistral-7B-v0.3 base. Resolve and pin
  official immutable revisions at metadata preflight; do not substitute the OLMo
  longitudinal ingredient checkpoint. Keep the original Qwen revision as comparator.
- Reuse all 496 original single-action prompts (124 scenarios, 54 families,
  24 domains), original 27/27 family and 12/12 domain splits, and unchanged
  `Decision:` capture boundary. No rewriting or scenario selection.
- Sample eight normalized depths, 1/8 through 1, after decoder blocks. Record
  realized depth; compare scalar metrics, never hidden-space vectors across models.
- Reuse Qwen scenario centering, grouped discovery-only probe fitting, legacy
  normalization and word/character adjustment. Add tokenizer-length adjustment,
  lexical residualization, separate length and word/bigram baselines, and nested
  conditional length/lexical predictive-gain controls.
- Report all four strategy directions, classification metrics, alignment,
  projection margins and paired raw-minus-adjusted attenuation. Compare model
  attenuation directly on matching held-out families/domains. Use cluster-aware
  bootstrap bands over layers and strategies, with declared multiplicity budgets.
- Detectable representations do not establish a preference for cooperation or
  causal behavioral use. No new behavioral assay is included.

## What passed locally

The [current preflight manifest](../research/cross_model_four_strategy_preflight_final_v2/manifest.json)
verifies original bank and prompt fingerprints and checks every stimulus against
the source. Family/domain grouping is intact. Original banks, Qwen machinery and
historical results have no tracked changes.

Qwen's actual cached tokenizer passed all 496 prompts; maximum full prompt length
is 89 tokens, total 35,083. Its new CPU baseline diagnostics are:

| Original held-out split | Length-only accuracy | Word/bigram accuracy |
|---|---:|---:|
| Families | 56.94% | 93.06% |
| Domains | 62.99% | 98.47% |

These are equal-held-out-cluster means from discovery-only fitting, not the earlier
six-fold baseline estimates. Lexical features include real strategic language, so
high lexical accuracy does not demonstrate a superficial artifact. Neither baseline
alone establishes the information used by the model to choose an action.

The original Qwen run was located under `mechanistic_artifacts/safe_download_full/`,
verified with the unchanged historical loader, and subsampled into
[`research/cross_model_qwen_import_v1`](../research/cross_model_qwen_import_v1/).
All 496 `(8,1536)` tensors and their new evidence hashes verify. This is a derived
copy, not a new forward pass or replacement for historical evidence. Comprehensive
new-control analysis has not been run on these tensors yet.

**21 targeted/existing tests passed; Ruff passed.** Checks include frozen-stimulus
and split integrity, normalized-depth mapping, authorization before model loading,
native-BOS versus final-EOS capture behavior, evaluation-label isolation in
conditional fitting, paired bands and plan mismatch refusal. Tiny randomly
initialized CPU OLMo2 and Mistral models verify the installed hook/decoder API and
finite tensor capture. They do not validate pretrained weights or GPU numerics.

## Resource estimates and blockers

Official [OLMo model details](https://huggingface.co/allenai/OLMo-2-1124-7B) and
[Mistral configuration](https://huggingface.co/mistralai/Mistral-7B-v0.3/blob/main/config.json)
specify 32 blocks and hidden width 4,096. Expected new-model resource envelope:

| Resource | Estimate per 7B model |
|---|---|
| Full capture | 496 sequential forward passes; eight retained vectors each |
| Saved vector payload | 62 MiB FP32 before compression/file overhead |
| FP32 weights alone | Roughly 28–30 GB decimal; runtime overhead additional |
| GPU recommendation | >=48 GB VRAM; 80 GB preferred for headroom |
| Host / cache | Roughly 64 GB host RAM; reserve 30–40 GB cache per model plus temporary overhead |
| CPU analysis | >=8 GB free RAM; potentially hours for nested fits and permutation controls |

These are engineering estimates, not observed full-model measurements. No runtime
or dollar quote is warranted yet. After authorization, four fixed prompts per model
should measure load time, forward latency and peak VRAM. Use those measurements
and the selected provider rate to establish a full-run ceiling before separate
full-run authorization. No automatic escalation from smoke to full execution.

**Blocking preflight dependency:** neither OLMo nor Mistral tokenizer/config is
cached locally. A metadata-only fetch failed on sandbox DNS; the escalated retry
failed TLS certificate validation. Their immutable revision pins, actual tokenizer
IDs, token baselines and context-fit audits remain unverified. The preflight marks
both BLOCKED and capture refuses them. We did not disable certificate verification,
invent revisions or download weights. Run metadata preflight in an environment
with working Hub trust before requesting GPU execution.

Methodological limits: same inspected bank and linguistic regularities across
families; unequal parameter counts/training data; native BOS and tokenization
differences; architecture-dependent post-block processing; historical versus new
framework/backend provenance; only 12 held-out domains; approximate simultaneous
bootstrap tails; linear nuisance adjustment can remove genuine semantic signal.
Legacy nuisance fitting is discovery-only but not fully nested in inner C folds;
the new conditional controls do nest preprocessing. None of these controls alone
establishes confound-free strategic representation or architecture-only causation.

## Recommendation

Proceed with this bounded cross-model replication after fixing metadata access.
The original instrument can answer whether its decodability and length sensitivity
recur across model families without another rewriting campaign. Preserve negative,
mixed and uncertain model differences. Do not infer that cooperation is length
sensitive in every model before the two new models have been captured and analyzed.

The immediate gate is successful CPU metadata/tokenizer preflight, followed by
explicit authorization for separate GPU smokes. Full inference remains unauthorized.
