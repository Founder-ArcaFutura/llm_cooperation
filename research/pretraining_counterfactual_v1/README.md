# Controlled pretraining counterfactual v1

Status: the **bounded local semantic pilot is complete**; the language-model
training experiment and full embedding census are **NOT RUN**. See the
[empirical pilot report](pilot_artifacts/PILOT_REPORT.md) and
[reproduction/annotation protocol](pilot_tools/README.md). The pilot scored 10,000
seeded random TinyStories records, including a nested 500-story smoke, and reviewed
140 selected stories with provisional Codex-assisted judgments. No Modal, Lambda
resources, LM training or dataset publication occurred. Source shards, sampled full
stories and large caches remain under ignored outputs/. Dose-response and PR16
files are unchanged. The synthetic unit tests remain separate from empirical data.

The paired narrative-rewriting follow-on is implemented separately under
[rewriting_v1](rewriting_v1/README.md). It prepares a pinned-sample selection,
few-shot prompt, vLLM runner, semantic validator, and report/review tools; no Lambda
inference has been run and no generated stories have been published.

Dataset/tokenizer revisions in config.json now pin this pilot's baseline. Use a
new versioned config/cache for a later baseline change. The original infrastructure
proposal below is an unexecuted plan, not evidence that the semantic interventions
have been validated; the pilot recommends classifier revision before a full census.

## Scientific scope and decisions

Test whether changing semantic sampling weights over an otherwise identical
pretraining source changes the existing cooperation-choice measures. TinyStories
is **synthetic**, generated with GPT-3.5/GPT-4, not naturally occurring human text:
https://huggingface.co/datasets/roneneldan/TinyStories and
https://arxiv.org/abs/2305.07759. It is a useful controlled pilot, but the intended
natural-text claim needs later replication on a human-authored corpus.

Streaming is appropriate: HF `streaming=True` transfers records as needed without
a full raw download on the workstation. A full census must still read the whole
source. The scorer writes text, token IDs and scores into a durable SQLite cache
on Modal; transfer that cache once to Lambda. Random-access weighted training
from the remote stream each step would waste bandwidth and frustrate exact resume.

The E5 defaults use the exact revision and `query: ` + normalized-vector convention
in `research/lexical_strategy_bridge_v1/encode_saved_actions.py`. This transfers
encoder preprocessing, **not** the validity of isolated-word labels to narratives.
For an independent BGE-M3 census, change encoder to `BAAI/bge-m3`, revision to
`3806044eb869c8756693584f7eb5dd04ab2bdd95`, prefix to `""`, and use a separate cache.
Scores from different encoders are not interchangeable.

Stories are scored in overlapping encoder-token windows with character offsets.
The five joint behavior/outcome anchor groups distinguish cooperation success,
cooperation failure, competition success, competition failure and neutral context.
Cooperation prevalence is max-window probability mass on either cooperative
outcome; successful competition is max-window positive difference between success
and failure mass. Softmax temperature is fixed at 0.05. These are **uncalibrated
semantic proxies**, not evidence that the same actor's behavior caused a reward.
Negation, moral endings, altruistic sacrifice, and another actor winning can fool
them. Audit actor, behavior, outcome and linkage, including failures/neutral cases.
Do not call the competition arm validated until that audit is satisfactory.

Sampling unit is an unchanged full story; weights are computed from its windows.
This preserves context and provenance rather than extracting reward sentences.
`original`: w=1; `cooperation_depleted`: w=exp(-strength * cooperation_score);
`competition_enriched`: w=exp(strength * successful_competition_score).
All arms sample documents **with replacement**, then concatenate their full token
sequences with EOS. Original retains all source rows and duplicate multiplicity,
with equal document probabilities; it is not a deduplicated or balanced baseline.
Token exposure naturally depends on story length. No rewriting, labels inserted
into training text, or keyword deletion. Strength zero is a parity control.

## Concrete stage plan

