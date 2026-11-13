"""Prepare and inspect outcome-blind Luna Batch QA without changing Qwen labels."""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKETS=ROOT/'reports/manuscript_readiness/adjudication_template_packets/all_152_blinded_packets.json'
KEY=ROOT/'reports/manuscript_readiness/adjudication_template_packets/INTERNAL_UNBLINDING_KEY.json'
QWEN=ROOT/'reports/manuscript_readiness/construct_qwen32b/construct-v1-8388c1e11b29c524.json'
LEDGER=ROOT/'construct_v1_qa_round2_ledger.json'
MODEL='gpt-6-luna'
FIELDS={
 'interaction':('Which interaction types are supported by the TARGET action in this scenario? Select all supported; use unclear if none can be established.', ['joint_task','timing_coordination','parallel_activity','unilateral_help','resource_sharing','information_sharing','exchange','other','unclear']),
 'interdependence':('For the TARGET action, assess whether contribution by multiple agents is necessary, beneficial but not necessary, absent, or unclear. Do not infer benefit or necessity from mere simultaneity.', ['necessary','beneficial_not_necessary','absent','unclear']),
 'goal_structure':('Are the goals of actor and counterpart shared, compatible but distinct, conflicting, unrelated, or unclear?', ['shared','compatible_distinct','conflicting','unrelated','unclear']),
 'actor_outcome':('Compare the TARGET with the REFERENCE for the actor. Use equal only when a comparable overall outcome is established; if dimensions are missing or mixed use unclear.', ['target_better','equal','reference_better','unclear']),
 'recipient_outcome':('Compare the TARGET with the REFERENCE for the counterpart. Use equal only when a comparable overall outcome is established; if dimensions are missing or mixed use unclear.', ['target_better','equal','reference_better','unclear']),
 'actor_cost':('Relative to the REFERENCE, does the TARGET have no stated actor cost, an opportunity cost, a realized cost, or uncertain cost? A missing stated cost is not evidence that no cost exists.', ['none_stated','opportunity_cost','realized_cost','uncertain']),
 'lexical_favor':('Considering wording and pragmatic framing, does the wording favor the TARGET or REFERENCE, appear balanced, or remain unclear? A stated benefit alone does not prove bias.', ['target','reference','balanced','unclear']),
}
SYSTEM=('You are reviewing a research scenario without access to prior ratings or behavioral outcomes. '
        'The actor is the scenario decision-maker; the counterpart is the other participant. '
        'Third-person narration may describe the decision-maker. Use only the supplied scenario and alternatives. '
        'Distinguish explicit statements from inference; do not invent facts, costs, or benefits. '
        'Provide exact quotations copied from the specified source fields. If the answer is uncertain, say so.')

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(value): return hashlib.sha256(value.encode('utf-8')).hexdigest()

def select_packets(key, ledger, seed, dev_count, heldout_count):
    old=set(ledger['scope']['previously_reviewed_packet_ids'])
    old.update(x['packet_id'] for x in ledger['new_diagnostic_sample'])
    old.add('RV-760143')
    old.update(p['packet_id'] for p in key if any(r.get('is_symmetric_control') for r in p['source_rows']))
    rng=random.Random(seed)
    dev=[p for p in key if p['packet_id'] in old]
    rng.shuffle(dev)
    held=[p for p in key if p['packet_id'] not in old]
    buckets=defaultdict(list)
    for p in held: buckets[p['source_bank']].append(p)
    for values in buckets.values(): rng.shuffle(values)
    chosen=[]
    while len(chosen)<heldout_count and any(buckets.values()):
        for bank in sorted(buckets):
            if buckets[bank] and len(chosen)<heldout_count: chosen.append(buckets[bank].pop())
    if len(dev)<dev_count or len(chosen)<heldout_count: raise ValueError('Insufficient distinct packets')
    return {'development':[p['packet_id'] for p in dev[:dev_count]],'heldout':[p['packet_id'] for p in chosen]}

