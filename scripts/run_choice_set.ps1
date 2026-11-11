param([string[]]$Models = @(), [switch]$UseHuggingFaceSecret, [ValidateSet('standard', 'all', 'replacement-only')][string]$Mode = 'standard')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($UseHuggingFaceSecret) { $env:MODAL_USE_HF_SECRET = '1' }
$cohort = @(
    @{ Name='Qwen/Qwen2.5-3B'; GPU='small' },
    @{ Name='Qwen/Qwen2.5-1.5B'; GPU='small' },
    @{ Name='allenai/OLMo-2-0425-1B'; GPU='small' },
    @{ Name='meta-llama/Llama-3.2-3B'; GPU='small' },
    @{ Name='google/gemma-2-2b'; GPU='small' },
    @{ Name='ibm-granite/granite-3.3-2b-base'; GPU='small' },
    @{ Name='Qwen/Qwen2.5-7B'; GPU='medium' },
    @{ Name='allenai/OLMo-2-1124-7B'; GPU='medium' },
    @{ Name='mistralai/Mistral-7B-v0.3'; GPU='medium' },
    @{ Name='deepseek-ai/deepseek-llm-7b-base'; GPU='medium' },
    @{ Name='google/gemma-2-9b'; GPU='medium' },
    @{ Name='EleutherAI/pythia-12b-deduped'; GPU='medium' },
    @{ Name='Qwen/Qwen2.5-3B-Instruct'; GPU='small' },
    @{ Name='founder-arcafutura/pythia-12b-exploratory-20261022'; GPU='medium' }
)
if ($Models.Count -gt 0) {
    $unknown = @($Models | Where-Object { $_ -notin $cohort.Name })
    if ($unknown.Count) { throw "Unknown model(s): $($unknown -join ', ')" }
    $cohort = @($cohort | Where-Object { $_.Name -in $Models })
}
$failed = @()
foreach ($item in $cohort) {
    Write-Host "`nRunning $($item.Name) on $($item.GPU)..."
    & modal run modal_choice_set.py --model $item.Name --gpu $item.GPU --mode $Mode
    if ($LASTEXITCODE -ne 0) { $failed += $item.Name; Write-Warning "Failed: $($item.Name). Continuing with remaining models." }
}
if ($failed.Count) { Write-Warning "Failed models: $($failed -join ', ')"; exit 1 }
Write-Host 'All requested models completed. Results are in results/choice_set/.'
