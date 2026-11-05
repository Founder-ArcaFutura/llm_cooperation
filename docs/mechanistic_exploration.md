# Exploratory mechanistic screen v1

This is an exploratory continuation, not the preregistered Phase 1 confirmatory assay. It screens candidate MLP neurons in small **base** Qwen2.5 and Llama 3.2 models; it does not identify a circuit by itself. No model inference or paid execution is performed by preparing this code.

## Probes and separation

The code uses all 60 scenarios in the existing Phase 0B exploratory partition, with four counterbalanced option positions each (240 presentations). These cover equal, advantageous and disadvantageous actor utility and paired human/AI partners. It also uses all 24 factual/arithmetic calibration questions in four positions (96 presentations). These are draft research instruments with known potential linguistic and payoff confounds; they need independent semantic review. No new prompts are claimed to be validated.

A fixed SHA-256 ordering partitions the Phase 0B exploratory data into discovery and evaluation groups. All permutations, both partners and every variant in a sensitivity triad remain together. The precise assignment and bank hashes are saved. The existing Phase 0B confirmatory and prospective Phase 1 banks are never loaded. The Phase 1 freeze manifest currently prohibits inference on its bank; this implementation does not override that gate. These within-exploratory evaluation items have appeared in prior behavioral runs, so they are **not an untouched confirmatory replication**.

At the final prompt token, each MLP's `down_proj` input is the post-gating activation of its intermediate neurons. For each discovery group, average activations and the COOPERATE-minus-INDEPENDENT answer-letter logit margin across its presentations. Rank all neurons by absolute Pearson correlation across groups; save the signed correlations and top K. This is an association with the model's answer margin, not a clean concept contrast. Correlations may reflect wording, position, partner type, payoff, or output preparation. The runner does not train a classifier, establish monosemanticity, or measure attention heads.

Evaluate the same held-out prompts under baseline, simultaneous zeroing of all selected neurons, and zeroing an equal number of randomly selected *non-candidate neurons in the same layers*. Interventions affect the final prompt token only. Analyze paired logit-margin changes at the group level with percentile bootstrap intervals, plus descriptive partner and utility strata. Report all three conditions and inspect per-presentation logits. A change can be a causal effect of this intervention on this measurement, but is not sufficient to establish a cooperation-specific circuit. Zero is potentially out of distribution; random controls, one seed, and finite calibration are not a complete selectivity test. Follow up with individual-neuron and dose-response interventions, mean ablation or activation patching, independent paraphrases, multiple controls, and a separately reviewed held-out confirmatory study before stronger claims. Do not treat a non-significant calibration change as proof of no degradation.

Calibration reports forced-choice accuracy and whether the unconstrained **first token** decodes to a letter. It does not measure full generated-answer validity, language-model loss, general fluency, or all possible task impairment. The four candidate letters are validated at every prompt boundary, and scores are their raw next-token logits (their difference equals the four-choice log-probability difference). Tokenization incompatibility fails the run rather than substituting a token. The result is not an estimate of open-ended behavior.

## Prepare and run

Supported IDs: `Qwen/Qwen2.5-1.5B`, `Qwen/Qwen2.5-3B`, `meta-llama/Llama-3.2-1B`, `meta-llama/Llama-3.2-3B`. Supply the exact 40-character Hugging Face commit SHA for the model and tokenizer; resolve and record it before launch. Llama requires the user's accepted model license and an authorized Hugging Face token. With the existing Modal secret named `huggingface-secret`, set `$env:MODAL_USE_HF_SECRET='1'` before invoking Modal. Qwen can run without this secret. Model access, GPU cost, runtime, and a budget must be checked before paid execution; no dollar cap is enforced by Modal here. Each run has a 2-hour GPU timeout, A10G, 10 candidates by default, no automatic retry, and roughly 700 single-prompt forward passes depending on the split. Start with one model, inspect the outputs, then authorize additional runs separately. The timeout is a safety bound, not a cost estimate.

From the repository root, after explicitly authorizing paid inference:

```powershell
modal run modal_mechanistic.py --model Qwen/Qwen2.5-1.5B --revision <40-character-commit-sha> --authorize-paid-run
# Llama, after arranging gated access:
$env:MODAL_USE_HF_SECRET='1'
modal run modal_mechanistic.py --model meta-llama/Llama-3.2-1B --revision <40-character-commit-sha> --authorize-paid-run
```

The command prints a unique run ID before launch. Results are stored on Modal volume `llm-coop-mechanistic` under that ID. Retrieve using `modal volume get llm-coop-mechanistic <run-id> results/<run-id>` and inspect `manifest.json`, `candidates.json`, `observations.jsonl`, and `summary.json`. The runner writes observations incrementally and commits the volume on normal completion or caught failure; abrupt container termination may lose uncommitted volume changes. Failed runs are marked and must be preserved, not silently retried. A successful run can be reanalyzed with `python -m llm_cooperation.mechanistic.analyze results/<run-id>`; incomplete runs are rejected by the summarizer. Weights use the existing `llm-coop-hf-cache` volume.

Local GPU execution uses `python run_mechanistic.py --model <model> --revision <sha> --output results/<new-run-directory> --authorize-inference`. Output directories must not exist, to prevent overwrite. Record the exact code version, revision, environment and authorization alongside results; the manifest records the screen source hash and runtime versions. Runs should use identical parameters when comparing families. None of the artifacts are evidence of live model behavior until a real run is completed and inspected.

## Larger exploratory ablation sweep

`modal_mechanistic_sweep.py` is a separate follow-up; it does not change the original experiment. It loads one model and ranks up to 1,000 neurons on the discovery partition, then tests nested candidate sets of 10, 100, 500 and 1,000 neurons. For each dose it evaluates three independently seeded random sets with the same layer-by-layer counts, excluding all of the top 1,000 candidates. All interventions zero the final prompt-token activations only. The sets and individual correlations are saved in `candidates.json`, along with the mean absolute **group-average** activation (not average absolute activation over presentations). These are descriptive candidate magnitudes, not estimates of causal effect.

The sweep uses a new deterministic split: one complete sensitivity triad plus seven ordinary templates for evaluation, with all paired partners and permutations together. The other triad is in discovery. This permits descriptive utility-stratified effects, but each advantageous and disadvantageous estimate comes from only one independent triad: a bootstrap interval for either stratum cannot quantify generalization. This split shares scenarios with the previous experiment, including discovery/evaluation overlap across runs; it is exploratory, not a fresh confirmatory test. Increasing intervention size, selecting doses after inspection, and trying multiple controls creates multiplicity; none of the intervals are adjusted for it. A selective, reproducible effect would be evidence for a causal influence on this measurement, not proof of a cooperation circuit.

Default configuration executes approximately 3,152 individual forward passes (160 discovery and 176 baseline/intervention presentations for 17 conditions), versus approximately 720 in the first screen. It has a four-hour GPU timeout, no automatic retry, and no dollar cap. Check the cost and decide whether to authorize it before launching. Both the implementation and the Modal execution path are prepared but have **not** been tested or executed as a sweep. A shorter diagnostic configuration is possible via `--doses 10,100 --random-controls 1`, but changing the planned sweep after inspecting results changes the interpretation. Preserve failed attempts.

```powershell
modal run modal_mechanistic_sweep.py `
  --model Qwen/Qwen2.5-1.5B `
  --revision 8faed761d45a263340a0528343f099c05c9a4323 `
  --doses 10,100,500,1000 `
  --random-controls 3 `
  --authorize-paid-run
```

Retrieve the printed ID with `modal volume get llm-coop-mechanistic <run-id> results/<run-id>`. Review `manifest.json`, `candidates.json`, `observations.jsonl` and `summary.json`. Recompute the summary with `python -m llm_cooperation.mechanistic.analyze_sweep results/<run-id>`. The summary reports paired candidate changes, candidate versus mean random-control effects, individual random controls, choice flips, calibration, and utility strata. Do not interpret net choice rate as the number of individual flips. The bootstrap is over independent template/triad groups, conditional on the observed random sets; it does not capture uncertainty over random-control sampling or compensate for the small number of groups. BF16 output quantization remains a limitation. Partial volume data is committed on normal exit and caught failures; hard termination can lose uncommitted results.
