import importlib.util
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]/'research/lexical_strategy_bridge_v1'
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result

def test_multitoken_and_special_token_pooling_positions():
    capture=module('capture')
    assert capture.token_positions([(0,0),(0,2),(2,4),(0,0)],0,4)==([1,2],2)
    assert capture.token_positions([(0,0),(0,1),(2,4),(4,6),(7,8)],2,6)==([2,3],4)
    with pytest.raises(ValueError): capture.token_positions([(0,0),(0,1)],2,4)

def test_concept_bootstrap_and_category_recalls():
    analysis=module('analyze_words')
    y=np.repeat(np.arange(4),10); concepts=np.repeat(np.arange(8),5)
    result=analysis.scores(y,y.copy(),concepts)
    assert result['balanced_accuracy']==1 and result['concept_bootstrap_95']==[1,1]
    assert result['confusion_matrix']==(np.eye(4,dtype=int)*10).tolist()

def test_heldout_concepts_do_not_share_translations():
    analysis=module('analyze_words')
    ids=np.arange(200); labels=np.repeat(np.arange(4),50)
    folds=list(analysis.StratifiedKFold(5,shuffle=True,random_state=42).split(ids,labels))
    assert all(not set(ids[a]) & set(ids[b]) and set(labels[b])==set(range(4)) for a,b in folds)
    assert sorted(np.concatenate([ids[b] for _,b in folds]).tolist())==ids.tolist()

def test_modal_explicit_authorization_and_plan(monkeypatch):
    monkeypatch.setenv('SSLKEYLOGFILE','')
    spec=importlib.util.spec_from_file_location('lexical_modal',ROOT.parents[1]/'modal_lexical_word_capture.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    with pytest.raises(PermissionError): mod.validate('qwen','smoke','test',False,False,False)
    with pytest.raises(PermissionError): mod.validate('qwen','full','test',True,True,False)
    assert len(mod.validate('qwen','smoke','test',True,True,False))==3

def test_synthetic_word_analysis_end_to_end(tmp_path, monkeypatch):
    import json
    analysis=module('analyze_words'); rng=np.random.default_rng(4); rows=[]
    for c in range(200):
        for lang in analysis.LANGS: rows.append({'id':str(c),'category':analysis.CATS[c//50],'language':lang,'word':'test'})
    x=rng.normal(0,.1,(1000,8,8)); labels=np.array([analysis.CATS.index(r['category']) for r in rows]); x[np.arange(1000)[:,None],np.arange(8),labels[:,None]]+=2
    manifest={'models':{'qwen':{'indices':list(range(8))}}}
    monkeypatch.setattr(analysis,'load_capture',lambda *args:(rows,x,np.ones(1000),manifest))
    # Keep the integration test short; the bootstrap is exercised independently above.
    monkeypatch.setattr(analysis,'scores',lambda y,p,c:{'balanced_accuracy':float(np.mean(y==p))})
    monkeypatch.setattr(analysis,'spearmanr',lambda a,b:type('Result',(),{'statistic':.5})())
    monkeypatch.setattr(analysis,'ROOT',tmp_path)
    base=tmp_path/'research/cooperative_lexical_geometry_v2_wordlevel_expanded/exploratory_results_20261106'; base.mkdir(parents=True)
    for enc in ('e5','bge-m3','labse'): np.save(base/(enc+'_embeddings.npy'),rng.normal(size=(1000,8)))
    reports=tmp_path/'reports/cross_model_qwen_v1'; reports.mkdir(parents=True)
    layer={'variants':{'raw':{'directions':{s:{'direction':[1]*8} for s in analysis.STRATEGIES}}}}
    (reports/'replication_analysis.json').write_text(json.dumps({'splits':{s:{'layers':[layer]*8} for s in ('family','domain')}}))
    import hashlib
    refits=tmp_path/'refits'; refits.mkdir(); (refits/'qwen_audit.json').write_text(json.dumps({'report_sha256':hashlib.sha256((reports/'replication_analysis.json').read_bytes()).hexdigest(),'fits':{f'{s}_{i}':{'prediction_mismatches':0} for s in ('family','domain') for i in range(8)}}))
    monkeypatch.setattr(analysis,'REFIT_DIR',refits)
    class FakeArchive(dict):
        def __getitem__(self,key): return np.ones((4,8))
    original=analysis.np.load
    def fake_load(path,*args,**kwargs):
        return FakeArchive() if str(path).endswith('_coefficients.npz') else original(path,*args,**kwargs)
    monkeypatch.setattr(analysis.np,'load',fake_load)
    result=tmp_path/'out'; analysis.analyze(tmp_path,'qwen',result)
    data=json.loads((result/'results.json').read_text()); assert len(data['depths'])==8
    assert data['depths'][0]['views']['multilingual']['balanced_accuracy']>.95
    assert data['depths'][0]['views']['en_to_fr']['balanced_accuracy']>.95
