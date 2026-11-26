# Phase 0B historical run provenance and qualification

**Status:** Historical observations with incomplete execution provenance. Raw result JSONL files and the frozen scenario bank are unchanged.

## Frozen bank and source integrity

The Phase 0B bank contains 124 scenarios across 62 paired templates: 30 exploratory reused templates (60 scenarios), 30 new confirmatory templates (60 scenarios), and 2 symmetric-control templates (4 scenarios). The latter controls are assigned to the confirmatory split, so the bank has 60 exploratory and 64 confirmatory scenarios (240 and 256 counterbalanced presentations).

The canonical LF Git blob SHA-256 for `data/scenarios_phase0b_utility_matched.json` is `b460e60657392ded9e781428517b33adfe5bd32d4e7d9ee5b883ac8647bc7bf0`, matching the preregistered protocol. The Windows CRLF working-tree hash is `a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b`; normalizing CRLF to LF reproduces the canonical Git blob. All 12 Phase 0B result headers record the CRLF hash.

## Run index and cohort boundary

Eight runs evaluated only the exploratory split: 60 scenarios, 30 templates, and 240 presentations each.

| Run ID | Model |
| --- | --- |
| `run_allenai_OLMo-2-1124-7B_20261104_120206_ffcb4165` | `allenai/OLMo-2-1124-7B` |
| `run_deepseek-ai_deepseek-llm-7b-base_20261104_120334_2d2d2bb8` | `deepseek-ai/deepseek-llm-7b-base` |
| `run_HuggingFaceTB_SmolLM2-1.7B_20261104_115554_ab063fcc` | `HuggingFaceTB/SmolLM2-1.7B` |
| `run_ibm-granite_granite-3.3-2b-base_20261104_115712_3e1fd8f8` | `ibm-granite/granite-3.3-2b-base` |
| `run_mistralai_Mistral-7B-v0.3_20261104_120042_05563590` | `mistralai/Mistral-7B-v0.3` |
| `run_Qwen_Qwen2.5-1.5B_20261104_115917_f21535c4` | `Qwen/Qwen2.5-1.5B` |
| `run_Qwen_Qwen2.5-7B_20261104_120438_f7fc4192` | `Qwen/Qwen2.5-7B` |
| `run_tiiuae_Falcon3-3B-Base_20261104_115818_bdf06018` | `tiiuae/Falcon3-3B-Base` |

Four later runs evaluated all 124 scenarios (496 presentations), including the held-out confirmatory partition and symmetric controls:

| Run ID | Model |
| --- | --- |
| `run_google_gemma-2-2b_20261104_122425_061953ae` | `google/gemma-2-2b` |
| `run_google_gemma-2-9b_20261104_122055_51c5ce8a` | `google/gemma-2-9b` |
| `run_meta-llama_Llama-3.2-3B_20261104_121441_f864e7c9` | `meta-llama/Llama-3.2-3B` |
| `run_microsoft_phi-2_20261104_121221_3c92ecf3` | `microsoft/phi-2` |

Their result rows contain 240 exploratory presentations and 256 confirmatory-split presentations. The confirmatory portion is exposed and cannot support a prospective held-out claim. The run headers do not preserve a signed scientific authorization event for that split.

## Bounded provenance recovery

All 12 result headers identify run ID, model name, timestamp, bank hash, precision, prompt mode, seed, and runtime package versions. They record `model_revision: null`, `tokenizer_revision: null`, and `git_commit: null`. A bounded search of the result files, model configuration, tracked cache metadata, run-ID references, cohort runner, and existing audit files found no verified link from these run IDs to immutable model/tokenizer revisions or the exact inference-code commit. Matching model names in cache metadata are not a run-to-checkpoint mapping and are not assigned as provenance.

The post-hoc item audit has a separately pinned provenance record: Qwen/Qwen2.5-32B-Instruct revision `5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd`, scenario-bank hash `a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b`, protocol `blind_item_v1_pair_v1`, and manifest time `2026-11-04T13:13:57Z`. It assessed 124 scenarios after the model outputs were already observed. Its results (89 HIGH, 33 REVIEW, 2 PASS) are AI-assisted diagnostic flags, not human scientific review or pre-inference approval. The per-template matrix remains `pending_human_scientific_review`.

## Analytical reproduction versus exact regeneration

The saved choices can be analyzed with this branch's utility-matched analysis implementation, pinned for analysis to evidence commit `0b89b202064f9ace47d62148970dfa4f070272fa`. That identifies an analysis-source snapshot; it does not establish which code or checkpoint revisions generated the historical model outputs.

From the repository root, analyze each run without model inference:

```powershell
python -m llm_cooperation.cli analyze results/run_HuggingFaceTB_SmolLM2-1.7B_20261104_115554_ab063fcc.jsonl --output-dir reports/phase0b_reanalysis/run_HuggingFaceTB_SmolLM2-1.7B_20261104_115554_ab063fcc --bootstrap-samples 2000
```

Repeat for a selected run ID from the tables above. Do not combine exploratory-only runs with full-bank runs as if they covered the same scenarios. Reports based on saved JSONL are analytical reproductions of the recorded choices; exact computational regeneration of the model outputs is not established.

## Claim eligibility

- The eight exploratory-only runs can support explicitly exploratory analyses on the reused 30-template split, subject to incomplete execution provenance and pending human instrument review.
- The four full-bank runs may be reported as historical observations, with confirmatory-item exposure disclosed. They are ineligible as prospective confirmatory replication.
- The AI-assisted post-hoc audit can support a sensitivity analysis of wording/payoff ambiguity, not an assertion that humans validated the bank.
- Do not pool these cohorts into a single common-scenario model comparison without restricting to matched templates and reporting which models saw which split.
