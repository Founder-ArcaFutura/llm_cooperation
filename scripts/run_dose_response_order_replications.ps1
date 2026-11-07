[CmdletBinding()]
param(
    [switch] $AuthorizePaidRun,
    [switch] $PrepareOnly,
    [string] $PlanPath = 'research/dose_response_order_replications_v1/plan.json'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $root
$oldSecret = $env:MODAL_USE_HF_SECRET
try {
    & python -m llm_cooperation.analysis.order_replications prepare --plan $PlanPath
    if ($LASTEXITCODE -ne 0) { throw 'Frozen order-replication plan audit failed.' }
    $plan = Get-Content -Raw -Encoding UTF8 -LiteralPath $PlanPath | ConvertFrom-Json
    Write-Host ("Plan: {0} jobs, {1} models, {2} presentations including calibration." -f $plan.jobs.Count, $plan.models.Count, ($plan.jobs.Count * 600))
    $plan.models | ForEach-Object { Write-Host (" - {0}: schedules 1 and 2, revision {1}" -f $_.model, $_.revision) }
    if ($PrepareOnly) { Write-Host 'Preparation only. No inference launched.'; return }
    if (-not $AuthorizePaidRun) { throw 'Pass -AuthorizePaidRun to authorize the planned GPU jobs, or -PrepareOnly for local validation.' }
    $env:MODAL_USE_HF_SECRET = '1'
    foreach ($job in $plan.jobs) {
        $manifestPath = Join-Path $root "results/dose_response_orders/$($job.tag)/batch_manifest.json"
        if (Test-Path -LiteralPath $manifestPath) {
            $existing = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
            if ($existing.model_runs.Count -eq 1 -and $existing.model_runs[0].status -eq 'complete') {
                Write-Host "Reusing completed $($job.tag); validation follows before comparison."
                continue
            }
            throw "Existing incomplete job. Recover without inference, then rerun this command: .\scripts\recover_dose_response_batch.ps1 -BatchDirectory '$(Split-Path -Parent $manifestPath)'"
        }
        $pins = @{}; $pins[$job.model] = $job.revision
        & (Join-Path $PSScriptRoot 'run_dose_response_models.ps1') -Models @($job.model) `
            -Revisions $pins -OrderReplication $job.order_replication -OrderSeed $plan.order_seed `
            -Seed $job.model_seed -Precision $job.precision `
            -OutputGroup dose_response_orders -BatchTag $job.tag -AuthorizePaidRun
    }
    & python -m llm_cooperation.analysis.order_replications compare --plan $PlanPath
    if ($LASTEXITCODE -ne 0) { throw 'Cross-schedule comparison validation failed; all raw results are preserved.' }
} finally {
    $env:MODAL_USE_HF_SECRET = $oldSecret
    Pop-Location
}
