# Research index

This index is a guide to the evidence and work streams in the repository. It distinguishes the primary behavioral cohort from follow-up assays, technical diagnostics, and exploratory mechanistic work. A phase label describes the project's sequence; it does not by itself mean that a study is confirmatory or independently reviewed.

## Read the evidence first

1. [Canonical manuscript](reports/manuscript_readiness/MANUSCRIPT_V1.md) — current synthesis of the main cohort, controls, results, and limitations.
2. [Manuscript readiness report](reports/manuscript_readiness/MANUSCRIPT_READINESS_REPORT.md) — provenance reconciliation, calibration and parser diagnostics, and sensitivity analyses.
3. [Cohort provenance manifest](reports/manuscript_readiness/cohort_provenance_manifest.json) and [statistical readout](reports/manuscript_readiness/cohort_statistical_readout.json) — run identities, source hashes, and canonical descriptive estimates.
4. [Post-hoc significance methods](reports/manuscript_readiness/POSTHOC_SIGNIFICANCE_METHODS.md) — inferential assumptions and exploratory tests.
5. [Blinded review brief](reports/manuscript_readiness/AUTHOR_REVIEW_BRIEF.md) — outstanding human review and adjudication needs.

The cohort manuscript reports descriptive forced-choice evidence as primary. Its post-hoc tests, family summaries, and choice-set intervention are exploratory. The manuscript's source snapshot and analysis provenance should be read with those conclusions; older drafts and summaries may have superseded values.

## Study sequence

| Stage | Question and design | Best entry points | Evidence status |
| --- | --- | --- | --- |
| **Phase 0: initial screen** | Does a constrained four-option screen show a measurable strategy-selection pattern? The original bank contains 24 scenarios and four counterbalanced presentations per scenario. | [Phase 0 protocol](docs/phase0_protocol.md) · [Original scenario bank](data/scenarios.json) · [Qwen 2.5 3B example report](reports/phase1_qwen3b/phase0_report_Qwen_Qwen2.5-3B_run_Qwen_Qwen2.5-3B_20261104_225437_9d3a9b99.md) | Exploratory starting point. It motivated later measurement controls and is not the full research programme. |
| **Phase 0 expansion** | Broader scenarios, contexts, and model coverage; added objective calibration and exploratory/held-out partitions. | [Expanded-study protocol](docs/expanded_study_protocol.md) · [Expanded scenario bank](data/scenarios_v1_expanded.json) · [Phase 0B audit analysis](phase0b_audit_analysis_20261104.md) | Historical evidence; bank/review status and executed rows must be checked against the canonical manuscript before making confirmatory claims. |
| **Phase 0B: utility matching and wording** | Compare cooperation with independent action in scenarios designed to match the actor's nominal utility; pair original and rewritten cooperative wording; retain human/AI partner variants and negative-control contexts. | [Utility-matched protocol](docs/phase0b_utility_matched_protocol.md) · [Canonical results](reports/manuscript_readiness/MANUSCRIPT_V1.md) · [Readiness audit](reports/manuscript_readiness/MANUSCRIPT_READINESS_REPORT.md) | Main descriptive evidence. 11 responsive base checkpoints across seven families had positive cooperation-minus-independence margins in both later banks. Scenario meaning and wording equivalence still need independent blinded review. |
| **Phase 1: separate scenario bank** | Check whether the pattern appears in a later bank with its own scenario templates and paired wording. | [Phase 1 protocol](research/phase1/PROTOCOL.md) · [Provisional results](research/phase1/PROVISIONAL_RESULTS_20261104.md) · [Canonical chronology and status discussion](reports/manuscript_readiness/MANUSCRIPT_V1.md) | The bank's prospective designation has an unresolved review and execution chronology. It is not described as a formally eligible prospective replication. |
| **Lexical robustness** | Test whether the measurement changes when cooperative language is rewritten or expanded into alternative lexical forms. | [Lexical confound pilot](docs/lexical_confound_pilot.md) · [Cooperative wording work](research/cooperative_lexical_geometry_v1/README.md) · [Canonical paired wording results](reports/manuscript_readiness/MANUSCRIPT_V1.md) | Specific wording sensitivity is measured; broad semantic invariance is not established. The main paired paraphrases await blinded equivalence review. |
| **Option-order robustness** | Randomize additional option schedules and compare strategy choice, order sensitivity, and calibration alongside the original schedule. | [Replication design](docs/dose_response_option_order_replications.md) · [Schedule comparison](reports/dose_response_order_comparison/comparison.md) | Exploratory replications. Keep schedule-level variation and calibration failures visible; they are not independent model-training replications. |
| **Choice-set intervention** | Remove the cooperative option and observe choices among the remaining alternatives. | [Intervention overview](research/choice_set_intervention_README.md) · [Follow-up audit](research/choice_set_followup_audit/AUDIT.md) · [Canonical analysis](reports/manuscript_readiness/MANUSCRIPT_V1.md) | Exploratory intervention. Substitution after changing the choice set does not establish a stable preference ranking in the original four-option task. |
| **Payoff and factorial extensions** | Vary payoff levels and task attributes to probe context and dose sensitivity. | [Dose-response expansion plan](docs/dose_response_expansion_and_format_plan.md) · [Option-order and dose report](reports/dose_response_order_comparison/comparison.md) · [Three-model factorial report](reports/factorial/three_model_full_comparison/REPORT.md) | Separate exploratory assays with their own stimulus, coverage, and calibration limits. Inspect each report before comparing it with the main cohort. |
| **Training and checkpoint emergence** | Ask whether behavior changes across training checkpoints or model variants. | [OLMo emergence materials](research/olmo2_emergence/) · [Pythia emergence protocol](dose_response_jules/docs/payoff_dose_response_and_emergence_protocol.md) | Exploratory and checkpoint-specific. Do not infer a general training effect from a single lineage or incomplete checkpoint series. |
| **Mechanistic probes** | Explore whether internal activations or interventions track strategy distinctions under controlled prompts. | [Mechanistic exploration](docs/mechanistic_exploration.md) · [Phase 1 mechanistic plan](docs/phase1_mechanistic_plan.md) · [Contrastive mapping report](mechanistic_artifacts/safe_download_full/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9/analysis/contrastive_report.md) | Exploratory probes only. They do not establish a cooperation circuit or causal mechanism. |
| **Other-agent preference and lexical strategy bridge** | Develop related scenario annotations and investigate lexical structure around strategy selection. | [Other-agent preference bank](data/scenarios_phase2_other_agent_preference.json) · [Lexical geometry work](research/cooperative_lexical_geometry_v2_wordlevel/README.md) | Active research threads; read their own audits and branch history before treating them as completed empirical findings. |

