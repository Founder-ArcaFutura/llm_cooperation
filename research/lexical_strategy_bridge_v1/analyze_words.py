"""Analyze completed isolated-word captures; never invokes a language model."""
import argparse, hashlib, json, os
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
PLAN=Path(__file__).resolve().parent/'frozen'
REFIT_DIR=Path(__file__).resolve().parent/'saved_action_analysis/reconstructed_original_probes'
CATS=('cooperation','competition','independent','neutral'); LANGS=('en','fr','zh','ja','ar')
STRATEGIES=('COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE')
def digest(b): return hashlib.sha256(b).hexdigest()
def scores(true,pred,concept):
    cm=confusion_matrix(true,pred,labels=range(4)); recall=np.diag(cm)/cm.sum(axis=1)
    unique=np.unique(concept); rng=np.random.default_rng(42); boot=[]
    for _ in range(1000):
        sample=rng.choice(unique,len(unique),replace=True); ix=np.concatenate([np.flatnonzero(concept==i) for i in sample]); mat=confusion_matrix(true[ix],pred[ix],labels=range(4)); denom=mat.sum(axis=1); boot.append(np.nanmean(np.divide(np.diag(mat),denom,out=np.full(4,np.nan),where=denom>0)))
    return {'balanced_accuracy':float(recall.mean()),'confusion_matrix':cm.tolist(),'per_category_recall':dict(zip(CATS,recall.tolist())),'concept_bootstrap_95':np.quantile(boot,[.025,.975]).tolist()}
def probe(x,y):
    return make_pipeline(StandardScaler(),LogisticRegression(C=.01,max_iter=2000,random_state=42)).fit(x,y)
def load_capture(directory,model):
    manifest=json.loads((PLAN/'manifest.json').read_text(encoding='utf8')); payload=(PLAN/'inventory.jsonl').read_bytes()
    if digest(payload)!=manifest['inventory_sha256']: raise ValueError('plan inventory mismatch')
    expected=[json.loads(v) for v in payload.splitlines() if json.loads(v)['condition']=='isolated']
    ident=json.loads((directory/'capture_identity.json').read_text(encoding='utf8')); receipt=json.loads((directory/'receipt.json').read_text(encoding='utf8'))
    if ident['plan_sha256']!=digest((PLAN/'manifest.json').read_bytes()) or ident['model']!=model or ident['revision']!=manifest['models'][model]['revision'] or ident['condition']!='isolated' or ident['limit']!=0 or not receipt['complete'] or receipt['smoke'] or receipt['identity']!=ident or receipt['total_records']!=1000: raise ValueError('capture identity/receipt mismatch')
    arrays=[]; tokens=[]
    for r in expected:
        name=f"{r['id']}_{r['language']}_isolated"; meta=json.loads((directory/'records'/(name+'.json')).read_text(encoding='utf8')); file=directory/'records'/(name+'.npz')
        if meta['record']!=r or meta['sha256']!=digest(file.read_bytes()): raise ValueError('capture evidence mismatch: '+name)
        with np.load(file,allow_pickle=False) as d: x=d['lexical']
        if x.shape!=(8,manifest['models'][model]['hidden_size']) or not np.isfinite(x).all(): raise ValueError('activation shape mismatch')
        arrays.append(x); tokens.append(len(meta['lexical_token_indices']))
    return expected,np.stack(arrays),np.array(tokens),manifest

