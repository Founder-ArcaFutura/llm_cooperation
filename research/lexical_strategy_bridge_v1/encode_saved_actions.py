"""Encode the original actions on CPU, checking cached references first."""
import hashlib, json, os, sys
from pathlib import Path
import numpy as np

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['SSLKEYLOGFILE'] = ''
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import prepare, audit_embeddings
from sentence_transformers import SentenceTransformer
import torch

torch.set_num_threads(4)
base = ROOT / 'research/cooperative_lexical_geometry_v2_wordlevel_expanded'
out = Path(__file__).resolve().parent / 'saved_action_analysis'
out.mkdir(exist_ok=True)
raw, canonical, entries = prepare()
audit = audit_embeddings(raw, canonical, base / 'exploratory_results_20261106')
rows = [json.loads(x) for x in (ROOT / 'research/contrastive_full_v1/prompts.jsonl').read_text(encoding='utf-8').splitlines() if x]
assert len(rows) == 496 and len({r['prompt_id'] for r in rows}) == 496
refs = [x for x in entries if x['condition'] == 'isolated']
(out / 'reference_rows.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in refs),encoding='utf-8')
(out / 'actions.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
for key in ('e5','bge-m3','labse'):
    spec=audit[key]; prefix='query: ' if key=='e5' else ''
    print('Loading',key,flush=True)
    model=SentenceTransformer(spec['model'],revision=spec['revision'],device='cpu',local_files_only=True)
    reference=np.load(base / 'exploratory_results_20261106' / (key+'_embeddings.npy'))
    sample=np.array([0,1,2,3,4,125,249,499,749,995,996,997,998,999])
    reproduced=model.encode([prefix+refs[i]['word'] for i in sample],batch_size=8,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
    diff=float(np.max(np.abs(reproduced-reference[sample])))
    cosine=np.sum(reproduced*reference[sample],axis=1)
    print(key,'reference max difference',diff,'minimum cosine',float(cosine.min()),flush=True)
    if diff > 0.003 or cosine.min() < 0.9999:
        raise ValueError('Cached encoder does not reproduce saved reference rows')
    x=model.encode([prefix+r['action_text'] for r in rows],batch_size=8,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=True)
    np.save(out/(key+'_actions.npy'),x)
    np.save(out/(key+'_profiles.npy'),x@reference.T)
    spec['reproduction_sample_indices']=sample.tolist(); spec['reproduction_max_abs_diff']=diff; spec['reproduction_min_cosine']=float(cosine.min())
    (out/(key+'_audit.json')).write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    del model
