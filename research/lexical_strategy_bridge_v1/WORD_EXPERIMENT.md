# Word-level capture and analysis plan

Status: **prepared and synthetic-tested; no pretrained word-level GPU capture or empirical word-probe results yet**. The expanded corpus is provisional pending fluent-speaker review. No corpus edits are made. The completed saved-data analysis and historical-probe reconstruction are in `saved_action_analysis/`.

## Inputs and capture

Use the existing frozen inventory: exactly 200 concepts × five translations in the `isolated` condition, one forward pass per entry and model. Do not capture the 1,000 optional bracketed entries as part of this run. Exact model revisions and block indices are in `frozen/manifest.json`. Use FP32, batch size one, eval mode and no generation. Eight post-block residuals are captured at the same blocks as the historical study. For a word split into multiple tokens, the representation is the arithmetic mean of every non-special token whose character offsets overlap the complete lexical span. Token IDs, offsets and selected positions are retained; the last non-special-token residual is also saved as a sensitivity artifact. Inputs that fail span coverage stop the capture. Per-record hashes and a capture identity bind the outputs to the plan. The full analyzer rejects smoke or incomplete receipts. Unexpected partial records are retained for inspection; there is no automatic retry.

## Independent lexical probes

Five stratified concept folds hold out every translation of each test concept. Multilingual training uses only words for training concepts. English-to-French/Chinese/Japanese/Arabic uses only English words from training concepts and tests only the target language on held-out concepts; other-to-target tests each held-out language using the other four languages from training concepts. These are harder concept-disjoint transfer tests, not translation retrieval of a seen concept. Fixed regularization, scaling fitted only to training rows, per-category recall, confusion matrices, and concept-bootstrap intervals are reported. Bootstrap intervals condition on fitted folds and do not include corpus-construction uncertainty. Negative controls use character/token length alone and one concept-level permutation of category labels per fold; the latter is a sanity check, not a calibrated permutation test. Logistic coefficients are saved per fold and depth after conversion back to activation units; individual word predictions should not be treated as model choices.

Geometry comparisons use within-representation centered cosine RSA against the same E5/BGE-M3/LaBSE reference rows, never cross-model hidden-vector dot products. RSA is descriptive and pairwise observations are dependent. The reference row mapping is producer-inferred and was sampled for reproduction; the entire mapping was not independently certified.

## Historical strategy transfer

Historical reports contain raw class-mean strategy directions and per-action predictions. The former have been reconstructed from the evidence and verified. Original fitted logistic coefficients were not serialized. `reconstruct_probes.py` refits each raw probe using its historical chosen C and preprocessing, and accepts a refit only if every historical held-out prediction matches. These matches do not establish bit-identical original coefficients. The word analysis projects each lexical state onto both the saved class-mean and refitted logistic directions within the same model and layer. Before projection it removes the mean of each lexical language. It reports four lexical category means, language-specific means and concept-bootstrap intervals for every direction, without assigning neutral to DISENGAGE. Language centering is a descriptive reference frame, not the historical within-scenario four-action centering. Therefore these projections are relative lexical contrasts, not calibrated original probe scores or demonstrated cross-context transfer. Intercepts are intentionally omitted because they do not affect category contrasts. Original strategy accuracy and semantic comparisons remain in `saved_action_analysis/REPORT.md`.

## Execution after explicit paid-run authorization

Modal is the prepared route because this repository already uses its named evidence volume and the SDK is present. The wrapper has been checked offline but its image, GPU access, provider credentials, model downloads and volume permissions have **not** been verified live. It uses one A100-80GB invocation, a 4-hour function timeout, a 20-minute smoke subprocess limit, a unique immutable output tag, and explicit inference and paid-run flags. No cloud staging, deployment, or GPU work has run. Model download time and provider billing are not yet measured, so obtain a budget and explicit authorization before any smoke.

Each separate command requires authorization. A smoke processes ten isolated entries; it does not trigger a full run. Example for Qwen after authorization:

```powershell
modal run modal_lexical_word_capture.py --model qwen --action smoke --tag qwen-smoke-01 --authorize-inference --authorize-paid-run
```

Inspect the receipt, token offsets, model compatibility, runtime, actual cost and durable evidence before a separately authorized full run. For example, after that separate authorization:

```powershell
modal run modal_lexical_word_capture.py --model qwen --action full --tag qwen-full-01 --authorize-inference --authorize-paid-run --authorize-full-capture
```

Repeat independently for `olmo7b` and `mistral7b`, using unique tags. Captures live under `/lexical_words_v1/{model}_{action}_{tag}/capture` in the existing `llm-cooperation-cross-model-v1` volume. Download a full capture without overwriting an existing local directory, then run:

```powershell
python research/lexical_strategy_bridge_v1/analyze_words.py --model qwen --capture PATH_TO_DOWNLOADED_CAPTURE --output PATH_TO_NEW_ANALYSIS
```

The analyzer checks the frozen plan, receipt, revision, every record's identity and hash, array shape and finiteness before analysis. Capture and analysis code, exact environment and output manifests should be retained alongside results. Failure or interrupted runs must remain preserved and require manual inspection; no automatic reuse or retry is authorized.
