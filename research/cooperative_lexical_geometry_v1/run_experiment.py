"""Run pinned local multilingual embedding and preregistered analyses."""
from __future__ import annotations

import argparse, hashlib, itertools, json, platform, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
MODELS = {
    "multilingual-e5-base": ("intfloat/multilingual-e5-base", "d13f1b27baf31030b7fd040960d60d909913633f", "query: "),
    "bge-m3": ("BAAI/bge-m3", "3806044eb869c8756693584f7eb5dd04ab2bdd95", ""),
    "LaBSE": ("sentence-transformers/LaBSE", "b7f9471", ""),
}
CATS = ["cooperation", "competition_exploitation", "independent_action", "neutral_activity"]
LANGS = ["en", "fr", "es", "ar", "zh"]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def matrix_metrics(sim: np.ndarray, rows: list[dict], language_pair: tuple[str, str], category: str) -> tuple[float, float]:
    a, b = language_pair
    ia = [i for i, r in enumerate(rows) if r["category"] == category and a in r["terms"]]
    ib = [i for i, r in enumerate(rows) if r["category"] == category and b in r["terms"]]
    # rows share concept IDs across languages; this function's indexes are language-specific below.
    return float(np.mean(sim[np.ix_(ia, ib)])), float("nan")

def bootstrap_ci(values: list[float], rng: np.random.Generator, draws: int = 4000) -> list[float]:
    x = np.asarray(values, dtype=np.float64)
    if len(x) < 2: return [float("nan"), float("nan")]
    means = np.mean(x[rng.integers(0, len(x), size=(draws, len(x)))], axis=1)
    return [float(np.quantile(means, .025)), float(np.quantile(means, .975))]

def encode(model_id: str, revision: str, prefix: str, texts: list[str], batch: int, local_only: bool) -> np.ndarray:
    model = SentenceTransformer(model_id, revision=revision, device="cpu", local_files_only=local_only)
    try:
        model.eval()
        chunks = []
        for start in range(0, len(texts), batch):
            chunks.append(model.encode([prefix + t for t in texts[start:start+batch]], convert_to_numpy=True,
                                       normalize_embeddings=False, show_progress_bar=False))
        x = np.concatenate(chunks).astype(np.float32)
        norms = np.linalg.norm(x, axis=1, keepdims=True)
        if np.any(norms == 0): raise ValueError("Encountered zero embedding")
        return x / norms
    finally:
        del model
        if torch.cuda.is_available(): torch.cuda.empty_cache()

