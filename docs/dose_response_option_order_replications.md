# Randomized option-order replications, exploratory v1

This tests whether the existing cooperation measurements survive new relative
option orders. It does not assume that replication will support cooperation or
that answer order explains all calibration failures. Preparation date: 2026-11-07.

## Cohort and jobs

The frozen plan is `research/dose_response_order_replications_v1/plan.json`.
It includes all thirteen completed non-Pythia checkpoints across ten families,
including failed-format and strongly position-sensitive models as diagnostic cases.
Every baseline is a complete real 504-presentation run with its paired calibration.
One original Qwen-3B run is used; its duplicate is not counted as independent evidence.
Revisions, model seed, precision, bank hashes and baseline evidence digests are fixed
to those baselines. Gated Llama/Gemma access uses the existing Modal secret named
`huggingface-secret` containing HF_TOKEN with the required license access.

Two new schedules per model mean **26 sequential paid GPU jobs**, **13,104 behavioral
presentations** and **2,496 calibration presentations**, or **15,600 total**.
Calibration runs alongside each job; diagnostic failure is recorded without halting
the cohort. Execution/download/analysis failure stops the launcher. No new inference
was launched during implementation. The user's remaining credit is not a guaranteed
cost estimate or an enforced dollar cap; the launcher limits the job inventory.

## What is randomized

The original four cyclic Latin-square rows remain schedule 0, byte-for-byte in their
prompt rendering and IDs. Changing the ordinary model seed still does not change
that baseline. The new controls are `order_replication=1/2` and `order_seed=20261107`.

The 24 possible orders partition into six cyclic rotation orbits. For each scenario
family, SHA-256 of the fixed seed and family ID seeds a local random generator.
Two different orbits are sampled without replacement from the five non-baseline
orbits, with shuffled row order. Each selected orbit supplies four presentations:
every strategy appears once at A, B, C and D. There are no duplicate option orders
within or between the three schedules for any scenario. Together they cover 12 of
the possible 24 orders. They are coordinated randomized perturbations, not IID
draws or independent training replications.

All payoff tiers, partner identities and factorial variants sharing a template
family use the same schedule. This preserves paired family comparisons across
tiers; it avoids introducing different option-order mixtures at different doses.
Scenario text, payoffs, decoding, candidate token validation and model revisions
are held fixed. The 24 factual calibration items also receive two disjoint balanced
option schedules, seeded by their item IDs independently of social content. Correct
answers remain exactly balanced over A/B/C/D. Calibration wording is unchanged.

The original numerical runtime is PyTorch `2.15.0+cu132` and Transformers `5.22.1`
for all thirteen baselines. New real order runs check those versions before loading
the model; a mismatch stops the job rather than silently confounding order and
runtime changes. The existing cached Modal dependency image is retained. A runtime
failure may still incur container startup charges before the check executes.

The plan records family rows and SHA-256 of all rendered behavioral prompts and
presentation IDs for each schedule. Real raw outputs record the replication index,
order seed and schedule hash; actual recorded mappings are checked against the
generated schedule before comparison. Bank and engine changes cause preflight to
fail. The new order mode is restricted to the exploratory dose-response bank;
confirmatory holdouts remain unused.

## Run from PowerShell

```powershell
Set-Location G:\llm_cooperation

# Local audit and display only; no network or model calls
.\scripts\run_dose_response_order_replications.ps1 -PrepareOnly

# Authorize all 26 planned GPU jobs, sequentially
.\scripts\run_dose_response_order_replications.ps1 -AuthorizePaidRun
```

Results go to `results/dose_response_orders/<model>_order<N>_s20261107/`.
Per-run reports go to the corresponding `reports/dose_response_orders/` directories.
Every job prints its live log location and a heartbeat every 20 seconds. Completed
jobs are validated and skipped on resume. An existing incomplete job is blocked
before another paid attempt; the launcher prints its exact download-only recovery
command. After recovering, rerun the same launch command to continue. Do not start
two copies of the launcher concurrently.

After all runs complete, comparison runs automatically. To rebuild it locally:

```powershell
python -m llm_cooperation.analysis.order_replications compare
```

The final Markdown table and detailed JSON go under
`reports/dose_response_order_comparison/`. No further inference is required.

## Analysis and falsification

For each model and schedule, report observed COOPERATE rates at all eight payoff
levels, equal-utility COOPERATE-minus-INDEPENDENT rate and log-probability contrast,
COOPERATE rate conditional on assigned A/B/C/D, and scenarios selecting COOPERATE
in all four presentations. A fixed-letter responder scores 25% cooperation under
these balanced schedules; synthetic fixed-letter and semantic-choice controls test
that the diagnostics distinguish those cases.

Compute a full-observed-range cooperation slope separately within each of the six
main families. Average those family slopes, and resample the six complete families
2,000 times for an exploratory interval using the same estimator and dose range in
the point estimate and every resample. This explicitly permits flat, negative and
heterogeneous responses. Do not replace an unobserved crossover with an extrapolated
claim of cost tolerance. Partner-benefit/horizon inference is still limited to two
families and two doses.

Compare each new schedule to its own model baseline using paired family-level
changes in main-sweep choice and log-probability contrasts, with family bootstrap
intervals. Keep counterbalanced presentations, partners, tiers and repeated model
runs together rather than inflating independent n. Report calibration accuracy,
generated-letter validity and letter distribution alongside each schedule. A
significant positive level with a near-zero payoff slope is a different result from
evidence of payoff-sensitive cooperation. An interval containing zero does not
demonstrate equivalence; no post-hoc equivalence margin is claimed here.

Stable cooperation across these orders would weaken a pure fixed-letter or a
particular relative-order explanation. A weaker, reversed, or unstable effect is
contradictory evidence and must be retained. Stable calibration failures remain
failures: repeated generation of explanations does not become letter-only format
compliance. This design cannot isolate numerical reasoning from payoff-related
wording, test autonomous social behavior, or establish an intrinsic cooperative
preference. Those require separate controls. This follow-up is designed after
viewing baseline data and remains exploratory.
