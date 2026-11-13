# Constrained factorial cooperation assay, development v0.1

Status: working offline compiler and generated design, **not a validated behavioral instrument**. No inference calls or paid evaluations have been made. No spending or compute caps are introduced. Inspection of this design and independent semantic review precede a separately authorized evaluation. Existing scenarios, choices, annotations and manuscript remain unchanged.

## Deliverables and scientific scope

The compiler in `scripts/factorial_cooperation_design.py` generates 44 conditions, not just matched pairs. There are two development domain implementations (water testing and analytical calibration), each containing these complete blocks:

| Block | Cross | Conditions per domain | Identifiable contrast, conditional on semantic acceptance |
|---|---|---:|---|
| Mechanism/time | Seven task arrangements × 0 or 20 additional actor work minutes | 14 | Within-arrangement time differences; task-package differences; differences in time sensitivity |
| Return/time | Absent or guaranteed conditional future return × time | 4 | Return/incentive package; time; interaction |
| Mutual necessity/time | Optional or necessary complementary contributions × time | 4 | Mutual necessity/outcome package; time; interaction |

This is a constrained collection of crossed blocks, not a 7 × 2 × 2 × 2 experiment. No effect is estimated by extrapolating into an excluded cell. Block-specific baselines remain separate even when some descriptions resemble each other. Two texts transplanted through a common construction grammar are **not two independent authoring replications**, a population sample, or a holdout test.

`design_matrix.csv` has one row per candidate condition and actual factor levels. `candidate_conditions.json` includes full text, action meanings, outcomes by party, overlap labels, provenance and limitations. `intended_comparisons.json` identifies all one-factor edges within blocks. It includes 84 between-mechanism package edges, not 84 independent tests; analyze prespecified omnibus contrasts rather than declaring all these primary. `*_model_matrix.csv` and `estimability.json` record numerical coding and rank. Full column rank establishes algebraic estimability only.

`presentations_RESTRICTED.jsonl` contains **4,576 rendered offline presentations**, with no model responses: 44 conditions × two counterpart identities × two sentence orders × (two binary permutations + 24 four-action permutations). These are repeated presentations, not 4,576 independent scenarios. Wording variants reorder identical sentences; they test order sensitivity, **not paraphrase robustness**.

## Factors, units and hypotheses

The decision-maker chooses its own action. Counterpart identity is human or embodied automation, explicitly equipped with tools, record transfer and scheduling authority. Neither condition is a recipient-preference question. Identity comparisons concern the described counterpart; they do not establish effects of the decision-maker's identity.

Mechanism is a categorical task arrangement, with overlapping multi-label annotations retained. Joint work may also transmit information and assist the counterpart. Exchange entails a conditional return. Parallel activity is a control, not a seventh cooperative subtype. There is no defensible ordinal mechanism score.

Cost is a named dose, 0 versus 20 additional minutes of active work after a 50-minute routine test. Zero is stated explicitly. Manual versus automated recording implements the difference; method, burden and opportunity cost cannot be disentangled from time here. All cost pairs hold action-option text and the other recorded outcomes fixed. The study estimates a finite difference at these doses, not a continuous dose-response curve or a utility derivative. Plausibility of zero additional time for each action requires review.

Return is guaranteed future service saving the actor ten minutes, conditional on lending today, versus explicitly no return. Removing uncertain trust improves specification but changes the realism of the construct. This estimates a return/incentive package, not social reciprocity independent of expected benefit. A later block with matched unconditional benefits and independently varied reliability can challenge that interpretation; it is not generated here.

Mutual necessity means both complementary contributions are required for **either party's additional certified check**. Ordinary tests still succeed in every binary condition. Under optional contributions, each party has a complete independent record and gets the additional check under either action. Necessity therefore changes reference outcomes for both parties and the actor's incentive to combine contributions. Conditioning statistically on those deterministically linked outcomes cannot recover a pure necessity effect.

Prespecify these prospective questions before new behavior is exposed:

1. Does added time alter target selection within each reviewed mechanism? Use two-sided contrasts; a universal negative cost effect is not assumed.
2. Do models differ in the vector of these time effects across mechanisms? This is a model × mechanism × time test, with checkpoint ancestry respected.
3. Does a conditional future return change selection, and does it change sensitivity to current time cost?
4. Does mutual necessity/reference-success change selection, and does it modify time sensitivity?
5. Do these contrast vectors survive counterpart identity, sentence order, position and choice-set perturbations and predict genuinely unexposed families?

A significant mechanism coefficient alone cannot distinguish mechanism sensitivity from action wording, actor/recipient outcomes or scenario plausibility. A stable response profile requires replication of contrasts in independently authored families with varied nuisance features and better held-family prediction than incentive-only models.

## Feasibility and unavoidable coupling

`feasibility_matrix.json` screens all 56 candidate mechanism/cost/return/necessity assignments. The matrix is a conceptual assessment under these operational definitions, not a generation whitelist or human-validated census. Each row records whether time is independently adjustable, other properties are coupled, or a combination contradicts the mechanism. Only declared blocks generate text.