1. Pin dataset and tokenizer commits in config.json; keep encoder/anchors frozen.
   Run an approved 1,000-story timed prefix diagnostic remotely. Measure startup,
   scoring documents/windows/tokens per second, output bytes and total provider
   charges. This prefix diagnoses engineering; it is not a representative estimate
   of semantic prevalence. A complete scan follows only if affordable.
2. Scan the full train split and a separate validation split. Generate distributions,
   40-bin histograms, score-decile audit samples and strength sweeps. Report total
   tokens, exact-unique-text tokens (not unique vocabulary), ESS, token-weighted
   semantic shifts, available support, and expected unique coverage after a chosen
   number of document draws. Review a second encoder separately if affordable.
3. Audit samples before choosing strength. Use a larger independently reviewed
   sample before a scientific freeze; the starter audit is not adequate to estimate
   precision tightly. Inspect length, vocabulary/topic and narrative-quality shifts
   as possible mediators/confounds. Matching/stratification is a later design change,
   not silently imposed here. Freeze inputs, score method, selected strengths and
   audit decision before CPI evaluation. Export weighted distributions locally.
4. Create the same random initialization for all three arms of seed 1. Benchmark
   each arm briefly on the actual cache and A100; use the slowest measured rate
   (prefer p10) in projections. Benchmark checkpoints are separate and never become
   the pilot initialization. Same context, batch, token budget and optimizer in all
   arms; compare at equal consumed prediction tokens, not equal weighted epochs.
5. Once approved, run the three arms sequentially, evaluate initialization and
   periodic/final checkpoints with existing CPI/calibration instruments. Examine
   held-out language-model loss, calibration, option-order effects and format
   validity alongside cooperation scores. Replicate with seeds 2 and 3 only after
   pilot review. Extra epochs mean a **new prespecified token budget/run identity**,
   not editing the target of an existing resumed run. Do not select epochs on the
   direction of CPI. A poor calibration result can make CPI uninterpretable.

No intervention strength, feasible unique-token count or empirical throughput is
claimed yet. Those are outputs of stages 1–2/4, not facts that code can establish.

## Costed proposal (estimates, not measurements)

Planning size: the HF viewer reports approximately 2.12M train rows. Actual pinned
counts and token totals come from the census. Model-token length is unknown until
tokenization: at an **assumed** 200 tokens/story, source size would be about 424M
tokens; deduplicated support could be smaller. Keep enough disk for token IDs
(4 bytes/token), text, per-window score metadata, SQLite indexes, exports and
multiple model+optimizer checkpoints. Allocate 30–50GB initially and measure actual
bytes from the diagnostic; this is a capacity allowance, not a measured requirement.

Modal's public T4 rate checked 2026-11-07 is $0.000164/s = $0.5904/h. Allowing
two CPU cores at $0.0000131/core/s and 8GiB at $0.00000222/GiB/s gives roughly
$0.75/h before volume/egress/startup. Full-census sensitivity:

| Assumed stories/s | Hours for 2.12M | Approximate compute USD |
| --- | ---: | ---: |
| 50 | 11.78 | 8.83 |
| 200 | 2.94 | 2.21 |
| 500 | 1.18 | 0.88 |

This implementation batches **windows within a story**, not stories across workers;
short stories may underutilize the GPU. Measure it before extrapolating. Each
invocation is bounded to at most 3,300 scoring seconds plus startup/commit overhead;
it is a serial resumable job, not an unbounded fan-out. Restarting a HF stream can
retransfer skipped records; no committed rows are re-embedded. Reserve $10 for a
first-encoder census provisionally. Credits/free tiers are not assumed.

Lambda's public page currently labels displayed prices as effective **November 16,
2026**, and directs users to their account for current prices. Therefore the CLI
requires `--hourly` from the actual account quote. Using **$2/h purely as a planning
scenario**, a 500M-token/arm pilot has these training-only costs:

