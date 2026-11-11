"""Update manuscript-ready reports and comparative tables for cooperative rewording assay."""
import json
from pathlib import Path

READOUT_PATH = Path('reports/manuscript_readiness/cohort_statistical_readout.json')
OUT_DIR = Path('reports/manuscript_readiness')


def format_margin_cell(stratum_data: dict) -> str:
    if not stratum_data or not stratum_data.get('paired_presentations'):
        return 'no usable pairs'
    orig = stratum_data['original_margin'] * 100
    para = stratum_data['paraphrase_margin'] * 100
    lo, hi = [x * 100 for x in stratum_data['paraphrase_margin_95pct_ci']]
    delta = stratum_data['change_delta'] * 100
    n = stratum_data['paired_presentations']
    ex = stratum_data['excluded_pairs']
    return f"{orig:.1f}% → {para:.1f}% [{lo:.1f}%, {hi:.1f}%]; Δ {delta:+.1f}pp; N={n} ({ex} excl)"


def generate_markdown_report(data: dict) -> str:
    models = data['per_model_results']
    fam_agg = data['family_aggregates']

    lines = [
        "# Cooperative Wording Assay — Canonical Manuscript-Readiness Audit Dossier",
        "",
        "**Document Version:** Manuscript V0.1 Offline Audit & Diagnostic Dossier (11 Nov 2026)",
        "**Target Working Manuscript:** *Cooperative Strategy Selection in Pretrained Language Models: Cross-Family Evidence Under Utility Matching and Lexical Rewording*",
        "**Branch Reference:** `codex/dose-response-option-orders` (commit `42aaf61`)",
        "",
        "## 1. Executive Summary & Audit Status",
        "",
        f"- **Cohort Completion Status:** 14 of 14 expected checkpoints complete (12 base models across 8 distinct model families, 1 instruction-tuned model `Qwen/Qwen2.5-3B-Instruct`, and 1 exploratory fine-tuned checkpoint `founder-arcafutura/pythia-12b-exploratory-20261022`).",
        "- **Run Reconciliations:** 17 total run directories reconciled against `data/cooperate_rewording_model_manifest.json`. Three models had duplicate reruns (`google/gemma-2-9b`, `EleutherAI/pythia-12b-deduped`, and `Qwen/Qwen2.5-3B-Instruct`); byte-for-byte SHA-256 row matching confirmed 100% deterministic identical outputs. Canonical runs are transparently documented.",
        "- **Estimand:** Difference in forced-choice selection rates: $\\Delta = P(\\text{COOPERATE}) - P(\\text{INDEPENDENT})$.",
        "- **Uncertainty & Clustering:** 95% confidence intervals derived from $B=1,000$ template/triad-clustered bootstrap resamples (presentation-weighted cluster aggregations, seed 42). Option rotations (4), partner types (2), and wordings (2) are treated as repeated measurements, not independent observations.",
        "- **Instrument Failure Diagnostic:** Pythia 12B base and exploratory fine-tune exhibit severe format/instrument failure (~100% forced-choice A selection; flat 25% strategy rates mechanically induced by Latin-square rotation). These are confirmed instrument failures, not null or negative behavioral findings.",
        "",
        "---",
        "",
        "## 2. Primary Results: Equal-Utility Non-Symmetric Strata (Forced-Choice Argmax, No Ties)",
        "",
        "Percentages represent COOPERATE-minus-INDEPENDENT margins (percentage points). Brackets indicate 95% template/triad-clustered bootstrap confidence intervals for the rewritten wording. $\\Delta$ denotes rewritten minus original margin.",
        "",
        "| Model | Family | Architecture / Type | Phase 0B Equal-Utility (orig → rewrite [CI]; Δ; N) | Phase 1 Prospective Equal-Utility (orig → rewrite [CI]; Δ; N) |",
        "|---|---|---|---|---|"
    ]

    for m, d in sorted(models.items()):
        fam = d['family']
        m_type = "Instruction-Tuned" if "Instruct" in m else ("Exploratory SFT" if "exploratory" in m else "Pretrained Base")
        p0b = d['analysis']['banks']['phase0b']['strata']['non_control_equal_utility']['forced_no_ties']
        p1 = d['analysis']['banks']['phase1']['strata']['non_control_equal_utility']['forced_no_ties']
        lines.append(f"| `{m}` | {fam} | {m_type} | {format_margin_cell(p0b)} | {format_margin_cell(p1)} |")

    lines.extend([
        "",
        "> [!IMPORTANT]",
        "> **Methodological Boundary:** Margins reflect selection under a restricted 4-token forced-choice argmax instrument. They do not demonstrate human-like mental states, general intent, or causal weight-level mechanisms.",
        "",
        "---",
        "",
        "## 3. Exploratory Family-Aware Aggregation (Pretrained Base Checkpoints Only)",
        "",
        "To prevent pseudoreplication across multiple checkpoints within the same family (e.g. Qwen, OLMo, Gemma), checkpoint-level and family-level summaries are reported separately. Instruction-tuned and exploratory fine-tuned checkpoints are excluded from base family averages.",
        "",
        "### Phase 0B Equal-Utility (Non-Control)",
        "",
        "| Family | Base Checkpoints Evaluated | Mean Original Margin | Mean Rewritten Margin | Mean Change (Δ) |",
        "|---|---|---|---|---|"
    ])

    for fam, f_data in sorted(fam_agg['phase0b']['by_family'].items()):
        models_str = ", ".join(f"`{x.split('/')[-1]}`" for x in f_data['models'])
        lines.append(f"| **{fam}** | {models_str} ({f_data['models_count']}) | {f_data['mean_orig_margin']*100:+.1f}pp | {f_data['mean_para_margin']*100:+.1f}pp | {f_data['mean_delta']*100:+.1f}pp |")

    lines.extend([
        "",
        "### Phase 1 Prospective Equal-Utility (Non-Control)",
        "",
        "| Family | Base Checkpoints Evaluated | Mean Original Margin | Mean Rewritten Margin | Mean Change (Δ) |",
        "|---|---|---|---|---|"
    ])

    for fam, f_data in sorted(fam_agg['phase1']['by_family'].items()):
        models_str = ", ".join(f"`{x.split('/')[-1]}`" for x in f_data['models'])
        lines.append(f"| **{fam}** | {models_str} ({f_data['models_count']}) | {f_data['mean_orig_margin']*100:+.1f}pp | {f_data['mean_para_margin']*100:+.1f}pp | {f_data['mean_delta']*100:+.1f}pp |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Generated-Answer Audit & Parser Comparison",
        "",
        "The repository's strict parser required generated text to match exact single option tokens with no trailing characters. Models emitting explanations (e.g. `A\\n\\nExplanation:...` or `A. Disengage...`) were marked non-compliant. We implemented a transparent, post-hoc secondary initial-answer-letter extraction (from the first 5 generated tokens) with explicit categorization.",
        "",
        "| Model | Strict Valid (N/2432) | Recovered Initial Letter (N/2432) | Recovered Agreement with Forced Choice | Multi-Answer Sequences (`A, B, C`) | Unparseable / Empty | Contradictory Explanations |",
        "|---|---|---|---|---|---|---|"
    ])

    for m, d in sorted(models.items()):
        p_audit = d['analysis']['parser_audit']['overall']
        cats = p_audit['category_counts']
        strict_n = p_audit['strict_valid']
        rec_n = p_audit['recovered_valid']
        agr = p_audit['recovered_fc_agreement_rate'] * 100
        multi_n = cats.get('AMBIGUOUS_MULTI_ANSWER', 0)
        unp_n = cats.get('UNPARSEABLE', 0)
        contra_n = cats.get('CONTRADICTORY_EXPLANATION', 0)
        lines.append(f"| `{m}` | {strict_n} ({strict_n/24.32:.1f}%) | {rec_n} ({rec_n/24.32:.1f}%) | {agr:.1f}% | {multi_n} | {unp_n} | {contra_n} |")

    lines.extend([
        "",
        "> [!NOTE]",
        "> **DeepSeek Low Agreement Note:** DeepSeek LLM 7B Base demonstrates only 58.1% agreement between forced-choice argmax and recovered generated letter. Forced choice exhibits strong D bias (49.2%) whereas free generation exhibits strong A bias (61.7%). These channels must not be conflated.",
        "",
        "---",
        "",
        "## 5. Pythia Instrument Failure Diagnostic",
        "",
        "EleutherAI Pythia 12B Base and its exploratory fine-tune (`founder-arcafutura/pythia-12b-exploratory-20261022`) must be understood as an instrument failure rather than a negative result:",
        "- **Base Pythia 12B:** Selected option `A` in **2,425 of 2,432** presentations (99.71%). Mean conditional probability for letter A is 0.429 across presentations.",
        "- **Exploratory Fine-Tuned Pythia 12B:** Selected option `A` in **2,431 of 2,432** presentations (99.96%). Mean conditional probability for letter A is 0.536. In free generation, 2,372 presentations generated `A, B, C` sequence repetition.",
        "- **Mechanical Null:** Latin-square rotation mechanically yields ~25% per strategy when position bias is extreme (608 COOPERATE, 608 INDEPENDENT, 607 COMPETE, 609 DISENGAGE), resulting in an artificial $\\approx 0$ margin. This flat 25% must not be interpreted as evidence against latent cooperation.",
        "",
        "---",
        "",
        "## 6. Sensitivity Analysis: Tied Logit Handling",
        "",
        "Below is a comparison of COOPERATE-minus-INDEPENDENT margins when strictly excluding tied pairs vs retaining tied argmax selections (Phase 0B Equal-Utility):",
        "",
        "| Model | Tied Pairs Excluded Margin | All Pairs (Argmax Ties Retained) | Excluded Pair Count |",
        "|---|---|---|---|"
    ])

    for m, d in sorted(models.items()):
        p0b_no_ties = d['analysis']['banks']['phase0b']['strata']['non_control_equal_utility']['forced_no_ties']
        p0b_with_ties = d['analysis']['banks']['phase0b']['strata']['non_control_equal_utility']['forced_include_ties']
        m_no = f"{p0b_no_ties['paraphrase_margin']*100:.1f}%" if p0b_no_ties['paraphrase_margin'] is not None else "N/A"
        m_with = f"{p0b_with_ties['paraphrase_margin']*100:.1f}%" if p0b_with_ties['paraphrase_margin'] is not None else "N/A"
        ex = p0b_no_ties['excluded_pairs']
        lines.append(f"| `{m}` | {m_no} | {m_with} | {ex} pairs |")

    lines.extend([
        "",
        "---",
        "",
        "## 7. Semantic Validation Status & Blinding",
        "",
        "- **Provisional Status:** All Phase 1 results are exploratory / provisional because behavioral inference preceded independent human semantic adjudication.",
        "- **Adjudication Queue:** A blinded human adjudication queue of 304 items has been prepared (`reports/manuscript_readiness/blinded_human_adjudication_queue.csv`).",
        "- **Automated vs Human Adjudication:** Automated checks identify length parity warnings and template flags, but automated triage does not constitute independent human certification.",
        "",
        "---",
        "",
        "## 8. Calibration Reconciliation",
        "",
        "Predeclared calibration records from `data/calibration_bank.json`:",
        "- 10 of 14 models have completed historical calibration runs in `results/dose_response_batch/`.",
        "- 4 models have **missing calibration outputs** in repository records: `allenai/OLMo-2-0425-1B`, `EleutherAI/pythia-12b-deduped`, `Qwen/Qwen2.5-3B-Instruct`, and `founder-arcafutura/pythia-12b-exploratory-20261022`.",
        "- **Gate Compliance:** Passing models on both forced choice accuracy (≥40%) and format compliance (≥50% valid letters) are `Qwen 1.5B`, `Qwen 3B`, `Qwen 7B`, and `Llama 3.2 3B`. Models failing format compliance on elementary factual calibration are documented without retroactive relabeling.",
        ""
    ])

    return "\n".join(lines)


def main():
    if not READOUT_PATH.exists():
        raise FileNotFoundError(f"Missing {READOUT_PATH}. Run scripts/run_cohort_statistical_analysis.py first.")

    data = json.loads(READOUT_PATH.read_text(encoding='utf-8-sig'))
    md = generate_markdown_report(data)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / 'MANUSCRIPT_READINESS_REPORT.md'
    out_file.write_text(md + '\n', encoding='utf-8')
    print(f"Generated comprehensive report at {out_file}")

    # Also update research/cooperative_paraphrase_current_audit/PAIRED_RESULTS_PARTIAL.md
    compat_file = Path('research/cooperative_paraphrase_current_audit/PAIRED_RESULTS_PARTIAL.md')
    compat_file.write_text(md + '\n', encoding='utf-8')
    print(f"Updated {compat_file}")


if __name__ == '__main__':
    main()
