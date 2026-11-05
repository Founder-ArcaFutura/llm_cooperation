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

Default configuration executes approximately 3,152 individual forward passes (160 discovery and 176 baseline/intervention presentations for 17 conditions), versus approximately 720 in the first screen. It has a four-hour GPU timeout, no automatic retry, and no dollar cap. Check the cost and decide whether to authorize it before launching. An earlier 10–1,000 sweep was reported as completed; the subsequently expanded caps have not been tested. A shorter diagnostic configuration is possible via `--doses 10,100 --random-controls 1`, but changing the planned sweep after inspecting results changes the interpretation. Preserve failed attempts.

```powershell
modal run modal_mechanistic_sweep.py `
  --model Qwen/Qwen2.5-1.5B `
  --revision 8faed761d45a263340a0528343f099c05c9a4323 `
  --doses 10,100,500,1000 `
  --random-controls 3 `
  --authorize-paid-run
```

Retrieve the printed ID with `modal volume get llm-coop-mechanistic <run-id> results/<run-id>`. Review `manifest.json`, `candidates.json`, `observations.jsonl` and `summary.json`. Recompute the summary with `python -m llm_cooperation.mechanistic.analyze_sweep results/<run-id>`. The summary reports paired candidate changes, candidate versus mean random-control effects, individual random controls, choice flips, calibration, and utility strata. Do not interpret net choice rate as the number of individual flips. The bootstrap is over independent template/triad groups, conditional on the observed random sets; it does not capture uncertainty over random-control sampling or compensate for the small number of groups. BF16 output quantization remains a limitation. Partial volume data is committed on normal exit and caught failures; hard termination can lose uncommitted results.

## Amplification and sign-separated interventions

`modal_mechanistic_amplification.py` is a separate exploratory experiment. It uses the deterministic split described for the larger sweep, ranks all varying discovery neurons by absolute correlation, then constructs three sets of `group_size` neurons (100 by default): the top overall, the top positively correlated, and the top negatively correlated from the full ranking. The sets overlap; positive/negative labels describe observational correlations, not causal signs. If there are too few candidates of either sign the run stops and records failure.

For each set, multiply the existing `down_proj` input activation at the last prompt token by 0, 1.5, or 2. Factor 1 is the shared unmodified baseline; 0 is zero ablation. Multiplication preserves the sign of a negative activation and does little to a near-zero activation. For each set, two independently seeded layer-matched random sets are sampled excluding the top 1,000 and every selected neuron across the three groups; the same random sets are used across all factors for that group. `candidates.json` records all sets, correlations, and the mean absolute group-average activation, which is not the distribution of individual activations. Larger factors can move activations outside their natural range. BF16 output precision remains a limitation.

This is exploratory, with overlapping candidate sets, shared data with previous runs, only eight held-out groups, one utility triad, and multiple comparisons. Bootstrap intervals resample groups and do not account for selection, multiplicity, or uncertainty across random-control draws. Unchanged calibration accuracy does not demonstrate intact general capability. The intervention and analysis scripts have not been tested or run. No inference takes place until the user runs a command.

The default has about 5,088 forward passes (160 discovery plus 176 presentations for 28 conditions). Modal uses an A10G with a four-hour timeout, no automatic retries, and no dollar cap. Check budget before launching. Preserve failure artifacts. The prior Modal volume commit caveats apply.

```powershell
modal run modal_mechanistic_amplification.py `
  --model Qwen/Qwen2.5-1.5B `
  --revision 8faed761d45a263340a0528343f099c05c9a4323 `
  --group-size 100 `
  --random-controls 2 `
  --authorize-paid-run
```

Retrieve the printed ID with `modal volume get llm-coop-mechanistic <run-id> results/<run-id>`. Inspect `manifest.json`, `candidates.json`, `observations.jsonl` and `summary.json`; reanalyze with `python -m llm_cooperation.mechanistic.analyze_amplification results/<run-id>`. The summary includes group-clustered paired margins, candidate versus mean random controls, calibration and individual argmax flips. As always, a model choice flip is not itself evidence of a cooperation-specific mechanism.


## Raising intervention sizes

Both Modal entry points and their workers now permit a maximum dose or amplification group size of 100,000; defaults remain unchanged. This is a software ceiling, not a guarantee that a dose is scientifically interpretable or that a matched control can be constructed. Qwen2.5-1.5B has 8,960 intermediate neurons per layer. For each layer, random controls must contain as many coordinates as that layer's candidate set while excluding the relevant candidate pool. If there are too few available, the run explicitly fails after discovery, potentially after GPU charges. There must also be enough varying neurons of each correlation sign for amplification. Larger ablations may impair general computation; monitor calibration and use additional selectivity checks. The output logs preserve the exact selected and random sets.

For example, explicitly extending the prior sweep:

