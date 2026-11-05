# Four-strategy linear-probe analysis

This is a separate, offline analysis of the saved contrastive-mapping activations. It does not modify the original two-strategy report and never loads model weights or performs inference.

## Retrieve and verify the completed real run

From the repository root, retrieve the exact saved run from Modal:

```powershell
modal volume get llm-coop-mechanistic contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9 mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9
```

The local directory must contain `manifest.json`, `prompts.jsonl`, `evidence_hashes.json`, and 496 files under `activations/`. The input inventory is `research/contrastive_full_v1/prompts.jsonl`; its prepared manifest declares 124 scenarios, 496 prompts, 54 template/triad families, 24 domains, 28 layers, and the Qwen2.5-1.5B immutable revision. The analyzer checks the run manifest, exact prompt and activation hashes, strategy completeness, tensor shape, and that real-run inventory before reading results. Do not construct activations from any other source if retrieval fails.

Run the saved-data analysis (CPU only):

```powershell
python -m llm_cooperation.mechanistic.four_strategy_probe `
  --run-dir mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9 `
  --prompts mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9/prompts.jsonl `
  --output reports/four_strategy_probe_real
```

Defaults use 1,000 held-out cluster bootstrap replicates and 100 within-scenario label permutations. Lower these only for a smoke check; record the changed counts.

## Analysis

At every scenario and layer, the four action residual vectors are centered by subtracting their scenario mean. Strategy mean residual directions first average scenarios within a discovery family and then give each family equal weight. One-vs-rest mean directions and a regularized multinomial logistic probe are evaluated across all 28 layers.

The primary outcome is cross-domain direction agreement: a direction estimated with equal weighting across discovery domains is compared with the same strategy's direction estimated independently in each held-out domain. Discovery-domain pairwise cosine consistency and held-out projection margins are reported per strategy and layer, with domain-cluster bootstrap intervals. Strict domain-held-out probe performance is a complementary outcome; no scenarios from held-out domains enter fitting or regularization selection. A separate template/triad-family held-out evaluation tests independent scenario generalization. Regularization `C` is selected with grouped folds restricted to discovery clusters. Balanced accuracy, macro-F1 and one-vs-rest AUROC intervals resample held-out clusters, retaining all scenarios and four actions in each sampled cluster.

Controls include exact within-scenario label permutations, a probe trained on per-vector unit-normalized residuals, residual norm summaries, and action word/character counts. A train-only ridge model also removes the linear association between centered word/character counts and activation vectors before a secondary probe; held-out actions are residualized using that discovery-only fit. This tests linear length-related signal only and cannot eliminate wording or semantic confounds. Direction cosines and effective rank describe the four discovery mean vectors jointly; no orthogonality assumption is made. The JSON contains layerwise OVR projection distributions and all geometry needed for follow-up.

## Interpretation boundary

The analysis tests whether these four presented action descriptions are linearly distinguishable in captured residual-stream activations, and how performance changes over transformer depth. It does not test strategy preference, whether the model uses the measured representations to choose, or whether four distinct causal decision mechanisms exist. The earliest layer with a signal is not a claim about where a representation originates. Lexical-length diagnostics do not remove semantic, tokenization, or prompt-content confounds. Layerwise curves are descriptive; no post-hoc first-detectable-layer claim should be treated as a preregistered localization result.
