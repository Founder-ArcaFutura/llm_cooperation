# Lexical-to-strategy bridge: initial scaffold

Status: **preparation and capture prototype only; no lexical LLM measurements or scientific conclusions**. The 200-concept corpus is provisional pending independent linguistic review. The original cohort named `confirmatory` is retained verbatim for provenance, but this experiment is exploratory.

## Local audit

`frozen/manifest.json` records the actual input bytes, canonical Git-LF source hash, exact model revisions and eight historical block locations, plus hashes of the locally available exploratory embedding files. Source identity agrees with the frozen manifest after CRLF-to-LF normalization; the actual CRLF bytes agree with the embedding summaries. Embedding dimensions, finiteness, unit normalization and both cosine matrices were checked. The producer specifies concept-major, en/fr/zh/ja/ar ordering, but the saved arrays contain no independent row identity record; their ordering and short LaBSE revision remain provenance limitations. The untracked embedding files remain in their original directory and are not included here.

Historical full-run manifests identify the requested base models and FP32, with 496 prompt activations per model. Every file listed in each evidence index matches its hash. The index's canonical LF bytes, but not local CRLF bytes, match the manifest. The existing strict loader also rejects the present checkout's code fingerprint; no historical files were changed. Original fitted model weights have not been located or reconstructed, and historical metrics have not been reproduced. The old analyses use scenario-centered features, which do not have an obvious direct counterpart for individual lexical items. Probe transfer therefore needs a predeclared centering sensitivity analysis; neutral lexical concepts are not the DISENGAGE class.

## Input protocol

Both conditions use the same 1,000 words. Isolated input is the word; neutral input is `[ word ]`, identical punctuation across languages. The capture prototype records character offsets, full model token IDs and token offsets, the mean of post-block hidden states overlapping the lexical character span, and the last non-special text position. It uses FP32, batch size one, no generation, eight historical blocks, and exact revisions. Bracket punctuation and causal ordering can affect contextual measurements and should be reported. The neutral final state includes the closing bracket; the lexical span does not.

## Prepare and run on a CUDA host

From the repository root in PowerShell (copy the repository, its frozen plan, and the script to the host first):

```powershell
python research/lexical_strategy_bridge_v1/prepare.py --output research/lexical_strategy_bridge_v1/frozen
python research/lexical_strategy_bridge_v1/capture.py --plan research/lexical_strategy_bridge_v1/frozen --model qwen --output D:/lexical-bridge/qwen-smoke --limit 10
python research/lexical_strategy_bridge_v1/capture.py --plan research/lexical_strategy_bridge_v1/frozen --model olmo7b --output D:/lexical-bridge/olmo-smoke --limit 10
python research/lexical_strategy_bridge_v1/capture.py --plan research/lexical_strategy_bridge_v1/frozen --model mistral7b --output D:/lexical-bridge/mistral-smoke --limit 10
```

`D:/lexical-bridge` is an example persistent disk and must exist on the host; CUDA, compatible PyTorch/Transformers and model access must be installed. Smoke receipts report total elapsed time including model load and peak allocated CUDA memory. They do not yet isolate per-record time or calculate a reliable full-run cost. Review model access, resources and actual timings before full capture. A full capture uses a **separate output directory** and omits `--limit`. Resume revalidates each completed record hash; an interruption between writing its tensor and metadata leaves an orphan requiring manual inspection and recovery. Copy outputs to durable storage; no Modal adapter or automatic remote staging has been implemented.

## Remaining work

Real-weight GPU smoke and full capture, robust automated recovery, environment pinning and cost estimation, audited probe reconstruction and metric reproduction, RSA with concept-level uncertainty and restricted controls, projection and sensitivity analyses, figures, scientific report, and PR are all pending. This prototype has not been tested against real pretrained weights or a GPU and is not yet a complete execution pipeline. Direct cosine comparisons across different model vector spaces are invalid. Any eventual alignment supports a transfer interpretation, not behavioral selection or a causal circuit.
