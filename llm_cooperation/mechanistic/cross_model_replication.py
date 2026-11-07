"""Frozen-stimulus, bounded cross-model representation replication.

prepare is metadata/tokenization only. capture requires two explicit authorization
flags; analysis consumes completed hash-verified saved vectors only.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import re
import time

import numpy as np

from .contrastive_mapping import STRATEGIES, format_single_action_prompt
from .four_strategy_probe import scenario_center, _layer_eval, _fit_probe

SOURCE = Path("data/scenarios_phase0b_utility_matched.json")
INVENTORY = Path("research/contrastive_full_v1/prompts.jsonl")
LEGACY = Path("research/contrastive_full_v1/manifest.json")
MODELS = {
    "olmo7b": "allenai/OLMo-2-1124-7B",
    "mistral7b": "mistralai/Mistral-7B-v0.3",
    "qwen": "Qwen/Qwen2.5-1.5B",
}
DEPTHS = tuple(i / 8 for i in range(1, 9))
SEED = 42
MODES = ("raw", "word_char", "token_length", "lexical")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf8",
        newline="\n",
    )


def depth_indices(n):
    return [max(0, int(np.ceil(d * n)) - 1) for d in DEPTHS]


def code_hashes():
    return {
        p.name: sha(p)
        for p in [
            Path(__file__),
            Path(__file__).with_name("four_strategy_probe.py"),
            Path(__file__).with_name("contrastive_mapping.py"),
        ]
    }


def original_prompts():
    legacy = read(LEGACY)
    if sha(INVENTORY) != legacy["prompts_sha256"]:
        raise ValueError("Original prompt bytes differ from legacy fingerprint")
    if sha(SOURCE) != legacy["bank_sha256"]:
        raise ValueError("Frozen source hash differs from original Qwen plan")
    rows = [
        json.loads(line) for line in INVENTORY.read_text(encoding="utf8").splitlines()
    ]
    ss = {s["id"]: s for s in read(SOURCE)["scenarios"]}
    if len(rows) != 496 or len(ss) != 124 or len({r["prompt_id"] for r in rows}) != 496:
        raise ValueError("Original inventory incomplete")
    groups, domains, family_domains = (
        defaultdict(set),
        defaultdict(set),
        defaultdict(set),
    )
    for p in rows:
        s = ss[p["scenario_id"]]
        if p["prompt_text"] != format_single_action_prompt(
            s["stem"], s["options"][p["strategy"]]
        ):
            raise ValueError("Stimulus differs from frozen source")
        if p["group_key"] != (s.get("triad_id") or s["template_id"]):
            raise ValueError("Family ID mismatch")
        if p["action_word_count"] != len(p["action_text"].split()) or p[
            "action_char_count"
        ] != len(p["action_text"]):
            raise ValueError("Original lexical feature mismatch")
        groups[p["group_key"]].add(p["split"])
        domains[p["domain"]].add(p["domain_split"])
        family_domains[p["group_key"]].add(p["domain_split"])
    if any(
        len(v) != 1
        for table in (groups, domains, family_domains)
        for v in table.values()
    ):
        raise ValueError("Family/domain leakage")
    for sid in ss:
        if sorted(p["strategy"] for p in rows if p["scenario_id"] == sid) != sorted(
            STRATEGIES
        ):
            raise ValueError("Incomplete strategy quartet")
    return rows, {
        "scenarios": len(ss),
        "families": len(groups),
        "domains": len(domains),
        "family_split_counts": dict(
            (s, sum(v == {s} for v in groups.values()))
            for s in ("discovery", "evaluation")
        ),
        "domain_split_counts": dict(
            (s, sum(v == {s} for v in domains.values()))
            for s in ("discovery", "evaluation")
        ),
        "inventory_bytes_sha256": sha(INVENTORY),
        "bank_sha256": sha(SOURCE),
    }


def token_audit(tokenizer, rows, context):
    result = []
    for p in rows:
        enc = tokenizer(
            p["prompt_text"],
            add_special_tokens=True,
            return_offsets_mapping=True,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        ids, offsets = enc["input_ids"], enc["offset_mapping"]
        # Native BOS is retained. Capture must be final text colon, never added EOS.
        if (
            not ids
            or offsets[-1][1] != len(p["prompt_text"])
            or offsets[-1][0] >= offsets[-1][1]
        ):
            raise ValueError("Final token is not the final text anchor")
        if len(ids) > context:
            raise ValueError("Prompt would require truncation")
        result.append(
            {
                "prompt_id": p["prompt_id"],
                "input_ids": ids,
                "capture_index": len(ids) - 1,
                "capture_offset": offsets[-1],
                "action_tokens": len(
                    tokenizer.encode(p["action_text"], add_special_tokens=False)
                ),
                "prompt_tokens": len(ids),
                "last_token_id": ids[-1],
            }
        )
    return result


def snapshot_for(model, download=False):
    from huggingface_hub import HfApi, snapshot_download

    if model == MODELS["qwen"]:
        revision = "8faed761d45a263340a0528343f099c05c9a4323"
    elif download:
        revision = HfApi().model_info(model, revision="main").sha
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Hub did not return immutable revision")
    else:
        ref = (
            Path.home()
            / ".cache/huggingface/hub"
            / ("models--" + model.replace("/", "--"))
            / "refs/main"
        )
        if not ref.exists():
            raise FileNotFoundError(
                "No cached official main ref; metadata/tokenizer download required"
            )
        revision = ref.read_text().strip()
    path = snapshot_download(
        model,
        revision=revision,
        local_files_only=not download,
        cache_dir=str(Path(".local/cross-model-hf-cache").resolve())
        if download and model != MODELS["qwen"]
        else None,
        allow_patterns=[
            "config.json",
            "tokenizer*",
            "special_tokens_map.json",
            "vocab.json",
            "merges.txt",
            "added_tokens.json",
        ],
    )
    return revision, Path(path)


def prepare(output, download=False):
    import httpx

    out = Path(output)
    if out.exists():
        raise FileExistsError(out)
    rows, integrity = original_prompts()
    out.mkdir(parents=True)
    shutil.copyfile(INVENTORY, out / "prompts.jsonl")
    shutil.copyfile(SOURCE, out / "bank_snapshot.json")
    states = {}
    for key, model in MODELS.items():
        try:
            revision, snapshot = snapshot_for(model, download)
            from transformers import AutoTokenizer, AutoConfig

            config = AutoConfig.from_pretrained(
                str(snapshot), local_files_only=True, trust_remote_code=False
            )
            tokenizer = AutoTokenizer.from_pretrained(
                str(snapshot),
                local_files_only=True,
                trust_remote_code=False,
                use_fast=True,
            )
            audit = token_audit(tokenizer, rows, config.max_position_embeddings)
            config_dict = config.to_dict()
            state = {
                "status": "TOKENIZER_PREFLIGHT_PASSED_WEIGHTS_UNTESTED",
                "model_id": model,
                "revision": revision,
                "num_layers": config.num_hidden_layers,
                "hidden_size": config.hidden_size,
                "model_type": config.model_type,
                "architecture": config_dict.get("architectures"),
                "context_limit": config.max_position_embeddings,
                "indices": depth_indices(config.num_hidden_layers),
                "realized_depths": [
                    (i + 1) / config.num_hidden_layers
                    for i in depth_indices(config.num_hidden_layers)
                ],
                "tokenizer_type": type(tokenizer).__name__,
                "native_special_tokens": True,
                "metadata_files": {
                    p.name: sha(p)
                    for p in sorted(snapshot.iterdir())
                    if p.is_file() and p.suffix != ".safetensors"
                },
                "max_prompt_tokens": max(a["prompt_tokens"] for a in audit),
                "sum_prompt_tokens": sum(a["prompt_tokens"] for a in audit),
                "capture_fp32_bytes": 496 * 8 * config.hidden_size * 4,
            }
            write(out / f"{key}_tokenization.json", audit)
            write(out / f"{key}_config.json", config_dict)
            baselines = baseline_report(rows, audit)
            write(out / f"{key}_baselines.json", baselines)
        except (OSError, ValueError, ImportError, RuntimeError, httpx.HTTPError) as e:
            state = {
                "status": "BLOCKED_METADATA_OR_TOKENIZER",
                "model_id": model,
                "error_type": type(e).__name__,
                "error": str(e)[:500],
            }
        states[key] = state
    import importlib.metadata

    versions = {
        k: importlib.metadata.version(k)
        for k in (
            "numpy",
            "scipy",
            "scikit-learn",
            "transformers",
            "torch",
            "tokenizers",
            "huggingface-hub",
        )
    }
    write(
        out / "manifest.json",
        {
            "version": "cross-model-four-strategy-v1",
            "status": "PREFLIGHT_ONLY_NO_INFERENCE",
            "integrity": integrity,
            "models": states,
            "depths": DEPTHS,
            "seed": SEED,
            "versions": versions,
            "code_hashes": code_hashes(),
            "files": {p.name: sha(p) for p in sorted(out.iterdir())},
        },
    )
    print(json.dumps(states, indent=2))
    return states


def conditional_fit(rows, features, y, groups, train, test, kind):
    """Inner-group fitting of vocabulary, scaling and regularization; no evaluation fitting."""
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    texts = np.array([r["action_text"] for r in rows], dtype=object)[:, None]
    data = np.concatenate([texts, features.astype(object)], axis=1)

    def make(c):
        transforms = []
        if kind.startswith("length"):
            transforms.append(
                (
                    "length",
                    Pipeline(
                        [
                            ("poly", PolynomialFeatures(2, include_bias=False)),
                            ("scale", StandardScaler()),
                        ]
                    ),
                    list(range(1, 5)),
                )
            )
        else:
            transforms.append(
                (
                    "lexical",
                    TfidfVectorizer(
                        ngram_range=(1, 2), max_features=2048, sublinear_tf=True
                    ),
                    0,
                )
            )
        if kind.endswith("_joint"):
            transforms.append(
                ("activation", StandardScaler(), list(range(5, data.shape[1])))
            )
        return Pipeline(
            [
                ("features", ColumnTransformer(transforms, sparse_threshold=1)),
                (
                    "classifier",
                    LogisticRegression(C=c, max_iter=1000, random_state=SEED),
                ),
            ]
        )

    scores = []
    for c in (0.01, 0.1, 1.0, 10.0):
        losses = []
        for a, b in GroupKFold(min(4, len(set(groups[train])))).split(
            data[train], y[train], groups[train]
        ):
            model = make(c).fit(data[train][a], y[train][a])
            loss = -np.log(
                np.maximum(
                    model.predict_proba(data[train][b])[np.arange(len(b)), y[train][b]],
                    1e-15,
                )
            )
            losses.append(
                np.mean(
                    [loss[groups[train][b] == g].mean() for g in set(groups[train][b])]
                )
            )
        scores.append(float(np.mean(losses)))
    c = (0.01, 0.1, 1.0, 10.0)[int(np.argmin(scores))]
    model = make(c).fit(data[train], y[train])
    probs = model.predict_proba(data[test])
    assert list(model.classes_) == [0, 1, 2, 3]
    return probs, {"C": c, "inner_family_macro_log_loss": scores}


def baseline_report(rows, audit):
    lookup = {r["prompt_id"]: r for r in audit}
    y = np.array([STRATEGIES.index(r["strategy"]) for r in rows])
    features = np.array(
        [
            [
                lookup[r["prompt_id"]]["action_tokens"],
                lookup[r["prompt_id"]]["prompt_tokens"],
                r["action_word_count"],
                r["action_char_count"],
            ]
            for r in rows
        ]
    )
    results = {}
    for split, field, group in [
        ("family", "split", "group_key"),
        ("domain", "domain_split", "domain"),
    ]:
        tr = np.array([r[field] == "discovery" for r in rows])
        te = ~tr
        groups = np.array([r[group] for r in rows])
        results[split] = {}
        for kind in ("length", "lexical"):
            probs, hp = conditional_fit(rows, features, y, groups, tr, te, kind)
            results[split][kind] = {
                "hyperparameters": hp,
                "per_cluster_accuracy": {
                    g: float(np.mean((probs.argmax(1) == y[te])[groups[te] == g]))
                    for g in sorted(set(groups[te]))
                },
            }
    return results


def verify_plan(plan):
    plan = Path(plan)
    m = read(plan / "manifest.json")
    if m["code_hashes"] != code_hashes():
        raise ValueError("Code changed since preparation")
    for name, value in m["files"].items():
        if Path(name).name != name or sha(plan / name) != value:
            raise ValueError(f"Plan hash mismatch: {name}")
    if (
        sha(plan / "prompts.jsonl") != m["integrity"]["inventory_bytes_sha256"]
        or sha(plan / "bank_snapshot.json") != m["integrity"]["bank_sha256"]
    ):
        raise ValueError("Stimulus inventory changed")
    return m


def capture(
    plan, key, output, authorize_inference=False, authorize_paid_run=False, smoke=False
):
    if not (authorize_inference and authorize_paid_run):
        raise PermissionError(
            "Both explicit inference and paid-run authorization required before loading weights"
        )
    plan, out = Path(plan), Path(output)
    m = verify_plan(plan)
    state = m["models"][key]
    if state["status"] != "TOKENIZER_PREFLIGHT_PASSED_WEIGHTS_UNTESTED":
        raise ValueError("Tokenizer preflight blocked")
    if out.exists():
        raise FileExistsError(out)
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(
        state["model_id"], revision=state["revision"], trust_remote_code=False
    )
    rows = [
        json.loads(line)
        for line in (plan / "prompts.jsonl").read_text(encoding="utf8").splitlines()
    ]
    audit = read(plan / f"{key}_tokenization.json")
    if smoke:
        # Fixed first complete scenario, not chosen using outcomes.
        rows, audit = rows[:4], audit[:4]
    for p, a in zip(rows, audit):
        if (
            tokenizer.encode(p["prompt_text"], add_special_tokens=True)
            != a["input_ids"]
            or p["prompt_id"] != a["prompt_id"]
        ):
            raise ValueError("Runtime tokenizer differs from plan")
    model = AutoModelForCausalLM.from_pretrained(
        state["model_id"],
        revision=state["revision"],
        torch_dtype=torch.float32,
        device_map="auto",
        trust_remote_code=False,
        attn_implementation="eager",
    )
    model.eval()
    layers = model.model.layers
    if (
        len(layers) != state["num_layers"]
        or model.config.hidden_size != state["hidden_size"]
    ):
        raise ValueError("Runtime architecture differs from preflight")
    out.mkdir(parents=True)
    (out / "activations").mkdir()
    write(out / "manifest.json", {"status": "running", "key": key, "smoke": smoke})
    timings = []
    for p, a in zip(rows, audit):
        started = time.perf_counter()
        arr = capture_vector(model, a["input_ids"], state["indices"])
        if arr.shape != (8, state["hidden_size"]) or not np.isfinite(arr).all():
            raise ValueError("Bad activation capture")
        np.savez_compressed(out / "activations" / f"{p['prompt_id']}.npz", residual=arr)
        timings.append(time.perf_counter() - started)
    shutil.copyfile(plan / "prompts.jsonl", out / "prompts.jsonl")
    hashes = {
        str(p.relative_to(out)).replace("\\", "/"): sha(p)
        for p in sorted((out / "activations").glob("*.npz"))
    }
    hashes["prompts.jsonl"] = sha(out / "prompts.jsonl")
    write(out / "evidence_hashes.json", hashes)
    write(
        out / "manifest.json",
        {
            "status": "completed",
            "mock": False,
            "key": key,
            "smoke": smoke,
            "dtype": "float32",
            "model": state,
            "plan_sha256": sha(plan / "manifest.json"),
            "indices": state["indices"],
            "evidence_sha256": sha(out / "evidence_hashes.json"),
            "seconds_per_prompt": timings,
            "torch_version": torch.__version__,
            "device": str(model.device),
        },
    )


def capture_vector(model, input_ids, indices):
    """Post-decoder-block final-token hooks shared by real capture and CPU API tests."""
    import torch

    cache = {}
    handles = []
    for idx in indices:

        def hook(module, args, result, index=idx):
            hidden = result[0] if isinstance(result, tuple) else result
            cache[index] = hidden[0, -1].detach().float().cpu().numpy()

        handles.append(model.model.layers[idx].register_forward_hook(hook))
    try:
        with torch.inference_mode():
            model.model(
                input_ids=torch.tensor([input_ids], device=model.device),
                use_cache=False,
            )
    finally:
        for h in handles:
            h.remove()
    return np.stack([cache[i] for i in indices])


def load_run(plan, run):
    plan, run = Path(plan), Path(run)
    m = verify_plan(plan)
    rm = read(run / "manifest.json")
    if (
        rm.get("status") != "completed"
        or rm.get("mock") is not False
        or rm.get("smoke")
        or rm.get("dtype") != "float32"
    ):
        raise ValueError(
            "Scientific analysis requires completed non-mock full FP32 run"
        )
    if (
        rm["plan_sha256"] != sha(plan / "manifest.json")
        or rm["model"] != m["models"][rm["key"]]
    ):
        raise ValueError("Run identity differs from plan")
    hashes = read(run / "evidence_hashes.json")
    if (
        sha(run / "evidence_hashes.json") != rm["evidence_sha256"]
        or (run / "prompts.jsonl").read_bytes() != (plan / "prompts.jsonl").read_bytes()
    ):
        raise ValueError("Evidence index or prompts differ")
    rows = [
        json.loads(line)
        for line in (plan / "prompts.jsonl").read_text(encoding="utf8").splitlines()
    ]
    expected = {"prompts.jsonl"} | {f"activations/{r['prompt_id']}.npz" for r in rows}
    if set(hashes) != expected or {
        p.name for p in (run / "activations").glob("*.npz")
    } != {f"{r['prompt_id']}.npz" for r in rows}:
        raise ValueError("Activation inventory mismatch")
    arrays = {}
    for name, value in hashes.items():
        if sha(run / name) != value:
            raise ValueError("Evidence hash mismatch")
        if name.startswith("activations/"):
            with np.load(run / name, allow_pickle=False) as f:
                arr = f["residual"]
            if (
                arr.shape != (8, rm["model"]["hidden_size"])
                or not np.isfinite(arr).all()
            ):
                raise ValueError("Invalid tensor")
            arrays[Path(name).stem] = arr.astype(float)
    return rm, rows, arrays


def import_qwen(plan, source_run, output):
    """Verify and subsample original saved Qwen evidence; zero model inference."""
    from .four_strategy_probe import load_dataset

    plan, source_run, out = Path(plan), Path(source_run), Path(output)
    m = verify_plan(plan)
    state = m["models"]["qwen"]
    if state["status"] != "TOKENIZER_PREFLIGHT_PASSED_WEIGHTS_UNTESTED" or out.exists():
        raise ValueError(
            "Ready tokenizer preflight and unused output directory required"
        )
    original, rows, arrays = load_dataset(
        source_run,
        source_run / "prompts.jsonl",
        expected_prompts_path=plan / "prompts.jsonl",
    )
    if original.get("dtype") != "float32":
        raise ValueError("Qwen precision differs; no implicit conversion accepted")
    if original["model_revision"] != state["revision"]:
        raise ValueError("Qwen revision differs")
    out.mkdir(parents=True)
    (out / "activations").mkdir()
    for p in rows:
        np.savez_compressed(
            out / "activations" / f"{p['prompt_id']}.npz",
            residual=arrays[p["prompt_id"]][state["indices"]].astype(np.float32),
        )
    shutil.copyfile(plan / "prompts.jsonl", out / "prompts.jsonl")
    hashes = {
        str(p.relative_to(out)).replace("\\", "/"): sha(p)
        for p in sorted((out / "activations").glob("*.npz"))
    }
    hashes["prompts.jsonl"] = sha(out / "prompts.jsonl")
    write(out / "evidence_hashes.json", hashes)
    write(
        out / "manifest.json",
        {
            "status": "completed",
            "mock": False,
            "smoke": False,
            "key": "qwen",
            "dtype": "float32",
            "model": state,
            "indices": state["indices"],
            "plan_sha256": sha(plan / "manifest.json"),
            "evidence_sha256": sha(out / "evidence_hashes.json"),
            "import_source_manifest_sha256": sha(source_run / "manifest.json"),
            "inference_performed": False,
        },
    )
    return {
        "imported_prompts": len(rows),
        "depth_indices": state["indices"],
        "inference_performed": False,
    }


def simultaneous_ci(values, alpha=0.0125 / 24, n_boot=10000):
    """Paired cluster bootstrap max-standardized-deviation band over every column.

    Alpha .0125/24 covers 3 models x 2 split schemes x 4 adjustment modes;
    all depths, strategies and metrics within a mode share one band.
    """
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or len(values) < 2:
        raise ValueError(
            "Undefined cluster statistic; report blocked rather than zero alignment"
        )
    means = values.mean(axis=0)
    se = values.std(axis=0, ddof=1) / np.sqrt(len(values))
    rng = np.random.default_rng(SEED)
    boot = values[rng.integers(0, len(values), size=(n_boot, len(values)))].mean(axis=1)
    z = np.abs(boot - means) / np.maximum(se, 1e-12)
    critical = float(np.quantile(z.max(axis=1), 1 - alpha))
    return {
        "mean": means.tolist(),
        "lower": (means - critical * se).tolist(),
        "upper": (means + critical * se).tolist(),
        "critical": critical,
        "alpha": alpha,
        "clusters": len(values),
        "bootstrap_draws": n_boot,
    }


def analyze(plan, run, output, n_boot=10000, permutations=100):
    from sklearn.linear_model import Ridge
    from sklearn.feature_extraction.text import TfidfVectorizer

    out = Path(output)
    if out.exists():
        raise FileExistsError(out)
    rm, rows, arrays = load_run(plan, run)
    sids, meta, x = scenario_center(rows, arrays)
    byid = {(r["scenario_id"], r["strategy"]): r for r in rows}
    ordered = [byid[(sid, st)] for sid in sids for st in STRATEGIES]
    audit = {
        r["prompt_id"]: r for r in read(Path(plan) / f"{rm['key']}_tokenization.json")
    }
    features = np.array(
        [
            [
                audit[r["prompt_id"]]["action_tokens"],
                audit[r["prompt_id"]]["prompt_tokens"],
                r["action_word_count"],
                r["action_char_count"],
            ]
            for r in ordered
        ],
        dtype=float,
    )
    nuisance = features.copy().reshape(len(sids), 4, 4)
    nuisance -= nuisance.mean(axis=1, keepdims=True)
    y = np.tile(np.arange(4), len(sids))
    report = {
        "model": rm["model"],
        "depths": DEPTHS,
        "splits": {},
        "run_sha256": sha(Path(run) / "manifest.json"),
        "plan_sha256": sha(Path(plan) / "manifest.json"),
        "code_hashes": code_hashes(),
        "behavioral_findings": None,
    }
    for split, field, groupfield in [
        ("family", "split", "group_key"),
        ("domain", "domain_split", "domain"),
    ]:
        tr = np.array([r[field] == "discovery" for r in meta])
        te = ~tr
        groups = np.array([r[groupfield] for r in meta])
        flatgroups = np.repeat(groups, 4)
        train, test = np.repeat(tr, 4), np.repeat(te, 4)
        clusters = sorted(set(groups[te]))
        # Exact legacy probe computations, including normalization and word/char adjustment.
        legacy = _layer_eval(
            x,
            tr,
            te,
            groups,
            nuisance[:, :, 2:],
            n_boot=n_boot,
            seed=SEED,
            permutations=permutations,
            label=split,
            progress=True,
        )
        text = np.array([r["action_text"] for r in ordered])
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), max_features=2048, sublinear_tf=True
        )
        vectorizer.fit(text[train])
        lexall = vectorizer.transform(text).toarray()
        inputs = {
            "word_char": nuisance[:, :, 2:].reshape(-1, 2),
            "token_length": nuisance.reshape(-1, 4),
            "lexical": np.concatenate([nuisance.reshape(-1, 4), lexall], axis=1),
        }
        baseline = {
            kind: conditional_fit(ordered, features, y, flatgroups, train, test, kind)
            for kind in ("length", "lexical")
        }
        matrices = {mode: [] for mode in MODES}
        column_names = {mode: [] for mode in MODES}
        layer_results = []
        raw_align = {}
        for li, depth in enumerate(DEPTHS):
            target = x[:, :, li].reshape(-1, x.shape[-1])
            variants = {"raw": target}
            for mode, inp in inputs.items():
                nuisance_model = Ridge(alpha=1.0, solver="lsqr").fit(
                    inp[train], target[train]
                )
                res = (target - nuisance_model.predict(inp)).reshape(len(sids), 4, -1)
                res -= res.mean(axis=1, keepdims=True)
                variants[mode] = res.reshape(-1, x.shape[-1])
            rawscale = np.sqrt(np.mean(np.sum(target[train] ** 2, axis=1)))
            layer_report = {
                "depth": depth,
                "block_index": rm["indices"][li],
                "variants": {},
                "conditional": {},
            }
            for mode, arr in variants.items():
                model, c, scores = _fit_probe(
                    arr[train], y[train], flatgroups[train], arr[test], y[test]
                )
                predictions = model.predict(arr[test])
                tensor = arr.reshape(len(sids), 4, -1)
                clsmean = np.mean(
                    [
                        tensor[(groups == g) & tr].mean(axis=0)
                        for g in sorted(set(groups[tr]))
                    ],
                    axis=0,
                )
                direction = clsmean - (clsmean.sum(axis=0, keepdims=True) - clsmean) / 3
                vals = [[] for g in clusters]
                metrics = ["accuracy"]
                for gi, g in enumerate(clusters):
                    vals[gi].append(
                        float(
                            np.mean(
                                (predictions == y[test])[np.repeat(groups[te], 4) == g]
                            )
                        )
                    )
                per_strategy = {}
                for si, st in enumerate(STRATEGIES):
                    v = direction[si]
                    norm = np.linalg.norm(v)
                    alignments, margins = [], []
                    for gi, g in enumerate(clusters):
                        local = tensor[groups == g].mean(axis=0)
                        d = local[si] - np.delete(local, si, axis=0).mean(axis=0)
                        dn = np.linalg.norm(d)
                        if norm <= 1e-12 or dn <= 1e-12:
                            raise ValueError(
                                f"Undefined direction for {split}/{mode}/{depth}/{st}/{g}; no zero substitution"
                            )
                        a = float(np.clip(d @ v / (dn * norm), -1, 1))
                        margin = float(d @ (v / norm))
                        alignments.append(a)
                        margins.append(margin)
                        attenuation = (
                            0.0 if mode == "raw" else raw_align[(li, st, g)] - a
                        )
                        if mode == "raw":
                            raw_align[(li, st, g)] = a
                        vals[gi].extend([a, margin / max(rawscale, 1e-12), attenuation])
                    metrics.extend(
                        [
                            f"{st}:alignment",
                            f"{st}:normalized_margin",
                            f"{st}:alignment_attenuation",
                        ]
                    )
                    per_strategy[st] = {
                        "direction": v.tolist(),
                        "alignment_by_cluster": dict(zip(clusters, alignments)),
                        "raw_unit_margin_by_cluster": dict(zip(clusters, margins)),
                    }
                for gi in range(len(clusters)):
                    if len(matrices[mode]) <= gi:
                        matrices[mode].append([])
                    matrices[mode][gi].extend(vals[gi])
                column_names[mode].extend([f"{depth}:{k}" for k in metrics])
                layer_report["variants"][mode] = {
                    "C": c,
                    "cv_accuracy": scores,
                    "directions": per_strategy,
                    "eval_predictions": predictions.tolist(),
                }
            for kind in ("length", "lexical"):
                joint_features = np.concatenate([features, target], axis=1)
                joint, hp = conditional_fit(
                    ordered, joint_features, y, flatgroups, train, test, kind + "_joint"
                )
                base = baseline[kind][0]
                gain = np.log2(
                    np.maximum(joint[np.arange(sum(test)), y[test]], 1e-15)
                    / np.maximum(base[np.arange(sum(test)), y[test]], 1e-15)
                )
                layer_report["conditional"][kind] = {
                    "hyperparameters": hp,
                    "gain_bits_by_cluster": {
                        g: float(gain[flatgroups[test] == g].mean()) for g in clusters
                    },
                }
            layer_results.append(layer_report)
        report["splits"][split] = {
            "legacy_probe_metrics": legacy,
            "layers": layer_results,
            "cluster_ids": clusters,
            "bands": {
                mode: {
                    "columns": column_names[mode],
                    "cluster_values": matrices[mode],
                    "simultaneous": simultaneous_ci(matrices[mode], n_boot=n_boot),
                }
                for mode in MODES
            },
            "conditional_bands": {
                kind: simultaneous_ci(
                    np.array(
                        [
                            [
                                layer_result["conditional"][kind][
                                    "gain_bits_by_cluster"
                                ][g]
                                for layer_result in layer_results
                            ]
                            for g in clusters
                        ]
                    ),
                    alpha=0.0125 / 12,
                    n_boot=n_boot,
                )
                for kind in ("length", "lexical")
            },
        }
    out.mkdir(parents=True)
    write(out / "replication_analysis.json", report)
    return report


def compare(paths, output):
    """Paired differences of scalar metrics, never cross-model vector cosines."""
    if not 2 <= len(paths) <= 3:
        raise ValueError("Compare two or three independently analyzed models")
    out = Path(output)
    if out.exists():
        raise FileExistsError(out)
    reports = [read(Path(p) / "replication_analysis.json") for p in paths]
    if len({r["model"]["model_id"] for r in reports}) != len(reports):
        raise ValueError("Duplicate model identity")
    if len({r["plan_sha256"] for r in reports}) != 1:
        raise ValueError("Different stimulus/preflight plans")
    result = []
    for i, a in enumerate(reports):
        for b in reports[i + 1 :]:
            if a["depths"] != b["depths"]:
                raise ValueError("Different depth grids")
            for split in ("family", "domain"):
                aa, bb = a["splits"][split], b["splits"][split]
                if aa["cluster_ids"] != bb["cluster_ids"]:
                    raise ValueError("Unpaired cluster inventories")
                for mode in MODES:
                    av, bv = aa["bands"][mode], bb["bands"][mode]
                    if av["columns"] != bv["columns"]:
                        raise ValueError("Metric columns differ")
                    values = np.asarray(av["cluster_values"]) - np.asarray(
                        bv["cluster_values"]
                    )
                    result.append(
                        {
                            "a": a["model"]["model_id"],
                            "b": b["model"]["model_id"],
                            "split": split,
                            "mode": mode,
                            "columns": av["columns"],
                            "paired_a_minus_b": simultaneous_ci(
                                values, alpha=0.025 / 24
                            ),
                        }
                    )
    out.mkdir(parents=True)
    write(
        out / "cross_model_comparison.json",
        {
            "comparisons": result,
            "input_analysis_hashes": [
                sha(Path(p) / "replication_analysis.json") for p in paths
            ],
            "interpretation": "Paired differences of dimensionless accuracy, alignment, normalized margin and attenuation; no common activation basis assumed.",
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("prepare")
    p.add_argument("--output", required=True)
    p.add_argument("--download-metadata", action="store_true")
    p = subs.add_parser("capture")
    p.add_argument("--plan", required=True)
    p.add_argument("--model", choices=MODELS, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--authorize-inference", action="store_true")
    p.add_argument("--authorize-paid-run", action="store_true")
    p.add_argument("--smoke", action="store_true")
    p = subs.add_parser("analyze")
    p.add_argument("--plan", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--output", required=True)
    p = subs.add_parser("compare")
    p.add_argument("--analyses", nargs="+", required=True)
    p.add_argument("--output", required=True)
    p = subs.add_parser("import-qwen")
    p.add_argument("--plan", required=True)
    p.add_argument("--source-run", required=True)
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.download_metadata)
    elif args.command == "capture":
        capture(
            args.plan,
            args.model,
            args.output,
            args.authorize_inference,
            args.authorize_paid_run,
            args.smoke,
        )
    elif args.command == "analyze":
        analyze(args.plan, args.run, args.output)
    elif args.command == "compare":
        compare(args.analyses, args.output)
    else:
        print(import_qwen(args.plan, args.source_run, args.output))


if __name__ == "__main__":
    main()
