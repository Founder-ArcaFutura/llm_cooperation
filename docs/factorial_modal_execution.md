# Execute the existing factorial presentations on Modal

The existing `modal_app.py` consumes `ScenarioBank` objects, historical strategy enums and regenerated four-option Latin-square schedules. `modal_choice_set_followup.py` and `modal_cooperate_rewording.py` also load specific historical banks. They cannot directly execute this JSONL's frozen binary/four-action presentations. `modal_six_case_feasibility.py` is a different fixed-model, fixed-four-option instrument. None provides the needed factorial result join or analysis.

The new `modal_factorial_cooperation.py` is a thin adapter: it uses the existing `ModelRunner` loader, `answer_token_ids` boundary resolver, `parse_response` parser, `llm-coop-hf-cache` and `llm-coop-results` volumes, L40S profile and the pinned runtime from the OLMo behavioral runner. Its only new scoring logic adapts the existing next-token procedure to the displayed action set, preserves exact ties, and records action mappings. It does not translate actions into historical COOPERATE/COMPETE labels or regenerate option schedules.

No paid inference was executed while implementing or testing this adapter. Runtime/image construction, GPU loading and genuine tokenizer/model compatibility remain to be verified by the user-run smoke jobs. The design and all historical evidence are unchanged. These remain unreviewed development stimuli; resulting analyses are descriptive.

## Local preflight

Run from PowerShell in the same environment used for the existing Modal jobs:

```powershell
Set-Location G:\llm_cooperation
python -m modal --version
python -m llm_cooperation.factorial_inference preflight
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest tests\test_factorial_inference.py tests\test_factorial_cooperation_design.py tests\test_multidimensional_cooperation_study.py -q
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
```

Preflight validates every condition reference, exact stem/options, action mapping, unique ID and complete option-permutation schedule. It prints file/schedule hashes and 4,576 full / 44 smoke presentations. It makes no Modal, Hugging Face or inference calls. The adapter only adds the candidate-letter instruction and `Answer:` suffix to the supplied stem and options. The stem's existing question remains unchanged. Input validation rejects inconsistencies instead of editing them.

Modal authentication is assumed from the existing setup. If missing, use `python -m modal setup`. If your existing runs use the named `huggingface-secret`, set `$env:MODAL_USE_HF_SECRET = '1'` in this PowerShell session; otherwise leave it unset. This reuses that secret and does not create or print credentials.

## Define run names and model pins

Keep this PowerShell session open across the following blocks. These immutable pins come from the existing `data/cooperate_rewording_model_manifest.json`, not an unpinned download of `main`.

```powershell
$factorialBatch = 'factorial_v1_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$factorialModels = @(
    @{ Key = 'qwen7b'; Model = 'Qwen/Qwen2.5-7B'; Revision = 'd149729398750b98c0af14eb82c78cfe92750796' },
    @{ Key = 'olmo7b'; Model = 'allenai/OLMo-2-1124-7B'; Revision = '7df9a82518afdecae4e8c026b27adccc8c1f0032' },
    @{ Key = 'mistral7b'; Model = 'mistralai/Mistral-7B-v0.3'; Revision = 'caa1feb0e54d415e2df31207e5f4e273e33509b1' }
)
New-Item -ItemType Directory -Force -Path results\factorial | Out-Null
$factorialModels | ConvertTo-Json | Set-Content -Encoding UTF8 "results\factorial\${factorialBatch}_models.json"
Write-Host "Batch: $factorialBatch"
```

The saved file records aliases and pins; the batch name is embedded in its filename. Run IDs contain the batch, model alias and scope. Do not reuse IDs for different inputs or model revisions.

## GPU smoke test, retrieval and diagnostics

This block **does launch paid GPU inference when you execute it**. It runs sequentially for all three models, using 44 actual source presentations each: one per block/factor-cell/choice-set combination across the two domains, with identities/orders selected deterministically from the original schedule. The smoke output is a diagnostic subset, not a complete factorial or a spending limit.

```powershell
foreach ($factorialModel in $factorialModels) {
    $factorialRun = "${factorialBatch}_$($factorialModel.Key)_smoke"
    python -m modal run --detach modal_factorial_cooperation.py --model $factorialModel.Model --revision $factorialModel.Revision --run-id $factorialRun --smoke
    if ($LASTEXITCODE -ne 0) { throw "Smoke failed: $factorialRun" }
    New-Item -ItemType Directory -Force -Path "results/factorial/$factorialRun" | Out-Null
    python -m modal volume get llm-coop-results "factorial/$factorialRun" "results/factorial/$factorialRun"
    if ($LASTEXITCODE -ne 0) { throw "Smoke retrieval failed: $factorialRun" }
    python -m llm_cooperation.factorial_inference analyze --runs "results/factorial/$factorialRun" --output "reports/factorial/$factorialRun" --allow-smoke
    if ($LASTEXITCODE -ne 0) { throw "Smoke analysis failed: $factorialRun" }
}
```

Inspect each `reports/factorial/<run-id>/diagnostics.csv` and downloaded `summary.json`: completion, finite scores, mapped A/B versus A/B/C/D candidates, token IDs, exact ties and generated-answer validity. Low free-generation validity is recorded separately from forced-choice results and is not automatically a reason to discard the assay. Smoke analysis deliberately emits no factorial contrasts, since its strata/permutations are incomplete. Choose whether to revise the instrument before launching the full jobs; this document does not automate a scientific approval decision.

