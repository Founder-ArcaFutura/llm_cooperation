# Replacement-option audit and review queue

Status: preliminary Codex triage, not independent review or a validation. The CSV covers all 244 scenario/partner variants (122 templates; selected Phase 0B payoff-tier variants intentionally share wording). It includes the original stem and all four options so a reviewer can judge the replacement in context. Source banks and options were not edited.

The original equal-utility specifications compare the existing cooperation and independence options; they do not establish the actor payoff of the newly written alternative. Do not interpret the replacement as payoff-matched or neutral without additional evidence. A literal prefix-based triage marks 76 of 120 Phase 0 variants and 100 of 124 Phase 0B variants as beginning with an inspection, check, record, request, comparison, or similar action. This is a broad mechanical flag, not a finding that all flagged items fail to complete the task; nor does lack of a flag mean an item passes. Every row remains unadjudicated.

Concrete examples of concerns:

- Phase 0 `expanded_001_human`: recording observation metadata on paper is not shown to produce the combined registry or complete the described analysis. Its payoff and task completion relative to the other options are unknown.
- Phase 0B `phase0b_001_human`: recording telescope metadata on paper differs from processing sky-survey logs; the original three-minute, zero-cost equivalence does not extend to it.
- Phase 0B `phase0b_016_human`: inspecting centrifuge rotor balance is not shown to spin the chemical vials, so it can be an additional precondition instead of a substitutable task outcome.
- Phase 0 `expanded_060_ai`: inventorying already shredded material differs from archiving intact legal records and may be salient precisely because it concerns destroyed records; it is not a matched alternative.

The review matrix is a review aid, not a set of certified judgements. Review task completion, feasibility, distinctness, actor outcome, partner effect, effort, risk, social tone, and lexical overlap in both partner variants. The appropriate interpretation of this condition may require revising and independently checking the replacements before collection. An independently reviewed instrument does not yet exist. Generation and positional scoring outcomes remain descriptive, and this triage does not fix the three-option position bias observed in some models.

Reproduce the matrix with `python scripts/audit_choice_set_followup_replacements.py`.
