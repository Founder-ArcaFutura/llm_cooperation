"""Exploratory description only; labels are unvalidated and may be wrong."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

root=Path('reports/manuscript_readiness')
classification=root/'construct_qwen32b/construct-v1-8388c1e11b29c524.json'
packet_file=root/'adjudication_template_packets/all_152_blinded_packets.json'
key_file=root/'adjudication_template_packets/INTERNAL_UNBLINDING_KEY.json'
data=json.loads(classification.read_text(encoding='utf-8'))
assert data['expected']==304 and len(data['records'])==304
assert data['input_sha256']==hashlib.sha256(packet_file.read_bytes()).hexdigest()
key=json.loads(key_file.read_text(encoding='utf-8'))
records={r['id']:r['review'] for r in data['records']}
assert len(records)==304 and len(key)==152
labels={}
for packet in key:
    for row in packet['source_rows']:
        review=records[packet['packet_id']+'_'+row['scenario_version']]
        for num in (1,2):
            label_key=(packet['source_bank'],row['scenario_id'],row[f'wording_{num}_source'])
            assert label_key not in labels
            labels[label_key]=review[f'wording_{num}']
assert len(labels)==608

manifest=json.loads((root/'cohort_provenance_manifest.json').read_text(encoding='utf-8'))
summary={}; unknown=Counter()
for model, entry in manifest['canonical_runs'].items():
    if 'pythia' in model.lower() or 'instruct' in model.lower() or model.startswith('founder-'): continue
    path=Path('results/cooperate_rewording')/entry['directory']/'rows.jsonl'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['rows_sha256']
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    paired=defaultdict(dict)
    for row in rows:
        if row.get('condition')!='four': continue
        label_key=(row['bank'],row['scenario_id'],row['wording'])
        if label_key not in labels: unknown[label_key]+=1; continue
        paired[(row['bank'],row['scenario_id'],row['permutation_index'])][row['wording']]=row
    groups=defaultdict(lambda: {'n':0,'cooperate':0,'independent':0,'templates':set()})
    for (bank,scenario,rotation),versions in paired.items():
        if set(versions)!={'original','paraphrase'}: continue
        if any(not r.get('forced_choice') or r['forced_choice'].get('tied_max_count')!=1 for r in versions.values()): continue
        for wording,row in versions.items():
            label=labels[(bank,scenario,wording)]
            for field in ('interdependence','goal_structure','actor_outcome','recipient_outcome','actor_cost','lexical_favor'):
                group=groups[(bank,wording,field,label[field])]
                group['n']+=1; group['templates'].add(row['template_id'])
                group['cooperate']+=row['forced_choice']['strategy']=='COOPERATE'
                group['independent']+=row['forced_choice']['strategy']=='INDEPENDENT'
    summary[model]=[{'bank':b,'wording':w,'field':f,'value':v,**{k:len(x) if k=='templates' else x for k,x in data.items()},'margin':(data['cooperate']-data['independent'])/data['n']} for (b,w,f,v),data in sorted(groups.items())]
assert not unknown, f'Unmapped scenario wordings: {len(unknown)}'
dest=root/'construct_qwen32b/provisional_label_join.json'
dest.write_text(json.dumps({'warning':'UNVALIDATED QWEN LABELS; role and outcome errors identified; descriptive only', 'label_count':len(labels),'models':summary},indent=2)+'\n',encoding='utf-8')
print('Joined',len(labels),'scenario-wording labels across',len(summary),'responsive base models; output',dest)
for value in ('absent','beneficial_not_necessary','necessary','unclear'):
    items=[g for groups in summary.values() for g in groups if g['bank']=='phase1' and g['wording']=='paraphrase' and g['field']=='interdependence' and g['value']==value]
    if items: print(value,'models',len(items),'template counts',min(x['templates'] for x in items),max(x['templates'] for x in items),'margin range',round(min(x['margin'] for x in items)*100,1),round(max(x['margin'] for x in items)*100,1))
