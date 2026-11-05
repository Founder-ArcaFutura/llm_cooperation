# Model-authored controlled-bank rewrites on Modal (experimental)

This runner produces **provisional candidate** scenario banks from the frozen
124-scenario Phase 0B source. It does NOT modify that source or silently
replace the PR's current bank files. It does not certify semantic equivalence.

## Inference model and controls

- Writer: `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` on a Modal H100.
- Exact model commit SHA is resolved once per run and written to its manifest.
- Measurement tokenizer: `Qwen/Qwen2.5-1.5B`, pinned to
  `8faed761d45a263340a0528343f099c05c9a4323`.
- Each call rewrites one complete set of four actions, preserving the original
  scenario, original strategy labels, and payoff specification.
- Three separate generations per scenario (A, B, C) are based on the original
  source actions. Prior-bank wording is *only* a collision-avoidance reference.
- A response is accepted automatically only when its four action descriptions
  are nonempty, distinct, grammatical-pattern checks pass, both action-only
  and full-prompt token span are <=1, and it does not duplicate or nearly
  duplicate the same labelled action in a prior bank.
- Failed candidates receive detailed token-count and similarity feedback and
  are retried up to the configured limit. Unresolved cases remain unresolved:
  no automatic padding, and **no silent acceptance**.
- All accepted automatic candidates retain
  `semantic_review: UNADJUDICATED`. All outputs remain **PROVISIONAL**.
- No paid inference occurs without `--authorize-paid-run`.

## Run commands (PowerShell, from repository root)

First inspect the dry-run guard (no GPU):

```powershell
modal run modal_controlled_bank_rewrite.py --limit 6 --run-name pilot01
```

Pilot on six scenarios: **18 four-action generation tasks**, plus any retries:

```powershell
modal run modal_controlled_bank_rewrite.py --limit 6 --run-name pilot01 --authorize-paid-run
```

Download and review the pilot:

```powershell
modal volume get llm-coop-controlled-rewrites pilot01 research/controlled_rewrites/pilot01
```

If the pilot results justify the paid run, generate the complete bank:

```powershell
modal run modal_controlled_bank_rewrite.py --limit 124 --run-name full01 --authorize-paid-run
modal volume get llm-coop-controlled-rewrites full01 research/controlled_rewrites/full01
```

Use a distinct run name for every run; the runner refuses to overwrite an
existing run directory. Repeated runs charge paid GPU time. Weight download
and initial model setup may be significant. **We have not run a pilot or full
GPU job yet**, so runtime, success rate, and cost are not established.

## Output contract

Inside each run's Modal volume directory:

- `records/NNN_A.json`, `NNN_B.json`, `NNN_C.json`: the raw candidate
  outcome, attempted action set, token counts, any failure reasons, and
  attempts.
- `bank_a_candidates.json`, `bank_b_candidates.json`,
  `bank_c_candidates.json`: **only automatically accepted** scenario
  variants; partial banks if failures occurred, or if running a pilot.
- `unresolved.json`: items needing another generation or repair pass.
- `manifest.json`: model revision, tokenizer revision, original corpus
  checksum, bounds, counts, and provisional status.

The full three-bank candidate output is **not** the frozen corpus. Before it
can be used scientifically, independently review semantic equivalence,
partner identity, tradeoffs, naturalness and any hidden distributional cues.
Then rerun the complete acceptance tests, create new inventories and hashes,
and only then freeze a validated version.

### Why this workflow is preferable

The earlier Jules implementation used string substitutions and token padding,
which left malformed prose and 235 scenario-bank length violations. This
generative pipeline lets the LLM write natural action alternatives **jointly**,
while deterministic code checks the measurable constraints after each attempt.
It does not confuse a model's own rewriting judgments with independent
scientific adjudication.

## Incremental reuse of accepted candidates

A successful token-matched set is saved as an immutable record in the original
run and can be reused in subsequent runs. This is **automatic-constraint
acceptance only**, not independent semantic validation.

After the `pilot02` results, do not regenerate its six accepted sets. Fetch
the latest branch, then inspect the dry run:

```powershell
git fetch origin
git switch --detach origin/controlled-strategy-banks-v1-13918473886041179938
modal run modal_controlled_bank_rewrite.py --limit 6 --reuse-run pilot02 --run-name pilot03
```

When you separately authorize paid compute:

```powershell
modal run modal_controlled_bank_rewrite.py --limit 6 --reuse-run pilot02 --run-name pilot03 --authorize-paid-run
```

The new run checks source SHA-256, pinned measurement tokenizer, model ID,
source scenario identity and each accepted record's tokenizer and duplication
checks again. Only unresolved variants are sent to the writer. The new
manifest counts `reused`, `newly_accepted`, and `unresolved` separately.
The old volume run remains unchanged. Subsequent runs should reuse the latest
run name to accumulate accepted samples. Do not use a pilot source as the
resume base for a full 124-scenario run without reviewing the exact coverage.

**Important:** this feature has been committed but has not yet completed an
integration test on Modal. Keep the next run to the existing six-scenario pilot.

## Bounded production pass (after pilot04)

The production run reuses ten accepted sets from pilot04 and attempts the
remaining 362 scenario-bank variants once, each with up to the configured
number of repair rounds. There is **no infinite retry loop**. Exceptions from
individual model calls are saved as failed records rather than ending the job.
Five consecutive generation exceptions trigger a circuit breaker. The volume
is checkpointed after each scenario. A soft runtime limit stops before the
next item; the existing item may finish after the nominal cutoff. This is a
runtime guard, **not a strict spending cap**, because initialization, GPU
billing, and in-flight calls may add cost. The Modal function itself also has
a hard four-hour timeout.

Run from the detached worktree, after fetching the current PR commit:

```powershell
git fetch origin
git switch --detach origin/controlled-strategy-banks-v1-13918473886041179938

# Verify flags without launching GPU
modal run modal_controlled_bank_rewrite.py --limit 124 --reuse-run pilot04 --run-name production01 --max-attempts 4 --max-runtime-minutes 60

# Only with explicit paid-compute authorization
modal run modal_controlled_bank_rewrite.py --limit 124 --reuse-run pilot04 --run-name production01 --max-attempts 4 --max-runtime-minutes 60 --authorize-paid-run

# Inspect outcomes directly, avoiding Windows destination-path collisions
modal volume get llm-coop-controlled-rewrites production01/manifest.json -
modal volume get llm-coop-controlled-rewrites production01/unresolved.json -
```

The manifest distinguishes accepted, reused, newly accepted, unresolved,
inference errors, and items not attempted because the run stopped early.
A stopped or partial production run remains **PROVISIONAL**, and should be
continued using `--reuse-run production01 --run-name production02` rather
than overwritten. Semantic review remains mandatory before scientific use.
