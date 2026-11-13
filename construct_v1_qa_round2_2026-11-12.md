# Construct-v1 QA — round 2: preserving correct annotations while isolating failures

**Scope:** Source-grounded QA of saved Qwen2.5-32B-Instruct annotations; commit `fce5c80`. **No new inference, no change to original behavioural results.**

**Status:** An assistant-conducted diagnostic, **not** independent adjudication, and **not** a population error-rate estimate. Source strata are author-defined. The original classification file remains unchanged.

## What was checked

- Complete existing label distribution: **152 templates, 304 scenario versions, 608 wording judgments**.
- The previous source-grounded **24-template** diagnostic plus the already known customs role-inversion case were retained as context.
- An **additional 18 distinct templates** were sampled deterministically within original source strata, excluding the prior sample and customs. One human counterpart version and first cooperative wording per template were manually compared with the original scenario and Qwen judgment; no historical model-response outcomes were inspected for selection.
- All eight author-designated symmetric control templates were separately screened across **32** scenario-version-wording judgments.

## Preliminary conclusion

- **7/18** newly inspected cases showed no material issue in the principal fields inspected. This is **not a certification of all fields**, and the sample is not representative of the overall dataset.
- The remaining **11/18** contained one or more unsupported or disputable annotations. This **does not mean 11 confirmed errors**; uncertain labels, unsupported equality claims, and source contradictions differ in severity.
- Coherent, supported classifications include unilateral helping with explicit time or capacity costs, and information sharing with a stated recipient benefit.
- Recurring concerns are inferred opportunity costs, equality inferred from matched *partial* metrics or from silence, and missed recipient-useful information.

## New source-stratified sample (18 templates)

| Packet | Bank / template | QA status | Source-grounded rationale |
|---|---|---|---|
| `RV-422889` | `phase0 / template_008` | Review | Reciprocal QA-certificate exchange and pre-clearance are stated; Qwen correctly identifies exchange/information sharing. Equal outcomes for both and actor opportunity cost are not established relative to sequential customs inspection. |
| `RV-958316` | `phase0 / template_007` | Review | Mutual waypoint telemetry provides navigational clearance. Information sharing is supported; equal outcomes and an actor opportunity cost are not established relative to standard radar-only navigation. |
| `RV-736314` | `phase0 / template_001` | Review | Consolidated sky-survey registry explicitly adds no overhead or observing-schedule change; Qwen nevertheless assigns opportunity_cost. Information sharing is supported; global payoff equality is not established merely by unchanged schedule. |
| `RV-987308` | `phase0 / template_026` | No material issue found | Lending the loading ramp for thirty minutes provides requested access to the perishable-produce carrier and displaces actor loading time. Qwen correctly identifies unilateral help and an opportunity cost. |
| `RV-447825` | `phase0 / template_029` | No material issue found | Providing the nearby clinic with a power line uses 10% of generator capacity. Unilateral helping, recipient benefit, and a stated resource draw are supported. |
| `RV-172720` | `phase0 / template_018` | No material issue found | Splitting a wholesale timber invoice is a requested unilateral accommodation, requiring a specified fifteen minutes of administrative work. |
| `RV-968044` | `phase0 / template_035` | No material issue found | Surrendering an urgent medical-device production slot to a graduate student is assistance that sacrifices the actor's assigned slot and conflicts with a mandatory production objective. Lexical favourability is not certified here. |
| `RV-209278` | `phase0 / template_036` | Review | Sharing sealed-bid production costs with a competitor to coordinate tenders conflicts with independent public procurement requirements. Recipient benefit, realized actor cost, and lexical preference are not textually established; compatible_distinct goal structure misses the normative conflict. |
| `RV-990265` | `phase0 / template_051` | No material issue found | Painting an actively ruptured water pipe is explicitly ineffective; isolation before repair is materially better. Parallel activity and absence of dependence are plausible. The source stem lacks an explicit second-person actor, a separate role-normalization concern. |
| `RV-439736` | `phase0 / template_050` | Review | The target transmits on a decommissioned, unmonitored maritime radio band; the reference uses certified VHF. Qwen reports both outcomes unclear and neutral wording. Operational reference advantage is strongly suggested, though communication success is not quantified. |
| `RV-923613` | `phase0b / template_010` | Review | Cross-facility voltage synchronization is said to stabilize distribution feeders; no reserve draw or revenue change is specified. Qwen correctly says no actor cost is stated, but global actor/recipient equality is not proven from those two matched dimensions. |
| `RV-146034` | `phase0b / template_028` | Review | Dual-stream conveyor operation matches standalone actor time, labor, and refrigeration. Qwen correctly captures actor equality on these dimensions but invents opportunity_cost and asserts recipient equality/coordination benefit without stated evidence. |
| `RV-894769` | `phase0b / template_054` | No material issue found | Ultrasonic frequency interleaving is described without a quantified reference outcome or recipient gain. Qwen records outcomes unclear, actor cost uncertain, and parallel activity. Those cautious labels are defensible. |
| `RV-799073` | `phase0b / template_026` | Review | Combining conveyor operations saves twenty minutes of the actor's labor time. Qwen correctly records actor target_better but also assigns an unsupported opportunity_cost and recipient equal despite no explicit recipient comparison. |
| `RV-982684` | `phase0b / template_059` | Review | Linking encryption equipment delays the actor from thirty to forty minutes. Qwen correctly assigns actor reference_better, realized time cost, and recipient unclear; beneficial_not_necessary interdependence has no explicitly stated benefit. |
| `RV-181237` | `phase1 / phase1_tpl_024` | Review | SCADA alignment supplies the counterpart with vapor-flow rates specifically to prevent condenser icing, while actor moisture/denaturation metrics remain matched. Qwen labels recipient equal and actor opportunity cost; both overclaim what the source establishes. |
| `RV-295444` | `phase1 / phase1_tpl_020` | Review | Shared diesel-injection timing maps provide starboard engineers torque phase angles to eliminate hull vibration harmonics. Qwen labels recipient equal, assumes actor opportunity cost, and may overread joint production from information sharing. |
| `RV-980435` | `phase1 / phase1_tpl_001` | No material issue found | A shared GIS service matches actor export precision/time/cost while providing the partner reference benchmarks. Qwen correctly identifies information sharing, target_better for recipient, equal actor on stated measures, and no stated actor cost. |

