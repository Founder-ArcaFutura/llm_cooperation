# Cross-Model Comparative Report: Phase 0 Screen

**Overall Gate Recommendation:** **REVISE / EXTEND SCREEN**: Only 1 base model family (QWEN with 1 checkpoint(s): `Qwen/Qwen2.5-3B`) qualified. Cross-family replication not yet achieved.

---

## 1. Pretrained Base Model Cohort (Primary Scientific Question)
*Models evaluating pretrained strategy-selection posture without SFT or alignment.*

| Model | Family | Stage | Run ID | Precision | Mock | Coop Rate (95% CI) | Cond Prob | Valid % | Pos Spread | Neutral | Cost | Conflict | Ineff |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EleutherAI/pythia-12b-deduped` | pythia | base | `run_EleutherAI_pythia-12b-deduped_20261104_230807_9911c9f7` | bfloat16 | False | 25.0% [25.0%–25.0%] | 0.265 | 0.0% | 100.0% | 25.0% | 0.0% | 0.0% | 0.0% |
| `Qwen/Qwen2.5-3B` | qwen | base | `run_Qwen_Qwen2.5-3B_20261104_225437_9d3a9b99` | bfloat16 | False | 93.3% [87.9%–97.5%] | 0.681 | 100.0% | 2.9% | 93.3% | 0.0% | 0.0% | 0.0% |
| `allenai/OLMo-2-1124-7B` | olmo | base | `run_allenai_OLMo-2-1124-7B_20261104_230239_2012fe3a` | bfloat16 | False | 82.9% [76.2%–89.2%] | 0.495 | 0.0% | 10.4% | 82.9% | 0.0% | 0.0% | 0.0% |
| `mistralai/Mistral-7B-v0.3` | mistral | base | `run_mistralai_Mistral-7B-v0.3_20261104_230109_783d0a07` | bfloat16 | False | 98.3% [96.7%–99.6%] | 0.620 | 0.0% | 1.3% | 98.3% | 0.0% | 0.0% | 0.0% |

---

## 2. Post-Trained Comparators (Diagnostic Sanity Checks Only)
*WARNING: Comparators are NEVER included in the pretrained base cohort or used as evidence for unaligned pretraining!*

_No models in this cohort._

---

## 3. Unverified / Unknown Provenance Cohort (Excluded from Scientific Evidence)
*Checkpoints without verified manifest provenance or explicit metadata are isolated here.*

| Model | Family | Stage | Run ID | Precision | Mock | Coop Rate (95% CI) | Cond Prob | Valid % | Pos Spread | Neutral | Cost | Conflict | Ineff |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Qwen/Qwen2.5-1.5B` | qwen | unverified | `run_Qwen_Qwen2.5-1.5B_20261104_225733_6d7c510c` | bfloat16 | False | 95.0% [90.8%–98.3%] | 0.747 | 82.9% | 4.2% | 95.0% | 0.0% | 0.0% | 0.0% |
| `Qwen/Qwen2.5-7B` | qwen | unverified | `run_Qwen_Qwen2.5-7B_20261104_230507_6a61a739` | bfloat16 | False | 97.5% [94.6%–99.6%] | 0.809 | 100.0% | 0.8% | 97.5% | 0.0% | 0.0% | 0.0% |
| `allenai/OLMo-2-0425-1B` | olmo | unverified | `run_allenai_OLMo-2-0425-1B_20261104_225817_ed118b25` | bfloat16 | False | 55.0% [49.6%–60.4%] | 0.296 | 2.1% | 42.1% | 55.0% | 0.0% | 0.0% | 0.0% |
| `deepseek-ai/deepseek-llm-7b-base` | deepseek-ai | unverified | `run_deepseek-ai_deepseek-llm-7b-base_20261104_230409_132a07ec` | bfloat16 | False | 61.7% [53.3%–69.6%] | 0.385 | 3.3% | 47.9% | 61.7% | 0.0% | 0.0% | 0.0% |
| `google/gemma-2-2b` | gemma | unverified | `run_google_gemma-2-2b_20261104_230841_3f8b9410` | bfloat16 | False | 49.2% [43.3%–55.4%] | 0.292 | 42.5% | 60.4% | 49.2% | 0.0% | 0.0% | 0.0% |
| `google/gemma-2-9b` | gemma | unverified | `run_google_gemma-2-9b_20261104_231104_f3615b96` | bfloat16 | False | 89.2% [83.3%–94.2%] | 0.533 | 4.2% | 7.9% | 89.2% | 0.0% | 0.0% | 0.0% |
| `ibm-granite/granite-3.3-2b-base` | ibm-granite | unverified | `run_ibm-granite_granite-3.3-2b-base_20261104_225923_d25e9d3e` | bfloat16 | False | 73.3% [67.1%–79.6%] | 0.538 | 0.0% | 40.4% | 73.3% | 0.0% | 0.0% | 0.0% |
| `meta-llama/Llama-3.2-3B` | llama | unverified | `run_meta-llama_Llama-3.2-3B_20261104_230738_d5b4b36e` | bfloat16 | False | 85.4% [78.8%–91.2%] | 0.459 | 100.0% | 9.6% | 85.4% | 0.0% | 0.0% | 0.0% |

---

## 4. Scientific Claim Boundary (§8, §10, & §13)
> "Phase 0 asks only about strategy-selection behaviour; it does not demonstrate innate agency, motives, altruism, or a weight-level mechanism. Later phases remain conditional and must be frozen before confirmatory held-out evaluation."