def compute_scores(sim: np.ndarray, keys: list[tuple[str,str]], rows: list[dict], centered: bool,
                   seed: int) -> dict:
    index = {key:i for i,key in enumerate(keys)}
    # Within-language distinct-concept pairs, first summarized at domain level.
    within_domain: dict[str,dict[str,list[float]]] = {c:{d:[] for d in sorted({r['domain'] for r in rows})} for c in CATS}
    within_lang = {c:{l:[] for l in LANGS} for c in CATS}
    for cat in CATS:
        for lang in LANGS:
            for domain in within_domain[cat]:
                ids = [index[(r['concept_id'],lang)] for r in rows if r['category']==cat and r['domain']==domain]
                block = sim[np.ix_(ids,ids)]
                vals = block[np.triu_indices(len(ids),1)]
                within_domain[cat][domain].append(float(vals.mean()))
                within_lang[cat][lang].extend(vals.tolist())
    # Cross-language pairs of distinct concepts only; exact translations are a separate positive control.
    lang_pairs = list(itertools.combinations(LANGS,2))
    cross = {c:{f'{a}-{b}':[] for a,b in lang_pairs} for c in CATS}
    cross_domain = {c:{f'{a}-{b}':{d:[] for d in sorted({r['domain'] for r in rows})} for a,b in lang_pairs} for c in CATS}
    exact = {c:[] for c in CATS}
    for cat in CATS:
        category_rows = [r for r in rows if r['category']==cat]
        for a,b in lang_pairs:
            ia = [index[(r['concept_id'],a)] for r in category_rows]
            ib = [index[(r['concept_id'],b)] for r in category_rows]
            block = sim[np.ix_(ia,ib)]
            mask = ~np.eye(len(category_rows),dtype=bool)
            # Aggregate at the domain level so repeated concepts/pairs are not treated as independent.
            for domain in cross_domain[cat][f'{a}-{b}']:
                local = [j for j,r in enumerate(category_rows) if r['domain']==domain]
                local_block = block[np.ix_(local,local)]
                cross_domain[cat][f'{a}-{b}'][domain] = local_block[~np.eye(len(local),dtype=bool)].astype(float).tolist()
            cross[cat][f'{a}-{b}'] = block[mask].astype(float).tolist()
            exact[cat].extend(np.diag(block).astype(float).tolist())
    domains = sorted(next(iter(within_domain.values())))
    rng = np.random.default_rng(seed)
    result = {"embedding_view":"centered_per_language" if centered else "raw",
              "within_language":{}, "cross_language_distinct_concepts":{}, "exact_translation_positive_control":{},
              "category_contrasts":{}, "leave_one_language_out":{}, "permutation_tests":{}}
    summary = {}
    for cat in CATS:
        domain_vals = [float(np.mean(within_domain[cat][d])) for d in domains]
        summary[cat] = float(np.mean(domain_vals))
        result['within_language'][cat] = {l:{"mean":float(np.mean(within_lang[cat][l])),"pairs":len(within_lang[cat][l])} for l in LANGS}
        result['within_language'][cat]['macro_mean'] = summary[cat]
        result['within_language'][cat]['domain_cluster_bootstrap_95ci'] = bootstrap_ci(domain_vals,rng)
        result['cross_language_distinct_concepts'][cat] = {
            p:{"mean":float(np.mean(v)),"pairs":len(v),
               "domain_cluster_bootstrap_95ci":bootstrap_ci([float(np.mean(x)) for x in cross_domain[cat][p].values()],rng)}
            for p,v in cross[cat].items()}
        result['cross_language_distinct_concepts'][cat]['macro_mean'] = float(np.mean([np.mean(v) for v in cross[cat].values()]))
        result['exact_translation_positive_control'][cat] = {"mean":float(np.mean(exact[cat])),"pairs":len(exact[cat])}
    controls = CATS[1:]
    coop_minus = summary['cooperation'] - float(np.mean([summary[c] for c in controls]))
    result['category_contrasts']['within_language_cooperation_minus_mean_controls'] = {
        "difference":coop_minus,
        "domain_cluster_bootstrap_95ci": bootstrap_ci([
            np.mean(within_domain['cooperation'][d]) - np.mean([np.mean(within_domain[c][d]) for c in controls]) for d in domains
        ],rng),
        "per_control":{c:summary['cooperation']-summary[c] for c in controls}}
    for l in LANGS:
        vals = {c:float(np.mean(within_lang[c][l])) for c in CATS}
        result['leave_one_language_out'][f'excluding_{l}'] = float(np.mean([summary[c] for c in CATS])) # replaced by pooled macro below
        kept=[x for x in LANGS if x!=l]
        result['leave_one_language_out'][f'excluding_{l}'] = {
            "cooperation_minus_mean_controls":float(np.mean([np.mean([np.mean(within_lang['cooperation'][x]) for x in kept]) - np.mean([np.mean([np.mean(within_lang[c][x]) for x in kept]) for c in controls])]))
        }
    # Concept-level category-label permutation within domain; relabel concept nodes, then recompute pair means.
    # Use English within-language matrix as the preregistered permutation statistic, and all languages as sensitivity.
    permutation = {}
    for lang in LANGS:
        obs_by_domain = {}
        blocks = {}
        for domain in domains:
            ids_by_cat = {c:[index[(r['concept_id'],lang)] for r in rows if r['category']==c and r['domain']==domain] for c in CATS}
            ids = list(itertools.chain.from_iterable(ids_by_cat.values()))
            blocks[domain] = (sim[np.ix_(ids,ids)], [c for c in CATS for _ in ids_by_cat[c]])
        observed_by_domain=[]
        for domain in domains:
            mat, labels = blocks[domain]
            labels = np.asarray(labels)
            means={}
            for cat in CATS:
                ix=np.flatnonzero(labels==cat)
                means[cat]=float(mat[np.ix_(ix,ix)][np.triu_indices(len(ix),1)].mean())
            observed_by_domain.append(means['cooperation']-np.mean([means[c] for c in controls]))
        observed = float(np.mean(observed_by_domain))
        null=[]
        for _ in range(1000):
            perdom=[]
            for domain in domains:
                mat, labels = blocks[domain]
                perm = rng.permutation(labels)
                means={}
                for cat in CATS:
                    ix=np.flatnonzero(np.asarray(perm)==cat)
                    means[cat]=float(mat[np.ix_(ix,ix)][np.triu_indices(len(ix),1)].mean())
                perdom.append(means['cooperation']-np.mean([means[c] for c in controls]))
            null.append(float(np.mean(perdom)))
        permutation[lang]={"statistic":"within-domain concept-label permutation, equal category counts; coop minus mean controls",
                           "observed":observed,"permutations":len(null),
                           "two_sided_p":float((1+sum(abs(v)>=abs(observed) for v in null))/(len(null)+1))}
    result['permutation_tests']=permutation
    # Cross-language category macro summary and paired contrast.
    cross_means={c:float(np.mean([np.mean(v) for v in cross[c].values()])) for c in CATS}
    result['category_contrasts']['cross_language_distinct_concepts_cooperation_minus_mean_controls'] = {
        "difference":cross_means['cooperation']-float(np.mean([cross_means[c] for c in controls])),
        "per_control":{c:cross_means['cooperation']-cross_means[c] for c in controls}}
    return result

