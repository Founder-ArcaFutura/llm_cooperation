"""Bounded lexical-confound pilot. Preparation is offline; no automatic semantic approval.

Use ``python -m llm_cooperation.mechanistic.lexical_pilot --help``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import difflib
import hashlib
import json
from pathlib import Path
import random
import re

from .contrastive_mapping import (
    DEFAULT_MODEL_ID,
    DEFAULT_REVISION,
    STRATEGIES,
    format_single_action_prompt,
    load_scenarios,
)

SEED = 20261106
SOURCE = Path("data/scenarios_phase0b_utility_matched.json")
POOLS = Path("research/controlled_rewrites/production01/records")
PROTOCOL = Path("docs/lexical_confound_pilot.md")
WORDS = re.compile(r"\b[\w]+(?:[-'][\w]+)*\b")
# These are conservative mechanical vetoes, NOT an exhaustive semantic parser.
PROTECTED = set(
    "no not never without unless if only all any each every some both either neither "
    "and or but although however instead rather than before after until while then "
    "more less fewer most least equal equally alone independently solely together "
    "shared private joint mutual exclusive own your their our with against for to "
    "from by through per must may can cannot should would will "
    "despite except otherwise even alongside within during between across "
    "because therefore thus consequently although since once whenever provided "
    "zero one two three four five six seven eight nine ten hundred thousand million "
    "several many few enough additional remaining total entire full maximum minimum "
    "human automated ai artificial intelligence independently exclusive exclusively "
    "priority high-priority preferential preferentially uniform separately unilateral "
    "mandatory optional required guaranteed promise commit agree consent".split()
)
LOW = {"the", "a", "an"}
STYLE_RULES = (
    ("in order to", "to"),
    ("by means of", "via"),
    ("prior to", "before"),
    ("subsequent to", "after"),
    ("make use of", "use"),
    ("utilize", "use"),
)
# Meaning-changing positive control: narrowly specified strategic operations only.
CONTENT = set(
    "share sharing coordinate coordinate synchronize synchronise pool reserve "
    "monopolize withhold withdraw defer delay abandon collaborate cooperate compete "
    "exchange allocate claim divert restrict retain exclude".split()
)
CONDITIONS = (
    "original",
    "concise",
    "expanded",
    "inversion",
    "reverse",
    "meaning_preserving",
    "low_ablation",
    "random_deletion",
    "content_deletion",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def write_json(path, obj):
    Path(path).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf8",
        newline="\n",
    )


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def family(s):
    return s.get("triad_id") or s["template_id"]


def stable_seed(*parts):
    return int(digest([SEED, *parts])[:16], 16)


class MeasurementTokenizer:
    """Pinned Qwen fast tokenizer, loaded directly from cached tokenizer.json.

    Avoid importing model weights or network clients. Inference rechecks equality
    against AutoTokenizer on every rendered prompt before forwarding it.
    """

    def __init__(self, snapshot=None):
        from tokenizers import Tokenizer

        self.snapshot = (
            Path(snapshot)
            if snapshot
            else Path.home()
            / ".cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B/snapshots"
            / DEFAULT_REVISION
        )
        if self.snapshot.name != DEFAULT_REVISION:
            raise ValueError("Snapshot directory must name the pinned revision")
        self.backend = Tokenizer.from_file(str(self.snapshot / "tokenizer.json"))
        self.files = {
            p.name: sha(p)
            for p in sorted(self.snapshot.iterdir())
            if p.is_file()
            and p.name
            in (
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.json",
                "merges.txt",
                "config.json",
            )
        }

    def encode(self, text):
        return self.backend.encode(text, add_special_tokens=False).ids

    def offsets(self, text):
        return self.backend.encode(text, add_special_tokens=False).offsets


def measure(tok, stem, action):
    text = format_single_action_prompt(stem, action)
    ids = tok.encode(text)
    # Qwen merges the preceding period + newline into one token. The actual
    # capture anchor is the unchanged Decision: suffix, not newline-in-isolation.
    marker = tok.encode("Decision:")
    offsets = tok.offsets(text)
    anchor_start = len(text) - len("Decision:")
    boundary_ok = (
        ids[-len(marker) :] == marker
        and offsets[-len(marker)][0] == anchor_start
        and offsets[-1][1] == len(text)
    )
    return {
        "action_tokens": len(tok.encode(action.strip())),
        "prompt_tokens": len(ids),
        "words": len(WORDS.findall(action)),
        "characters": len(action),
        "marker_suffix_ids": ids[-len(marker) :],
        "boundary_ok": boundary_ok,
        "capture_token_offset": list(offsets[-1]),
        "anchor_start": anchor_start,
        "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def signature(text):
    return Counter(
        w.lower()
        for w in WORDS.findall(text)
        if w.lower() in PROTECTED or any(c.isdigit() for c in w)
    )


def screen(original, candidate):
    flags = []
    if not candidate or "\n" in candidate or not candidate.endswith("."):
        flags.append("malformed_action")
    if re.search(
        r"<\|.*?\|>|\[MASK\]|\b(?:COOPERATE|INDEPENDENT|COMPETE_EXPLOIT|DISENGAGE)\b",
        candidate,
    ):
        flags.append("special_token_or_label")
    if signature(original) != signature(candidate):
        flags.append("protected_word_or_number_changed_REVIEW")
    if re.search(
        r"\b(?:the the|according in order to|claim lockers|an early docking access)\b",
        candidate,
        re.I,
    ):
        flags.append("known_bad_phrase")
    return flags


def diff_spans(original, candidate):
    return [
        {
            "original_start": a,
            "original_end": b,
            "before": original[a:b],
            "candidate_start": c,
            "candidate_end": d,
            "after": candidate[c:d],
        }
        for op, a, b, c, d in difflib.SequenceMatcher(
            None, original, candidate, autojunk=False
        ).get_opcodes()
        if op != "equal"
    ]


def delete_word(text, match):
    # Delete a complete surface word then normalize whitespace. No token-ID surgery.
    return re.sub(r"\s+", " ", text[: match.start()] + text[match.end() :]).strip()


def deletions(text, eligible):
    return [
        (delete_word(text, m), {"start": m.start(), "end": m.end(), "text": m.group()})
        for m in WORDS.finditer(text)
        if eligible(m.group().lower())
    ]


def perturbations(tok, stem, text, sid, strategy):
    rng = random.Random(stable_seed(sid, strategy, "deletion"))
    low = deletions(text, lambda w: w in LOW)
    rng.shuffle(low)
    result = {}
    # Stylistic replacements only when the actual source contains the expression.
    for old, new in STYLE_RULES:
        m = re.search(r"\b" + re.escape(old) + r"\b", text, re.I)
        if m:
            replacement = new.capitalize() if m.start() == 0 else new
            result["meaning_preserving"] = (
                text[: m.start()] + replacement + text[m.end() :],
                {"rule": [old, new]},
            )
            break
    if not low:
        return result
    target, span = low[0]
    before = measure(tok, stem, text)
    after = measure(tok, stem, target)
    dose = (
        before["action_tokens"] - after["action_tokens"],
        before["prompt_tokens"] - after["prompt_tokens"],
    )
    if min(dose) <= 0:
        return result
    result["low_ablation"] = (target, {"deleted_span": span, "dose": dose})
    # Random over eligible nonprotected whole words, not assumed meaning preserving.
    # Exclude the targeted article; allow other articles. Record the eligible pool.
    leading = next(WORDS.finditer(text), None)
    eligible = [
        (cand, sp)
        for cand, sp in deletions(
            text,
            lambda w: w not in PROTECTED | CONTENT and not any(c.isdigit() for c in w),
        )
        if leading is None or sp["start"] != leading.start()
    ]
    for name, pool in [
        ("random_deletion", eligible),
        ("content_deletion", deletions(text, lambda w: w in CONTENT)),
    ]:
        matched = []
        for cand, sp in pool:
            if sp == span:
                continue
            m = measure(tok, stem, cand)
            if (
                before["action_tokens"] - m["action_tokens"],
                before["prompt_tokens"] - m["prompt_tokens"],
            ) == dose:
                matched.append((cand, sp))
        if matched:
            cand, sp = rng.choice(matched)
            result[name] = (
                cand,
                {
                    "deleted_span": sp,
                    "dose": dose,
                    "eligible_matched_spans": [p[1] for p in matched],
                    "matched_to": "low_ablation",
                },
            )
    return result


def candidate_pools(scenarios, pool_dir):
    pools = defaultdict(dict)
    for s in scenarios:
        for strategy in STRATEGIES:
            pools[(s["id"], strategy)][s["options"][strategy]] = {
                "origin": "immutable_source"
            }
    sources = {}
    if pool_dir and Path(pool_dir).exists():
        valid = {s["id"] for s in scenarios}
        for p in sorted(Path(pool_dir).glob("*.json")):
            rec = read_json(p)
            sid = rec.get("scenario_id")
            if sid not in valid:
                continue
            sources[str(p).replace("\\", "/")] = sha(p)
            for st in STRATEGIES:
                texts = [rec.get("options", {}).get(st)] + rec.get(
                    "candidate_pool", {}
                ).get(st, [])
                for text in texts:
                    if isinstance(text, str) and text.strip():
                        pools[(sid, st)].setdefault(
                            text.strip(),
                            {
                                "origin": str(p).replace("\\", "/"),
                                "sha256": sources[str(p).replace("\\", "/")],
                            },
                        )
    return pools, sources


def audit(tok, scenarios):
    import numpy as np
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer

    rows = []
    for s in scenarios:
        for st in STRATEGIES:
            rows.append(
                {
                    "scenario_id": s["id"],
                    "family": family(s),
                    "domain": s["domain"],
                    "source_split": s["split"],
                    "partner_type": s["partner_type"],
                    "strategy": st,
                    "text": s["options"][st],
                    **measure(tok, s["stem"], s["options"][st]),
                }
            )
    counts = {
        st: Counter(r["action_tokens"] for r in rows if r["strategy"] == st)
        for st in STRATEGIES
    }
    overlap = {
        f"{a}:{b}": sum(
            min(
                counts[a][k] / sum(counts[a].values()),
                counts[b][k] / sum(counts[b].values()),
            )
            for k in counts[a].keys() | counts[b].keys()
        )
        for i, a in enumerate(STRATEGIES)
        for b in STRATEGIES[i + 1 :]
    }
    inversion = []
    quartet_spans = []
    for s in scenarios:
        ms = {st: measure(tok, s["stem"], s["options"][st]) for st in STRATEGIES}
        if all(
            ms["COOPERATE"][f] < min(ms[st][f] for st in STRATEGIES[1:])
            for f in ("action_tokens", "prompt_tokens")
        ):
            inversion.append(s["id"])
        quartet_spans.append(
            {
                "scenario_id": s["id"],
                "family": family(s),
                "action_span": max(v["action_tokens"] for v in ms.values())
                - min(v["action_tokens"] for v in ms.values()),
                "prompt_span": max(v["prompt_tokens"] for v in ms.values())
                - min(v["prompt_tokens"] for v in ms.values()),
            }
        )
    # Full-bank diagnostic OOF baselines; no activations used for selection.
    groups = np.array([r["family"] for r in rows])
    y = np.array([STRATEGIES.index(r["strategy"]) for r in rows])
    x = np.array(
        [
            [r[k] for k in ("action_tokens", "prompt_tokens", "words", "characters")]
            for r in rows
        ]
    )
    texts = np.array([r["text"] for r in rows])
    predictions = {}
    for name in ("length_only", "lexical_only"):
        pred = np.zeros_like(y)
        for tr, te in GroupKFold(n_splits=6).split(x, y, groups):
            model = (
                make_pipeline(
                    PolynomialFeatures(2, include_bias=False),
                    StandardScaler(),
                    LogisticRegression(C=1, max_iter=2000),
                )
                if name == "length_only"
                else make_pipeline(
                    TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
                    LogisticRegression(C=1, max_iter=2000),
                )
            )
            features = x if name == "length_only" else texts
            model.fit(features[tr], y[tr])
            pred[te] = model.predict(features[te])
        by_family = {
            g: float((pred[groups == g] == y[groups == g]).mean())
            for g in sorted(set(groups))
        }
        vals = np.array(list(by_family.values()))
        boot = vals[
            np.random.default_rng(SEED).integers(0, len(vals), size=(2000, len(vals)))
        ].mean(axis=1)
        predictions[name] = {
            "family_macro_accuracy": float(vals.mean()),
            "per_family": by_family,
            "family_bootstrap_95_ci": [
                float(np.quantile(boot, 0.025)),
                float(np.quantile(boot, 0.975)),
            ],
            "note": "Fixed C=1, 6-fold family OOF; lexical TF-IDF L2 normalized, no explicit length features.",
        }
    return {
        "rows": rows,
        "n_scenarios": len(scenarios),
        "n_families": len(set(groups)),
        "summary": {
            st: {
                "mean": float(
                    np.mean([r["action_tokens"] for r in rows if r["strategy"] == st])
                ),
                "histogram": dict(sorted(counts[st].items())),
            }
            for st in STRATEGIES
        },
        "pairwise_histogram_overlap_0_to_1": overlap,
        "original_inversion_scenario_ids": inversion,
        "original_quartet_spans": quartet_spans,
        "original_within_quartet_overlap": {
            str(limit): [
                r["scenario_id"]
                for r in quartet_spans
                if max(r["action_span"], r["prompt_span"]) <= limit
            ]
            for limit in (0, 1, 2, 4)
        },
        "baselines": predictions,
    }


def lengths(tok, s, pools):
    out = {}
    for st in STRATEGIES:
        options = [
            (text, origin, measure(tok, s["stem"], text))
            for text, origin in pools[(s["id"], st)].items()
            if not any(
                f in ("malformed_action", "special_token_or_label", "known_bad_phrase")
                for f in screen(s["options"][st], text)
            )
        ]
        options.sort(key=lambda x: (x[2]["action_tokens"], x[2]["prompt_tokens"], x[0]))
        out[st] = (options[0], options[-1])
    return out


def is_inverted(choices):
    return all(
        choices["COOPERATE"][2][f] < min(choices[s][2][f] for s in STRATEGIES[1:])
        for f in ("action_tokens", "prompt_tokens")
    )


def select_families(tok, scenarios, pools, n=12):
    grouped = defaultdict(list)
    for s in scenarios:
        grouped[family(s)].append(s)
    records = []
    for g, ss in grouped.items():
        natural = feasible = coverage = 0
        for s in ss:
            le = lengths(tok, s, pools)
            natural += is_inverted(
                {
                    st: (
                        s["options"][st],
                        {},
                        measure(tok, s["stem"], s["options"][st]),
                    )
                    for st in STRATEGIES
                }
            )
            feasible += is_inverted(
                {st: le[st][0 if st == "COOPERATE" else 1] for st in STRATEGIES}
            )
            coverage += sum(
                le[st][0][2]["action_tokens"] < le[st][1][2]["action_tokens"]
                for st in STRATEGIES
            )
        records.append(
            {
                "family": g,
                "domain": ss[0]["domain"],
                "source_split": ss[0]["split"],
                "n_scenarios": len(ss),
                "natural_inversion_fraction": natural / len(ss),
                "candidate_inversion_fraction": feasible / len(ss),
                "two_length_fraction": coverage / (4 * len(ss)),
                "triad": bool(ss[0].get("triad_id")),
                "tie": stable_seed("selection", g),
            }
        )
    selected = []
    domains = set()
    # Equal source strata; include one utility triad from each stratum when present.
    # These are feasibility criteria only, not semantic acceptance.
    for split in ("exploratory", "confirmatory"):
        available = [r for r in records if r["source_split"] == split]
        for i in range(n // 2):
            choices = [r for r in available if r["family"] not in selected]
            if i == 0 and any(r["triad"] for r in choices):
                choices = [r for r in choices if r["triad"]]
            choices.sort(
                key=lambda r: (
                    r["domain"] in domains,
                    -r["natural_inversion_fraction"],
                    -r["candidate_inversion_fraction"],
                    -r["two_length_fraction"],
                    r["tie"],
                )
            )
            r = choices[0]
            selected.append(r["family"])
            domains.add(r["domain"])
    return selected, records


def prepare(output, snapshot=None):
    out = Path(output)
    if out.exists():
        raise FileExistsError(
            "Use a new output directory; previous pilot artifacts are immutable"
        )
    tok = MeasurementTokenizer(snapshot)
    scenarios = load_scenarios(SOURCE)
    source_sha = sha(SOURCE)
    pools, pool_hashes = candidate_pools(scenarios, POOLS)
    report = audit(tok, scenarios)
    selected, selection = select_families(tok, scenarios, pools)
    chosen = [s for s in scenarios if family(s) in selected]
    out.mkdir(parents=True)
    (out / "source_snapshot.json").write_bytes(SOURCE.read_bytes())
    write_json(out / "audit.json", report)
    write_json(
        out / "selection.json",
        {
            "selected_families": selected,
            "all_family_scores": selection,
            "method": "6 per source stratum; one full utility triad per stratum; then domain diversity, original inversion, existing candidate feasibility, seed tie break. No activation outcomes.",
        },
    )
    write_json(out / "selected_scenarios.json", chosen)
    candidates = {}
    panel_rows = []
    missing = []

    def add(s, st, text, kind, origin, extra=None):
        original = s["options"][st]
        if text == original:
            kind, origin = "original", {"origin": "immutable_source"}
        key = digest([s["id"], st, text, kind])[:20]
        candidates.setdefault(
            key,
            {
                "candidate_id": key,
                "scenario_id": s["id"],
                "family": family(s),
                "strategy": st,
                "kind": kind,
                "original": original,
                "text": text,
                "origin": origin,
                "seed": stable_seed(s["id"], st, "deletion"),
                "original_measurement": measure(tok, s["stem"], original),
                "measurement": measure(tok, s["stem"], text),
                "edits": diff_spans(original, text),
                "screen_flags": screen(original, text),
                "perturbation": extra or {},
                "semantic_status": "UNADJUDICATED",
                "status": "QUARANTINED_PENDING_REVIEW",
            },
        )
        return key

    for s in chosen:
        variants = defaultdict(dict)
        le = lengths(tok, s, pools)
        for st in STRATEGIES:
            original = s["options"][st]
            variants["original"][st] = add(
                s, st, original, "original", {"origin": "immutable_source"}
            )
            short, long = le[st]
            if (
                short[2]["action_tokens"] < long[2]["action_tokens"]
                and short[2]["prompt_tokens"] < long[2]["prompt_tokens"]
            ):
                for cond, opt in [("concise", short), ("expanded", long)]:
                    variants[cond][st] = add(s, st, opt[0], "natural_rewrite", opt[1])
            else:
                missing.append(
                    {
                        "scenario_id": s["id"],
                        "strategy": st,
                        "condition": "two_lengths",
                        "reason": "no distinct existing short/long pair; no padding or forced rewrite",
                    }
                )
            perturb = perturbations(tok, s["stem"], original, s["id"], st)
            # If no conservative stylistic rule applies, reuse an existing same-length
            # candidate with unchanged protected-word signature, for human review.
            if "meaning_preserving" not in perturb:
                opts = [
                    (t, o)
                    for t, o in pools[(s["id"], st)].items()
                    if t != original
                    and not screen(original, t)
                    and measure(tok, s["stem"], t)["action_tokens"]
                    == measure(tok, s["stem"], original)["action_tokens"]
                ]
                if opts:
                    t, o = sorted(
                        opts, key=lambda v: (len(diff_spans(original, v[0])), v[0])
                    )[0]
                    perturb["meaning_preserving"] = (
                        t,
                        {
                            "existing_candidate_origin": o,
                            "rule": "same-token-count candidate; equivalence UNADJUDICATED",
                        },
                    )
            for cond, (text, record) in perturb.items():
                variants[cond][st] = add(
                    s,
                    st,
                    text,
                    "meaning_preserving_candidate"
                    if cond == "meaning_preserving"
                    else cond,
                    {"origin": "deterministic_surface_edit"},
                    record,
                )
        if len(variants["concise"]) == len(variants["expanded"]) == 4:
            inv = {st: le[st][0 if st == "COOPERATE" else 1] for st in STRATEGIES}
            rev = {st: le[st][1 if st == "COOPERATE" else 0] for st in STRATEGIES}
            if is_inverted(inv):
                variants["inversion"] = {
                    st: variants["concise" if st == "COOPERATE" else "expanded"][st]
                    for st in STRATEGIES
                }
            if all(
                rev["COOPERATE"][2][f] > max(rev[st][2][f] for st in STRATEGIES[1:])
                for f in ("action_tokens", "prompt_tokens")
            ):
                variants["reverse"] = {
                    st: variants["expanded" if st == "COOPERATE" else "concise"][st]
                    for st in STRATEGIES
                }
        # Explicitly targeted stress panels. Missing edits stay IDENTICAL to source,
        # and the changed-label inventory accompanies every panel. Never pretend a
        # no-op is a successful intervention or a balanced lexical manipulation.
        for cond in (
            "meaning_preserving",
            "low_ablation",
            "random_deletion",
            "content_deletion",
        ):
            if variants[cond]:
                changed = sorted(variants[cond])
                panel_rows.append(
                    {
                        "scenario_id": s["id"],
                        "family": family(s),
                        "condition": cond,
                        "candidates": {
                            st: variants[cond].get(st, variants["original"][st])
                            for st in STRATEGIES
                        },
                        "changed_strategies": changed,
                        "targeted_partial_intervention": len(changed) != 4,
                        "status": "QUARANTINED_PENDING_REVIEW",
                    }
                )
        for cond in CONDITIONS:
            if cond in (
                "meaning_preserving",
                "low_ablation",
                "random_deletion",
                "content_deletion",
            ):
                if len(variants[cond]) != 4:
                    missing.append(
                        {
                            "scenario_id": s["id"],
                            "condition": cond,
                            "reason": "balanced all-four-strategy perturbation unavailable",
                            "available_strategies": sorted(variants[cond]),
                        }
                    )
                continue
            if len(variants[cond]) == 4:
                panel_rows.append(
                    {
                        "scenario_id": s["id"],
                        "family": family(s),
                        "condition": cond,
                        "candidates": variants[cond],
                        "status": "QUARANTINED_PENDING_REVIEW",
                    }
                )
            else:
                missing.append(
                    {
                        "scenario_id": s["id"],
                        "condition": cond,
                        "reason": "incomplete quartet or length inequality not met",
                        "available_strategies": sorted(variants[cond]),
                    }
                )
    write_json(out / "candidates.json", list(candidates.values()))
    write_json(out / "panels.json", panel_rows)
    write_json(out / "infeasible.json", missing)
    review = {
        "packet_source_sha256": source_sha,
        "reviewer": "",
        "decisions": [
            {
                "candidate_id": c["candidate_id"],
                "candidate_sha256": digest(c),
                "decision": "PENDING",
                "actors_resources_constraints_payoffs_checked": False,
                "strategy_checked": False,
                "naturalness_checked": False,
                "stress_test_scope_checked": False,
                "notes": "",
            }
            for c in candidates.values()
        ],
    }
    write_json(out / "review_decisions.template.json", review)
    cards = [
        "# Lexical pilot review — all candidates quarantined",
        "",
        "Review by scenario. Original stems/payoffs are unchanged but not automatically scientifically validated.",
        "Approve natural formulations only after checking meaning; stress-test approval acknowledges corruption, not equivalence.",
        "",
    ]
    for s in chosen:
        cards += [
            f"## {s['id']} · {family(s)} · {s['domain']}",
            "",
            s["stem"],
            "",
            "Payoffs: `"
            + json.dumps(s.get("payoff_spec", {}), ensure_ascii=False)
            + "`",
            "",
        ]
        for st in STRATEGIES:
            cards += [f"### {st}", "", f"Original: {s['options'][st]}", ""]
            for c in candidates.values():
                if c["scenario_id"] != s["id"] or c["strategy"] != st:
                    continue
                a, b = c["original_measurement"], c["measurement"]
                cards += [
                    f"- `{c['candidate_id']}` **{c['kind']}**: {c['text']}",
                    f"  Tokens action {a['action_tokens']} → {b['action_tokens']}; prompt {a['prompt_tokens']} → {b['prompt_tokens']}. Flags: {', '.join(c['screen_flags']) or 'none detected; semantic review still required'}.",
                ]
            cards += [""]
    (out / "review.md").write_text(
        "\n".join(cards) + "\n", encoding="utf8", newline="\n"
    )
    counts = dict(Counter(p["condition"] for p in panel_rows))
    summary = {
        "selected_families": len(selected),
        "selected_scenarios": len(chosen),
        "candidate_count": len(candidates),
        "complete_provisional_quartets": counts,
        "accepted_candidates": 0,
        "perturbation_coverage": {
            cond: dict(
                Counter(
                    st
                    for p in panel_rows
                    if p["condition"] == cond
                    for st in p.get("changed_strategies", [])
                )
            )
            for cond in (
                "meaning_preserving",
                "low_ablation",
                "random_deletion",
                "content_deletion",
            )
        },
        "recommendation": "Review feasibility pilot only. Scaling and inference not justified before semantic review and paired coverage gates.",
        "source_unchanged": sha(SOURCE) == source_sha,
    }
    write_json(out / "summary.json", summary)
    selected_groups = {
        family(s): [r for r in chosen if family(r) == family(s)] for s in chosen
    }
    paired_coverage = {}
    for name, needed in {
        "length": ("original", "concise", "expanded", "inversion", "reverse"),
        "ablation": ("original", "low_ablation", "random_deletion"),
        "meaning": ("original", "meaning_preserving"),
        "content": ("original", "low_ablation", "random_deletion", "content_deletion"),
    }.items():
        keys = {(p["scenario_id"], p["condition"]) for p in panel_rows}
        paired_coverage[name] = [
            g
            for g, ss in selected_groups.items()
            if all((s["id"], c) in keys for s in ss for c in needed)
        ]
    write_json(out / "paired_coverage.json", paired_coverage)
    coverage_metadata = {
        name: {
            "n_families": len(gs),
            "n_scenarios": sum(family(s) in gs for s in chosen),
            "domains": sorted({s["domain"] for s in chosen if family(s) in gs}),
            "utility_conditions": dict(
                Counter(
                    s.get("utility_condition", "unknown")
                    for s in chosen
                    if family(s) in gs
                )
            ),
            "source_splits": dict(
                Counter(s["split"] for s in chosen if family(s) in gs)
            ),
        }
        for name, gs in paired_coverage.items()
    }
    write_json(out / "coverage_metadata.json", coverage_metadata)
    for comparison, gs in paired_coverage.items():
        needed = {
            "length": ("original", "concise", "expanded", "inversion", "reverse"),
            "ablation": ("original", "low_ablation", "random_deletion"),
            "meaning": ("original", "meaning_preserving"),
            "content": (
                "original",
                "low_ablation",
                "random_deletion",
                "content_deletion",
            ),
        }[comparison]
        used = {
            cid
            for p in panel_rows
            if p["family"] in gs and p["condition"] in needed
            for cid in p["candidates"].values()
        }
        focused = {
            **review,
            "decisions": [d for d in review["decisions"] if d["candidate_id"] in used],
        }
        write_json(out / f"review_{comparison}_decisions.template.json", focused)
        lines = [
            f"# {comparison.title()} review — {len(gs)} complete provisional families",
            "",
            f"{len(used)} distinct candidate records. All remain quarantined. Full payoff details are in review.md and selected_scenarios.json.",
            "Only complete families appear here; reviewing excluded partial families is unnecessary for this comparison.",
            "",
        ]
        for s in chosen:
            if family(s) not in gs:
                continue
            lines += [f"## {s['id']} · {family(s)}", "", s["stem"], ""]
            for st in STRATEGIES:
                lines += [f"### {st}", "", "Original: " + s["options"][st], ""]
                for c in candidates.values():
                    if (
                        c["candidate_id"] not in used
                        or c["scenario_id"] != s["id"]
                        or c["strategy"] != st
                    ):
                        continue
                    m = c["measurement"]
                    before = c["original_measurement"]
                    desc = "Unchanged source" if c["kind"] == "original" else c["text"]
                    lines += [
                        f"- `{c['candidate_id']}` ({c['kind']}): {desc}",
                        f"  Action tokens {before['action_tokens']} → {m['action_tokens']}; prompt {before['prompt_tokens']} → {m['prompt_tokens']}; flags: {', '.join(c['screen_flags']) or 'none detected'}.",
                    ]
                lines += [""]
        (out / f"review_{comparison}.md").write_text(
            "\n".join(lines) + "\n", encoding="utf8", newline="\n"
        )
    audit_lines = [
        "# Automatic token-length and overlap audit",
        "",
        f"Source: {len(scenarios)} scenarios, {report['n_families']} families; pinned Qwen tokenizer {DEFAULT_REVISION}.",
        "",
        "| Strategy | Mean action tokens |",
        "|---|---:|",
    ]
    audit_lines += [
        f"| {st} | {report['summary'][st]['mean']:.3f} |" for st in STRATEGIES
    ]
    audit_lines += [
        "",
        f"Naturally inverted original quartets: {len(report['original_inversion_scenario_ids'])}.",
        "",
        "| Length-distribution pair | Histogram overlap (0–1) |",
        "|---|---:|",
    ]
    audit_lines += [
        f"| {pair} | {value:.3f} |"
        for pair, value in report["pairwise_histogram_overlap_0_to_1"].items()
    ]
    audit_lines += [
        "",
        "Six-fold family-held-out baseline diagnostics (equal family weight at reporting):",
        "",
    ]
    audit_lines += [
        f"- {name}: {v['family_macro_accuracy']:.3f}, 95% family-bootstrap interval {v['family_bootstrap_95_ci']} (conditional on OOF fits)"
        for name, v in report["baselines"].items()
    ]
    audit_lines += [
        "",
        "Lexical features include meaningful strategy vocabulary; high performance is not proof of a spurious confound.",
        "Histogram overlap does not establish within-scenario equivalence. All original counts are retained in audit.json.",
        "",
        f"Selected: {len(selected)} families, {len(chosen)} scenarios, {len({s['domain'] for s in chosen})} domains.",
        "Feasibility selection uses metadata/text only and enriches for usable existing candidate lengths. It is not representative sampling.",
        "",
        "Complete-family coverage BEFORE semantic review:",
        "",
    ]
    audit_lines += [
        f"- {k}: {len(v)} families ({', '.join(v)})" for k, v in paired_coverage.items()
    ]
    audit_lines += [
        "",
        "Length-comparison utility coverage: "
        + json.dumps(coverage_metadata["length"]["utility_conditions"])
        + ".",
        "Incomplete utility triads are excluded as whole families; results cannot support utility-sensitivity claims if those strata are absent.",
    ]
    audit_lines += [
        "",
        "All candidates remain quarantined. No new model inference or accepted semantic equivalence.",
        "Article deletion is strongly strategy-asymmetric. Partial panels explicitly leave unavailable actions unchanged.",
        "No balanced all-strategy ablation result or general paraphrase robustness claim is licensed by these partial panels.",
        "Scaling recommendation: review the bounded length and targeted-ablation pilot; do not scale the corpus.",
    ]
    (out / "audit.md").write_text(
        "\n".join(audit_lines) + "\n", encoding="utf8", newline="\n"
    )
    manifest = {
        "version": "lexical-pilot-v1",
        "status": "QUARANTINED",
        "seed": SEED,
        "target_model": DEFAULT_MODEL_ID,
        "target_revision": DEFAULT_REVISION,
        "source_sha256": source_sha,
        "tokenizer_files_sha256": tok.files,
        "pool_files_sha256": pool_hashes,
        "protocol_sha256": sha(PROTOCOL),
        "code_sha256": sha(__file__),
        "files": {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    write_json(out / "manifest.json", manifest)
    print(json.dumps(summary, indent=2))
    return summary


def verify_packet(path):
    path = Path(path)
    manifest = read_json(path / "manifest.json")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or sha(path / name) != expected:
            raise ValueError(f"Packet hash mismatch: {name}")
    if sha(path / "source_snapshot.json") != manifest["source_sha256"]:
        raise ValueError("Source snapshot mismatch")
    if (
        manifest["target_model"] != DEFAULT_MODEL_ID
        or manifest["target_revision"] != DEFAULT_REVISION
    ):
        raise ValueError("Unsupported model/revision")
    if (
        sha(__file__) != manifest["code_sha256"]
        or sha(PROTOCOL) != manifest["protocol_sha256"]
    ):
        raise ValueError(
            "Preparation code/protocol changed; regenerate to a new directory before freeze"
        )
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser(
        "prepare", help="Offline audit and quarantined pilot; cached tokenizer only"
    )
    a.add_argument("--output", required=True)
    a.add_argument("--tokenizer-snapshot")
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.tokenizer_snapshot)


if __name__ == "__main__":
    main()
