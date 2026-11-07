"""Freeze, audit and compare exploratory option-order replications; no inference."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

from llm_cooperation.analysis.metrics import load_run_results
from llm_cooperation.items.schema import ScenarioBank, CalibrationBank
from llm_cooperation.items.permutations import (
    generate_all_presentations, generate_all_calibration_presentations, counterbalanced_rows, ORDER_RUNTIME_V1,
)

BANK = Path('data/scenarios_dose_response_exploratory.json')
CAL = Path('data/calibration_bank.json')
ENGINE = Path('llm_cooperation/items/permutations.py')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def banks():
    return ScenarioBank(**json.loads(BANK.read_text(encoding='utf-8'))), CalibrationBank(**json.loads(CAL.read_text(encoding='utf-8')))


def schedule_hash(presentations):
    return hashlib.sha256(json.dumps([(p.presentation_id, p.prompt_text) for p in presentations],
                                    ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def inspect_run(path, replica, seed, allow_mock=False):
    meta, records = load_run_results(str(path), validate=True)
    if meta.get('mock') and not allow_mock:
        raise ValueError('Mock run cannot be admitted as real replication evidence')
    bank, _ = banks()
    expected = generate_all_presentations(bank.scenarios, order_replication=replica, order_seed=seed)
    if meta.get('order_replication', 0) != replica:
        raise ValueError('Run has the wrong order replication')
    if meta.get('scenario_bank_hash') != hashlib.sha256(BANK.read_bytes()).hexdigest():
        raise ValueError('Scenario bank mismatch')
    if replica and (meta.get('order_seed') != seed or meta.get('presentation_schedule_hash') != schedule_hash(expected)):
        raise ValueError('Order seed or sealed prompt schedule mismatch')
    mapping = {p.presentation_id: p for p in expected}
    if set(mapping) != {r['presentation_id'] for r in records}:
        raise ValueError('Presentation inventory differs from prepared schedule')
    for r in records:
        p = mapping[r['presentation_id']]
        if r['letter_to_strategy'] != p.letter_to_strategy or r['strategy_to_letter'] != p.strategy_to_letter:
            raise ValueError('Actual strategy mapping differs from prepared schedule')
        if (r['forced_choice_argmax_strategy'] != r['letter_to_strategy'][r['forced_choice_argmax_letter']] or
            r['conditional_probs'][r['forced_choice_argmax_letter']] < max(r['conditional_probs'].values())):
            raise ValueError('Recorded strategy choice does not match candidate scores and mapping')
    return meta, records


def inspect_calibration(path, replica, seed, model_meta):
    lines = [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    meta, rows = lines[0], lines[1:]
    _, cal = banks()
    expected = generate_all_calibration_presentations(cal.items, order_replication=replica, order_seed=seed)
    if len(rows) != len(expected) or len({r['presentation_id'] for r in rows}) != len(expected):
        raise ValueError('Calibration record count/identity failure')
    if (meta.get('mock') != model_meta.get('mock') or meta['model_name'] != model_meta['model_name'] or
        meta.get('model_revision') != model_meta.get('model_revision') or meta.get('order_replication', 0) != replica or
        meta.get('calibration_bank_hash') != hashlib.sha256(CAL.read_bytes()).hexdigest() or
        (replica and meta.get('order_seed') != seed)):
        raise ValueError('Calibration provenance mismatch')
    mapping = {p.presentation_id: p for p in expected}
    for row in rows:
        p = mapping.get(row['presentation_id'])
        if p is None or row['letter_to_option_id'] != p.letter_to_option_id or row['correct_letter'] != p.correct_letter:
            raise ValueError('Calibration mapping mismatch')
        probs = row['conditional_probs']
        if (set(probs) != set('ABCD') or not all(np.isfinite(v) and 0<=v<=1 for v in probs.values()) or
            abs(sum(probs.values())-1)>1e-4 or
            probs[row['forced_choice_argmax_letter']] < max(probs.values()) or
            row['is_forced_choice_correct'] != (row['forced_choice_argmax_letter']==p.correct_letter)):
            raise ValueError('Invalid calibration scores or correctness flag')
    return dict(accuracy=float(np.mean([r['is_forced_choice_correct'] for r in rows])),
                generated_validity=float(np.mean([r['is_valid_letter'] for r in rows])),
                letter_distribution={l: sum(r['forced_choice_argmax_letter'] == l for r in rows)/len(rows) for l in 'ABCD'})


def prepare(path, seed=20261107):
    path = Path(path)
    if path.exists():
        audit(path)
        print(f'Reusing frozen plan: {path}')
        return
    inventory = json.loads(Path('configs/dose_response_expansion_inventory.json').read_text())
    names = {r['model'] for r in inventory['models'] if r['expansion_status'] != 'excluded_invariant_position'}
    found = {}
    for file in sorted(Path('results/dose_response_batch').glob('*/batch_manifest.json')):
        manifest = json.loads(file.read_text(encoding='utf-8-sig'))
        for entry in manifest['model_runs']:
            name = entry['model']
            if name not in names or name in found or entry['status'] != 'complete':
                continue
            meta, rows = inspect_run(entry['raw_results'], 0, seed)
            inspect_calibration(entry['calibration_results'], 0, seed, meta)
            if meta['prompt_mode'] != 'standard_plaintext' or len(meta.get('model_revision') or '') != 40:
                raise ValueError('Baseline requires pinned revision and standard plaintext')
            if any(meta.get(k) != v for k,v in ORDER_RUNTIME_V1.items()):
                raise ValueError('Baseline numerical runtime differs from frozen order protocol')
            found[name] = dict(model=name, revision=meta['model_revision'], baseline=entry['raw_results'],
                               calibration=entry['calibration_results'], baseline_digest=digest([meta, rows]),
                               precision=meta['precision'], model_seed=meta['seed'])
    if set(found) != names:
        raise ValueError(f'Missing complete baselines: {sorted(names-set(found))}')
    bank, _ = banks()
    plan = dict(version='disjoint_rotation_orbits_v1', order_seed=seed, runtime=ORDER_RUNTIME_V1,
                bank_sha256=hashlib.sha256(BANK.read_bytes()).hexdigest(),
                calibration_sha256=hashlib.sha256(CAL.read_bytes()).hexdigest(),
                engine_sha256=hashlib.sha256(ENGINE.read_text(encoding='utf-8').encode()).hexdigest(), models=list(found.values()), jobs=[],
                schedules={str(rep): schedule_hash(generate_all_presentations(bank.scenarios, order_replication=rep, order_seed=seed)) for rep in (0,1,2)},
                rows_by_family={family: {str(rep): counterbalanced_rows(family, rep, seed) for rep in (0,1,2)}
                                for family in sorted({s.template_family_id or s.template_id or s.id for s in bank.scenarios})})
    for row in plan['models']:
        slug = row['model'].replace('/', '_')
        for replica in (1, 2):
            plan['jobs'].append(dict(model=row['model'], revision=row['revision'], order_replication=replica,
                                     tag=f'{slug}_order{replica}_s{seed}', model_seed=row['model_seed'], precision=row['precision']))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
    audit(path)
    print(f'Prepared {len(plan["jobs"])} jobs: {path}')


def audit(path):
    plan = json.loads(Path(path).read_text())
    if plan['runtime'] != ORDER_RUNTIME_V1:
        raise ValueError('Frozen runtime changed')
    for key, file in [('bank_sha256',BANK),('calibration_sha256',CAL),('engine_sha256',ENGINE)]:
        content = file.read_text(encoding='utf-8').encode() if file == ENGINE else file.read_bytes()
        if plan[key] != hashlib.sha256(content).hexdigest():
            raise ValueError(f'Frozen {key} changed')
    bank, _ = banks()
    for rep in (0,1,2):
        if plan['schedules'][str(rep)] != schedule_hash(generate_all_presentations(bank.scenarios, order_replication=rep, order_seed=plan['order_seed'])):
            raise ValueError('Prepared schedule hash changed')
    for row in plan['models']:
        meta, records = inspect_run(row['baseline'], 0, plan['order_seed'])
        if (meta['model_name'] != row['model'] or meta['model_revision'] != row['revision'] or
            meta['precision'] != row['precision'] or meta['seed'] != row['model_seed']):
            raise ValueError('Frozen baseline parameters changed')
        if digest([meta, records]) != row['baseline_digest']:
            raise ValueError('Baseline evidence changed')
        inspect_calibration(row['calibration'], 0, plan['order_seed'], meta)
        jobs = [j for j in plan['jobs'] if j['model']==row['model']]
        if sorted(j['order_replication'] for j in jobs) != [1, 2]:
            raise ValueError('Plan must have exactly two replications per model')
        for job in jobs:
            tag = f"{row['model'].replace('/', '_')}_order{job['order_replication']}_s{plan['order_seed']}"
            if (job['tag'] != tag or job['revision'] != row['revision'] or
                job['model_seed'] != meta['seed'] or job['precision'] != meta['precision']):
                raise ValueError('Job parameters differ from paired baseline')
    if len(plan['jobs']) != 2*len(plan['models']):
        raise ValueError('Unexpected model jobs in plan')
    for job in plan['jobs']:
        file = Path('results/dose_response_orders')/job['tag']/'batch_manifest.json'
        if file.exists():
            entries = json.loads(file.read_text(encoding='utf-8-sig'))['model_runs']
            if len(entries) != 1:
                raise ValueError('Expected one model per replication job')
            entry = entries[0]
            if entry['status'] == 'complete':
                meta, _ = inspect_run(entry['raw_results'], job['order_replication'], plan['order_seed'])
                if (meta['model_name'] != job['model'] or meta['model_revision'] != job['revision'] or
                    meta['seed'] != job['model_seed'] or meta['precision'] != job['precision']):
                    raise ValueError('Completed job does not match the frozen plan')
                inspect_calibration(entry['calibration_results'], job['order_replication'], plan['order_seed'], meta)
    return plan


def scenario_measures(records):
    groups = defaultdict(list)
    for r in records:
        groups[r['scenario_id']].append(r)
    result = {}
    for sid, rows in groups.items():
        differences, log_ratios = [], []
        for row in rows:
            differences.append(float(row['forced_choice_argmax_strategy']=='COOPERATE') - float(row['forced_choice_argmax_strategy']=='INDEPENDENT'))
            probs = row['conditional_probs']; letters = row['strategy_to_letter']
            log_ratios.append(float(np.log(max(probs[letters['COOPERATE']],1e-12)/max(probs[letters['INDEPENDENT']],1e-12))))
        result[sid] = dict(choice_diff=float(np.mean(differences)), log_diff=float(np.mean(log_ratios)),
                           unanimous_coop=all(r['forced_choice_argmax_strategy']=='COOPERATE' for r in rows),
                           coop_rate=sum(r['forced_choice_argmax_strategy']=='COOPERATE' for r in rows)/4)
    return result


def describe(records):
    bank, _ = banks(); measures = scenario_measures(records)
    main = [s for s in bank.scenarios if s.source_type=='exploratory_sweep']
    families = sorted({s.template_family_id for s in main})
    def dose(s): return float(s.payoff_spec['COOPERATE']['delta_u_actor'])
    equal = [s for s in main if dose(s)==0]
    slopes = []
    for family in families:
        items = [s for s in main if s.template_family_id==family]
        slopes.append(float(np.polyfit([dose(s) for s in items], [measures[s.id]['coop_rate'] for s in items], 1)[0]))
    rng = np.random.default_rng(20261107)
    boot = np.mean(rng.choice(slopes, (2000,len(slopes)), replace=True),axis=1)
    return dict(equal_utility_choice_diff=float(np.mean([measures[s.id]['choice_diff'] for s in equal])),
                equal_utility_log_diff=float(np.mean([measures[s.id]['log_diff'] for s in equal])),
                coop_by_position={l: float(np.mean([r['forced_choice_argmax_strategy']=='COOPERATE' for r in records if r['strategy_to_letter']['COOPERATE']==l])) for l in 'ABCD'},
                scenarios_unanimous_coop=sum(v['unanimous_coop'] for v in measures.values()),
                dose_coop={str(d):float(np.mean([measures[s.id]['coop_rate'] for s in main if dose(s)==d])) for d in sorted({dose(s) for s in main})},
                family_slopes=dict(zip(families,slopes)), slope_mean=float(np.mean(slopes)),
                family_bootstrap_slope_ci=np.quantile(boot,[.025,.975]).tolist())


def paired_difference(baseline, new):
    bank, _ = banks(); a=scenario_measures(baseline); b=scenario_measures(new)
    groups=defaultdict(list)
    for s in bank.scenarios:
        if s.source_type=='exploratory_sweep': groups[s.template_family_id].append(s.id)
    out={}
    for metric in ('choice_diff','log_diff'):
        vals=[float(np.mean([b[s][metric]-a[s][metric] for s in ids])) for ids in groups.values()]
        rng=np.random.default_rng(20261107)
        boot=np.mean(rng.choice(vals,(2000,len(vals)),replace=True),axis=1)
        out[metric]=dict(mean=float(np.mean(vals)),family_bootstrap_ci=np.quantile(boot,[.025,.975]).tolist())
    return out


def compare(path):
    plan=audit(path); output=[]
    for row in plan['models']:
        meta, baseline=inspect_run(row['baseline'],0,plan['order_seed'])
        output.append(dict(model=row['model'],replica=0,metrics=describe(baseline),calibration=inspect_calibration(row['calibration'],0,plan['order_seed'],meta)))
        for job in [j for j in plan['jobs'] if j['model']==row['model']]:
            file=Path('results/dose_response_orders')/job['tag']/'batch_manifest.json'
            manifest=json.loads(file.read_text(encoding='utf-8-sig'))
            entry=manifest['model_runs'][0]
            if entry['status']!='complete': raise ValueError(f'Incomplete job: {file}')
            rep=job['order_replication']; m,records=inspect_run(entry['raw_results'],rep,plan['order_seed'])
            for key in ('model_name','model_revision','precision','seed','prompt_mode','mock','torch_version','transformers_version'):
                if m[key]!=meta[key]: raise ValueError(f'Unpaired {key}: {file}')
            output.append(dict(model=row['model'],replica=rep,metrics=describe(records),
                               calibration=inspect_calibration(entry['calibration_results'],rep,plan['order_seed'],m),
                               paired_change=paired_difference(baseline,records)))
    out=Path('reports/dose_response_order_comparison'); out.mkdir(parents=True,exist_ok=True)
    (out/'comparison.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    lines=['# Option-order comparison','', '| Model | Schedule | Equal-utility C-I | Coop at A/B/C/D | All-four COOP scenarios | Full-range coop slope | Calibration accuracy / format |',
           '|---|---|---:|---|---:|---:|---|']
    for r in output:
        m=r['metrics']; c=r['calibration']; positions='/'.join(f'{v:.1%}' for v in m['coop_by_position'].values())
        lines.append(f"| {r['model']} | {r['replica']} | {m['equal_utility_choice_diff']:+.3f} | {positions} | {m['scenarios_unanimous_coop']}/126 | {m['slope_mean']:+.3f} | {c['accuracy']:.1%} / {c['generated_validity']:.1%} |")
    lines += ['', 'Schedule 0 is the original baseline. Dose curves, family slopes and paired main-sweep changes with six-family bootstrap intervals are in comparison.json. All slopes and resamples use the same full observed dose range. Calibration options also change across schedules; words/payoffs remain fixed. These are paired order perturbations, not independent model training replications. Flat, reversed and unstable effects must be retained. Stability does not establish numerical payoff reasoning. No extrapolated crossover is treated as observed.']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Comparison saved: {out}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','audit','compare'])
    parser.add_argument('--plan',default='research/dose_response_order_replications_v1/plan.json')
    parser.add_argument('--seed',type=int,default=20261107)
    args=parser.parse_args()
    if args.action=='prepare': prepare(args.plan,args.seed)
    elif args.action=='audit': audit(args.plan); print('Frozen plan and baseline audit: PASS')
    else: compare(args.plan)
