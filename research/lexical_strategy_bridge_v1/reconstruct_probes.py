"""Refit original raw probes using saved selected C; fail closed on prediction mismatch."""
import hashlib, json, os
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
strategies=('COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE')
paths={'qwen':ROOT/'mechanistic_artifacts/cross_model_qwen_v1','olmo7b':ROOT/'mechanistic_artifacts/cross_model_olmo7b_v1/olmo7b_full_olmo-full-01','mistral7b':ROOT/'mechanistic_artifacts/cross_model_mistral7b_v1/mistral7b_full_mistral-full-01'}
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'saved_action_analysis'/'reconstructed_original_probes'; out.mkdir(exist_ok=True)
    for key,path in paths.items():
        reportpath=ROOT/f'reports/cross_model_{key}_v1/replication_analysis.json'; report=json.loads(reportpath.read_text(encoding='utf8'))
        b=(path/'manifest.json').read_bytes(); assert report['run_sha256'] in (sha(b),sha(b.replace(b'\r\n',b'\n')))
        rows=[json.loads(s) for s in (path/'prompts.jsonl').read_text(encoding='utf8').splitlines()]; lookup={(r['scenario_id'],r['strategy']):r for r in rows}; sids=sorted({r['scenario_id'] for r in rows})
        ordered=[lookup[(sid,st)] for sid in sids for st in strategies]; arrays=[]; evidence=json.loads((path/'evidence_hashes.json').read_text(encoding='utf8'))
        for r in ordered:
            name='activations/'+r['prompt_id']+'.npz'; p=path/name; assert sha(p.read_bytes())==evidence[name]
            with np.load(p,allow_pickle=False) as d: arrays.append(d['residual'])
        a=np.stack(arrays).reshape(len(sids),4,8,-1); a=a-a.mean(axis=1,keepdims=True); y=np.tile(np.arange(4),len(sids)); output={}; audit={}
        for split,field in [('family','split'),('domain','domain_split')]:
            train=np.repeat([lookup[(sid,strategies[0])][field]=='discovery' for sid in sids],4); test=~train
            for li,layer in enumerate(report['splits'][split]['layers']):
                x=a[:,:,li].reshape(len(y),-1); old=layer['variants']['raw']; fit=LogisticRegression(C=float(old['C']),max_iter=500,solver='lbfgs',random_state=42).fit(x[train],y[train]); pred=fit.predict(x[test]); mismatch=int(np.sum(pred!=np.array(old['eval_predictions'])))
                audit[f'{split}_{li}']={'C':old['C'],'prediction_mismatches':mismatch}
                if mismatch: raise ValueError(f'{key} {split} layer {li} has {mismatch} historical prediction mismatches; coefficients not accepted')
                output[f'{split}_{li}_coef']=fit.coef_; output[f'{split}_{li}_intercept']=fit.intercept_; output[f'{split}_{li}_classes']=fit.classes_
            print(key,split,'verified',flush=True)
        np.savez_compressed(out/(key+'_coefficients.npz'),**output)
        (out/(key+'_audit.json')).write_text(json.dumps({'report_sha256':sha(reportpath.read_bytes()),'strategy_order':strategies,'preprocessing':'within-scenario mean across four action activations; no scaling','fits':audit,'note':'Refitted using saved selected C and matching held-out predictions; matching predictions does not prove bit-identical original coefficients.'},indent=2)+'\n',encoding='utf8')
if __name__=='__main__': main()
