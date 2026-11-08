# TinyStories paired counterfactual rewriting v1

This sub-workstream converts the already pinned 10,000-story TinyStories semantic
pilot sample into paired narrative alternatives. It does not edit the embedding
pilot, dose-response analysis, or PR16. The source is
`../outputs/semantic_pilot/sample.jsonl`; its IDs and hashes are cross-checked
against `../pilot_artifacts/sample_index.jsonl` before selection. Outputs belong
under this directory's ignored `outputs/` folder and are not committed.

The selector uses reproducible, overlapping lexical retrieval cues for sharing,
help/reciprocity, rivalry, and defection/self-advantage. Those cues are not semantic
labels. Pilot review strata can inform selection coverage, but their labels remain
provisional single-reader judgments. Use the separate semantic validator and a
stratified independent human review before using generated stories as training
text. The non-cooperative subtype is stored separately as `fair_competition`,
`unilateral_self_advantage`, or `exploitative_success`; an independent solo success
does not qualify.

## Frozen assets

- Prompt: `prompt_v1.json` (`paired-story-rewrite-v1.0.0`)
- Five paired demonstrations: `demonstrations_v1.json`
- Validation contract: `validation_prompt_v1.json`
- Generation config: `generation_config.json`
- Inference engine: vLLM `0.33.0`, used for batched offline generation; runtime
  package, Python, CUDA and GPU metadata are captured in each run manifest.
- Initial model: `Qwen/Qwen3-8B` at immutable revision
  `b968826d9c46dd6066d109eabc6255188de91218` (8.19B BF16 parameters; Qwen model
  card declares Apache-2.0). This is a candidate for a quality benchmark, not a
  claim of validated rewriting quality.

Versioned files are hashed into every run manifest. Change a prompt, demonstration,
generation setting, or model only in a new version; do not resume a run after an
identity change. vLLM offline batch generation is used; the pipeline never
provisions Lambda resources. A manually provisioned Lambda instance and an actual
account hourly quote are supplied by the operator.

## Local setup and selection (offline)

The existing raw sample cache is ignored and is expected to be present locally.
If it is absent, restore it from the original pilot's pinned source before
continuing; the sample index alone does not contain stories.

```powershell
python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py prepare `
  --count 100 --seed 20261107 `
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/benchmark-selection

python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py prepare `
  --count 1000 --seed 20261107 `
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-selection
```

`selection.json` preserves complete source stories, source IDs, hashes, source
shards, retrieval cues and any provisional pilot tags. Its SHA-256 is carried into
the run manifest. A new selection uses the same sample and a fixed seed; never
silently replace a source text or hash.

## Lambda environment and 100-story benchmark

Use a manually started single-GPU Lambda instance. The starting point is an A100
40 GB or better; BF16 weights alone occupy about 16.4 GB, with additional KV cache
and runtime memory required. An A100 40 GB is the suggested cost/fit baseline;
measure peak memory and throughput on the instance actually available. Do not
launch resources from these scripts. Install the pinned runtime on the Lambda host:

```bash
python3 -m venv .venv-rewrite
source .venv-rewrite/bin/activate
python -m pip install --upgrade pip
python -m pip install -r research/pretraining_counterfactual_v1/rewriting_v1/lambda_requirements.txt
```

Before any run, read the actual hourly rate shown in the Lambda account for the
chosen instance. The current public pricing page is date-effective November 16,
2026, after this task's date, and says to log in for current rates. Its public
prices therefore do not establish this account's rate. The CLI requires the
operator-provided `--hourly-rate-usd`; no billing API is queried.

On the provisioned instance, after confirming the selected machine, account rate,
and output volume, transfer the versioned code and
`outputs/benchmark-selection/selection.json` to the instance (for example, using
`scp` or `rsync` over the authenticated session). Keep generated outputs on the
instance or return them through the same authenticated transfer. Then run the
100-story benchmark:

```bash
RATE_USD_PER_HOUR='REPLACE_WITH_CURRENT_LAMBDA_ACCOUNT_RATE'
LAMBDA_INSTANCE_ID='REPLACE_WITH_MANUALLY_PROVISIONED_INSTANCE_ID'
python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py run \
  --selection research/pretraining_counterfactual_v1/rewriting_v1/outputs/benchmark-selection/selection.json \
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/benchmark-qwen3-8b-v1 \
  --count 100 --benchmark --hourly-rate-usd "$RATE_USD_PER_HOUR" \
  --approve-paid-inference --lambda-instance-id "$LAMBDA_INSTANCE_ID"
```

Generation config fixes batch size at 8, sampling seed 20261107, temperature 0.2,
top-p 0.9, and up to three attempts. The benchmark records model load-inclusive
wall time, timed inference throughput, prompt/completion tokens including retries,
GPU peak allocated/reserved memory, schema-and-integrity acceptance, retry counts,
and measured inference cost. The batch throughput excludes model startup; the
separate wall rate includes startup. GPU-hours used during this process are
counted at the supplied Lambda rate, but billing may also include setup, idle time,
storage, tax, and other account charges. Stop or terminate the instance manually
after the command completes.

