# Six-case feasibility instrument

Status: executable candidate bank, not independently semantically validated or scientifically approved. The bank modifies source wording and omits source domain-role detail in places. Treat as exploratory; source Phase 1 metadata and its contradictory history are preserved in source records, not a prospective holdout claim. Review `review_cards_final.md` before interpreting or running results. Source records, hashes, nominal payoff metadata and annotated consequences are in `sample_bank.json`; the 24-candidate selection remains in `selection_manifest.json`.

Four candidate cases support both perspectives: freight, bit, spectrophotometer and financial audit. Museum and milk are actor-only because original counterpart authority/physical capacity is unclear. The actor AI museum case still assumes participation by a device with unspecified physical ability; the milk AI source has a robot/transport identity inconsistency. Actor-choice uses the model as source decision-maker; recipient-preference uses the model as original counterpart while the other agent controls the original actor's action. Joint actions need partner consent. Acting model is the same model in both perspectives. Human/AI describes the other agent, not a different evaluated model. AI and human are generic in the reconstruction and omit some original occupational detail. The audit case is an actor conflict but the recipient may want the help. The milk competition label is an inherited strategic label even though waste tagging can be the responsible action.

The 160 presentations are 4 paired cases × 2 perspectives × 2 other-agent identities × 2 wordings × 4 rotations = 128, plus 2 actor-only cases × 2 identities × 2 wordings × 4 rotations = 32. Templates, not presentations, are the independent units. No historical-original prompts are included, so this run on its own does not estimate a paired original-versus-revision change. It assesses responses to the revised candidate bank.

Mechanical checks verify exact source hashes, presence of an authority statement and structured consequences, two four-option variants, distinct options and rotation coverage. Pattern checks flag selected role pronouns, transferred agency, beneficiary expressions, asymmetrical evaluative terms and large word-count differences. These are heuristics and cannot prove agency, beneficiary attribution, lexical neutrality, payoff preservation, semantic equivalence, realistic capabilities, or absence of omitted facts. Warnings are reported, not hidden. Every case still needs review; the two variants are candidate paraphrases, not independently verified equivalents. Comparison of identities is complicated by whether the model occupies actor or recipient and by source mismatches. Rendered prompts are in `rendered_prompts.jsonl`; `instrument_audit.json` records the warnings.

## Run locally, without Modal or GPU

From repository root, with a unique run name:

```powershell
python modal_six_case_feasibility.py --run-name dry_001
```

This writes `research/scenario_reconstruction_feasibility/runs/dry_001/prompts.jsonl` and `manifest.json`. It refuses to overwrite an existing run. Tests:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest tests/test_six_case_feasibility.py -q
```

## Paid evaluation, after scientific review

```powershell
modal run modal_six_case_feasibility.py --run-name evaluation_001 --no-dry-run
```

This sends the locally rendered bank to one A10G function. It loads the pretrained base `Qwen/Qwen2.5-3B` at commit `3aab1f1954e9cc14eb9509a215f9e5ca08227a9b`, BF16, with 4 CPU cores and 16 GiB memory. It checks answer-token boundaries for each prompt; records all four letter logits, ties, forced-choice winner, greedy generated text and parsing; writes `prompts.jsonl`, `manifest.json`, and `results.json` beneath the named local run directory. No hidden automatic retry, replacement model, or spending cap is configured. The function has a six-hour execution timeout, a runtime limit rather than a monetary cap. A failed or disconnected run may leave only the prompts and manifest, with no results checkpoint; use a new run name for a retry. This remote path has not yet been exercised on Modal or on the pinned model, so its operational correctness and tokenizer boundary checks are not proven in a live environment.

Modal pricing as checked 2026-11-12: A10 is $0.000306/GPU-second ($1.10/GPU-hour), CPU and memory billed separately: https://modal.com/pricing . A 15–60 minute container is roughly $0.28–$1.10 for GPU alone, plus CPU, memory, possible volume/network charges and tax. Actual runtime is unmeasured; cold weight download and installation can dominate, and actual billing depends on allocated/used resources, credits and plan. This is an illustrative estimate, not a cap. Do not interpret the 160 presentations as independent evidence or pool them without case-level analysis. Report tie and invalid-generation rates, letter-position effects, case-level preferences, and actor/recipient contrasts separately; outcomes remain exploratory and cannot by themselves establish intrinsic preference.
