# Delayed-mapping instrument pilot v1

This is a separate exploratory instrument, with a new synthetic **draft** bank. It does not edit or load earlier experiment banks/results. Joint action is an operational category, not a moral judgment or always the optimal action. No independent semantic validation is claimed. The non-social condition is a closely matched wording control, not proof of absence of social processing. The eight domain families share a scaffold, limiting generalization even when families are held out.

Plan transport uses exact bytes so Windows CRLF and Linux LF files retain their original SHA-256 hashes. Existing valid plans do not need regeneration for this transport fix. The first failed smoke attempt (`delayed-mapping-84a892762c4f4088b80f09e2b2bf4bbc`) encountered `bank hash mismatch` during remote plan validation, before model loading/inference; the old text transport had normalized CRLF to LF. Preserve that attempt rather than treating it as model evidence. No paid retry is launched by applying the fix.

## Run the smoke first

From the repository root in PowerShell:

```powershell
python -m llm_cooperation.mechanistic.delayed_mapping prepare --output research/delayed_mapping/plans/smoke-v1 --smoke
modal run modal_delayed_mapping.py --plan research/delayed_mapping/plans/smoke-v1 --revision 8faed761d45a263340a0528343f099c05c9a4323 --authorize-paid-run
```

The revision above is the existing recorded **Qwen/Qwen2.5-1.5B base** revision. Model and tokenizer both use that immutable revision. This script has not been remotely executed during implementation. A10G, FP32 by default, four-hour timeout, no automatic retries, **no dollar cap**. Preparing a plan is offline. The second command authorizes a paid run. Review the generated prompts, counts, and resource envelope before executing it. Smoke has 9 scenarios including 3 reading checks, 36 pre-key prefixes, and 288 scored presentations. It is a plumbing/instrument check, not a representation study.

The command prints a unique run ID. Retrieve it without overwriting an existing directory:

```powershell
modal volume get llm-coop-mechanistic <run-id> mechanistic_artifacts/<run-id>
python -m llm_cooperation.mechanistic.delayed_mapping analyze mechanistic_artifacts/<run-id>
```

Optional `--generate` records deterministic full responses (96-token cap), exact-match validity and invalid outputs. Without it, reports describe candidate likelihoods only; validity is **unknown**, not zero invalids. Generation can increase runtime substantially; a truncated response remains invalid. No normalization/coercion into a strategy. HF public Qwen access requires no secret.

Local execution instead:

```powershell
python -m llm_cooperation.mechanistic.delayed_mapping run --plan research/delayed_mapping/plans/smoke-v1 --output mechanistic_artifacts/delayed-local-smoke-v1 --revision 8faed761d45a263340a0528343f099c05c9a4323 --authorize-inference
```

## Full exploratory pilot, after reviewing smoke

```powershell
python -m llm_cooperation.mechanistic.delayed_mapping prepare --output research/delayed_mapping/plans/pilot-v1
modal run modal_delayed_mapping.py --plan research/delayed_mapping/plans/pilot-v1 --revision 8faed761d45a263340a0528343f099c05c9a4323 --authorize-paid-run
# After retrieving that completed run:
python -m llm_cooperation.mechanistic.delayed_mapping fit-probe mechanistic_artifacts/<run-id>
```

Full default: 8 domain families × 4 outcome regimes × 3 counterpart descriptions (human, AI, non-social) = 96 decisions, plus 8 payoff checks. There are 3 discovery, 2 validation, 3 evaluation families. All outcome variants, counterpart variants, action orders and answer mappings in a family stay together. Each item crosses 4 balanced action orders with 4 independent label rotations and 2 response formats: **3,328 scored presentations and 416 pre-key captures**. Two single-token answer formats require 3,744 forward passes for scoring/capture; tokenization is checked, and multi-token answers increase the count. The plan includes a deliberately loose byte-based forward-call bound excluding optional generation. No repeated presentation is an independent scenario.

Use `--formats letters,numbers,actions` during **preparation** to add exact action-text responses (one mapping per action order), or `--all-orders` for all 24 action orders. These change the protocol and compute; use a new plan name. Full action continuations can be long and expensive. Their summed sequence likelihoods have length/wording confounds; they are a transfer diagnostic, not a ground-truth action preference. Labels/numbers can also have tokenization confounds. Every continuation is checked against the exact prompt token boundary; incompatibility fails rather than silently substituting tokens. Scores cover the candidate text without a termination token, not complete-output probabilities. FP32 is the default; `--dtype bfloat16` is an explicitly recorded alternative with quantization limitations. Casting BF16 logits to FP32 does not recover lost precision.

## What is measured

The first prefix includes the situation, complete outcomes and numbered action slots, ending **before** the randomized response key. It still contains action-order information; this design excludes the future key, not every nuisance feature. Prefix text is identical across mappings and formats for an item/order. Residuals after blocks near 25%, 50%, 75% depth are captured at the last prefix token and again immediately before answering. Separate full forwards with no KV cache preserve causal prefix isolation. Compressed arrays are keyed to exact prompts in `presentations.jsonl`; manifest records layers, revision, dtype, source/bank/plan hashes and software versions.

Every action receives its full continuation log probability. The softmax of four such scores is a **conditional candidate score**, not a probability of all possible generated answers. Exact-score ties have no unique winner. `instrument_report.json` reports scenario-level joint-action scores, action-order spread, response-label spread, payoff-reading accuracy, counterpart/outcome/task strata and optional generation invalidity. The overall format average includes controls: use the strata for substantive interpretation. No significance intervals or inflated presentation-level sample size.

The optional ridge probe predicts model-observed joint-action scores from **pre-key** residuals, averaging letters mappings for each prefix. It uses social preference items only. Layer and regularization are selected using validation families, then evaluated on held-out families and other response formats. Comparators include the discovery mean, a payoff-only ridge baseline, a train-vocabulary word-count/length ridge baseline, and five whole-discovery-family target permutations. Baseline regularization uses validation only. Permuted controls use the selected real-probe layer and regularization; they are descriptive controls, not a calibrated permutation p-value. If all families behave identically the family permutations may be uninformative, which the output preserves. It saves coefficients and training normalization in `probe.npz`. Smoke fitting and effectively constant discovery choices are rejected. No architecture weight files are saved.

This initial runnable pilot does **not** establish a cooperation mechanism. The linear fit is a candidate generator; additional nuisance probes and controlled signed interventions/patching remain necessary before causal claims. The same underlying prompt scaffold across families makes the held-out test weaker than a new independently authored game bank. A poor probe or format transfer is a reason to revise the instrument, not automatically scale the model or ablation.

Inspect payoff-check accuracy and failures, invalid generations, label/order spread and cross-format agreement before fitting. Set scientific acceptance thresholds prospectively before interpreting a full pilot; this code does not invent validated thresholds. Preserve failed runs: local writes flush per observation; Modal commits on normal/caught exit, but hard termination can lose uncommitted data. Incomplete runs cannot be summarized as completed evidence. Existing output/plan directories are rejected; no resume/retry is automatic. Existing mechanistic artifacts remain untouched.
