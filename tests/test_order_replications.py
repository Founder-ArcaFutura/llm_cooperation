import json
from collections import Counter

import pytest

from llm_cooperation.items.schema import ScenarioBank, CalibrationBank
from llm_cooperation.items.permutations import (
    LATIN_SQUARE_4X4, counterbalanced_rows, generate_all_presentations,
    generate_all_calibration_presentations,
)
from llm_cooperation.analysis.order_replications import describe, paired_difference, inspect_run, inspect_calibration
from llm_cooperation.harness.runner import run_experiment, run_calibration


def test_balanced_disjoint_orders_and_unchanged_content():
    bank = ScenarioBank(**json.load(open('data/scenarios_dose_response_exploratory.json')))
    families = {s.template_family_id or s.template_id or s.id for s in bank.scenarios}
    for family in families:
        schedules = [counterbalanced_rows(family, r) for r in (0, 1, 2)]
        assert schedules[0] == LATIN_SQUARE_4X4
        assert len({tuple(row) for schedule in schedules for row in schedule}) == 12
        for schedule in schedules:
            assert all(set(row) == set(range(4)) for row in schedule)
            assert all({row[col] for row in schedule} == set(range(4)) for col in range(4))
    for rep in (0, 1, 2):
        presentations = generate_all_presentations(bank.scenarios, order_replication=rep)
        assert len(presentations) == len({p.presentation_id for p in presentations}) == 504
        scenarios = {s.id: s for s in bank.scenarios}
        for p in presentations:
            s = scenarios[p.scenario_id]
            assert p.stem == s.stem
            assert all(o.text == s.options[o.strategy] for o in p.options)
        assert Counter(p.strategy_to_letter['COOPERATE'] for p in presentations) == dict.fromkeys('ABCD', 126)


def test_families_pair_across_payoffs_and_seeds_change_orders():
    assert counterbalanced_rows('family', 1, 20261107) == counterbalanced_rows('family', 1, 20261107)
    assert len({tuple(tuple(r) for r in counterbalanced_rows('family', 1, seed)) for seed in range(10)}) > 1
    bank = ScenarioBank(**json.load(open('data/scenarios_dose_response_exploratory.json')))
    presentations = generate_all_presentations(bank.scenarios, order_replication=1)
    by_family = {}
    scenarios = {s.id:s for s in bank.scenarios}
    for p in presentations:
        family = scenarios[p.scenario_id].template_family_id
        if family:
            key = (family, p.permutation_index)
            assert key not in by_family or by_family[key] == p.letter_to_strategy
            by_family[key] = p.letter_to_strategy


def test_calibration_is_balanced_and_disjoint_too():
    bank = CalibrationBank(**json.load(open('data/calibration_bank.json')))
    all_orders = {}
    for rep in (0, 1, 2):
        rows = generate_all_calibration_presentations(bank.items, order_replication=rep)
        assert len(rows) == 96
        assert Counter(p.correct_letter for p in rows) == dict.fromkeys('ABCD',24)
        for p in rows:
            orders = all_orders.setdefault(p.item_id, set())
            order = tuple(p.letter_to_option_id[l] for l in 'ABCD')
            assert order not in orders
            orders.add(order)


def fixture_records(rep, fixed_letter=False):
    bank = ScenarioBank(**json.load(open('data/scenarios_dose_response_exploratory.json')))
    return [dict(scenario_id=p.scenario_id, strategy_to_letter=p.strategy_to_letter,
                 forced_choice_argmax_strategy=p.letter_to_strategy['A'] if fixed_letter else 'COOPERATE',
                 conditional_probs={l:(.97 if l==('A' if fixed_letter else p.strategy_to_letter['COOPERATE']) else .01) for l in 'ABCD'})
            for p in generate_all_presentations(bank.scenarios,order_replication=rep)]


def test_comparison_distinguishes_fixed_letter_from_stable_semantic_choice():
    fixed = describe(fixture_records(1,True))
    assert fixed['coop_by_position'] == dict(A=1., B=0., C=0., D=0.)
    assert fixed['scenarios_unanimous_coop'] == 0
    for rep in (0,1,2):
        semantic = describe(fixture_records(rep))
        assert semantic['coop_by_position'] == dict.fromkeys('ABCD',1.)
        assert semantic['scenarios_unanimous_coop'] == 126
        assert abs(semantic['slope_mean']) < 1e-10  # Stable preference can be flat in dose.
    assert paired_difference(fixture_records(0),fixture_records(1))['choice_diff']['mean'] == 0


