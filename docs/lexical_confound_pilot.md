# Lexical-confound feasibility pilot v1

Date: 2026-11-06. Prospective for new activations; previous exploratory results have
been inspected. Status: preparation and feasibility only, not a validated corpus.
The Phase 0B bank and all historical runs remain byte-for-byte unchanged. This
replaces exhaustive matching with a bounded experiment; no repair campaign or
paid inference is part of preparation.

## Question and hypotheses

Does strategy information generalize when length and ordinary wording change?
The unit of independence is `triad_id or template_id`, never an action, partner
variant, option permutation, or paraphrase. All relatives stay together.

| Condition | Construction | Hypothesis / interpretation |
|---|---|---|
| Original | Exact source action and stem | Baseline decodability; not semantic ground truth |
| Concise / expanded | Existing naturally worded candidates, each strategy at both lengths | Transfer between length ranges on unseen families |
| Inversion | Concise cooperation, expanded alternatives; cooperation strictly shorter than **each** alternative in action and full-prompt tokens | A simple longer-is-cooperation shortcut should fail |
| Reverse | Expanded cooperation, concise alternatives; cooperation strictly longer than each | Opposing association; compare with inversion on identical families |
| Meaning-preserving candidate | Narrow stylistic substitution or same-token-count existing candidate, pending review | Stability under approved natural paraphrase; no universal optional-article rule |
| Low ablation | Delete one surface article, then re-tokenize | Robustness to bounded syntactic corruption; **not** equivalence |
| Matched random deletion | Seeded deletion of one eligible nonprotected whole word, distinct from target span | General corruption control, exact same action AND full-prompt token reduction |
| Content deletion | One prelisted strategic operation word, when exact dose matching is possible | Meaning-changing positive sensitivity control; original labels denote source actions, not corrected post-deletion semantics |

Deletion never introduces `[MASK]`, unknown tokens, or ID-level fragments. Qwen is
a decoder-only causal LM. Edits operate on character spans of complete surface
words, normalize whitespace, and re-tokenize the entire rendered input. Articles
can affect reference and scope; even article deletion is explicitly a stress test.
Random deletion is restricted, not uniform over all words. Protected connectives,
negation, quantities, commitments, and allocation qualifiers are excluded by a
conservative stoplist; a human must check remaining context-dependent roles.
Content deletion is a distinct deliberate meaning alteration, restricted to an
enumerated operation-word list. Failure to find an exact matched control is
reported; controls are never silently substituted. One seeded draw per action
keeps review bounded; inference applies only to this draw and these eligible spans.

**Observed preparation limitation (no activation outcomes):** original articles
are concentrated in cooperation actions. Balanced all-four-strategy deletion
quartets are unavailable in the first bounded pass. Partial panels retain exact
original text for unavailable actions and list `changed_strategies`. These are
targeted stress tests, not balanced lexical replications. The analyzer reports
cooperation recall, changed-only accuracy, and matched random-deletion contrasts;
whole-quartet accuracy alone can be inflated by unchanged actions. Training on
these selectively corrupted panels can create a new label cue; cross-perturbation
fits are descriptive, and only original-trained transfer is used to assess
robustness. Small natural-perturbation/content subsets may fail the minimum-family
gate. Do not expand eligibility to protected words merely to fill cells.

## Model, selection, and audit

Initial target: `Qwen/Qwen2.5-1.5B`, revision
`8faed761d45a263340a0528343f099c05c9a4323`, the original representation target.
Preparation loads its cached actual `tokenizer.json` with the Rust tokenizer,
special tokens disabled. Inference must check token IDs against the actual
AutoTokenizer. A different model/tokenizer requires a new versioned preparation.

Audit all 124 original scenarios: per-action and full-prompt token counts,
word/character counts, per-strategy length histograms, pairwise histogram overlap
(sum of minimum bin probabilities), and naturally inverted original quartets.
Fixed-C length-only quadratic logistic and L2-normalized word/bigram TF-IDF
baselines use six-fold family-held-out predictions. These are descriptive
diagnostics, not proof that all surface information has been controlled.

