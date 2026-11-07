# Acceptance report — incomplete, not approved for inference

The current corpora are not scientifically accepted or frozen. The existing
generator uses substitutions and token padding that can change meaning and
produce malformed text. It is disabled pending a replacement workflow. Bank C
was generated from the same originals by parallel substitution rules; it is
not an independent paraphrase corpus. The keyword classifier is triage, not
independent semantic adjudication.

The original PR audit reports maximum action token spans of 9, 13 and 10 for
banks A, B and C, and 288 identical corresponding actions between B and C.
The original loading code did not pin the tokenizer revision. A subsequent
run with the pinned Qwen revision initially confirmed 235 scenario variants exceeded the
one-token span limit across the three banks. After a provisional manual rewrite of
the two Bank A canal scenarios, 233 remain: 75 in A, 80 in B and 78 in C.
The new acceptance test pins the stated Qwen revision and
requires every scenario in every bank to have a span no greater than one.
It also rejects exact corresponding action duplicates across banks. Zero exact
matches alone would not establish lexical or syntactic diversity or independent
construction; those require further analysis and review.

All 372 scenario variants are queued as unadjudicated, including items that
passed the heuristic. Each queue entry retains original and revised options
and any prior heuristic warnings. Human reviewers must assess strategic meaning,
payoffs, partner identity, naturalness and equivalence against the source; no
approval is inferred from a lack of warnings. The prior queue contained 312
flagged variants, not 312 independently adjudicated failures.

The source scenarios remain unchanged. Eight Bank A action records in the human
and AI canal scenario pair have been rewritten; all remain unadjudicated.
Accordingly the remaining corpus repair, diversity evaluation, regenerated
complete regenerated audit, and independent review remain outstanding. The
manifest and hashes describe the current provisional files only. The strict
acceptance tests are expected to fail until the corpus is actually repaired.
