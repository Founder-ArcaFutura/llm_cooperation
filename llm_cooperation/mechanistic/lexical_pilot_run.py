"""Review-gated freeze and authorized extraction for the lexical pilot."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil

from .lexical_pilot import (
    MeasurementTokenizer,
    DEFAULT_MODEL_ID,
    DEFAULT_REVISION,
    STRATEGIES,
    SEED,
    digest,
    sha,
    read_json,
    write_json,
    verify_packet,
    family,
    measure,
    screen,
    format_single_action_prompt,
    PROTOCOL,
)

COMPARISONS = {
    "length": ("original", "concise", "expanded", "inversion", "reverse"),
    "ablation": ("original", "low_ablation", "random_deletion"),
    "meaning": ("original", "meaning_preserving"),
    "content": ("original", "low_ablation", "random_deletion", "content_deletion"),
}


def behavior_text(stem, actions, order):
    return (
        "Read the situation and select the action you would take. Reply with one letter: A, B, C, or D.\n\n"
        + stem.strip()
        + "\n\n"
        + "\n".join(f"{'ABCD'[i]}. {actions[st]}" for i, st in enumerate(order))
        + "\n\nAnswer:"
    )


def freeze(packet, decisions_path, output, comparison, snapshot=None):
    packet, output = Path(packet), Path(output)
    manifest = verify_packet(packet)
    if output.exists():
        raise FileExistsError(output)
    tok = MeasurementTokenizer(snapshot)
    if tok.files != manifest["tokenizer_files_sha256"]:
        raise ValueError("Tokenizer files differ from prepared packet")
    decisions = read_json(decisions_path)
    if (
        not decisions.get("reviewer", "").strip()
        or decisions.get("packet_source_sha256") != manifest["source_sha256"]
    ):
        raise ValueError("Named reviewer and exact source hash required")
    candidates = {c["candidate_id"]: c for c in read_json(packet / "candidates.json")}
    approved = set()
    decision_ids = set()
    for d in decisions["decisions"]:
        cid = d["candidate_id"]
        if cid in decision_ids or cid not in candidates:
            raise ValueError("Duplicate or unknown review ID")
        decision_ids.add(cid)
        c = candidates[cid]
        if d["candidate_sha256"] != digest(c):
            raise ValueError("Stale candidate review")
        if d["decision"] not in ("PENDING", "REJECT", "APPROVE"):
            raise ValueError("Unknown review decision")
        if d["decision"] != "APPROVE":
            continue
        natural = c["kind"] in (
            "original",
            "natural_rewrite",
            "meaning_preserving_candidate",
        )
        required = (
            (
                "actors_resources_constraints_payoffs_checked",
                "strategy_checked",
                "naturalness_checked",
            )
            if natural
            else ("stress_test_scope_checked",)
        )
        if not all(d.get(k) is True for k in required):
            raise ValueError(f"Review checks incomplete: {cid}")
        if c["screen_flags"] and not d.get("notes", "").strip():
            raise ValueError("Flagged candidate needs an explicit adjudication note")
        if any(
            f in ("malformed_action", "special_token_or_label", "known_bad_phrase")
            for f in screen(c["original"], c["text"])
        ):
            raise ValueError("Hard structural rejection cannot be overridden")
        if not c["measurement"]["boundary_ok"]:
            raise ValueError("Capture token boundary failed")
        approved.add(cid)
    conditions = COMPARISONS[comparison]
    scenarios = read_json(packet / "selected_scenarios.json")
    by_sid = {s["id"]: s for s in scenarios}
    panels = {
        (p["scenario_id"], p["condition"]): p for p in read_json(packet / "panels.json")
    }
    groups = defaultdict(list)
    for s in scenarios:
        groups[family(s)].append(s["id"])
    eligible, excluded = [], {}
    for g, sids in groups.items():
        failures = []
        for sid in sids:
            for cond in conditions:
                p = panels.get((sid, cond))
                if not p or set(p["candidates"]) != set(STRATEGIES):
                    failures.append(f"{sid}/{cond}: missing quartet")
                elif not set(p["candidates"].values()) <= approved:
                    failures.append(f"{sid}/{cond}: pending/rejected candidate")
        if failures:
            excluded[g] = failures
        else:
            eligible.append(g)
    chosen = [s for s in scenarios if family(s) in eligible]
    if (
        len(eligible) < 6
        or len({s["domain"] for s in chosen}) < 4
        or {s["partner_type"] for s in chosen} != {"human", "ai"}
    ):
        raise ValueError(
            f"Feasibility gate failed: {len(eligible)} complete reviewed families; need >=6, >=4 domains, both partners. Exclusions: {json.dumps(excluded)}"
        )
    kept = [panels[(s["id"], c)] for s in chosen for c in conditions]
    # Recheck experimental inequalities and matched doses, not just review flags.
    for s in chosen:
        if comparison == "length":
            for cond, sign in [("inversion", -1), ("reverse", 1)]:
                cs = {
                    st: candidates[panels[(s["id"], cond)]["candidates"][st]]
                    for st in STRATEGIES
                }
                for feature in ("action_tokens", "prompt_tokens"):
                    coop = cs["COOPERATE"]["measurement"][feature]
                    if not all(
                        sign * (coop - cs[st]["measurement"][feature]) > 0
                        for st in STRATEGIES[1:]
                    ):
                        raise ValueError("Length ordering violated")
        if comparison in ("ablation", "content"):
            low = panels[(s["id"], "low_ablation")]
            rand = panels[(s["id"], "random_deletion")]
            if low["changed_strategies"] != rand["changed_strategies"]:
                raise ValueError(
                    "Random control must perturb the identical strategy subset"
                )
            for st in low["changed_strategies"]:
                lc, rc = [candidates[p["candidates"][st]] for p in (low, rand)]
                if lc["perturbation"]["dose"] != rc["perturbation"]["dose"]:
                    raise ValueError("Deletion dose mismatch")
    prompts = {}
    final_panels = []
    for panel in kept:
        s = by_sid[panel["scenario_id"]]
        ids = {}
        for st, cid in panel["candidates"].items():
            c = candidates[cid]
            actual = measure(tok, s["stem"], c["text"])
            if actual != c["measurement"]:
                raise ValueError("Candidate measurement differs from current tokenizer")
            pid = digest([s["id"], st, c["text"]])[:24]
            ids[st] = pid
            prompts[pid] = {
                "prompt_id": pid,
                "scenario_id": s["id"],
                "group_key": family(s),
                "domain": s["domain"],
                "strategy": st,
                "action_text": c["text"],
                "prompt_text": format_single_action_prompt(s["stem"], c["text"]),
                "measurement": actual,
                "input_ids": tok.encode(
                    format_single_action_prompt(s["stem"], c["text"])
                ),
            }
        final_panels.append({**panel, "prompt_ids": ids})
    behavior = []
    for panel in final_panels:
        s = by_sid[panel["scenario_id"]]
        actions = {
            st: prompts[pid]["action_text"] for st, pid in panel["prompt_ids"].items()
        }
        for rotation in range(4):
            order = list(STRATEGIES[rotation:] + STRATEGIES[:rotation])
            text = behavior_text(s["stem"], actions, order)
            prefix = tok.encode(text)
            labels = []
            for letter in "ABCD":
                encoded = tok.encode(text + " " + letter)
                if encoded[:-1] != prefix:
                    raise ValueError(
                        "Behavior answer is not an exact one-token continuation"
                    )
                labels.append(encoded[-1])
            behavior.append(
                {
                    "id": f"{s['id']}_{panel['condition']}_{rotation}",
                    "scenario_id": s["id"],
                    "family": family(s),
                    "condition": panel["condition"],
                    "rotation": rotation,
                    "order": order,
                    "prompt_text": text,
                    "input_ids": prefix,
                    "letter_ids": labels,
                    "letter_continuations": [" " + letter for letter in "ABCD"],
                }
            )
    output.mkdir(parents=True)
    for name in ("source_snapshot.json", "selected_scenarios.json"):
        shutil.copyfile(packet / name, output / name)
    shutil.copyfile(decisions_path, output / "review_decisions.json")
    shutil.copyfile(PROTOCOL, output / "protocol.md")
    (output / "prompts.jsonl").write_text(
        "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in prompts.values()),
        encoding="utf8",
        newline="\n",
    )
    write_json(output / "panels.json", final_panels)
    write_json(output / "behavior_prompts.json", behavior)
    write_json(
        output / "coverage.json",
        {
            "families": eligible,
            "excluded": excluded,
            "comparison": comparison,
            "conditions": conditions,
            "perturbed_counts": {
                c: dict(
                    Counter(
                        st
                        for p in kept
                        if p["condition"] == c
                        for st in p.get("changed_strategies", [])
                    )
                )
                for c in conditions
            },
            "targeted_stress_warning": comparison != "length",
        },
    )
    final = {
        "status": "REVIEWED_FROZEN_NOT_AUTHORIZED",
        "comparison": comparison,
        "conditions": conditions,
        "num_prompts": len(prompts),
        "num_scenarios": len(chosen),
        "num_families": len(eligible),
        "num_layers": 28,
        "hidden_size": 1536,
        "seed": SEED,
        "target_model": DEFAULT_MODEL_ID,
        "target_revision": DEFAULT_REVISION,
        "bank_sha256": manifest["source_sha256"],
        "source_packet_manifest_sha256": sha(packet / "manifest.json"),
        "script_sha256": sha(__file__),
        "extractor_sha256": sha(Path(__file__).with_name("contrastive_mapping.py")),
        "analysis_sha256": sha(Path(__file__).with_name("lexical_pilot_analysis.py")),
        "behavior_script_sha256": sha(
            Path(__file__).with_name("lexical_pilot_behavior.py")
        ),
        "prompts_sha256": sha(output / "prompts.jsonl"),
        "tokenizer_files_sha256": tok.files,
        "files": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    write_json(output / "manifest.json", final)
    return final


def verify_plan(plan):
    plan = Path(plan)
    m = read_json(plan / "manifest.json")
    if m["status"] != "REVIEWED_FROZEN_NOT_AUTHORIZED":
        raise ValueError("A reviewed frozen plan is required")
    for name, expected in m["files"].items():
        if Path(name).name != name or sha(plan / name) != expected:
            raise ValueError(f"Frozen plan hash mismatch: {name}")
    if (
        m["target_model"] != DEFAULT_MODEL_ID
        or m["target_revision"] != DEFAULT_REVISION
    ):
        raise ValueError("Model/revision mismatch")
    if sha(Path(__file__).with_name("contrastive_mapping.py")) != m["extractor_sha256"]:
        raise ValueError("Extractor changed since freeze")
    if sha(__file__) != m["script_sha256"]:
        raise ValueError("Runner changed since freeze")
    return m


def run(plan, output, authorize_inference=False, authorize_paid_run=False):
    # Guards precede any model initialization or output creation.
    if not (authorize_inference and authorize_paid_run):
        raise PermissionError(
            "Explicit --authorize-inference AND --authorize-paid-run required; no model loaded"
        )
    plan = Path(plan)
    m = verify_plan(plan)
    from transformers import AutoTokenizer

    tok = MeasurementTokenizer()
    if tok.files != m["tokenizer_files_sha256"]:
        raise ValueError("Tokenizer provenance mismatch")
    actual = AutoTokenizer.from_pretrained(str(tok.snapshot), local_files_only=True)
    rows = [
        json.loads(line)
        for line in (plan / "prompts.jsonl").read_text(encoding="utf8").splitlines()
    ]
    if len(rows) != m["num_prompts"] or len({r["prompt_id"] for r in rows}) != len(
        rows
    ):
        raise ValueError("Prompt inventory invalid")
    for row in rows:
        if actual.encode(row["prompt_text"]) != row["input_ids"]:
            raise ValueError(
                "Actual inference tokenizer differs from measured prompt IDs"
            )
    from .contrastive_mapping import run_inference

    result = run_inference(
        plan,
        output,
        model_id=DEFAULT_MODEL_ID,
        revision=DEFAULT_REVISION,
        authorize=True,
    )
    if (result["num_layers"], result["hidden_size"]) != (28, 1536):
        raise ValueError("Unexpected model architecture; output quarantined")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--packet", required=True)
    f.add_argument("--decisions", required=True)
    f.add_argument("--output", required=True)
    f.add_argument("--comparison", choices=COMPARISONS, required=True)
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    r.add_argument("--output", required=True)
    r.add_argument("--authorize-inference", action="store_true")
    r.add_argument("--authorize-paid-run", action="store_true")
    a = p.parse_args()
    result = (
        freeze(a.packet, a.decisions, a.output, a.comparison)
        if a.command == "freeze"
        else run(a.plan, a.output, a.authorize_inference, a.authorize_paid_run)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
