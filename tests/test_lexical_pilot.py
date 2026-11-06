"""Offline safety/design regressions; synthetic fixtures are never scientific reviews."""

import numpy as np
import pytest

from llm_cooperation.mechanistic import lexical_pilot as lp
from llm_cooperation.mechanistic import lexical_pilot_run as runner
from llm_cooperation.mechanistic.lexical_pilot_analysis import (
    cosine,
    evaluate,
    interval,
    fit_nested,
)
from llm_cooperation.mechanistic.lexical_pilot_behavior import (
    competence_gate,
    format_hash,
    parse_answer,
    run_behavior,
)


@pytest.fixture(scope="module")
def tokenizer():
    try:
        return lp.MeasurementTokenizer()
    except FileNotFoundError as exc:
        pytest.skip(f"Pinned tokenizer not available: {exc}")


def test_surface_deletion_protected_words_and_exact_dose(tokenizer):
    text = (
        "Share the logs with a partner, but never share private keys before approval."
    )
    a = lp.perturbations(tokenizer, "Keep the keys private.", text, "s1", "COOPERATE")
    assert a == lp.perturbations(
        tokenizer, "Keep the keys private.", text, "s1", "COOPERATE"
    )
    assert {"low_ablation", "random_deletion", "content_deletion"} <= set(a)
    assert (
        a["low_ablation"][1]["dose"]
        == a["random_deletion"][1]["dose"]
        == a["content_deletion"][1]["dose"]
    )
    for condition in ("low_ablation", "random_deletion"):
        edited, record = a[condition]
        assert lp.signature(edited) == lp.signature(text)
        assert record["deleted_span"]["text"].lower() not in lp.PROTECTED
        assert "[MASK]" not in edited


def test_no_eligible_article_is_not_silent_success(tokenizer):
    result = lp.perturbations(
        tokenizer, "Stem.", "Process your logs independently.", "s2", "INDEPENDENT"
    )
    assert "low_ablation" not in result and "random_deletion" not in result


def test_capture_and_behavior_boundaries_real_tokenizer(tokenizer):
    m = lp.measure(tokenizer, "A situation.", "Share the records.")
    assert m["boundary_ok"]
    counts = {s: [] for s in lp.STRATEGIES}
    for r in range(4):
        order = lp.STRATEGIES[r:] + lp.STRATEGIES[:r]
        text = runner.behavior_text(
            "A situation.", dict.fromkeys(lp.STRATEGIES, "An action."), order
        )
        ids = tokenizer.encode(text)
        for letter in "ABCD":
            full = tokenizer.encode(text + " " + letter)
            assert full[:-1] == ids and len(full) == len(ids) + 1
        for i, s in enumerate(order):
            counts[s].append(i)
    assert all(sorted(x) == [0, 1, 2, 3] for x in counts.values())


@pytest.fixture
def synthetic_packet(tmp_path, monkeypatch, tokenizer):
    """Tiny invented bank, explicit synthetic reviews confined to pytest temp."""
    source = tmp_path / "source.json"
    pools = tmp_path / "pools"
    pools.mkdir()
    scenarios = []
    short = dict(
        zip(
            lp.STRATEGIES,
            [
                "Share supplies.",
                "Work independently.",
                "Reserve supplies.",
                "Defer work.",
            ],
        )
    )
    long = dict(
        zip(
            lp.STRATEGIES,
            [
                "Share the available supplies with the assigned partner.",
                "Work independently with the available supplies for the full assigned task.",
                "Reserve the available supplies exclusively for the full assigned task.",
                "Defer the assigned work until the next regularly scheduled work session.",
            ],
        )
    )
    # Expanded cooperation longer than concise alternatives; shorter than expanded alternatives.
    for i in range(12):
        for partner in ("human", "ai"):
            sid = f"synthetic_{i}_{partner}"
            scenarios.append(
                {
                    "id": sid,
                    "template_id": f"family_{i}",
                    "domain": f"domain_{i % 6}",
                    "split": "exploratory" if i < 6 else "confirmatory",
                    "partner_type": partner,
                    "stem": "This is an invented software test situation.",
                    "options": long,
                    "payoff_spec": {},
                }
            )
            lp.write_json(
                pools / f"{sid}.json",
                {
                    "scenario_id": sid,
                    "options": long,
                    "candidate_pool": {
                        st: [short[st], long[st]] for st in lp.STRATEGIES
                    },
                },
            )
    lp.write_json(source, {"scenarios": scenarios})
    monkeypatch.setattr(lp, "SOURCE", source)
    monkeypatch.setattr(lp, "POOLS", pools)
    packet = tmp_path / "packet"
    lp.prepare(packet)
    return packet


