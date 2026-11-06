"""Non-destructive, matrix-only reanalysis of cooperative_lexical_geometry_v1."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "research" / "cooperative_lexical_geometry_v1"
RESULTS = SOURCE / "results"
LEXICON = SOURCE / "lexicon_frozen.json"
OUT = Path(__file__).resolve().parent / "outputs"
LANGS = ["en", "fr", "es", "ar", "zh"]
CATS = ["cooperation", "competition_exploitation", "independent_action", "neutral_activity"]
CONTROLS = CATS[1:]
MODELS = ["multilingual-e5-base", "bge-m3", "LaBSE"]

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def pair_masks(rows: list[dict], category_rows: list[dict]) -> dict[str, np.ndarray]:
    n = len(category_rows)
    domains = np.asarray([r["domain"] for r in category_rows])
    kernels = np.asarray([r["concept_id"].rsplit("-", 1)[1] for r in category_rows])
    upper = np.triu(np.ones((n, n), dtype=bool), 1)
    offdiag = ~np.eye(n, dtype=bool)
    same_domain = domains[:, None] == domains[None, :]
    same_kernel = kernels[:, None] == kernels[None, :]
    return {
        "within_all_distinct_concepts": upper,
        "within_same_domain": upper & same_domain,
        "within_excluding_repeated_kernel": upper & ~same_kernel,
        "cross_all_distinct_concepts": offdiag,
        "cross_excluding_repeated_kernel": offdiag & ~same_kernel,
    }

def weighted_pair_mean_batch(matrices: np.ndarray, mask: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Evaluate pair means using crossed domain × kernel pigeonhole weights."""
    numer = np.einsum("bi,ij,bj->b", weights, matrices * mask, weights, optimize=True)
    denom = np.einsum("bi,ij,bj->b", weights, mask.astype(np.float64), weights, optimize=True)
    return np.divide(numer, denom, out=np.full_like(numer, np.nan), where=denom > 0)

def crossed_pair_bootstrap_batch(
    matrix: np.ndarray, mask: np.ndarray, domain_draws: np.ndarray, kernel_draws: np.ndarray,
    domain_index: np.ndarray, kernel_index: np.ndarray, chunk: int = 128,
) -> np.ndarray:
    """Bootstrap pair records without inventing pairs between duplicate cluster copies.

    For pair endpoints from different clusters, multiply endpoint draw counts. If
    both endpoints share a domain or phrase kernel, use that cluster's count once.
    This preserves the original all-pairs estimand in expectation instead of
    inflating within-cluster pair mass under a naive endpoint-weight product.
    """
    result = np.empty(len(domain_draws), dtype=np.float64)
    domain_diff = domain_index[:, None] != domain_index[None, :]
    kernel_diff = kernel_index[:, None] != kernel_index[None, :]
    masked_matrix = matrix * mask
    for start in range(0, len(domain_draws), chunk):
        stop = min(len(domain_draws), start + chunk)
        d = domain_draws[start:stop][:, domain_index]
        k = kernel_draws[start:stop][:, kernel_index]
        dleft, dright = d[:, :, None], d[:, None, :]
        kleft, kright = k[:, :, None], k[:, None, :]
        dw = np.where(domain_diff[None, :, :], dleft * dright, dleft)
        kw = np.where(kernel_diff[None, :, :], kleft * kright, kleft)
        pair_w = dw * kw
        numer = np.einsum("bij,ij->b", pair_w, masked_matrix, optimize=True)
        denom = np.einsum("bij,ij->b", pair_w, mask, optimize=True)
        result[start:stop] = np.divide(numer, denom, out=np.full(stop-start, np.nan), where=denom > 0)
    return result

