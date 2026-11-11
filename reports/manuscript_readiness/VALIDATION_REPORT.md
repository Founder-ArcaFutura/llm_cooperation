# Validation report

## Completed offline validation

- The named external artifacts `cooperation_significance_analysis_20261111.md` and `.json` were not found in the repository. The reported tests were therefore reproduced from the available repository rows, not assumed correct from the outside summary.
- Recomputed the cohort readout from canonical run rows with 2,000 template/triad-clustered bootstrap draws and seed 42. The output now records the source revision, runner and analysis-engine SHA-256 values, and input-row hashes.
- Reproduced 22 four-option model-by-bank tests with 50,000 randomizations each, plus six three-option intervention tests. Three-option tied top logits were detected from stored logits and excluded from the primary denominator; a tie-inclusive analysis was also run. The JSON records both sets of results, seeds, denominators, cluster counts, input hashes, model revisions, Monte Carlo exceedances, Monte Carlo standard errors, exact binomial Monte Carlo intervals, and Holm-adjusted p-values.
- Regenerated the Markdown readiness dossier and manuscript tables from the canonical outputs.
- Regenerated the complete manuscript from the analysis JSON and checked that generated tables match those outputs.
- Verified raw source rows against the existing per-run SHA-256 manifest. The raw `rows.jsonl` files were not edited. Derived `paired_analysis.json` summaries were refreshed by the cohort analysis runner.

## Commands and outcomes

From `G:\llm_cooperation` in PowerShell:

```powershell
python scripts/run_cohort_statistical_analysis.py --bootstrap 2000 --seed 42
python scripts/analyze_posthoc_significance.py --iterations 50000 --seed 20261111
python scripts/report_cooperate_rewording.py
python scripts/build_manuscript_v1.py
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest tests/test_manuscript_readiness_audit.py tests/test_cooperate_rewording_assay.py tests/test_posthoc_significance.py tests/test_manuscript_v1_integrity.py
```

The targeted test suite completed with **12 passed**. A pytest launch without `PYTEST_DISABLE_PLUGIN_AUTOLOAD` stopped during third-party plugin initialization: the auto-loaded LangSmith plugin attempted to access a protected Windows SSL key-log path and raised `PermissionError`. Disabling unrelated global plugin autoload allowed the repository tests to run. Pytest also emitted a `pyreadline3` console-destruction warning after reporting the successful result; it did not change the exit code or test result.

## Validation limitations and unresolved scientific work

- No model was rerun; all analyses were offline.
- The randomization tests are post-hoc exploratory tests. Their inferential meaning depends on the within-template/triad exchangeability assumptions documented in `POSTHOC_SIGNIFICANCE_METHODS.md`.
- The Phase 1 bank metadata says it was held out and unexecuted pending human review, but model run records exist. Its actual JSON contains 60 scenarios and 30 templates; an older draft's 120/60 figures were incorrect for the operative bank. The chronology and approval status need Adrian's resolution.
- Independent human semantic adjudication of the prepared 304-item queue is not complete. Earlier semantic review was AI-assisted, not independent human review.
- Only four checkpoints from two families passed both historical calibration criteria, below the four-family threshold for formal prospective replication.
- The six-model three-option follow-up was selected as exploratory, and its underlying bank remains marked `pending_human_scientific_review`.
- The generated analysis artifacts and scripts are in the working tree and have not been committed. Machine-readable source revisions and hashes identify their input/output provenance; commit these files together if they are accepted.