def save_plot(sim: np.ndarray, keys: list[tuple[str,str]], rows: list[dict], out: Path, title: str) -> None:
    idx={k:i for i,k in enumerate(keys)}
    cats=CATS; languages=LANGS
    grid=np.zeros((len(cats)*len(languages),len(cats)*len(languages)))
    labels=[]
    for ci,c in enumerate(cats):
        for li,l in enumerate(languages):
            labels.append(f"{c}\n{l}")
            ids=[idx[(r['concept_id'],l)] for r in rows if r['category']==c]
            for cj,c2 in enumerate(cats):
                for lj,l2 in enumerate(languages):
                    ids2=[idx[(r['concept_id'],l2)] for r in rows if r['category']==c2]
                    grid[ci*len(languages)+li,cj*len(languages)+lj]=float(sim[np.ix_(ids,ids2)].mean())
    fig,ax=plt.subplots(figsize=(17,14)); im=ax.imshow(grid,cmap='viridis',vmin=-.2,vmax=1)
    ax.set_xticks(range(len(labels)),labels,rotation=90); ax.set_yticks(range(len(labels)),labels)
    ax.set_title(title); fig.colorbar(im,ax=ax,label='mean cosine'); fig.tight_layout(); fig.savefig(out,dpi=160); plt.close(fig)

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--model',choices=['all',*MODELS],default='all')
    ap.add_argument('--batch-size',type=int,default=24)
    ap.add_argument('--local-files-only',action='store_true')
    ap.add_argument('--seed',type=int,default=20261106)
    args=ap.parse_args()
    lexpath=ROOT/'lexicon_frozen.json'; manifest=json.loads((ROOT/'lexicon_freeze.json').read_text(encoding='utf-8'))
    if sha(lexpath)!=manifest['lexicon_sha256']: raise SystemExit('Lexicon hash mismatch; aborting inference.')
    rows=json.loads(lexpath.read_text(encoding='utf-8'))
    if len(rows)!=600 or any(sum(r['category']==c for r in rows)!=150 for c in CATS): raise SystemExit('Lexicon count gate failed.')
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    report={"experiment":"cooperative_lexical_geometry_v1","lexicon_sha256":manifest['lexicon_sha256'],
            "lexicon_review_status":manifest['status'],"execution":{"python":sys.version,"platform":platform.platform(),
            "torch":torch.__version__,"device":"cpu","cuda_available":torch.cuda.is_available(),"seed":args.seed},"models":{}}
    chosen=MODELS if args.model=='all' else {args.model:MODELS[args.model]}
    for model_name,(model_id,revision,prefix) in chosen.items():
        print(f"Loading {model_id}@{revision} on CPU",flush=True)
        keys=[(r['concept_id'],lang) for r in rows for lang in LANGS]
        texts=[r['terms'][lang] for r in rows for lang in LANGS]
        emb=encode(model_id,revision,prefix,texts,args.batch_size,args.local_files_only)
        if emb.shape[0]!=len(keys): raise RuntimeError('Embedding count mismatch')
        np.save(out/f'{model_name}_embeddings_normalized.npy',emb)
        sim=emb@emb.T
        np.save(out/f'{model_name}_cosine_raw.npy',sim.astype(np.float32))
        # Center per language to remove language-specific common directions; renormalize before cosine.
        centered=emb.copy()
        for li,lang in enumerate(LANGS):
            ix=np.arange(li,len(keys),len(LANGS)); centered[ix]-=centered[ix].mean(axis=0,keepdims=True)
            centered[ix]/=np.linalg.norm(centered[ix],axis=1,keepdims=True)
        simc=centered@centered.T
        np.save(out/f'{model_name}_cosine_centered.npy',simc.astype(np.float32))
        for view,matrix in [('raw',sim),('centered',simc)]:
            scores=compute_scores(matrix,keys,rows,view=='centered',args.seed)
            (out/f'{model_name}_{view}_results.json').write_text(json.dumps(scores,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            save_plot(matrix,keys,rows,out/f'{model_name}_{view}_matrix.png',f'{model_name}: category × language cosine ({view})')
        report['models'][model_name]={"model_id":model_id,"pinned_revision":revision,"encoding_prefix":prefix,
            "embedding_shape":list(emb.shape),"embedding_sha256":sha(out/f'{model_name}_embeddings_normalized.npy'),
            "raw_matrix_sha256":sha(out/f'{model_name}_cosine_raw.npy'),"centered_matrix_sha256":sha(out/f'{model_name}_cosine_centered.npy'),
            "raw_results":f'{model_name}_raw_results.json',"centered_results":f'{model_name}_centered_results.json'}
        del emb,sim,simc,centered
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    report['model_revision_source']='Hugging Face model repositories; revisions pinned in source.'
    (out/'run_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({"models_completed":list(report['models']),"out":str(out)},indent=2))

if __name__=='__main__': main()
