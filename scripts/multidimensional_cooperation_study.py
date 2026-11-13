"""Offline exploratory inventory and descriptive analyses; no inference or source mutation."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/multidimensional_cooperation_v1'
BANKS={'phase0':'data/scenarios_v1_expanded.json','phase0b':'data/scenarios_phase0b_utility_matched.json','phase1':'data/scenarios_phase1_prospective.json'}
QWEN=ROOT/'reports/manuscript_readiness/construct_qwen32b/construct-v1-8388c1e11b29c524.json'
PACKETS=ROOT/'reports/manuscript_readiness/adjudication_template_packets/all_152_blinded_packets.json'
KEY=ROOT/'reports/manuscript_readiness/adjudication_template_packets/INTERNAL_UNBLINDING_KEY.json'
PROV=ROOT/'reports/manuscript_readiness/cohort_provenance_manifest.json'
LUNA_QA=ROOT/'reports/manuscript_readiness/construct_luna_qa/pilot_20261112/development_qa_results.json'

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvout(p,rows):
    if not rows: return
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def complete_triad_conditions(groups):
    needed={'coop_advantageous','equal_utility','coop_disadvantageous'}
    out=defaultdict(list)
    for k,conditions in groups.items():
        if set(conditions)!=needed: continue
        maps=[r['letter_to_strategy'] for r in conditions.values()]
        if any(mapping!=maps[0] for mapping in maps[1:]): raise ValueError('Inconsistent triad option rotation')
        out[(k[0],k[3])].append(conditions)
    return out

def read_inputs():
    key=load(KEY); q=load(QWEN); prov=load(PROV)
    if q['input_sha256']!=sha(PACKETS): raise ValueError('Packet provenance mismatch')
    reviews={x['id']:x['review'] for x in q['records']}; labels={}; inventory=[]
    banks={name:load(ROOT/path)['scenarios'] for name,path in BANKS.items()}
    source={(bank,s['id']):s for bank,scenarios in banks.items() for s in scenarios}
    for packet in key:
        bank=packet['source_bank']
        for row in packet['source_rows']:
            s=source[(bank,row['scenario_id'])]
            if s['template_id']!=packet['source_template_id']: raise ValueError('Template mismatch')
            for w in (1,2):
                wording=row[f'wording_{w}_source']; k=(bank,s['id'],wording)
                if k in labels: raise ValueError('Duplicate label mapping')
                labels[k]=reviews[packet['packet_id']+'_'+row['scenario_version']]['wording_'+str(w)]
            inventory.append({'bank':bank,'template_id':s['template_id'],'scenario_id':s['id'],'partner':s['partner_type'],
                'domain':s.get('domain'),'context':s.get('context_type'),'utility_condition':s.get('utility_condition'),
                'triad':s.get('triad_id'),'symmetric_control':bool(s.get('is_symmetric_control')),
                'source_split':s.get('split'),'annotation_status':'Qwen v1 unvalidated; independent adjudication pending'})
    if len(inventory)!=304 or len(labels)!=608: raise ValueError('Unexpected corpus size')
    return banks,labels,inventory,prov

def summarize(banks,labels,inventory,prov):
    interaction=[]; triads=[]; sensitivity=[]; missing=Counter(); hashes={}
    qa={r['custom_id']:r for r in load(LUNA_QA)['results'] if r['field']=='interaction' and r['status']=='format_valid'}
    dev_labels={}
    for packet in load(KEY):
        for row in packet['source_rows']:
            for w in (1,2):
                cid=f"{packet['packet_id']}_{row['scenario_version']}_w{w}_interaction"
                if cid in qa:
                    k=(packet['source_bank'],row['scenario_id'],row[f'wording_{w}_source'])
                    dev_labels[k]={'Qwen':set(qa[cid]['qwen_label']),'Luna':set(qa[cid]['luna']['answers'])}
    for model,entry in sorted(prov['canonical_runs'].items()):
        if 'pythia' in model.lower() or 'instruct' in model.lower() or model.startswith('founder-'): continue
        for bank,relpath in BANKS.items():
            raw=(ROOT/relpath).read_bytes(); info=entry['summary_meta']['banks'][bank]
            raw_hash=hashlib.sha256(raw).hexdigest()
            lf_hash=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
            if raw_hash!=info['source_sha256'] and lf_hash!=info.get('source_lf_sha256'):
                raise ValueError('Scenario source hash mismatch: '+model+' '+bank)
        path=ROOT/'results/cooperate_rewording'/entry['directory']/'rows.jsonl'
        if sha(path)!=entry['rows_sha256']: raise ValueError('Behavioral input hash mismatch: '+model)
        hashes[model]=sha(path)
        rows=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
        pairs=defaultdict(dict)
        for r in rows:
            if r.get('condition')!='four': continue
            k=(r['bank'],r['scenario_id'],r['wording'])
            if k not in labels: missing[k]+=1; continue
            key=(r['bank'],r['scenario_id'],r['permutation_index'])
            if r['wording'] in pairs[key]: raise ValueError('Duplicate wording row')
            pairs[key][r['wording']]=r
        kept=[]
        for versions in pairs.values():
            if set(versions)!={'original','paraphrase'}: continue
            if any(not r.get('forced_choice') or r['forced_choice'].get('tied_max_count')!=1 for r in versions.values()): continue
            kept.extend(versions.values())
        groups=defaultdict(list)
        for r in kept:
            label=labels[(r['bank'],r['scenario_id'],r['wording'])]
            for subtype in label['interaction']:
                groups[(r['bank'],r['wording'],subtype)].append(r)
        for (bank,wording,subtype),rs in sorted(groups.items()):
            counts=Counter(r['forced_choice']['strategy'] for r in rs)
            interaction.append({'model':model,'bank':bank,'wording':wording,'qwen_provisional_label':subtype,
                 'presentations':len(rs),'templates':len({r['template_id'] for r in rs}),
                 'cooperate':counts['COOPERATE'],'independent':counts['INDEPENDENT'],
                 'cooperate_minus_independent':(counts['COOPERATE']-counts['INDEPENDENT'])/len(rs)})
        # Same held rows, alternative unvalidated reviewers, development sample only.
        devgroups=defaultdict(list)
        for r in kept:
            k=(r['bank'],r['scenario_id'],r['wording'])
            if k not in dev_labels: continue
            for reviewer,tags in dev_labels[k].items():
                for tag in tags: devgroups[(reviewer,r['bank'],r['wording'],tag)].append(r)
        for (reviewer,bank,wording,tag),rs in sorted(devgroups.items()):
            counts=Counter(r['forced_choice']['strategy'] for r in rs)
            sensitivity.append({'model':model,'reviewer':reviewer,'bank':bank,'wording':wording,'provisional_label':tag,
                 'templates':len({r['template_id'] for r in rs}),'presentations':len(rs),
                 'cooperate':counts['COOPERATE'],'independent':counts['INDEPENDENT'],
                 'cooperate_minus_independent':(counts['COOPERATE']-counts['INDEPENDENT'])/len(rs)})
        # Pair each authored triad across conditions by partner, position permutation, and wording.
        groups=defaultdict(dict)
        for r in kept:
            if r['bank']=='phase0b' and r.get('triad_id'):
                k=(r['triad_id'],r['partner_type'],r['permutation_index'],r['wording'])
                condition=r['utility_condition']
                if condition in groups[k]: raise ValueError('Duplicate triad condition')
                groups[k][condition]=r
        needed={'coop_advantageous','equal_utility','coop_disadvantageous'}
        bytriad=complete_triad_conditions(groups)
        for (triad,wording),matched in sorted(bytriad.items()):
            rec={'model':model,'triad':triad,'wording':wording,'matched_presentations_per_condition':len(matched)}
            for condition in sorted(needed):
                strategies=[x[condition]['forced_choice']['strategy'] for x in matched]
                rec[condition+'_cooperate_rate']=strategies.count('COOPERATE')/len(strategies)
                rec[condition+'_independent_rate']=strategies.count('INDEPENDENT')/len(strategies)
            triads.append(rec)
    if missing: raise ValueError(f'Unmapped scenario/wordings: {len(missing)}')
    coverage=Counter()
    for (bank,scenario,wording),v in labels.items():
        for subtype in v['interaction']: coverage[(bank,subtype)]+=1
    return interaction,triads,sensitivity,[{'bank':k[0],'qwen_provisional_label':k[1],'scenario_wordings':n} for k,n in sorted(coverage.items())],hashes

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    banks,labels,inventory,prov=read_inputs(); interaction,triads,sensitivity,coverage,hashes=summarize(banks,labels,inventory,prov)
    csvout(OUT/'scenario_inventory.csv',inventory); csvout(OUT/'provisional_interaction_coverage.csv',coverage)
    csvout(OUT/'provisional_subtype_behavior.csv',interaction); csvout(OUT/'within_triad_choice_rates.csv',triads)
    csvout(OUT/'development_annotation_sensitivity.csv',sensitivity)
    save(OUT/'analysis_manifest.json',{'description':'Exploratory authored-label and unvalidated Qwen-label descriptive analysis; no causal claims',
       'inputs':{str((ROOT/p).relative_to(ROOT)):sha(ROOT/p) for p in BANKS.values()},'packet_sha256':sha(PACKETS),'mapping_sha256':sha(KEY),'qwen_sha256':sha(QWEN),
       'behavioral_row_sha256':hashes,'luna_development_qa_sha256':sha(LUNA_QA),'models':len(hashes),'scenario_versions':len(inventory),'scenario_wordings':len(labels),
       'within_triad':'Matched triad, partner, permutation, wording; both original and paraphrase untied in each included condition; no inference with four triads',
       'warning':'Qwen v1 labels are unvalidated and fields can be wrong; group overlap and selection changes across variants; source split is not a prospective heldout guarantee.'})
    plot_triads(triads)
    print('Inventory:',len(inventory),'scenario versions;',len(labels),'wordings;',len(hashes),'responsive models')
    print('Within-triad rows:',len(triads),'provisional subtype groups:',len(interaction))

def plot_triads(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import TwoSlopeNorm
    models=sorted({r['model'] for r in rows}); tids=sorted({r['triad'] for r in rows})
    selected={(r['model'],r['triad']):r for r in rows if r['wording']=='original'}
    values=np.full((len(models),len(tids)),np.nan)
    for i,model in enumerate(models):
        for j,tid in enumerate(tids):
            r=selected.get((model,tid))
            if r: values[i,j]=100*(r['coop_disadvantageous_cooperate_rate']-r['coop_advantageous_cooperate_rate'])
    fig,ax=plt.subplots(figsize=(8.5,6.5)); image=ax.imshow(values,cmap='BrBG',norm=TwoSlopeNorm(vmin=-100,vcenter=0,vmax=100))
    ax.set_xticks(range(len(tids)),[str(int(t.split('_')[-1])) for t in tids]); ax.set_xlabel('Authored triad'); ax.set_yticks(range(len(models)),[m.split('/')[-1] for m in models]);
    for i in range(len(models)):
        for j in range(len(tids)):
            val=values[i,j]; record=selected.get((models[i],tids[j])); label='—' if np.isnan(val) else f'{val:+.0f}\n(n={record["matched_presentations_per_condition"]})'
            ax.text(j,i,label,ha='center',va='center',fontsize=7,color='white' if not np.isnan(val) and abs(val)>65 else 'black')
    ax.set_title('Descriptive within-triad change in COOPERATE selection\nDisadvantageous minus advantageous; original wording (pp)')
    fig.colorbar(image,ax=ax,label='Percentage points'); fig.text(.02,.01,'n = matched presentations per condition, not independent scenarios. Ties excluded; descriptive only.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(OUT/'triad_selection_changes.png',dpi=170); plt.close(fig)

if __name__=='__main__': main()