## Controls and interpretation

- **Moral vocabulary:** The primary scenario banks avoid moralizing labels. The canonical cohort does not contain a completed explicit moral-framing inversion test. Reversing moral labels or evaluative framing while holding outcomes constant remains a useful open control.
- **Option order:** Counterbalanced rotations and additional randomized schedules expose letter-position dependence. Near-invariant letter responding is an instrument failure, not a strategy-level null result.
- **Negative controls:** Objective-conflict and ineffective/inappropriate contexts distinguish context-sensitive selection from blanket endorsement of cooperative wording.
- **Nominal utility matching:** Matching is a property of scenario construction. It does not prove that a model understood the scenario or represented the two actions as equally valuable.
- **Lexical rewrites:** Paired wording tests cover the tested substitutions only. Human review is needed before treating the variants as semantically equivalent.
- **Calibration and response channels:** Forced-choice argmax, conditional answer probabilities, and free generation are distinct measurements. Calibration, ties, format validity, and position diagnostics qualify the interpretation of strategy rates.
- **Clustering and multiplicity:** Repeated rotations, partner versions, and wording pairs belong to scenario/template clusters. Do not count each presentation as an independent case. The manuscript's post-hoc tests remain exploratory.

## Branch map

The repository has several parallel histories. This is a navigation aid for the principal streams visible in the current checkout, not a completed audit or merge recommendation. Branch links open the branch history on GitHub; files and validation status can differ by branch.

| Work stream | Branch |
| --- | --- |
| Original Phase 0 harness | [`main`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/main) |
| Expanded behavior and Phase 0B finalization | [`phase0b-finalize`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/phase0b-finalize) |
| Randomized option-order replications | [`codex/dose-response-option-orders`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/codex/dose-response-option-orders) |
| Checkpoint-level training emergence | [`phase_1a_training_emergence`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/phase_1a_training_emergence) |
| Other-agent preference | [`codex/phase2-other-agent-preference`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/codex/phase2-other-agent-preference) |
| Lexical strategy bridge | [`codex/lexical-strategy-bridge`](https://github.com/Founder-ArcaFutura/llm_cooperation/tree/codex/lexical-strategy-bridge) |

## Open research questions

1. Do independent reviewers agree that scenarios convey the intended utility, partner consequences, and non-moralized strategy distinctions?
2. Does the measured pattern persist in a formally eligible prospective replication across multiple independently calibrated model families?
3. How much of the response depends on option order, answer-token compatibility, ties, and the gap between forced choice and free generation?
4. Does behavior respond systematically to payoff magnitude, partner benefit, and task context, including flat, negative, and heterogeneous effects?
5. What changes under an explicit moral-framing inversion that preserves outcome structure?
6. Do mechanistic probes survive stronger controls and held-out validation, and can any causal interpretation be distinguished from response-format effects?

## Provenance and artifact handling

Prefer the canonical manuscript, its readiness report, manifests, and immutable run identifiers over older summaries. Keep raw results and derived analyses attached to their source bank, prompt/rendering version, model revision, analysis version, and branch history. A phase index is not evidence that separate branches have been merged, nor that every local artifact is published on the default branch.