`--detach` keeps the remote app alive if the client disconnects; the CLI normally still waits for completion. A nonzero CLI exit after disconnect does not prove that remote inference failed. Inspect the Modal app/volume before rerunning the same ID; use `--resume` only after the prior worker has stopped, so two workers never append to the same run.

## Full inference

After inspecting the smoke results, execute:

```powershell
foreach ($factorialModel in $factorialModels) {
    $factorialRun = "${factorialBatch}_$($factorialModel.Key)_full"
    python -m modal run --detach modal_factorial_cooperation.py --model $factorialModel.Model --revision $factorialModel.Revision --run-id $factorialRun
    if ($LASTEXITCODE -ne 0) { throw "Full run failed or client disconnected: $factorialRun" }
}
```

Each model scores all 4,576 presentations in bfloat16 on L40S: 13,728 full presentations across the three models. Five greedy completion tokens are also retained as in the existing harness. Candidate logits and softmax use float32; binary probabilities normalize over A/B only. Full-vocabulary log probabilities are stored separately. Exact raw-logit ties have no arbitrary single winner. No prompt truncation, dollar cap, presentation cap or reduced full-run subset is imposed. The function uses the existing OLMo runner's 24-hour operational timeout and zero automatic retries; checkpoints allow explicit continuation after interruption.

All input data are read from `research/factorial_cooperation_v1` and archived byte-for-byte with the new results. No inference outputs are written back to the design directory. Results are committed every 25 presentations and on completion/failure. The manifest records source hashes, rendered-schedule hash, model revision, scoring-code hashes, prompt format, scope, seed and expected count. The summary records the resolved revision, runtime and completion status.

## Retrieve full results and generate analysis

```powershell
$factorialRunPaths = @()
foreach ($factorialModel in $factorialModels) {
    $factorialRun = "${factorialBatch}_$($factorialModel.Key)_full"
    New-Item -ItemType Directory -Force -Path "results/factorial/$factorialRun" | Out-Null
    python -m modal volume get llm-coop-results "factorial/$factorialRun" "results/factorial/$factorialRun"
    if ($LASTEXITCODE -ne 0) { throw "Full retrieval failed: $factorialRun" }
    $factorialRunPaths += "results/factorial/$factorialRun"
}
python -m llm_cooperation.factorial_inference analyze --runs $factorialRunPaths --output "reports/factorial/$factorialBatch"
if ($LASTEXITCODE -ne 0) { throw 'Full analysis failed' }
Get-Content "reports/factorial/$factorialBatch/REPORT.md"
```

The command verifies the source hashes and all rendered records, mappings, scores, tie handling and complete expected ID set before computing results. It rejects incomplete runs and refuses to mix smoke runs into full analysis. If the original development inputs later change, analyze using their archived copy with `--input results/factorial/<run-id>/presentations_input.jsonl`; its neighboring `candidate_conditions.json` is the matching snapshot.

Outputs:

- `condition_strata.csv`: per-condition/identity/wording/choice-set probabilities for all actions, target probability, tie-inclusive fractional target rate, unique-max target rate and generated-answer validity.
- `family_contrasts.csv`: within-family time effects, mechanism package contrasts at each time level, mechanism × time differences, return/necessity contrasts and difference-in-differences. Identity and sentence-order strata are averaged equally; binary and four-action sets remain separate.
- `model_comparisons.csv`: matched differences between model-specific contrasts in the same family/block/choice set.
- `diagnostics.csv`, `analysis_manifest.json`, `REPORT.md`: position/generation/tie diagnostics, provenance and scope.

These are descriptive contrasts, not population-level confidence intervals, p-values or evidence that a pure latent mechanism has been isolated. There are only two exposed domain implementations. Incentive/outcome coupling remains as documented in the preserved design report. Raw stratum outputs support further identity, framing and choice-set inspection without pooling away those distinctions.

## Retrieve after a disconnect; resume a stopped partial run

Recover the original `$factorialBatch` and run IDs; do not create a new batch merely to retrieve existing data:

```powershell
# Example: Qwen full run from the same batch.
$factorialRun = "${factorialBatch}_qwen7b_full"
python -m modal volume ls llm-coop-results "factorial/$factorialRun"
New-Item -ItemType Directory -Force -Path "results/factorial/$factorialRun" | Out-Null
python -m modal volume get llm-coop-results "factorial/$factorialRun" "results/factorial/$factorialRun" --force
# Only once the previous worker has stopped:
python -m modal run --detach modal_factorial_cooperation.py --model 'Qwen/Qwen2.5-7B' --revision 'd149729398750b98c0af14eb82c78cfe92750796' --run-id $factorialRun --resume
# Refresh the local snapshot, then rerun the analysis to a new output directory.
New-Item -ItemType Directory -Force -Path "results/factorial/$factorialRun" | Out-Null
python -m modal volume get llm-coop-results "factorial/$factorialRun" "results/factorial/$factorialRun" --force
```

Resume requires identical source bytes, scope, model revision and code hashes, validates existing records and skips completed presentation IDs. A torn final append is saved as an `interrupted_tail_*.bin` artifact before removal; malformed complete rows are rejected. A completed identical run returns its existing path without reloading the model. Reusing a run ID without `--resume` is refused. Separate replicate runs need separate IDs and separate analyses; they must not be counted as independent families.
