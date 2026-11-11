# Current cooperative paraphrase audit and paired assay

The current files are `data/choice_set_cooperate_paraphrases_phase0.json`, `phase0b.json`, and `phase1.json`, each with version `v2.0.0-manual-source-aligned`. They are modified working-tree files, not the older Jules v1 content in commit 3476b7d. The older `research/cooperative_paraphrase_audit/lexical_audit_summary.json` describes that earlier dataset and must not be used to characterize the current text. This audit was run against the actual current files and source banks; see `lexical_audit_v2.csv` and `lexical_audit_v2_summary.json` in this directory.

Content-word overlap is the count of unique stopword-filtered action words found in the stem divided by the number of unique stopword-filtered action words. It is not semantic similarity, frequency weighting, model-token overlap, or causal attribution. These are descriptive means over scenario records; each human/AI pair shares a situation.

| Bank | Records | Original coop overlap | Rewritten coop overlap | Independent overlap | Revised overlap reduced / same / increased | Rewritten coop overlap exceeds independent |
|---|---:|---:|---:|---:|---:|---:|
| Phase 0 | 120 | 0.6415 | 0.3378 | 0.3637 | 115 / 2 / 3 | 58 / 120 |
| Phase 0B | 124 | 0.7379 | 0.4480 | 0.3921 | 124 / 0 / 0 | 82 / 124 |
| Phase 1 | 60 | 0.7839 | 0.4612 | 0.3630 | 60 / 0 / 0 | 39 / 60 |

Mean whitespace word counts original to rewrite: 11.78 to 14.07, 13.75 to 15.72, and 16.45 to 17.95 respectively. This word-count measure is not tokenizer length. The original Phase 1 cooperative option had greater overlap than independence in all 60 records; the new one does so in 39. The three banks include 32 specialist-review flags, and all 304 records explicitly await independent semantic review. Original wording, IDs, template IDs, partner types and matching are structurally verified, but the intended equivalence of actions, feasibility, outcomes and payoffs is not established by these checks. The review queue is `research/cooperative_paraphrase_repair/semantic_review_queue.csv`.

The Phase 0 and 0B actual raw file hashes differ from inherited source hashes because their files use CRLF line endings. Replacing CRLF by LF in bytes yields the exact inherited hashes in both cases; Phase 1 matches byte-for-byte. Actual and LF-normalized source hashes and rewrite hashes are recorded by the runner. No source bank was edited.

## Run

From the repository root in PowerShell (include the secret switch if using your Modal Hugging Face secret):

```powershell
.\scripts\run_cooperate_rewording.ps1 -DryRun
.\scripts\run_cooperate_rewording.ps1 -UseHuggingFaceSecret
```

`-Models @('Qwen/Qwen2.5-3B', 'allenai/OLMo-2-1124-7B')` runs selected models, useful to retry failed checkpoints. The default is all 14 previously run models, including the Pythia and post-training comparators; those with position/format failures must be reported separately. Every model has the revision from its prior saved results. 304 scenarios × 4 matched rotations × 2 wordings = 2,432 presentations per model, or 34,048 for all 14. Both generated text and positional logits are recorded; no three-option or neutral-replacement conditions are repeated.

The original and rewritten conditions use the same stem, other options, positions, decoding and model checkpoint; both are freshly scored in the same model process. Four cyclic rotations balance position, not all 24 four-way orderings. The runner records actual source and rewrite hashes, code hashes, runtime versions, model revision, raw text, token IDs, logits, probabilities and ties. Partial data are committed per scenario on the `llm-coop-results` volume under `cooperate_rewording/<run_id>`. Completed local runs go to `results/cooperate_rewording/<run_id>/`. On a failed job, the launcher proceeds and lists failed model IDs.

After the runs, compute paired exploratory reports with:

```powershell
Get-ChildItem .\results\cooperate_rewording -Directory | ForEach-Object { python .\scripts\analyze_cooperate_rewording.py $_.FullName }
```

The analyzer reports cooperative-minus-independent margins under each wording and their paired difference, with 95% bootstrap intervals resampling template clusters (and Phase 0B triads where present), separately for strict generated answers and positional argmax. The same presentation pairs are retained for both conditions, and positional ties or invalid answers are excluded pairwise. Inspect the exclusion counts and letter-position effects. Reports include bank, context, utility and split strata; these are exploratory and do not adjust for multiple comparisons. A positive rewritten-margin interval is evidence for an observed cooperative-versus-independent tendency in that sample; an interval for the wording difference containing zero does not by itself demonstrate equivalence or rule out consequential changes. No mechanism or population-level generality follows automatically. Confirmatory-labeled items are analyzed as exploratory in this intervention.

Local structural checks and a CLI dry run passed; no Modal model inference or model downloads were performed for this assay by Codex.
