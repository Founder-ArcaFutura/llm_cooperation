# Review packet blinding incident

**Status:** historical packet mappings were publicly exposed on the research branch `codex/phase2-other-agent-preference`. The exposure is a methodological limitation, not evidence that completed human reviews occurred.

## Affected materials

The public branch contains an internal mapping for all 152 manuscript-readiness packet IDs, including the 76-packet priority subset; a 352-record factorial review mapping; and a six-entry construct-QA mapping covering three packets. Their associated blind packet sets are therefore not blind to anyone who accessed the public branch history. The response templates inspected for the 152, 76, and 352 packet cohorts contain no recorded completed human ratings. The construct-QA blind response template contains no records. No independent human review is established by those materials.

The keys and packet files are intentionally excluded from this canonical evidence PR. The source branch and its historical commits remain preserved; this integration does not delete or rewrite them. Their prior public exposure cannot be undone by omitting them from `main`.

## Remediation for a genuinely independent review

1. Freeze the scenario bank, paired wording, review questions, and analysis plan before recruiting reviewers.
2. Generate new packet identifiers and a fresh randomized order from the frozen bank. Do not reuse packet IDs, ordering, response templates, or reviewer access from the exposed sets.
3. Keep the new packet-to-item mapping key with an independent custodian outside GitHub. Publish only the blinded packet export and its hash; keep the key and any identity-bearing reviewer information access-controlled.
4. Recruit reviewers who have not seen the exposed keys or packet mappings. Record first-pass ratings with timestamps before reconciliation or unblinding.
5. Resolve disagreements while still blinded, freeze the adjudication dataset and its hashes, and only then release the key for analysis.

The existing packet templates may be retained as archival records but must not be represented as an independent blinded review. See [`AUTHOR_REVIEW_BRIEF.md`](../reports/manuscript_readiness/AUTHOR_REVIEW_BRIEF.md) for the outstanding human-review questions.
