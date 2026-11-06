#!/usr/bin/env python3
"""Run a fail-closed, offline feasibility scan; no source records are changed."""
import hashlib, itertools, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_cooperation.items.controlled_repair_engine import BANKS, STRATEGIES, collision, jaccard_similarity, measure, quartets, select_joint
from scripts.repair_controlled_banks_phase1 import reconstruct_effective_dataset

ROOT = Path(__file__).resolve().parents[1]
REV = '8faed761d45a263340a0528343f099c05c9a4323'
PILOT = [1,6,8,10,11,12,13,0,4,9,15,17,18,20]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical_sha(path): return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()

def run(indices, tok, records, scenarios):
    start=time.perf_counter(); results=[]
    for i in indices:
        records_i={b:records[f'{i:03d}_{b}'] for b in BANKS}
        fixed={b:r['options'] for b,r in records_i.items() if r['accepted_automatic_constraints']}
        original={b:r['options'] for b,r in records_i.items() if b not in fixed}
        pools={b:quartets(tok,scenarios[i]['stem'],v) for b,v in original.items()}
        selected=select_joint(fixed,pools,original)
        final={**fixed,**selected}; collisions=[]
        for a,b in itertools.combinations(final,2):
            for s in STRATEGIES:
                x,y=final[a][s],final[b][s]; j=jaccard_similarity(x,y)
                if x.strip().casefold()==y.strip().casefold() or j>.85:
                    collisions.append({'banks':[a,b], 'strategy':s, 'jaccard':j})
        details={}
        for b,v in selected.items():
            acts, prompts=measure(tok,scenarios[i]['stem'],v)
            details[b]={'options':v,'action_tokens':acts,'full_prompt_tokens':prompts,
                        'semantic_review':'UNADJUDICATED',
                        'edits':{s:{'before':original[b][s], 'after':v[s]} for s in STRATEGIES if original[b][s]!=v[s]}}
        reasons={b: ('no_eligible_token_valid_quartet' if not pools[b] else 'no_compatible_joint_selection') for b in original if b not in selected}
        results.append({'scenario_index':i,'scenario_id':scenarios[i]['id'],'initial_accepted':sorted(fixed),
                        'candidate_quartet_counts':{b:len(v) for b,v in pools.items()},
                        'selected':details,'unresolved':reasons,'final_collisions':collisions})
    return {'indices':list(indices),'results':results,'elapsed_seconds':round(time.perf_counter()-start,6),
            'summary':{'new_variants':sum(len(r['selected']) for r in results),
                       'new_triads':sum(len(r['initial_accepted'])<3 and len(r['initial_accepted'])+len(r['selected'])==3 for r in results),
                       'collision_count':sum(len(r['final_collisions']) for r in results),
                       'transformed_actions_pending_review':sum(len(v['edits']) for r in results for v in r['selected'].values())}}

def main():
    # Resolve a revision snapshot explicitly; avoids Transformers' model-name network lookup.
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    snapshot=snapshot_download('Qwen/Qwen2.5-1.5B',revision=REV,local_files_only=True)
    tok=AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
    source=ROOT/'data/scenarios_phase0b_utility_matched.json'; overlay=ROOT/'research/controlled_rewrites/production01_repaired/repaired_records.json'
    prod=ROOT/'research/controlled_rewrites/production01'
    scenarios=json.loads(source.read_text(encoding='utf8'))['scenarios']
    records=reconstruct_effective_dataset(str(prod),overlay)
    provenance={'frozen_source_sha256':sha(source),'overlay_sha256':sha(overlay), 'frozen_source_canonical_sha256':canonical_sha(source), 'overlay_canonical_sha256':canonical_sha(overlay),
                'production_files_canonical_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):canonical_sha(p) for p in sorted(prod.rglob('*')) if p.is_file()},
                'tokenizer_model':'Qwen/Qwen2.5-1.5B','tokenizer_revision':REV,
                'tokenizer_files_sha256':{p.name:sha(p) for p in sorted(Path(snapshot).iterdir()) if p.is_file()},
                'semantic_status':'UNADJUDICATED','scientific_use_allowed':False,'paid_inference':False}
    for name, indices in [('pilot',PILOT),('full_scan',range(len(scenarios)))]:
        report={'provenance':provenance,**run(indices,tok,records,scenarios)}
        dest=ROOT/f'reports/controlled_repair_conservative_{name}.json'
        dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
        print(name,report['summary'],flush=True)
if __name__=='__main__': main()
