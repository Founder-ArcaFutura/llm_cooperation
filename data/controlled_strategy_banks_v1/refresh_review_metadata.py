"""Refresh provisional review and integrity records; never adjudicate semantics."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
old_queue = json.loads((root / "human_review_queue.json").read_text(encoding="utf-8"))
if any(item.get("semantic_status", "unadjudicated") != "unadjudicated" for item in old_queue):
    raise RuntimeError("Refusing to overwrite adjudication records")
old = {(item["bank"], item["scenario_id"]): item for item in old_queue}
queue = []
for bank, path in manifest["banks"].items():
    corpus = json.loads((root / Path(path).name).read_text(encoding="utf-8"))
    for scenario in corpus["scenarios"]:
        item = old.get((bank, scenario["id"]), {})
        queue.append({
            "scenario_id": scenario["id"], "bank": bank,
            "semantic_status": "unadjudicated",
            "reason": "Independent review of equivalence, fluency, payoff and partner meaning required",
            "heuristic_issues": item.get("heuristic_issues", item.get("issues", [])),
            "original_options": scenario["original_options"],
            "options": scenario["options"],
        })
(root / "human_review_queue.json").write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
names = [Path(path).name for path in (*manifest["banks"].values(), *manifest["prompts"].values())]
names += ["human_review_queue.json", "audit_report.md", "acceptance_report.md", "EXPERIMENTAL_PROTOCOL.md"]
hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
(root / "hashes.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
manifest["status"] = "provisional_not_accepted"
manifest["file_hashes"] = hashes
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
