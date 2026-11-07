[CmdletBinding()]
param(
    [string[]] $Models = @(
        "Qwen/Qwen2.5-3B",
        "mistralai/Mistral-7B-v0.3",
        "allenai/OLMo-2-1124-7B"
    ),
    [switch] $AuthorizePaidRun,
    [switch] $PreviewOnly,
    [int] $BootstrapSamples = 2000
)

$ErrorActionPreference = "Stop"
# Modal's Python CLI emits Unicode status symbols even when its output is
# redirected. Windows PowerShell otherwise gives Python a legacy code page.
$previousPythonUtf8 = $env:PYTHONUTF8
$previousPythonIoEncoding = $env:PYTHONIOENCODING
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    if (-not $PreviewOnly -and -not $AuthorizePaidRun) {
        throw "Live Modal inference costs money. Re-run with -AuthorizePaidRun after reviewing the plan, or use -PreviewOnly."
    }
    if ($Models.Count -eq 0) { throw "Provide at least one model." }
    if ($BootstrapSamples -lt 1) { throw "BootstrapSamples must be positive." }

    & python -m llm_cooperation.cli audit-items --bank dose-response --calibration-path data/calibration_bank.json
    if ($LASTEXITCODE -ne 0) { throw "Dose-response or calibration-bank audit failed; no model jobs were started." }

    $bankHash = (Get-FileHash -Algorithm SHA256 data/scenarios_dose_response_exploratory.json).Hash.ToLowerInvariant()
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMdd_HHmmss")
    $batchRoot = Join-Path $repoRoot (Join-Path "results/dose_response_batch" $stamp)
    $manifestPath = Join-Path $batchRoot "batch_manifest.json"
    $reportRoot = Join-Path $repoRoot (Join-Path "reports/dose_response_batch" $stamp)
    $null = New-Item -ItemType Directory -Force -Path $batchRoot, $reportRoot

    # Resolve every mutable model ref before the first paid call. Runs are pinned to the returned SHA.
    $resolvedModels = @()
    foreach ($model in $Models) {
        $modelInfo = Invoke-RestMethod -Method Get -Uri "https://huggingface.co/api/models/$model" -TimeoutSec 30
        if ($modelInfo.sha -notmatch '^[0-9a-fA-F]{40}$') {
            throw "Could not resolve a full immutable Hugging Face revision for '$model'; no model jobs were started."
        }
        $resolvedModels += [pscustomobject]@{ Id = $model; Revision = $modelInfo.sha }
    }

    $manifest = [ordered]@{
        created_utc = [DateTime]::UtcNow.ToString("o")
        bank = "dose-response"
        bank_sha256 = $bankHash
        calibration_bank_sha256 = (Get-FileHash -Algorithm SHA256 data/calibration_bank.json).Hash.ToLowerInvariant()
        bootstrap_samples = $BootstrapSamples
        preview_only = [bool]$PreviewOnly
        model_runs = @()
    }
    if ($PreviewOnly) {
        foreach ($resolved in $resolvedModels) {
            $slug = $resolved.Id -replace '[^A-Za-z0-9._-]', '_'
            $modelOut = Join-Path $batchRoot $slug
            $reportOut = Join-Path $reportRoot $slug
            Write-Host ("PREVIEW: modal run modal_app.py --model `"{0}`" --revision {1} --bank dose-response --precision bfloat16 --no-mock --include-calibration --authorize-paid-run" -f $resolved.Id, $resolved.Revision)
            Write-Host ("PREVIEW: raw and calibration output -> {0}; dose-response report -> {1}" -f $modelOut, $reportOut)
        }
        Write-Host "Preview complete. No Modal job was launched."
        return
    }

    $failed = 0
    foreach ($resolved in $resolvedModels) {
        $slug = $resolved.Id -replace '[^A-Za-z0-9._-]', '_'
        $modelOut = Join-Path $batchRoot $slug
        $reportOut = Join-Path $reportRoot $slug
        $null = New-Item -ItemType Directory -Force -Path $modelOut, $reportOut
        $entry = [ordered]@{
            model = $resolved.Id
            revision = $resolved.Revision
            status = "running"
            modal_log = (Join-Path $modelOut "modal_run.log")
            raw_results = $null
            calibration_results = $null
            calibration_summary = $null
            report_dir = $reportOut
            error = $null
        }
        $modalStdoutPath = Join-Path $modelOut "modal_stdout.log"
        $modalStderrPath = Join-Path $modelOut "modal_stderr.log"
        try {
            $modalArgs = @(
                "run", "modal_app.py", "--model", $resolved.Id,
                "--revision", $resolved.Revision, "--bank", "dose-response",
                "--precision", "bfloat16", "--no-mock", "--include-calibration",
                "--authorize-paid-run"
            )
            # Capture at the process level: PowerShell can turn native stderr
            # into a terminating ErrorRecord and truncate a formatted Modal
            # error before a pipeline or Tee-Object can save the full message.
            $modalExe = (Get-Command modal -CommandType Application | Select-Object -First 1).Source
            if (-not $modalExe) { throw "Could not locate the Modal CLI executable." }
            $modalProcess = Start-Process -FilePath $modalExe -ArgumentList $modalArgs `
                -WorkingDirectory $repoRoot -PassThru -Wait -NoNewWindow `
                -RedirectStandardOutput $modalStdoutPath -RedirectStandardError $modalStderrPath
            $modalExit = $modalProcess.ExitCode
            $stdoutText = if (Test-Path -LiteralPath $modalStdoutPath) { Get-Content -Raw -Encoding UTF8 -LiteralPath $modalStdoutPath } else { "" }
            $stderrText = if (Test-Path -LiteralPath $modalStderrPath) { Get-Content -Raw -Encoding UTF8 -LiteralPath $modalStderrPath } else { "" }
            $modalLogText = "=== STDOUT ===`r`n$stdoutText`r`n=== STDERR ===`r`n$stderrText"
            Set-Content -LiteralPath $entry.modal_log -Value $modalLogText -Encoding utf8
            if ($stdoutText) { Write-Host $stdoutText }
            if ($stderrText) { Write-Host $stderrText }
            $modalOutput = @($stdoutText, $stderrText) -join "`n"
            if ($modalExit -ne 0) { throw "Modal exited with status $modalExit." }

            $outputText = ($modalOutput | ForEach-Object { "$_" }) -join "`n"
            $rawMatch = [regex]::Match($outputText, '(?m)^\[modal_app\] Successfully finished run! Output persisted on Modal Volume at: (.+)$')
            $calMatch = [regex]::Match($outputText, '(?m)^\[modal_app\] Calibration output persisted on Modal Volume at: (.+)$')
            if (-not $rawMatch.Success -or -not $calMatch.Success) {
                throw "Modal finished without reporting both expected result paths. Review the Modal output above."
            }
            $rawName = [IO.Path]::GetFileName($rawMatch.Groups[1].Value.Trim())
            $calName = [IO.Path]::GetFileName($calMatch.Groups[1].Value.Trim())

            & modal volume get llm-coop-results $rawName $modelOut
            if ($LASTEXITCODE -ne 0) { throw "Could not download behavioral results '$rawName'." }
            & modal volume get llm-coop-results $calName $modelOut
            if ($LASTEXITCODE -ne 0) { throw "Could not download calibration results '$calName'." }
            & modal volume get llm-coop-results "$calName.summary.json" $modelOut
            if ($LASTEXITCODE -ne 0) { throw "Could not download calibration summary '$calName.summary.json'." }

            $rawPath = Join-Path $modelOut $rawName
            $calPath = Join-Path $modelOut $calName
            $calSummaryPath = Join-Path $modelOut "$calName.summary.json"
            if (-not (Test-Path -LiteralPath $rawPath) -or -not (Test-Path -LiteralPath $calPath) -or -not (Test-Path -LiteralPath $calSummaryPath)) {
                throw "One or more downloaded artifacts are missing from '$modelOut'."
            }
            & python -m llm_cooperation.cli analyze-dose-response $rawPath --output-dir $reportOut --bootstrap-samples $BootstrapSamples
            if ($LASTEXITCODE -ne 0) { throw "Dose-response analysis failed for '$($resolved.Id)'." }

            $entry.raw_results = $rawPath
            $entry.calibration_results = $calPath
            $entry.calibration_summary = $calSummaryPath
            $entry.status = "complete"
            $calSummary = Get-Content -Raw -LiteralPath $calSummaryPath | ConvertFrom-Json
            Write-Host ("{0}: calibration={1}; report={2}" -f $resolved.Id, $calSummary.status, (Join-Path $reportOut "dose_response_report.md"))
        } catch {
            $failed++
            $entry.status = "failed"
            if (-not (Test-Path -LiteralPath $entry.modal_log)) {
                $entry.modal_log = $null
            }
            $details = [string]$modalOutput
            if (-not $details -and $entry.modal_log) {
                $details = Get-Content -Raw -Encoding UTF8 -LiteralPath $entry.modal_log
            }
            if ($details.Length -gt 12000) { $details = $details.Substring(0, 12000) + "`n[Modal log truncated in manifest; see modal_log file.]" }
            $entry.error = $_.Exception.Message
            if ($details) { $entry.error += "`n" + $details }
            Write-Host ("{0} failed. Full Modal output: {1}" -f $resolved.Id, $entry.modal_log)
        }
        $manifest.model_runs += [pscustomobject]$entry
        $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
        if ($entry.status -eq "failed") {
            Write-Host "Stopping here so later paid model jobs are not launched after a Modal failure."
            break
        }
    }

    Write-Host "Batch outputs: $batchRoot"
    Write-Host "Batch reports: $reportRoot"
    Write-Host "Batch manifest: $manifestPath"
    if ($failed -gt 0) { throw "$failed model run(s) failed. Successful model outputs are preserved in the batch directories." }
} finally {
    Pop-Location
    $env:PYTHONUTF8 = $previousPythonUtf8
    $env:PYTHONIOENCODING = $previousPythonIoEncoding
}