def crossed_cluster_bootstrap(
    matrices: dict[str, np.ndarray], masks: dict[str, np.ndarray], rows_by_cat: dict[str, list[dict]],
    draws: int, seed: int,
) -> dict[str, dict[str, np.ndarray]]:
    """Resample 10 domain clusters and 15 within-category kernel clusters.

    The domain draw is shared across categories for paired category contrasts;
    phrase-kernel clusters are resampled independently within each category.
    Pair weights count shared clusters once to preserve the all-pairs estimand.
    """
    rng = np.random.default_rng(seed)
    n_domain = len({r["domain"] for r in next(iter(rows_by_cat.values()))})
    n_kernel = len({r["concept_id"].rsplit("-", 1)[1] for r in next(iter(rows_by_cat.values()))})
    domain_names = sorted({r["domain"] for r in next(iter(rows_by_cat.values()))})
    domain_index = {d: i for i, d in enumerate(domain_names)}
    samples: dict[str, np.ndarray] = {}
    shared_domains = rng.multinomial(n_domain, np.full(n_domain, 1 / n_domain), size=draws)
    for cat, cat_rows in rows_by_cat.items():
        kernel_names = sorted({r["concept_id"].rsplit("-", 1)[1] for r in cat_rows})
        kernel_index = {k: i for i, k in enumerate(kernel_names)}
        kernels = rng.multinomial(n_kernel, np.full(n_kernel, 1 / n_kernel), size=draws)
        d_ix = np.asarray([domain_index[r["domain"]] for r in cat_rows])
        k_ix = np.asarray([kernel_index[r["concept_id"].rsplit("-", 1)[1]] for r in cat_rows])
        samples[cat] = crossed_pair_bootstrap_batch(matrices[cat], masks[cat], shared_domains, kernels, d_ix, k_ix)
    return samples

def ci(a: np.ndarray) -> list[float]:
    return [float(np.nanquantile(a, .025)), float(np.nanquantile(a, .975))]

def direct_pair_mean(matrix: np.ndarray, mask: np.ndarray) -> float:
    return float(matrix[mask].mean())

def kernel_group_permutation(
    concept_matrix: np.ndarray, rows: list[dict], draws: int, seed: int, exclude_same_kernel: bool = False,
) -> dict:
    """Exchange category labels over 60 kernel clusters, retaining all 10 domain frames."""
    rng = np.random.default_rng(seed)
    groups = sorted({(r["category"], r["concept_id"].rsplit("-", 1)[1]) for r in rows})
    labels0 = np.asarray([c for c, _ in groups])
    if len(groups) != 60 or any(np.sum(labels0 == c) != 15 for c in CATS):
        raise ValueError("Expected 60 phrase-kernel clusters, 15 per category")
    group_indices = []
    for c, k in groups:
        group_indices.append([i for i, r in enumerate(rows) if r["category"] == c and r["concept_id"].rsplit("-", 1)[1] == k])
    # Collapse each 10×10 phrase-kernel block; exact concept diagonals are removed.
    gmat = np.zeros((len(groups), len(groups)), dtype=np.float64)
    gcount = np.zeros_like(gmat)
    for i, ix in enumerate(group_indices):
        for j, jx in enumerate(group_indices):
            block = concept_matrix[np.ix_(ix, jx)]
            valid = ~np.eye(len(ix), dtype=bool) if i == j else np.ones(block.shape, dtype=bool)
            gmat[i, j] = float(block[valid].mean())
            gcount[i, j] = int(valid.sum())
    if exclude_same_kernel:
        # The diagonal is the only repeated phrase-kernel cluster; ordinal kernel
        # numbers in different categories do not identify the same kernel.
        np.fill_diagonal(gcount, 0)
    observed_labels = labels0.copy()
    def statistic(labels: np.ndarray) -> float:
        means = {}
        for cat in CATS:
            ix = np.flatnonzero(labels == cat)
            w = gcount[np.ix_(ix, ix)]
            means[cat] = float((gmat[np.ix_(ix, ix)] * w).sum() / w.sum())
        return means["cooperation"] - float(np.mean([means[c] for c in CONTROLS]))
    observed = statistic(observed_labels)
    null = np.empty(draws, dtype=np.float64)
    for b in range(draws):
        null[b] = statistic(rng.permutation(labels0))
    p = (1 + np.sum(np.abs(null) >= abs(observed))) / (draws + 1)
    return {"observed_cooperation_minus_mean_controls": observed, "two_sided_p": float(p),
            "permutations": draws, "unit": "phrase-kernel cluster; all domain renderings remain together",
            "excludes_repeated_kernel_pairs": exclude_same_kernel}

