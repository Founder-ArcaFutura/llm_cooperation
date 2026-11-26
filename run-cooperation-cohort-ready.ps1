<#
  Expanded Phase 0 overnight cohort runner for llm_cooperation.
  Windows PowerShell 5.1 / PowerShell 7.
  Invoke from the repository root, or place this file in G:\llm_cooperation.

  Paid compute: each model launches Modal GPU inference. Defaults to five A10G
  checkpoints; -IncludeL40S adds three larger checkpoints.

  Important: keep the computer powered on and the user session running.
  The script requests that Windows not enter idle sleep while it is running,
  but it cannot override lid-close, hibernation, logout, or shutdown policies.
#>
[CmdletBinding()]
param(
    [switch]$IncludeL40S
)

$ErrorActionPreference = 'Stop'

# Find the repository, even if the script is executed from Downloads.
$root = 'G:\llm_cooperation'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'modal_app.py')) {
    $root = $PSScriptRoot
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'modal_app.py'))) {
    throw "Cannot find modal_app.py. Save this script into G:\llm_cooperation or update `$root."
}
Set-Location -LiteralPath $root

foreach ($command in @('modal', 'llm-coop', 'git')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command"
    }
}

$bankPath = Join-Path $root 'data\scenarios_v1_expanded.json'
if (-not (Test-Path -LiteralPath $bankPath)) {
    throw 'Expanded scenario bank not found; update your jules_integration branch first.'
}

# These checkpoints are ungated. Do not force a lookup for the missing
# Modal secret named 'huggingface-secret'. This does not delete stored secrets.
Remove-Item Env:MODAL_USE_HF_SECRET -ErrorAction SilentlyContinue
Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:HUGGING_FACE_HUB_TOKEN -ErrorAction SilentlyContinue
$env:NO_COLOR = '1'

$helpOutput = & modal run modal_app.py --help 2>&1 | Out-String
if (($LASTEXITCODE -ne 0) -or ($helpOutput -notmatch '--bank') -or
    ($helpOutput -notmatch '--no-mock') -or ($helpOutput -notmatch '--authorize-paid-run')) {
    throw 'This modal_app.py does not expose the expanded paid-run options. Check the branch.'
}

$bankHash = (Get-FileHash -LiteralPath $bankPath -Algorithm SHA256).Hash.Substring(0, 12).ToLowerInvariant()
$gitHead = (& git rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not read the Git commit.' }

# Persistent local state outside the repository: no accidental git add of logs.
$stateBase = Join-Path $env:LOCALAPPDATA 'llm_cooperation\cohorts'
$stateDir = Join-Path $stateBase "expanded_${bankHash}_${gitHead}"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$resultsDir = Join-Path $root 'results'
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
$summaryPath = Join-Path $stateDir 'summary.csv'

# Small GPU default cohort: base checkpoints only.
$models = @(
    'EleutherAI/pythia-2.8b',
    'HuggingFaceTB/SmolLM2-1.7B',
    'ibm-granite/granite-3.3-2b-base',
    'tiiuae/Falcon3-3B-Base',
    'Qwen/Qwen2.5-1.5B'
)

# Additional paid L40S tests, deliberately opt-in.
if ($IncludeL40S) {
    $models += @(
        'mistralai/Mistral-7B-v0.3',
        'deepseek-ai/deepseek-llm-7b-base',
        'allenai/OLMo-2-1124-7B'
    )
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][string[]]$CommandArguments,
        [Parameter(Mandatory=$true)][string]$LogPath
    )
    $lines = New-Object 'System.Collections.Generic.List[string]'
    # Windows PowerShell can wrap external stderr in a nonterminating ErrorRecord.
    $ErrorActionPreference = 'Continue'
    & $Executable @CommandArguments 2>&1 | ForEach-Object {
        $line = [string]$_
        Write-Host $line
        [void]$lines.Add($line)
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
    $nativeExit = $LASTEXITCODE
    return [PSCustomObject]@{
        ExitCode = $nativeExit
        Text = ($lines -join "`n")
    }
}

