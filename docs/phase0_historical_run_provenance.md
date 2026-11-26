# Phase 0 historical run provenance and qualification

**Status:** Historical observations with incomplete execution provenance. The raw JSONL records are preserved unchanged.

## Scope

The Phase 0 integration branch contains 14 non-mock run files: four 24-scenario pilot records (96 presentations each) and ten expanded-bank records (120 scenarios, 480 presentations each). All record bfloat16, device auto, prompt mode standard_plaintext, seed 42, and run timestamps/IDs. They also record runtime versions torch 2.15.0+cu132, transformers 5.22.1, and Modal 1.6.2.

All 14 headers have model_revision: null, tokenizer_revision: null, and git_commit: null. The model manifest uses mutable main refs for several base models. A bounded search of existing result headers, configs/models.yaml, the run-ID inventory, its referenced batch manifest, and tracked Hugging Face cache metadata did not recover a verified run-to-checkpoint or run-to-code association. The inventory identifies ten expanded runs by model name but records no immutable revisions; it does not identify the four pilot run IDs. Two tracked cache snapshots overlap model names, but no record ties either snapshot to a specific Phase 0 run, so they are not assigned as provenance.

Do not infer model/tokenizer revisions from current Hub state, model names, timestamps, or unlinked caches. These outputs support reanalysis of the saved observations; they do **not** support exact computational regeneration of the historical model outputs.

## Run index

| Bank | Run ID | Model | Recorded time (UTC) | Presentations |
| --- | --- | --- | --- | ---: |
| Pilot, 24 scenarios | run_allenai_OLMo-2-0425-1B_20261104_014221_4dfe0470 | allenai/OLMo-2-0425-1B | 2026-11-04 01:42 | 96 |
| Expanded, 120 scenarios | run_allenai_OLMo-2-1124-7B_20261104_032715_5c0ead30 | allenai/OLMo-2-1124-7B | 2026-11-04 03:27 | 480 |
| Expanded, 120 scenarios | run_deepseek-ai_deepseek-llm-7b-base_20261104_033154_b05ab389 | deepseek-ai/deepseek-llm-7b-base | 2026-11-04 03:31 | 480 |
| Expanded, 120 scenarios | run_EleutherAI_pythia-12b-deduped_20261104_034036_74031811 | EleutherAI/pythia-12b-deduped | 2026-11-04 03:40 | 480 |
| Pilot, 24 scenarios | run_EleutherAI_pythia-2.8b_20261104_005919_357b07df | EleutherAI/pythia-2.8b | 2026-11-04 00:59 | 96 |
| Expanded, 120 scenarios | run_EleutherAI_pythia-2.8b_20261104_030951_01004e2a | EleutherAI/pythia-2.8b | 2026-11-04 03:09 | 480 |
| Expanded, 120 scenarios | run_HuggingFaceTB_SmolLM2-1.7B_20261104_031133_69aaf94c | HuggingFaceTB/SmolLM2-1.7B | 2026-11-04 03:11 | 480 |
| Expanded, 120 scenarios | run_ibm-granite_granite-3.3-2b-base_20261104_031428_a244d219 | ibm-granite/granite-3.3-2b-base | 2026-11-04 03:14 | 480 |
| Pilot, 24 scenarios | run_mistralai_Mistral-7B-v0.3_20261104_014921_af123908 | mistralai/Mistral-7B-v0.3 | 2026-11-04 01:49 | 96 |
| Expanded, 120 scenarios | run_mistralai_Mistral-7B-v0.3_20261104_032148_bd119eca | mistralai/Mistral-7B-v0.3 | 2026-11-04 03:21 | 480 |
| Expanded, 120 scenarios | run_Qwen_Qwen2.5-1.5B_20261104_031916_4366e687 | Qwen/Qwen2.5-1.5B | 2026-11-04 03:19 | 480 |
| Pilot, 24 scenarios | run_Qwen_Qwen2.5-3B_20261104_005402_eba5983d | Qwen/Qwen2.5-3B | 2026-11-04 00:54 | 96 |
| Expanded, 120 scenarios | run_Qwen_Qwen2.5-7B_20261104_033413_0aade9f0 | Qwen/Qwen2.5-7B | 2026-11-04 03:34 | 480 |
| Expanded, 120 scenarios | run_tiiuae_Falcon3-3B-Base_20261104_031802_c8f2f372 | tiiuae/Falcon3-3B-Base | 2026-11-04 03:18 | 480 |

## Bank hashes

The canonical Git blobs use LF line endings:

| Bank | Canonical Git blob SHA-256 | Hash recorded by Windows run |
| --- | --- | --- |
| data/scenarios.json (24 scenarios) | bfa2204eb4acad51001372fd5f59914ed54a96f96da52532ffd28ab97414485b | 7a81b504032011aef490961ebbd3ed58d85486e12283222213d6ef1a6d13c158 |
| data/scenarios_v1_expanded.json (120 scenarios) | ba6c93c9aadf30749b4a3438cf1e3a95a3bb8804d8d955f0bf0acc79638d5b55 | 78f513e4b3c481841c11aaa1d9f4ab5d5690c212d0398f9e4c28e29eb16f26cd |

The run hashes match the Windows CRLF worktree bytes; normalizing CRLF to LF reproduces the canonical Git blob hashes. The independent calibration bank is data/calibration_bank.json, SHA-256 4343b76d98733e4fa6061867c5deea9619bfac5a5951f14a1d61007d5c058a39.

## Analytical reproduction

The saved observations can be reanalyzed without model inference. The validated analysis implementation used for this reanalysis is pinned to PR #2 source commit 91cf9d4d3f958a671c01285ac2b8833c0878e712; this identifies the analysis version, not the unknown historical execution version.

From the repository root, with the branch's 14 raw JSONL files present:

~~~powershell
$files = Get-ChildItem results -File -Filter *.jsonl | ForEach-Object { $_.FullName }
python -m llm_cooperation.cli compare-models @files --output-dir reports/phase0_reanalysis --bootstrap-samples 2000
~~~

The report is analytically reproducible from these records and the identified analysis source. It is not a regeneration of the model outputs. Keep this qualification attached to any table, figure, or manuscript claim derived from these runs.
