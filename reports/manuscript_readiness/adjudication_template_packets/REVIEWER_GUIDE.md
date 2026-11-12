# Blinded template-level adjudication guide

## Purpose and workload

The source queue has 304 scenario rows. Each bank-specific template has one human-partner scenario and one AI-partner scenario. The reviewer package groups those two scenarios into one packet, yielding **152 template packets** rather than 304 separate rows.

Start with the **76 priority packets** that support the main nominally equal-utility, non-symmetric comparisons: 52 Phase 0B templates and 24 Phase 1 templates. After that review and reconciliation, extend the same process to the remaining 76 templates supporting Phase 0 conditions, utility sensitivity triads, and symmetric controls.

Files:

- `priority_76_blinded_packets.csv` / `.json`: first review batch, 76 packets.
- `priority_review_response_template_76.csv`: matching 76-row response sheet; duplicate a fresh copy for each reviewer.
- `all_152_blinded_packets.csv` / `.json`: complete 152-packet set.
- `review_response_template_152.csv`: blank response columns for one reviewer copy. Make a separate copy per reviewer.
- `INTERNAL_UNBLINDING_KEY.json`: coordinator only. It contains bank, template, partner, condition, and wording-source mappings. Do not provide it to reviewers before independent scoring and disagreement resolution are complete.
- `COORDINATOR_PRIORITY_MANIFEST.csv`: coordinator only; identifies the priority cohort without requiring a search through the key.

The original 304-row source queue is preserved. These packet files are derived review materials and do not change experimental records.

## Blinding

Each packet shows two scenario versions together, labeled A and B. Their order is randomized. Within each version, the two cooperative-action formulations are labeled 1 and 2; their order is independently randomized per source scenario. The package omits bank, template ID, scenario ID, partner label, context type, utility condition, symmetry/control status, source split, automated flags, original/paraphrase labels, and all model outputs.

The scenario prose itself may reveal whether the counterpart is a person or an automated system. That content cannot be hidden while reviewers assess partner-version equivalence. Reviewers should not be told which packet cohort is primary, which wording is original, or the models' responses.

## Independent scoring

Two reviewers should score each assigned packet independently before seeing one another's answers. For each scenario version, score each cooperative wording against the independent action:

- `EQUAL`: the described focal-actor outcome appears approximately equivalent.
- `COOPERATIVE_BETTER`: the cooperative option appears to give the focal actor a material advantage.
- `INDEPENDENT_BETTER`: the independent option appears to give the focal actor a material advantage.
- `UNCLEAR`: the comparison cannot be judged from the text or depends on missing assumptions.

For each scenario version, also record:

- **Plausibility:** `ALL_PLAUSIBLE`, `ONE_OR_MORE_FLAWED`, or `UNREALISTIC_OR_UNINTERPRETABLE`.
- **Wording relation:** whether formulations 1 and 2 preserve the same action and desirability, shift meaning, shift desirability, or remain unclear.
- **Notes:** cite the phrase or assumption behind any non-equivalence or uncertainty.

For the A/B scenario comparison, record whether the versions are materially equivalent apart from the counterpart description, materially different, or unclear. A material difference includes changes to task, timing, cost, risk, success, objective, or what the partner receives.

Use the confidence and follow-up fields in the response template. Do not infer the intended classification from the project name, scenario wording, or other packets.

## Disagreement and unblinding sequence

1. Freeze each reviewer's independent response copy before sharing scores.
2. Compare disagreements by packet and rubric field while the original labels and model results remain hidden.
3. Resolve disagreements through a documented blind discussion or a third blind adjudicator. Preserve both original scores and the resolution rationale; do not overwrite the first-pass responses.
4. Only after decisions are frozen should the coordinator use the internal key to restore bank, template, partner, wording-source, and primary/secondary mappings.
5. Analyze how many primary packets and both partner versions pass each criterion. Report unclear, disputed, and excluded items explicitly; a packet-level decision does not imply both partner versions passed.

The 76-template priority set is a workload order. It does not justify treating unreviewed secondary/control items as validated, and reviewing both partner variants together does not collapse their judgments into one scenario-level score.

## Coordinator checklist

1. Give both reviewers the same `priority_76_blinded_packets.csv` and a separate copy of `priority_review_response_template_76.csv`. Do not give them the internal key or coordinator manifest.
2. Ask each reviewer to fill their own response file independently, using a stable reviewer code in `reviewer_id`. They should keep packet IDs unchanged.
3. Collect both completed files before sharing either reviewer's judgments. Compare matching packet IDs and rubric fields, then document blind resolutions while labels remain hidden.
4. Freeze the two first-pass files and the resolution record. Only then use the internal key to interpret partner and wording mappings and to identify the priority cohort.

No script is needed to begin review. If the source queue or packet-building code changes, rebuild all exports from the repository root with `python scripts/build_template_adjudication_packets.py`; this regenerates the derived packet files with the documented fixed seed.