$summary = New-Object 'System.Collections.Generic.List[object]'
$keepAwake = $false
try {
    # Idle-sleep inhibition during this PowerShell process (Windows only).
    # No permanent Windows power-settings changes.
    try {
        Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class CohortPowerControl {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@ -ErrorAction Stop
        $keepAwake = ([CohortPowerControl]::SetThreadExecutionState([uint32]2147483649) -ne 0)
        if (-not $keepAwake) { Write-Warning 'Idle-sleep inhibition was not accepted by Windows.' }
    }
    catch {
        Write-Warning "Could not request idle-sleep inhibition: $_"
    }

    Write-Host "`n=== EXPANDED COHORT: $($models.Count) MODELS ===" -ForegroundColor Cyan
    Write-Host "Repo commit: $gitHead | Expanded bank SHA256 prefix: $bankHash"
    Write-Host "Raw output: $resultsDir"
    Write-Host "Run logs and resume markers: $stateDir"
    Write-Host 'Paid GPU compute is explicitly authorized for each attempted model.' -ForegroundColor Yellow
    Write-Host 'Keep this PowerShell process running and the computer powered on.' -ForegroundColor Yellow

    foreach ($model in $models) {
        $safe = $model -replace '[^A-Za-z0-9_.-]', '_'
        $resultMarker = Join-Path $stateDir "$safe.result.txt"
        $doneMarker = Join-Path $stateDir "$safe.complete.txt"
        $failureMarker = Join-Path $stateDir "$safe.launch-failed.txt"
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
                Write-Host "Skipping completed model: $filename"
                $status = 'SKIPPED_COMPLETE'
                continue
            }
            if (Test-Path -LiteralPath $failureMarker) {
                Write-Warning "Previous launch failed; skipping to avoid automatic paid retries. See: $runLog"
                $status = 'SKIPPED_PREVIOUS_FAILURE'
                continue
            }

            if (Test-Path -LiteralPath $resultMarker) {
                $filename = (Get-Content -LiteralPath $resultMarker -Raw).Trim()
                Write-Host "Resuming retrieval/analysis for existing remote result: $filename"
            }
            else {
                $runArgs = @('run', 'modal_app.py', '--model', $model,
                             '--bank', 'expanded', '--precision', 'bfloat16',
                             '--no-mock', '--authorize-paid-run')
                $run = Invoke-LoggedCommand -Executable 'modal' -CommandArguments $runArgs -LogPath $runLog
                if ($run.ExitCode -ne 0) {
                    Set-Content -LiteralPath $failureMarker -Value "Modal exit: $($run.ExitCode)" -Encoding UTF8
                    throw "Modal launch failed with exit code $($run.ExitCode)"
                }

                $match = [regex]::Match(
                    $run.Text,
                    'modal volume get llm-coop-results\s+(run_[^\s/\\]+\.jsonl)\s+results[/\\]'
                )
                if (-not $match.Success) {
                    # A successful command without a verifiable result path is not safe to retry.
                    Set-Content -LiteralPath $failureMarker -Value 'No result filename in Modal output; inspect log/volume manually.' -Encoding UTF8
                    throw 'Could not extract a durable JSONL filename from the Modal output.'
                }
                $filename = $match.Groups[1].Value
                # Write immediately after a paid success: resume never rebuys this run.
                Set-Content -LiteralPath $resultMarker -Value $filename -Encoding UTF8
            }

            $localFile = Join-Path $resultsDir $filename
            if (-not (Test-Path -LiteralPath $localFile)) {
                $download = Invoke-LoggedCommand -Executable 'modal' -CommandArguments @(
                    'volume', 'get', 'llm-coop-results', $filename, 'results/'
                ) -LogPath $downloadLog
                if ($download.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $localFile)) {
                    throw 'Volume download failed or the downloaded JSONL file is missing.'
                }
            }
            else { Write-Host "Using already downloaded: $localFile" }

            $analysis = Invoke-LoggedCommand -Executable 'llm-coop' -CommandArguments @(
                'analyze', $localFile, '-o', 'reports'
            ) -LogPath $analysisLog
            if ($analysis.ExitCode -ne 0) {
                throw "Local analysis failed with exit code $($analysis.ExitCode)"
            }

            Set-Content -LiteralPath $doneMarker -Value $filename -Encoding UTF8
            Write-Host "SUCCESS: $model -> $filename" -ForegroundColor Green
            $status = 'COMPLETE'
        }
        catch {
            $details = $_.Exception.Message
            $status = 'FAILED'
            Write-Warning "$model : $details"
            Write-Warning 'Continuing to the next model. Consult the logs for details.'
        }
        finally {
            [void]$summary.Add([PSCustomObject]@{
                utc_time = (Get-Date).ToUniversalTime().ToString('o')
                model = $model
                status = $status
                result_filename = $filename
                note = $details
                bank_hash_prefix = $bankHash
                git_commit = $gitHead
            })
            $summary | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8
        }
    }
}
finally {
    if ($keepAwake) {
        [void][CohortPowerControl]::SetThreadExecutionState([uint32]2147483648)
    }
}

Write-Host "`n=== BATCH FINISHED ===" -ForegroundColor Green
$summary | Format-Table model, status, result_filename -AutoSize
Write-Host "Summary: $summaryPath"
Write-Host "Raw JSONLs: $resultsDir"
Write-Host 'No Git commits or pushes were performed; review results before committing.'
