#!/usr/bin/env python3
"""
Deterministic Lexical Audit Script for Cooperative-Action Paraphrase Banks.

This script evaluates lexical overlap, token counts, and normalized similarity
across original and paraphrased COOPERATE options, compared against scenario stems
and INDEPENDENT option baselines.

Metrics:
1. Original COOPERATE content-word lexical overlap with scenario stem.
2. Paraphrased COOPERATE content-word lexical overlap with scenario stem.
3. Word and character token counts for original and paraphrase.
4. Normalized lexical similarity (Jaccard similarity of content words) between original and paraphrase.
5. INDEPENDENT alternative content-word lexical overlap with scenario stem (comparator baseline).

Content-Word Tokenization & Normalization:
- Lowercased tokens matching regex [a-zA-Z]+.
- Filtered using a standard English stopword list and minimum length > 1.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

STOPWORDS: Set[str] = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
    'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such',
    'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they',
    'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn', 'we',
    'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'you', 'your',
    'yours', 'yourself', 'yourselves'
}

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RESEARCH_DIR = ROOT_DIR / "research" / "cooperative_paraphrase_audit"

BANKS_INFO = [
    {
        "bank_key": "phase0",
        "source_file": DATA_DIR / "scenarios_v1_expanded.json",
        "paraphrase_file": DATA_DIR / "choice_set_cooperate_paraphrases_phase0.json",
        "expected_count": 120
    },
    {
        "bank_key": "phase0b",
        "source_file": DATA_DIR / "scenarios_phase0b_utility_matched.json",
        "paraphrase_file": DATA_DIR / "choice_set_cooperate_paraphrases_phase0b.json",
        "expected_count": 124
    },
    {
        "bank_key": "phase1",
        "source_file": DATA_DIR / "scenarios_phase1_prospective.json",
        "paraphrase_file": DATA_DIR / "choice_set_cooperate_paraphrases_phase1.json",
        "expected_count": 60
    }
]


def extract_content_words(text: str) -> Set[str]:
    """Tokenize text into content words (lowercased, non-stopwords, len > 1)."""
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return set(t for t in tokens if t not in STOPWORDS and len(t) > 1)


def word_count(text: str) -> int:
    """Return count of whitespace-delimited words."""
    return len(text.strip().split())


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def overlap_ratio(target_words: Set[str], reference_words: Set[str]) -> float:
    """Calculate proportion of target words found in reference words."""
    if not target_words:
        return 0.0
    return len(target_words & reference_words) / len(target_words)


def audit_item(scenario: dict, paraphrase_record: dict) -> dict:
    """Perform deterministic lexical audit on a single scenario and paraphrase record."""
    stem = scenario["stem"]
    orig_coop = scenario["options"]["COOPERATE"]
    para_coop = paraphrase_record["paraphrased_cooperate"]
    indep_opt = scenario["options"]["INDEPENDENT"]

    stem_cw = extract_content_words(stem)
    orig_cw = extract_content_words(orig_coop)
    para_cw = extract_content_words(para_coop)
    indep_cw = extract_content_words(indep_opt)

    orig_stem_overlap = overlap_ratio(orig_cw, stem_cw)
    para_stem_overlap = overlap_ratio(para_cw, stem_cw)
    indep_stem_overlap = overlap_ratio(indep_cw, stem_cw)

    overlap_reduction = orig_stem_overlap - para_stem_overlap
    orig_para_jaccard = jaccard_similarity(orig_cw, para_cw)

    orig_words = word_count(orig_coop)
    para_words = word_count(para_coop)
    word_diff = para_words - orig_words

    shared_orig_stem = sorted(list(orig_cw & stem_cw))
    shared_para_stem = sorted(list(para_cw & stem_cw))

    return {
        "bank": paraphrase_record["source_bank"],
        "scenario_id": scenario["id"],
        "template_id": scenario.get("template_id"),
        "partner_type": scenario.get("partner_type"),
        "context_type": scenario.get("context_type"),
        "domain": scenario.get("domain"),
        "split": scenario.get("split"),
        "utility_condition": scenario.get("utility_condition"),
        "triad_id": scenario.get("triad_id"),
        "is_symmetric_control": scenario.get("is_symmetric_control", False),
        "orig_coop_text": orig_coop,
        "para_coop_text": para_coop,
        "indep_text": indep_opt,
        "orig_word_count": orig_words,
        "para_word_count": para_words,
        "word_count_diff": word_diff,
        "orig_char_count": len(orig_coop),
        "para_char_count": len(para_coop),
        "char_count_diff": len(para_coop) - len(orig_coop),
        "orig_stem_overlap": round(orig_stem_overlap, 4),
        "para_stem_overlap": round(para_stem_overlap, 4),
        "overlap_reduction": round(overlap_reduction, 4),
        "indep_stem_overlap": round(indep_stem_overlap, 4),
        "orig_para_jaccard": round(orig_para_jaccard, 4),
        "shared_stem_words_orig": " ".join(shared_orig_stem),
        "shared_stem_words_para": " ".join(shared_para_stem),
        "flag_for_review": paraphrase_record.get("flag_for_review", False),
        "authoring_rationale": paraphrase_record.get("authoring_rationale", "")
    }


def compute_aggregates(rows: List[dict], group_key: str) -> Dict[str, dict]:
    """Compute mean metrics grouped by a specified categorical attribute."""
    groups = defaultdict(list)
    for r in rows:
        val = str(r.get(group_key))
        groups[val].append(r)

    aggregates = {}
    for val, items in sorted(groups.items()):
        n = len(items)
        avg_orig_stem = sum(i["orig_stem_overlap"] for i in items) / n
        avg_para_stem = sum(i["para_stem_overlap"] for i in items) / n
        avg_reduction = sum(i["overlap_reduction"] for i in items) / n
        avg_indep_stem = sum(i["indep_stem_overlap"] for i in items) / n
        avg_jaccard = sum(i["orig_para_jaccard"] for i in items) / n
        avg_orig_words = sum(i["orig_word_count"] for i in items) / n
        avg_para_words = sum(i["para_word_count"] for i in items) / n
        avg_word_diff = sum(i["word_count_diff"] for i in items) / n

        aggregates[val] = {
            "count": n,
            "mean_orig_stem_overlap": round(avg_orig_stem, 4),
            "mean_para_stem_overlap": round(avg_para_stem, 4),
            "mean_overlap_reduction": round(avg_reduction, 4),
            "mean_indep_stem_overlap": round(avg_indep_stem, 4),
            "mean_orig_para_jaccard": round(avg_jaccard, 4),
            "mean_orig_words": round(avg_orig_words, 2),
            "mean_para_words": round(avg_para_words, 2),
            "mean_word_diff": round(avg_word_diff, 2)
        }
    return aggregates


def run_audit() -> Tuple[List[dict], dict]:
    """Run full deterministic audit across all three banks."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for info in BANKS_INFO:
        src_data = json.loads(info["source_file"].read_text(encoding="utf-8-sig"))
        para_data = json.loads(info["paraphrase_file"].read_text(encoding="utf-8"))

        src_map = {s["id"]: s for s in src_data["scenarios"]}
        para_list = para_data["paraphrases"]

        assert len(para_list) == info["expected_count"], (
            f"Expected {info['expected_count']} records for {info['bank_key']}, got {len(para_list)}"
        )

        for p_rec in para_list:
            sid = p_rec["scenario_id"]
            scenario = src_map[sid]
            audit_res = audit_item(scenario, p_rec)
            all_rows.append(audit_res)

    assert len(all_rows) == 304, f"Expected 304 total audited items, got {len(all_rows)}"

    # Save item-level CSV
    csv_path = RESEARCH_DIR / "lexical_audit_items.csv"
    fieldnames = list(all_rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # Compute group summaries
    summary = {
        "total_items": len(all_rows),
        "by_bank": compute_aggregates(all_rows, "bank"),
        "by_partner_type": compute_aggregates(all_rows, "partner_type"),
        "by_context_type": compute_aggregates(all_rows, "context_type"),
        "by_utility_condition": compute_aggregates(all_rows, "utility_condition"),
        "by_split": compute_aggregates(all_rows, "split"),
    }

    summary_path = RESEARCH_DIR / "lexical_audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    return all_rows, summary


if __name__ == "__main__":
    rows, summary = run_audit()
    print("=" * 60)
    print(f"AUDIT COMPLETE: Audited {len(rows)} items across 3 banks.")
    print("=" * 60)
    print("Summary by Bank:")
    for bank, s in summary["by_bank"].items():
        print(f"  [{bank.upper()}] (N={s['count']}):")
        print(f"    Orig COOP Stem Overlap: {s['mean_orig_stem_overlap']:.3f}")
        print(f"    Para COOP Stem Overlap: {s['mean_para_stem_overlap']:.3f} (Reduction: {s['mean_overlap_reduction']:.3f})")
        print(f"    Indep Stem Overlap:     {s['mean_indep_stem_overlap']:.3f}")
        print(f"    Orig/Para Jaccard:      {s['mean_orig_para_jaccard']:.3f}")
        print(f"    Word Count: Orig {s['mean_orig_words']:.1f} -> Para {s['mean_para_words']:.1f} (Diff: {s['mean_word_diff']:+.1f})")
    print("=" * 60)
    print(f"Output files written to {RESEARCH_DIR}")
