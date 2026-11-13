import copy
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'scripts/factorial_cooperation_design.py'
loader = importlib.util.spec_from_file_location('factorial_design', path)
m = importlib.util.module_from_spec(loader)
loader.loader.exec_module(m)


def sample():
    spec = m.specification()
    spec['families'] = spec['families'][:1]
    spec['blocks'] = spec['blocks'][1:2]
    cells = [m.condition(spec['families'][0], spec['blocks'][0], r, i)
             for i, r in enumerate(m.expand(spec['blocks'][0]))]
    return spec, cells, list(m.presentations(cells))


def test_complete_cross_and_counterbalance():
    spec, cells, rows = sample()
    assert len(cells) == 4 and len(rows) == 416
    assert not m.validate(spec, cells, rows)
    assert len(m.comparisons(cells)) == 4
    assert m.digest(rows) == m.digest(list(m.presentations(cells)))


def test_reject_missing_cell_and_missing_order():
    spec, cells, rows = sample()
    assert 'missing, invalid or duplicated design cells' in m.validate(spec, cells[:-1], rows)
    assert 'permutation coverage mismatch' in m.validate(spec, cells, rows[1:])


def test_reject_incorrect_outcomes_and_mapping():
    spec, cells, rows = sample()
    cells[0]['outcomes']['target']['actor_today_minutes'] += 1
    rows[0]['options']['A'] = 'Unrelated action'
    errors = m.validate(spec, cells, rows)
    assert 'cost ledger mismatch' in errors and 'text mapping mismatch' in errors


def test_constraints_filter_instead_of_multiply():
    block = copy.deepcopy(m.specification()['blocks'][1])
    block['constraints'] = [{'exclude_if': {'return': 1, 'cost': 20}, 'reason': 'test exclusion'}]
    rows = list(m.expand(block))
    assert len(rows) == 3
    assert not any(r['return'] == 1 and r['cost'] == 20 for r in rows)


def test_incoherent_cells_are_screened_not_generated():
    grid = m.feasibility()
    assert len(grid) == 56
    assert all(r['status'] == 'incoherent' for r in grid if r['mechanism'] == 'parallel_activity' and (r['return'] or r['dependency']))
    assert all(r['status'] == 'incoherent' for r in grid if r['mechanism'] == 'exchange' and not r['return'])


def test_return_and_necessity_outcomes_are_explicit():
    spec, cells, _ = sample()
    for c in cells:
        assert c['outcomes']['target']['actor_future_minutes_saved'] == 10 * c['factors']['return']
    b = m.specification()['blocks'][2]
    dep = [m.condition(spec['families'][0], b, r, i) for i, r in enumerate(m.expand(b))]
    assert all(c['outcomes']['reference']['counterpart_extra_check'] == (not c['factors']['dependency']) for c in dep)
    assert all(c['outcomes']['reference']['actor_extra_check'] == (not c['factors']['dependency']) for c in dep)


def test_complete_build_provenance_rank_and_blind_export(tmp_path):
    import hashlib
    import json
    m.build(tmp_path)
    results = json.loads((tmp_path / 'validation_results.json').read_text(encoding='utf-8'))
    assert results['conditions'] == 44 and results['presentations'] == 4576
    assert results['comparisons'] == 114 and results['full_rank_blocks']
    review = json.loads((tmp_path / 'review_packets_blind.json').read_text(encoding='utf-8'))
    assert len(review) == 352
    assert all(set(r) == {'review_id', 'stem', 'options', 'ratings'} for r in review)
    assert len({r['review_id'] for r in review}) == 352
    manifest = json.loads((tmp_path / 'input_manifest.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((m.ROOT / p).read_bytes()).hexdigest() == value for p, value in manifest.items())


def test_cost_pairs_reject_hidden_outcome_changes():
    spec, cells, rows = sample()
    cells[0]['outcomes']['target']['counterpart_today_minutes'] += 10
    assert 'cost pair changed a held outcome' in m.validate(spec, cells, rows)
