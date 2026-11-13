"""Audit independent, answer-counterbalanced comprehension probes."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from llm_cooperation.coverage_extension_v6 import OUT, comprehension_presentations
from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, sha, validate_resume


def analyze(paths,output):
    cases_raw=(OUT/'cases.json').read_bytes()
    probe_raw=(OUT/'comprehension_RESTRICTED.jsonl').read_bytes()
    expected=[json.loads(x) for x in probe_raw.decode('utf-8').splitlines() if x.strip()]
    if expected!=list(comprehension_presentations(json.loads(cases_raw))): raise ValueError('Probe bank mismatch')
    groups=defaultdict(list)
    seen_models=set()
    for path in map(Path,paths):
        manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
        summary=json.loads((path/'summary.json').read_text(encoding='utf-8'))
        model=manifest['model']
        if model in seen_models or model not in MODEL_REVISIONS or manifest['revision']!=MODEL_REVISIONS[model]: raise ValueError('Duplicate or mismatched model')
        seen_models.add(model)
        if manifest['scope']!='comprehension' or manifest['cases_sha256']!=sha(cases_raw) or manifest['presentations_sha256']!=sha(probe_raw): raise ValueError('Wrong probe bank')
        if summary['manifest_sha256']!=sha(canonical(manifest)) or summary['status']!='complete': raise ValueError('Incomplete run')
        rows=[json.loads(x) for x in (path/'rows.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        if len(validate_resume(rows,expected))!=len(expected): raise ValueError('Missing probe rows')
        for r in rows:groups[(model,r['question_id'],r['perspective'])].append(r)
    output=Path(output)
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    with (output/'comprehension_summary.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['model','question','perspective','n','unique_n','ties','unique_accuracy','fractional_accuracy','mean_correct_probability','generated_valid','generated_correct']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for (model,question,perspective),rows in groups.items():
            unique=[r for r in rows if len(r['tied_max_letters'])==1]
            fractional=sum(sum(r['letter_to_action'][k]=='correct' for k in r['tied_max_letters'])/len(r['tied_max_letters']) for r in rows)/len(rows)
            prob=sum(sum(r['conditional_probs'][k] for k,v in r['letter_to_action'].items() if v=='correct') for r in rows)/len(rows)
            w.writerow({'model':model,'question':question,'perspective':perspective,'n':len(rows),'unique_n':len(unique),'ties':len(rows)-len(unique),'unique_accuracy':sum(r['forced_action']=='correct' for r in unique)/len(unique) if unique else None,'fractional_accuracy':fractional,'mean_correct_probability':prob,'generated_valid':sum(r['generated_action'] is not None for r in rows),'generated_correct':sum(r['generated_action']=='correct' for r in rows)})
    print(f'Wrote {output}; these are separate closed-choice probes, not direct proof of comprehension.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',nargs='+',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();analyze(a.runs,a.output)


if __name__=='__main__':main()
