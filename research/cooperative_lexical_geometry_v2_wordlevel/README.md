# Cooperative lexical geometry v2: word-level pilot

This new corpus contains candidate single-word labels in English, French, Mandarin, Japanese and Arabic, with six concepts per category. Every label passes a structural check for a single unpunctuated token and there are no repeated labels within a language. **This is not lexical validation:** Chinese and Japanese are not space-delimited, and translation sense, wordhood, part of speech and cross-category matching still need fluent dictionary-backed review. The independently validated cohort is currently zero. Candidate translations were authored for this pilot; none is represented as independently verified. No model outcomes have been examined for this lexicon.

`review_template.csv` provides one review row per concept and language; its lookup URLs are leads, not verification. For example, the Wiktionary entries for [cooperation](https://en.wiktionary.org/wiki/cooperation) and [competition](https://en.wiktionary.org/wiki/competition) give translation evidence for some entries, but do not by themselves validate every selected sense. Particular candidates such as reciprocity/tبادل and solitude/独居 need scrutiny. Reject or replace questionable entries before a confirmatory study; maintain equal category counts. Save a new frozen hash after any review changes and before viewing model outputs.

## PowerShell

From the repository root:

```powershell
python research\cooperative_lexical_geometry_v2_wordlevel\validate.py
$lexiconHash = (Get-FileHash research\cooperative_lexical_geometry_v2_wordlevel\lexicon.json -Algorithm SHA256).Hash.ToLower()
python research\cooperative_lexical_geometry_v2_wordlevel\run.py --expected-sha256 $lexiconHash
```

Add `--local-files-only` to prohibit model downloads. The pinned multilingual E5, BGE-M3 and LaBSE models run locally; E5 uses its documented `query: ` encoding prefix. The runner produces normalized embeddings, full raw and per-language-centered cosine matrices, and descriptive within-language, distinct-concept cross-language and translation-control means. The runner is a **provisional descriptive pilot**: it does not implement the v1 inferential bootstrap, permutation tests, frequency or valence controls, plots, or a confirmatory statistical test. Model outputs must not be described as validating the translations or the hypothesis. Local inference was not run for this candidate corpus.