def build_view(model: str, view: str, rows: list[dict], keys: list[tuple[str, str]], draws: int,
               permutation_draws: int, seed: int) -> dict:
    matrix_path = RESULTS / f"{model}_cosine_{'raw' if view == 'raw' else 'centered'}.npy"
    full = np.load(matrix_path, mmap_mode="r")
    if full.shape != (3000, 3000):
        raise ValueError(f"Unexpected cosine matrix shape in {matrix_path}: {full.shape}")
    key_index = {k: i for i, k in enumerate(keys)}
    rows_by_cat = {c: [r for r in rows if r["category"] == c] for c in CATS}
    cats_global = {}
    masks = {}
    lang_within = {c: {} for c in CATS}
    cross_by_pair = {c: {} for c in CATS}
    exact = {c: [] for c in CATS}
    for cat in CATS:
        cr = rows_by_cat[cat]
        masks[cat] = pair_masks(rows, cr)
        cat_lang_mats = []
        cat_cross_mats = []
        for lang in LANGS:
            ix = [key_index[(r["concept_id"], lang)] for r in cr]
            m = np.asarray(full[np.ix_(ix, ix)], dtype=np.float64)
            lang_within[cat][lang] = {
                "all_distinct_concepts": direct_pair_mean(m, masks[cat]["within_all_distinct_concepts"]),
                "same_domain_only": direct_pair_mean(m, masks[cat]["within_same_domain"]),
                "exclude_repeated_kernel": direct_pair_mean(m, masks[cat]["within_excluding_repeated_kernel"]),
                "pair_counts": {name: int(mask.sum()) for name, mask in masks[cat].items() if name.startswith("within_")},
            }
            cat_lang_mats.append(m)
        cats_global[cat] = np.mean(cat_lang_mats, axis=0)
        for a, b in itertools.combinations(LANGS, 2):
            ia = [key_index[(r["concept_id"], a)] for r in cr]
            ib = [key_index[(r["concept_id"], b)] for r in cr]
            m = np.asarray(full[np.ix_(ia, ib)], dtype=np.float64)
            cross_by_pair[cat][f"{a}-{b}"] = {
                "all_distinct_concepts": direct_pair_mean(m, masks[cat]["cross_all_distinct_concepts"]),
                "exclude_repeated_kernel": direct_pair_mean(m, masks[cat]["cross_excluding_repeated_kernel"]),
                "pair_counts": {"all_distinct_concepts": int(masks[cat]["cross_all_distinct_concepts"].sum()),
                                "exclude_repeated_kernel": int(masks[cat]["cross_excluding_repeated_kernel"].sum())},
            }
            cat_cross_mats.append(m)
            exact[cat].extend(np.diag(m).tolist())
        # 10 language-pair matrices averaged before cluster bootstrap; all pair estimands remain equal-weighted.
        cats_global[f"cross::{cat}"] = np.mean(cat_cross_mats, axis=0)

    metric_specs = {
        "within_all_distinct_concepts": ({c: cats_global[c] for c in CATS}, {c: masks[c]["within_all_distinct_concepts"] for c in CATS}),
        "within_exclude_repeated_kernel": ({c: cats_global[c] for c in CATS}, {c: masks[c]["within_excluding_repeated_kernel"] for c in CATS}),
        "cross_all_distinct_concepts": ({c: cats_global[f"cross::{c}"] for c in CATS}, {c: masks[c]["cross_all_distinct_concepts"] for c in CATS}),
        "cross_exclude_repeated_kernel": ({c: cats_global[f"cross::{c}"] for c in CATS}, {c: masks[c]["cross_excluding_repeated_kernel"] for c in CATS}),
    }
    output = {"model": model, "view": view, "within_language": lang_within, "cross_language_distinct_concepts": cross_by_pair,
              "exact_translation_positive_control": {c: {"mean": float(np.mean(exact[c])), "n": len(exact[c])} for c in CATS},
              "estimand_note": "All language-level values are concept-pair means; bootstrap intervals resample domain and phrase-kernel clusters with crossed pigeonhole weights."}
    bootstrap_draws = {}
    for metric, (mats, maskmap) in metric_specs.items():
        bs = crossed_cluster_bootstrap(mats, maskmap, rows_by_cat, draws,
                                       seed + sum(map(ord, metric)) % 100000)
        vals = bs
        bootstrap_draws[metric] = vals
        point = {c: direct_pair_mean(mats[c], maskmap[c]) for c in CATS}
        controls_mean = np.mean(np.stack([vals[c] for c in CONTROLS]), axis=0)
        coopdiff = vals["cooperation"] - controls_mean
        pairwise_diffs = {c: vals["cooperation"] - vals[c] for c in CONTROLS}
        independent_diff = vals["independent_action"] - vals["cooperation"]
        output.setdefault("category_contrasts", {})[metric] = {
            "category_means": point,
            "category_cluster_bootstrap_95ci": {c: ci(vals[c]) for c in CATS},
            "cooperation_minus_mean_controls": point["cooperation"] - float(np.mean([point[c] for c in CONTROLS])),
            "cooperation_minus_mean_controls_cluster_bootstrap_95ci": ci(coopdiff),
            "cooperation_minus_each_control": {c: point["cooperation"] - point[c] for c in CONTROLS},
            "cooperation_minus_each_control_cluster_bootstrap_95ci": {c: ci(pairwise_diffs[c]) for c in CONTROLS},
            "independent_action_minus_cooperation": point["independent_action"] - point["cooperation"],
            "independent_action_minus_cooperation_cluster_bootstrap_95ci": ci(independent_diff),
            "bootstrap_design": "paired domain and category-specific kernel cluster resampling; shared-cluster pair counts included once",
            "draws": draws,
        }
    output["leave_one_language_out"] = {}
    for excluded in LANGS:
        kept = [l for l in LANGS if l != excluded]
        outvals = {}
        for cat in CATS:
            per_lang = [lang_within[cat][l]["all_distinct_concepts"] for l in kept]
            outvals[cat] = float(np.mean(per_lang))
        outvals["cooperation_minus_mean_controls"] = outvals["cooperation"] - float(np.mean([outvals[c] for c in CONTROLS]))
        output["leave_one_language_out"][f"excluding_{excluded}"] = outvals
    # Kernel-cluster permutation uses language-macro matrices for within and cross-language macro matrices for cross.
    output["kernel_cluster_permutation"] = {}
    for metric, (mats, maskmap) in metric_specs.items():
        perm_matrix = np.zeros((600, 600), dtype=np.float64)
        # Align in frozen lexicon order; average over language pairs or languages first.
        if metric.startswith("within"):
            lang_mats = []
            for l in LANGS:
                ix = [key_index[(r["concept_id"], l)] for r in rows]
                lang_mats.append(np.asarray(full[np.ix_(ix, ix)], dtype=np.float64))
            perm_matrix = np.mean(lang_mats, axis=0)
        else:
            pair_mats = []
            for a, b in itertools.combinations(LANGS, 2):
                ia = [key_index[(r["concept_id"], a)] for r in rows]
                ib = [key_index[(r["concept_id"], b)] for r in rows]
                pair_mats.append(np.asarray(full[np.ix_(ia, ib)], dtype=np.float64))
            perm_matrix = np.mean(pair_mats, axis=0)
        # Build category-specific permutation results over the 60 kernel clusters.
        output["kernel_cluster_permutation"][metric] = kernel_group_permutation(
            perm_matrix, rows, permutation_draws, seed + 7001 + len(metric), metric.endswith("exclude_repeated_kernel"))
    return output

