"""Quarantined examination of the Jules pilot and existing model candidate pools.

No function here accepts or writes repairs. The checks identify specific defects;
absence of a flag is not evidence of semantic equivalence or grammaticality.
"""
import hashlib
import itertools
import json
import re
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm_cooperation.items.controlled_repair_engine import BANKS, STRATEGIES, collision, jaccard_similarity, measure, select_joint
from scripts.repair_controlled_banks_phase1 import reconstruct_effective_dataset
from scripts.audit_controlled_production01 import BAD_PATTERNS

ARCHIVE = ROOT / 'jules_session_9218804022744716065.zip'
REV = '8faed761d45a263340a0528343f099c05c9a4323'
MAX_JOINT_OPTIONS = 30  # Explicitly bounded; nonexistence is not proven after truncation.


def sha(data): return hashlib.sha256(data).hexdigest()


def grammar_flags(text):
    flags = []
    if not text or not text[0].isupper(): flags.append('lowercase_or_missing_opening')
    if not text.endswith('.'): flags.append('missing_terminal_period')
    if any(p.search(text) for p in BAD_PATTERNS): flags.append('known_bad_padding')
    if re.search(r'\ban early docking access\b', text, re.I): flags.append('ungrammatical_early_docking_access')
    if re.search(r'\bclaim lockers\b', text, re.I): flags.append('ungrammatical_claim_lockers')
    return flags


def fact_findings(original, candidate, strategy, partner):
    """Return narrow explicit contradictions and review cues, not a semantic verdict."""
    violations, review = [], []
    lower = candidate.lower()
    if re.search(r'\bclaim lockers\b', lower): violations.append('storage_resource_corrupted_claim_lockers')
    if strategy == 'COOPERATE':
        human = bool(re.search(r'\b(?:human|person|colleague)\b', lower))
        ai = bool(re.search(r'\b(?:automated|ai|artificial intelligence)\b', lower))
        if partner == 'human' and ai and not human: violations.append('explicit_partner_type_mismatch')
        if partner == 'ai' and human and not ai: violations.append('explicit_partner_type_mismatch')
    if candidate != original:
        review.append('wording_changed_review_all_protected_facts_and_strategy')
        nums = re.findall(r'\b\d+(?:\.\d+)?\b', original)
        if any(n not in re.findall(r'\b\d+(?:\.\d+)?\b', candidate) for n in nums): review.append('numeric_literal_not_preserved')
        neg = re.compile(r'\b(?:no|not|never|without)\b', re.I)
        if bool(neg.search(original)) != bool(neg.search(candidate)): review.append('negation_word_changed')
    return violations, review


def collision_details(options, others):
    found=[]
    for bank, existing in others.items():
        for s in STRATEGIES:
            x,y=options[s],existing[s]; j=jaccard_similarity(x,y)
            if x.strip().casefold() == y.strip().casefold() or j > .85:
                found.append({'other_bank':bank,'strategy':s,'exact':x.strip().casefold()==y.strip().casefold(),'jaccard':j})
    return found


def evaluate_pilot(report, records, scenarios, tok):
    rows=[]
    for case in report['results']:
        i=case['scenario_index']; initial={b:records[f'{i:03d}_{b}']['options'] for b in case['initial_accepted']}
        proposed={b:d['options'] for b,d in case['details'].items()}
        for b,opts in proposed.items():
            base=records[f'{i:03d}_{b}']['options']; frozen=scenarios[i]['options']; acts, prompts=measure(tok,scenarios[i]['stem'],opts)
            action_span=max(acts.values())-min(acts.values()); prompt_span=max(prompts.values())-min(prompts.values())
            findings={}
            for s in STRATEGIES:
                violations,review=fact_findings(frozen[s],opts[s],s,scenarios[i]['partner_type'])
                findings[s]={'frozen_original':frozen[s], 'record_original':base[s], 'candidate':opts[s],
                             'grammar_flags':grammar_flags(opts[s]), 'protected_fact_violations':violations, 'review_cues':review}
            others={**initial,**{k:v for k,v in proposed.items() if k!=b}}
            coll=collision_details(opts,others)
            rows.append({'record_id':f'{i:03d}_{b}', 'action_tokens':acts,'prompt_tokens':prompts,
                         'action_span':action_span,'prompt_span':prompt_span,
                         'mechanical_token_pass':action_span<=1 and prompt_span<=1,
                         'reported_spans':{'action':case['details'][b]['action_span'],'prompt':case['details'][b]['prompt_span']},
                         'grammar_screen_pass':not any(x['grammar_flags'] for x in findings.values()),
                         'confirmed_fact_violation':any(x['protected_fact_violations'] for x in findings.values()),
                         'cross_bank_collisions':coll,'actions':findings,'semantic_status':'UNADJUDICATED',
                         'acceptance_status':'QUARANTINED'})
    return rows


