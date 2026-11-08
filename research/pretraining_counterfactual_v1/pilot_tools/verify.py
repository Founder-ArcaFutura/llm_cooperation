"""Read-only verification of the committed compact pilot; no cache/model needed."""
import gzip
import hashlib
import json
import random
import numpy as np

from research.pretraining_counterfactual_v1.data import file_hash, semantic_scores
from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT


def require(value,message):
    if not value:
        raise ValueError(message)


def verify():
    p=DEFAULT_REPORT
    inventory=json.loads((p/'artifact_manifest.json').read_text())
    for name,expected in inventory['files'].items():
        require(file_hash(p/name)==expected,f'Artifact hash mismatch: {name}')
    contents=gzip.decompress((p/'scores.jsonl.gz').read_bytes())
    require(hashlib.sha256(contents).hexdigest()==inventory['uncompressed_scores_sha256'],'Score decompression hash')
    scores=[json.loads(x) for x in contents.splitlines()]
    index=[json.loads(x) for x in (p/'sample_index.jsonl').read_text().splitlines()]
    manifest=json.loads((p/'sample_manifest.json').read_text())
    expected=random.Random(manifest['seed']).sample(range(manifest['source_rows']),10000)
    by_id={r['source_index']:r for r in scores}
    require(len(scores)==len(by_id)==len(index)==10000,'Bounded sample cardinality')
    require(set(by_id)==set(expected)=={r['source_index'] for r in index},'Sample identity')
    require({r['source_index'] for r in index if r['smoke']}==set(expected[:500]),'Nested smoke identity')
    for r in index:
        s=by_id[r['source_index']]
        require(r['sha256']==s['sha256'],'Content-hash identity')
        require('text' not in s,'No full raw story text in scores')
        sims=np.asarray(s['cosines']); probs=np.asarray(s['proxy_probabilities'])
        require(sims.shape==probs.shape==(len(s['spans']),5),'All five window scores retained')
        require(np.isfinite(sims).all() and np.abs(sims).max()<=1.00001,'Cosine domain')
        coop,compete,recomputed=semantic_scores(sims,s['names'],manifest['config']['temperature'])
        require(np.allclose(probs,recomputed,atol=2e-6),'Softmax reconstruction')
        require(abs(coop-s['coop_present'])<2e-6 and abs(compete-s['competition_success_margin'])<2e-6,'Aggregate reconstruction')
    selected=json.loads((p/'review_selection.json').read_text())['rows']
    reviews=json.loads((p/'integrity_reviews.json').read_text())['reviews']
    require(len(reviews)==len(selected)==len({r['source_index'] for r in reviews})==140,'Integrity140 cardinality')
    require({r['source_index'] for r in selected}=={r['source_index'] for r in reviews},'Review selection identity')
    require({r['source_index'] for r in selected if r['stratum']=='independent_random'}==set(
        random.Random(manifest['seed']+1).sample(sorted(by_id),40)),'Independent random40')
    for r in reviews:
        require(r['sha256']==by_id[r['source_index']]['sha256'],'Review source provenance')
        require(r['review_status']=='PROVISIONAL_LLM_ASSISTED_NOT_HUMAN_GOLD','Review authority')
    print(json.dumps({'verified_artifacts':len(inventory['files']),'verified_scores':10000,
                      'verified_reviews':140,'network_calls':0,'model_loads':0}))


if __name__=='__main__':
    verify()
