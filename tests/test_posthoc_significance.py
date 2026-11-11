from scripts.analyze_posthoc_significance import holm, randomization_tests


def test_holm_known_values():
    assert holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def test_randomization_is_seeded_and_uses_cluster_blocks():
    counts = {
        "template-a": {"COOPERATE": 8, "INDEPENDENT": 1, "COMPETE_EXPLOIT": 1, "DISENGAGE": 0},
        "template-b": {"COOPERATE": 6, "INDEPENDENT": 2, "COMPETE_EXPLOIT": 1, "DISENGAGE": 1},
    }
    a = randomization_tests(counts, ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"),
                            "COOPERATE", "INDEPENDENT", iterations=300, seed=4)
    b = randomization_tests(counts, ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE"),
                            "COOPERATE", "INDEPENDENT", iterations=300, seed=4)
    assert a == b
    assert a["clusters"] == 2 and a["presentations"] == 20
    assert a["uniform_test"]["p_mc"] >= 1 / 301
    assert a["contrast_test"]["p_mc"] >= 1 / 301
