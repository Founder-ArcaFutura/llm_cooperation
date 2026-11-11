# Cooperative-action paraphrases — manual source-aligned repair

## Scope

This package replaces Jules' `3476b7d` paraphrase **text** for all 304 records, preserving source identities, original cooperative actions, human/AI counterpart designations, source-bank metadata, and the existing experimental records. It leaves the original scenario banks and the other three options untouched.

| Bank | Scenario records | Distinct situation templates | Specialist-review flags |
|---|---:|---:|---:|
| Phase 0 | 120 | 60 | 10 |
| Phase 0B | 124 | 62 | 14 |
| Phase 1 | 60 | 30 | 8 |
| **Total** | **304** | **152** | **32** |

Each situation was written from its corresponding **original COOPERATE action**, not from Jules' paraphrase. For paired human/AI scenarios the substantive paraphrase is identical aside from the original counterpart designation. The deliberately inappropriate, risky, and useless cooperative actions in Phase 0 have NOT been changed into sensible actions; for example, the confetti-to-leather-binding option remains confetti-to-leather-binding.

## What is and isn't validated

- **Completed structural checks:** 304 entries; original scenario IDs and order retained; original action strings retained; role substitution consistent across paired versions; all new paraphrases nonempty, nonidentical to their original, and not contaminated with another task selected from Jules' previous dataset.
- **Completed exact stem-overlap check for Phase 1:** original mean content-word overlap `0.7839`, revised mean `0.4612`; all 60 Phase 1 paraphrases reduce measured overlap with their corresponding stem. The calculation uses the stopword-filtered overlap definition from Jules' original audit.
- **Phase 0 and 0B stem-overlap checks:** bundled audit script calculates these against the authoritative source banks on your machine. They were not available as mounted source files in the isolated authoring runtime, so no numbers are invented here.
- **Semantic validation:** these are manually constructed, action-aligned drafts, **not independently validated**. All 304 carry `semantic_validation_status: pending_independent_review`. The 32 specialist-review flags identify especially technical or unusual cases; unflagged items still require review prior to presenting the lexical assay as a controlled replication. No script sets all semantic fields to `PRESERVED` by default.
- **Source SHA-256 metadata:** carried forward from the corresponding Jules records. The audit script recomputes hashes from the authoritative local source banks and warns on mismatch (e.g., line endings or source revisions), while requiring exact original-action correspondence.

## Install into repository

Your previous paraphrase data are committed in `3476b7d` and can be recovered via Git. If another agent is editing those three files, save its work before installing this package. This archive uses the same three data filenames as Jules' original and **will overwrite those copies** if extracted with `-Force`.

From PowerShell in `G:\llm_cooperation` after ensuring your working tree is safe:

```powershell
Expand-Archive -LiteralPath 'PATH_TO_ZIP\cooperate_paraphrases_manual_repair.zip' -DestinationPath 'G:\llm_cooperation' -Force
python .\scripts\audit_source_aligned_paraphrases.py --repo-root .
```

The audit writes:

- `research/cooperative_paraphrase_repair/lexical_audit_v2.csv`
- `research/cooperative_paraphrase_repair/lexical_audit_v2_summary.json`

The bundled `research/cooperative_paraphrase_repair/semantic_review_queue.csv` has every original/paraphrase pair for independent evaluation and includes flagged concerns. Accept a record only after action, counterpart, mechanism, payoff, and outcome equivalence have been checked.

## Experimental comparison

In the subsequent paired lexical assay, hold the stem, other three actions, answer permutation, model revision, and decoding/scoring method fixed. Swap only `COOPERATE` wording. Report scenario/template-clustered results for both generated choices and positional logit preferences, and track differences in word count and lexical-overlap separately. Note that even a successful lexical paraphrase test cannot identify the neural mechanism behind the preference.