Select 12 families: six from each original source split, one complete utility
triad in each split when present, then maximize domain diversity; prioritize
natural original inversion, existing candidate inversion feasibility, and
availability of two distinct lengths, with seed `20261106` breaking ties.
Keep every human/AI and utility variant. Use source metadata and text only;
never consult activations, probe accuracy, or behavioral results for selection.
Audit all family scores and report exclusions. This is a diverse feasibility
sample enriched for usable wording, not a probability sample or population claim.
The old source split is not a new confirmatory split: all material has previously
been inspected. New analysis uses outer held-out families and is exploratory.

Prefer source wording and saved production candidate pools. No model generation,
synonym cascade, filler, or repeated repair loops. Existing candidates are
unadjudicated. The deterministic generator assembles conditions, applies bounded
surface edits, counts tokens, and quarantines outputs; it does not certify them.
Unavailable conditions remain unavailable. Broad cross-length overlap is audited
again on approved prompts; a short/long label alone does not establish balance.

## Review and immutable artifacts

Every proposed action, including originals whose scientific review is pending,
needs a recorded decision. Review cards show unchanged stem/payoffs, original,
candidate, exact edits, token differences, provenance, and mechanical flags.
Review natural variants for actors, resources, constraints, payoffs, timing,
strategy, reference, and naturalness. Review stress variants for exact bounded
deletion and absence of unintended protected changes, acknowledging corruption.
Protected-word-signature changes are review warnings, not a semantic verdict.
Malformed actions, special tokens/strategy-label injection, and known corrupted
phrases are hard exclusions. A missing warning is not acceptance.

Copy `review_decisions.template.json` outside the immutable packet. Record reviewer,
candidate hash, checks, notes, and `APPROVE` or `REJECT`; no bulk auto-approval.
Freeze accepts only complete paired quartets and complete families for requested
conditions. A missing relative invalidates that family for that comparison.
Require at least six families for runnable analysis; fewer yields infeasibility.
The primary inversion comparison requires original, concise, expanded, inversion,
and reverse together. Primary low-ablation comparison requires original, low
ablation, and matched random deletion together. Meaning-preserving and content
controls are separate panels if their coverage is smaller. No post-outcome changes
to conditions, family selection, thresholds, layers, or review decisions.

Hash source snapshot, input pools, tokenizer files, protocol, code, proposals,
decisions, and final prompt inventories. New output directories only. Freeze and
run artifacts retain exact UTF-8 bytes. Human review is a necessary validation
step; a freeze record is not permission to spend on inference.

## Extraction and leakage controls

Reuse the established single-action formatter:
`{stem}\n\nAction: {action}\nDecision:`. Capture residual output at the final
marker token after each decoder block, exactly as the original contrastive probe.
Strategy labels, condition names, family IDs and response letters are metadata
only. Verify marker suffix token IDs, full prompt token counts/hashes, architecture,
and pinned revision. No padding, no truncation, FP32, eval mode, no sampling.
The period/newline before `Decision:` can form a merged token in Qwen. Verify the
stable `Decision:` suffix and its character offsets in the full input; do not
require the newline to tokenize as it does in isolation. Behavior scores the
single-token continuations ` A`, ` B`, ` C`, ` D` after `Answer:`; no-space `:A`
can merge across the prompt boundary and is rejected.

Behavior uses separate four-option prompts and four cyclic Latin-square orders:
each strategy occupies A/B/C/D once. This balances position but not all adjacency
effects (24 permutations would require a new protocol). Validate each candidate
letter as a single continuation token at the exact prompt boundary. Do not infer
preference from single-action activation probes. Behavioral conclusions require a
separate, model/revision/prompt-format-bound competence receipt demonstrating
>=95% generated answer validity, >=80% objective calibration accuracy, and <=0.15
position spread on an independent calibration instrument with at least 24 items
and all four positions. Additionally require at least 12 independent strategic
comprehension items (objective questions about actors, payoffs, or action meaning)
at all four positions, with the same validity, accuracy, and spread thresholds.
These checks establish necessary competence, not general strategic rationality.
Receipt includes raw evidence hash and reviewer; it is
not supplied or assumed by this preparation. Report forced letter probabilities
separately from generated answers; invalid answers remain in denominators.

