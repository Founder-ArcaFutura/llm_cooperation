import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "lexical_strategy_bridge_v1"))
from diagnose_rsa import cosine_matrix, effective_rank, partial_spearman, upper


def test_global_centered_cosine_matches_explicit_legacy_transform():
    x = np.array([[1.0, 0.0], [0.0, 1.0], [2.0, 1.0], [1.0, 3.0]])
    z = x - x.mean(axis=0)
    z = z / np.linalg.norm(z, axis=1, keepdims=True)
    expected = z @ z.T
    assert np.allclose(cosine_matrix(x, center="global"), expected)
    assert np.allclose(upper(expected), expected[np.triu_indices(4, 1)])


def test_language_centering_removes_group_means_before_normalization():
    x = np.array([[10.0, 0.0], [11.0, 0.0], [-10.0, 0.0], [-11.0, 0.0]])
    groups = np.array(["en", "en", "zh", "zh"])
    sim = cosine_matrix(x, center="language", groups=groups)
    assert sim[0, 1] == pytest.approx(-1.0)
    assert sim[2, 3] == pytest.approx(-1.0)
    assert np.allclose(sim[0:2, 2:4], [[-1.0, 1.0], [1.0, -1.0]])


def test_partial_spearman_controls_language_pair_group_structure():
    rng = np.random.default_rng(7)
    group = np.repeat(np.arange(4), 80)
    signal = rng.normal(size=group.size)
    x = 8 * group + signal
    y = 8 * group + rng.normal(size=group.size)
    controls = np.zeros((group.size, 1))
    original_controls = controls.copy()
    raw, group_adjusted, fully_adjusted = partial_spearman(
        x, y, group, controls
    )
    assert raw > group_adjusted
    assert abs(group_adjusted) < 0.25
    assert fully_adjusted == pytest.approx(group_adjusted)
    assert np.array_equal(controls, original_controls)


def test_effective_rank_detects_one_dimensional_geometry():
    x = np.arange(8, dtype=float)[:, None] * np.array([[1.0, 2.0, -1.0]])
    original = x.copy()
    result = effective_rank(x)
    assert result["effective_rank"] == pytest.approx(1.0)
    assert result["participation_ratio"] == pytest.approx(1.0)
    assert result["top1_variance"] == pytest.approx(1.0)
    assert np.array_equal(x, original)
