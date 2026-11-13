"""Offline forensic audit of the saved Luna/Qwen construct pilot; no API calls."""
import csv
import hashlib
import io
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/manuscript_readiness/construct_luna_qa/pilot_20261112'
DEST=ROOT/'reports/manuscript_readiness/construct_luna_qa/forensic_20261113'
PACKETS=ROOT/'reports/manuscript_readiness/adjudication_template_packets/all_152_blinded_packets.json'
KEY=ROOT/'reports/manuscript_readiness/adjudication_template_packets/INTERNAL_UNBLINDING_KEY.json'
QWEN=ROOT/'reports/manuscript_readiness/construct_qwen32b/construct-v1-8388c1e11b29c524.json'
FIELDS=('interaction','interdependence','goal_structure','actor_outcome','recipient_outcome','actor_cost','lexical_favor')

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def safe_write(p, text):
    if p.exists():
        if p.read_text(encoding='utf-8').replace('\r\n','\n')!=text.replace('\r\n','\n'):
            raise FileExistsError(f'Refusing to overwrite changed artifact: {p}')
        return
    p.write_bytes(text.encode('utf-8'))
def write(p,v): safe_write(p,json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def norm(s): return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def sets(x): return set(x if isinstance(x,list) else [x])
def label(x): return '|'.join(sorted(x)) if isinstance(x,list) else x

def kappa(pairs):
    if not pairs: return None
    n=len(pairs); x=Counter(a for a,b in pairs); y=Counter(b for a,b in pairs)
    observed=sum(a==b for a,b in pairs)/n
    expected=sum(x[k]*y[k] for k in x.keys()|y.keys())/(n*n)
    return (observed-expected)/(1-expected) if expected<1 else None

def cluster_interval(rows, iterations=2000):
    groups=defaultdict(list)
    for row in rows: groups[row['packet']].append(row)
    ids=sorted(groups); rng=random.Random(20261113); values=[]
    if len(ids)<2: return None
    for _ in range(iterations):
        sampled=[r for __ in ids for r in groups[rng.choice(ids)]]
        values.append(sum(r['agreement'] for r in sampled)/len(sampled))
    values.sort(); return [values[int(.025*(len(values)-1))],values[int(.975*(len(values)-1))]]

def quote_reason(e,src):
    q=e.get('quote',''); name=e.get('source','');
    if name not in src: return 'unknown_source'
    if not q: return 'empty_quote'
    if q in src[name]: return 'exact'
    if norm(q) in norm(src[name]): return 'normalization_only'
    if any(q in text for key,text in src.items() if key!=name): return 'wrong_source'
    if any(norm(q) in norm(text) for key,text in src.items() if key!=name): return 'wrong_source_normalized'
    return 'not_found_verbatim'

def run():
    DEST.mkdir(parents=True,exist_ok=True)
    manifest=load(BASE/'manifest.json'); mapping=load(BASE/'development_mapping.json'); data=load(BASE/'development_qa_results.json')
    assert sha(BASE/'development.jsonl')==manifest['cohorts']['development']['request_sha256']
    assert sha(BASE/'development_mapping.json')==manifest['cohorts']['development']['mapping_sha256']
    assert sha(PACKETS)==manifest['sources'][PACKETS.name] and sha(KEY)==manifest['sources'][KEY.name] and sha(QWEN)==manifest['sources'][QWEN.name]
    requests=[json.loads(x) for x in (BASE/'development.jsonl').read_text(encoding='utf-8').splitlines()]
    raw=[json.loads(x) for x in (BASE/'development_sync_output.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(requests)==len(mapping)==len(data['results'])==len(raw)==280
    req={x['custom_id']:x for x in requests}; rawmap={x['custom_id']:x for x in raw}
    results={x['custom_id']:x for x in data['results']}
    assert len(req)==len(rawmap)==len(results)==280 and set(req)==set(rawmap)==set(results)==set(mapping)
    packet_index={p['packet_id']:p for p in load(PACKETS)}; key_index={p['packet_id']:p for p in load(KEY)}
    qdata=load(QWEN); assert qdata['input_sha256']==sha(PACKETS)
    qrecords={r['id']:r['review'] for r in qdata['records']}
    enriched=[]; quote_items=[]; schema_errors=[]
    for cid,meta in mapping.items():
        row=results[cid]; packet=meta['packet_id']; variant=meta['variant']; w=meta['wording']; field=meta['field']
        assert meta['qwen_label']==qrecords[packet+'_'+variant]['wording_'+str(w)][field]
        assert row['qwen_label']==meta['qwen_label'] and row['field']==field
        packet_src=packet_index[packet]['scenario_'+variant]
        assert meta['source']=={'scenario':packet_src['scenario_stem'],'target':packet_src['cooperative_wording_'+str(w)],'reference':packet_src['independent_action']}
        body=rawmap[cid]['response']['body']; chunks=[c for o in body.get('output',[]) if o.get('type')=='message' for c in o.get('content',[]) if c.get('type')=='output_text']
        parsed=json.loads(chunks[0]['text']) if len(chunks)==1 else None
        if row['status']=='error': schema_errors.append({'custom_id':cid,'error':row.get('error'),'raw_answer':parsed})
        else:
            assert parsed==row['luna']
            for e in row['luna']['evidence']:
                quote_items.append({'custom_id':cid,**e,'category':quote_reason(e,meta['source'])})
        enriched.append({'custom_id':cid,'packet':packet,'variant':variant,'wording':w,'field':field,'status':row['status'],
                         'qwen':row['qwen_label'],'luna':row.get('luna',{}).get('answers'), 'agreement':row.get('agreement'),
                         'qwen_evidence':qrecords[packet+'_'+variant]['wording_'+str(w)]['evidence'],
                         'luna_response':row.get('luna'), 'source':meta['source']})
    assert len({x['packet'] for x in enriched})==10

    metrics=[]; matrices=[]; subtype=[]; packetstats=[]
    for mode in ('format_valid','including_quote_flags'):
        eligible=[x for x in enriched if x['status']=='format_valid' or (mode=='including_quote_flags' and x['status']=='review_needed')]
        for f in FIELDS:
            rows=[x for x in eligible if x['field']==f]; pairs=[(label(x['qwen']),label(x['luna'])) for x in rows]
            agreement=sum(x['agreement'] for x in rows)/len(rows) if rows else None
            metrics.append({'subset':mode,'field':f,'n':len(rows),'packets':len({x['packet'] for x in rows}),
                            'exact_agreement':agreement,'cohen_kappa':kappa(pairs),
                            'packet_bootstrap_95pct_agreement':cluster_interval(rows),
                            'note':'kappa for interaction treats complete label sets as nominal categories; descriptive only'})
            for (q,l),n in sorted(Counter(pairs).items()): matrices.append({'subset':mode,'field':f,'qwen':q,'luna':l,'count':n})
            if f=='interaction':
                usable=[x for x in rows if 'unclear' not in sets(x['qwen']) and 'unclear' not in sets(x['luna'])]
                for cat in sorted({v for x in usable for v in sets(x['qwen'])|sets(x['luna'])}):
                    tp=sum(cat in sets(x['qwen']) and cat in sets(x['luna']) for x in usable)
                    fp=sum(cat not in sets(x['qwen']) and cat in sets(x['luna']) for x in usable)
                    fn=sum(cat in sets(x['qwen']) and cat not in sets(x['luna']) for x in usable)
                    subtype.append({'subset':mode,'label':cat,'tp':tp,'luna_only':fp,'qwen_only':fn,
                                    'jaccard':tp/(tp+fp+fn) if tp+fp+fn else None,
                                    'precision_vs_qwen':tp/(tp+fp) if tp+fp else None,
                                    'recall_vs_qwen':tp/(tp+fn) if tp+fn else None,
                                    'f1_vs_qwen':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None})
                j=[len(sets(x['qwen']) & sets(x['luna']))/len(sets(x['qwen'])|sets(x['luna'])) for x in usable]
                metrics[-1]['mean_example_jaccard_excluding_unclear']=sum(j)/len(j) if j else None
                metrics[-1]['jaccard_n']=len(j)
                tp=sum(len(sets(x['qwen']) & sets(x['luna'])) for x in usable)
                fp=sum(len(sets(x['luna'])-sets(x['qwen'])) for x in usable)
                fn=sum(len(sets(x['qwen'])-sets(x['luna'])) for x in usable)
                metrics[-1]['micro_precision_vs_qwen']=tp/(tp+fp) if tp+fp else None
                metrics[-1]['micro_recall_vs_qwen']=tp/(tp+fn) if tp+fn else None
                metrics[-1]['micro_f1_vs_qwen']=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        for pid in sorted({x['packet'] for x in eligible}):
            rows=[x for x in eligible if x['packet']==pid]
            packetstats.append({'subset':mode,'packet_id':pid,'n':len(rows),'agree':sum(x['agreement'] for x in rows),'disagree':sum(not x['agreement'] for x in rows),
                                'bank':key_index[pid]['source_bank']})

    # Compare original versus paraphrase within each partner, and human versus AI within each source wording.
    consistency=[]
    for pid in sorted({x['packet'] for x in enriched}):
        lookup={(x['variant'],x['wording'],x['field']):x for x in enriched if x['packet']==pid}
        for f in FIELDS:
            for variant in ('A','B'):
                a,b=(lookup[(variant,w,f)] for w in (1,2))
                for model in ('qwen','luna'):
                    if a[model] is not None and b[model] is not None:
                        consistency.append({'packet_id':pid,'field':f,'comparison':'wording_within_partner','model':model,'agree':sets(a[model])==sets(b[model])})
            a,b=key_index[pid]['source_rows']
            for source_wording in ('original','paraphrase'):
                wa=next(w for w in (1,2) if a[f'wording_{w}_source']==source_wording)
                wb=next(w for w in (1,2) if b[f'wording_{w}_source']==source_wording)
                x,y=lookup[(a['scenario_version'],wa,f)],lookup[(b['scenario_version'],wb,f)]
                for model in ('qwen','luna'):
                    if x[model] is not None and y[model] is not None:
                        consistency.append({'packet_id':pid,'field':f,'comparison':'partner_within_source_wording','model':model,'agree':sets(x[model])==sets(y[model])})

    # Corpus label distribution: coding assignments only, multi-label by wording, not observed behavioral prevalence.
    corpus=Counter(); cooccur=Counter(); bybank=Counter(); keyrows={}
    for p in load(KEY):
        for r in p['source_rows']: keyrows[p['packet_id']+'_'+r['scenario_version']]=p['source_bank']
    for record in qdata['records']:
        bank=keyrows[record['id']]
        for judgment in record['review'].values():
            tags=sorted(set(judgment['interaction']))
            for t in tags: corpus[('interaction',t)]+=1; bybank[(bank,'interaction',t)]+=1
            for a,b in combinations(tags,2): cooccur[(a,b)]+=1
            for f in FIELDS[1:]: corpus[(f,judgment[f])]+=1; bybank[(bank,f,judgment[f])]+=1

    # Blind packet set includes all development material, without labels, model explanations or outcomes.
    rng=random.Random(20261113); blind=[]; comparison=[]
    pids=sorted({x['packet'] for x in enriched}); rng.shuffle(pids)
    for index,pid in enumerate(pids,1):
        bpid=f'BR-{index:03d}'; versions=['A','B']; rng.shuffle(versions); scenarios=[]
        for vi,variant in enumerate(versions,1):
            s=packet_index[pid]['scenario_'+variant]; opts=[s['independent_action'],s['competing_action'],s['disengaging_action']]
            rng.shuffle(opts); wordings=[1,2]; rng.shuffle(wordings)
            scenarios.append({'version':f'V{vi}','stem':s['scenario_stem'],'target_phrasings':[{'wording':f'W{j}', 'text':s['cooperative_wording_'+str(w)]} for j,w in enumerate(wordings,1)],
                              'reference_action':s['independent_action'],'other_actions':[o for o in opts if o!=s['independent_action']]})
            for j,w in enumerate(wordings,1):
                for field in FIELDS:
                    row=next(x for x in enriched if x['packet']==pid and x['variant']==variant and x['wording']==w and x['field']==field)
                    comparison.append({'blind_packet':bpid,'blind_version':f'V{vi}','blind_wording':f'W{j}',**row})
        blind.append({'packet':bpid,'versions':scenarios})
    write(DEST/'blind_review_packets.json',blind)
    write(DEST/'blind_response_template.json',{'instructions':'One response per field and wording; use codebook and cite evidence; no gold or model outputs supplied.',
         'items':[{'packet':p['packet'],'version':v['version'],'wording':w['wording'],'field':f,'answer':'','evidence':'','reasoning':'','uncertainty':''}
                  for p in blind for v in p['versions'] for w in v['target_phrasings'] for f in FIELDS]})
    write(DEST/'comparison_key_RESTRICTED.json',comparison)
    write(DEST/'analysis.json',{'provenance':{str(p.relative_to(ROOT)):sha(p) for p in (PACKETS,KEY,QWEN,BASE/'manifest.json',BASE/'development_mapping.json',BASE/'development_qa_results.json',BASE/'development_sync_output.jsonl',BASE/'development.jsonl')},
        'counts':{'requests':len(enriched),'packets':len(pids),'statuses':dict(Counter(x['status'] for x in enriched)),
                  'quotes':dict(Counter(x['category'] for x in quote_items))},'metrics':metrics,'confusion':matrices,'subtype_metrics':subtype,'packet_disagreements':packetstats,
        'consistency':consistency,'quote_review':quote_items,'schema_errors':schema_errors,
        'corpus_labels':[{'field':f,'label':v,'n':n} for (f,v),n in sorted(corpus.items())],
        'corpus_cooccurrence':[{'first':a,'second':b,'n':n} for (a,b),n in sorted(cooccur.items())],
        'corpus_by_bank':[{'bank':b,'field':f,'label':v,'n':n} for (b,f,v),n in sorted(bybank.items())]})
    for name,rows in [('field_metrics',metrics),('confusion_matrices',matrices),('interaction_metrics',subtype),('packet_disagreements',packetstats)]:
        cols=list(dict.fromkeys(k for row in rows for k in row))
        f=io.StringIO(newline=''); wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader(); wr.writerows(rows)
        safe_write(DEST/(name+'.csv'),f.getvalue())
    for name,rows in [('corpus_assignments',[{'bank':b,'field':f,'label':v,'n':n} for (b,f,v),n in sorted(bybank.items())]),('corpus_cooccurrence',[{'first':a,'second':b,'n':n} for (a,b),n in sorted(cooccur.items())])]:
        f=io.StringIO(newline=''); wr=csv.DictWriter(f,fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
        safe_write(DEST/(name+'.csv'),f.getvalue())
    print('Audited',len(enriched),'requests across',len(pids),'packets; results:',DEST)
    print('Quote categories:',dict(Counter(x['category'] for x in quote_items)))
    for x in metrics[:7]: print(x['field'],x['n'],round(100*x['exact_agreement'],1), 'kappa',round(x['cohen_kappa'],3) if x['cohen_kappa'] is not None else None)

if __name__=='__main__': run()
