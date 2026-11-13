# Proposed extension matrix: design review draft

The purpose is to separate named outcomes and decision perspective while preserving the existing v1 data. This matrix specifies prospective contrasts; its entries are **not yet authored, validated, or approved stimuli**. All three verified v1 runs remain distinct evidence. Every new approved cell must be presented to all three pinned 7B models, with identities and option order counterbalanced.

## Block A: benefits, cost, and decision perspective

Use the same authorized information-transfer action in each row. Relative to a specified alternative, the action can give the actor an additional useful check (A = 1), give the counterpart an additional useful check (B = 1), both, or neither. The actor incurs 0 or 20 additional minutes only if the action is performed. No future benefit, promise, payment, safety change, or other effect is stated. The independent record must explicitly say whether each additional check occurs under each option; silence is not zero.

| Actor additional check A | Counterpart additional check B | Target relative to reference | Interpretation |
|---:|---:|---|---|
| 0 | 0 | Actor: no additional check; counterpart: no additional check | Outcome-neutral control; if cost = 20, redundant costly action control |
| 0 | 1 | Actor: no additional check; counterpart: additional check | One-way helping; cost = 20 is costly unreciprocated helping |
| 1 | 0 | Actor: additional check; counterpart: no additional check | Actor-only advantage |
| 1 | 1 | Actor: additional check; counterpart: additional check | Mutual benefit |

Cross these four rows with cost `{0,20}` and perspective `{actor chooses, counterpart affected expresses preference}`: **16 cells per independently authored family**. In recipient perspective, the other agent controls the action and the model is the affected counterpart; ask which action the model wants the decision-maker to take. Keep physical roles and outcome allocation fixed, and do not infer that a stated preference is the recipient's own cooperative behavior. A perspective change alters agency and question wording; it is an experimental package, not a pure decontextualized viewpoint toggle.

Primary contrasts: actor benefit effect conditional on counterpart benefit and cost; counterpart benefit effect conditional on actor benefit and cost; cost effect conditional on both; and their interactions. Report effects separately by perspective. A neutral no-benefit/costly target is a negative control, not assumed to be selected zero times. The target and reference should name concrete, comparably complete plans. Exact outcome encoding, credibility of the zero cost, and absence of hidden incentives require independent review.

## Block B: return and incentives

For a fixed costly assistance action, cross cost `{0,20}` with return `{none, guaranteed conditional service saving actor 10 minutes}`: **4 cells**. State separately what each party gets under both actions. Compare conditional return to no return as a return-plus-future-benefit package. An additional unconditional-service control should be authored with the same future service regardless of choice; it tests changed contingency but also alters the reference outcome. Neither comparison isolates reciprocity independent of expected consequences.

## Block C: goal relation

Three separately authored goal arrangements: `{shared named goal, compatible distinct goals, conflicting goals}`. Preserve physical action and explicit outcome table where logically possible. Conflict necessarily changes at least one goal or valuation; this is a goal-framing/outcome package. Review broad versus immediate goal scope, action feasibility, and whether the purported conflict is real. These are categorical conditions, not a continuous alignment scale.

## Block D: harm and risk

For the same transfer decision, use `{no additional harm stated explicitly, certain named third-party harm, specified probability of named third-party harm}` as separate conditions. Disclose magnitude, affected party, baseline, probability and authority; avoid arithmetic implying equal expected disutility without human judgment. Certain harm versus risk differs in uncertainty and expected outcomes. These cells are not a pure risk-aversion measurement. Obtain independent review for plausibility and agency.

## Block E: choice-set intervention

Construct each set from a single common condition with fixed shared option texts and outcomes:

1. Base: target, reference, and realistic independent alternative.
2. Removal: reference and the same independent alternative; target absent.
3. Replacement: reference, same independent alternative, and a separately reviewed neutral alternative in place of target.

Each set receives every feasible permutation. Matched alternative outcomes and plausibility must be explicit and independently reviewed; a neutral label alone proves nothing. Removing the target does not measure a hidden second preference from the base set. Replacement effects include the identity and properties of the new alternative. Balance target-present, target-absent, and replacement conditions without equating these changes to position rotation or label blinding.

## Family sampling, validation, and implementation gaps

Construct at least two independently authored domains for development; additional unexposed independently authored families are needed for prospective generalization and must be kept outside prompt tuning. A noun-swapped copy does not provide independent replication. Set family count through uncertainty and power simulation, not an arbitrary compute limit. No factorial claim may rely on excluded or infeasible corners; record exclusions and estimate only contrasts supported by retained complete cells.

Before inference: write full scenario and option text, per-party ledgers for every option, source provenance and hashes, explicit transformations and restrictions. Two independent reviewers must check authority, role/perspective, baseline outcomes, cost, probability, goal assignment, option feasibility, framing, identity capabilities and outcome equivalence. Preserve disagreement and adjudication; do not force an assignment. Separately probe model comprehension, keeping all-eligible analyses primary.

**Not yet completed:** scenario text, counterbalanced presentations, presentation-level per-model manifest, outstanding-cell selection, integration for recipient-perspective and variable-sized choice sets, numerical analysis adapters, and tests. Existing v1 `prepare()` assumes specific stem, binary/four-action structure and permutations and cannot safely be pointed at this proposal unchanged. New inference is not approved by this document.

`proposed_extension_cells.json` contains the 29 logical condition specifications above; `proposed_model_condition_coverage.csv` expands these to 87 explicitly ineligible model-condition placeholders. They do not yet represent authored families, frozen prompts, or permission to execute.