| Arrangement | Time variation | Return variation | Contribution necessity |
|---|---|---|---|
| Joint task | Feasible with fixed routine outcomes | Coupled to incentives | Optional joint work is possible; changing complementary necessity alters independent success |
| Timing coordination | Feasible if schedule slack is explicit and credible | Possible but changes incentives | Success may depend on synchrony; necessity then changes reference outcomes |
| Information sharing | Feasible | Possible but transfer becomes conditional exchange when return is required | Redundant versus necessary information changes reference success |
| Resource sharing | Feasible if unused equipment and return are specified | Demonstrated return/time block; conditional return also gives exchange features | Availability of substitutes couples necessity and reference success |
| Exchange | Feasible | A no-return exchange contradicts this operational definition | Necessity of traded inputs couples to alternatives and outcomes |
| Unilateral assistance | Feasible with review of zero-time implementation | Conditional return adds exchange features | Substitute assistance changes incremental recipient benefit |
| Parallel control | Feasible as an activity/schedule preference control | Contingent return introduces interaction | Cross-contribution necessity introduces interaction |

In the mechanism block, social arrangements yield a counterpart additional check only under the target action. Parallel activity yields it under either choice. This makes parallel useful as a no-incremental-help control but prevents calling social-minus-parallel a pure mechanism effect. Exchange additionally gives an archive of no stated task value. Its value cannot be presumed zero just because no current use is stated.

The mutual-necessity block tests joint complementary work rather than quietly calling one-way informational dependence mutual interdependence. The resource-return block follows the cutting-bit prototype's logic using unused diagnostic equipment; the actual historical cutting-bit scenario is not presented as a rewritten condition.

## Provenance and immutability

Water descendants anchor to Phase 0B `template_025`; laboratory descendants anchor to Phase 0B `template_061`. Both human and AI historical scenario IDs, full-file SHA-256 and canonical selected-record SHA-256 are stored per condition. These anchors are selected for concrete physical operations and clear historical pointers, **not certified as semantically valid parents by provisional model labels**. Their original payoffs, options and split labels are never inherited as new truth. All generated text is explicitly new and the original four-strategy labels are not reused as outcome categories.

The taxonomy, 304-scenario inventory, transformation specification, report and three prototypes in `research/multidimensional_cooperation_v1` informed this design. `input_manifest.json` hashes these inputs and historical parent files. It permits drift detection; it does not change or recode those files. The compiler only writes to its designated output directory. Save human annotations separately; regeneration replaces derived files, including empty review templates.

## Independent review and manipulation validation

`review_packets_blind.json` contains 352 first-pass packets: every condition × counterpart identity × sentence order × choice set, with one deterministically shuffled option order per packet. `review_RESTRICTED_key.json` and the presentation manifest reveal intended factors/action mappings. **Distribute only the blind packets and the reviewer guide to first-pass annotators**, in a separate folder or access-controlled location. A private repository does not protect blinding from collaborators with access to the keys. Opaque IDs are not encryption, and the manipulations remain visible in the prose.

Assign each packet independently to at least two reviewers without model outcomes or intent keys. Balance reviewer assignment across domain and variant without showing linked pairs first. Record mechanisms as multi-label; recover numeric actor time for each action, future return, each party's ordinary/additional success and whether contributions are necessary for the named outcome. Ask about authority, feasibility, framing, plausibility and uncertainty. Freeze independent responses before adjudication. In a separate second pass, reveal paired conditions, intent and historical anchors to assess intended changes, residual changes and provenance fidelity. Source fidelity does not require new text to preserve the old payoff.

An authored family/block is eligible only after both reviewers agree on all critical manipulated values and binary outcomes, or an independent adjudicator resolves discrepancies with recorded reasons. Any unresolved role impossibility, contradictory outcome, wrong time dose or major unintended change makes that block ineligible. Revise and review all affected pairs together. Do not silently drop a difficult cell and retain a claim about a complete factorial. Publish disagreements, exclusions and revised version hashes. This is a semantic acceptance rule, not an inference spending cap.

All current semantic and identity review fields are pending. Structural validation checks exact crossed coverage, constraints, parent resolution/hashes, outcome arithmetic, invariant cost-pair ledgers and option meanings, unique IDs, every permutation, and action-to-letter mappings. Tests deliberately remove cells and orders and corrupt outcomes/mappings. These checks cannot prove naturalness, construct validity, reviewer independence or perceived manipulation strength.

Before behavioral inference, freeze a reviewed specification, text hashes, eligibility decisions, model cohort and analysis plan. Manipulation-comprehension probes should ask for time, return, outcome and dependence extraction on separate presentations; do not insert probes into choice prompts. Report probe failures and sensitivity using all eligible cases as well as comprehension-qualified cases. Model-based comprehension checks are diagnostic and do not replace independent human validation.

## Analysis and family-level uncertainty

Primary response is target selection from the binary set. Four-action responses are a separate multinomial sensitivity, because supervisor referral and deferral change the comparison set and introduce explicit alternative time/outcome tradeoffs. Never treat a removed alternative as revealing an unobserved second preference. Report all action probabilities/choices and their changes across sets, not only a cooperative share.

