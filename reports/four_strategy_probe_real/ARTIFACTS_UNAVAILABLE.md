# Four-strategy real-run analysis status

No real-model analysis is reported here. The local workspace has the prepared expected inventory at `research/contrastive_full_v1/` (124 scenarios, 496 prompts, 54 template/triad families, 24 domains; Qwen/Qwen2.5-1.5B revision `8faed761d45a263340a0528343f099c05c9a4323`) but does not contain activation artifacts for `contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9`.

A read-only `modal volume get` attempt was issued for the requested run and did not return output within 30 seconds. It was interrupted. This establishes an access/tooling blocker, not that the run is absent from the Modal volume. No inference, GPU job, or synthetic substitution was performed for the scientific analysis.

Retrieve the existing run from the repository root:

```powershell
modal volume get llm-coop-mechanistic contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9 mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9
```

After retrieval succeeds, run:

```powershell
python -m llm_cooperation.mechanistic.four_strategy_probe `
  --run-dir mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9 `
  --prompts mechanistic_artifacts/contrastive-mapping-9ba6be347e1643c6ad01ad72b3a3e1b9/prompts.jsonl `
  --output reports/four_strategy_probe_real
```

The command checks the saved run against the prepared expected prompt inventory and plan manifest, complete activation inventory, model/revision provenance, `[28,1536]` tensor dimensions, and SHA-256 evidence index before analyzing. It writes layerwise probe and geometry figures plus JSON and Markdown reports. If retrieval continues to stall, run these same read-only volume commands in an environment with an authenticated Modal profile; do not create replacement activations.
