<#
  Phase 0B Utility-Matched Cooperation Assay — resumable multi-model runner
  Windows PowerShell 5.1 / PowerShell 7

  Examples (from G:\llm_cooperation):
    .\run-cooperation-phase0b-cohort.ps1 -Preset Large -DryRun
    .\run-cooperation-phase0b-cohort.ps1 -Preset Large -AuthorizePaidCohort
    .\run-cooperation-phase0b-cohort.ps1 -Preset Small -MaxModels 2 -AuthorizePaidCohort
    .\run-cooperation-phase0b-cohort.ps1 -Preset All -AuthorizePaidCohort
    .\run-cooperation-phase0b-cohort.ps1 -Models 'Qwen/Qwen2.5-7B','mistralai/Mistral-7B-v0.3' -AuthorizePaidCohort

  Confirmatory is deliberately opt-in and must be scientifically approved first.
  No git commits or pushes are made.
#>
[CmdletBinding()]
param(
    [ValidateSet('Small', 'Large', 'All')]
    [string]$Preset = 'Large',

    [string[]]$Models = @(),

    [ValidateRange(1, 25)]
    [int]$MaxModels = 8,

    [ValidateSet('exploratory', 'confirmatory', 'all')]
    [string]$Split = 'exploratory',

    [switch]$AuthorizePaidCohort,
    [switch]$AuthorizeConfirmatory,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# Prefer the script's own repository folder; fall back to the established drive location.
$root = 'G:\llm_cooperation'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'modal_app.py')) {
    $root = $PSScriptRoot
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'modal_app.py'))) {
    throw 'Cannot locate modal_app.py. Place this script in G:\llm_cooperation.'
}
Set-Location -LiteralPath $root

foreach ($command in @('modal', 'llm-coop', 'git')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command"
    }
}

$bankPath = Join-Path $root 'data\scenarios_phase0b_utility_matched.json'
if (-not (Test-Path -LiteralPath $bankPath)) {
    throw 'Missing Phase 0B bank. Switch to updated phase0b-finalize and pull.'
}
$modalSource = Get-Content -LiteralPath (Join-Path $root 'modal_app.py') -Raw
if ($modalSource -notmatch 'resolve_bank_and_split' -or $modalSource -notmatch 'split_filter') {
    throw 'Local modal_app.py lacks Phase 0B routing. Update to the branch containing PR #6.'
}

if ($Split -ne 'exploratory' -and -not $AuthorizeConfirmatory) {
    throw 'Confirmatory or all-split execution requires -AuthorizeConfirmatory and prior scientific review.'
}

# Avoid accidentally authenticating or attempting gated models by default.
$smallModels = @(
    'HuggingFaceTB/SmolLM2-1.7B',
    'ibm-granite/granite-3.3-2b-base',
    'tiiuae/Falcon3-3B-Base',
    'Qwen/Qwen2.5-1.5B'
)
$largeModels = @(
    'mistralai/Mistral-7B-v0.3',
    'allenai/OLMo-2-1124-7B',
    'deepseek-ai/deepseek-llm-7b-base',
    'Qwen/Qwen2.5-7B'
)

if ($Models.Count -gt 0) {
    $selectedModels = @($Models)
} elseif ($Preset -eq 'Small') {
    $selectedModels = @($smallModels)
} elseif ($Preset -eq 'Large') {
    $selectedModels = @($largeModels)
} else {
    $selectedModels = @($smallModels + $largeModels)
}
$selectedModels = @($selectedModels | Select-Object -Unique | Select-Object -First $MaxModels)
if ($selectedModels.Count -eq 0) { throw 'No models selected.' }

# Known bank composition: 30 exploratory templates, 32 confirmatory, two partners each.
$expectedScenarios = switch ($Split) {
    'exploratory'  { 60 }
    'confirmatory' { 64 }
    'all'          { 124 }
}
$expectedPresentations = $expectedScenarios * 4

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:NO_COLOR = '1'
try {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
} catch { }

$helpOutput = (& modal run modal_app.py --help 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $helpOutput -notmatch '--bank' -or
    $helpOutput -notmatch '--split' -or $helpOutput -notmatch '--authorize-confirmatory' -or
    $helpOutput -notmatch '--authorize-paid-run' -or $helpOutput -notmatch '--no-mock') {
    throw 'Modal CLI is not exposing Phase 0B and authorization options. Check checkout and environment.'
}

