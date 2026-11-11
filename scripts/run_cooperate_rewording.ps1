param([string[]]$Models = @(), [switch]$UseHuggingFaceSecret, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($UseHuggingFaceSecret) { $env:MODAL_USE_HF_SECRET = '1' }
& python -c "from llm_cooperation.cooperate_rewording_assay import BANKS,load_items; [(print(b, len(load_items('data',b)[0]), load_items('data',b)[2])) for b in BANKS]"
if ($LASTEXITCODE -ne 0) { throw 'Bank/rewrite validation failed; no model was launched.' }
$manifest = Get-Content -LiteralPath 'data/cooperate_rewording_model_manifest.json' -Raw | ConvertFrom-Json
$available = @($manifest.models | ForEach-Object { $_.model })
$unknown = @($Models | Where-Object { $_ -notin $available })
if ($unknown.Count) { throw "Unknown models: $($unknown -join ', ')" }
$cohort = @($manifest.models | Where-Object { $Models.Count -eq 0 -or $_.model -in $Models })
if ($cohort.Count -eq 0) { throw 'No models selected.' }
Write-Host "Models ($($cohort.Count)): $(@($cohort | ForEach-Object { $_.model }) -join ', ')"
Write-Host "Paired original and paraphrased four-option prompts: 2,432 per model; total $($cohort.Count * 2432)."
Write-Host 'Each model uses its recorded checkpoint revision. No masked-choice conditions are run.'
if ($DryRun) { Write-Host 'Dry run: no Modal jobs launched.'; return }
$failed = @()
foreach ($item in $cohort) {
    Write-Host "`nRunning $($item.model)..."
    & modal run modal_cooperate_rewording.py --model $item.model --revision $item.revision --gpu $item.gpu
    if ($LASTEXITCODE -ne 0) { $failed += $item.model; Write-Warning "Failed: $($item.model). Continuing." }
}
if ($failed.Count) { Write-Warning "Failed models: $($failed -join ', ')"; exit 1 }
Write-Host 'Finished. Results: results/cooperate_rewording/'
