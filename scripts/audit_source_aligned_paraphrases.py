#!/usr/bin/env python3
"""Structural and lexical audit of manually reworded COOPERATE choices.

Run from the repository root or provide --repo-root. The checks DO NOT certify
semantic equivalence: a human/domain expert must inspect action meaning.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import defaultdict,Counter
from pathlib import Path
STOPWORDS=set('a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was wasn we were what when where which while who whom why with you your yours yourself yourselves'.split())
BANKS={
 'phase0':('scenarios_v1_expanded.json',120),
 'phase0b':('scenarios_phase0b_utility_matched.json',124),
 'phase1':('scenarios_phase1_prospective.json',60),
}
def content_words(s):return set(x for x in re.findall('[a-zA-Z]+',s.lower()) if len(x)>1 and x not in STOPWORDS)
def overlap(a,b):
 a=content_words(a);b=content_words(b)
 return len(a&b)/len(a) if a else 0

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.',help='Root directory containing data/')
 ap.add_argument('--outdir',default='research/cooperative_paraphrase_repair')
 args=ap.parse_args();root=Path(args.repo_root).resolve();data=root/'data';out=root/args.outdir;out.mkdir(parents=True,exist_ok=True)
 records=[];warnings=[]
 for bank,(filename,n) in BANKS.items():
  source=data/filename; para=data/f'choice_set_cooperate_paraphrases_{bank}.json'
  if not source.exists() or not para.exists(): raise SystemExit(f'Missing file: {source} or {para}')
  sourcebytes=source.read_bytes();sourcej=json.loads(sourcebytes.decode('utf-8-sig'));paraj=json.loads(para.read_text(encoding='utf8'))
  actual_hash=hashlib.sha256(sourcebytes).hexdigest()
  if actual_hash!=paraj['source_sha256']:
   warnings.append(f'{bank}: source byte-hash differs from inherited metadata ({actual_hash} vs {paraj["source_sha256"]}); may reflect line endings or source changes. Review before interpreting.')
  src=sourcej['scenarios'];items=paraj['paraphrases'];assert len(src)==len(items)==n,bank
  ids=[x['id'] for x in src];pids=[x['scenario_id'] for x in items]
  assert ids==pids, f'{bank}: source and paraphrase scenario ID/order mismatch'
  assert len(set(ids))==n
  for s,p in zip(src,items):
   assert s['options']['COOPERATE']==p['original_cooperate'],f'Action text mismatch: {bank} {s["id"]}'
   assert s.get('template_id')==p.get('template_id') and s.get('partner_type')==p.get('partner_type')
   assert p['paraphrased_cooperate']!=p['original_cooperate'] and p['paraphrased_cooperate'].strip()
   assert '{P}' not in p['paraphrased_cooperate']
   records.append({
    'bank':bank,'scenario_id':s['id'],'template_id':s.get('template_id'),'partner_type':s.get('partner_type'),
    'context_type':s.get('context_type'),'utility_condition':s.get('utility_condition'),'split':s.get('split'),
    'source_sha256_actual':actual_hash,
    'original_cooperate':p['original_cooperate'],'paraphrased_cooperate':p['paraphrased_cooperate'],
    'original_stem_overlap':round(overlap(p['original_cooperate'],s['stem']),5),
    'paraphrase_stem_overlap':round(overlap(p['paraphrased_cooperate'],s['stem']),5),
    'independent_stem_overlap':round(overlap(s['options']['INDEPENDENT'],s['stem']),5),
    'original_word_count':len(p['original_cooperate'].split()),
    'paraphrase_word_count':len(p['paraphrased_cooperate'].split()),
    'flag_for_review':p.get('flag_for_review',False),
    'review_warning':p.get('validation_warning') or '',
    'semantic_equivalence_status':p.get('semantic_validation_status','NOT_VALIDATED')
   })
 assert len(records)==304
 for r in records:r['stem_overlap_reduction']=round(r['original_stem_overlap']-r['paraphrase_stem_overlap'],5)
 with (out/'lexical_audit_v2.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 summary={'total_records':len(records),'validation_disclaimer':'Structural and lexical check only; no automatic semantic certification. All records pending independent review.','warnings':warnings,'by_bank':{}}
 for bank in BANKS:
  rr=[r for r in records if r['bank']==bank]
  summary['by_bank'][bank]={
   'count':len(rr),'flagged_for_review':sum(bool(r['flag_for_review']) for r in rr),
   'mean_original_stem_overlap':round(sum(r['original_stem_overlap'] for r in rr)/len(rr),5),
   'mean_paraphrase_stem_overlap':round(sum(r['paraphrase_stem_overlap'] for r in rr)/len(rr),5),
   'mean_overlap_reduction':round(sum(r['stem_overlap_reduction'] for r in rr)/len(rr),5),
   'items_overlap_reduced':sum(r['stem_overlap_reduction']>0 for r in rr),
   'items_overlap_unchanged':sum(r['stem_overlap_reduction']==0 for r in rr),
   'items_overlap_increased':sum(r['stem_overlap_reduction']<0 for r in rr),
  }
 (out/'lexical_audit_v2_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
 print(json.dumps(summary,indent=2))
 if warnings: print('NOTE: Source-byte hash warnings found; inspect summary before treating source provenance as confirmed.')
if __name__=='__main__':main()