$bankHashFull = (Get-FileHash -LiteralPath $bankPath -Algorithm SHA256).Hash.ToLowerInvariant()
$bankHashShort = $bankHashFull.Substring(0, 12)
$gitHead = (& git rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $gitHead) { throw 'Cannot determine Git HEAD.' }

# State keyed by the exact scenario bank, code revision, and split. Avoids
# accidentally claiming a run from another experimental instrument as done.
$stateBase = Join-Path $env:LOCALAPPDATA 'llm_cooperation\cohorts'
$stateDir = Join-Path $stateBase "phase0b_${Split}_${bankHashShort}_${gitHead}"
$resultsDir = Join-Path $root 'results'
$reportsDir = Join-Path $root 'reports'
New-Item -ItemType Directory -Path $stateDir, $resultsDir, $reportsDir -Force | Out-Null
$summaryPath = Join-Path $stateDir 'summary.csv'

Write-Host "`n=== PHASE 0B: $Split / $($selectedModels.Count) BASE CHECKPOINTS ===" -ForegroundColor Cyan
Write-Host "Bank hash: $bankHashFull"
Write-Host "Git HEAD:  $gitHead"
Write-Host "Expected per model: $expectedScenarios scenarios / $expectedPresentations presentations"
Write-Host "State: $stateDir"
$selectedModels | ForEach-Object { Write-Host "  - $_" }

if ($DryRun) {
    Write-Host "Dry run only. No GPU requests made." -ForegroundColor Yellow
    return
}
if (-not $AuthorizePaidCohort) {
    throw 'Paid GPU compute not authorized. Add -AuthorizePaidCohort to launch the cohort.'
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [Parameter(Mandatory=$true)][string]$LogPath
    )
    $lines = New-Object 'System.Collections.Generic.List[string]'
    # External stderr can be a nonterminating PowerShell ErrorRecord.
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments 2>&1 | ForEach-Object {
        $line = [string]$_
        Write-Host $line
        [void]$lines.Add($line)
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
    $exit = $LASTEXITCODE
    return [PSCustomObject]@{ ExitCode = $exit; Text = ($lines -join "`n") }
}