For checkpoint m, family f and mechanism k, define p(m,f,k,c) as target probability (or forced-choice rate) equally averaged over the prespecified identity, wording and option-position strata at cost c. The family-specific cost contrast is p(20) − p(0). A mechanism × cost contrast is the difference of two such contrasts. For return/time and necessity/time, the interaction is [p(1,20) − p(1,0)] − [p(0,20) − p(0,0)]. Average families equally within prespecified domains, then domains equally; do not weight a family more heavily because it has extra permutations. Report binary probabilities and percentage-point contrasts, not just log-odds coefficients.

The numerical matrices use a family intercept, time indicator, mechanism indicators relative to parallel activity and their time interactions; the two smaller blocks use factor, time and factor × time terms. Corresponding full ranks are 15/15 for 28 mechanism rows and 5/5 for each eight-row block. Treat coefficients as descriptive for these two development domains. Rank does not give independent residual replication: reused grammar, deterministic forced choice, or repeated permutations cannot create independent families.

With a larger independently authored family sample, fit block-specific logistic or multinomial hierarchical models with family intercepts and treatment slopes, model-specific factor interactions and prespecified domain effects. Report marginal probability contrasts from the fitted models. Fit checkpoints as named cases; do not use related checkpoints as independent random draws of model architectures. A model-family sensitivity should leave out related checkpoint groups. Avoid one omnibus regression pretending all factors are orthogonal across blocks.

For deterministic restricted-choice evaluation, retain logits/probabilities for every option if available. Store exact prompts, model revision, scoring method, tokenizer, seed where applicable, complete mapping and ties. Predeclare tie handling: report unique maxima, fractional allocation across tied maxima, and ties as a separate outcome; report missing/invalid rows without replacing them by reference choices. Do not condition primary eligibility on favorable model responses or successful tie resolution. For stochastic sampling, repeated draws estimate within-prompt sampling variability separately from between-family uncertainty.

With enough independently authored families, bootstrap whole families within domains or use a hierarchical interval and report leave-domain-out sensitivity; never bootstrap individual permutations as independent situations. With only these two template implementations, show separate descriptive contrasts and no population-level confidence claim. Choose the independent-family count and evaluation replication by simulation under scientifically relevant effect sizes, observed variance and desired interval width after a reviewed pilot; avoid treating presentations as the power-analysis sample size. This prototype imposes no arbitrary compute ceiling.

Prespecify the primary binary time omnibus test and the two package interactions. Treat all other pairwise mechanism comparisons as secondary, with simultaneous intervals or a declared multiplicity correction. If cell exclusions break a contrast, mark it non-estimable rather than imputing a missing factorial corner. Keep selection-based comprehension analyses secondary to all-eligible analyses.

## Testing profiles beyond incentives and framing

Compare prospectively specified predictive models on whole held-out families: (A) aggregate checkpoint tendency plus position/identity/order; (B) add explicit actor time, future benefit and each party's outcomes; (C) add mechanism-package indicators and their model interactions. Use held-family log loss/Brier score and calibration, and compare predicted contrast vectors, not just the training fit. Current exchange/return and necessity/outcome couplings prevent a causal decomposition even if model C predicts better. Replication with different task implementations is required.

Freeze these development families before commissioning new ones. Have independent authors construct genuinely new domains, for example archive curation and field logistics, with distinct action implementations and their own reviewed complete blocks. Do not merely substitute nouns or rename old exposed banks as holdout. Keep their text and responses out of template tuning, reviewer calibration and model selection; register authoring chronology and exposure ledgers. Blindly evaluate the frozen procedure once, then report all families and domain failures. Separately authored paraphrases and sham sentence changes should be reviewed for matched outcomes and then crossed with the same blocks; the two current sentence orders cannot support paraphrase generalization.

Mechanism-profile evidence would consist of reproducible, model-specific contrasts across these independent constructions, useful held-family prediction beyond outcomes/incentives, and resilience to framing/choice-set tests. Disappearing contrasts after outcome matching, reversals across domains, position dominance, or no predictive improvement are substantive findings against a stable mechanism interpretation. This instrument cannot establish motives, welfare preferences, general social cooperation, or a universal latent cooperation trait.

## Reproduce and extend locally

From `G:\llm_cooperation`:

```powershell
python scripts\factorial_cooperation_design.py
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest tests\test_factorial_cooperation_design.py tests\test_multidimensional_cooperation_study.py -q
# Compile a separately authored specification without replacing this development output:
python scripts\factorial_cooperation_design.py --spec research\factorial_cooperation_v1\design_spec.json --output research\factorial_cooperation_rebuild
```

The structured specification supports independently declared blocks, fixed dimensions, crossed levels and `exclude_if` partial assignments with reasons. Domain slots reference an immutable historical anchor. New task mechanisms or outcome structures require authored renderer changes and semantic review, not automatic Cartesian multiplication. Generated `validation_results.json` records the actual structural check status. No paid runner is wired to these development prompts.
