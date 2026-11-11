# Phase 0 and Phase 0B choice-set follow-up

This is separate from the Phase 1 launcher and can be started after that run. The default command runs all three choice-set conditions, both generated-letter and forced-choice scoring, and the selected five-model default cohort for both full banks:

```powershell
.\scripts\run_choice_set_phase0_followup.ps1 -UseHuggingFaceSecret
```

`phase0` is the 120-scenario expanded Phase 0 bank; `phase0b` is the 124-scenario utility-matched bank. All splits are included. Split, utility condition, context type, partner type and other available item attributes are recorded per presentation. This intervention is exploratory; exposure of a previously held-out item to this experiment means it is not unexposed for future work using this intervention. These runs do not certify either bank or the replacement options.

There are 14 presentations per scenario per model: 4 original, 6 three-option, and 4 replacement-option presentations. That is 1,680 and 1,736 prompts per model respectively, or 17,080 prompts over the five-model default cohort (47,824 if all 14 models are explicitly selected). Each prompt records both measures. These repeated presentations are not independent scenarios. Results go to unique `results/choice_set/<run_id>` folders; each summary records the bank and both file hashes, plus model provenance. Partial runs are committed to the Modal results volume after every scenario.

The 60 Phase 0 and 62 Phase 0B draft replacement actions are in `data/choice_set_phase0_replacements.json` and `data/choice_set_phase0b_replacements.json`. Human/AI pairs share a replacement. For Phase 0B, corresponding payoff-tier variants deliberately share wording to avoid introducing another wording difference. These alternatives are newly authored, unreviewed, and have unknown feasibility, outcomes, neutrality, distinctness and partner effects. They can introduce equipment or procedures not specified by the source. Several do not complete the task and should not be assumed utility-matched. Cooperative framing in the stems remains. Results for the replacement condition must be treated accordingly.

For selected models, add `-Models @('Qwen/Qwen2.5-3B')`; for one condition set use `-Mode standard` or `-Mode replacement-only`. Both banks run in sequence. Individual failures are reported and the remaining jobs continue.

## Provisional model selection

The launcher defaults to Qwen2.5-3B, Qwen2.5-1.5B, Qwen2.5-7B, Llama-3.2-3B, and OLMo-2-1124-7B, while preserving the full 14-model manifest. The first four were selected from the previous Phase 1 generated-letter/position screen; OLMo 7B was added at the user's request for positional scoring. These are candidates, not validated or independently calibration-qualified models. The new three-option condition has marked positional imbalance for Qwen 1.5B, Qwen 7B, and Llama 3B despite useful valid-letter rates, and the four-replacement condition also has substantial position imbalance for Qwen 1.5B and Llama 3B. Treat condition-specific results with care. Prior strict generated-letter failures do not by themselves invalidate restricted positional scores; excluded models can be explicitly selected for that analysis.

The default all-mode workload is 17,080 presentations across five models. `-DryRun` reports selected and excluded models, source and replacement hashes, conditions, and expected workload without launching anything. A real invocation records the selection and exclusion reasons to `results/choice_set_manifests/`. Use `-Models @('Qwen/Qwen2.5-3B', 'meta-llama/Llama-3.2-3B')` to specify a cohort, or `-ExcludeModels @('Qwen/Qwen2.5-1.5B')` to remove candidates. Explicit selection can restore excluded models. See `research/choice_set_followup_audit/AUDIT.md` for the replacement triage and its limits.


## OLMo 7B and Mistral update

OLMo-2-1124-7B is included in the default follow-up at the user's request to preserve its constrained positional scores. In the Phase 1 intervention, those scores were available for all presentations, while strict generated-letter validity was zero: many raw outputs begin with a choice letter and continue with text. The three-option positional letter counts were A=198, B=30, C=132, a 46.7-percentage-point max/min spread; this is a position sensitivity warning, not a clean validity pass. Four-option and three-option measures should be reported separately.

Mistral failed to load its tokenizer before Phase 1 inference; the image lacked SentencePiece. The separate `modal_choice_set_mistral_retry.py` image adds SentencePiece and protobuf; `modal_choice_set_followup.py` includes them too. The original Phase 1 launcher remains unchanged while its cohort is running. After it finishes, retry Mistral with:

```powershell
$env:MODAL_USE_HF_SECRET = '1'
modal run modal_choice_set_mistral_retry.py --model 'mistralai/Mistral-7B-v0.3' --gpu medium --mode all
```

These added dependencies address the reported error but have not been verified with a remote model load. Mistral remains excluded from the default follow-up pending assessment; it can be explicitly selected.