def pool_quartets(record, scenario, tok, extra=None):
    """Enumerate raw supplied model candidates; no new word substitutions."""
    candidates={}; per_strategy={}
    for s in STRATEGIES:
        texts=list(dict.fromkeys(([extra[s]] if extra else []) + [x for x in record.get('candidate_pool',{}).get(s,[]) if isinstance(x,str) and x.strip()] + [record['options'][s]]))
        entries=[]
        for text in texts:
            original=scenario['options'][s]; violations, review=fact_findings(original,text,s,scenario['partner_type'])
            entries.append({'text':text, 'frozen_original':original, 'record_original':record['options'][s],
                            'origins':([ 'jules_serialized_pilot' ] if extra and text == extra[s] else []) + ([ 'production_candidate_pool' ] if text in record.get('candidate_pool',{}).get(s,[]) else []) + ([ 'production_current_option' ] if text == record['options'][s] else []),
                            'grammar_flags':grammar_flags(text), 'protected_fact_violations':violations,
                            'review_cues':review, 'semantic_status':'UNADJUDICATED',
                            'action_tokens':len(tok.encode(text.strip(),add_special_tokens=False)),
                            'prompt_tokens':len(tok.encode(f"{scenario['stem'].strip()}\n\nAction: {text.strip()}\nDecision:",add_special_tokens=False))})
        per_strategy[s]=entries
        candidates[s]=[x for x in entries if not x['grammar_flags'] and not x['protected_fact_violations']]
    raw_combinations=1; screened_combinations=1
    for s in STRATEGIES: raw_combinations*=len(per_strategy[s]); screened_combinations*=len(candidates[s])
    valid=[]; span_fail=0; duplicate_fail=0
    for combo in itertools.product(*(candidates[s] for s in STRATEGIES)):
        a=[x['action_tokens'] for x in combo]; p=[x['prompt_tokens'] for x in combo]
        if max(a)-min(a)>1 or max(p)-min(p)>1: span_fail+=1; continue
        if len({x['text'].casefold() for x in combo}) != 4: duplicate_fail+=1; continue
        valid.append(dict(zip(STRATEGIES,[x['text'] for x in combo])))
    return per_strategy, {'raw_combinations':raw_combinations,'post_screen_combinations':screened_combinations,
                          'token_span_failed_combinations':span_fail,'within_quartet_duplicate_combinations':duplicate_fail,
                          'token_valid_quartets':len(valid)}, valid


def scan_pools(records, scenarios, tok):
    result=[]
    for i,scen in enumerate(scenarios):
        fixed={b:records[f'{i:03d}_{b}']['options'] for b in BANKS if records[f'{i:03d}_{b}']['accepted_automatic_constraints']}
        pools={}; banks={}
        for b in BANKS:
            record=records[f'{i:03d}_{b}']
            if b in fixed: continue
            entries, counts, quads=pool_quartets(record,scen,tok)
            compatible=[q for q in quads if not collision_details(q,fixed)]
            counts.update({'fixed_bank_collision_quartets':len(quads)-len(compatible),
                           'fixed_bank_compatible_quartets':len(compatible),
                           'joint_search_truncated':len(compatible)>MAX_JOINT_OPTIONS})
            banks[b]={'actions':entries,'funnel':counts}
            pools[b]=compatible[:MAX_JOINT_OPTIONS]
        if any(pools.values()):
            selected=select_joint(fixed,pools)
        else: selected={}
        result.append({'scenario_index':i,'fixed_banks':sorted(fixed),'banks':banks,
                       'joint_selected_quarantined':selected,
                       'joint_search_complete_for_enumerated_pools':all(not x['funnel']['joint_search_truncated'] for x in banks.values()),
                       'joint_selection_status':'QUARANTINED_NOT_ACCEPTED'})
    return result