| Assumed training tokens/s | Three-arm hours | USD at assumed $2/h |
| --- | ---: | ---: |
| 5,000 | 83.33 | 166.67 |
| 10,000 | 41.67 | 83.33 |
| 20,000 | 20.83 | 41.67 |

At 10k tokens/s, adding $10 census and one GPU-hour of overhead gives about $95.33,
near the $100 target. Three seeds at the same budget would cost about $262 before
extra overhead and exceed $150. A smaller token pilot may be required. Under the
same assumptions, $100/$150 permit about 528M/828M prediction tokens per arm for
one seed, reserving $12 for census+overhead. These are arithmetic scenarios, not a
promise that $100 suffices for learned behavior or that one hour covers all evals.

Sources: https://modal.com/pricing, https://lambda.com/pricing,
https://huggingface.co/docs/datasets/stream, https://modal.com/docs/guide/volumes,
https://huggingface.co/docs/transformers/model_doc/gpt2.

The shared SQLite ledger rejects cumulative reserved job time plus a nondecreasing
prior-cost floor above $150. Use the **same ledger** for all arms, benchmarks and
seeds. Include scoring, untracked setup/idle time, storage, transfer and tax in the
prior-cost floor; count reserved jobs separately to avoid double counting. No
override above $150 is implemented. Operator must approve a plan before launching.
The runner stops between steps with checkpoint headroom; it cannot terminate your
Lambda instance or enforce a provider invoice ceiling. Idle instances keep costing
money after this process exits. Set provider-side limits where available and
terminate resources manually. Code reservations are conservative estimates, not a
replacement for provider billing. Evaluation commands need their own time allowance.

## Setup and commands — for the operator to run later

From repository root on the intended host. Use **Python 3.11** and a separate venv;
the pinned CUDA stack is intended for Linux, not the current Windows/Python 3.13.
These instructions do not require changing branches or existing research files.

```bash
python3.11 -m venv .venv-counterfactual
source .venv-counterfactual/bin/activate
pip install -r research/pretraining_counterfactual_v1/requirements.txt
pip install -e . --no-deps
```

Resolve current HF revisions without downloading corpus/model contents, then edit
config.json (or preferably an immutable copy in outputs/). The following metadata
query is **not** executed by this implementation session:

```bash
python -c "from huggingface_hub import HfApi; a=HfApi(); print('dataset', a.dataset_info('roneneldan/TinyStories').sha); print('tokenizer', a.model_info('openai-community/gpt2').sha)"
```

The config deliberately refuses placeholder/mutable revisions. For Modal, use your
already configured Modal CLI (`pip install modal` in the operator environment if
needed). Do not deploy a persistent service. After explicit approval:

```bash
modal run research/pretraining_counterfactual_v1/modal_score.py \
  --config research/pretraining_counterfactual_v1/config.json \
  --run-name train-e5-v1 --limit 1000 --seconds 600 --approve-cloud

# Continue same cache without re-embedding committed rows; repeat bounded calls
# only after reviewing elapsed time/cost. limit=0 means the full remaining split.
modal run research/pretraining_counterfactual_v1/modal_score.py \
  --config research/pretraining_counterfactual_v1/config.json \
  --run-name train-e5-v1 --limit 0 --seconds 3300 --approve-cloud

# Download cache+tokenizer+receipt to Lambda, or to your chosen transfer location.
modal volume get cooperation-pretraining-census-v1 train-e5-v1 ./counterfactual/train
```

For validation, copy the config, set `split` to `validation`, use run-name
`validation-e5-v1`, and retrieve to `./counterfactual/validation`. It is safe to
score just a prefix for validation loss; the full validation census is preferable.
Training validation uses a fixed original prefix, excludes exact train-text
duplicates, and records its token hash. It never uses intervention weights.

Equivalent direct scoring on an approved local/remote GPU:

