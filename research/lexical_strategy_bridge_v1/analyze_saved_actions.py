"""Exploratory held-out analysis of saved action profiles and residual geometry."""
import hashlib, json, os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'saved_action_analysis'
rows=[json.loads(x) for x in (OUT/'actions.jsonl').read_text(encoding='utf-8').splitlines()]
refs=[json.loads(x) for x in (OUT/'reference_rows.jsonl').read_text(encoding='utf-8').splitlines()]
cats=['cooperation','competition','independent','neutral']; langs=['en','fr','zh','ja','ar']
labels=sorted({r['strategy'] for r in rows}); y=np.array([labels.index(r['strategy']) for r in rows])
length=np.array([[r['action_word_count'],r['action_char_count']] for r in rows],dtype=float)
scenarios=np.array([r['scenario_id'] for r in rows]); results={'strategies':labels,'splits':{},'note':'Exploratory; activation includes full scenario prompt; no neutral-to-DISENGAGE mapping.'}
paths={'qwen':ROOT/'mechanistic_artifacts/cross_model_qwen_v1','olmo7b':ROOT/'mechanistic_artifacts/cross_model_olmo7b_v1/olmo7b_full_olmo-full-01','mistral7b':ROOT/'mechanistic_artifacts/cross_model_mistral7b_v1/mistral7b_full_mistral-full-01'}
def sha(b): return hashlib.sha256(b).hexdigest()
def centered(x):
    x=x.copy()
    for s in np.unique(scenarios):
        mask=scenarios==s; x[mask]-=x[mask].mean(axis=0)
    return x
def r2(y,p,base):
    denom=np.sum((y-base)**2); return float(1-np.sum((y-p)**2)/denom) if denom>0 else None
def pair_data(x, lens, idx):
    a,b=np.triu_indices(len(idx),1); X=x[idx]; L=lens[idx]
    n=np.linalg.norm(X,axis=1); sim=(X@X.T)/np.maximum(n[:,None]*n[None,:],1e-20)
    return 1-sim[a,b], np.abs(L[a]-L[b])
def corr(a,b):
    v=spearmanr(a,b).statistic
    return float(v) if np.isfinite(v) else None

profiles={k:np.load(OUT/(k+'_profiles.npy')) for k in ('e5','bge-m3','labse')}
concept_masks={}
for key in profiles:
    reference=np.load(ROOT/'research/cooperative_lexical_geometry_v2_wordlevel_expanded/exploratory_results_20261106'/(key+'_embeddings.npy')).reshape(200,5,-1).mean(axis=1)
    reference=reference/np.linalg.norm(reference,axis=1,keepdims=True)
    kept=[]
    for i in range(200):
        if not kept or np.max(reference[kept]@reference[i])<0.95: kept.append(i)
    concept_masks[key]=kept
