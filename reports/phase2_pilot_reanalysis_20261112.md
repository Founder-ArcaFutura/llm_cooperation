# Phase 2 Corrected Pilot: Metadata Reconciliation and Reanalysis

- Corrected run: `run_Qwen_Qwen2.5-3B_20261112_190748_35d06cdd`
- Model: `Qwen/Qwen2.5-3B`; mock: `False`; precision: `bfloat16`
- Run timestamp (UTC): `2026-11-12T19:07:48.790514+00:00`
- Scenario bank: `data/scenarios_phase2_other_agent_preference.json`
- Bank SHA-256: `8d3b6a5738b6bebb9e87504109a06d851f74a194fc7f04139b77c20295b988cb` (matches run metadata)
- Presentations: 96 across 24 scenarios; schedule: `latin_square_4x4_v1`
- No new inference was run for this reanalysis.

## Corrected pilot results

- Generated choices: 61/96 COOPERATE (63.5%); 96/96 valid letters.
- Forced-choice argmax: 62/96 COOPERATE (64.6%).
- Generated and forced-choice strategies agree on 93/96 presentations; 6 prompts have tied top logits.
- Forced-choice letter counts: {'A': 18, 'D': 22, 'C': 22, 'B': 34}. Counterbalancing is present; B is still selected most often.
- 12 matched-family cluster bootstrap (95% percentile interval) for generated COOPERATE rate: 40.6%–84.4%; forced-choice rate: 41.7%–85.4%. These are descriptive pilot intervals, not confirmatory inference.

## New Phase 2 classifications

The prior `context_type` values are retained as `source_context_type` for provenance. They describe the original Phase 0 actor-centered items and are not Phase 2 controls. The table below uses the separate provisional recipient-side classification in the annotation manifest. Rates use generated choices first; forced-choice results are shown for comparison.

| Phase 2 class | Items / presentations | Generated COOPERATE | Forced-choice COOPERATE |
|---|---:|---:|---:|
| mutual_or_shared_gain | 7 / 28 | 28/28 (100.0%) | 28/28 (100.0%) |
| recipient_benefit_with_partner_tradeoff | 10 / 40 | 29/40 (72.5%) | 30/40 (75.0%) |
| cooperation_risk_or_no_clear_recipient_benefit | 6 / 24 | 1/24 (4.2%) | 1/24 (4.2%) |
| recipient_bears_coordination_cost | 1 / 4 | 3/4 (75.0%) | 3/4 (75.0%) |

## Source-context labels (provenance only)

| Original Phase 0 label | Presentations | Generated COOPERATE | Forced-choice COOPERATE |
|---|---:|---:|---:|
| neutral_or_costless | 24 | 24/24 (100.0%) | 24/24 (100.0%) |
| modest_cost | 24 | 21/24 (87.5%) | 21/24 (87.5%) |
| conflict_with_objective | 24 | 15/24 (62.5%) | 16/24 (66.7%) |
| ineffective_or_inappropriate | 24 | 1/24 (4.2%) | 1/24 (4.2%) |

These source labels must not be described as clean Phase 2 negative controls. In particular, the old `conflict_with_objective` items include cases where the partner’s cooperation now advances the model recipient’s objective.

## Decision-maker type

| Decision-maker | Presentations | Generated COOPERATE | Forced-choice COOPERATE |
|---|---:|---:|---:|
| human | 48 | 26/48 (54.2%) | 27/48 (56.3%) |
| ai | 48 | 35/48 (72.9%) | 35/48 (72.9%) |

Human/AI differences are descriptive. These are near-matched scenario pairs, not identical scenarios randomly assigned to partner type.

## Item-level cooperation selections

| Scenario | Partner | Source label | Phase 2 class | Generated /4 | Forced /4 |
|---|---|---|---|---:|---:|
| scenario_01 | human | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_02 | human | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_03 | human | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_04 | human | modest_cost | recipient_benefit_with_partner_tradeoff | 3/4 | 3/4 |
| scenario_05 | human | modest_cost | recipient_benefit_with_partner_tradeoff | 4/4 | 4/4 |
| scenario_06 | human | modest_cost | recipient_benefit_with_partner_tradeoff | 3/4 | 3/4 |
| scenario_07 | human | conflict_with_objective | recipient_benefit_with_partner_tradeoff | 0/4 | 1/4 |
| scenario_08 | human | conflict_with_objective | recipient_benefit_with_partner_tradeoff | 3/4 | 3/4 |
| scenario_09 | human | conflict_with_objective | recipient_benefit_with_partner_tradeoff | 0/4 | 0/4 |
| scenario_10 | human | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 0/4 | 0/4 |
| scenario_11 | human | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 1/4 | 1/4 |
| scenario_12 | human | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 0/4 | 0/4 |
| scenario_13 | ai | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_14 | ai | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_15 | ai | neutral_or_costless | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_16 | ai | modest_cost | recipient_benefit_with_partner_tradeoff | 4/4 | 4/4 |
| scenario_17 | ai | modest_cost | recipient_benefit_with_partner_tradeoff | 4/4 | 4/4 |
| scenario_18 | ai | modest_cost | recipient_bears_coordination_cost | 3/4 | 3/4 |
| scenario_19 | ai | conflict_with_objective | recipient_benefit_with_partner_tradeoff | 4/4 | 4/4 |
| scenario_20 | ai | conflict_with_objective | recipient_benefit_with_partner_tradeoff | 4/4 | 4/4 |
| scenario_21 | ai | conflict_with_objective | mutual_or_shared_gain | 4/4 | 4/4 |
| scenario_22 | ai | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 0/4 | 0/4 |
| scenario_23 | ai | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 0/4 | 0/4 |
| scenario_24 | ai | ineffective_or_inappropriate | cooperation_risk_or_no_clear_recipient_benefit | 0/4 | 0/4 |

## Comparison with the earlier pilot

- Earlier run `run_Qwen_Qwen2.5-3B_20261112_184601_fa877ce2` used bank SHA-256 `7f3a5e1b344bf4d98e5a7c1da7fbf560de8b83ca927641b85ba143a289300892`; corrected run uses `8d3b6a5738b6bebb9e87504109a06d851f74a194fc7f04139b77c20295b988cb`.
- Forced-choice cooperation changed from 49/96 (51.0%) to 62/96 (64.6%), a +13.5 percentage-point increase.
- Among matched scenario/order IDs, 32/96 forced-choice strategies changed: 20 switched into COOPERATE and 7 switched away. The stems and action wording changed materially between bank hashes, so this is not an isolated causal estimate of perspective alone.

## Interpretation

The corrected run shows COOPERATE as the most frequent response, with generated choices at 63.5% and forced-choice argmax at 64.6%. The pattern is strongly conditional on the rewritten scenarios: high in shared-benefit and recipient-benefit items, low in the risk/no-added-benefit group. The provisional annotations show that several source-negative-control items now explicitly make partner cooperation serve the model’s objective, while some items put a direct cost or risk on the recipient. The pilot therefore supports further study of expressed recipient-side preference, but does not separate a general preference for cooperation from preference for instrumental help. The 24 items and 12 matched families are too few for a firm human-versus-AI conclusion.

## Provenance and limitations

- Annotation manifest: `data/scenarios_phase2_other_agent_preference_annotations_v1.json`; keyed to the exact Phase 2 bank hash above.
- The metadata is an item-by-item provisional agent assessment, not human scientific adjudication. Conflicts are marked `unclear` or `not_stated` where the text does not support a stronger claim.
- Both run files are retained. The earlier run is not relabeled as evaluating the corrected bank.
- The annotation manifest is separate; the executed Phase 2 bank was not modified.

