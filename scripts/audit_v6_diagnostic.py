"""Read-only reanalysis of frozen v6 diagnostic; no model calls."""
import csv
import json
from collections import defaultdict
from pathlib import Path

from llm_cooperation.coverage_extension_v6 import OUT, verify_freeze
from llm_cooperation.factorial_inference import MODEL_REVISIONS, canonical, sha, validate_resume

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'results/coverage_extension_v6/capture_20261113_140618'
OUTPUT=ROOT/'reports/coverage_extension_v6/offline_diagnostic_audit'


def main():
    verify_freeze()
    choice_raw=(OUT/'presentations.jsonl').read_bytes()
    probe_raw=(OUT/'comprehension_RESTRICTED.jsonl').read_bytes()
    cases_raw=(OUT/'cases.json').read_bytes()
    expected={name:[json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()] for name,raw in [('choice',choice_raw),('probe',probe_raw)]}
    paired=[];probe_counts=defaultdict(int);probe_probs=defaultdict(list);manifest=[]
    for alias,model in [('qwen7b','Qwen/Qwen2.5-7B'),('olmo7b','allenai/OLMo-2-1124-7B'),('mistral7b','mistralai/Mistral-7B-v0.3')]:
        for kind,suffix,raw in [('choice','',choice_raw),('probe','_comprehension',probe_raw)]:
            folder=SOURCE/f'coverage_extension_v6_{alias}{suffix}'
            m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            s=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
            raw_results=(folder/'rows.jsonl').read_bytes()
            rows=[json.loads(x) for x in raw_results.decode('utf-8').splitlines() if x.strip()]
            if m['model']!=model or m['revision']!=MODEL_REVISIONS[model] or m['cases_sha256']!=sha(cases_raw) or m['presentations_sha256']!=sha(raw) or s['manifest_sha256']!=sha(canonical(m)):raise ValueError('provenance mismatch')
            if len(validate_resume(rows,expected[kind]))!=s['completed'] or s['status']!=('complete' if kind=='probe' else 'diagnostic_complete'):raise ValueError('incomplete')
            manifest.append({'model':model,'kind':kind,'n':len(rows),'rows_sha256':sha(raw_results),'manifest_sha256':sha(canonical(m))})
            if kind=='probe':
                for r in rows:
                    response=r['options'].get(r['forced_letter'],'TIE')
                    key=(model,r['question_id'],r['perspective'],response)
                    probe_counts[key]+=1
                    probe_probs[key[:3]].append(sum(r['conditional_probs'][k] for k,v in r['letter_to_action'].items() if v=='correct'))
            else:
                groups=defaultdict(dict)
                for r in rows:
                    f=r['factors']
                    if r['block']!='benefit_cost' or f['choice_set'] not in ('binary','three_action'):continue
                    key=(r['family_id'],f['actor_benefit'],f['counterpart_benefit'],f['choice_set'],r['perspective'],r['actor_identity'],r['counterpart_identity'],tuple(r['letter_to_action'].items()))
                    groups[key][f['cost']]=r
                for k,g in groups.items():
                    if set(g)!={0,20}:raise ValueError('incomplete cost pair')
                    low,high=g[0],g[20]
                    letter=next(x for x,v in low['letter_to_action'].items() if v=='send')
                    ref=next(x for x,v in low['letter_to_action'].items() if v=='retain')
                    paired.append({'model':model,'family':k[0],'actor_benefit':k[1],'counterpart_benefit':k[2],'choice_set':k[3],'perspective':k[4],'actor_identity':k[5],'counterpart_identity':k[6],'target_letter':letter,'low_presentation_id':low['presentation_id'],'high_presentation_id':high['presentation_id'],'delta_target_probability':high['conditional_probs'][letter]-low['conditional_probs'][letter],'delta_target_logit':high['raw_logits'][letter]-low['raw_logits'][letter],'delta_reference_logit':high['raw_logits'][ref]-low['raw_logits'][ref],'delta_target_full_vocab_logprob':high['full_vocab_logprobs'][letter]-low['full_vocab_logprobs'][letter]})
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with (OUTPUT/'cost_pairs.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
    with (OUTPUT/'probe_answer_counts.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['model','question','perspective','selected_text','count','mean_correct_probability']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for (model,question,perspective,response),count in sorted(probe_counts.items()):
            v=probe_probs[(model,question,perspective)]
            w.writerow(dict(zip(fields,[model,question,perspective,response,count,sum(v)/len(v)])))
    (OUTPUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Validated {len(manifest)} runs; wrote {len(paired)} matched cost-presentation pairs to {OUTPUT}')


if __name__=='__main__':main()
