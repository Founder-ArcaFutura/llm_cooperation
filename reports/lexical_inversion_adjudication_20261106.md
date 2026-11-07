# Nine-family semantic adjudication: decision report

**Current-scope outcome: infeasible for the planned inversion pilot.** One complete
family remains provisionally reviewable after minimal repair; zero families are
approved. The existing minimum is six complete families. No extraction is justified.
This is the result of a bounded adjudication pass, not proof that no possible
equivalent wording could ever work.

| Complete-family disposition | Count | Families |
|---|---:|---|
| Structurally passing and semantically defensible without further explicit judgments, pending human approval | 0 | — |
| Structurally passing after proposed minimal repairs; explicit judgments remain | 1 | 031 |
| Reject at the current scope | 8 | 015, 016, 022, 024, 035, 046, 048, 053 |

“Provisional survivor” means a complete human/AI family across original, concise,
expanded, inversion and reverse conditions, with all four strategies retained.
It does not mean accepted wording or experimental eligibility. Repair proposals
exist only in a quarantined sidecar; they have not replaced bank entries.

## Shared transformation decisions

| Recurring transformation | Grouped decision |
|---|---|
| Shortened actor/resource names; ordinary synonyms and clause reordering | Potentially defensible when the unchanged stem uniquely resolves the same entity, method and action. A shared class label alone is insufficient. |
| First relative to others → ahead of schedule | Reject. Restore relative priority explicitly; do not infer timetable improvement. |
| Equal yield → full yield; new success guarantees | Reject. Equality to private runs does not entail absolute yield or guaranteed success. |
| New deadline; full-day → full days; new resumption commitment | Reject changes to temporal constraints unless exact equivalence is demonstrated. |
| Logging out → terminating access; omitted partner-cohort rights; immediate → priority access | Reject the changed access/right/commitment scope. |
| Lost alternation/exclusivity/landing; extra chambers; equipment substitution | Reject changed operations or scope unless the same physical/strategic action is established. |
| Altitude boundary → altitude-band extent | Reject the changed allocation reference. |

The [record ledger](../research/lexical_inversion_adjudication_20261106_r2/record_ledger.json)
maps all 198 records to shared groups, explicit transformation rejections,
quarantined repair proposals, or withholding because their family is incomplete.
Unchanged originals receive no semantic approval through this process. Family-level
rejection withholds even individually plausible options; it does not assert that
every option in the family is intrinsically invalid.

## One family still worth explicit judgment

**031: dual-channel osmolality profiling.** Three single-defect proposals retain
strict length ordering and intact family membership:

| Proposed repair | Action / full-prompt tokens before → after |
|---|---|
| Human competitive expanded: “ahead of schedule” → “before other users” | 20 / 86 → 20 / 86 |
| AI competitive expanded: same relative-priority restoration | 20 / 88 → 20 / 88 |
| Human cooperative expanded: remove “concurrent,” retaining “osmolality profiling” | 22 / 87 → 21 / 86 |

Only **two grouped semantic judgments** remain, covering both partner variants:

1. Does “take/claim all cartridges” preserve the source's preemptive resource
   control, rather than merely acquiring sufficient cartridges?
2. Does collaboration through the same dual-channel sensor preserve the original
   partner role—metabolic monitoring—with the focal actor doing osmolality profiling?

The exact source/rejected/proposed wording, candidate IDs, and recomputed token
measurements are in the [seven-proposal repair ledger](../research/lexical_inversion_adjudication_20261106_r2/bounded_repair_proposals.json).
Three proposals concern 031; four concern the rejected 015 family. No repeated
generation, synonym search, or token-target retry was performed.

## Why the other complete families stop here

| Family | Reason to reject at current scope |
|---|---|
| 015 | Restoring explicit alternating delivery bays makes AI cooperation 15 action / 71 prompt tokens, equal to two expanded alternatives. Strict inversion fails. No further shortening attempted. |
| 016 | Several distinct changes: buckets/slots, joint loading/simultaneous preparation, immediate/priority access, and pluralized full-day duration. |
| 022 | Altitude partition reference, occupation versus use, explicit energy-harm mechanism and weather premises change together. Negative partner utility does not certify a particular new mechanism. |
| 024 | Partner-cohort rights scope, agent role/data flow and termination of access all need restoration. |
| 035 | Venting versus releasing pressure, both-chamber scope, supply identity and relative priority are unresolved. |
| 046 | Full yield, added success/throughput claims and booking-versus-allocation scope interact. Removing “full yield” alone is insufficient. |
| 048 | Added deadline, filing-versus-initiation, private-index method, defensive claims and later-review commitments interact. Removing the deadline alone is insufficient. |
| 053 | Exclusive attention, recording equipment/method and actual landing are weakened or altered. Apostrophes are valid Unicode and are not a rejection reason. |

These seven multi-defect families are rejected in their current form rather than
sent through another repair campaign. Their possible repairability has not been
exhaustively tested. No failed family has been replaced or reselected.

## Integrity and scientific scope

All nine original selections, both partner conditions, original payoff metadata,
and source-family memberships are retained in the audit. The structural pass
recomputes every action/full-prompt count, all strategies' concise/expanded
ordering, inversion/reverse ordering, and capture boundaries after hypothetical
repairs. A failed partner or strategy fails the whole family.

The original bank, earlier packets and all PENDING approval records remain
unchanged. No new scenarios, extraction plans, approvals, model calls or GPU jobs
were created. Selection was not revised in response to anticipated probe outcomes.
The [family ledger](../research/lexical_inversion_adjudication_20261106_r2/family_decisions.json)
retains every rejection and structural failure; the accompanying manifest hashes
the source, script and derived files.

Length predictability, lexical predictability and strategic information remain
distinct hypotheses. Even perfect token ordering cannot rescue changed semantics;
lexical prediction can use authentic strategy words; successful decoding would not
by itself show behavioral preference or a causal cooperation mechanism. The cohort
still covers equal-utility cases only, uses previously inspected families, and has
no approved activation outcomes. Underpowered natural-paraphrase and content-word
controls remain exploratory.

**Recommendation: stop this nine-family pilot at the current scope.** There is no
need for the user to review all 198 records: even approving the two judgments for
031 would leave only one family, below the declared minimum. Preserve this negative
feasibility finding. Any redesigned or expanded experiment needs subsequent
authorization; no such work was initiated.

Reproduce the bounded adjudication into a new directory:

```powershell
python scripts/adjudicate_inversion_families_offline.py --output research/inversion_adjudication_reproduction
```