def analyze(directory,model,out):
    rows,x,tokens,manifest=load_capture(directory,model)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    concepts=np.array([r['id'] for r in rows]); categories=np.array([CATS.index(r['category']) for r in rows]); languages=np.array([r['language'] for r in rows]); ids=np.array(list(dict.fromkeys(concepts)))
    assert len(ids)==200 and len(rows)==1000 and all(np.sum(concepts==c)==5 for c in ids)
    cy=np.array([categories[np.flatnonzero(concepts==c)[0]] for c in ids]); splitter=StratifiedKFold(5,shuffle=True,random_state=42)
    folds=list(splitter.split(ids,cy)); result={'model':model,'categories':CATS,'strategies':STRATEGIES,'method':'Five stratified held-out concept folds. English transfer trains on English words from training concepts only. Bootstrap resamples held-out concepts, conditional on fitted folds.','depths':[]}
    reportpath=ROOT/f'reports/cross_model_{model}_v1/replication_analysis.json'; report=json.loads(reportpath.read_text(encoding='utf8'))
    refit_dir=REFIT_DIR
    refit_audit=json.loads((refit_dir/(model+'_audit.json')).read_text(encoding='utf8'))
    if refit_audit['report_sha256']!=digest(reportpath.read_bytes()) or set(refit_audit['fits'])!={f'{split}_{i}' for split in ('family','domain') for i in range(8)} or any(v['prediction_mismatches'] for v in refit_audit['fits'].values()): raise ValueError('historical probe refit failed validation')
    coefficients=np.load(refit_dir/(model+'_coefficients.npz'),allow_pickle=False)
    directions={}
    for layer in range(8):
        depth={'block_index':manifest['models'][model]['indices'][layer],'views':{},'strategy_direction_projection':{},'embedding_rsa':{}}
        # Each word is evaluated once per view; translation siblings never train and test together.
        modes=['multilingual']+[f'en_to_{lang}' for lang in LANGS[1:]]+[f'other_to_{lang}' for lang in LANGS]+['length_only','concept_label_permutation']
        for mode in modes:
            all_y=[]; all_p=[]; all_c=[]
            for fi,(a,b) in enumerate(folds):
                train=np.isin(concepts,ids[a]); test=np.isin(concepts,ids[b])
                if mode.startswith('en_to_'): train &= languages=='en'; test &= languages==mode[6:]
                if mode.startswith('other_to_'): train &= languages!=mode[9:]; test &= languages==mode[9:]
                if set(concepts[train]) & set(concepts[test]): raise ValueError('concept leakage')
                X=x[:,layer,:].astype(np.float64) if mode!='length_only' else np.column_stack(([len(r['word']) for r in rows],tokens))
                y=categories.copy()
                if mode=='concept_label_permutation':
                    rng=np.random.default_rng(420+fi); shuffled=rng.permutation(cy[a]); mapping=dict(zip(ids[a],shuffled)); y[train]=[mapping[c] for c in concepts[train]]
                fit=probe(X[train],y[train]); pred=fit.predict(X[test]); all_y.extend(categories[test]); all_p.extend(pred); all_c.extend(concepts[test])
                if mode=='multilingual':
                    # Convert standardized-feature logistic coefficients back to activation units.
                    clf=fit[-1]; scale=fit[0].scale_; directions[f'layer{layer}_fold{fi}']=clf.coef_/scale
            depth['views'][mode]=scores(np.array(all_y),np.array(all_p),np.array(all_c))
        # Saved class-mean scenario-centered direction projections are descriptive only.
        # Remove each lexical language's overall mean, never subtract an action-scenario mean.
        z=x[:,layer,:].astype(np.float64).copy()
        for lang in LANGS: z[languages==lang]-=z[languages==lang].mean(axis=0)
        for split in ('family','domain'):
            saved=report['splits'][split]['layers'][layer]['variants']['raw']['directions']
            for si,st in enumerate(STRATEGIES):
              for kind,v in [('saved_class_mean',np.array(saved[st]['direction'],dtype=float)),('refitted_logistic',coefficients[f'{split}_{layer}_coef'][si].astype(float))]:
                v/=np.linalg.norm(v); projected=z@v
                category_values={}
                for i,c in enumerate(CATS):
                    concept_values=np.array([projected[concepts==cid].mean() for cid in ids[cy==i]])
                    rng=np.random.default_rng(42); boot=rng.choice(concept_values,size=(2000,len(concept_values)),replace=True).mean(axis=1)
                    category_values[c]={'mean':float(concept_values.mean()),'concept_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),'language_means':{lang:float(projected[(categories==i)&(languages==lang)].mean()) for lang in LANGS}}
                depth['strategy_direction_projection'][split+':'+kind+':'+st]=category_values
        # RSA compares centered cosine geometry only within each representation.
        def geometry(v):
            v=v-v.mean(axis=0); v=v/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-20); mat=v@v.T; return mat[np.triu_indices(len(v),1)]
        gx=geometry(x[:,layer,:].astype(np.float64)); base=ROOT/'research/cooperative_lexical_geometry_v2_wordlevel_expanded/exploratory_results_20261106'
        for enc in ('e5','bge-m3','labse'):
            ref=np.load(base/(enc+'_embeddings.npy')); depth['embedding_rsa'][enc]=float(spearmanr(gx,geometry(ref)).statistic)
        result['depths'].append(depth)
        print(model,'layer',layer+1,'complete',flush=True)
    np.savez_compressed(out/'lexical_probe_directions.npz',**directions)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--capture',type=Path,required=True); p.add_argument('--model',choices=['qwen','olmo7b','mistral7b'],required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); analyze(a.capture,a.model,a.output)