```bash
python -m research.pretraining_counterfactual_v1.data score \
  --config research/pretraining_counterfactual_v1/config.json \
  --output counterfactual/train --limit 1000 --max-seconds 600

python -m research.pretraining_counterfactual_v1.data census \
  --source counterfactual/train/corpus.sqlite --output counterfactual/census --draws 1000000
```

Review `census.json`, `feasibility.md`, `histograms.png`, `audit.jsonl`, and
`manifest.json`. Unique coverage is expected after *document draws*, not a fixed
prediction-token budget; approximate draws = target tokens / reported mean document
tokens. All conditions retain the same available support; enrichment changes reuse.

On a manually started Lambda A100, initialize once per seed. Approximately 45.2M
parameters: 6 layers, 512 hidden, 8 heads, GPT-2 tokenizer, 1024 position capacity,
tied embeddings, zero dropout. **No pretrained model weights** are loaded. Only
tokenizer and semantic encoder are pretrained. The tokenizer's prior is shared
across all arms. AdamW: LR 6e-4, betas .9/.95, weight decay .1, clip 1; linear warmup
100 steps then cosine to 10% LR. Default context 512, batch 8, accumulation 4,
bf16 AMP. Actual parameter count and full optimizer configuration are recorded.

```bash
python -m research.pretraining_counterfactual_v1.train init \
  --source counterfactual/train/corpus.sqlite --output counterfactual/init-seed1 --seed 1 --execute

# REAL billable benchmark, not executed here. Set RATE to current account USD/h.
RATE=2.00  # illustrative placeholder: REPLACE with actual account quote
python -m research.pretraining_counterfactual_v1.train train \
  --source counterfactual/train/corpus.sqlite --init counterfactual/init-seed1 \
  --output counterfactual/benchmark-original --ledger counterfactual/budget.sqlite \
  --condition original --strength 0 --seed 1 --tokens 100000000 \
  --seconds 600 --hourly "$RATE" --prior-cost 10 --benchmark --execute
```

Repeat separate benchmark outputs for depleted/enriched using the reviewed
strength. `summary.json` reports post-warmup mean and p10 step throughput. It times
real data sampling, GPU forward/backward/optimizer and device synchronization;
checkpointing, cold start and evaluation need separate overhead allowances. Use at
least 20 measured steps; if fewer, extend a separately budgeted benchmark. A real
benchmark trains disposable weights; never continue these into a treatment arm.

```bash
# Local arithmetic only. Replace TPS/RATE/prior with measured/current values.
python -m research.pretraining_counterfactual_v1.train project \
  --tokens 500000000 --tps 10000 --hourly "$RATE" --seeds 1 \
  --overhead-hours 1 --prior-cost 10
```

After reviewing and explicitly approving the full pilot, three commands use the
same initialization, seed, optimizer settings and exact prediction-token budget:

```bash
# One example arm. Repeat for cooperation_depleted / competition_enriched,
# using the REVIEWED strength and a different output directory for each arm.
python -m research.pretraining_counterfactual_v1.train train \
  --source counterfactual/train/corpus.sqlite \
  --validation-source counterfactual/validation/corpus.sqlite \
  --init counterfactual/init-seed1 --seed 1 --condition original --strength 0 \
  --tokens 500000000 --output counterfactual/seed1-original \
  --ledger counterfactual/budget.sqlite --hourly "$RATE" --prior-cost 10 \
  --seconds 54000 --checkpoint-steps 500 --execute
```

`54000` is only an example **total lifetime** runtime reservation per arm, including
resumes. Choose it from the measured throughput and total approved budget; a short
time reservation can end before the token target. Reinvoke the *identical* command
with `--resume` to load the last committed checkpoint within its remaining runtime.
Any change to identity (including source hash, code, environment, target tokens or
initialization) is rejected. Source cache must remain immutable during training.
The RNG, partial document/buffer, optimizer, model, step and logs resume together.
Uncommitted checkpoint folders are ignored. This is paired initialization, not a
promise of bitwise identical CUDA kernels across different hosts/software.