def request_for(packet, variant, wording, field, effort):
    s=packet['scenario_'+variant]
    source={'scenario':s['scenario_stem'],'target':s['cooperative_wording_'+str(wording)],'reference':s['independent_action']}
    question,choices=FIELDS[field]
    prompt='SCENARIO:\n'+source['scenario']+'\n\nTARGET:\n'+source['target']+'\n\nREFERENCE:\n'+source['reference']+'\n\nQUESTION: '+question
    schema={'type':'object','additionalProperties':False,'required':['answers','evidence','explanation'],
      'properties':{'answers':{'type':'array','items':{'type':'string','enum':choices}},
        'evidence':{'type':'array','items':{'type':'object','additionalProperties':False,'required':['source','quote'],
            'properties':{'source':{'type':'string','enum':['scenario','target','reference']},'quote':{'type':'string'}}}},
        'explanation':{'type':'string'}}}
    cid=f'{packet["packet_id"]}_{variant}_w{wording}_{field}'
    body={'model':MODEL,'reasoning':{'effort':effort},'input':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
          'text':{'format':{'type':'json_schema','name':'construct_qa','strict':True,'schema':schema}}}
    return {'custom_id':cid,'method':'POST','url':'/v1/responses','body':body},source

def prepare(out,seed,dev_count,heldout_count,effort):
    if out.exists() and any(out.iterdir()): raise FileExistsError('Output directory is not empty')
    packets=read(PACKETS); key=read(KEY); qwen=read(QWEN); ledger=read(LEDGER)
    if qwen['input_sha256']!=sha(PACKETS): raise ValueError('Qwen packet hash mismatch')
    by_id={p['packet_id']:p for p in packets}; reviews={r['id']:r['review'] for r in qwen['records']}
    if len(by_id)!=152 or len(reviews)!=304: raise ValueError('Unexpected input counts')
    selection=select_packets(key,ledger,seed,dev_count,heldout_count)
    if set(selection['development']) & set(selection['heldout']): raise ValueError('Overlapping selections')
    out.mkdir(parents=True,exist_ok=True); manifests={}
    for cohort,ids in selection.items():
        requests=[]; mapping={}
        for pid in ids:
            for variant in ('A','B'):
                for w in (1,2):
                    for field in FIELDS:
                        request,source=request_for(by_id[pid],variant,w,field,effort)
                        cid=request['custom_id']; requests.append(request)
                        mapping[cid]={'packet_id':pid,'variant':variant,'wording':w,'field':field,'source':source,
                                      'qwen_label':reviews[pid+'_'+variant]['wording_'+str(w)][field]}
        path=out/(cohort+'.jsonl')
        path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in requests),encoding='utf-8')
        dump(out/(cohort+'_mapping.json'),mapping)
        manifests[cohort]={'packets':ids,'requests':len(requests),'request_sha256':sha(path),'mapping_sha256':sha(out/(cohort+'_mapping.json'))}
    dump(out/'manifest.json',{'protocol':'luna-independent-qa-v1','model':MODEL,'reasoning_effort':effort,'seed':seed,
       'sources':{p.name:sha(p) for p in (PACKETS,KEY,QWEN,LEDGER)},'cohorts':manifests,
       'warning':'Held-out excludes documented prior review; other prior exposure cannot be excluded. No human gold labels supplied.'})
    print('Prepared:',', '.join(f'{k}={v["requests"]} requests' for k,v in manifests.items()))

