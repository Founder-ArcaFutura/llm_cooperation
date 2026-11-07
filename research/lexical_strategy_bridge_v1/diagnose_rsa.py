"""Offline diagnostics for the lexical-strategy-bridge RSA results.

This script reads frozen captures and cached embedding arrays only. It never
loads a language model or contacts Modal. Pairwise RSA is descriptive; the
included bootstrap resamples concepts as clusters for the final-depth change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sysconfig
import platform
from importlib.metadata import version as package_version
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MODELS = ("qwen", "mistral7b", "olmo7b")
LANGUAGES = ("en", "fr", "zh", "ja", "ar")
ENCODERS = ("e5", "bge-m3", "labse")
POOLINGS = ("lexical", "final")
TRANSFORMS = ("raw_normalized_cosine", "global_centered_cosine", "language_centered_cosine")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cosine_matrix(x: np.ndarray, *, center: str = "global", groups=None) -> np.ndarray:
    """Return cosine similarities after the explicitly named centering step."""
    z = np.asarray(x, dtype=np.float64).copy()
    if center == "global":
        z -= z.mean(axis=0, keepdims=True)
    elif center == "language":
        if groups is None:
            raise ValueError("language centering requires group labels")
        for group in np.unique(groups):
            mask = np.asarray(groups) == group
            z[mask] -= z[mask].mean(axis=0, keepdims=True)
    elif center != "none":
        raise ValueError(f"unknown center mode: {center}")
    norms = np.linalg.norm(z, axis=1, keepdims=True)
    if np.any(norms <= 1e-20):
        raise ValueError("centering produced a zero vector")
    z /= norms
    return z @ z.T


def upper(matrix: np.ndarray) -> np.ndarray:
    return matrix[np.triu_indices(matrix.shape[0], 1)]


def spearman(x, y, mask=None) -> float:
    if mask is not None:
        x, y = np.asarray(x)[mask], np.asarray(y)[mask]
    value = float(spearmanr(x, y).statistic)
    return value if np.isfinite(value) else float("nan")


def partial_spearman(x, y, group_codes, covariates) -> tuple[float, float, float]:
    """Rank correlation before/after categorical and continuous pair controls.

    Pair-group effects are removed by within-group rank demeaning, equivalent
    to controlling a full set of language-pair indicators. Additional controls
    are residualized by least squares on the group-centered rank vectors.
    Returns raw rho, language-pair-adjusted rho, and fully adjusted rho.
    """
    rx, ry = rankdata(x).astype(float), rankdata(y).astype(float)
    codes = np.asarray(group_codes, dtype=np.int32)
    counts = np.bincount(codes)
    mx = np.bincount(codes, weights=rx) / counts
    my = np.bincount(codes, weights=ry) / counts
    gx, gy = rx - mx[codes], ry - my[codes]
    lang_rho = float(np.corrcoef(gx, gy)[0, 1])
    cov = np.asarray(covariates, dtype=float).copy()
    # Group-center each nuisance column before residualizing it.
    for j in range(cov.shape[1]):
        means = np.bincount(codes, weights=cov[:, j]) / counts
        cov[:, j] -= means[codes]
    gram = cov.T @ cov
    ex = gx - cov @ np.linalg.lstsq(gram, cov.T @ gx, rcond=None)[0]
    ey = gy - cov @ np.linalg.lstsq(gram, cov.T @ gy, rcond=None)[0]
    full = float(np.corrcoef(ex, ey)[0, 1])
    return float(spearmanr(x, y).statistic), lang_rho, full


def effective_rank(x: np.ndarray) -> dict:
    """Effective rank diagnostics from the centered 1000-by-hidden Gram matrix."""
    z = np.asarray(x, dtype=np.float64).copy()
    z -= z.mean(axis=0, keepdims=True)
    gram = z @ z.T
    eig = np.linalg.eigvalsh(gram)
    eig = np.maximum(eig, 0.0)[::-1]
    total = float(eig.sum())
    if total == 0:
        return {"effective_rank": 0.0, "participation_ratio": 0.0, "top1_variance": 1.0, "rank90": 0}
    p = eig / total
    nz = p > 0
    rank90 = int(np.searchsorted(np.cumsum(p), 0.90) + 1)
    return {
        "effective_rank": float(np.exp(-np.sum(p[nz] * np.log(p[nz])))),
        "participation_ratio": float(1.0 / np.sum(p * p)),
        "top1_variance": float(p[0]),
        "rank90": rank90,
    }


def load_capture(path: Path, model: str, rows: list[dict], manifest: dict):
    identity = json.loads((path / "capture_identity.json").read_text(encoding="utf-8"))
    receipt = json.loads((path / "receipt.json").read_text(encoding="utf-8"))
    wanted = {
        "plan_sha256": sha256((HERE / "frozen/manifest.json").read_bytes()),
        "model": model,
        "revision": manifest["models"][model]["revision"],
        "condition": "isolated",
        "limit": 0,
        "dtype": "float32",
    }
    if identity != wanted or receipt.get("identity") != wanted:
        raise ValueError(f"{model}: receipt identity differs from frozen plan")
    if not receipt.get("complete") or receipt.get("smoke") or receipt.get("total_records") != 1000:
        raise ValueError(f"{model}: capture is incomplete or not a full capture")
    h = manifest["models"][model]["hidden_size"]
    lexical = np.empty((1000, 8, h), dtype=np.float32)
    final = np.empty_like(lexical)
    token_counts = np.empty(1000, dtype=np.int32)
    for i, row in enumerate(rows):
        name = f"{row['id']}_{row['language']}_isolated"
        meta_path = path / "records" / f"{name}.json"
        array_path = path / "records" / f"{name}.npz"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("record") != row or meta.get("sha256") != sha256(array_path.read_bytes()):
            raise ValueError(f"{model}: record identity/hash mismatch at {name}")
        with np.load(array_path, allow_pickle=False) as data:
            lexical[i] = data["lexical"]
            final[i] = data["final"]
        if lexical[i].shape != (8, h) or final[i].shape != (8, h):
            raise ValueError(f"{model}: activation shape mismatch at {name}")
        if not np.isfinite(lexical[i]).all() or not np.isfinite(final[i]).all():
            raise ValueError(f"{model}: non-finite activations at {name}")
        token_counts[i] = len(meta["lexical_token_indices"])
    return lexical, final, token_counts, identity, receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-qwen", type=Path, required=True)
    ap.add_argument("--capture-mistral7b", type=Path, required=True)
    ap.add_argument("--capture-olmo7b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--bootstrap-replicates", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261106)
    args = ap.parse_args()
    if args.bootstrap_replicates < 20:
        raise ValueError("use at least 20 concept bootstrap replicates")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {args.output}")

    plan_dir = HERE / "frozen"
    frozen_manifest = json.loads((plan_dir / "manifest.json").read_text(encoding="utf-8"))
    inv_payload = (plan_dir / "inventory.jsonl").read_bytes()
    if sha256(inv_payload) != frozen_manifest["inventory_sha256"]:
        raise ValueError("frozen inventory hash mismatch")
    rows = [json.loads(line) for line in inv_payload.splitlines()]
    rows = [r for r in rows if r["condition"] == "isolated"]
    ref_rows = [json.loads(line) for line in (HERE / "saved_action_analysis/reference_rows.jsonl").read_text(encoding="utf-8").splitlines()]
    if rows != ref_rows or len(rows) != 1000:
        raise ValueError("frozen rows do not exactly match the embedding reference row mapping")

    langs = np.array([r["language"] for r in rows])
    concepts = np.array([r["id"] for r in rows])
    categories = np.array([r["category"] for r in rows])
    char_counts = np.array([len(r["word"]) for r in rows], dtype=float)
    concept_ids = list(dict.fromkeys(concepts.tolist()))
    concept_rows = {c: np.flatnonzero(concepts == c) for c in concept_ids}
    pair_i, pair_j = np.triu_indices(1000, 1)
    same_language = langs[pair_i] == langs[pair_j]
    cross_language = ~same_language
    same_concept = concepts[pair_i] == concepts[pair_j]
    matched_cross = cross_language & same_concept
    distinct_cross = cross_language & ~same_concept
    lang_pair = np.array(["-".join(sorted((a, b))) for a, b in zip(langs[pair_i], langs[pair_j])])
    _, lang_pair_codes = np.unique(lang_pair, return_inverse=True)
    references = {}
    ref_dir = ROOT / "research/cooperative_lexical_geometry_v2_wordlevel_expanded/exploratory_results_20261106"
    for encoder in ENCODERS:
        reference = np.load(ref_dir / f"{encoder}_embeddings.npy", allow_pickle=False)
        if reference.shape[0] != 1000 or not np.isfinite(reference).all():
            raise ValueError(f"invalid {encoder} reference embedding array")
        references[encoder] = reference
    reference_matrices = {
        encoder: {
            name: cosine_matrix(reference, center=mode, groups=langs if mode == "language" else None)
            for name, mode in (("raw_normalized_cosine", "none"), ("global_centered_cosine", "global"), ("language_centered_cosine", "language"))
        }
        for encoder, reference in references.items()
    }
    output_references = {
        encoder: {
            "path": f"research/cooperative_lexical_geometry_v2_wordlevel_expanded/exploratory_results_20261106/{encoder}_embeddings.npy",
            "shape": list(references[encoder].shape),
            "dtype": str(references[encoder].dtype),
            "sha256": sha256((ref_dir / f"{encoder}_embeddings.npy").read_bytes()),
        }
        for encoder in ENCODERS
    }

    # Mapping and source checks are explicit provenance outputs.
    capture_paths = {
        "qwen": args.capture_qwen,
        "mistral7b": args.capture_mistral7b,
        "olmo7b": args.capture_olmo7b,
    }
    captures, capture_meta = {}, {}
    for model, path in capture_paths.items():
        captures[model] = load_capture(path, model, rows, frozen_manifest)
        capture_meta[model] = {"identity": captures[model][3], "receipt": captures[model][4]}
        print(f"validated {model}: 1000 hashed records", flush=True)

    saved_results = {
        m: json.loads((HERE / f"word_analysis_results/{m}/results.json").read_text(encoding="utf-8"))
        for m in MODELS
    }
    output = {
        "method": {
            "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": package_version("scipy"), "transformers": package_version("transformers")},
            "frozen_inventory_sha256": sha256(inv_payload),
            "reference_rows_exact_match": True,
            "capture_identities": capture_meta,
            "capture_hook": "capture.py registers forward hooks on model.model.layers[i]; model.model is called directly. Stored vectors are decoder-block outputs before the enclosing model's final normalization.",
            "rsa": "Spearman correlation of upper-triangle cosine similarities; raw-normalized, globally feature-centered then row-normalized, or separately language-mean-centered then row-normalized.",
            "partial_rsa": "Rank both RDM vectors; first subtract means within each unordered language-pair stratum; then residualize same-concept status, absolute and mean character length, and absolute and mean captured-model subword count. Pearson-correlate residual ranks. Descriptive only.",
            "pair_classes": {"within_language": "same language, any concept relation", "cross_language_matching_concept": "different languages, same concept ID", "cross_language_distinct_concept": "different languages and different concept IDs"},
            "character_count": "Python Unicode code-point length of frozen word string; not grapheme-cluster length.",
            "subword_count": "number of captured tokenizer lexical-span token indices; counts are model/tokenizer-specific.",
            "reference_embeddings": output_references,
            "bootstrap": {"kind": "category-stratified concept-cluster bootstrap", "replicates": args.bootstrap_replicates, "seed": args.seed, "scope": "D7-to-D8 change in globally centered lexical-pooling E5 RSA; percentile interval; pairs are recomputed within each resampled set of 200 concepts."},
            "pair_counts": {"all": int(len(pair_i)), "within_language": int(same_language.sum()), "cross_language_matching_concept": int(matched_cross.sum()), "cross_language_distinct_concept": int(distinct_cross.sum())},
            "no_model_inference": True,
        },
        "reproduction": {},
        "rsa": {},
        "activation_geometry": {},
        "lexical_covariates": {},
        "final_transition_bootstrap": {},
    }
    capture_source = (HERE / "capture.py").read_bytes()
    if b"layers=model.model.layers" not in capture_source or b"register_forward_hook" not in capture_source:
        raise ValueError("capture hook implementation differs from the audited block-hook path")
    hf_models = Path(sysconfig.get_paths()["purelib"]) / "transformers/models"
    model_sources = {"qwen": "qwen2/modeling_qwen2.py", "mistral7b": "mistral/modeling_mistral.py", "olmo7b": "olmo2/modeling_olmo2.py"}
    hook_audit = {"capture_source_sha256": sha256(capture_source), "capture_layer_indices": {}, "transformers_model_sources": {}}
    for model, rel in model_sources.items():
        source_path = hf_models / rel
        source_text = source_path.read_text(encoding="utf-8")
        final_norm_lines = [i for i, line in enumerate(source_text.splitlines(), 1) if re.search(r"hidden_states\s*=\s*self\.norm\(hidden_states\)", line)]
        if not final_norm_lines:
            raise ValueError(f"could not verify final normalization location in {source_path}")
        indices = frozen_manifest["models"][model]["indices"]
        result_blocks = [d["block_index"] for d in saved_results[model]["depths"]]
        if result_blocks != indices:
            raise ValueError(f"{model}: saved analysis block indices differ from frozen plan")
        hook_audit["capture_layer_indices"][model] = indices
        hook_audit["transformers_model_sources"][model] = {
            "path": rel,
            "sha256": sha256(source_path.read_bytes()),
            "final_norm_line_numbers": final_norm_lines,
            "final_norm_expression": "hidden_states = self.norm(hidden_states)",
            "hook_relation": "capture.py hooks model.model.layers[i] outputs; model.model applies final norm after the decoder-layer loop, so saved block states, including the last block, are pre-final-norm.",
        }
    output["method"]["block_hook_audit"] = hook_audit
    # Reproduce analyzer's exact legacy calculation before doing controlled variants.
    for model in MODELS:
        lexical, final, token_counts, identity, receipt = captures[model]
        old = saved_results[model]
        values = {e: {"recomputed": [], "published": [], "absolute_error": []} for e in ENCODERS}
        for layer in range(8):
            activation = cosine_matrix(lexical[:, layer, :], center="global")
            for encoder in ENCODERS:
                ref = references[encoder]
                # Original analyzer retains reference dtype (float32) for its geometry.
                rz = ref - ref.mean(axis=0)
                rz /= np.maximum(np.linalg.norm(rz, axis=1, keepdims=True), 1e-20)
                ref_rdm = rz @ rz.T
                reproduced = spearman(upper(activation), upper(ref_rdm))
                published = old["depths"][layer]["embedding_rsa"][encoder]
                # SciPy releases can differ by a few 1e-10 in Spearman's final
                # floating-point reduction while preserving the ranked data.
                if not np.isclose(reproduced, published, rtol=0.0, atol=1e-8):
                    raise AssertionError(f"RSA mismatch {model} depth {layer+1} {encoder}: {reproduced} vs {published}")
                values[encoder]["recomputed"].append(reproduced)
                values[encoder]["published"].append(published)
                values[encoder]["absolute_error"].append(abs(reproduced - published))
        for encoder in ENCODERS:
            values[encoder]["max_absolute_error"] = max(values[encoder].pop("absolute_error"))
        output["reproduction"][model] = values

    # Main RSA tables across pooling, centering, layers, language, and pair classes.
    for model in MODELS:
        lexical, final, token_counts, _, _ = captures[model]
        chars = char_counts
        per_model_covars = np.column_stack((
            same_concept.astype(float),
            np.abs(chars[pair_i] - chars[pair_j]),
            (chars[pair_i] + chars[pair_j]) / 2,
            np.abs(token_counts[pair_i] - token_counts[pair_j]),
            (token_counts[pair_i] + token_counts[pair_j]) / 2,
        ))
        output["rsa"][model] = {}
        output["lexical_covariates"][model] = {
            "token_count_mean": float(token_counts.mean()),
            "token_count_range": [int(token_counts.min()), int(token_counts.max())],
            "token_counts_by_language": {l: {"mean": float(token_counts[langs == l].mean()), "range": [int(token_counts[langs == l].min()), int(token_counts[langs == l].max())]} for l in LANGUAGES},
            "character_count_by_language": {l: {"mean": float(chars[langs == l].mean()), "range": [int(chars[langs == l].min()), int(chars[langs == l].max())]} for l in LANGUAGES},
        }
        output["activation_geometry"][model] = {"lexical": [], "final": []}
        for pool_name, tensor in (("lexical", lexical), ("final", final)):
            for layer in range(8):
                x = tensor[:, layer, :]
                norms = np.linalg.norm(x.astype(np.float64), axis=1)
                center = x.astype(np.float64) - x.astype(np.float64).mean(axis=0)
                raw_cos = cosine_matrix(x, center="none")
                norm_diag = {
                    "block_index": frozen_manifest["models"][model]["indices"][layer],
                    "norm_median": float(np.median(norms)),
                    "norm_p05": float(np.quantile(norms, .05)),
                    "norm_p95": float(np.quantile(norms, .95)),
                    "norm_spearman_characters": float(spearmanr(norms, chars).statistic),
                    "norm_spearman_subword_tokens": float(spearmanr(norms, token_counts).statistic),
                    "norm_by_language": {
                        lang: {
                            "mean": float(norms[langs == lang].mean()),
                            "median": float(np.median(norms[langs == lang])),
                            "p05": float(np.quantile(norms[langs == lang], .05)),
                            "p95": float(np.quantile(norms[langs == lang], .95)),
                        }
                        for lang in LANGUAGES
                    },
                    **effective_rank(x),
                    "raw_normalized_cosine_quantiles": [float(v) for v in np.quantile(upper(raw_cos), [.05, .5, .95])],
                    "raw_normalized_cosine_distance_quantiles": [float(v) for v in np.quantile(1.0 - upper(raw_cos), [.05, .5, .95])],
                    "raw_normalized_cosine_mean_within_language": float(upper(raw_cos)[same_language].mean()),
                    "raw_normalized_cosine_mean_cross_language": float(upper(raw_cos)[cross_language].mean()),
                }
                output["activation_geometry"][model][pool_name].append(norm_diag)
                transformed = {"raw_normalized_cosine": raw_cos}
                transformed["global_centered_cosine"] = cosine_matrix(x, center="global")
                transformed["language_centered_cosine"] = cosine_matrix(x, center="language", groups=langs)
                output["rsa"][model].setdefault(pool_name, []).append({"block_index": norm_diag["block_index"], "encoders": {}})
                for encoder, ref in references.items():
                    ref_transformed = reference_matrices[encoder]
                    result = {"transforms": {}, "within_language_global_centered": {}, "cross_language_pair_classes_global_centered": {}}
                    for transform, matrix in transformed.items():
                        ax = upper(matrix)
                        by = upper(ref_transformed[transform])
                        pooled = spearman(ax, by)
                        summary = {"pooled_rsa": pooled}
                        if transform == "global_centered_cosine":
                            _, lang_adj, full_adj = partial_spearman(ax, by, lang_pair_codes, per_model_covars)
                            # Language-pair R2 in rank-space is descriptive and uses the same pair observations.
                            ar, br = rankdata(ax).astype(float), rankdata(by).astype(float)
                            counts = np.bincount(lang_pair_codes)
                            am = np.bincount(lang_pair_codes, weights=ar) / counts
                            bm = np.bincount(lang_pair_codes, weights=br) / counts
                            summary.update({
                                "language_pair_adjusted_rsa": lang_adj,
                                "language_concept_length_token_adjusted_rsa": full_adj,
                                "activation_rank_variance_explained_by_language_pair": float(np.sum(counts * (am - ar.mean())**2) / np.sum((ar - ar.mean())**2)),
                                "embedding_rank_variance_explained_by_language_pair": float(np.sum(counts * (bm - br.mean())**2) / np.sum((br - br.mean())**2)),
                            })
                        result["transforms"][transform] = summary
                    # Separate within-language RSA: each group is centered independently, then cosine normalized.
                    for lang in LANGUAGES:
                        idx = np.flatnonzero(langs == lang)
                        ax = upper(cosine_matrix(x[idx], center="global"))
                        by = upper(cosine_matrix(ref[idx], center="global"))
                        result["within_language_global_centered"][lang] = spearman(ax, by)
                    # Pair classes use the original pooled global-centered transformation.
                    ax, by = upper(transformed["global_centered_cosine"]), upper(ref_transformed["global_centered_cosine"])
                    result["cross_language_pair_classes_global_centered"] = {
                        "within_language_all": spearman(ax, by, same_language),
                        "cross_language_matching_concept": spearman(ax, by, matched_cross),
                        "cross_language_distinct_concept": spearman(ax, by, distinct_cross),
                        "mean_activation_cosine": {
                            "within_language": float(ax[same_language].mean()),
                            "cross_matching": float(ax[matched_cross].mean()),
                            "cross_distinct": float(ax[distinct_cross].mean()),
                        },
                        "mean_embedding_cosine": {
                            "within_language": float(by[same_language].mean()),
                            "cross_matching": float(by[matched_cross].mean()),
                            "cross_distinct": float(by[distinct_cross].mean()),
                        },
                    }
                    # Nuisance correlations against paired absolute differences in lexical length/tokenization.
                    result["transforms"]["global_centered_cosine"]["pairwise_nuisance_spearman"] = {
                        "activation_cosine_vs_abs_char_difference": float(spearmanr(ax, per_model_covars[:, 1]).statistic),
                        "embedding_cosine_vs_abs_char_difference": float(spearmanr(by, per_model_covars[:, 1]).statistic),
                        "activation_cosine_vs_abs_subword_difference": float(spearmanr(ax, per_model_covars[:, 3]).statistic),
                        "embedding_cosine_vs_abs_subword_difference": float(spearmanr(by, per_model_covars[:, 3]).statistic),
                    }
                    output["rsa"][model][pool_name][layer]["encoders"][encoder] = result
                print(f"{model} {pool_name} depth {layer+1}/8 complete", flush=True)

    # Concept-clustered bootstrap of the last sampled transition, primary legacy transform.
    rng = np.random.default_rng(args.seed)
    cat_concepts = {cat: [c for c in concept_ids if next(r["category"] for r in rows if r["id"] == c) == cat] for cat in sorted(set(categories))}
    bootstrap_sample = {m: {"d7": [], "d8": []} for m in MODELS}
    upper_idx = np.triu_indices(1000, 1)
    bootstrap_activation = {
        m: {d: cosine_matrix(captures[m][0][:, layer, :], center="global") for d, layer in (("d7", 6), ("d8", 7))}
        for m in MODELS
    }
    bootstrap_reference = cosine_matrix(references["e5"], center="global")
    for rep in range(args.bootstrap_replicates):
        sampled = []
        for cat in sorted(cat_concepts):
            sampled.extend(rng.choice(cat_concepts[cat], size=len(cat_concepts[cat]), replace=True).tolist())
        row_idx = np.concatenate([concept_rows[c] for c in sampled])
        for model in MODELS:
            for depth_name in ("d7", "d8"):
                sampled_act = bootstrap_activation[model][depth_name][np.ix_(row_idx, row_idx)][upper_idx]
                sampled_ref = bootstrap_reference[np.ix_(row_idx, row_idx)][upper_idx]
                bootstrap_sample[model][depth_name].append(spearman(sampled_act, sampled_ref))
    for model in MODELS:
        output["final_transition_bootstrap"][model] = {}
        d7 = np.asarray(bootstrap_sample[model]["d7"])
        d8 = np.asarray(bootstrap_sample[model]["d8"])
        delta = d8 - d7
        output["final_transition_bootstrap"][model]["e5"] = {
            "d7_median": float(np.median(d7)),
            "d8_median": float(np.median(d8)),
            "delta_median": float(np.median(delta)),
            "delta_percentile_95": [float(v) for v in np.quantile(delta, [.025, .975])],
            "replicates": args.bootstrap_replicates,
        }

    args.output.mkdir(parents=True)
    (args.output / "rsa_diagnostic_results.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "reproduction": output["reproduction"], "bootstrap": output["final_transition_bootstrap"]}, indent=2))


if __name__ == "__main__":
    main()
