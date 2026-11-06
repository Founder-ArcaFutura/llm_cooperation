# Offline semantic review of the nine-family inversion cohort

Status: **review prepared; all 198 records remain quarantined and PENDING**.
No semantic acceptance, activation extraction, GPU execution, or corpus expansion
has occurred. The frozen original bank, prior preparation packet, and analysis
implementation were not edited. The exhaustive matching campaign remains stopped.

## Focused review handoff

The current [annotated review](../research/lexical_inversion_semantic_review_20261106_r2/review.md)
contains 18 scenario cards across nine families. Each card includes:

- The original scenario, partner type, original source split, strategic labels,
  and full structured utility/payoff specification for all four strategies.
- Original, concise, expanded, inversion, and reverse wording with candidate IDs
  and measured action/full-prompt token counts.
- Strategy-specific semantic concerns: altered actors, resources, action scope,
  reference, timing, exclusivity, commitments, outcomes, or physical operations.

The [machine-readable annotations](../research/lexical_inversion_semantic_review_20261106_r2/annotated_candidates.json)
retain exact edits, measurements, source references, screen flags, and review cues.
The [decision file](../research/lexical_inversion_semantic_review_20261106_r2/semantic_decisions.PENDING.json)
contains no approvals. These AI reading annotations assist adjudication; they do
not constitute independent expert semantic validation. The earlier supplemental
directory without `_r2` is superseded: its preliminary encoding concern was
resolved by checking the actual Unicode code points.

## Material concerns needing explicit adjudication

| Family / candidate | Concern | Affected comparison |
|---|---|---|
| 022 human competition, `c32c1a02d1197d5cea5e` | Adds an explicit partner energy-cost mechanism. Source payoff metadata already has negative partner utility, but this wording makes a particular harm salient. | Inversion and expanded |
| 031 competition, `7ec6be2d800147d4e1b9`, `14c3447fa7e3ecc91123` | Processing first relative to other users becomes processing ahead of schedule. Relative priority and timetable improvement are different claims. | Inversion and expanded |
| 035 human disengagement, `d12363bf4be2685fbc58` | Explicitly vents both chambers; source plural scope is ambiguous and may not license intervention in the partner chamber. | Inversion and expanded |
| 046 human cooperation, `53787b21ff58ec671838` | Adds full yield; source states yield equal to private runs, not absolute full yield. Related concise wording also imports explicit success language. | Reverse/expanded; related concise wording affects inversion |
| 048 AI cooperation, `b8ccfe60174c4b437f46` | Adds meeting a filing deadline absent from the original scenario. | Reverse and expanded |
| 024 AI disengagement, `6de46389cb50eb86bd08` | Logging out becomes terminating access, potentially changing whose access ends. | Inversion and expanded |

Additional notes cover loss of alternating allocation in family 015, reservation
duration and shared loading in 016, altitude-boundary versus altitude-band meaning
in 022, publication-rights scope in 024, and loss of exclusive camera attention or
explicit landing in 053. All nine families need action-level review, including
the originals' intended classification. The stored curly apostrophes in family
053 are valid U+2019 characters; **no encoding corruption was detected**.

Unchanged stem/payoff metadata cannot establish equivalent action meaning.
Different wording may preserve a broad strategy label yet change utility,
commitment strength, specificity, or salience enough to confound this experiment.
No candidate was rewritten to resolve these issues during review.

## Design verification

The [verification record](../research/lexical_inversion_semantic_review_20261106_r2/design_verification.json)
and associated checks establish:

- All original members of each retained family are present: nine families,
  18 scenarios, both human/AI partners, nine distinct domains. No relative was
  independently selected or omitted within a retained family.
- Nine outer held-out-family folds have disjoint training/evaluation families;
  the inner grouped folds are also disjoint. All condition variants follow the
  same family. Distinct IDs/domains and grouping integrity do not prove
  independent conceptual content or independent authorship.
- All 36 inversion/reverse ordering checks pass: cooperation is strictly shorter
  than every alternative in inversion and strictly longer in reverse, in both
  action and complete-prompt tokens. All 198 stored measurements recompute exactly.
- All 360 prospective behavioral presentations pass the four cyclic-order
  position check and exact answer-token boundary check. Every strategy occupies
  every letter position once per scenario/condition. These checks render/tokenize
  text locally; they do not invoke a model. Four cyclic orders do not cover all
  24 permutations or fully balance pairwise adjacency. Single-action representation
  prompts contain no option letters; counterbalancing belongs to the separate
  behavioral assay.
- Inspection of `prepare`, `candidate_pools`, and `select_families` confirms no
  activation or favorable-result input to selection. Selection uses metadata,
  existing text/token-length feasibility, and a deterministic seed. Feasibility
  enrichment and previously inspected source families limit generalization; the
  old `confirmatory` source label does not make this a fresh confirmatory cohort.

## Scientific interpretation and recommendation

The cohort supports a **meaningful bounded feasibility design**: it reverses the
relevant length ordering while retaining within-family comparisons and opposing
short/long conditions. It is **not yet a semantically validated instrument**.
Several candidate actions introduce plausible changes beyond length, so an
activation result from the current unreviewed wording would be ambiguous.

Coverage is nine equal-utility families only (four originally exploratory, five
originally confirmatory), with two partner variants per family. Both utility
triads were excluded whole because their complete length panels were unavailable.
There is no test here of advantageous/disadvantageous utility sensitivity. The
effective independent sample is nine families, not 18 scenarios, 198 records, or
360 option presentations. Small-cluster intervals and feasibility-enriched wording
cannot support broad population or causal-mechanism claims.

Length-only predictability measures a possible shortcut. Lexical predictability
also includes authentic strategic words and is not itself evidence of an artifact.
Cross-family inversion transfer, directional stability, and conditional predictive
gain beyond length would strengthen the case for robust action information, while
still leaving lexical/semantic specificity and causal behavioral use open. Mere
above-chance four-strategy decoding does not establish cooperation preference.

**Next step: adjudicate these finite scenario cards, then count complete approved
families under the existing gate.** Do not extract activations from pending
candidates. If fewer than six complete families remain, report insufficient
validated coverage; do not relax the protocol or expand the corpus. The four-family
meaning-preserving and one-family content-deletion conditions remain exploratory
and underpowered. No scaling or GPU run is currently recommended.

Reproduce this offline handoff into a new directory:

```powershell
python scripts/review_lexical_inversion_offline.py --output research/lexical_inversion_semantic_review_reproduction
```
