# Canonical cohort provenance qualification

**Scope:** the 14-checkpoint paired-wording cohort summarized in `MANUSCRIPT_V1.md`, plus the six-run choice-set follow-up. These are historical observations. The qualification separates saved-row analysis from exact regeneration of model outputs.

## Paired-wording cohort

The source snapshot audited for this integration is `codex/phase2-other-agent-preference` at `58da0bd8fbb4ea33e166ec32ab73b0409ae7a0a3`. The canonical manifest identifies 14 checkpoints, 17 run directories, 3 duplicate reruns, and 2,432 rows per canonical run (34,048 canonical rows). The 14 immutable run IDs, row digests, model metadata, per-file code digests, and bank/paraphrase digests are recorded in [`cohort_provenance_manifest.json`](../reports/manuscript_readiness/cohort_provenance_manifest.json) and summarized in the [machine-readable qualification manifest](../reports/manuscript_readiness/canonical_evidence_qualification.json). All 17 source `rows.jsonl` files and their `summary.json` records are included under `results/cooperate_rewording/`; duplicate runs are retained and remain identified as duplicates.

A bounded check of the retained source branch verified all 14 canonical row digests against the committed row files after the recorded Windows CRLF normalization. The canonical and duplicate records are therefore content-checkable. The three bank source files and three paired paraphrase files also match the run-recorded digests under raw or documented line-ending normalization.

All 14 run summaries contain requested and resolved immutable model revisions. None records a tokenizer revision. Each run also records four inference-source file digests. Across 14 runs, 42 of 56 recorded file digests match source blobs in retained Git history. The remaining 14 entries all refer to `llm_cooperation/cooperate_rewording_assay.py` with digest `f0b919f3f41b4457efcd863bea680ded78689d42ca8fe2a8450e627a87ca9a6d`; no matching blob was found in the bounded history of available refs. Do not infer a generating commit from the other three files or from the later analysis snapshot.

**Reproducibility boundary:** the included raw choices can be reanalyzed using the included, versioned analysis code and frozen banks. Exact historical model-output regeneration is not established because tokenizer revisions are absent and the exact assay source blob is unavailable. The manuscript’s Phase 1 designation is also not a formally eligible prospective replication: the bank metadata says held out/unexecuted pending review while model rows exist. Human semantic review and the required calibration breadth remain outstanding. Post-hoc tests are exploratory.

## Choice-set follow-up

The post-hoc analysis selects six Phase 0B three-option runs by model identity and the bank hash recorded in each `summary.json`. The six selected run directories are included under `results/choice_set/`. Their purpose is to reproduce the manuscript’s exploratory conditional-substitution analysis. They are not independent training-history replications, and they inherit the Phase 0B bank’s pending human review. The intervention changes the choice set and does not establish an intrinsic second preference.

## Offline reproduction

From the repository root, with the Python dependencies in `pyproject.toml` installed, run:

```powershell
python -m scripts.audit_cooperate_rewording_results
python -m scripts.run_cohort_statistical_analysis --bootstrap 2000 --seed 42
python -m scripts.analyze_posthoc_significance --iterations 50000 --seed 20261111
python -m scripts.report_cooperate_rewording
python -m scripts.build_manuscript_v1
```

These commands use saved records only; they do not load models, contact inference providers, or require GPU execution. The audit and analysis scripts regenerate the machine-readable manifests/readouts and manuscript summaries. The 2,000-resample descriptive readout and 50,000-iteration post-hoc output were rerun from clean committed snapshots and matched the saved numeric outputs exactly in this Windows environment. Bootstrap and Monte Carlo output reproduced exactly in the validated Windows environment for the recorded seeds. The repository does not currently lock exact dependency versions, so numerical reproducibility across environments should be checked against the saved readout. The report’s historical run hashes reflect CRLF source bytes; Git stores normalized text, so the file bytes and hash display can differ across checkout settings while the LF-normalized content is identical.

## Separate Phase 0 cohort

The 14-run paired-wording records above are distinct from the 14 older Phase 0 result files described in [`phase0_historical_run_provenance.md`](phase0_historical_run_provenance.md), and from the 12 November 4 Phase 0B records described in [`phase0b_historical_run_provenance.md`](phase0b_historical_run_provenance.md). Do not pool those execution cohorts just because they share model names or scenario banks. Their missing revisions qualify those historical outputs individually; they do not invalidate the newer paired-wording cohort’s available model revision evidence.