def test_mock_runner_to_analysis_all_schedules(tmp_path, monkeypatch):
    runs = []
    for rep in (0,1,2):
        path=run_experiment('mock-orders',scenarios_path='data/scenarios_dose_response_exploratory.json',
                            output_dir=str(tmp_path),revision='a'*40,mock=True,device='cpu',order_replication=rep)
        meta, records = inspect_run(path,rep,20261107,allow_mock=True)
        assert len(records)==504
        with pytest.raises(ValueError,match='Mock run'):
            inspect_run(path,rep,20261107)
        cal,_=run_calibration('mock-orders',output_dir=str(tmp_path),revision='a'*40,mock=True,device='cpu',order_replication=rep)
        assert inspect_calibration(cal,rep,20261107,meta)['accuracy'] > .4
        runs.append((path,cal))
        if rep:
            with pytest.raises(ValueError,match='replication'):
                inspect_run(path,0,20261107,allow_mock=True)
    # Exercise comparison serialization and admission logic without admitting
    # synthetic fixtures into real evidence or touching repository result dirs.
    from llm_cooperation.analysis import order_replications as module
    monkeypatch.setattr(module, 'BANK', module.BANK.resolve())
    monkeypatch.setattr(module, 'CAL', module.CAL.resolve())
    monkeypatch.chdir(tmp_path)
    plan = dict(order_seed=20261107, models=[dict(model='mock-orders',baseline=str(runs[0][0]),calibration=str(runs[0][1]))],
                jobs=[dict(model='mock-orders',order_replication=r,tag=f'fixture{r}') for r in (1,2)])
    for r in (1,2):
        directory=tmp_path/'results/dose_response_orders'/f'fixture{r}'
        directory.mkdir(parents=True)
        (directory/'batch_manifest.json').write_text(json.dumps(dict(model_runs=[dict(status='complete',raw_results=str(runs[r][0]),calibration_results=str(runs[r][1]))])))
    monkeypatch.setattr(module,'audit',lambda _:plan)
    monkeypatch.setattr(module,'inspect_run',lambda path,rep,seed:inspect_run(path,rep,seed,allow_mock=True))
    module.compare('fixture-plan')
    result=json.loads((tmp_path/'reports/dose_response_order_comparison/comparison.json').read_text())
    assert [row['replica'] for row in result]==[0,1,2]
    assert (tmp_path/'reports/dose_response_order_comparison/comparison.md').is_file()


def test_new_schedules_cannot_use_other_banks(tmp_path):
    with pytest.raises(PermissionError,match='exploratory dose-response'):
        run_experiment('mock-orders',mock=True,output_dir=str(tmp_path),order_replication=1)


def test_runtime_mismatch_stops_before_model_loading(tmp_path, monkeypatch):
    import torch
    monkeypatch.setattr(torch,'__version__','fixture-wrong-runtime')
    with pytest.raises(RuntimeError,match='No inference started'):
        run_experiment('unused-model',scenarios_path='data/scenarios_dose_response_exploratory.json',
                       output_dir=str(tmp_path),order_replication=1,mock=False)


@pytest.mark.parametrize('model,mock,route',[
    ('Qwen/Qwen2.5-3B',False,'run_evaluation_remote'),
    ('mistralai/Mistral-7B-v0.3',False,'run_evaluation_remote_l40s'),
    ('mock-orders',True,'run_evaluation_mock_remote'),
])
def test_modal_routes_order_controls_without_remote_execution(monkeypatch,model,mock,route):
    import modal_app
    calls=[]
    monkeypatch.setattr(getattr(modal_app,route),'remote',lambda **kwargs:calls.append(kwargs) or ('/root/results/raw.jsonl','/root/results/cal.jsonl'))
    modal_app.main(model=model,mock=mock,bank='dose-response',authorize_paid_run=True,
                   include_calibration=True,order_replication=2,order_seed=1234)
    assert calls[0]['order_replication']==2 and calls[0]['order_seed']==1234
