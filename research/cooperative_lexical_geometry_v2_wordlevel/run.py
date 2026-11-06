"""Descriptive pilot only; input is frozen by hash before model loading."""
import argparse, hashlib, itertools, json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--expected-sha256',required=True)
p.add_argument('--local-files-only',action='store_true')
p.add_argument('--batch-size',type=int,default=16)
a=p.parse_args()
raw=(root/'lexicon.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=a.expected_sha256: raise SystemExit('Lexicon hash mismatch')
rows=json.loads(raw); langs=['en','fr','zh','ja','ar']; cats=sorted({r['category'] for r in rows})
from sentence_transformers import SentenceTransformer
models={'e5':('intfloat/multilingual-e5-base','d13f1b27baf31030b7fd040960d60d909913633f','query: '),
        'bge-m3':('BAAI/bge-m3','3806044eb869c8756693584f7eb5dd04ab2bdd95',''),
        'labse':('sentence-transformers/LaBSE','b7f9471','')}
out=root/'results'; out.mkdir(exist_ok=True)
for name,(model_id,rev,prefix) in models.items():
    print('Loading',model_id,rev,flush=True)
    model=SentenceTransformer(model_id,revision=rev,local_files_only=a.local_files_only)
    texts=[prefix+r[l] for r in rows for l in langs]
    emb=model.encode(texts,batch_size=a.batch_size,normalize_embeddings=True,convert_to_numpy=True)
    np.save(out/f'{name}_embeddings.npy',emb)
    results={}
    for view in ['raw','centered']:
        x=emb.copy()
        if view=='centered':
            for li in range(len(langs)):
                ix=np.arange(li,len(x),len(langs)); x[ix]-=x[ix].mean(axis=0); x[ix]/=np.linalg.norm(x[ix],axis=1,keepdims=True)
        sim=x@x.T; np.save(out/f'{name}_{view}_cosine.npy',sim)
        results[view]={}
        for cat in cats:
            ids=[i for i,r in enumerate(rows) if r['category']==cat]; n=len(ids)
            within={l:float(sim[np.ix_([i*5+j for i in ids],[i*5+j for i in ids])][np.triu_indices(n,1)].mean()) for j,l in enumerate(langs)}
            cross={}; exact={}
            for j,k in itertools.combinations(range(5),2):
                block=sim[np.ix_([i*5+j for i in ids],[i*5+k for i in ids])]
                cross[langs[j]+'-'+langs[k]]=float(block[~np.eye(n,dtype=bool)].mean())
                exact[langs[j]+'-'+langs[k]]=float(np.diag(block).mean())
            results[view][cat]={'within_language':within,'cross_language_distinct':cross,'exact_translation_control':exact}
    (out/f'{name}_summary.json').write_text(json.dumps({'model':model_id,'revision':rev,'lexicon_sha256':a.expected_sha256,'status':'provisional_unreviewed','results':results},indent=2)+'\n',encoding='utf-8')