## Dataset-wide screens and important limits

| Screen | Count | Interpretation |
|---|---:|---|
| Actor-cost `opportunity_cost` | 314/608 | Model assignments, **not 314 verified costs**. |
| Actor-cost `realized_cost` | 132/608 | Model assignments; some are based on risks rather than realized losses. |
| Interdependence `beneficial_not_necessary` | 403/608 | Common label; sometimes applied without explicit incremental benefit. |
| Symmetric controls: opportunity cost | 22/32 | Unsupported additional costs in controls that explicitly match stated outcomes. |
| Symmetric controls: beneficial-but-unnecessary | 14/32 | Conflicts with declared lack of added operational benefit under intended definition. |
| Same-version, two-wording difference in outcome and cost fields | 0/304 | Identical Qwen labels do **not** prove both wordings are semantically equivalent. |
| Matched human/AI actor-outcome discordance | 40/304 | **Triage flag**, not necessarily an error; substitutions can change capabilities. |
| Matched human/AI recipient-outcome discordance | 42/304 | Also a triage flag only. |

A broad keyword pass over all 608 judgments flagged **4** instances of explicitly shortened runtime with actor-outcome `equal`, **102** instances of broad no-additional phrasing with claimed beneficial interdependence, and **90** no-additional phrasing with claimed actor cost. The first includes the known pressure-testing contradiction. **The 102 and 90 are not error counts**: a statement of unchanged actor performance can coexist with a genuine recipient benefit, and broad regex cannot adjudicate the causal comparison.

## One important codebook issue identified

Some original negative-control stems are third-person descriptions such as “A human maintenance worker is applying ...” and do not explicitly begin with a second-person “you.” Consequently, the proposed deterministic role-binding normalizer must use canonical packet/action metadata and preserve an ambiguity flag; “find `you` in the stem” is not universally reliable.

## Working QA interpretation (not a gold standard)

1. Mark **supported** when the specific source language warrants a specific interaction or stated outcome.
2. Mark **unsupported** when Qwen asserts a new cost, equal global utility, or benefit absent explicit support; this is *not* a proven opposite outcome.
3. Mark **contradicted** only when the classification conflicts with an explicit source proposition, for example the pressure-testing time savings or tariff beneficiary reversal.
4. Mark **ambiguous** where legitimate constructions differ (e.g., whether “alongside” constitutes joint production, or whether a reference alternative shares a benefit).
5. Preserve the original v1 label and append field-specific QA judgments; never overwrite raw inference.
6. Keep stratified random adjudication of ostensibly clean annotations: selective QA of failures alone cannot estimate false negatives.

## Recommended immediate continuation

Continue source-grounded inspection **field by field**, starting with actor/recipient outcome attribution and cost, while retaining a random sample of apparently clean interaction labels. Use the current 42 distinct diagnostic templates (24 previous + 18 new) as development and failure-analysis cases, not as a held-out test set. Freeze a separate independent, outcome-blind adjudication sample before testing new prompts/models. No rerun of the 11-model behavioural experiment is indicated.

## Related artifact

Prior 24-case QA: `construct_v1_independent_quality_audit_2026-11-12.md`. Machine-readable annotations for the 18 new cases and screening tallies: `construct_v1_qa_round2_ledger.json`.
