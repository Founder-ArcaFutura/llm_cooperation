# Research report: cooperative lexical geometry v1

## Execution outcome (2026-11-06)

The protocol and scripts are prepared, but the requested embedding experiment did **not** execute. The host has CPU-only PyTorch, the requested snapshots are absent from its Hugging Face cache, and the pinned multilingual E5 load failed because the host could not resolve `huggingface.co` (`getaddrinfo failed`). The other two models were not attempted after the shared download blocker was observed. No embeddings or cosine matrices were generated.

Accordingly, the hypothesis result is **undetermined**: this run provides no evidence that cooperation has excess semantic coherence, and no evidence for or against replication across the three models. No controls can be said to survive because no model outcomes exist.

## What is ready

- A pre-inference frozen lexicon of 600 concept IDs: 150 each for cooperation, competition/exploitation, independent action, and neutral activity; 10 domains; five language labels.
- Structural validation and local inference scripts, with pinned model revisions, full cosine matrices, raw and centered views, language-level summaries, distinct-concept cross-language statistics, exact-translation positive controls, domain-cluster intervals, concept-label permutations, category contrasts, and leave-one-language-out summaries.
- Test result: **4 passed** (Windows pytest auto-loading needed to be disabled because of a machine-level SSL key-log path permission problem).

## Provisional design limitations

The 15 phrase kernels within each category are reused across ten domain frames. The language labels were composed by the researcher and have not been reviewed by fluent translators; ambiguity is unassessed. Lexical frequency, shared morphology, and positive emotional valence were not measured. These gaps make the lexicon a pilot scaffold rather than a valid final test of cooperation-specific geometry. Category coherence, even if later high, would describe embedding-space similarity and would not establish behavioral preference in base language models.

## Next execution

Run the PowerShell commands in `README.md` in an environment that can reach Hugging Face. Review translations and expand/validate the lexical sampling before treating resulting estimates as confirmatory. Results will be saved under `results/` only after the pinned local models load and inference completes.
