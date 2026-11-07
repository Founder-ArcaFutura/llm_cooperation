[CmdletBinding()]
param([Parameter(Mandatory=$true)][string] $BatchDirectory, [int] $BootstrapSamples = 2000)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$batch = (Resolve-Path -LiteralPath $BatchDirectory).Path
if (-not $batch.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Recovery batch must be within this repository.'
}
$manifestPath = Join-Path $batch 'batch_manifest.json'
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$oldUtf8 = $env:PYTHONUTF8
$oldIo = $env:PYTHONIOENCODING
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Invoke-RecoveryCommand {
    param([string] $Executable, [string[]] $Arguments)
    # PS 5.1 wraps native stderr (including progress messages) as ErrorRecords.
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments 2>&1 | ForEach-Object { Write-Host ([string]$_) }
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "$Executable exited with status $code during recovery." }
}

Push-Location $root
try {
    $bankHash = (Get-FileHash data/scenarios_dose_response_exploratory.json -Algorithm SHA256).Hash.ToLowerInvariant()
    $calHash = (Get-FileHash data/calibration_bank.json -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($manifest.bank_sha256 -ne $bankHash -or $manifest.calibration_bank_sha256 -ne $calHash) {
        throw 'Batch bank hashes do not match the current frozen banks.'
    }
    $backup = "$manifestPath.before_recovery.json"
    if (-not (Test-Path -LiteralPath $backup)) { Copy-Item -LiteralPath $manifestPath -Destination $backup }
    foreach ($entry in $manifest.model_runs) {
        if ($entry.status -eq 'complete') { continue }
        if (-not $entry.modal_log -or -not (Test-Path -LiteralPath $entry.modal_log)) {
            throw "No captured Modal log available for $($entry.model). Recovery cannot launch inference."
        }
        $log = Get-Content -Raw -Encoding UTF8 -LiteralPath $entry.modal_log
        $rawMatch = [regex]::Match($log, '(?m)^\[modal_app\] Successfully finished run! Output persisted on Modal Volume at: (.+)$')
        $calMatch = [regex]::Match($log, '(?m)^\[modal_app\] Calibration output persisted on Modal Volume at: (.+)$')
        if (-not $rawMatch.Success -or -not $calMatch.Success) { throw "No remote completion markers for $($entry.model); inspect its log." }
        $rawName = [IO.Path]::GetFileName($rawMatch.Groups[1].Value.Trim())
        $calName = [IO.Path]::GetFileName($calMatch.Groups[1].Value.Trim())
        $modelDir = Split-Path -Parent $entry.modal_log
        foreach ($path in @($modelDir, $entry.report_dir)) {
            if (-not ([IO.Path]::GetFullPath($path)).StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Artifact path is outside this repository.'
            }
        }
        foreach ($name in @($rawName, $calName, "$calName.summary.json")) {
            if (-not (Test-Path -LiteralPath (Join-Path $modelDir $name))) {
                Invoke-RecoveryCommand -Executable 'modal' -Arguments @('volume','get','llm-coop-results',$name,$modelDir)
            }
        }
        $rawPath = Join-Path $modelDir $rawName
        $calPath = Join-Path $modelDir $calName
        $rawHeader = Get-Content -Encoding UTF8 -LiteralPath $rawPath -TotalCount 1 | ConvertFrom-Json
        $calHeader = Get-Content -Encoding UTF8 -LiteralPath $calPath -TotalCount 1 | ConvertFrom-Json
        if ($rawHeader.mock -or $calHeader.mock -or $rawHeader.model_name -ne $entry.model -or $calHeader.model_name -ne $entry.model -or
            $rawHeader.model_revision -ne $entry.revision -or $calHeader.model_revision -ne $entry.revision -or
            $rawHeader.scenario_bank_hash -ne $bankHash -or $calHeader.calibration_bank_hash -ne $calHash) {
            throw 'Recovered metadata does not match the batch model/revision/bank.'
        }
        if ($rawHeader.num_presentations -ne 504 -or $calHeader.num_presentations -ne 96 -or
            @(Get-Content -LiteralPath $rawPath).Count -ne 505 -or @(Get-Content -LiteralPath $calPath).Count -ne 97) {
            throw 'Recovered run has incomplete presentation counts.'
        }
        Invoke-RecoveryCommand -Executable 'python' -Arguments @('-m','llm_cooperation.cli','analyze-dose-response',$rawPath,'--output-dir',$entry.report_dir,'--bootstrap-samples',"$BootstrapSamples")
        $entry.raw_results = $rawPath
        $entry.calibration_results = $calPath
        $entry.calibration_summary = Join-Path $modelDir "$calName.summary.json"
        $entry.status = 'complete'
        $entry.error = $null
        $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        Write-Host "Recovered $($entry.model) without inference. Report: $($entry.report_dir)"
    }
} finally {
    Pop-Location
    $env:PYTHONUTF8 = $oldUtf8
    $env:PYTHONIOENCODING = $oldIo
}