The run is resumable: every record is written to its own temporary file and then
atomically replaced, and a checkpoint is committed after a run segment. Existing
valid records are skipped only when the source hash and frozen run identity match.
Generation output JSON/schema/integrity failures are automatically retried up to
the configured cap. Failed attempts and raw responses remain in per-record retry
history, including records that fail all attempts. No source is silently dropped.
The exact token-ID sequences for each source and accepted rewrite are stored beside
each record. The report counts token supply and unique token IDs using the pinned
tokenizer, separately from lexical word-type measures.

Review `benchmark.json` before scaling. A recommendation should include:

- At least 100 source stories, generation acceptance and retry/error categories.
- GPU memory headroom and whether output limits truncated stories.
- Review of a stratified sample across all four selector cues and all produced
  non-cooperative subtypes; add an independent reviewer before scale-up.
- Separate prose-quality judgments and semantic validity judgments.
- Re-run projections using the measured inference rate and account rate.

The `report` and `cost` commands calculate inference-only projections for 1,000,
100,000 and 300,000 sources. The cost identity is
`(N / measured_stories_per_second / 3600 + startup_and_validation_hours) * actual_hourly_rate`.
The report includes inference-only values; add measured startup and validation
hours before budgeting. No model training is part of this pipeline.

```bash
python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py report \
  --run research/pretraining_counterfactual_v1/rewriting_v1/outputs/benchmark-qwen3-8b-v1 \
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/benchmark-qwen3-8b-v1/report.json

python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py cost \
  --stories-per-second 0.5 --hourly-rate-usd "$RATE_USD_PER_HOUR" --startup-hours 0.5
```

## 1,000-source pilot, after benchmark review

The script refuses a 1,000-source run unless `--approve-1000-pilot` is supplied.
Only after the 100-story results have been reviewed and the pilot is approved,
start a manually provisioned instance and use the separate 1,000-story selection:

```bash
python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py run \
  --selection research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-selection/selection.json \
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-qwen3-8b-v1 \
  --count 1000 --approve-1000-pilot --hourly-rate-usd "$RATE_USD_PER_HOUR" \
  --approve-paid-inference --lambda-instance-id "$LAMBDA_INSTANCE_ID"
```

## Separate semantic validation and report

Validation uses a distinct prompt/version and stores one judgment record per
generated pair. It assesses behavior identity, intended actor outcome, causal
linkage, opposing-treatment distinction, source preservation, age/language
complexity, and ending consistency. Uncertain, failed, and malformed cases remain
on disk; validation status never deletes a generation. Using the same model family
as judge is not independent evidence, so a stratified human review is a required
scale gate.

```bash
python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py validate \
  --run research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-qwen3-8b-v1 \
  --hourly-rate-usd "$RATE_USD_PER_HOUR" --approve-paid-inference \
  --lambda-instance-id "$LAMBDA_INSTANCE_ID"

python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py review-sample \
  --run research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-qwen3-8b-v1 \
  --count 50 --seed 20261109 \
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/human-review.jsonl

python research/pretraining_counterfactual_v1/rewriting_v1/pipeline.py report \
  --run research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-qwen3-8b-v1 \
  --human-review research/pretraining_counterfactual_v1/rewriting_v1/outputs/human-review-completed.jsonl \
  --human-review-key research/pretraining_counterfactual_v1/rewriting_v1/outputs/human-review.jsonl.key.jsonl \
  --output research/pretraining_counterfactual_v1/rewriting_v1/outputs/pilot-qwen3-8b-v1/report.json
```

The human review pack randomizes displayed A/B sides and writes the key separately
as `human-review.jsonl.key.jsonl`; keep that key away from reviewers. It samples
across available non-cooperative subtypes and asks reviewers to assess behavior,
outcome linkage, source content, language level, and endings. Provide both completed
review JSONL and the separate key to `report` to compute per-treatment summaries;
the report cannot determine whether a reviewer was independent, so that provenance
must be recorded in each `reviewer_id` field. The report's default 50-row completeness
gate follows the review-pack default; it is a procedural gate, not a validated
sample-size claim or semantic acceptance threshold. A complete review still requires
an explicit scaling decision.

Record schema is JSON-friendly for later dataset packaging: one row per source,
with the unchanged `source_story`, `cooperative_story`, `non_cooperative_story`,
subtype, source/output hashes, model/config/prompt versions, token counts, retry
history, and validation outcomes. Metadata is outside the training text. This code
does not upload or publish datasets; future Hugging Face publication requires a
separate reviewed card, licensing review, version/tag, and explicit authorization.

## Local offline checks

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest tests/test_tinystories_rewriting.py -q
```

These tests use temporary fixtures or the committed pilot index only; they do not
download model weights, call a model API, initialize vLLM, provision a GPU, train,
or publish data.
