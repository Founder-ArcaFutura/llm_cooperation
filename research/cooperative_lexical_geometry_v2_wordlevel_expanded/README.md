# Cooperative lexical geometry v2: word-level expanded corpus

## Overview

This directory contains the expanded, structurally audited, dictionary-backed multilingual word-level cooperation corpus across five languages:
- English (`en`)
- French (`fr`)
- Mandarin Chinese (`zh`)
- Japanese (`ja`)
- Arabic (`ar`)

The corpus consists of **200 concepts** (50 concepts per category across *cooperation*, *competition*, *independent*, and *neutral*). Every concept satisfies the strict constraint of **one naturally occurring single unpunctuated lexical word per language**.

## Governance and Scientific Integrity

- **Pilot preservation:** The original 24-concept pilot in `research/cooperative_lexical_geometry_v2_wordlevel/` is completely preserved. In this expanded corpus, original pilot concepts are explicitly tagged with `"cohort": "pilot"`, while new candidate concepts are tagged with `"cohort": "confirmatory"`.
- **Pre-inference gate:** In accordance with scientific integrity guidelines, no model embeddings (multilingual E5, BGE-M3, LaBSE) have been computed for this expanded corpus. Corpus expansion, independent lexical verification, and structural auditing strictly precede confirmatory hypothesis testing.
- **Human review status:** All items are supported by independent lexicographical resources (OED/Merriam-Webster, TLFi/Larousse, CC-CEDICT/Contemporary Chinese Dictionary, Daijirin/Kojien/JMDict, Hans Wehr/Al-Maany). However, **native fluent speaker review has not yet been performed** and remains required before formal hypothesis testing.

## Files

- `lexicon.json`: 200 concept entries with ID, category, cohort, subdomain, gloss, and words in all 5 languages.
- `verification_records.json`: Detailed per-concept verification data including lemmas, parts of speech, independent lexical URLs, sense definitions, polysemy notes, and verification statuses.
- `rejected_candidates.json`: Register of evaluated candidates that were rejected due to multi-word phrasing, punctuation/hyphenation, idiom compositionality, or semantic redundancy.
- `validate.py`: Validation script verifying single-token constraints, absence of whitespace/punctuation, zero within-language duplicates, category balance, and schema integrity.
- `balance_report.py`: Script generating statistics on subdomain distributions, character length profiles, and cross-category balance.
- `balance_summary.json`: Machine-readable summary produced by `balance_report.py`.
- `corpus_audit_and_balance_report.md`: Detailed scientific report assessing the maximum defensible cohort size and answering whether the corpus is ready for confirmatory inference.
- `frozen_manifest.json`: Crytographic SHA-256 hashes freezing the expanded corpus files.

## Validation

To run structural and lexical validation:

```bash
python3 research/cooperative_lexical_geometry_v2_wordlevel_expanded/validate.py
python3 research/cooperative_lexical_geometry_v2_wordlevel_expanded/balance_report.py
```