def test_packet_tamper_rejected(synthetic_packet):
    lp.verify_packet(synthetic_packet)
    with (synthetic_packet / "panels.json").open("a") as f:
        f.write(" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        lp.verify_packet(synthetic_packet)


def synthetic_decisions(packet, path):
    decisions = lp.read_json(packet / "review_decisions.template.json")
    decisions["reviewer"] = "SYNTHETIC TEST ONLY - NOT A SCIENTIFIC REVIEW"
    for d in decisions["decisions"]:
        d.update(
            {
                "decision": "APPROVE",
                "actors_resources_constraints_payoffs_checked": True,
                "strategy_checked": True,
                "naturalness_checked": True,
                "stress_test_scope_checked": True,
                "notes": "Synthetic fixture only",
            }
        )
    lp.write_json(path, decisions)


def test_review_gate_and_complete_family_freeze(synthetic_packet, tmp_path):
    pending = lp.read_json(synthetic_packet / "review_decisions.template.json")
    pending["reviewer"] = "TEST"
    path = tmp_path / "decisions.json"
    lp.write_json(path, pending)
    with pytest.raises(ValueError, match="Feasibility gate"):
        runner.freeze(synthetic_packet, path, tmp_path / "fail", "length")
    assert not (tmp_path / "fail").exists()
    synthetic_decisions(synthetic_packet, path)
    plan = tmp_path / "frozen"
    manifest = runner.freeze(synthetic_packet, path, plan, "length")
    assert manifest["num_families"] == 12
    runner.verify_plan(plan)
    panels = lp.read_json(plan / "panels.json")
    assert {p["condition"] for p in panels} == set(runner.COMPARISONS["length"])
    # Remove approval for one original: every condition/partner in the family must go.
    decisions = lp.read_json(path)
    first = next(
        c
        for c in lp.read_json(synthetic_packet / "candidates.json")
        if c["kind"] == "original"
    )
    for d in decisions["decisions"]:
        if d["candidate_id"] == first["candidate_id"]:
            d["decision"] = "REJECT"
    lp.write_json(path, decisions)
    second = tmp_path / "second"
    runner.freeze(synthetic_packet, path, second, "length")
    assert lp.read_json(second / "manifest.json")["num_families"] == 11
    assert all(
        p["family"] != first["family"] for p in lp.read_json(second / "panels.json")
    )


def test_authorization_guards_before_paths_or_model_import(tmp_path):
    with pytest.raises(PermissionError):
        runner.run("missing", tmp_path / "out", True, False)
    with pytest.raises(PermissionError):
        run_behavior("missing", "missing", tmp_path / "behavior", False, True)
    assert not (tmp_path / "out").exists() and not (tmp_path / "behavior").exists()


def test_stale_review_rejected(synthetic_packet, tmp_path):
    path = tmp_path / "decisions.json"
    synthetic_decisions(synthetic_packet, path)
    d = lp.read_json(path)
    d["decisions"][0]["candidate_sha256"] = "wrong"
    lp.write_json(path, d)
    with pytest.raises(ValueError, match="Stale"):
        runner.freeze(synthetic_packet, path, tmp_path / "out", "length")


def test_angles_and_paired_family_bootstrap():
    assert cosine(np.zeros(3), np.ones(3)) is None
    assert cosine(np.array([1.0, 0]), np.array([-1.0, 0])) == -1
    ci = interval([0.1] * 6)
    assert ci["lower"] == pytest.approx(0.1) and ci["upper"] == pytest.approx(0.1)
    assert interval([None] * 6)["mean"] is None


def test_nested_lexical_vocabulary_excludes_heldout_text():
    x = np.array(["share logs", "work alone", "reserve tools", "defer work"] * 4)
    groups = np.repeat(np.arange(4), 4)
    y = np.tile(np.arange(4), 4)
    model, _ = fit_nested(x, y, groups, "lexical")
    assert "heldoutonly" not in model[0].vocabulary_
    model.predict(np.array(["heldoutonly"]))
    assert "heldoutonly" not in model[0].vocabulary_


def test_length_shortcut_fails_when_order_is_reversed():
    # A classifier that only encodes description length must not pass inversion.
    y = np.tile(np.arange(4), 6)
    groups = np.repeat(np.arange(6), 4)
    lengths = np.tile(np.array([20.0, 12.0, 14.0, 16.0]), 6)[:, None]
    model, _ = fit_nested(lengths, y, groups, "length")
    assert np.mean(model.predict(lengths) == y) == 1
    inverted = np.tile(np.array([12.0, 20.0, 16.0, 14.0]), 6)[:, None]
    assert np.mean(model.predict(inverted) == y) == 0


def test_synthetic_semantic_signal_cross_family_analysis():
    # Pure software test: strategy one-hot geometry independent of length.
    # Never saved as scientific evidence or fed to the real-run analyzer.
    rng = np.random.default_rng(17)
    y = np.tile(np.arange(4), 6)
    groups = np.repeat([f"f{i}" for i in range(6)], 4)
    x = np.eye(4)[y] + rng.normal(0, 0.01, (24, 4))
    x = x.reshape(6, 4, 4)
    x -= x.mean(axis=1, keepdims=True)
    x = x.reshape(24, 1, 4)
    length = rng.normal(size=(24, 4))
    texts = np.array(["share logs", "work alone", "reserve tools", "defer work"] * 6)
    data = {
        cond: {
            "x": x.copy(),
            "length": length.copy(),
            "lexical": texts.copy(),
            "y": y.copy(),
            "groups": groups.copy(),
            "changed": np.ones(24, dtype=bool),
            "sids": np.repeat([f"s{i}" for i in range(6)], 4),
        }
        for cond in ("original", "inversion")
    }
    result = evaluate(data, layers=(0,), n_boot=50, progress=False)
    assert len(result["predictions"]) == 96
    assert all(r["accuracy"] == 1 for r in result["per_family"])
    assert all(r["paired_accuracy_change"] == 0 for r in result["per_family"])
    assert all(r["alignment"] > 0.99 for r in result["per_family"])


def test_competence_gate_requires_raw_balanced_evidence(tmp_path):
    samples = [
        {
            "item_id": f"{task}_{i}",
            "task": task,
            "rotation": r,
            "correct_letter": "ABCD"[r],
            "generated_text": "ABCD"[r],
        }
        for task, n in [("objective", 24), ("strategic", 12)]
        for i in range(n)
        for r in range(4)
    ]
    evidence = tmp_path / "evidence.json"
    lp.write_json(
        evidence,
        {
            "target_model": lp.DEFAULT_MODEL_ID,
            "target_revision": lp.DEFAULT_REVISION,
            "mock": False,
            "samples": samples,
        },
    )
    receipt = tmp_path / "receipt.json"
    r = {
        "target_model": lp.DEFAULT_MODEL_ID,
        "target_revision": lp.DEFAULT_REVISION,
        "prompt_format_sha256": format_hash(),
        "reviewer": "SYNTHETIC TEST",
        "approved": True,
        "evidence_file": "evidence.json",
        "evidence_sha256": lp.sha(evidence),
    }
    lp.write_json(receipt, r)
    assert competence_gate(receipt)["strategic"]["accuracy"] == 1
    e = lp.read_json(evidence)
    e["samples"] = e["samples"][:-1]
    lp.write_json(evidence, e)
    r["evidence_sha256"] = lp.sha(evidence)
    lp.write_json(receipt, r)
    with pytest.raises(ValueError, match="every item|Each independent"):
        competence_gate(receipt)
    assert parse_answer("I would choose A") is None
    assert parse_answer(" A. ") == "A"