$summary = New-Object 'System.Collections.Generic.List[object]'
$keepAwake = $false
try {
    try {
        Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class Phase0BCohortPowerControl {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@ -ErrorAction Stop
        $keepAwake = ([Phase0BCohortPowerControl]::SetThreadExecutionState([uint32]2147483649) -ne 0)
    } catch { Write-Warning "Could not request Windows idle-sleep inhibition: $_" }

    foreach ($model in $selectedModels) {
        $safe = $model -replace '[^A-Za-z0-9_.-]', '_'
        $resultMarker = Join-Path $stateDir "$safe.result.txt"
        $doneMarker = Join-Path $stateDir "$safe.complete.txt"
        $failedMarker = Join-Path $stateDir "$safe.launch-failed.txt"
        $runLog = Join-Path $stateDir "$safe.modal.log"
        $downloadLog = Join-Path $stateDir "$safe.download.log"
        $analysisLog = Join-Path $stateDir "$safe.analysis.log"
        $status = 'UNKNOWN'
        $filename = ''
        $details = ''
        Write-Host "`n=== $model ===" -ForegroundColor Cyan

        try {
            if (Test-Path -LiteralPath $doneMarker) {
                $filename = (Get-Content -LiteralPath $doneMarker -Raw).Trim()
                $status = 'SKIPPED_COMPLETE'
                Write-Host "Already completed: $filename"
                continue
            }
            if (Test-Path -LiteralPath $failedMarker) {
                $status = 'SKIPPED_PREVIOUS_FAILURE'
                Write-Warning "Prior launch failed. Inspect $runLog before attempting a paid retry."
                continue
            }

            if (Test-Path -LiteralPath $resultMarker) {
                $filename = (Get-Content -LiteralPath $resultMarker -Raw).Trim()
                Write-Host "Resuming download/analysis: $filename"
            } else {
                $runArgs = @('run', 'modal_app.py', '--model', $model,
                    '--bank', 'phase0b', '--split', $Split,
                    '--precision', 'bfloat16', '--no-mock', '--authorize-paid-run')
                if ($Split -ne 'exploratory') { $runArgs += '--authorize-confirmatory' }
                $run = Invoke-LoggedCommand -Executable 'modal' -Arguments $runArgs -LogPath $runLog
                if ($run.ExitCode -ne 0) {
                    Set-Content -LiteralPath $failedMarker -Value "Modal exit: $($run.ExitCode)" -Encoding UTF8
                    throw "Modal launch exited $($run.ExitCode). No automatic paid retry."
                }
                $match = [regex]::Match($run.Text,
                    'modal volume get llm-coop-results\s+(run_[^\s/\\]+\.jsonl)\s+results[/\\]')
                if (-not $match.Success) {
                    Set-Content -LiteralPath $failedMarker -Value 'No result marker. Inspect Modal volume before retrying.' -Encoding UTF8
                    throw 'Could not identify durable JSONL filename from Modal output.'
                }
                $filename = $match.Groups[1].Value
                # Never purchase inference a second time just because a download failed.
                Set-Content -LiteralPath $resultMarker -Value $filename -Encoding UTF8
            }

            $localFile = Join-Path $resultsDir $filename
            if (-not (Test-Path -LiteralPath $localFile)) {
                $dl = Invoke-LoggedCommand -Executable 'modal' -Arguments @(
                    'volume', 'get', 'llm-coop-results', $filename, 'results/'
                ) -LogPath $downloadLog
                if ($dl.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $localFile)) {
                    throw 'Volume download failed; result remains available remotely.'
                }
            }

            # Verify metadata before analysis so a wrong bank or an accidental mock run
            # cannot be silently reported as real Phase 0B evidence.
            $header = (Get-Content -LiteralPath $localFile -TotalCount 1 | Out-String).Trim() | ConvertFrom-Json
            if ($header.model_name -ne $model -or $header.mock -eq $true -or
                [int]$header.num_scenarios -ne $expectedScenarios -or
                [int]$header.num_presentations -ne $expectedPresentations) {
                throw "Run metadata mismatch: $($header.model_name), mock=$($header.mock), scenarios=$($header.num_scenarios), presentations=$($header.num_presentations)."
            }
            # Line-ending normalization between Windows Git and Modal can affect the
            # SHA256 of raw JSON bytes, so record a mismatch prominently rather than
            # claiming equality. Reconcile before using the run as scientific evidence.
            if ($header.scenario_bank_hash -and $header.scenario_bank_hash -ne $bankHashFull) {
                Write-Warning 'Local bank byte hash differs from remote-run hash. Confirm source revision and line endings.'
            }

            $an = Invoke-LoggedCommand -Executable 'llm-coop' -Arguments @(
                'analyze', $localFile, '-o', 'reports'
            ) -LogPath $analysisLog
            if ($an.ExitCode -ne 0) { throw "Local analysis exited $($an.ExitCode)" }

            Set-Content -LiteralPath $doneMarker -Value $filename -Encoding UTF8
            $status = 'COMPLETE'
            Write-Host "SUCCESS: $model -> $filename" -ForegroundColor Green
        }
        catch {
            $status = 'FAILED'
            $details = $_.Exception.Message
            Write-Warning "$model : $details"
            Write-Warning "Inspect logs in $stateDir; continuing to next model."
        }
        finally {
            [void]$summary.Add([PSCustomObject]@{
                utc_time = (Get-Date).ToUniversalTime().ToString('o')
                model = $model
                status = $status
                result_filename = $filename
                note = $details
                scenario_bank = 'phase0b'
                split = $Split
                bank_hash_local = $bankHashFull
                git_commit = $gitHead
            })
            $summary | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8
        }
    }
}
finally {
    if ($keepAwake) {
        [void][Phase0BCohortPowerControl]::SetThreadExecutionState([uint32]2147483648)
    }
}
Write-Host "`n=== PHASE 0B BATCH FINISHED ===" -ForegroundColor Green
$summary | Format-Table model, status, result_filename -AutoSize
Write-Host "Summary: $summaryPath"
Write-Host "Raw JSONL: $resultsDir"
Write-Host 'No git commits or pushes performed; review outputs and experimental provenance first.'