summaries={}
for enc,p in profiles.items():
    category=np.column_stack([p[:,[i for i,r in enumerate(refs) if r['category']==c]].mean(axis=1) for c in cats])
    records=[]
    for i,row in enumerate(rows):
        # Each concept contributes once, independent of number of translations.
        concept=p[i].reshape(200,5).mean(axis=1)
        nearest=np.argsort(concept)[-10:][::-1]
        ranks={c:int(1+sum(category[j,k]>category[i,k] for j in np.where(scenarios==scenarios[i])[0])) for k,c in enumerate(cats)}
        records.append({'prompt_id':row['prompt_id'],'scenario_id':row['scenario_id'],'strategy':row['strategy'],
          'category_mean':dict(zip(cats,map(float,category[i]))),'within_scenario_category_rank':ranks,
          'nearest_words':[{'id':refs[int(j)]['id'],'category':refs[int(j)]['category'],'language':refs[int(j)]['language'],'word':refs[int(j)]['word'],'similarity':float(p[i,j])} for j in np.argsort(p[i])[-10:][::-1]],
          'nearest_concepts':[{'id':refs[int(j)*5]['id'],'category':refs[int(j)*5]['category'],'words':{r['language']:r['word'] for r in refs[int(j)*5:int(j)*5+5]},'mean_five_language_similarity':float(concept[j]),'per_language':dict(zip(langs,map(float,p[i,int(j)*5:int(j)*5+5])))} for j in nearest]})
    (OUT/(enc+'_scenario_summary.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    summaries[enc]=category

for split,field,group in [('family','split','group_key'),('domain','domain_split','domain')]:
    tr=np.array([r[field]=='discovery' for r in rows]); te=~tr
    assert not set(r[group] for i,r in enumerate(rows) if tr[i]) & set(r[group] for i,r in enumerate(rows) if te[i])
    assert not set(r['group_key'] for i,r in enumerate(rows) if tr[i]) & set(r['group_key'] for i,r in enumerate(rows) if te[i])
    splitout=results['splits'][split]={'semantic':{},'models':{}}
    semantic_predictions={}
    for enc,p in profiles.items():
        # Equal concept contribution and single-language views expose language effects.
        splitout['semantic'][enc]={}
        concept=p.reshape(496,200,5).mean(axis=2)
        for view,X in [('length',length),('all_concepts',concept),('deduplicated_concepts_cosine_095',concept[:,concept_masks[enc]]),('length_plus_concepts',np.column_stack([length,concept])),('category',summaries[enc])]+[(lang,p[:,j::5]) for j,lang in enumerate(langs)]:
            scaler=StandardScaler().fit(X[tr]); clf=LogisticRegression(C=1,max_iter=2000,class_weight='balanced').fit(scaler.transform(X[tr]),y[tr]); pred=clf.predict(scaler.transform(X[te]))
            groups=np.array([r[group] for r in rows])[te]; unique=np.unique(groups); rng=np.random.default_rng(42)
            pergroup=np.array([np.mean(pred[groups==g]==y[te][groups==g]) for g in unique]); boot=rng.choice(pergroup,size=(2000,len(unique)),replace=True).mean(axis=1)
            splitout['semantic'][enc][view]={'accuracy':float(accuracy_score(y[te],pred)),'balanced_accuracy':float(balanced_accuracy_score(y[te],pred)), 'cluster_macro_accuracy':float(pergroup.mean()),'cluster_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(), 'per_strategy_accuracy':{labels[k]:float(np.mean(pred[y[te]==k]==k)) for k in range(4)},'predictions':pred.tolist(),'feature_count':int(X.shape[1])}
            if view=='all_concepts': semantic_predictions[enc]=pred
    for key,path in paths.items():
        manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8')); raw=(path/'evidence_hashes.json').read_bytes(); evidence=json.loads(raw)
        assert manifest['status']=='completed' and not manifest['mock']
        assert sha(raw.replace(b'\r\n',b'\n'))==manifest['evidence_sha256'] or sha(raw)==manifest['evidence_sha256']
        saved=[json.loads(x) for x in (path/'prompts.jsonl').read_text(encoding='utf-8').splitlines()]
        assert saved==rows
        arrays=[]
        for row in rows:
            name='activations/'+row['prompt_id']+'.npz'; f=path/name
            assert sha(f.read_bytes())==evidence[name]
            with np.load(f,allow_pickle=False) as d: arrays.append(d['residual'])
        a=np.stack(arrays); assert a.shape[:2]==(496,8) and np.isfinite(a).all()
        m=splitout['models'][key]=[]
        for depth in range(8):
            x=centered(a[:,depth,:].astype(np.float64)); clf=LogisticRegression(C=0.1,max_iter=1000).fit(x[tr],y[tr]); scores=clf.decision_function(x[te]); pred=clf.predict(x[te]); train_scores=clf.decision_function(x[tr]);
            item={'block_index':manifest['indices'][depth], 'probe_accuracy':float(accuracy_score(y[te],pred)),'probe_predictions':pred.tolist(),'encoders':{}}
            for enc,p in profiles.items():
                px=centered(p.astype(np.float64)); ti=np.where(tr)[0]; ei=np.where(te)[0]
                rd_train,ld_train=pair_data(px,length,ti); rd_test,ld_test=pair_data(px,length,ei)
                ad_train,_=pair_data(x,length,ti); ad_test,_=pair_data(x,length,ei)
                base=Ridge(alpha=1).fit(ld_train,ad_train); joint=Ridge(alpha=1).fit(np.column_stack([ld_train,rd_train]),ad_train)
                bl=base.predict(ld_test); jp=joint.predict(np.column_stack([ld_test,rd_test]))
                # Probe score prediction uses discovery-only fit and an action-length baseline.
                s=StandardScaler().fit(np.column_stack([length,px])[tr]); features=s.transform(np.column_stack([length,px])); b=Ridge(alpha=100).fit(features[tr,:2],train_scores); j=Ridge(alpha=100).fit(features[tr],train_scores)
                bp=b.predict(features[te,:2]); pp=j.predict(features[te]);
                item['encoders'][enc]={'heldout_rsa_spearman':corr(rd_test,ad_test),'heldout_rdm_length_mse':float(np.mean((ad_test-bl)**2)), 'heldout_rdm_joint_mse':float(np.mean((ad_test-jp)**2)), 'score_length_mse':float(np.mean((scores-bp)**2)),'score_joint_mse':float(np.mean((scores-pp)**2)),'score_r2_by_strategy':{labels[k]:r2(scores[:,k],pp[:,k],bp[:,k]) for k in range(4)},'semantic_probe_prediction_agreement':float(np.mean(semantic_predictions[enc]==pred))}
            m.append(item)
(OUT/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print('Analysis completed:',OUT,flush=True)
