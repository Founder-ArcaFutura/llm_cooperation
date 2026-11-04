#!/usr/bin/env python3
"""Collect, validate, analyze, and optionally push Phase 1 PROVISIONAL results.

Run in the root of Founder-ArcaFutura/llm_cooperation:
    python collect_phase1_provisional.py

Does not run inference, modify the scenario bank, approve a freeze, or evaluate
models. Safe to rerun as Modal jobs finish. Auto-commits/pushes only this collector,
verified Phase 1 run files, semantic-audit output, and derived reports.

Options:
    --no-push    Download/analyze only; no git commit/push.
    --no-audit   Skip downloading the completed Qwen-32B instrument review.
    --no-compare Skip running the cross-model comparison.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_BANK_SHA = "5994103be281863e336fbad2d325b99a9d235c982ef7bc0f00d512f713e8886f"
RESEARCH_STATUS = "phase1_provisional_exploratory_not_human_adjudicated"
VOLUME = "llm-coop-results"
AUDIT_VOLUME = "llm-coop-phase1-instrument-audits"
AUDIT_RUN = "phase1_4f9ae253471a_qwen25-32bi_phase1_blind_item_v1_pair_v1"
FIRST_VALID_TIMESTAMP = "20261104225000"  # UTC, before first Phase 1 real-model run
# Fallbacks from completed Modal logs; discover all other files from the live volume.
KNOWN_COMPLETED = [
    "run_Qwen_Qwen2.5-3B_20261104_225437_9d3a9b99.jsonl",
    "run_meta-llama_Llama-3.2-3B_20261104_230738_d5b4b36e.jsonl",
    "run_google_gemma-2-2b_20261104_230841_3f8b9410.jsonl",
]
FILENAME_RE = re.compile(r"run_[A-Za-z0-9_.-]+_(\d{8})_(\d{6})_[a-fA-F0-9]{8}\.jsonl")


def command(argv: list[str], *, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    if not quiet:
        print("$", " ".join(argv), flush=True)
    result = subprocess.run(argv, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if not quiet or result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0 and check:
        raise RuntimeError(f"Command failed (exit {result.returncode}): {' '.join(argv)}")
    return result


def frac(rows: list[dict], strategy: str = "COOPERATE") -> float:
    if not rows:
        return 0.0
    return sum(r.get("forced_choice_argmax_strategy") == strategy for r in rows) / len(rows) * 100


def summarize(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        header = json.loads(next(fh))
        rows = [json.loads(line) for line in fh if line.strip()]
    if header.get("research_status") != RESEARCH_STATUS:
        raise ValueError(f"Not a Phase 1 provisional output: {path.name}")
    if header.get("scenario_bank_hash") != EXPECTED_BANK_SHA:
        raise ValueError(f"Bank fingerprint mismatch: {path.name}: {header.get('scenario_bank_hash')}")
    if header.get("mock") is not False:
        raise ValueError(f"Mock result excluded: {path.name}")
    if header.get("num_presentations") != 240 or len(rows) != 240:
        raise ValueError(f"Expected exactly 240 presentations: {path.name}; found {len(rows)}")
    if header.get("run_id") != path.stem:
        raise ValueError(f"Run identifier mismatch in {path.name}")
    eq = [r for r in rows if not r.get("is_symmetric_control")]
    sym = [r for r in rows if r.get("is_symmetric_control")]
    hum = [r for r in rows if r.get("partner_type") == "human"]
    ai = [r for r in rows if r.get("partner_type") == "ai"]
    if (len(eq), len(sym), len(hum), len(ai)) != (192, 48, 120, 120):
        raise ValueError(f"Unexpected Phase 1 strata in {path.name}")
    letters = [sum(r.get("forced_choice_argmax_letter") == letter for r in rows) for letter in "ABCD"]
    return {
        "model_name": header["model_name"],
        "run_id": header["run_id"],
        "num_presentations": len(rows),
        "cooperate_count": sum(r.get("forced_choice_argmax_strategy") == "COOPERATE" for r in rows),
        "cooperate_pct": round(frac(rows), 3),
        "independent_pct": round(frac(rows, "INDEPENDENT"), 3),
        "equal_utility_cooperate_pct": round(frac(eq), 3),
        "equal_utility_independent_pct": round(frac(eq, "INDEPENDENT"), 3),
        "equal_utility_choice_margin_pp": round(frac(eq) - frac(eq, "INDEPENDENT"), 3),
        "symmetric_control_cooperate_pct": round(frac(sym), 3),
        "symmetric_control_independent_pct": round(frac(sym, "INDEPENDENT"), 3),
        "human_partner_cooperate_pct": round(frac(hum), 3),
        "ai_partner_cooperate_pct": round(frac(ai), 3),
        "valid_letter_pct": round(sum(r.get("is_valid_letter") is True for r in rows) / len(rows) * 100, 3),
        "position_spread_pp": round((max(letters) - min(letters)) / len(rows) * 100, 3),
        "bank_sha256": header["scenario_bank_hash"],
        "research_status": header["research_status"],
    }


def normalize(path: Path) -> str:
    return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--no-compare", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if not (root / "modal_app.py").is_file() or not (root / "data/scenarios_phase1_prospective.json").is_file():
        print("ERROR: Save this file at G:\\llm_cooperation beside modal_app.py", file=sys.stderr)
        return 2
    for program in ("modal", "llm-coop", "git"):
        if not shutil.which(program):
            print(f"ERROR: {program} is not available on PATH", file=sys.stderr)
            return 2
    import os
    os.chdir(root)
    branch = command(["git", "branch", "--show-current"], quiet=True).stdout.strip()
    if branch != "phase_1":
        print(f"ERROR: Refusing Git automation on branch {branch!r}; expected 'phase_1'", file=sys.stderr)
        return 2
    canonical = (root / "data/scenarios_phase1_prospective.json").read_bytes().replace(b"\r\n", b"\n")
    sha = hashlib.sha256(canonical).hexdigest()
    if sha != EXPECTED_BANK_SHA:
        print(f"ERROR: Local scenario bank differs from the pinned research corpus: {sha}", file=sys.stderr)
        return 2
    print(f"[PROVENANCE] Phase 1 canonical SHA-256: {sha}")

    staged_before = command(["git", "diff", "--cached", "--name-only"], quiet=True).stdout.strip()
    if staged_before and not args.no_push:
        print("[WARNING] Other staged files already exist. Collector will analyze, but NOT commit/push automatically.")
        args.no_push = True

    raw = command(["modal", "volume", "ls", "--json", VOLUME], check=False)
    listing = raw.stdout
    if raw.returncode:
        print("[WARNING] Could not list Modal volume; using filenames from completed run logs only.")
    candidates = set(KNOWN_COMPLETED)
    for match in FILENAME_RE.finditer(listing):
        if match.group(1) + match.group(2) >= FIRST_VALID_TIMESTAMP:
            candidates.add(match.group(0))
    print(f"[DISCOVERY] {len(candidates)} candidate files; only valid Phase 1 real-model records will be analyzed")

    result_dir = root / "results"
    report_root = root / "reports/phase1_provisional"
    result_dir.mkdir(exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    verified: list[tuple[Path, dict]] = []
    staged: list[str] = []
    for filename in sorted(candidates):
        target = result_dir / filename
        if not target.is_file():
            got = command(["modal", "volume", "get", VOLUME, filename, normalize(target)], check=False)
            if got.returncode != 0:
                print(f"[SKIP] Not yet downloadable (perhaps still running): {filename}")
                continue
        try:
            row = summarize(target)
        except (ValueError, UnicodeError, StopIteration, json.JSONDecodeError) as err:
            print(f"[SKIP] {filename}: {err}")
            continue
        print(f"[VERIFIED] {row['model_name']}: {row['cooperate_pct']:.1f}% cooperation, "
              f"equal-utility margin {row['equal_utility_choice_margin_pp']:+.1f} pp")
        verified.append((target, row))
        staged.append(normalize(target.relative_to(root)))
        output_dir = report_root / row["run_id"]
        output_dir.mkdir(parents=True, exist_ok=True)
        if not list(output_dir.glob("*.md")):
            analyzed = command(["llm-coop", "analyze", normalize(target), "-o", normalize(output_dir)], check=False)
            if analyzed.returncode:
                print(f"[WARNING] Analysis failed for {row['model_name']}; raw data remains preserved")
        staged.append(normalize(output_dir.relative_to(root)))
    if not verified:
        print("[NO RESULTS] No matching completed Phase 1 provisional models found; nothing to commit.")
        return 1

    rows = [row for _, row in verified]
    rows.sort(key=lambda x: (x["model_name"], x["run_id"]))
    csv_path = report_root / "cohort_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    readme = report_root / "README.md"
    readme.write_text(
        "# Phase 1 provisional observational results\n\n"
        "These are **pre-human-semantic-adjudication exploratory observations**, not a "
        "completed prospective confirmatory replication. Each checked run records its original "
        "bank SHA-256 and the explicit provisional research status.\n\n"
        "The legacy `llm-coop analyze` utility labels some outputs `Phase 0`, `Phase 0B`, "
        "`confirmatory`, or `FORMAL REPLICATION TEST` based on scenario metadata; **these "
        "legacy labels do not upgrade the scientific status of this dataset**.\n\n"
        "The cohort_summary.csv rates are descriptive presentation-level proportions; "
        "repeated Latin-square presentations of the same scenario are not independent "
        "samples. Consult scenario/template-clustered analysis and protocol for inference.\n\n"
        "Scenario bank SHA-256 (canonical LF bytes): `" + EXPECTED_BANK_SHA + "`\n",
        encoding="utf-8",
    )
    staged += [normalize(csv_path.relative_to(root)), normalize(readme.relative_to(root))]

    if len(verified) >= 2 and not args.no_compare:
        compare_dir = report_root / "comparison"
        compare_dir.mkdir(parents=True, exist_ok=True)
        compared = command(
            ["llm-coop", "compare-models", *[normalize(p) for p, _ in verified], "-o", normalize(compare_dir)],
            check=False,
        )
        if compared.returncode:
            print("[WARNING] Cross-model comparison failed. Individual reports and summary are still preserved.")
        else:
            staged.append(normalize(compare_dir.relative_to(root)))

    if not args.no_audit:
        audit_dir = root / "audit_download" / AUDIT_RUN
        audit_dir.parent.mkdir(parents=True, exist_ok=True)
        if not (audit_dir / "audit_summary.md").is_file():
            downloaded = command(
                ["modal", "volume", "get", AUDIT_VOLUME, AUDIT_RUN + "/", normalize(audit_dir)],
                check=False,
            )
            if downloaded.returncode:
                print("[WARNING] Qwen-32B instrument audit could not be downloaded; continuing without it")
        if audit_dir.exists() and any(audit_dir.rglob("*.jsonl")):
            staged.append(normalize(audit_dir.relative_to(root)))
            print("[INSTRUMENT AUDIT] Downloaded Qwen-32B item and pair reviews")

    print("\n========== PHASE 1 PROVISIONAL COHORT ==========")
    for row in rows:
        print(f"{row['model_name']:<39} coop={row['cooperate_pct']:>5.1f}%   "
              f"equal-margin={row['equal_utility_choice_margin_pp']:>+6.1f} pp   "
              f"symmetric={row['symmetric_control_cooperate_pct']:>5.1f}%")
    print(f"Summary: {csv_path}")

    if args.no_push:
        print("[FINISHED] Files downloaded and analyzed. Git push skipped.")
        return 0
    # Stage ONLY collected research material and the collector itself.
    if root / "collect_phase1_provisional.py" == Path(__file__).resolve():
        staged.append("collect_phase1_provisional.py")
    for rel in sorted(set(staged)):
        command(["git", "add", "-f", "--", rel])
    delta = command(["git", "diff", "--cached", "--name-only"], quiet=True).stdout.strip()
    if not delta:
        print("[FINISHED] All findings already committed; nothing to push.")
        return 0
    command(["git", "diff", "--cached", "--stat"])
    command(["git", "commit", "-m", f"Archive Phase 1 provisional runs and audits ({len(rows)} models)"])
    command(["git", "push", "origin", "phase_1"])
    print("[SUCCESS] Results, reports and audit evidence archived to GitHub phase_1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