Each checkpoint is HF-loadable; state.pt is for trusted local resume only. Keep
untrusted checkpoints away from that loader. `latest.json` authenticates checkpoint
files. `train.jsonl` tracks loss, LR, exact prediction tokens, cumulative GPU-hours,
estimated charges, draws and actual semantic exposure. `summary.json` includes
per-source-ID token counts (including the initial one-token context). Validation
loss/perplexity is in `validation.jsonl`. Partial final steps still hit the exact
prediction-token target. EOS boundaries and the tokenization policy are identical.

Evaluate initialization and selected periodic/final checkpoints, each to a new
output directory, only when ready to spend the evaluation allowance:

```bash
python -m research.pretraining_counterfactual_v1.train eval \
  --checkpoint counterfactual/seed1-original/checkpoint-00030518 \
  --output counterfactual/eval-seed1-original-final --execute
```

The checkpoint name above is illustrative: use `latest.json`. This calls the
existing pilot bank `data/scenarios.json`, calibration bank, and existing analysis
with option orders 0/1/2. Raw records, bank hashes and weight identity remain
separate for each checkpoint. It does not consume the protected phase1 bank or
modify dose-response instruments. Compare at matched tokens across arms; do not
pool presentations as independent seed replicates. A 45M story model may lack the
language/reasoning competence for the current adult scenarios. Report that result
without treating format familiarity as social preference. A new child-language
instrument would be a separately validated follow-up.

Plot the three arms offline (no GPU). The report rejects runs whose paired
initialization, source, optimizer, seed or token budget differ:

```bash
python -m research.pretraining_counterfactual_v1.report \
  --runs counterfactual/seed1-original counterfactual/seed1-depleted counterfactual/seed1-enriched \
  --output counterfactual/curves-seed1
```

Evaluation also writes `cooperation_metrics.json` with scenario-clustered choice
rates, conditional probabilities, and calibration status for each option order.

Seed replication: `init --seed 2` / `--seed 3` to distinct initialization directories,
then the same three-arm commands with the corresponding seed. Run `project --seeds 3`
first. The present ceiling can require reducing tokens or further explicit approval.

## Optional versioned export and publication

Export after a **complete** census and documented audit/strength decision:

```bash
python -m research.pretraining_counterfactual_v1.data export \
  --source counterfactual/train/corpus.sqlite --output counterfactual/export-enriched-v1 \
  --condition competition_enriched --strength 4
```

Strength 4 is an example, not a scientific selection. Export retains unchanged
stories, indices, hashes, token counts and weights, plus provenance and dataset
card attribution under the upstream `cdla-sharing-1.0` declaration. Review upstream
license terms and dataset card before publication. A weighted dataset does not
become a reweighted training distribution unless its consumer uses sampling_weight.
Export the three arms separately and include the reviewed census/audit report in
the eventual publication package.

No destination/credentials were supplied or inspected. Only after explicit external
publication approval, and with HF authentication already configured:

```bash
python -m research.pretraining_counterfactual_v1.data publish \
  --folder counterfactual/export-enriched-v1 --repo YOUR_ORG/YOUR_DATASET \
  --tag enriched-v1 --approve-publish
```

This authenticates, verifies the export hash, uploads, and tags the exact resulting
commit. Newly created repositories default private; it does not alter visibility
of an existing destination. Do not use a public destination without publication
approval. There is no automatic publish, GPU launch, training, or credential search.

## Local checks and outstanding acceptance

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:SSLKEYLOGFILE=''
python -m pytest tests/test_pretraining_counterfactual.py -q
```

Synthetic checks cover baseline parity/duplicate multiplicity, smooth full-support
weights, valence contrast, exact sampler resume/exposure counts, provenance exports,
partial-scan refusal, pinned-revision rejection and cumulative budget reservations.
Cloud container build, full source census, encoder validity, CUDA training/resume,
HF publication and trained-model CPI acceptance remain untested until authorized.