def import_results(out,cohort,output_file,error_file=None):
    manifest=read(out/'manifest.json')['cohorts'][cohort]
    if sha(out/(cohort+'.jsonl'))!=manifest['request_sha256'] or sha(out/(cohort+'_mapping.json'))!=manifest['mapping_sha256']: raise ValueError('Input or mapping changed')
    mapping=read(out/(cohort+'_mapping.json')); seen=set(); results=[]
    for file in [output_file,error_file]:
        if not file: continue
        for line in file.read_text(encoding='utf-8').splitlines():
            row=json.loads(line); cid=row.get('custom_id')
            if cid not in mapping or cid in seen: raise ValueError(f'Unexpected or duplicate custom_id {cid}')
            seen.add(cid); meta=mapping[cid]; item={'custom_id':cid,'qwen_label':meta['qwen_label'],'field':meta['field']}
            response=row.get('response') or {}; body=response.get('body') or {}
            item['usage']=body.get('usage'); item['status']='error'; item['error']=row.get('error')
            try:
                if response.get('status_code')!=200 or body.get('status')!='completed': raise ValueError('non-successful or incomplete response')
                contents=[c for o in body.get('output',[]) if o.get('type')=='message' for c in o.get('content',[])]
                text=[c['text'] for c in contents if c.get('type')=='output_text']
                if len(text)!=1: raise ValueError('missing output text or refusal')
                answer=json.loads(text[0]); vals=answer['answers']; choices=FIELDS[meta['field']][1]
                if not isinstance(vals,list) or not vals or len(vals)!=len(set(vals)) or any(v not in choices for v in vals): raise ValueError('invalid answer')
                if meta['field']!='interaction' and len(vals)!=1: raise ValueError('expected exactly one answer')
                if 'unclear' in vals and len(vals)>1: raise ValueError('unclear combined with another answer')
                evidence=answer['evidence']; invalid=[e for e in evidence if e.get('source') not in meta['source'] or not e.get('quote') or e['quote'] not in meta['source'][e['source']]]
                q=meta['qwen_label']; q=q if isinstance(q,list) else [q]
                item.update({'status':'review_needed' if invalid or not evidence else 'format_valid', 'luna':answer,
                             'invalid_evidence':invalid,'agreement':set(q)==set(vals)})
            except (KeyError,ValueError,TypeError,json.JSONDecodeError) as exc: item['error']=str(exc)
            results.append(item)
    missing=sorted(set(mapping)-seen)
    dest=out/(cohort+'_qa_results.json')
    if dest.exists(): raise FileExistsError(dest)
    dump(dest,{'warning':'Model agreement and exact quotation matches are not human validation.','results':results,'missing_custom_ids':missing,
               'summary':{'expected':len(mapping),'received':len(seen),'missing':len(missing),'statuses':dict(Counter(r['status'] for r in results))}})
    print('Imported',len(seen),'of',len(mapping),'requests;',len(missing),'missing; saved',dest)

def client():
    try: from openai import OpenAI
    except ImportError: raise SystemExit('Install the OpenAI Python SDK in your environment to submit or retrieve a batch.')
    return OpenAI()

