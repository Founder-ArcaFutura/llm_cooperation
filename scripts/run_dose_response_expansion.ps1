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
Write-Host ("Expansion: {0} additional models; existing three-model dose-response batch is excluded." -f $models.Count)
$models | ForEach-Object { Write-Host " - $_" }
if ($ListOnly) { return }
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
