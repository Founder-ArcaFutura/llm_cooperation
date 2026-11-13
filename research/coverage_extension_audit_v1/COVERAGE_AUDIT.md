# Preliminary coverage reconciliation

This is an incomplete audit and planning artifact, not an approved new battery. No inference was initiated. A label or an authored outcome is not a validated manipulation.

| Intended dimension | Current classification | Evidence and limitations |
|---|---|---|
| Seven mechanism arrangements | Partially implemented/confounded | `research/factorial_cooperation_v1/design_spec.json`, mechanism_cost: 7 × 2 in two exposed template implementations. Mechanisms overlap and differ in task and recipient outcomes. All three full runs were verified against their raw root-level run directories and `reports/factorial/three_model_full_comparison/analysis_manifest.json`: 4,576 presentations each. |
| Actor time cost | Partially implemented/confounded | Same block; 0 versus 20 minutes also changes recording from automatic to manual. `reports/factorial_qwen_smoke_instrument_audit.md` documents generic reference wording and apparent target asymmetry. |
| Actor benefit × counterpart benefit | Absent as a controlled cross | `research/multidimensional_cooperation_v1/taxonomy_v1.json` distinguishes incremental effects by party and dimension; factorial v1 does not cross both benefits. Historical `within_triad_choice_rates.csv` mixes consequence and wording changes. |
| Actor cost × recipient benefit | Partially implemented/confounded | V1 social conditions generally add the recipient check, parallel control does not; mechanism and benefit therefore change together. |
| Costly unreciprocated helping | Partially implemented/confounded | Information/resource/helping with cost and no stated return exists in mechanism_cost, but return and necessity are not independently crossed there. |
| Conditional return × cost | Partially implemented/confounded | V1 `return_cost`: conditional future saving also changes actor incentive. Guaranteed return is not reciprocity isolated from expected benefit. |
| Necessary interdependence × cost | Partially implemented/confounded | V1 `dependency_cost` changes reference outcomes and actor incentives with necessity. Necessity independent of consequences is not identified by this implementation. |
| Recipient perspective | Implemented but not evaluated across current cohort | `data/scenarios_phase2_other_agent_preference.json`; `reports/phase2_pilot_reanalysis_20261112.md` documents Qwen 2.5 3B pilot, not the requested three 7B models. Perspective and source controls need semantic review. |
| Choice-set removal and replacement | Partially implemented/confounded | `research/choice_set_phase0_followup_README.md`, `research/choice_set_followup_audit/AUDIT.md`, `results/choice_set/` contain historical tests; replacement options lack validated task/payoff equivalence. Removal changes choice set, distinct from permutations or blind labels. Exact cohort and presentation-level reconciliation remains pending. |
| Identity | Partially implemented/confounded | V1 crosses human and embodied automation descriptions, but affordances and perceived identity are not independently reviewed. |
| Goal relation | Partially implemented/confounded | Historical banks vary context and goals; no validated factorial shared/compatible/conflicting goal manipulation was established by this audit. |
| Harm, risk, and affected third parties | Partially implemented/confounded | Existing banks have competitive, risky or ineffective historical controls; outcome attribution and validity are unresolved. V1 has no crossed harm/risk block. |
| Wording and framing | Partially implemented/confounded | V1 uses sentence order rather than independently reviewed paraphrases. Source/paraphrase validity remains unresolved. |
| Option order | Implemented and evaluated across current cohort | All permutations are generated; position remains a diagnostic and does not control for choice-set composition. All three models have complete locally verified records. |
| Reciprocal exchange without any return | Conceptually infeasible under v1 definition | A conditional exchange without a return is incompatible with that label. Unconditional return and no-return help are separately meaningful conditions. |
| Necessity with invariant success under removal of a required contribution | Conceptually infeasible for the named outcome | If contribution is required, removing it necessarily changes that outcome, absent a substitute. Alternative outcome definitions and substitute mechanisms can be studied as different packages. |

## Execution evidence and safeguards

`v1_model_presentation_coverage.csv` enumerates all 13,728 model × presentation cells. Each full run was located at the repository root, and all rows were validated against the frozen input, model/revision, prompt/action mapping, numeric scores and run summary. Raw file and manifest hashes match `reports/factorial/three_model_full_comparison/analysis_manifest.json`. All are `full_verified`; the independent smoke flag records the separately verified smoke rows. No v1 inference is outstanding for this three-model cohort. Absence of an execution record in any future bank is not a negative result, and instrument failures are not model refusals.

## Remaining deliverables

The complete independently reviewable extension matrix, authored candidate conditions, outcome-ledger pairs, per-model new-battery manifests, runnable outstanding-only scheduler and analysis adapters have not yet been produced. They require construction and review; this preliminary audit must not be used as authorization to execute paid inference. Do not blend historic choice-set, recipient-perspective or v1 records as if they shared prompts, response coding or estimands.
