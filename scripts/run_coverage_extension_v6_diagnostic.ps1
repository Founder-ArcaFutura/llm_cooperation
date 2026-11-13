$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$captureStamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
$captureRoot = "results/coverage_extension_v6/capture_$captureStamp"
$reportRoot = "reports/coverage_extension_v6/capture_$captureStamp"
if (Test-Path -LiteralPath $captureRoot) { throw "Capture directory already exists: $captureRoot" }
New-Item -ItemType Directory -Path $captureRoot -Force | Out-Null
$models = @(
    @{ Key = 'qwen7b'; Name = 'Qwen/Qwen2.5-7B' },
    @{ Key = 'olmo7b'; Name = 'allenai/OLMo-2-1124-7B' },
    @{ Key = 'mistral7b'; Name = 'mistralai/Mistral-7B-v0.3' }
)
$choicePaths = @()
$probePaths = @()
foreach ($entry in $models) {
    $choiceRun = "coverage_extension_v6_$($entry.Key)"
    $probeRun = "${choiceRun}_comprehension"
    Write-Host "Starting diagnostic for $($entry.Name)"
    python -m modal run --detach modal_coverage_extension_v6.py --model $entry.Name --run-id $choiceRun --approved --diagnostic --resume
    if ($LASTEXITCODE -ne 0) { throw "Diagnostic failed or disconnected: $choiceRun. Check the Modal app before resuming." }
    Write-Host "Starting separate comprehension probes for $($entry.Name)"
    python -m modal run --detach modal_coverage_extension_v6.py --model $entry.Name --run-id $probeRun --approved --comprehension --resume
    if ($LASTEXITCODE -ne 0) { throw "Comprehension run failed or disconnected: $probeRun. Check the Modal app before resuming." }
    foreach ($remoteRun in @($choiceRun, $probeRun)) {
        $destination = "$captureRoot/$remoteRun"
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        foreach ($resultFile in @('manifest.json', 'summary.json', 'rows.jsonl')) {
            python -m modal volume get llm-coop-results "coverage_extension_v6/$remoteRun/$resultFile" "$destination/$resultFile"
            if ($LASTEXITCODE -ne 0) { throw "Download failed: $remoteRun/$resultFile" }
        }
    }
    $choicePaths += "$captureRoot/$choiceRun"
    $probePaths += "$captureRoot/$probeRun"
}
python -m llm_cooperation.coverage_extension_analysis_v6 --runs $choicePaths --output "$reportRoot/choice"
if ($LASTEXITCODE -ne 0) { throw 'Choice analysis failed' }
python -m llm_cooperation.coverage_extension_comprehension --runs $probePaths --output "$reportRoot/comprehension"
if ($LASTEXITCODE -ne 0) { throw 'Comprehension analysis failed' }
Write-Host "Choice diagnostics: $reportRoot/choice/position_diagnostics.csv"
Write-Host "Comprehension probes: $reportRoot/comprehension/comprehension_summary.csv"