```powershell
modal run modal_mechanistic_sweep.py `
  --model Qwen/Qwen2.5-1.5B `
  --revision 8faed761d45a263340a0528343f099c05c9a4323 `
  --doses 10,100,500,1000,2000,5000,10000 `
  --random-controls 3 `
  --authorize-paid-run
```

That configuration performs about 5,264 forward passes and has a four-hour timeout, with no dollar cap. Random sets at earlier doses can differ from the previous run because controls exclude the entire largest candidate set for the new run. Record this when comparing results. The larger-cap code has not been tested or executed.

For sign-separated ablation and amplification of 1,000 neurons per group, use `modal run modal_mechanistic_amplification.py --model Qwen/Qwen2.5-1.5B --revision 8faed761d45a263340a0528343f099c05c9a4323 --group-size 1000 --random-controls 2 --authorize-paid-run`. It retains the 0, 1.5, and 2 multipliers and approximately 5,088 forward passes regardless of group size.

## Disjoint rank-band follow-up (prepared, not executed)

The separately prepared `modal_mechanistic_bands.py` reads the exact ranked coordinates from a supplied completed sweep, then independently zeros ranks 1–100, 101–500, 501–1,000, 1,001–1,250, and 1,251–2,000 with three layer-matched random controls per band. The run validates the model revision, bank fingerprints, and split against the source manifest and records canonical JSON hashes and copies of the supplied inputs. Source files are not cryptographically bound to one another by the old manifest, so verify their common origin. Controls exclude the first 2,000 candidates but are not activation- or output-influence matched. Separate-band ablations estimate effects on baseline; they cannot alone explain interactions when multiple bands are ablated together. Both datasets have already informed analysis, so this is exploratory.

The completed local 2,000-candidate source is `mechanistic_artifacts/mechanistic-sweep-f0942041aa324255a2969f3b3ae38466`. The full follow-up is 21 conditions × 176 presentations = 3,696 forward passes, with a four-hour A10G timeout, no dollar cap and no automatic retries. It is a newly prepared, untested script; review cost and obtain explicit paid authorization before running. No such run has been launched by preparing it.

```powershell
modal run modal_mechanistic_bands.py `
  --source 'G:\llm_cooperation\mechanistic_artifacts\mechanistic-sweep-f0942041aa324255a2969f3b3ae38466' `
  --random-controls 3 `
  --authorize-paid-run
```

The local-only `python -m llm_cooperation.mechanistic.analyze_reversal <run-directory> --band-ends 100,500,1000,1250,1500,1750,2000 --output <new-path>.json` inspects existing observations and ranks, with no inference. It reports exact-score ties in addition to argmax flips. Never overwrite source outputs.

## Focused 101–500 follow-up (prepared, not executed)

`modal_mechanistic_focus.py` reads the exact candidate ranking of the completed source sweep and tests ten overlapping candidate sets: the 400-neuron ranks 101–500, its four 100-neuron rank blocks, positive and negative discovery-correlation subsets, and subgroups in layers 20–22, 23–25, and other layers. Every set has three independently seeded layer-matched random controls, sampled outside the first 2,000 candidates. The source manifest, candidate provenance, bank fingerprints and split are checked, and the used source files, coordinate sets and controls are recorded. Controls are not matched for activation magnitude or output influence. No new candidate ranking is computed.

For each set the summary records margin shifts and matched-control differences overall and stratified by the letter assigned to cooperation, plus tie-aware unique-winner flips and factual calibration. These are overlapping exploratory comparisons on the same eight previously analyzed groups; bootstrap intervals are not corrected for selection or multiplicity. Results cannot by themselves separate semantic strategy from position or establish a circuit. Scores remain BF16 and exact ties depend on that precision. True specificity requires reviewed new scenarios, other task formats, matched controls and higher-precision replay.

The default has 41 conditions × 176 presentations = 7,216 forward passes; an A10G has a four-hour timeout, no enforced dollar cap, and no automatic retries. A `huggingface-secret` Modal secret is configured, consistent with the existing local bands runner. Check resource cost before authorizing. Basic subgroup and summary logic passed local synthetic tests; the model/Modal path is untested. No paid run has been launched.

```powershell
modal run modal_mechanistic_focus.py `
  --source 'G:\llm_cooperation\mechanistic_artifacts\mechanistic-sweep-f0942041aa324255a2969f3b3ae38466' `
  --random-controls 3 `
  --authorize-paid-run
```

Download the printed run ID from `llm-coop-mechanistic`, and inspect the manifest, exact subgroup and control coordinates, raw observations and summary. Run `python -m llm_cooperation.mechanistic.analyze_focus <run-directory>` to regenerate a completed run's summary. As with earlier runners, a hard container termination can lose uncommitted volume writes.
