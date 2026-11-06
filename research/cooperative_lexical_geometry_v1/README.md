# Cooperative lexical geometry v1

## Status

**Prepared; model inference not executed.** The frozen 600-row lexicon passes structural tests, but its 15 phrase kernels per category are reused across ten domain frames. The non-English entries are researcher-authored compositional drafts, all requiring fluent human review. The corpus is therefore a pilot scaffold, not yet a publication-quality validated multilingual lexicon.

The local host is CPU-only and none of the three requested models is cached. A real download/inference attempt for pinned multilingual E5 failed because DNS lookup for `huggingface.co` failed (`getaddrinfo failed`). No embeddings, cosine matrices, model results, or scientific effect estimates exist yet. No remote or paid inference was used.

## Frozen corpus

- `lexicon_frozen.json`: 600 concept IDs, 150 per category, 10 domains × 15 phrase kernels, five languages.
- `lexicon_freeze.json`: SHA-256 and freeze metadata. Do not edit the lexicon after embeddings are produced. Changes require a new version and freeze hash.
- All rows have noun-phrase labels. Every translation records provenance; French, Spanish, Arabic, and Chinese labels are marked `human_review_required`. Ambiguity is currently unassessed, so a null ambiguity flag must not be read as a human-approved translation.

The design matches broad domain and phrase count, but semantic kernels and translated terms remain a substantial source of confounding. Shared morphology and positive emotional valence are not yet empirically controlled. The runner reports raw and per-language-centered embeddings, language-stratified similarities, distinct-concept cross-language pairs, exact-translation positive controls, domain bootstrap intervals, category permutations, and leave-one-language-out results when inference is available.

## Models and encoding

Model IDs and revisions are fixed in `run_experiment.py`. Multilingual E5 uses its documented `query: ` prefix for symmetric similarity; BGE-M3 and LaBSE use their documented sentence-transformer sentence encoding without added prefixes. Embeddings are L2-normalized before cosine calculations. See the [E5 model card](https://huggingface.co/intfloat/multilingual-e5-base), [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3), and [LaBSE model card](https://huggingface.co/sentence-transformers/LaBSE).

## Windows PowerShell

From the repository root, run tests, then local inference:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:SSLKEYLOGFILE = ''
python -m pytest research\cooperative_lexical_geometry_v1\tests -q

python research\cooperative_lexical_geometry_v1\run_experiment.py `
  --model all `
  --batch-size 12
```

The first run needs network access to Hugging Face to fetch the pinned model snapshots; later runs can use the cache. `--local-files-only` prevents downloads and fails promptly if a snapshot is missing. Inference runs on CPU and can take a long time. Outputs are written to `results\` and include normalized embeddings, full raw and centered cosine matrices, plots, per-view results, and SHA-256 hashes.

If using WSL, from the repository root run:

```bash
python3 -m pytest research/cooperative_lexical_geometry_v1/tests -q
python3 research/cooperative_lexical_geometry_v1/run_experiment.py --model all --batch-size 12
```

## Result interpretation gate

Do not report a cooperation-specific effect until (1) target translations have fluent review and ambiguity adjudication, (2) phrase diversity and category matching have been expanded or justified, and (3) lexical overlap, frequency where available, morphology, and valence have been assessed. Even if those gates pass, embedding similarity describes encoder geometry, not behavioral preference in a base language model.
