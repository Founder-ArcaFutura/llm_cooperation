# Lexical-confound pilot: preparation and recommendation

**Status: implemented and tested offline; no new activation or behavioral inference.
All candidate wording remains quarantined for semantic review.** The source bank
and historical runs were not changed. No corpus repair campaign was continued.

Use the final packet at
[`research/lexical_confound_pilot_20261106_r2`](../research/lexical_confound_pilot_20261106_r2/).
Earlier `lexical_confound_pilot_v1` and `lexical_confound_pilot_20261106` directories
are superseded preparation snapshots, retained without rewriting them. They are
not executable reviewed instruments.

## Findings from the automatic audit

The pinned Qwen tokenizer reproduces the original disparity: mean action lengths
are 16.895 tokens for cooperation, 13.145 for independent action, 14.081 for
competition/exploitation, and 14.258 for disengagement. There are **zero** original
quartets with cooperation shorter than all alternatives, and zero quartets with
both action and full-prompt spans at most one token. Seven quartets have spans at
most two; 63 have spans at most four. These are structural counts, not semantic
validation.

Six-fold family-held-out, equal-family-reported accuracy is **56.1% for length
features** and **97.0% for word/bigram features**, against 25% four-class chance.
The lexical baseline includes meaningful strategy vocabulary: its performance
does not establish that the signal is spurious. Exact counts, histogram overlaps,
family bootstrap intervals and all rows are in the [audit](../research/lexical_confound_pilot_20261106_r2/audit.md).

Selection used metadata and text feasibility, never activation outcomes. The
packet retains 12 families, 32 scenarios, 12 domains, both partner types, and two
complete utility triads. This is a feasibility-enriched selection, not a
representative probability sample.

| Comparison | Complete provisional families | Current interpretation |
|---|---:|---|
| Original / concise / expanded / inversion / reverse | 9 | Reviewable length-inversion pilot; 18 scenarios |
| Original / low ablation / dose-matched random deletion | 12 | Targeted stress test, not balanced all-strategy corruption |
| Natural meaning-preserving perturbation | 4 | Below the six-family analysis minimum |
| Matched strategic-content deletion | 1 | Below the minimum; no general content-sensitivity conclusion |

The length panel excludes incomplete families as units, including both utility
triads. Its remaining scenarios are equal-utility cases; it cannot support claims
about robustness across utility conditions. Cooperation is strictly shorter than
each alternative in both action and full-prompt tokens in inversion, with the
opposite ordering in reverse. Every retained strategy has distinct concise and
expanded candidates. This describes token structure, **not approved meaning**.

The article-deletion opportunity is sharply asymmetric: cooperation can be
perturbed in all 32 scenarios, versus 2 independent, 2 competitive and 6 disengage
actions. Unavailable actions remain explicitly unchanged. Accordingly, report
cooperation recall and changed-only performance alongside whole-quartet accuracy;
compare the same changed actions to exact token-dose-matched random deletion.
Training on selectively corrupted labels can create a new shortcut. The protocol
does not treat that training result as evidence of semantic specificity.

## What to review and run

- [Length review](../research/lexical_confound_pilot_20261106_r2/review_length.md):
  198 distinct records, including 72 unchanged originals and 126 proposed natural
  formulations. Review 18 scenario cards; token counting is already done.
- [Targeted ablation review](../research/lexical_confound_pilot_20261106_r2/review_ablation.md):
  original text, exact deletions, counts, flags and candidate IDs.
- [Protocol and executable commands](../docs/lexical_confound_pilot.md): hypotheses,
  paired family-held-out analysis, predeclared primary layers/criteria, approval
  schema, extraction, and separate behavioral competence gate.
- [Full candidate manifest](../research/lexical_confound_pilot_20261106_r2/candidates.json)
  and [infeasibility records](../research/lexical_confound_pilot_20261106_r2/infeasible.json).

Human review must establish naturalness and preservation of actors, resources,
constraints, payoffs and strategy. Stress-test approval acknowledges bounded
corruption; it does not assert equivalence. The freeze command rejects pending,
stale or incomplete reviews and incomplete related families. No actual candidate
has been automatically approved.

The analysis implementation covers four-class accuracy/recall, angular and
cooperation-direction stability, cross-condition transfer, length and lexical
baselines, held-out conditional predictive gain beyond length, paired changes,
and family-aware uncertainty. Behavioral collection is separately gated on raw,
reviewed objective and strategic-comprehension evidence for the same model and
prompt format. No qualifying behavioral receipt is assumed.

## Validation and recommendation

Targeted tests plus the existing contrastive/four-strategy tests: **24 passed**.
Checks exercise protected-word deletion gates, exact dose matching, real tokenizer
boundaries, all four option positions, review/hash tampering, complete-family
exclusion, authorization guards, nested vocabulary isolation, synthetic strategic
signal, and failure of a synthetic pure-length shortcut under inversion.
Ruff checks pass. Two independent preparations produce identical manifests and
artifact hashes. The original bank SHA-256 remains
`a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b`.
The raw cached tokenizer also agrees with actual AutoTokenizer input IDs on all
496 source prompts and all 453 candidate prompts; every candidate capture offset
passes. This verifies tokenization locally, not actual model execution.

**Proceed to semantic review of the nine-family length pilot and the explicitly
targeted ablation panel. Do not scale the corpus yet.** Natural-paraphrase and
content-deletion coverage are insufficient in this bounded existing-candidate
pass; this is not a proof of general infeasibility. No conclusion about survival
of the cooperation representation is available until reviewed instruments are
frozen and an explicitly authorized activation run is analyzed. GPU execution,
semantic acceptance, behavioral competence, and scientific survival remain
unverified.
