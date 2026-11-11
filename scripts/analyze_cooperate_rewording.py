"""Analyze paired wording runs, resampling template clusters (exploratory)."""
import argparse,json,random,statistics
from collections import Counter,defaultdict
from pathlib import Path


def rate_margin(pairs, wording, field):
    eligible=[]
    for pair in pairs:
        r=pair[wording]
        if field=='forced':
            f=r.get('forced_choice')
            if not f or f.get('tied_max_count',0)!=1: continue
            strategy=f['strategy']
        else:
            strategy=r.get('generated_strategy')
            if strategy is None: continue
        eligible.append(strategy)
    if not eligible: return None
    return (eligible.count('COOPERATE')-eligible.count('INDEPENDENT'))/len(eligible)

def summarize(pairs,field,bootstrap,seed):
    # Compare the same presentations, excluding either invalid/tied side.
    clean=[]
    for p in pairs:
        if field=='forced':
            if any(not p[w].get('forced_choice') or p[w]['forced_choice'].get('tied_max_count')!=1 for w in ('original','paraphrase')): continue
        elif any(p[w].get('generated_strategy') is None for w in ('original','paraphrase')): continue
        clean.append(p)
    clusters=defaultdict(list)
    for p in clean:
        item=p['original']
        cluster=('triad',item['triad_id']) if item.get('triad_id') else ('template',item['template_id'])
        clusters[cluster].append(p)
    if not clusters: return {'paired_presentations':0,'excluded_pairs':len(pairs),'clusters':0}
    orig=rate_margin(clean,'original',field); para=rate_margin(clean,'paraphrase',field)
    # A bootstrap replicate only needs the signed counts and number of pairs
    # per cluster; aggregating first preserves the presentation-weighted estimand.
    groups=[]
    for group in clusters.values():
        group_orig=sum((1 if (p['original']['forced_choice']['strategy'] if field=='forced' else p['original']['generated_strategy'])=='COOPERATE' else -1 if (p['original']['forced_choice']['strategy'] if field=='forced' else p['original']['generated_strategy'])=='INDEPENDENT' else 0) for p in group)
        group_para=sum((1 if (p['paraphrase']['forced_choice']['strategy'] if field=='forced' else p['paraphrase']['generated_strategy'])=='COOPERATE' else -1 if (p['paraphrase']['forced_choice']['strategy'] if field=='forced' else p['paraphrase']['generated_strategy'])=='INDEPENDENT' else 0) for p in group)
        groups.append((group_orig,group_para,len(group)))
    rng=random.Random(seed); samples=[]; orig_samples=[]; para_samples=[]
    for _ in range(bootstrap):
        draw=[rng.choice(groups) for _ in groups]
        denom=sum(x[2] for x in draw)
        original_sample=sum(x[0] for x in draw)/denom
        paraphrase_sample=sum(x[1] for x in draw)/denom
        orig_samples.append(original_sample); para_samples.append(paraphrase_sample)
        samples.append(paraphrase_sample-original_sample)
    samples.sort(); orig_samples.sort(); para_samples.sort()
    def percentile(values,q):
        x=(len(values)-1)*q;lo=int(x);hi=min(lo+1,len(values)-1)
        return values[lo]+(values[hi]-values[lo])*(x-lo)
    def interval(values): return [percentile(values,.025),percentile(values,.975)]
    counts={}
    for w in ('original','paraphrase'):
        values=[p[w]['forced_choice']['strategy'] if field=='forced' else p[w]['generated_strategy'] for p in clean]
        counts[w]=dict(Counter(values))
    return {'paired_presentations':len(clean),'excluded_pairs':len(pairs)-len(clean),'clusters':len(groups),
      'strategy_counts':counts,'original_coop_minus_independent':orig,'paraphrase_coop_minus_independent':para,
      'change_paraphrase_minus_original':para-orig,'change_95pct_template_bootstrap_ci':interval(samples),
      'original_margin_95pct_template_bootstrap_ci':interval(orig_samples),
      'paraphrase_margin_95pct_template_bootstrap_ci':interval(para_samples),
      'bootstrap_resamples':bootstrap}

def analyze(rows, bootstrap=2000,seed=42):
    grouped=defaultdict(dict)
    for r in rows:
        key=(r['bank'],r['scenario_id'],r['permutation_index'])
        if r['wording'] in grouped[key]: raise ValueError(f'duplicate presentation {key}')
        grouped[key][r['wording']]=r
    if any(set(v)!= {'original','paraphrase'} for v in grouped.values()): raise ValueError('Incomplete original/paraphrase pairing')
    output={}
    for bank in sorted({k[0] for k in grouped}):
        all_pairs=[v for k,v in grouped.items() if k[0]==bank]
        strata={'all':all_pairs}
        for attr in ('context_type','utility_condition','split'):
            vals=sorted({str(p['original'].get(attr)) for p in all_pairs if p['original'].get(attr) is not None})
            for val in vals:
                strata[f'{attr}={val}']=[p for p in all_pairs if str(p['original'].get(attr))==val]
        strata['symmetric_control']=[p for p in all_pairs if p['original'].get('is_symmetric_control')]
        strata['non_control_equal_utility']=[p for p in all_pairs if p['original'].get('utility_condition')=='equal_utility' and not p['original'].get('is_symmetric_control')]
        output[bank]={key:{'positional_no_ties':summarize(ps,'forced',bootstrap,seed),
                           'strict_generated':summarize(ps,'generated',bootstrap,seed)} for key,ps in strata.items() if ps}
    return output

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run_dir',type=Path);ap.add_argument('--bootstrap',type=int,default=2000);ap.add_argument('--seed',type=int,default=42)
    args=ap.parse_args()
    if args.bootstrap<100: ap.error('--bootstrap must be at least 100')
    rows=[json.loads(x) for x in (args.run_dir/'rows.jsonl').read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    meta=json.loads((args.run_dir/'summary.json').read_text(encoding='utf-8-sig'))
    result={'model':meta['model'],'run_id':meta['run_id'],'warning':'Exploratory template/triad-cluster bootstrap; paired validity/tie exclusions may affect estimand. No multiple-testing adjustment. Semantic equivalence unvalidated.', 'banks':analyze(rows,args.bootstrap,args.seed)}
    output=args.run_dir/'paired_analysis.json';output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(output)
if __name__=='__main__': main()
