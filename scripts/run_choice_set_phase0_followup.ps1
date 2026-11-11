param([string[]]$Models = @(), [string[]]$ExcludeModels = @(), [switch]$UseHuggingFaceSecret, [switch]$DryRun, [ValidateSet('standard', 'all', 'replacement-only')][string]$Mode = 'all')
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
$candidateDefaults = @('Qwen/Qwen2.5-3B', 'Qwen/Qwen2.5-1.5B', 'Qwen/Qwen2.5-7B', 'meta-llama/Llama-3.2-3B', 'allenai/OLMo-2-1124-7B')
$available = @($cohort | ForEach-Object { $_.Name })
$unknown = @(@($Models) + @($ExcludeModels) | Where-Object { $_ -and $_ -notin $available })
if ($unknown.Count) { throw "Unknown model(s): $($unknown -join ', ')" }
$requested = if ($Models.Count -gt 0) { @($Models) } else { $candidateDefaults }
$selected = @($cohort | Where-Object { $_.Name -in $requested -and $_.Name -notin $ExcludeModels })
if ($selected.Count -eq 0) { throw 'No models selected.' }
$conditions = switch ($Mode) {
    'all' { @('four', 'three', 'four_neutral') }
    'standard' { @('four', 'three') }
    'replacement-only' { @('four_neutral') }
}
$ordersPerScenario = switch ($Mode) { 'all' { 14 } 'standard' { 10 } 'replacement-only' { 4 } }
$bankFiles = [ordered]@{
    phase0 = 'data/scenarios_v1_expanded.json'
    phase0b = 'data/scenarios_phase0b_utility_matched.json'
}
$hashes = [ordered]@{}
foreach ($bank in $bankFiles.Keys) {
    $hashes[$bank] = (Get-FileHash -LiteralPath $bankFiles[$bank] -Algorithm SHA256).Hash.ToLowerInvariant()
    $replacement = "data/choice_set_${bank}_replacements.json"
    $hashes["${bank}_replacements"] = (Get-FileHash -LiteralPath $replacement -Algorithm SHA256).Hash.ToLowerInvariant()
}
$selectedNames = @($selected | ForEach-Object { $_.Name })
$excluded = @($available | Where-Object { $_ -notin $selectedNames })
$evidence = @{
    'allenai/OLMo-2-0425-1B' = 'Prior Phase 1: 2.1% valid; new choice-set run also shows low validity and strong position effects.'
    'google/gemma-2-2b' = 'Prior Phase 1: 42.5% valid and 60.4-point position spread; new run also shows severe position effects.'
    'ibm-granite/granite-3.3-2b-base' = 'Prior and new Phase 1 runs: zero valid generated choices.'
    'EleutherAI/pythia-12b-deduped' = 'Prior Phase 1: invariant A positional scores and zero valid generated choices.'
    'allenai/OLMo-2-1124-7B' = 'User requested OLMo-7B for positional scoring; strict generated-letter compliance is zero and three-option position spread is substantial.'
    'mistralai/Mistral-7B-v0.3' = 'Prior Phase 1: zero valid generated choices despite low positional spread in that condition.'
    'deepseek-ai/deepseek-llm-7b-base' = 'Prior Phase 1: 3.3% valid generated choices and 47.9-point positional spread.'
    'google/gemma-2-9b' = 'Prior Phase 1: 4.2% valid generated choices despite low positional spread in that condition.'
    'Qwen/Qwen2.5-3B-Instruct' = 'Comparator not yet screened for this follow-up at time of selection.'
    'founder-arcafutura/pythia-12b-exploratory-20261022' = 'SFT comparator not yet screened for this follow-up at time of selection.'
}
$exclusionDetails = [ordered]@{}
foreach ($name in $excluded) {
    $exclusionDetails[$name] = if ($name -in $ExcludeModels) { 'Explicitly excluded by user.' } elseif ($Models.Count -gt 0) { 'Not included in user-specified model list.' } elseif ($evidence.ContainsKey($name)) { $evidence[$name] } else { 'Not in provisional default candidate list.' }
} 
$provenance = [ordered]@{
    created_utc = [DateTime]::UtcNow.ToString('o')
    selection_rule = if ($Models.Count -gt 0) { 'user-specified models, then explicit exclusions' } else { 'four provisional candidates from prior screen plus OLMo-7B explicitly requested for positional scoring; current condition-specific position warnings apply' }
    selected_models = $selectedNames
    excluded_models = $excluded
    exclusion_reasons = $exclusionDetails
    explicit_exclusions = @($ExcludeModels)
    mode = $Mode
    conditions = $conditions
    bank_hashes_sha256 = $hashes
    presentations_per_model = 244 * $ordersPerScenario
    total_presentations = 244 * $ordersPerScenario * $selected.Count
    research_status = 'exploratory; includes original confirmatory-labeled scenarios'
    qualification_note = 'Selection is provisional; current three-option and replacement-condition position effects are not qualification passes. Independent calibration and neutral-option review pending.'
}
Write-Host "Selected models ($($selected.Count)): $($selectedNames -join ', ')"
Write-Host "Excluded models: $($excluded -join ', ')"
Write-Host "Conditions: $($conditions -join ', '); mode: $Mode"
Write-Host "SHA-256: phase0=$($hashes.phase0); phase0b=$($hashes.phase0b)"
Write-Host "SHA-256 replacements: phase0=$($hashes.phase0_replacements); phase0b=$($hashes.phase0b_replacements)"
Write-Host "Presentations per model: $($provenance.presentations_per_model); total: $($provenance.total_presentations)"
Write-Host 'Selection is provisional. Inspect condition-specific position effects and the replacement review before interpreting results.'
if ($DryRun) { Write-Host 'Dry run: no Modal jobs launched.'; return }
$manifestDir = 'results/choice_set_manifests'
New-Item -ItemType Directory -Path $manifestDir -Force | Out-Null
$manifestId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$manifestPath = Join-Path $manifestDir "followup_$manifestId.json"
$provenance | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "Selection manifest: $manifestPath"
$cohort = $selected
$failed = @()
foreach ($bank in @('phase0', 'phase0b')) {
foreach ($item in $cohort) {
    Write-Host "`nRunning $bank / $($item.Name) on $($item.GPU)..."
    & modal run modal_choice_set_followup.py --model $item.Name --gpu $item.GPU --mode $Mode --bank $bank
    if ($LASTEXITCODE -ne 0) { $failed += "$bank / $($item.Name)"; Write-Warning "Failed: $bank / $($item.Name). Continuing with remaining models." }
}
}
if ($failed.Count) { Write-Warning "Failed models: $($failed -join ', ')"; exit 1 }
Write-Host 'All requested models completed. Results are in results/choice_set/.'