## Analyses declared before new activation outcomes

Outer leave-one-family-out evaluation, all conditions and relatives of the test
family excluded from training. Inner GroupKFold selects C from [.01,.1,1,10]
using discovery families only. Feature scaling/vocabulary and quadratic length
expansion fit inside each inner fold. Equal-family weights prevent large triads
dominating either fitting or summaries. Train/test every requested condition pair.

1. Four-class balanced accuracy, per-class recall, macro-F1 and out-of-fold
   predictions; source-label retention only for meaning-changing stress tests.
2. Scenario-centered residuals as in the existing probe. Cooperation direction
   is cooperation minus the mean of the other three. Equal-family means for
   training. Cosine and angle to the test family's direction, and paired original
   vs intervention direction stability. Zero norms produce null, never zero-degree
   certainty. Primary layers are the prespecified historical candidates 18 and
   22 (zero-based decoder-block indices); other layers descriptive only.
3. Cross-length, cross-perturbation, and cross-family transfer matrix.
4. Length-only baseline: action/prompt tokens, words, characters and degree-two
   terms. Lexical-only baseline: train-fitted L2-normalized TF-IDF unigrams/bigrams.
5. Conditional information: difference in held-out cross-entropy (bits/action)
   between length-only and length-plus-activation logistic predictors, using the
   same families and nested fitting. This is a finite-model predictive estimate,
   not universal mutual information or a guarantee that nonlinear length effects
   are absent. Report conditional-on-lexical improvement as a secondary diagnostic
   if added in a future version. Do not equate residualization with confound removal.
6. Paired accuracy changes relative to original, same held-out families; low
   ablation minus matched random-deletion effects. Family bootstrap, 2,000 draws,
   seed fixed; resample a family's entire paired outcomes. Intervals condition on
   trained OOF models, not a bootstrap refit of the whole learning process.
7. Optional behavioral selection and paired changes, family-aware intervals,
   generated validity and position spread reported separately for each condition.

