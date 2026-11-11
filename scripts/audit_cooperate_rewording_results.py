"""Validate paired experiment artifacts against source text and provenance."""
import hashlib,json,math
from collections import Counter
from pathlib import Path
from llm_cooperation.cooperate_rewording_assay import BANKS,load_items,paired_presentations

root=Path('results/cooperate_rewording')
manifest=json.loads(Path('data/cooperate_rewording_model_manifest.json').read_text(encoding='utf-8-sig'))
expected_models={v['model']:v['revision'] for v in manifest['models']}
banks={b:load_items('data',b) for b in BANKS}
expected={}
for bank,(scenarios,rewrites,hashes) in banks.items():
 for s in scenarios:
  for p in paired_presentations(s,rewrites[s['id']]):
   expected[(bank,s['id'],p['permutation_index'],p['wording'])]=p
seen_models=set(); outputs=[]
for summary in sorted(root.glob('*/summary.json')):
 meta=json.loads(summary.read_text(encoding='utf-8-sig'));model=meta['model']
 if model in seen_models or model not in expected_models: raise ValueError('Unexpected/duplicate model: '+model)
 seen_models.add(model)
 if meta['requested_model_revision'] != expected_models[model] or meta['resolved_model_revision'] != expected_models[model]: raise ValueError('Revision mismatch: '+model)
 for bank in BANKS:
  if meta['banks'][bank] != banks[bank][2]: raise ValueError('Bank provenance mismatch: '+model+' '+bank)
 rows=[];seen=set(); counts=Counter()
 with (summary.parent/'rows.jsonl').open(encoding='utf-8-sig') as f:
  for line in f:
   row=json.loads(line);key=(row['bank'],row['scenario_id'],row['permutation_index'],row['wording'])
   if key in seen or key not in expected: raise ValueError('Unexpected/duplicate row: '+str(key))
   seen.add(key); ref=expected[key]
   for field in ('prompt','letter_to_strategy','template_id','partner_type','context_type','utility_condition','split','triad_id'):
    if row.get(field)!=ref.get(field): raise ValueError('Mismatch '+model+' '+str(key)+' '+field)
   choice=row.get('forced_choice')
   if choice:
    probs=choice['conditional_probabilities']
    if set(probs)!=set(row['letter_to_strategy']) or not math.isclose(sum(probs.values()),1,abs_tol=1e-5): raise ValueError('Probability mismatch '+str(key))
    if choice['strategy']!=row['letter_to_strategy'][choice['letter']]: raise ValueError('Strategy mismatch '+str(key))
    counts['tie' if choice['tied_max_count']>1 else 'untied']+=1
   else: counts['no_token_score']+=1
   counts['valid_generated' if row['generated_strategy'] else 'invalid_generated']+=1
   rows.append(row)
 if seen!=set(expected): raise ValueError('Incomplete rows for '+model)
 if len(rows)!=2432: raise ValueError('Incorrect count for '+model)
 outputs.append({'model':model,'run_id':meta['run_id'],'rows':len(rows),'counts':dict(counts),'rows_sha256':hashlib.sha256((summary.parent/'rows.jsonl').read_bytes()).hexdigest()})
result={'expected_models':len(expected_models),'completed_local_models':len(outputs),'expected_rows_per_model':len(expected),'total_validated_rows':sum(x['rows'] for x in outputs),'missing_models':sorted(set(expected_models)-seen_models),'runs':outputs}
out=Path('research/cooperative_paraphrase_current_audit/run_integrity.json');out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
