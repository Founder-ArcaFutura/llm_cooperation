import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reanalysis", ROOT / "reanalyze.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def make_rows():
    return [
        {"concept_id": f"{cat[:3].upper()}-{domain:02d}-{kernel:02d}", "category": cat,
         "domain": f"d{domain:02d}", "terms": {"en": "x"}}
        for cat in module.CATS for domain in range(1, 11) for kernel in range(1, 16)
    ]

def test_pair_estimands_have_expected_counts():
    rows = make_rows()
    masks = module.pair_masks(rows, rows[:150])
    assert int(masks["within_all_distinct_concepts"].sum()) == 11175
    assert int(masks["within_same_domain"].sum()) == 1050
    assert int(masks["within_excluding_repeated_kernel"].sum()) == 10500
    assert int(masks["cross_all_distinct_concepts"].sum()) == 22350
    assert int(masks["cross_excluding_repeated_kernel"].sum()) == 21000

def test_unit_cluster_weights_reproduce_direct_pair_mean():
    rng = np.random.default_rng(7)
    matrix = rng.normal(size=(150, 150))
    matrix = (matrix + matrix.T) / 2
    rows = make_rows()[:150]
    masks = module.pair_masks(rows, rows)
    weights = np.ones((1, 150))
    result = module.weighted_pair_mean_batch(matrix, masks["within_all_distinct_concepts"], weights)[0]
    assert np.isclose(result, module.direct_pair_mean(matrix, masks["within_all_distinct_concepts"]))

def test_crossed_pair_bootstrap_unit_weights_preserve_full_estimand():
    rng = np.random.default_rng(8)
    matrix = rng.normal(size=(150, 150))
    matrix = (matrix + matrix.T) / 2
    rows = make_rows()[:150]
    masks = module.pair_masks(rows, rows)
    domain_names = sorted({r["domain"] for r in rows})
    kernel_names = sorted({r["concept_id"].rsplit("-", 1)[1] for r in rows})
    domain_index = np.asarray([domain_names.index(r["domain"]) for r in rows])
    kernel_index = np.asarray([kernel_names.index(r["concept_id"].rsplit("-", 1)[1]) for r in rows])
    domain_draws = np.ones((3, 10), dtype=int)
    kernel_draws = np.ones((3, 15), dtype=int)
    values = module.crossed_pair_bootstrap_batch(matrix, masks["within_all_distinct_concepts"],
                                                   domain_draws, kernel_draws, domain_index, kernel_index)
    assert np.allclose(values, module.direct_pair_mean(matrix, masks["within_all_distinct_concepts"]))

def test_kernel_permutation_keeps_domain_renders_together():
    rows = make_rows()
    matrix = np.eye(600, dtype=float)
    result = module.kernel_group_permutation(matrix, rows, draws=9, seed=11)
    assert result["permutations"] == 9
    assert result["unit"].startswith("phrase-kernel cluster")
