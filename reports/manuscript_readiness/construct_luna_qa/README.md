# Independent Luna QA scaffold

This is a prepared pilot, not completed QA. It asks Luna to classify one field at a time without seeing Qwen's answer or historical model outcomes, then compares Luna's answer with Qwen locally. Qwen's records remain unchanged. An exact quotation match establishes only that words appear in the text; it does not establish that a judgment is supported. Model agreement is not human validation.

## Pilot selection and scope

`pilot_20261112` contains a seeded development set of 10 previously flagged or reviewed packets and a held-out set of 30 packets selected across the three source banks. Each packet has two scenario variants and two wordings; seven fields produce 280 and 840 requests respectively. The held-out selection excludes packet IDs documented in `construct_v1_qa_round2_ledger.json`, the known customs case and symmetric controls. It does not prove freedom from all previous exposure. Selection is balanced by bank where possible, not a representative sample of the corpus or of all labels. Treat it as a pilot; don't extrapolate its agreement rate to the entire bank.

There is no validated human gold set in these files. Reviewers should separately compare a stratified sample of agreements and disagreements against scenario text, including known errors and examples that appear correct, before making reliability claims. Missing quotes are flagged for review; an `unclear` answer may legitimately lack a quotation. The scaffold does not automatically declare Qwen correct, adjudicate discrepancies, reclassify scenarios, or join QA judgments to behavioral outcomes.

## Steps

From PowerShell in the repository root, the prepared files may be inspected without making an API call:

```powershell
Set-Location G:\llm_cooperation
Get-Content reports\manuscript_readiness\construct_luna_qa\pilot_20261112\manifest.json
Get-Content reports\manuscript_readiness\construct_luna_qa\pilot_20261112\development.jsonl -TotalCount 1
```

The following submits scenario text to OpenAI and incurs API charges. Submit development first; review its results and the prompt before choosing whether to submit the held-out set. The current script reads `OPENAI_API_KEY` from the process environment through the OpenAI Python SDK; an existing key stored only in an env file needs to be loaded into that environment by the user's normal secure process. No key is copied or written by this scaffold.

```powershell
$qa = 'reports\manuscript_readiness\construct_luna_qa\pilot_20261112'
python scripts\construct_luna_qa.py submit --out $qa --cohort development
python scripts\construct_luna_qa.py status BATCH_ID
python scripts\construct_luna_qa.py download BATCH_ID --out $qa --cohort development
python scripts\construct_luna_qa.py import --out $qa --cohort development --output "$qa\development_output.jsonl"
python scripts\construct_luna_qa.py review-sheet --out $qa --cohort development --per-group 20
```

Replace `BATCH_ID` with the returned ID. If an errors file is downloaded, add `--errors "$qa\development_errors.jsonl"` to the import command. Use `heldout` in place of `development` only when ready to run that cohort. `download` accepts terminal completed, expired, failed, or cancelled batches; if no output file exists, inspect the downloaded errors file and submission status. Import reports absent IDs and failed requests rather than treating them as successes. A submission record prevents accidental repeat submission; if the network fails after submission but before the returned batch ID is saved, check the OpenAI dashboard before taking any further action because the operation may have succeeded remotely.

The review-sheet command samples both agreement and disagreement cases across fields for manual adjudication; the resulting sheet contains both model answers and is therefore not blind to those answers. For independent gold review, have reviewers first annotate the source material without seeing either answer, then compare their judgments with this sheet. The sample is diagnostic, not prevalence-weighted.

To prepare a new, separate run (never overwrite an existing nonempty output directory):

```powershell
python scripts\construct_luna_qa.py prepare --out reports\manuscript_readiness\construct_luna_qa\new_pilot --seed 20261112 --dev-count 10 --heldout-count 30 --effort low
```

The `low` setting is an initial choice, not evidence of adequate quality. No fixed monetary spending cap is implemented. Batch files include scenario text and use the Responses API with `gpt-6-luna`; each line is one field. Usage including output/reasoning tokens is recorded where returned, and estimates should be revised from observed usage. Batch submission/retrieval has not been exercised live. See [Batch API documentation](https://developers.openai.com/api/docs/guides/batch) and [Luna pricing](https://developers.openai.com/api/docs/models/gpt-6-luna).
