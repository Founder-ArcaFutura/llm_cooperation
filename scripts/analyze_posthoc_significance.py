"""Reproduce post-hoc clustered randomization tests from recorded responses.

Randomization units are scenario templates (or explicit triads). The nulls are
label exchangeability within a cluster, not claims that choices are literally
random. See the generated methodological report for assumptions and scope.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "manuscript_readiness"
STRATEGIES4 = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
STRATEGIES3 = ("INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
BASE_MODELS = [
    "Qwen/Qwen2.5-3B", "Qwen/Qwen2.5-1.5B", "meta-llama/Llama-3.2-3B",
    "Qwen/Qwen2.5-7B", "allenai/OLMo-2-1124-7B", "google/gemma-2-9b",
    "allenai/OLMo-2-0425-1B", "google/gemma-2-2b",
    "ibm-granite/granite-3.3-2b-base", "mistralai/Mistral-7B-v0.3",
    "deepseek-ai/deepseek-llm-7b-base",
]
THREE_MODELS = [
    "Qwen/Qwen2.5-3B", "Qwen/Qwen2.5-1.5B", "meta-llama/Llama-3.2-3B",
    "Qwen/Qwen2.5-7B", "allenai/OLMo-2-1124-7B", "google/gemma-2-9b",
]


def holm(p_values):
    """Holm step-down adjusted p values, returned in original order."""
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted, running = [0.0] * n, 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (n - rank) * p_values[idx]))
        adjusted[idx] = running
    return adjusted


def exact_mc_interval(exceedances, iterations, confidence=0.95):
    """Clopper-Pearson interval for the Monte Carlo exceedance probability."""
    alpha = 1 - confidence
    lo = 0.0 if exceedances == 0 else float(beta.ppf(alpha / 2, exceedances, iterations - exceedances + 1))
    hi = 1.0 if exceedances == iterations else float(beta.ppf(1 - alpha / 2, exceedances + 1, iterations - exceedances))
    return [lo, hi]


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_unique_top_logit(row):
    logits = row.get("forced_choice", {}).get("raw_logits", {})
    if not logits:
        return False
    values = list(logits.values())
    return sum(value == max(values) for value in values) == 1


def _clusters(rows, allowed, *, require_pair=False):
    """Return counts by template; optionally retain only complete wording pairs."""
    rows = [r for r in rows if r.get("forced_choice") and r["forced_choice"].get("strategy") in allowed]
    if require_pair:
        grouped = {}
        for r in rows:
            key = (r.get("scenario_id"), r.get("permutation_index"))
            grouped.setdefault(key, {})[r.get("wording")] = r
        rows = []
        for pair in grouped.values():
            if set(pair) != {"original", "paraphrase"}:
                continue
            if any(pair[w]["forced_choice"].get("tied_max_count", 1) != 1 for w in pair):
                continue
            rows.extend(pair.values())
    counts = {}
    for r in rows:
        cluster = r.get("triad_id") or r.get("template_id") or r.get("scenario_id")
        if cluster is None:
            raise ValueError("row lacks cluster identifier")
        vector = counts.setdefault(cluster, {s: 0 for s in allowed})
        vector[r["forced_choice"]["strategy"]] += 1
    return counts, len(rows)


def randomization_tests(counts, strategies, observed_strategy, contrast_strategy,
                        *, iterations=50_000, seed=20261111):
    """Cluster-block strategy relabeling and C-vs-comparator cluster sign flips."""
    if not counts:
        raise ValueError("empty analysis set")
    labels = tuple(strategies)
    perms = list(itertools.permutations(range(len(labels))))
    matrix = np.array([[v[s] for s in labels] for v in counts.values()], dtype=np.int64)
    n = int(matrix.sum())
    obs_idx, cmp_idx = labels.index(observed_strategy), labels.index(contrast_strategy)
    observed_rate = float(matrix[:, obs_idx].sum() / n)
    observed_diff = float((matrix[:, obs_idx] - matrix[:, cmp_idx]).sum() / n)
    rng = np.random.default_rng(seed)

    # Under label exchangeability, permute the category names as a block within
    # each template, preserving all repeated observations and cluster totals.
    perm_array = np.asarray(perms, dtype=np.int64)
    draw_ids = rng.integers(0, len(perms), size=(iterations, len(counts)))
    permuted_counts = np.empty((iterations, len(counts)), dtype=np.int64)
    for k in range(len(counts)):
        permuted_counts[:, k] = matrix[k, perm_array[draw_ids[:, k], obs_idx]]
    null_rates = permuted_counts.sum(axis=1) / n
    exceed_uniform = int(np.count_nonzero(null_rates >= observed_rate - 1e-15))
    p_uniform = (exceed_uniform + 1) / (iterations + 1)

    # Under C/comparator exchangeability, swap those labels for each whole
    # template. Other categories and within-template dependence remain intact.
    d = matrix[:, obs_idx] - matrix[:, cmp_idx]
    signs = rng.choice(np.array([-1, 1], dtype=np.int8), size=(iterations, len(counts)))
    null_diffs = (signs * d).sum(axis=1) / n
    exceed_diff = int(np.count_nonzero(np.abs(null_diffs) >= abs(observed_diff) - 1e-15))
    p_diff = (exceed_diff + 1) / (iterations + 1)
    return {
        "clusters": len(counts), "presentations": n,
        "strategy_counts": {s: int(matrix[:, i].sum()) for i, s in enumerate(labels)},
        "observed_rate": observed_rate, "uniform_reference": 1 / len(labels),
        "rate_minus_uniform": observed_rate - 1 / len(labels),
        "uniform_test": {"null": "within-cluster strategy-label exchangeability",
                         "tail": "one-sided greater", "exceedances": exceed_uniform,
                         "iterations": iterations, "p_mc": p_uniform,
                         "mc_se": float((p_uniform * (1-p_uniform) / (iterations+1)) ** 0.5),
                         "exceedance_probability_mc_95pct_ci": exact_mc_interval(exceed_uniform, iterations)},
        "contrast_strategy": contrast_strategy, "rate_difference": observed_diff,
        "contrast_test": {"null": f"within-cluster exchangeability of {observed_strategy} and {contrast_strategy}",
                          "tail": "two-sided", "exceedances": exceed_diff,
                          "iterations": iterations, "p_mc": p_diff,
                          "mc_se": float((p_diff * (1-p_diff) / (iterations+1)) ** 0.5),
                          "exceedance_probability_mc_95pct_ci": exact_mc_interval(exceed_diff, iterations)},
    }


def run(iterations=50_000, seed=20261111):
    readout = json.loads((OUT / "cohort_statistical_readout.json").read_text(encoding="utf-8-sig"))
    four_records = []
    for model in BASE_MODELS:
        if model not in readout["per_model_results"] or model.endswith("pythia-12b-deduped"):
            continue
        meta = readout["per_model_results"][model]
        path = ROOT / "results" / "cooperate_rewording" / meta["directory"] / "rows.jsonl"
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
        run_summary = json.loads((path.parent / "summary.json").read_text(encoding="utf-8-sig"))
        for bank in ("phase0b", "phase1"):
            subset = [r for r in rows if r.get("bank") == bank
                      and r.get("utility_condition") == "equal_utility"
                      and not r.get("is_symmetric_control")]
            counts, n = _clusters(subset, STRATEGIES4, require_pair=True)
            rec = randomization_tests(counts, STRATEGIES4, "COOPERATE", "INDEPENDENT",
                                      iterations=iterations, seed=seed + len(four_records))
            rec.update({"model": model, "family": meta["family"], "bank": bank,
                        "data_file": str(path.relative_to(ROOT)), "data_sha256": _hash(path),
                        "run_id": run_summary.get("run_id"),
                        "resolved_model_revision": run_summary.get("resolved_model_revision"),
                        "wordings": ["original", "paraphrase"],
                        "tie_rule": "keep only complete original/paraphrase pairs with unique argmax on both",
                        "excluded_by_tie_or_pair_rule": len(subset) - n})
            four_records.append(rec)

    # Select phase0b follow-up runs by immutable bank hash and model identity.
    three_records = []
    wanted_hash = "a01b07fa14d02ff5b52647fe9e5357a664ceb4825e6cc84379385ac1f07da73b"
    for model in THREE_MODELS:
        candidates = []
        for summary_path in (ROOT / "results" / "choice_set").glob("*/summary.json"):
            summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
            if summary.get("model") == model and summary.get("bank_sha256") == wanted_hash:
                candidates.append(summary_path.parent / "rows.jsonl")
        if not candidates:
            continue
        path = sorted(candidates)[-1]
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
        run_summary = json.loads((path.parent / "summary.json").read_text(encoding="utf-8-sig"))
        subset = [r for r in rows if r.get("condition") == "three"]
        tied = [r for r in subset if not has_unique_top_logit(r)]
        unique = [r for r in subset if has_unique_top_logit(r)]
        counts, n = _clusters(unique, STRATEGIES3)
        rec = randomization_tests(counts, STRATEGIES3, "INDEPENDENT", "COMPETE_EXPLOIT",
                                  iterations=iterations, seed=seed + 10_000 + len(three_records))
        # Keep the legacy deterministic tie-broken outcome as a transparent sensitivity.
        tied_counts, _ = _clusters(subset, STRATEGIES3)
        tie_inclusive = randomization_tests(tied_counts, STRATEGIES3, "INDEPENDENT", "COMPETE_EXPLOIT",
                                            iterations=iterations, seed=seed + 20_000 + len(three_records))
        selected = [r for r in unique if r.get("forced_choice")]
        letters = {letter: sum(r["forced_choice"]["letter"] == letter for r in selected) for letter in "ABC"}
        rec.update({"model": model, "family": readout["per_model_results"].get(model, {}).get("family"),
                    "bank": "phase0b_choice_set_removal", "data_file": str(path.relative_to(ROOT)),
                    "data_sha256": _hash(path), "run_id": run_summary.get("run_id"),
                    "resolved_model_revision": run_summary.get("resolved_model_revision"),
                    "bank_sha256": run_summary.get("bank_sha256"),
                    "replacement_bank_sha256": run_summary.get("replacement_bank_sha256"),
                    "bank_status": run_summary.get("bank_status"),
                    "research_status": run_summary.get("research_status"),
                    "excluded_tied_maxima": len(tied),
                    "tie_inclusive_sensitivity": tie_inclusive,
                    "position_letter_counts": letters,
                    "position_letter_rates": {k: v / len(selected) for k, v in letters.items()},
                    "strategy_rate_by_position": {
                        letter: {s: sum(r["forced_choice"]["strategy"] == s for r in selected if r["forced_choice"]["letter"] == letter) / max(1, letters[letter]) for s in STRATEGIES3}
                        for letter in "ABC"},
                    "interpretation": "conditional substitution after removing COOPERATE; not an inherent preference"})
        three_records.append(rec)

    # The stated primary family contains both four-option hypotheses for each
    # checkpoint-bank combination: one Holm family of 44 tests.
    four_p = [(x, key) for x in four_records for key in ("uniform_test", "contrast_test")]
    four_adj = holm([x[key]["p_mc"] for x, key in four_p])
    for (x, key), p in zip(four_p, four_adj):
        x[key]["p_holm"] = p
    for family in ("uniform_test", "contrast_test"):
        pvals = [x[family]["p_mc"] for x in three_records]
        adj = holm(pvals)
        for x, p in zip(three_records, adj):
            x[family]["p_holm"] = p
        tie_pvals = [x["tie_inclusive_sensitivity"][family]["p_mc"] for x in three_records]
        tie_adj = holm(tie_pvals)
        for x, p in zip(three_records, tie_adj):
            x["tie_inclusive_sensitivity"][family]["p_holm"] = p
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip())
    return {
        "analysis": "post-hoc template-clustered Monte Carlo randomization",
        "source_revision": revision, "worktree_dirty_at_analysis": dirty,
        "analysis_code_sha256": _hash(Path(__file__)),
        "seed": seed, "iterations_per_test": iterations,
        "multiple_testing": "Holm across all 44 four-option tests; Holm separately across six tests per three-option hypothesis",
        "four_option": four_records, "three_option": three_records,
    }


def report(data):
    out = ["# Post-hoc clustered significance analysis", "",
           "The inferential analyses below were formulated after inspecting the experimental results. They are exploratory, not preregistered confirmatory tests.", "",
           "## Four-option forced-choice results", "",
           "The test set is 11 responsive pretrained base checkpoints × two banks, pooling original and reworded presentations while retaining them inside the same template cluster. Pythia is excluded because near-invariant position-A responding makes strategy labels uninterpretable. Complete wording pairs are kept only when both argmax results are untied.", "",
           "| Model | Bank | N | Clusters | COOP rate | COOP−INDEP | p uniform (Holm) | p contrast (Holm) |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for x in data["four_option"]:
        out.append(f"| {x['model']} | {x['bank']} | {x['presentations']} | {x['clusters']} | {x['observed_rate']:.3f} | {x['rate_difference']:.3f} | {x['uniform_test']['p_mc']:.6g} ({x['uniform_test']['p_holm']:.6g}) | {x['contrast_test']['p_mc']:.6g} ({x['contrast_test']['p_holm']:.6g}) |")
    out += ["", "## Three-option choice-set removal", "",
            "Six pretrained checkpoints were selected for this follow-up; the six were not six independent training-history replications. The primary denominator excludes rows with tied top logits, so only unique argmax outcomes count. The tie-broken legacy outcome is analyzed as a Holm-adjusted sensitivity in the JSON. The main comparison uses template-block label exchangeability for independence above a 1/3 uniform-choice reference and template-block swaps for independence versus competition. Position-letter counts are calculated on unique-argmax rows.", "",
            "| Model | N unique / ties excluded | Clusters | INDEP rate | INDEP−COMPETE | p uniform (Holm) | p contrast (Holm) | Position A/B/C |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for x in data["three_option"]:
        q = x['position_letter_rates']
        out.append(f"| {x['model']} | {x['presentations']} / {x['excluded_tied_maxima']} | {x['clusters']} | {x['observed_rate']:.3f} | {x['rate_difference']:.3f} | {x['uniform_test']['p_mc']:.6g} ({x['uniform_test']['p_holm']:.6g}) | {x['contrast_test']['p_mc']:.6g} ({x['contrast_test']['p_holm']:.6g}) | {q['A']:.2f}/{q['B']:.2f}/{q['C']:.2f} |")
    out += ["", "## Methods and assumptions", "",
            f"Each test uses {data['iterations_per_test']:,} Monte Carlo randomizations, a fixed seed, and the plus-one p-value estimator. The smallest reportable Monte Carlo p is 1/(B+1); each test stores a Monte Carlo standard error and an exact binomial 95% interval for its exceedance probability. Holm adjustment is applied jointly to the 44 four-option tests and separately within each six-test three-option hypothesis family.", "",
            "The 25% and 33.3% references are uniform-choice benchmarks. Randomization constructs test exchangeability of strategy labels within template clusters while preserving the observed response pattern and repeated measures; they do not prove that a model literally samples uniformly under the null. The cooperation–independence contrast is a selection-rate contrast. Cluster-level label exchangeability is a substantive assumption, particularly because templates are deliberately heterogeneous. Results are sensitivity evidence, not estimates of population behavior across model training histories.", "",
            "Rewording is paired by scenario and option permutation, and both wordings remain within the same randomized cluster. The intervention is analyzed separately because removing an option changes the choice set. It is conditional substitution, not evidence that independence is an intrinsic second choice.", "",
            "Three-option runs use the phase0b bank hash marked `pending_human_scientific_review`; semantic validity and utility properties therefore remain provisional. See the JSON for input SHA-256 values, denominators, counts, position-specific selection rates, and Monte Carlo exceedances.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20261111)
    args = parser.parse_args()
    data = run(args.iterations, args.seed)
    (OUT / "posthoc_significance_results.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (OUT / "POSTHOC_SIGNIFICANCE_METHODS.md").write_text(report(data), encoding="utf-8")
    print(f"Wrote {len(data['four_option'])} four-option and {len(data['three_option'])} three-option tests")


if __name__ == "__main__":
    main()