The conditional-predictive approach follows the motivation of
[Hewitt et al. (2021)](https://aclanthology.org/2021.emnlp-main.122/).
Decodability does not establish behavioral use, as discussed by
[Elazar et al. (2021)](https://aclanthology.org/2021.tacl-1.10/).

## Decision criteria and stopping

Feasibility gate: >=6 complete reviewed families for a comparison (target 12),
both partner types, >=4 domains, intact related items, no structural failures,
strict inversion/reverse inequalities where requested, exact deletion-dose match.
Insufficient coverage stops that comparison; this does not prove general
infeasibility or absence of strategic representation.

For the primary inversion comparison, preliminary survival requires at both
layers 18 and 22, training on original descriptions and testing inversion:
cross-condition family-bootstrap lower accuracy bound >.25,
lower cooperation-direction alignment bound >0, lower conditional length-adjusted
predictive-gain bound >0 bits, and lower paired accuracy-change bound >-.10.
Use 99.375% pointwise intervals for these eight prespecified layer/endpoint checks
(Bonferroni .05/8); this remains an exploratory feasibility signal because the
pilot uses previously inspected source families and small cluster counts.
Natural perturbation applies the same descriptive endpoints, reported separately.
Stress-test stability is not required for proof of semantics: failure can reflect
corruption, grammatical disruption, or changed meaning. Low-ablation results must
be interpreted against dose-matched random and feasible content controls. A
non-significant difference is inconclusive, not equivalence. Report the .10
accuracy-loss margin as a pragmatic pilot criterion, not a biological constant.

Scale only after semantic/coverage gates and interpretable representation results.
If length baselines explain performance, inversion fails, or lexical transfer
collapses, retain that result and revise the scientific claim rather than repair
items to rescue it. Even positive survival does not establish a causal cooperation
circuit. Independent new families/wording and behavioral causal interventions
would be a subsequent study. No scaling is currently justified by new activation
evidence, because this packet contains none.

## Reproduction and execution

Run from the repository root. All preparation and analysis commands are CPU-only;
preparation requires the pinned tokenizer already cached, and makes no downloads.
The packet includes all source counts, selected families, infeasibility records,
candidate provenance, a review document, and review-decision template.

```powershell
python -m llm_cooperation.mechanistic.lexical_pilot prepare --output research/lexical_confound_pilot_reproduction
```

Review `review.md` and `paired_coverage.json`. Copy the decisions template outside
the packet and edit it; do not alter the packet. `PENDING` is not approval. Each
approved natural candidate needs all meaning/strategy/naturalness checks. Each
stress candidate needs scope review. Flagged candidates need explicit notes.
For a smaller review queue, use `review_length.md` and
`review_length_decisions.template.json`, or their `ablation` counterparts. They
contain only candidates from complete families for that comparison, with original
text deduplicated across conditions. The full manifest retains excluded candidates
and all infeasibility reasons for audit.

```powershell
python -m llm_cooperation.mechanistic.lexical_pilot_run freeze --packet research/lexical_confound_pilot_20261106_r2 --decisions research/lexical_pilot_decisions.json --comparison length --output research/lexical_length_reviewed_v1
# Separate ablation, meaning, or content comparisons use the same command with
# --comparison ablation / meaning / content and a new output directory.
```

Freeze refuses insufficient complete-family coverage; it does not silently relax
the design. It deduplicates identical single-action prompts across conditions.
Review remains separate from permission to run. The following is a **future**
execution command and must not be run without explicit authorization:

```powershell
python -m llm_cooperation.mechanistic.lexical_pilot_run run --plan research/lexical_length_reviewed_v1 --output mechanistic_artifacts/lexical_length_v1 --authorize-inference --authorize-paid-run
```

This uses the existing FP32 Qwen decoder-block extraction implementation and may
download weights. No Modal deployment is introduced. A cloud operator can run the
same command in a provisioned environment; environment/GPU provisioning is not
performed by this package. Omitting either authorization flag fails before model
initialization. The runner checks token IDs against AutoTokenizer before inference.

```powershell
python -m llm_cooperation.mechanistic.lexical_pilot_analysis --plan research/lexical_length_reviewed_v1 --run mechanistic_artifacts/lexical_length_v1 --output reports/lexical_length_v1
```

Analysis verifies exact evidence hashes and rejects mock runs. It writes full
out-of-family predictions, per-family paired estimates, cross-condition matrices,
angles, baselines, conditional predictive gains, and decision criteria. No new
activation evidence currently exists for this pilot.

Optional behavior (also requires separate explicit execution authorization):

```powershell
python -m llm_cooperation.mechanistic.lexical_pilot_behavior format-hash
python -m llm_cooperation.mechanistic.lexical_pilot_behavior run --plan research/lexical_length_reviewed_v1 --competence-receipt research/competence_receipt.json --output mechanistic_artifacts/lexical_behavior_v1 --authorize-inference --authorize-paid-run
python -m llm_cooperation.mechanistic.lexical_pilot_behavior analyze --plan research/lexical_length_reviewed_v1 --run mechanistic_artifacts/lexical_behavior_v1 --output reports/lexical_behavior_v1
```

Competence receipt schema: `target_model`, `target_revision`,
`prompt_format_sha256` (from `format-hash`), `reviewer`, `approved: true`,
`evidence_file` (relative to receipt), `evidence_sha256`. Evidence contains model,
revision, `mock: false`, and `samples`; each sample has `item_id`, `task`
(`objective` or `strategic`), `rotation` (0–3), `correct_letter`, and
`generated_text`. Reviewer must verify that the evidence came from this exact
prompt format/model and independently reviewed questions. Every item must cover
all four correct-answer positions. The gate recomputes metrics from raw text;
aggregate claimed scores are insufficient. No such receipt is fabricated here.
The existing 24-item factual calibration bank can supply objective questions but
does not by itself demonstrate strategic comprehension. Behavioral collection
remains blocked until this independent evidence exists.