def plot_summary(results: dict, path: Path) -> None:
    metrics = ["within_all_distinct_concepts", "within_exclude_repeated_kernel", "cross_all_distinct_concepts", "cross_exclude_repeated_kernel"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, metric in zip(axes.ravel(), metrics):
        x = np.arange(len(MODELS)); width = .19
        for ci_cat, cat in enumerate(CATS):
            vals = [results[m]["category_contrasts"][metric]["category_means"][cat] for m in MODELS]
            ax.bar(x + (ci_cat - 1.5) * width, vals, width, label=cat)
        ax.set_xticks(x, MODELS, rotation=10); ax.set_title(metric.replace("_", " ")); ax.set_ylabel("mean cosine")
    axes[0, 0].legend(fontsize=8); fig.suptitle("Non-destructive reanalysis: estimand-matched category coherence")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap-draws", type=int, default=2000)
    ap.add_argument("--permutation-draws", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261106)
    args = ap.parse_args()
    if not LEXICON.exists(): raise SystemExit(f"Missing frozen lexicon: {LEXICON}")
    rows = json.loads(LEXICON.read_text(encoding="utf-8"))
    freeze = json.loads((SOURCE / "lexicon_freeze.json").read_text(encoding="utf-8"))
    if file_sha(LEXICON) != freeze["lexicon_sha256"]: raise SystemExit("Frozen lexicon hash mismatch")
    if len(rows) != 600: raise SystemExit("Expected 600 concepts")
    keys = [(r["concept_id"], l) for r in rows for l in LANGS]
    OUT.mkdir(parents=True, exist_ok=True)
    all_results = {}
    for mi, model in enumerate(MODELS):
        for vi, view in enumerate(["raw", "centered"]):
            print(f"Analyzing {model} / {view}", flush=True)
            all_results[f"{model}::{view}"] = build_view(model, view, rows, keys, args.bootstrap_draws,
                                                          args.permutation_draws,
                                                          args.seed + 100 * mi + vi)
            # Re-run permutation count at the requested setting through the same deterministic seed.
            outpath = OUT / f"{model}_{view}_reanalysis.json"
            outpath.write_text(json.dumps(all_results[f"{model}::{view}"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    plot_summary({m: all_results[f"{m}::centered"] for m in MODELS}, OUT / "category_coherence_comparison.png")
    manifest = {
        "analysis": "cooperative_lexical_geometry_v1_reanalysis", "source_experiment": str(SOURCE),
        "source_lexicon_sha256": file_sha(LEXICON), "source_matrices": {
            f"{m}_{v}": {"path": str(RESULTS / f"{m}_cosine_{'raw' if v == 'raw' else 'centered'}.npy"),
                          "sha256": file_sha(RESULTS / f"{m}_cosine_{'raw' if v == 'raw' else 'centered'}.npy")}
            for m in MODELS for v in ["raw", "centered"]},
        "no_model_inference": True, "bootstrap_draws": args.bootstrap_draws,
        "permutation_draws": args.permutation_draws, "seed": args.seed,
        "bootstrap_unit": "crossed domain (10) and phrase-kernel (15/category) pair-cluster bootstrap; shared-cluster pairs weighted once",
        "outputs": "New outputs only; original experiment results and frozen lexicon were not modified.",
        "permutation_adjustment_family": "Holm correction across all 24 model × view × metric tests",
    }
    # Correct the family of 24 kernel-cluster permutation tests, then persist the adjusted results.
    tests = []
    for key, result in all_results.items():
        model, view = key.split("::")
        for metric, test in result["kernel_cluster_permutation"].items():
            tests.append((key, metric, float(test["two_sided_p"])))
    order = sorted(range(len(tests)), key=lambda i: tests[i][2])
    adjusted = [0.0] * len(tests)
    running = 0.0
    m = len(tests)
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * tests[i][2]))
        adjusted[i] = running
    for (key, metric, _), p_adj in zip(tests, adjusted):
        all_results[key]["kernel_cluster_permutation"][metric]["holm_adjusted_p_24_tests"] = p_adj
    for key, result in all_results.items():
        model, view = key.split("::")
        (OUT / f"{model}_{view}_reanalysis.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "reanalysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote matrix-only reanalysis to {OUT}")

if __name__ == "__main__": main()
