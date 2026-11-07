"""Compare saved historical directions and evaluation predictions to prior semantic analysis."""
import hashlib, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]; out=Path(__file__).resolve().parent/'saved_action_analysis'
rows=[json.loads(x) for x in (out/'actions.jsonl').read_text(encoding='utf8').splitlines()]
results=json.loads((out/'results.json').read_text(encoding='utf8'))
historical=['COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE']
lookup={(r['scenario_id'],r['strategy']):r for r in rows}
paths={'qwen':ROOT/'mechanistic_artifacts/cross_model_qwen_v1','olmo7b':ROOT/'mechanistic_artifacts/cross_model_olmo7b_v1/olmo7b_full_olmo-full-01','mistral7b':ROOT/'mechanistic_artifacts/cross_model_mistral7b_v1/mistral7b_full_mistral-full-01'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
result={}
for model,path in paths.items():
    reportpath=ROOT/f'reports/cross_model_{model}_v1/replication_analysis.json'; report=json.loads(reportpath.read_text(encoding='utf8'))
    manifest_bytes=(path/'manifest.json').read_bytes()
    assert report['run_sha256'] in (sha(path/'manifest.json'),hashlib.sha256(manifest_bytes.replace(b'\r\n',b'\n')).hexdigest())
    acts={r['prompt_id']:np.load(path/'activations'/f"{r['prompt_id']}.npz",allow_pickle=False)['residual'] for r in rows}
    sids=sorted({r['scenario_id'] for r in rows}); ordered=[lookup[(sid,st)] for sid in sids for st in historical]
    a=np.stack([acts[r['prompt_id']] for r in ordered]).reshape(len(sids),4,8,-1); a=a-a.mean(axis=1,keepdims=True)
    result[model]={'report_sha256':sha(reportpath),'splits':{}}
    for split,field,group in [('family','split','group_key'),('domain','domain_split','domain')]:
        meta=[lookup[(sid,historical[0])] for sid in sids]; train=np.array([r[field]=='discovery' for r in meta]); groups=np.array([r[group] for r in meta]); groupmeans=np.stack([a[train & (groups==g)].mean(axis=0) for g in sorted(set(groups[train]))]).mean(axis=0)
        expected=groupmeans-(groupmeans.sum(axis=0,keepdims=True)-groupmeans)/3
        held=[r for r in ordered if r[field]!='discovery']; semantic_order=[r for r in rows if r[field]!='discovery']; idx={r['prompt_id']:i for i,r in enumerate(semantic_order)}
        layers=[]
        for depth,layer in enumerate(report['splits'][split]['layers']):
            raw=layer['variants']['raw']; diffs=[np.max(np.abs(np.array(raw['directions'][st]['direction'])-expected[k,depth])) for k,st in enumerate(historical)]
            if max(diffs)>1e-5: raise ValueError(f'historical direction mismatch {model} {split} {depth}: {max(diffs)}')
            pred=np.array(raw['eval_predictions']); assert len(pred)==len(held)
            old=[historical[int(i)] for i in pred]
            agreement={}
            for enc in ('e5','bge-m3','labse'):
                sem=results['splits'][split]['semantic'][enc]['all_concepts']['predictions']; sem=[results['strategies'][sem[idx[r['prompt_id']]]] for r in held]
                agreement[enc]=float(np.mean(np.array(sem)==old))
            layers.append({'depth':depth,'block_index':layer['block_index'],'direction_reconstruction_max_abs_diff':float(max(diffs)),'semantic_historical_prediction_agreement':agreement})
        result[model]['splits'][split]=layers
(out/'historical_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('Verified historical saved directions and compared original held-out predictions.')
