"""Four-strategy linear-probe analysis for saved contrastive-mapping runs.

This module consumes saved activations only; it never loads a model or performs
inference. See docs/four_strategy_probe.md for assumptions and interpretation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .contrastive_mapping import DEFAULT_MODEL_ID, DEFAULT_REVISION, STRATEGIES

VERSION = "four-strategy-probe-v1.1"


def _sha(path: str | Path) -> str:
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_dataset(run_dir: str | Path, prompts_path: str | Path, *, expected_prompts_path: str | Path | None = None,
                 expected_manifest_path: str | Path | None = None, allow_mock: bool = False):
    """Load and integrity-check all prompt-aligned residual arrays."""
    run_dir, prompts_path = Path(run_dir), Path(prompts_path)
    manifest_path = run_dir / "manifest.json"
    hashes_path = run_dir / "evidence_hashes.json"
    for path in (manifest_path, hashes_path, prompts_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes_bytes = hashes_path.read_bytes()
    if manifest.get("status") != "completed":
        raise ValueError("Run is not marked completed")
    if manifest.get("model_id") != DEFAULT_MODEL_ID or manifest.get("model_revision") != DEFAULT_REVISION:
        raise ValueError("Unexpected model identity or immutable revision")
    if manifest.get("mock") and not allow_mock:
        raise ValueError("Synthetic run refused; pass allow_mock only for test fixtures")
    if manifest.get("evidence_hashes_sha256") != hashlib.sha256(hashes_bytes).hexdigest():
        raise ValueError("evidence_hashes.json SHA256 does not match run manifest")
    expected_prompt_sha = manifest.get("prompts_sha256")
    if expected_prompt_sha != _sha(prompts_path):
        raise ValueError("Prompt inventory SHA256 does not match run manifest")
    if expected_prompts_path is not None:
        expected_path = Path(expected_prompts_path)
        if not expected_path.is_file():
            raise FileNotFoundError(expected_path)
        if _sha(expected_path) != expected_prompt_sha or expected_path.read_bytes() != prompts_path.read_bytes():
            raise ValueError("Saved run prompt inventory does not match the prepared expected inventory")
    expected_plan = None
    if expected_manifest_path is not None:
        expected_manifest_path = Path(expected_manifest_path)
        if not expected_manifest_path.is_file():
            raise FileNotFoundError(expected_manifest_path)
        expected_plan = json.loads(expected_manifest_path.read_text(encoding="utf-8"))
        for field in ("prompts_sha256", "bank_sha256", "script_sha256", "num_scenarios", "num_prompts", "strategies", "target_model", "target_revision"):
            if manifest.get(field) != expected_plan.get(field):
                raise ValueError(f"Run provenance does not match prepared plan field {field}")
    hashes = json.loads(hashes_bytes)
    if hashes.get("prompts.jsonl") != _sha(prompts_path):
        raise ValueError("Prompt inventory SHA256 does not match evidence hashes")
    prompts = [json.loads(line) for line in prompts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(prompts) != manifest.get("num_prompts"):
        raise ValueError(f"Prompt count mismatch: expected {manifest.get('num_prompts')}, found {len(prompts)}")
    by_sid: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for p in prompts:
        sid, strat, pid = p["scenario_id"], p["strategy"], p["prompt_id"]
        if strat not in STRATEGIES or strat in by_sid[sid]:
            raise ValueError(f"Invalid or duplicate strategy inventory for {sid}: {strat}")
        if pid != f"{sid}_{strat}":
            raise ValueError(f"Noncanonical prompt_id for {sid}/{strat}")
        by_sid[sid][strat] = p
    if any(set(x) != set(STRATEGIES) for x in by_sid.values()):
        raise ValueError("Every scenario must contain exactly one prompt for each strategy")
    if len(by_sid) != manifest.get("num_scenarios"):
        raise ValueError("Scenario count does not match run manifest")
    for sid, strat_map in by_sid.items():
        rows = list(strat_map.values())
        for field in ("group_key", "domain", "split", "domain_split"):
            if len({r.get(field) for r in rows}) != 1:
                raise ValueError(f"Scenario {sid} has inconsistent {field}")
    family_splits, domain_splits, family_domain_splits = defaultdict(set), defaultdict(set), defaultdict(set)
    for sid, strat_map in by_sid.items():
        p = next(iter(strat_map.values()))
        family_splits[p["group_key"]].add(p["split"])
        domain_splits[p["domain"]].add(p["domain_split"])
        family_domain_splits[p["group_key"]].add(p["domain_split"])
    if any(len(v) != 1 for v in family_splits.values()):
        raise ValueError("Template/triad family crosses discovery and evaluation splits")
    if any(len(v) != 1 for v in domain_splits.values()):
        raise ValueError("Domain crosses discovery and evaluation splits")
    if any(len(v) != 1 for v in family_domain_splits.values()):
        raise ValueError("A template/triad family crosses the domain-held-out split")
    prompt_ids = {p["prompt_id"] for p in prompts}
    activation_files = set((run_dir / "activations").glob("*.npz"))
    expected_names = {f"{pid}.npz" for pid in prompt_ids}
    actual_names = {p.name for p in activation_files}
    if expected_names != actual_names:
        raise ValueError(f"Activation inventory mismatch; missing={sorted(expected_names-actual_names)[:3]}, extra={sorted(actual_names-expected_names)[:3]}")
    if set(hashes) != {"prompts.jsonl", *(f"activations/{name}" for name in expected_names)}:
        raise ValueError("Evidence hash inventory has missing or unexpected entries")
    arrays = {}
    shape = None
    for p in prompts:
        pid = p["prompt_id"]
        rel = f"activations/{pid}.npz"
        ap = run_dir / rel
        if hashes.get(rel) != _sha(ap):
            raise ValueError(f"Evidence hash mismatch: {rel}")
        try:
            with np.load(ap, allow_pickle=False) as data:
                arr = data["residual"]
        except Exception as e:
            raise ValueError(f"Unreadable residual tensor: {ap}: {e}") from e
        if arr.ndim != 2 or not np.isfinite(arr).all():
            raise ValueError(f"Malformed/non-finite activation tensor: {pid}")
        if shape is None:
            shape = arr.shape
        if arr.shape != shape:
            raise ValueError(f"Inconsistent tensor shape at {pid}: {arr.shape}, expected {shape}")
        arrays[pid] = arr.astype(np.float64, copy=False)
    if tuple(shape) != (manifest.get("num_layers"), manifest.get("hidden_size")):
        raise ValueError(f"Tensor shape {shape} disagrees with manifest dimensions")
    if not manifest.get("mock") and (len(by_sid) != 124 or len(prompts) != 496 or shape != (28, 1536)):
        raise ValueError("Real run does not match expected 124-scenario, 496-prompt, [28,1536] inventory")
    return manifest, prompts, arrays


def scenario_center(prompts, arrays):
    """Return [scenarios, strategies, layers, hidden] scenario-centered residuals."""
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for p in prompts:
        grouped[p["scenario_id"]][p["strategy"]] = p
    sids = sorted(grouped)
    meta = [grouped[s][STRATEGIES[0]] for s in sids]
    x = np.stack([[arrays[grouped[s][k]["prompt_id"]] for k in STRATEGIES] for s in sids])
    x -= x.mean(axis=1, keepdims=True)
    return sids, meta, x


def _fit_probe(x_train, y_train, groups, x_eval, y_eval, *, c_values=(0.01, 0.1, 1.0, 10.0), seed=42):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import balanced_accuracy_score
    folds = min(4, len(set(groups)))
    if folds < 2:
        raise ValueError("At least two discovery families/domains are required for grouped C selection")
    splitter = GroupKFold(n_splits=folds)
    scores = []
    for c in c_values:
        fold_scores = []
        for tr, va in splitter.split(x_train, y_train, groups):
            model = LogisticRegression(C=float(c), max_iter=500, solver="lbfgs", random_state=seed)
            model.fit(x_train[tr], y_train[tr])
            fold_scores.append(balanced_accuracy_score(y_train[va], model.predict(x_train[va])))
        scores.append(float(np.mean(fold_scores)))
    best_c = float(c_values[int(np.argmax(scores))])
    model = LogisticRegression(C=best_c, max_iter=500, solver="lbfgs", random_state=seed)
    model.fit(x_train, y_train)
    return model, best_c, scores


def _cluster_bootstrap(metric, y, pred, groups, *, n_boot, seed):
    unique = np.asarray(sorted(set(groups)))
    per_cluster = {g: np.flatnonzero(np.asarray(groups) == g) for g in unique}
    rng = np.random.default_rng(seed)
    cluster_values = {g: float(metric(y[ix], pred[ix])) for g, ix in per_cluster.items()}
    value_array = np.asarray([cluster_values[g] for g in unique], dtype=float)
    sampled = rng.integers(0, len(unique), size=(n_boot, len(unique)))
    vals = value_array[sampled].mean(axis=1)
    point = float(np.mean(list(cluster_values.values())))
    return [float(point), float(np.quantile(vals, .025)), float(np.quantile(vals, .975))]


def _cluster_bootstrap_pairwise_cosine(cosine_matrix, *, n_boot=1000, seed=42):
    """Bootstrap a pairwise cosine U-statistic without domain self-pairs.

    A repeated bootstrap draw changes domain weight, but is not a new domain.
    Weight each distinct original pair by count[i]*count[j] and exclude i == j.
    """
    matrix = np.asarray(cosine_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] < 2:
        raise ValueError("Pairwise cosine bootstrap requires a square matrix for at least two domains")
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    i, j = np.triu_indices(matrix.shape[0], 1)
    pair_values = matrix[i, j]
    if not np.isfinite(pair_values).all():
        raise ValueError("Pairwise cosine matrix has non-finite off-diagonal values")
    point = float(pair_values.mean())
    rng = np.random.default_rng(seed)
    n = matrix.shape[0]
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        while True:
            counts = np.bincount(rng.integers(0, n, size=n), minlength=n)
            weights = counts[i] * counts[j]
            total = weights.sum()
            if total:
                boot[b] = float(np.dot(weights, pair_values) / total)
                break
    return [point, float(np.quantile(boot, .025)), float(np.quantile(boot, .975))]


def _layer_eval(x, discovery, evaluation, cluster_keys, lexical_centered, *, n_boot, seed, permutations, label="split", progress=False):
    from sklearn.metrics import (balanced_accuracy_score, f1_score, confusion_matrix,
                                 roc_auc_score, classification_report)
    layers = x.shape[2]
    result = []
    rng = np.random.default_rng(seed)
    for layer in range(layers):
        xd, xv = x[discovery, :, layer, :].reshape(-1, x.shape[-1]), x[evaluation, :, layer, :].reshape(-1, x.shape[-1])
        yd = np.tile(np.arange(4), int(discovery.sum()))
        yv = np.tile(np.arange(4), int(evaluation.sum()))
        dg = np.repeat(np.asarray(cluster_keys)[discovery], 4)
        eg = np.repeat(np.asarray(cluster_keys)[evaluation], 4)
        model, c, cv_scores = _fit_probe(xd, yd, dg, xv, yv)
        pred = model.predict(xv)
        probs = model.predict_proba(xv)
        cm = confusion_matrix(yv, pred, labels=np.arange(4))
        auc = {}
        for i, name in enumerate(STRATEGIES):
            binary = (yv == i).astype(int)
            auc[name] = float(roc_auc_score(binary, probs[:, i])) if len(np.unique(binary)) == 2 else None
        raw_norm = np.linalg.norm(x[evaluation, :, layer, :], axis=-1)
        # Direction-only control: unit-normalize each scenario-centered action vector.
        nd = xd / np.maximum(np.linalg.norm(xd, axis=1, keepdims=True), 1e-12)
        nv = xv / np.maximum(np.linalg.norm(xv, axis=1, keepdims=True), 1e-12)
        nmodel, nc, _ = _fit_probe(nd, yd, dg, nv, yv)
        # Train-only multivariate adjustment for scenario-centered word and character counts.
        from sklearn.linear_model import Ridge
        ld = lexical_centered[discovery].reshape(-1, 2)
        lv = lexical_centered[evaluation].reshape(-1, 2)
        ridge = Ridge(alpha=1.0).fit(ld, xd)
        xdr, xvr = xd - ridge.predict(ld), xv - ridge.predict(lv)
        lmodel, _, _ = _fit_probe(xdr, yd, dg, xvr, yv)
        family_boot = _cluster_bootstrap(balanced_accuracy_score, yv, pred, eg, n_boot=n_boot, seed=seed + layer)
        f1_boot = _cluster_bootstrap(lambda a,b: f1_score(a,b,average="macro"), yv, pred, eg, n_boot=n_boot, seed=seed + 500 + layer)
        auc_ci = {}
        for i, name in enumerate(STRATEGIES):
            auc_ci[name] = _cluster_bootstrap(lambda a,b,ix=i: roc_auc_score((a==ix).astype(int), b[:,ix]),
                                               yv, probs, eg, n_boot=n_boot, seed=seed + 800 + layer*4+i)
        perm_acc = []
        for _ in range(permutations):
            # Permute strategy labels independently inside each scenario (4! options),
            # preserving family/domain cluster structure and exact scenario balance.
            py_d = yd.reshape(-1, 4).copy()
            py_v = yv.reshape(-1, 4).copy()
            for row in py_d:
                row[:] = rng.permutation(row)
            for row in py_v:
                row[:] = rng.permutation(row)
            pm = __import__("sklearn.linear_model", fromlist=["LogisticRegression"]).LogisticRegression(
                C=c, max_iter=500, solver="lbfgs", random_state=seed)
            pm.fit(xd, py_d.ravel())
            perm_acc.append(float(balanced_accuracy_score(py_v.ravel(), pm.predict(xv))))
        result.append({
            "layer": layer, "selected_C": c, "cv_balanced_accuracy_by_C": dict(zip([str(c0) for c0 in (.01,.1,1.,10.)], cv_scores)),
            "balanced_accuracy": family_boot, "macro_f1": f1_boot,
            "one_vs_rest_auroc": auc, "one_vs_rest_auroc_cluster_ci": auc_ci, "confusion_matrix": cm.tolist(),
            "direction_normalized_balanced_accuracy": float(balanced_accuracy_score(yv, nmodel.predict(nv))),
            "lexical_adjusted_balanced_accuracy": float(balanced_accuracy_score(yv, lmodel.predict(xvr))),
            "mean_action_residual_norm_by_strategy": {STRATEGIES[i]: float(raw_norm[:,i].mean()) for i in range(4)},
            "permutation_balanced_accuracy": {"mean": float(np.mean(perm_acc)) if perm_acc else None,
                                               "q025": float(np.quantile(perm_acc,.025)) if perm_acc else None,
                                               "q975": float(np.quantile(perm_acc,.975)) if perm_acc else None,
                                               "n": permutations},
        })
        if progress and (layer == layers - 1 or (layer + 1) % 4 == 0):
            print(f"{label}: completed layer {layer + 1}/{layers}", flush=True)
    return result


def analyze_four_strategy(run_dir, prompts_path, output_dir, *, expected_prompts_path=None, expected_manifest_path=None,
                          n_boot=1000, permutations=100, allow_mock=False, seed=42, progress=False):
    """Compute layerwise strategy means, OVR directions, probes and controls."""
    from sklearn.metrics import balanced_accuracy_score
    manifest, prompts, arrays = load_dataset(run_dir, prompts_path, expected_prompts_path=expected_prompts_path,
                                             expected_manifest_path=expected_manifest_path, allow_mock=allow_mock)
    sids, meta, x = scenario_center(prompts, arrays)
    family = np.asarray([m["group_key"] for m in meta])
    domain = np.asarray([m["domain"] for m in meta])
    fam_disc = np.asarray([m["split"] == "discovery" for m in meta])
    fam_eval = ~fam_disc
    dom_disc = np.asarray([m["domain_split"] == "discovery" for m in meta])
    dom_eval = ~dom_disc
    prompt_lookup = {p["scenario_id"]: {} for p in prompts}
    for p in prompts:
        prompt_lookup[p["scenario_id"]][p["strategy"]] = p
    lexical = np.asarray([[[prompt_lookup[s][k]["action_word_count"], prompt_lookup[s][k]["action_char_count"]]
                           for k in STRATEGIES] for s in sids], dtype=np.float64)
    lexical -= lexical.mean(axis=1, keepdims=True)
    if len(set(family[fam_disc])) < 2 or len(set(family[fam_eval])) < 1:
        raise ValueError("Insufficient held-out template/triad families")
    if len(set(domain[dom_disc])) < 2 or len(set(domain[dom_eval])) < 1:
        raise ValueError("Insufficient strict held-out domains")
    # Mean residual vectors weight independent families equally, then scenarios equally within family.
    strategy_means = np.zeros((x.shape[2], 4, x.shape[3]))
    for li in range(x.shape[2]):
        for si in range(4):
            family_means = [x[(family == f) & fam_disc, si, li].mean(axis=0) for f in sorted(set(family[fam_disc]))]
            strategy_means[li, si] = np.mean(family_means, axis=0)
    ovr = strategy_means - (strategy_means.sum(axis=1, keepdims=True) - strategy_means) / 3
    pair_cos, eff_rank, stab = [], [], []
    rng = np.random.default_rng(seed)
    for li in range(x.shape[2]):
        norms = np.linalg.norm(strategy_means[li], axis=1)
        unit = strategy_means[li] / np.maximum(norms[:, None], 1e-12)
        cos = unit @ unit.T
        singular = np.linalg.svd(strategy_means[li], compute_uv=False)
        p = singular / max(singular.sum(), 1e-12)
        erank = float(np.exp(-np.sum(p[p > 0] * np.log(p[p > 0]))))
        pair_cos.append(cos.tolist()); eff_rank.append(erank)
        fs = sorted(set(family[fam_disc]))
        half = len(fs) // 2
        a, b = fs[:half], fs[half:]
        ma = np.mean([x[(family == f), :, li].mean(axis=0) for f in a], axis=0)
        mb = np.mean([x[(family == f), :, li].mean(axis=0) for f in b], axis=0)
        cos_halves = []
        for si in range(4):
            va = ma[si] - np.mean(np.delete(ma, si, axis=0), axis=0)
            vb = mb[si] - np.mean(np.delete(mb, si, axis=0), axis=0)
            cos_halves.append(float(va @ vb / max(np.linalg.norm(va)*np.linalg.norm(vb), 1e-12)))
        stab.append(cos_halves)
    discovery_domains_for_means = sorted(set(domain[dom_disc]))
    domain_strategy_means = np.zeros_like(strategy_means)
    for li in range(x.shape[2]):
        per_domain = [x[(domain == d) & dom_disc, :, li].mean(axis=0) for d in discovery_domains_for_means]
        domain_strategy_means[li] = np.mean(per_domain, axis=0)
    domain_ovr = domain_strategy_means - (domain_strategy_means.sum(axis=1, keepdims=True) - domain_strategy_means) / 3
    fam_metrics = _layer_eval(x, fam_disc, fam_eval, family, lexical, n_boot=n_boot, seed=seed,
                              permutations=permutations, label="family held-out", progress=progress)
    dom_metrics = _layer_eval(x, dom_disc, dom_eval, domain, lexical, n_boot=n_boot, seed=seed + 10000,
                              permutations=permutations, label="domain held-out", progress=progress)
    # Layerwise projections onto discovery-only one-vs-rest mean residual directions.
    projections = {s: [] for s in STRATEGIES}
    direction_corr = {s: [] for s in STRATEGIES}
    for li in range(x.shape[2]):
        for si, s in enumerate(STRATEGIES):
            v = ovr[li, si]; v /= max(np.linalg.norm(v), 1e-12)
            pos = x[fam_eval, si, li] @ v
            rest = x[fam_eval][:, np.arange(4) != si, li].reshape(-1, x.shape[-1]) @ v
            projections[s].append({"positive": pos, "rest": rest})
            words = lexical[fam_eval, si, 0]
            chars = lexical[fam_eval, si, 1]
            direction_corr[s].append({"word_count_r": float(np.corrcoef(words, pos)[0, 1]) if np.std(words)>1e-12 and np.std(pos)>1e-12 else 0.0,
                                      "char_count_r": float(np.corrcoef(chars, pos)[0, 1]) if np.std(chars)>1e-12 and np.std(pos)>1e-12 else 0.0})
    # Cross-domain direction agreement is a primary endpoint. Domain means use
    # only scenario-centered vectors and are compared with the pooled discovery direction.
    domain_directional = []
    rng_domains = np.random.default_rng(seed + 30000)
    discovery_domains, heldout_domains = sorted(set(domain[dom_disc])), sorted(set(domain[dom_eval]))
    for li in range(x.shape[2]):
        from sklearn.linear_model import Ridge
        dlex=lexical[dom_disc].reshape(-1,2)
        dx=x[dom_disc,:,li].reshape(-1,x.shape[-1])
        lexical_model=Ridge(alpha=1.0).fit(dlex,dx)
        xadj=x[:,:,li]-lexical_model.predict(lexical.reshape(-1,2)).reshape(x.shape[0],4,x.shape[-1])
        xadj-=xadj.mean(axis=1,keepdims=True)
        adj_domain_means=np.mean([xadj[(domain==d)&dom_disc].mean(axis=0) for d in discovery_domains],axis=0)
        adj_ovr=adj_domain_means-(adj_domain_means.sum(axis=0,keepdims=True)-adj_domain_means)/3
        by_strategy = {}
        for si, strat in enumerate(STRATEGIES):
            ref = domain_ovr[li, si]
            ref_unit = ref / max(np.linalg.norm(ref), 1e-12)
            adj_ref=adj_ovr[si]
            adj_ref_unit=adj_ref/max(np.linalg.norm(adj_ref),1e-12)
            split_dirs, adj_split_dirs = {}, {}
            for d in discovery_domains + heldout_domains:
                mask = domain == d
                cls = x[mask, :, li].mean(axis=0)
                dv = cls[si] - np.mean(np.delete(cls, si, axis=0), axis=0)
                split_dirs[d] = dv
                acl= xadj[mask].mean(axis=0)
                adj_split_dirs[d]=acl[si]-np.mean(np.delete(acl,si,axis=0),axis=0)
            discovery_cos = []
            for i, da in enumerate(discovery_domains):
                va = split_dirs[da]
                for db in discovery_domains[i+1:]:
                    vb = split_dirs[db]
                    discovery_cos.append(float(va @ vb / max(np.linalg.norm(va)*np.linalg.norm(vb),1e-12)))
            alignment, margin, adj_alignment, adj_margin = [], [], [], []
            for d in heldout_domains:
                v = split_dirs[d]
                alignment.append(float(v @ ref_unit / max(np.linalg.norm(v),1e-12)))
                av=adj_split_dirs[d]
                adj_alignment.append(float(av @ adj_ref_unit/max(np.linalg.norm(av),1e-12)))
                mask = domain == d
                pos = x[mask, si, li] @ ref_unit
                rest = x[mask][:, np.arange(4) != si, li].reshape(-1,x.shape[-1]) @ ref_unit
                margin.append(float(pos.mean()-rest.mean()))
                apos=xadj[mask,si]@adj_ref_unit
                arest=xadj[mask][:,np.arange(4)!=si].reshape(-1,x.shape[-1])@adj_ref_unit
                adj_margin.append(float(apos.mean()-arest.mean()))
            def ci(values):
                vals=np.asarray(values,dtype=float)
                if len(vals)<2: return [float(vals.mean()),float(vals.mean()),float(vals.mean())]
                boot=np.mean(rng_domains.choice(vals,size=(n_boot,len(vals)),replace=True),axis=1)
                return [float(vals.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]
            cos_matrix=np.zeros((len(discovery_domains),len(discovery_domains)),dtype=float)
            pair_map={}
            for ia,da in enumerate(discovery_domains):
                for ib in range(ia+1,len(discovery_domains)):
                    db=discovery_domains[ib]
                    value=float(split_dirs[da] @ split_dirs[db] / max(np.linalg.norm(split_dirs[da])*np.linalg.norm(split_dirs[db]),1e-12))
                    cos_matrix[ia,ib]=cos_matrix[ib,ia]=value
                    pair_map[f"{da}|{db}"]=value
            discovery_pair_ci=_cluster_bootstrap_pairwise_cosine(cos_matrix,n_boot=n_boot,seed=seed+li*4+si)
            by_strategy[strat] = {"discovery_domain_pairwise_cosine_mean": float(np.mean(discovery_cos)) if discovery_cos else 0.0,
                "discovery_domain_pairwise_cosine_cluster_ci": discovery_pair_ci,
                "discovery_domain_pairwise_cosines": pair_map,
                "heldout_domain_direction_alignment_cosine": ci(alignment),
                "heldout_domain_projection_margin": ci(margin),
                "lexically_adjusted_heldout_domain_direction_alignment_cosine": ci(adj_alignment),
                "lexically_adjusted_heldout_domain_projection_margin": ci(adj_margin),
                "heldout_domain_alignment_by_domain": dict(zip(heldout_domains,alignment)),
                "heldout_domain_margin_by_domain": dict(zip(heldout_domains,margin))}
        domain_directional.append({"layer":li,"by_strategy":by_strategy})
    report = {
        "version": VERSION, "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_module_sha256": _sha(Path(__file__)),
        "model_id": manifest["model_id"], "model_revision": manifest["model_revision"],
        "source_run": str(Path(run_dir).resolve()), "source_manifest_sha256": _sha(Path(run_dir)/"manifest.json"),
        "source_evidence_hashes_sha256": manifest["evidence_hashes_sha256"], "num_scenarios": len(sids),
        "expected_prompt_inventory_sha256": _sha(expected_prompts_path) if expected_prompts_path else None,
        "prepared_plan_manifest_sha256": _sha(expected_manifest_path) if expected_manifest_path else None,
        "provenance": {k: manifest.get(k) for k in ("bank_path", "bank_sha256", "script_sha256", "prompts_sha256", "created_utc", "started_utc", "ended_utc", "dtype", "device", "mock")},
        "num_prompts": len(prompts), "tensor_shape": list(next(iter(arrays.values())).shape),
        "scenario_centering": "For each scenario and layer, subtract the mean of its four strategy residual vectors.",
        "strategy_order": list(STRATEGIES), "family_held_out": {"discovery_families": sorted(set(family[fam_disc])),
            "evaluation_families": sorted(set(family[fam_eval])), "layer_metrics": fam_metrics},
        "domain_held_out": {"discovery_domains": sorted(set(domain[dom_disc])),
            "evaluation_domains": sorted(set(domain[dom_eval])), "layer_metrics": dom_metrics,
            "directional_consistency_primary_outcome": domain_directional,
            "domain_equal_weighted_discovery_strategy_means": domain_strategy_means.tolist(),
            "domain_equal_weighted_discovery_ovr_directions": domain_ovr.tolist()},
        "geometry": {"strategy_mean_residuals": strategy_means.tolist(), "one_vs_rest_directions": ovr.tolist(),
            "pairwise_direction_cosines": pair_cos, "effective_rank": eff_rank,
            "split_half_ovr_direction_cosines": stab},
        "projection_distributions": {k: [{"positive": a["positive"].tolist(), "rest": a["rest"].tolist()} for a in v]
                                     for k,v in projections.items()},
        "projection_length_correlations": direction_corr,
        "controls": {"permutation": "Within-scenario strategy-label shuffle; all four labels remain represented per scenario. Probe C is fixed at the training-only selected value.",
            "normalization": "Each scenario-centered vector L2-normalized before train-only C selection and evaluation.",
            "lexical_adjustment": "Within-scenario centered action word and character counts are regressed from activations with Ridge(alpha=1) fit only on discovery rows; probes and cross-domain direction consistency are evaluated on residualized vectors.",
            "lexical_length": {s: {"mean_words": float(np.mean([p["action_word_count"] for p in prompts if p["strategy"]==s])),
                                     "mean_chars": float(np.mean([p["action_char_count"] for p in prompts if p["strategy"]==s]))} for s in STRATEGIES}},
        "interpretation_boundary": "Tests linear distinguishability of the four presented action descriptions in residual-stream activations. Does not establish preference, action selection, or distinct causal decision mechanisms. First detectable layer is not an origin claim."
    }
    report["empirical_summary"] = _empirical_summary(report)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/"four_strategy_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_report(report, out/"four_strategy_report.md")
    _plot(report, out/"four_strategy_layerwise.png")
    _plot_geometry(report, out/"four_strategy_geometry.png")
    return report


def _empirical_summary(r):
    """Compact descriptive findings derived only from saved evaluation metrics."""
    strategies = r["strategy_order"]
    directional = r["domain_held_out"]["directional_consistency_primary_outcome"]
    domain_metrics = r["domain_held_out"]["layer_metrics"]
    family_metrics = r["family_held_out"]["layer_metrics"]
    adjusted_candidate_layers = []
    raw_all_positive = True
    per_strategy = {}
    for strategy in strategies:
        raw = [entry["by_strategy"][strategy]["heldout_domain_direction_alignment_cosine"] for entry in directional]
        adj = [entry["by_strategy"][strategy]["lexically_adjusted_heldout_domain_direction_alignment_cosine"] for entry in directional]
        per_strategy[strategy] = {
            "raw_alignment_mean_range": [float(min(x[0] for x in raw)), float(max(x[0] for x in raw))],
            "raw_alignment_min_pointwise_ci_lower": float(min(x[1] for x in raw)),
            "length_adjusted_alignment_mean_range": [float(min(x[0] for x in adj)), float(max(x[0] for x in adj))],
            "length_adjusted_alignment_layers_ci_lower_above_zero": [i for i,x in enumerate(adj) if x[1] > 0],
        }
        raw_all_positive &= all(x[1] > 0 for x in raw)
    for entry, metric in zip(directional, domain_metrics):
        all_directions_positive = all(
            entry["by_strategy"][s]["lexically_adjusted_heldout_domain_direction_alignment_cosine"][1] > 0
            and entry["by_strategy"][s]["lexically_adjusted_heldout_domain_projection_margin"][1] > 0
            for s in strategies
        )
        if all_directions_positive and metric["lexical_adjusted_balanced_accuracy"] >= 0.85:
            adjusted_candidate_layers.append(entry["layer"])
    example_layers = [i for i in (18,22) if i < len(domain_metrics)]
    examples = {}
    for i in example_layers:
        examples[str(i)] = {
            "family_balanced_accuracy": family_metrics[i]["balanced_accuracy"],
            "domain_balanced_accuracy": domain_metrics[i]["balanced_accuracy"],
            "domain_macro_f1": domain_metrics[i]["macro_f1"],
            "direction_normalized_balanced_accuracy": domain_metrics[i]["direction_normalized_balanced_accuracy"],
            "lexical_adjusted_balanced_accuracy": domain_metrics[i]["lexical_adjusted_balanced_accuracy"],
            "permutation_balanced_accuracy": domain_metrics[i]["permutation_balanced_accuracy"],
            "one_vs_rest_auroc": domain_metrics[i]["one_vs_rest_auroc"],
            "confusion_matrix": domain_metrics[i]["confusion_matrix"],
            "strategy_direction_alignment": {s: {
                "raw": directional[i]["by_strategy"][s]["heldout_domain_direction_alignment_cosine"],
                "length_adjusted": directional[i]["by_strategy"][s]["lexically_adjusted_heldout_domain_direction_alignment_cosine"],
                "raw_projection_margin": directional[i]["by_strategy"][s]["heldout_domain_projection_margin"],
                "length_adjusted_projection_margin": directional[i]["by_strategy"][s]["lexically_adjusted_heldout_domain_projection_margin"],
            } for s in strategies},
            "pairwise_strategy_direction_cosines": r["geometry"]["pairwise_direction_cosines"][i],
            "strategy_subspace_effective_rank": r["geometry"]["effective_rank"][i],
        }
    return {
        "family_balanced_accuracy_range": [float(min(x["balanced_accuracy"][0] for x in family_metrics)), float(max(x["balanced_accuracy"][0] for x in family_metrics))],
        "domain_balanced_accuracy_range": [float(min(x["balanced_accuracy"][0] for x in domain_metrics)), float(max(x["balanced_accuracy"][0] for x in domain_metrics))],
        "domain_macro_f1_range": [float(min(x["macro_f1"][0] for x in domain_metrics)), float(max(x["macro_f1"][0] for x in domain_metrics))],
        "direction_normalized_domain_balanced_accuracy_range": [float(min(x["direction_normalized_balanced_accuracy"] for x in domain_metrics)), float(max(x["direction_normalized_balanced_accuracy"] for x in domain_metrics))],
        "length_adjusted_domain_balanced_accuracy_range": [float(min(x["lexical_adjusted_balanced_accuracy"] for x in domain_metrics)), float(max(x["lexical_adjusted_balanced_accuracy"] for x in domain_metrics))],
        "raw_domain_alignment_pointwise_ci_positive_for_all_strategies_all_layers": bool(raw_all_positive),
        "length_adjusted_candidate_layers": adjusted_candidate_layers,
        "candidate_layer_rule": "Exploratory candidates require all four strategies' pointwise 95% cluster-CI lower bounds above zero for length-adjusted held-out-domain direction alignment and projection margin, plus length-adjusted four-class balanced accuracy >= 0.85.",
        "strategy_directional_ranges": per_strategy,
        "illustrative_layers": examples,
    }


def _write_report(r, path):
    summary = r.get("empirical_summary") or _empirical_summary(r)
    candidate_layers = ", ".join(map(str, summary["length_adjusted_candidate_layers"])) or "none"
    lines = ["# Four-strategy linear-probe analysis", "", f"- Model: `{r['model_id']}` revision `{r['model_revision']}`",
        f"- Source run: `{r['source_run']}`", f"- Scenarios/prompts: {r['num_scenarios']} / {r['num_prompts']}",
        f"- Tensor: {r['tensor_shape']} per prompt", "", r["interpretation_boundary"], "",
        "Scenario-centered residual vectors are evaluated with discovery-only regularization selection and grouped held-out evaluation.", "",
        "See [EMPIRICAL_INTERPRETATION.md](EMPIRICAL_INTERPRETATION.md) for a run-specific scientific interpretation.", "",
        "![Layerwise held-out probe performance](four_strategy_layerwise.png)", "", "![Cross-domain direction consistency and strategy geometry](four_strategy_geometry.png)", "",
        "## Empirical summary", "",
        f"Family-held-out balanced accuracy spans {summary['family_balanced_accuracy_range'][0]:.3f}–{summary['family_balanced_accuracy_range'][1]:.3f}; strict domain-held-out balanced accuracy spans {summary['domain_balanced_accuracy_range'][0]:.3f}–{summary['domain_balanced_accuracy_range'][1]:.3f} (macro-F1 {summary['domain_macro_f1_range'][0]:.3f}–{summary['domain_macro_f1_range'][1]:.3f}). Unit-normalized domain accuracy spans {summary['direction_normalized_domain_balanced_accuracy_range'][0]:.3f}–{summary['direction_normalized_domain_balanced_accuracy_range'][1]:.3f}; length-adjusted accuracy spans {summary['length_adjusted_domain_balanced_accuracy_range'][0]:.3f}–{summary['length_adjusted_domain_balanced_accuracy_range'][1]:.3f}.", "",
        f"Raw held-out-domain direction-alignment pointwise 95% cluster intervals are positive for all four strategies at every layer: {summary['raw_domain_alignment_pointwise_ci_positive_for_all_strategies_all_layers']}. The length-adjusted exploratory candidate layers are {candidate_layers}, requiring all four alignment and projection-margin intervals to exclude zero and adjusted four-class balanced accuracy ≥ 0.85. These pointwise scans are not multiplicity-corrected and do not localize representational origins.", "",
        "| Strategy | Raw domain alignment mean range | Length-adjusted alignment mean range |", "|---|---:|---:|"]
    for strategy in r["strategy_order"]:
        stats=summary["strategy_directional_ranges"][strategy]
        lines.append(f"| {strategy} | {stats['raw_alignment_mean_range'][0]:.3f}–{stats['raw_alignment_mean_range'][1]:.3f} | {stats['length_adjusted_alignment_mean_range'][0]:.3f}–{stats['length_adjusted_alignment_mean_range'][1]:.3f} |")
    lines += ["", "## Template/triad-family held-out", "", "| Layer | Balanced accuracy (cluster 95% CI) | Macro-F1 (cluster 95% CI) | Direction-normalized BA | Permutation mean | C |", "|---:|---:|---:|---:|---:|---:|"]
    for m in r["family_held_out"]["layer_metrics"]:
        ba, f1 = m["balanced_accuracy"], m["macro_f1"]
        lines.append(f"| {m['layer']} | {ba[0]:.3f} [{ba[1]:.3f}, {ba[2]:.3f}] | {f1[0]:.3f} [{f1[1]:.3f}, {f1[2]:.3f}] | {m['direction_normalized_balanced_accuracy']:.3f} | {m['permutation_balanced_accuracy']['mean'] if m['permutation_balanced_accuracy']['mean'] is not None else float('nan'):.3f} | {m['selected_C']:g} |")
    lines += ["", "## Strict domain-held-out", "", "Domain-level directional agreement with the discovery aggregate is the primary outcome. Each held-out domain is summarized separately after within-scenario centering; cluster intervals resample held-out domains. Length-adjusted columns use discovery-only ridge residualization of centered word and character counts.", "", "| Layer | Strategy | Held-out direction cosine (95% CI) | Length-adjusted cosine (95% CI) | Projection margin (95% CI) | Length-adjusted margin (95% CI) | Discovery domain-pair cosine (95% cluster CI) |", "|---:|---|---:|---:|---:|---:|---:|"]
    for entry in r["domain_held_out"]["directional_consistency_primary_outcome"]:
        for strategy, vals in entry["by_strategy"].items():
            cos, margin = vals["heldout_domain_direction_alignment_cosine"], vals["heldout_domain_projection_margin"]
            acos, amargin = vals["lexically_adjusted_heldout_domain_direction_alignment_cosine"], vals["lexically_adjusted_heldout_domain_projection_margin"]
            dcos=vals["discovery_domain_pairwise_cosine_cluster_ci"]
            lines.append(f"| {entry['layer']} | {strategy} | {cos[0]:.3f} [{cos[1]:.3f}, {cos[2]:.3f}] | {acos[0]:.3f} [{acos[1]:.3f}, {acos[2]:.3f}] | {margin[0]:.3f} [{margin[1]:.3f}, {margin[2]:.3f}] | {amargin[0]:.3f} [{amargin[1]:.3f}, {amargin[2]:.3f}] | {dcos[0]:.3f} [{dcos[1]:.3f}, {dcos[2]:.3f}] |")
    lines += ["", "Held-out four-class classification is a complementary endpoint.", "", "| Layer | Balanced accuracy (cluster 95% CI) | Macro-F1 (cluster 95% CI) | Direction-normalized BA | Lexically adjusted BA | Permutation mean |", "|---:|---:|---:|---:|---:|---:|"]
    for m in r["domain_held_out"]["layer_metrics"]:
        ba, f1 = m["balanced_accuracy"], m["macro_f1"]
        pm=m['permutation_balanced_accuracy']['mean']
        lines.append(f"| {m['layer']} | {ba[0]:.3f} [{ba[1]:.3f}, {ba[2]:.3f}] | {f1[0]:.3f} [{f1[1]:.3f}, {f1[2]:.3f}] | {m['direction_normalized_balanced_accuracy']:.3f} | {m['lexical_adjusted_balanced_accuracy']:.3f} | {pm:.3f} |")
    lines += ["", "## Geometry and diagnostics", "", "Pairwise cosine matrices, effective rank, split-half direction stability, OVR projection distributions, confusion matrices, AUROCs, residual norms, and lexical length summaries are in the companion JSON. The permutation baseline shuffles labels within each scenario and preserves exact class balance and cluster membership. Confidence intervals resample held-out families/domains as clusters.", "", "## Scientific limits", "", r["interpretation_boundary"], "Lexical controls are descriptive only; matched word/character counts do not remove semantic or tokenization confounds. The number of independent family/domain clusters limits uncertainty, and layerwise inspection is descriptive rather than a multiplicity-corrected change-point test."]
    path.write_text("\n".join(lines)+"\n", encoding="utf-8")


def _plot(r, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam, dom = r["family_held_out"]["layer_metrics"], r["domain_held_out"]["layer_metrics"]
    layers = [m["layer"] for m in fam]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for ax, data, title in ((axes[0,0],fam,"Family held-out"),(axes[0,1],dom,"Domain held-out")):
        y=np.array([m["balanced_accuracy"] for m in data]); ax.plot(layers,y[:,0],label="raw vectors")
        ax.fill_between(layers,y[:,1],y[:,2],alpha=.2); ax.plot(layers,[m["direction_normalized_balanced_accuracy"] for m in data],"--",label="unit-normalized")
        ax.plot(layers,[m["permutation_balanced_accuracy"]["mean"] or 0 for m in data],":",label="within-scenario permutation")
        ax.axhline(.25,color="black",lw=.7); ax.set(title=title,ylabel="Balanced accuracy",xlabel="Transformer block"); ax.legend(fontsize=8)
    axes[1,0].plot(layers,r["geometry"]["effective_rank"]); axes[1,0].set(title="Strategy mean subspace effective rank",xlabel="Transformer block",ylabel="Effective rank")
    ddata=r["domain_held_out"]["directional_consistency_primary_outcome"]
    dmean=[np.mean([v["heldout_domain_direction_alignment_cosine"][0] for v in e["by_strategy"].values()]) for e in ddata]
    dlo=[np.mean([v["heldout_domain_direction_alignment_cosine"][1] for v in e["by_strategy"].values()]) for e in ddata]
    dhi=[np.mean([v["heldout_domain_direction_alignment_cosine"][2] for v in e["by_strategy"].values()]) for e in ddata]
    axes[1,1].plot(layers,dmean); axes[1,1].fill_between(layers,dlo,dhi,alpha=.2); axes[1,1].axhline(0,color="black",lw=.7); axes[1,1].set(title="Held-out domain direction alignment (primary)",xlabel="Transformer block",ylabel="Mean cosine")
    fig.suptitle("Four-strategy representation probe (scenario-centered)")
    fig.savefig(path,dpi=160); plt.close(fig)


def _plot_geometry(r, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    layers=list(range(len(r["geometry"]["effective_rank"])))
    fig,axes=plt.subplots(1,3,figsize=(16,4.5),constrained_layout=True)
    directional=r["domain_held_out"]["directional_consistency_primary_outcome"]
    for strategy in STRATEGIES:
        means=[e["by_strategy"][strategy]["heldout_domain_direction_alignment_cosine"][0] for e in directional]
        low=[e["by_strategy"][strategy]["heldout_domain_direction_alignment_cosine"][1] for e in directional]
        high=[e["by_strategy"][strategy]["heldout_domain_direction_alignment_cosine"][2] for e in directional]
        adjusted=[e["by_strategy"][strategy]["lexically_adjusted_heldout_domain_direction_alignment_cosine"][0] for e in directional]
        line,=axes[0].plot(layers,means,label=strategy); axes[0].plot(layers,adjusted,linestyle="--",color=line.get_color(),label=f"{strategy} length-adjusted"); axes[0].fill_between(layers,low,high,alpha=.08,color=line.get_color())
    axes[0].axhline(0,color="black",lw=.7); axes[0].set(title="Held-out domain direction alignment",xlabel="Transformer block",ylabel="Cosine")
    axes[0].legend(fontsize=7)
    labels=[]
    for i in range(4):
        for j in range(i+1,4):
            axes[1].plot(layers,[m[i][j] for m in r["geometry"]["pairwise_direction_cosines"]])
            labels.append(f"{STRATEGIES[i]} / {STRATEGIES[j]}")
    axes[1].axhline(0,color="black",lw=.7); axes[1].set(title="Discovery strategy direction cosines",xlabel="Transformer block",ylabel="Cosine")
    axes[1].legend(labels,fontsize=6)
    axes[2].plot(layers,r["geometry"]["effective_rank"]); axes[2].set(title="Strategy subspace effective rank",xlabel="Transformer block",ylabel="Effective rank")
    fig.suptitle("Domain invariance and strategy geometry")
    fig.savefig(path,dpi=160); plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",required=True); p.add_argument("--prompts",required=True); p.add_argument("--output",required=True)
    p.add_argument("--expected-prompts",default="research/contrastive_full_v1/prompts.jsonl")
    p.add_argument("--expected-manifest",default="research/contrastive_full_v1/manifest.json")
    p.add_argument("--bootstrap",type=int,default=1000); p.add_argument("--permutations",type=int,default=100)
    a=p.parse_args(); analyze_four_strategy(a.run_dir,a.prompts,a.output,expected_prompts_path=a.expected_prompts,
        expected_manifest_path=a.expected_manifest,n_boot=a.bootstrap,permutations=a.permutations,progress=True)
    print(f"Report written to {a.output}")

if __name__ == "__main__": main()
