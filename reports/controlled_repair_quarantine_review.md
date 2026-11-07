# Jules pilot and production-pool quarantine review

This review uses the original root archive `jules_session_9218804022744716065.zip` (SHA-256 `7afb056bfaa192441065225cc4b9a47fe95efb8bfa1e401a578474b81ee31424`). The diagnostic JSON records hashes of all four archive files, the input source, overlay, and cached tokenizer files. Run `python scripts/diagnose_controlled_repair_quarantine.py` with that exact archive in the repository root and the pinned tokenizer revision cached. There is no inference and no write to source, production01, or the PR #11 overlay.

## Reconciliation of the 13 reported candidates

Re-tokenization of all 13 serialized quartets confirms both token spans are at most one. Recomputed comparisons against the fixed accepted bank and the other serialized candidate banks in the same scenario find no exact or >0.85 word-Jaccard collisions. These are mechanical checks, not evidence of meaning preservation. The following table records known defects found by the *limited* screens; every candidate remains `UNADJUDICATED` and none is accepted.

| Record | Limited grammar screen | Confirmed protected-fact defect | Disposition |
|---|---|---|---|
| 008_A | Lowercase opening in DISENGAGE | None detected | Fix/review; quarantined |
| 010_A | Lowercase opening in COMPETE_EXPLOIT | None detected | Fix/review; quarantined |
| 011_A | Lowercase opening in COMPETE_EXPLOIT | None detected | Fix/review; quarantined |
| 012_A | No listed defect | None detected | Human review required |
| 012_B | No listed defect | None detected | Human review required |
| 012_C | No listed defect | None detected | Human review required |
| 013_A | Lowercase opening in COOPERATE | None detected | Fix/review; quarantined |
| 013_B | “an early docking access” | None detected | Fix/review; quarantined |
| 013_C | No listed defect | None detected | Human review required |
| 004_A | Lowercase opening in COOPERATE | None detected | Fix/review; quarantined |
| 009_A | “claim lockers” | Storage resource corrupted | Reject that wording; quarantined |
| 018_B | Lowercase opening in COOPERATE | None detected | Fix/review; quarantined |
| 020_A | Lowercase opening in COOPERATE | None detected | Fix/review; quarantined |

Thus all 13 satisfy the token gates; four satisfy the limited grammar screen and have no *detected* explicit protected-fact violation. Nine fail the grammar screen, including 009_A, which also has a confirmed protected-resource defect. A missing flag is not proof that actors, resources, payoffs, timing, physical feasibility, strategy, or grammar are correct. For example, source and candidate text in the report show that 018_B's inherited competitive wording describes overloading neighboring grid segments, whereas the frozen option describes exporting surplus reactive power to induce adjustments; the significance needs review. The reported two triads are mechanically token-valid and collision-free in their serialized form, but the scenario 013 triad includes two grammar failures. Scenario 012's triad remains unadjudicated.

## Quarantined pool funnel

The full scan enumerates each unresolved record's saved production candidate pool plus its current record action, without generating fresh substitutions. Across 293 unresolved records it examines 2,121 per-strategy action entries and 2,889 quartet combinations. The limited grammar and explicit-fact screens flagged no action in these raw pools, and every one of the 2,889 combinations failed an action or full-prompt token span. Hence no raw-pool quartet reached cross-bank compatibility or joint selection. The report provides per-action checks and per-record counts, including overlapping diagnostics; it does not treat an unflagged item as fact-preserving.

Separately, the diagnostic combines each scenario's actual serialized Jules actions with its production pools and searches the resulting grammar-screened, token-valid quartets in quarantine. Scenario 012 has 8, 4, and 4 choices for A, B, and C and joint selection finds a collision-free triad; sequential greedy also finds one for this case. A reproducible synthetic regression demonstrates the alternative case where greedy blocks B and backtracking selects both A and B. Search in the augmented pilot is limited to the first 10 eligible quartets per bank; the result records per-bank truncation. The raw full-pool search is capped at 30 per bank after fixed-bank collision checks, with truncation recorded; here all pools were empty before the cap. The diagnostic's selected options are not accepted records or scientific results.

## Existing PR #11 test failures on this Windows checkout

A targeted rerun with `PYTHONUTF8=1` made `test_reconstructed_dataset_matches_candidate_files` pass, confirming that its default-encoding reads caused the previous mismatch. The manifest provenance test still failed because `core.autocrlf=true` gives the checkout overlay SHA-256 `db4f2b306e6b33538831de0e0e8b75209d0ec271e6d8c78acaddb5ec483cfeb0`, while the committed LF blob hashes to `ba64a11c07be02c63be94d95ce2c2072bf5bec1c5693c79cab9f764288845d84`, exactly the manifest value. Comparing the working file after CRLF-to-LF normalization to `git show HEAD:...` confirmed equality. These are independent characterizations, not repairs to the protected artifacts. The existing idempotence test writes directly into the protected overlay directory and was not run.

The earlier three-rule scan did not establish general infeasibility. No new versioned overlay is created: the unadjudicated candidate combinations cannot establish preservation of the protected facts. No paid inference or scientific validation was performed.