def review_sheet(out,cohort,per_group,seed):
    report=read(out/(cohort+'_qa_results.json')); mapping=read(out/(cohort+'_mapping.json'))
    groups=defaultdict(list)
    for row in report['results']:
        if row['status'] in ('format_valid','review_needed'):
            groups['agreement' if row['agreement'] else 'disagreement'].append(row)
    rng=random.Random(seed); selected=[]
    for group in ('agreement','disagreement'):
        items=groups[group][:]; rng.shuffle(items)
        # Cycle fields so one frequent field cannot dominate the review sample.
        by_field=defaultdict(list)
        for item in items: by_field[item['field']].append(item)
        picked=[]
        while len(picked)<per_group and any(by_field.values()):
            for field in sorted(by_field):
                if by_field[field] and len(picked)<per_group: picked.append(by_field[field].pop())
        for row in picked:
            meta=mapping[row['custom_id']]
            selected.append({'custom_id':row['custom_id'],'sample_group':group,'field':row['field'],'source':meta['source'],
                             'qwen_label':row['qwen_label'],'luna':row['luna'],
                             'qwen_human_verdict':'','luna_human_verdict':'','human_evidence':'','notes':''})
    dest=out/(cohort+'_human_review.json')
    if dest.exists(): raise FileExistsError(dest)
    dump(dest,{'instruction':'Assign supported, contradicted, not_established, or unresolved independently to each label. Blank means not reviewed.',
               'seed':seed,'sampling':'Field-balanced within agreement/disagreement; nonrepresentative diagnostic sample.', 'items':selected})
    print('Prepared',len(selected),'human-review rows:',dest)

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--out',type=Path,required=True); p.add_argument('--seed',type=int,default=20261112); p.add_argument('--dev-count',type=int,default=10); p.add_argument('--heldout-count',type=int,default=30); p.add_argument('--effort',choices=['none','low','medium','high','xhigh','max'],default='low')
    p=sub.add_parser('submit'); p.add_argument('--out',type=Path,required=True); p.add_argument('--cohort',choices=['development','heldout'],required=True)
    p=sub.add_parser('status'); p.add_argument('batch_id')
    p=sub.add_parser('download'); p.add_argument('batch_id'); p.add_argument('--out',type=Path,required=True); p.add_argument('--cohort',choices=['development','heldout'],required=True)
    p=sub.add_parser('import'); p.add_argument('--out',type=Path,required=True); p.add_argument('--cohort',choices=['development','heldout'],required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--errors',type=Path)
    p=sub.add_parser('review-sheet'); p.add_argument('--out',type=Path,required=True); p.add_argument('--cohort',choices=['development','heldout'],required=True); p.add_argument('--per-group',type=int,default=20); p.add_argument('--seed',type=int,default=20261112)
    a=ap.parse_args()
    if a.cmd=='prepare':
        if a.dev_count<0 or a.heldout_count<0 or a.dev_count+a.heldout_count==0: raise ValueError('Invalid sample sizes')
        prepare(a.out,a.seed,a.dev_count,a.heldout_count,a.effort)
    elif a.cmd=='submit':
        record=a.out/(a.cohort+'_submission.json')
        if record.exists(): raise FileExistsError('Submission record exists; inspect it before resubmitting')
        manifest=read(a.out/'manifest.json')['cohorts'][a.cohort]; path=a.out/(a.cohort+'.jsonl')
        if sha(path)!=manifest['request_sha256']: raise ValueError('Request file changed')
        c=client()
        with path.open('rb') as f: uploaded=c.files.create(file=f,purpose='batch')
        dump(record,{'input_file_id':uploaded.id,'state':'uploaded_not_confirmed_submitted','request_sha256':sha(path)})
        batch=c.batches.create(input_file_id=uploaded.id,endpoint='/v1/responses',completion_window='24h')
        dump(record,{'input_file_id':uploaded.id,'batch_id':batch.id,'state':batch.status,'request_sha256':sha(path)})
        print('Submitted batch',batch.id)
    elif a.cmd=='status':
        b=client().batches.retrieve(a.batch_id); print(json.dumps({'id':b.id,'status':b.status,'request_counts':b.request_counts.model_dump() if b.request_counts else None,'output_file_id':b.output_file_id,'error_file_id':b.error_file_id},indent=2))
    elif a.cmd=='download':
        record=read(a.out/(a.cohort+'_submission.json'))
        if record.get('batch_id')!=a.batch_id: raise ValueError('Batch does not match submission record')
        c=client(); b=c.batches.retrieve(a.batch_id)
        if b.status not in ('completed','failed','expired','cancelled'): raise ValueError('Batch is not terminal')
        for kind,file_id in [('output',b.output_file_id),('errors',b.error_file_id)]:
            if file_id:
                dest=a.out/(a.cohort+'_'+kind+'.jsonl')
                if dest.exists(): raise FileExistsError(dest)
                dest.write_bytes(c.files.content(file_id).read()); print('Saved',dest)
    elif a.cmd=='import': import_results(a.out,a.cohort,a.output,a.errors)
    else:
        if a.per_group<1: raise ValueError('per-group must be positive')
        review_sheet(a.out,a.cohort,a.per_group,a.seed)

if __name__=='__main__': main()