def augmented_pilot_search(pilot, records, scenarios, tok):
    """Joint search on real pilot options and production pool options, all quarantined."""
    outcomes=[]
    for row in pilot['results']:
        i=row['scenario_index']; proposed={b:d['options'] for b,d in row['details'].items()}
        if not proposed: continue
        fixed={b:records[f'{i:03d}_{b}']['options'] for b in row['initial_accepted']}
        choices={}; counts={}
        for b in BANKS:
            if b in fixed: continue
            _, funnel, valid=pool_quartets(records[f'{i:03d}_{b}'],scenarios[i],tok,proposed.get(b))
            compatible=[q for q in valid if not collision_details(q,fixed)]
            # Exhaustive search within an explicitly bounded prefix, preserving pilot-first ordering.
            counts[b]={'eligible':len(compatible),'searched':min(len(compatible),10),'truncated':len(compatible)>10}
            choices[b]=compatible[:10]
        selected=select_joint(fixed,choices)
        greedy={}
        for b in BANKS:
            if b in fixed: continue
            for q in choices[b]:
                if not any(collision(q,v) for v in list(fixed.values())+list(greedy.values())):
                    greedy[b]=q; break
        outcomes.append({'scenario_index':i,'fixed_banks':sorted(fixed),'pool_sizes':counts,
                         'joint_selected_quarantined':selected,'greedy_selected_banks':sorted(greedy),
                         'joint_collisions':[{'bank':b, **x} for b,q in selected.items() for x in collision_details(q,{**fixed,**{k:v for k,v in selected.items() if k!=b}})],
                         'semantic_status':'UNADJUDICATED', 'acceptance_status':'QUARANTINED'})
    return outcomes


def main():
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    snapshot=snapshot_download('Qwen/Qwen2.5-1.5B',revision=REV,local_files_only=True)
    tok=AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        files={x.filename:sha(z.read(x)) for x in z.infolist() if not x.is_dir()}
        pilot=json.loads(z.read('reports/controlled_repair_pilot_report.json'))
    source=ROOT/'data/scenarios_phase0b_utility_matched.json'; overlay=ROOT/'research/controlled_rewrites/production01_repaired/repaired_records.json'
    scenarios=json.loads(source.read_text(encoding='utf8'))['scenarios']
    records=reconstruct_effective_dataset(str(ROOT/'research/controlled_rewrites/production01'),overlay)
    t=time.perf_counter(); pilot_rows=evaluate_pilot(pilot,records,scenarios,tok); pools=scan_pools(records,scenarios,tok); augmented=augmented_pilot_search(pilot,records,scenarios,tok)
    out={'archive_sha256':sha(ARCHIVE.read_bytes()),'archive_member_sha256':files,'source_sha256':sha(source.read_bytes()),
         'overlay_sha256':sha(overlay.read_bytes()),'tokenizer_revision':REV,'tokenizer_snapshot_files_sha256':{p.name:sha(p.read_bytes()) for p in sorted(Path(snapshot).iterdir()) if p.is_file()},
         'status':'QUARANTINED_NO_AUTOMATIC_ACCEPTANCE','paid_inference':False,
         'limits':'Grammar and fact checks detect only explicitly enumerated defects; all candidates require independent semantic adjudication. Joint search uses at most 30 eligible quartets per bank in the raw-pool scan and 10 in the pilot-augmented scan; truncation is reported.',
         'pilot_reported_summary':pilot['summary'],'pilot':pilot_rows,'pool_scan':pools,'pilot_augmented_joint_search':augmented,'elapsed_seconds':round(time.perf_counter()-t,3)}
    dest=ROOT/'reports/controlled_repair_quarantine_diagnostics.json'
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('pilot candidates',len(pilot_rows),'pool scenarios',len(pools),'elapsed',out['elapsed_seconds'])
    print('pilot token',sum(x['mechanical_token_pass'] for x in pilot_rows),'grammar',sum(x['grammar_screen_pass'] for x in pilot_rows),'fact violation',sum(x['confirmed_fact_violation'] for x in pilot_rows),'collisions',sum(bool(x['cross_bank_collisions']) for x in pilot_rows))
    print('pilot augmented selected',sum(len(r['joint_selected_quarantined']) for r in augmented),'scenarios',len(augmented))
    print('pool eligible records',sum(v['funnel']['fixed_bank_compatible_quartets']>0 for r in pools for v in r['banks'].values()),'joint selections',sum(len(r['joint_selected_quarantined']) for r in pools))
if __name__=='__main__': main()
