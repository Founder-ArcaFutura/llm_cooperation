# Bounded empirical validation protocol

The pilot is **local CPU inference**, not language-model training. It scores only
a seeded uniform 10,000-story sample from the four pinned train parquet shards.
The nested 500-story smoke is part of those 10,000, not an additional sample.
Reading source shards to retrieve uniformly sampled row indices is not a
full-corpus embedding census. Public source bytes and sampled full stories remain
under ignored `outputs/semantic_pilot/`.

From repository root, using the existing local Python environment and cached E5:
Use a **new ignored report directory** for a fresh inference reproduction; the
committed `pilot_artifacts` directory holds a frozen capture whose run identity
must not be mixed with a different checkout's Git identity. Existing source shards
in the default cache are reused after validation, not downloaded again.

```powershell
$env:SSLKEYLOGFILE=''
$pilotReport='research/pretraining_counterfactual_v1/outputs/reproduction'
python -m research.pretraining_counterfactual_v1.pilot prepare --report $pilotReport --system-trust
$env:HF_HUB_OFFLINE='1'
$env:TOKENIZERS_PARALLELISM='false'
python -m research.pretraining_counterfactual_v1.pilot smoke --report $pilotReport --threads 4
python -m research.pretraining_counterfactual_v1.pilot score --report $pilotReport --threads 4
python -m research.pretraining_counterfactual_v1.pilot review --report $pilotReport
```

`--system-trust` is an optional Windows workaround that uses the Windows trusted
certificate store via pip's bundled truststore, preserving TLS verification. It
does not disable certificates or send credentials. `prepare` downloads only the
four pinned source shards and tokenizer files. It does not download GPT-2 weights.
For a different cache location, pass `--cache` and the exact `--encoder-path` whose
final directory name is the pinned E5 revision. Setup may require the dependencies
listed in requirements.txt; actual versions used are in scorer_identity.json.

The review selector draws random40 first with seed 20261108, then disjoint top20
and bottom20 cooperation-presence scores, top20 and bottom20 competitive-success
margins, and 20 ambiguous near-ties. Numerical scores are not part of the full-text
reading packet, but the stratum is known. This is **not** blinded independent gold
annotation. The automatic evidence candidates are regex-selected sentences with
exact offsets, not semantic judgments. Codex read each original full story and
selected short supporting excerpts; all semantic interpretations remain provisional.
Equal-score ties use source-index order. In particular, the zero-margin diagnostic
stratum is not a randomized prevalence sample within the entire zero-score bin.
Only random40 is used for population prevalence estimates.

`pilot_artifacts/review_notes.json` preserves those compact annotations. The eight
fields for each source ID are labels, uncertainty, actor, action, outcome,
attribution, exact evidence substring, and explanation. To replay the **frozen
reported analysis**, restore its recorded scores (no inference) and reconstruct
evidence from the cached source stories:

```powershell
python -m research.pretraining_counterfactual_v1.pilot_tools.restore_scores
python -m research.pretraining_counterfactual_v1.pilot_tools.build_reviews
python -m research.pretraining_counterfactual_v1.pilot_tools.supplement
python -m research.pretraining_counterfactual_v1.pilot_analysis
python -m research.pretraining_counterfactual_v1.pilot_tools.augment
python -m research.pretraining_counterfactual_v1.pilot_tools.quality
python -m research.pretraining_counterfactual_v1.pilot_tools.report
python -m research.pretraining_counterfactual_v1.pilot_tools.finalize
python -m research.pretraining_counterfactual_v1.pilot_tools.verify
```

`restore_scores` verifies the committed archive and never overwrites a different
existing score capture. Decompressed scores remain ignored. Reanalysis may change
plot bytes across library/font environments; verify the original package first.
Preserve generated originals; finalization compresses with fixed timestamp without
deleting the full local capture. Artifact_manifest.json hashes tracked outputs;
raw shard hashes and original source indices permit reconstruction.

Interpretation rules are deliberately separated:

- Cooperative behavior present is not the same as reward to that cooperative
  actor. Recipient-only benefit, counterfactual sharing, and help preceding an
  unrelated disaster are recorded separately in notes, not converted to actor return.
  Explicit thanks/praise/hugs directed to the helper count as social return even
  when the helper's feelings are not separately stated. Coding guidelines were
  clarified for consistency during this exploratory pilot, before metric calculation;
  these are development-set judgments, not a frozen independent validation set.
- Failure of a cooperative group is distinct from moral punishment or proof that
  cooperation caused the adverse outcome. The legacy `cooperation_punished` field
  names adverse/failed cooperation, with this explicit limitation.
- Rivalrous victory, selfish material gain, independent personal success, and moral
  endorsement are different constructs. Fair racing can be rewarded while the
  story remains friendly. Unpunished theft can yield material gain while narration
  condemns it. Neither implies the same causal intervention as endorsing selfishness.
- The five separate window similarities, all five softmax proxy values and success
  minus failure margins are preserved. Max-window probabilities are not calibrated
  probabilities and need not sum to one across a whole story.

Diagnostic thresholds were encoded before completing the reviews: .5 for cooperation
presence, .25 for cooperative reward margin, .1 for competitive-success margin.
They are arbitrary diagnostics, not selected to maximize measured accuracy. Top20
competition precision is a separate retrieval metric. Random40 alone supports
approximate prevalence; stratified140 confusion matrices are explicitly diagnostic
and cannot be reported as population accuracy. Wilson intervals describe sampling
uncertainty conditional on provisional labels; they do not include annotation bias.
Uncertain cases are excluded from definitive confusion matrices, and should be
shown in sensitivity bounds rather than silently assigned confident classes.

Eight supplementary lexical follow-ups document fair contests and error cases in
the same 10,000 sample. A ninth case preserves an early score-tail false positive
that fell outside the final140, with its final rank. These are purposive, excluded
from prevalence/classifier metrics, and do not add embedding calls. No keywords
become training filters.

Do not treat any estimate of sample token mass as full-corpus unique-token counts.
Exact duplicate text within the sample is measurable; corpus-wide duplicate clusters
are unknown. Reweighting curves are sample projections, not frozen training weights.
The intervention is not scientifically validated without independent human review,
a reward/actor-sensitive classifier and held-out acceptance criteria.
