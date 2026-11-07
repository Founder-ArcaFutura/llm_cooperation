[CmdletBinding()]
param(
    [switch] $IncludeGated,
    [switch] $AuthorizePaidRun,
    [switch] $PreviewOnly,
    [switch] $ListOnly,
    [int] $BootstrapSamples = 2000
)

$ErrorActionPreference = 'Stop'
# Ten additional previously screened base checkpoints. The completed Qwen-3B,
# Mistral-7B and OLMo-7B batch is reused, rather than paid for again.
$models = @(
    'HuggingFaceTB/SmolLM2-1.7B',
    'ibm-granite/granite-3.3-2b-base',
    'tiiuae/Falcon3-3B-Base',
    'Qwen/Qwen2.5-1.5B',
    'Qwen/Qwen2.5-7B',
    'deepseek-ai/deepseek-llm-7b-base',
    'microsoft/phi-2'
)
if ($IncludeGated) {
    $models += @('meta-llama/Llama-3.2-3B', 'google/gemma-2-2b', 'google/gemma-2-9b')
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$bankHash = (Get-FileHash (Join-Path $root 'data/scenarios_dose_response_exploratory.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$calHash = (Get-FileHash (Join-Path $root 'data/calibration_bank.json') -Algorithm SHA256).Hash.ToLowerInvariant()
$recoveryNeeded = @()
foreach ($file in Get-ChildItem (Join-Path $root 'results/dose_response_batch') -Filter batch_manifest.json -Recurse -File) {
    $prior = Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName | ConvertFrom-Json
    if ($prior.bank_sha256 -ne $bankHash -or $prior.calibration_bank_sha256 -ne $calHash) { continue }
    foreach ($entry in $prior.model_runs) {
        if ($models -notcontains $entry.model) { continue }
        if ($entry.status -eq 'complete' -and $entry.raw_results -and $entry.calibration_results -and $entry.calibration_summary -and
            (Test-Path -LiteralPath $entry.raw_results) -and (Test-Path -LiteralPath $entry.calibration_results) -and
            (Test-Path -LiteralPath $entry.calibration_summary) -and (Test-Path -LiteralPath (Join-Path $entry.report_dir 'dose_response_report.md'))) {
            $raw = Get-Content -Encoding UTF8 -LiteralPath $entry.raw_results -TotalCount 1 | ConvertFrom-Json
            $cal = Get-Content -Encoding UTF8 -LiteralPath $entry.calibration_results -TotalCount 1 | ConvertFrom-Json
            if (-not $raw.mock -and -not $cal.mock -and $raw.model_name -eq $entry.model -and $cal.model_name -eq $entry.model -and
                $entry.revision -match '^[0-9a-f]{40}$' -and $raw.model_revision -eq $entry.revision -and $cal.model_revision -eq $entry.revision -and
                $raw.scenario_bank_hash -eq $bankHash -and $cal.calibration_bank_hash -eq $calHash -and
                $raw.num_presentations -eq 504 -and $cal.num_presentations -eq 96 -and
                @(Get-Content -LiteralPath $entry.raw_results).Count -eq 505 -and @(Get-Content -LiteralPath $entry.calibration_results).Count -eq 97) {
                Write-Host "Reusing completed $($entry.model) from $($file.Directory.Name)"
                $models = @($models | Where-Object { $_ -ne $entry.model })
            }
        }
        if ($models -contains $entry.model -and $entry.modal_log -and (Test-Path -LiteralPath $entry.modal_log)) {
            $log = Get-Content -Raw -Encoding UTF8 -LiteralPath $entry.modal_log
            if ($log -match '\[modal_app\] Successfully finished run!' -and $log -match '\[modal_app\] Calibration output persisted') {
                $recoveryNeeded += [pscustomobject]@{Model=$entry.model; Batch=$file.Directory.FullName}
            }
        }
    }
}
foreach ($pending in $recoveryNeeded) {
    if ($models -contains $pending.Model) {
        $message = "Recover saved $($pending.Model) before more paid inference: .\scripts\recover_dose_response_batch.ps1 -BatchDirectory '$($pending.Batch)'"
        if ($ListOnly) { Write-Warning $message } else { throw $message }
    }
}
Write-Host ("Expansion: {0} additional models; existing three-model dose-response batch is excluded." -f $models.Count)
$models | ForEach-Object { Write-Host " - $_" }
if ($ListOnly) { return }
if ($models.Count -eq 0) { Write-Host 'All selected expansion models are already complete.'; return }
if (-not $PreviewOnly -and -not $AuthorizePaidRun) {
    throw 'Pass -AuthorizePaidRun for paid GPU inference, -PreviewOnly for network preflight, or -ListOnly for an offline model list.'
}
$previousSecretSetting = $env:MODAL_USE_HF_SECRET
try {
    if ($IncludeGated) {
        Write-Host "Gated models require accepted model licenses and Modal secret 'huggingface-secret' containing HF_TOKEN."
        $env:MODAL_USE_HF_SECRET = '1'
    }
    & (Join-Path $PSScriptRoot 'run_dose_response_models.ps1') -Models $models `
        -AuthorizePaidRun:$AuthorizePaidRun -PreviewOnly:$PreviewOnly -BootstrapSamples $BootstrapSamples
} finally {
    $env:MODAL_USE_HF_SECRET = $previousSecretSetting
}
