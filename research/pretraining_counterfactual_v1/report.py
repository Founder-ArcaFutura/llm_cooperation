"""Offline paired-arm learning curves; never loads a model or contacts a provider."""
import argparse
import json
from pathlib import Path

from .data import CONDITIONS, digest, write_json


def paired_identity(identity):
    return {k: v for k, v in identity.items() if k not in ("condition", "strength")}


def report(runs, output):
    roots = list(map(Path, runs))
    manifests = [json.loads((root / "run.json").read_text()) for root in roots]
    conditions = [m["identity"]["condition"] for m in manifests]
    if len(roots) != 3 or set(conditions) != set(CONDITIONS):
        raise ValueError("Provide exactly one run per condition, for one paired seed")
    if len({digest(paired_identity(m["identity"])) for m in manifests}) != 1:
        raise ValueError("Arms differ beyond condition/strength (initialization, budget, optimizer, data, environment or seed)")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    summaries = []
    for root, manifest in zip(roots, manifests):
        condition = manifest["identity"]["condition"]
        for ax, filename, label in zip(axes, ("train.jsonl", "validation.jsonl"),
                                       ("Training loss", "Fixed validation loss")):
            path = root / filename
            rows = [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []
            if rows:
                ax.plot([r["tokens"] for r in rows], [r["loss"] for r in rows], label=condition)
            ax.set(xlabel="Consumed prediction tokens", ylabel=label)
        summaries.append({"run": str(root), "condition": condition,
                          "summary": json.loads((root / "summary.json").read_text())})
    for ax in axes:
        ax.legend()
    fig.tight_layout(); fig.savefig(output / "learning_curves.png"); plt.close(fig)
    write_json(output / "paired_runs.json", {"seed": manifests[0]["identity"]["seed"],
               "paired_identity": paired_identity(manifests[0]["identity"]), "runs": summaries,
               "caution": "Descriptive curves. Compare CPI checkpoints at matched tokens and retain calibration failures; one seed is not replication."})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", nargs=3, required=True); p.add_argument("--output", required=True)
    a = p.parse_args(); report(a.runs, a.output)
