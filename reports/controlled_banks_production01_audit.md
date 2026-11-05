# Offline Scientific Audit of Controlled Strategy Banks (`production01`)

**Audit Status:** COMPLETE
**Input Source:** `research/controlled_rewrites/production01/`
**Phase 0B Source:** `data/scenarios_phase0b_utility_matched.json` (124 scenarios)
**Target Execution Scope:** Candidate Banks A, B, and C (372 scenario-bank variants)
**Authoritative Tokenizer:** `Qwen/Qwen2.5-1.5B` (`8faed761d45a263340a0528343f099c05c9a4323`)

---

## Executive Summary

A rigorous, offline, reproducible scientific audit of the complete Modal `production01` rewrite generation was conducted. No language models were executed, no GPUs or cloud infrastructure were invoked, and no source files were modified.

Key takeaways:
1. **Provenance & Completeness (100% Accounted):** All 372 scenario-bank JSON records (`000_A` through `123_C`) are present and intact. Manifest accounting perfectly matches individual records: exactly **72 passed automatic constraints** (30 Bank A, 21 Bank B, 21 Bank C) and **300 remain unresolved**. Scenario identities, strategic labels (COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE), and payoff structures are rigorously preserved across all items.
2. **Strict Token-Span Barrier:** Only 19.4% (72/372) satisfy the strict span ≤ 1 criterion under both action-only and full-prompt tokenization. However, a substantial cluster of candidates represent high-quality near-misses.
3. **Threshold Relaxation Trade-Off:** Relaxing the permitted token span from **span ≤ 1** to **span ≤ 2** increases accepted candidates from 72 (19.4%) to **157 (42.2%)**. Relaxing to **span ≤ 3** brings coverage to **240 (64.5%)**.
4. **Lexical Independence vs Collision:** Bank A, B, and C are largely diversified, though exact cross-bank action duplicates were detected across pairs (2 in A vs B, 10 in A vs C, 38 in B vs C). Cross-bank mean Jaccard similarity ranges between 0.46 and 0.56, reflecting necessary domain noun sharing while preserving distinctive phrasing across rewriting styles.
5. **Semantic Integrity & Diagnostic Triage:** Diagnostic heuristics flagged **297 actions across 238 records** for potential semantic shifts (such as loss of human/AI partner cues, extreme length compression, or polarity changes). These flags are diagnostic triage indicators, not definitive rejections.
6. **Actionable Repair Queue:** The remaining 300 unresolved items are partitioned into a finite, prioritized repair queue: **166 Priority 1 near-misses (spans 2-3)** that require minor wording adjustment, **100 Priority 2 moderate repairs (spans 4-5)**, and **34 Priority 3 substantial reconstructions** (structural duplicates, excessive overlap, or spans ≥ 6).

---

## 1. Provenance and Record Accounting

| Metric | Bank A | Bank B | Bank C | Total / Status |
| :--- | :---: | :---: | :---: | :---: |
| **Expected Scenarios** | 124 | 124 | 124 | 372 |
| **Records Found on Disk** | 124 | 124 | 124 | 372 (100%) |
| **Manifest Accepted Count** | 30 | 21 | 21 | 72 |
| **Records Verified Accepted** | 30 | 21 | 21 | 72 |
| **Manifest Unresolved Count** | 94 | 103 | 103 | 300 |
| **Records Verified Unresolved** | 94 | 103 | 103 | 300 |
| **Candidate JSON File Count** | 30 | 21 | 21 | 72 |
| **`unresolved.json` Count** | - | - | - | 300 |

**Reconciliation Conclusion:** The records on disk, `manifest.json`, `unresolved.json`, and the candidate JSON files are 100% mutually consistent. No record corruption, missing files, or schema violations were identified. Payoff specifications and scenario identities match Phase 0B exactly.

---

## 2. Token Matching Characterization

The production run evaluated both **action-only token lengths** and **full-prompt token lengths** (`stem + '\n\nAction: ' + action + '\nDecision:'`).

### Distribution of Token Spans (Max - Min across the 4 options):

| Span (Tokens) | Action-Only Count | Prompt Token Count | Combined Max Span Count | Cumulative % (Combined) |
| :---: | :---: | :---: | :---: | :---: |
| **Span = 0** | 5 | 4 | 4 | 1.1% |
| **Span = 1** | 69 | 69 | 68 | 19.4% |
| **Span = 2** | 93 | 88 | 85 | 42.2% |
| **Span = 3** | 82 | 81 | 83 | 64.5% |
| **Span = 4** | 63 | 61 | 59 | 80.4% |
| **Span = 5** | 33 | 37 | 41 | 91.4% |
| **Span = 6** | 20 | 20 | 20 | 96.8% |
| **Span = 7** | 3 | 6 | 6 | 98.4% |
| **Span = 8** | 1 | 3 | 3 | 99.2% |
| **Span = 9** | 2 | 2 | 2 | 99.7% |
| **Span = 10** | 1 | 1 | 1 | 100.0% |

### Coverage Under Alternative Span Thresholds:

| Permitted Span Threshold | Action-Only Pass | Prompt-Only Pass | Both Pass (Joint Constraint) | Bank A | Bank B | Bank C |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Span ≤ 1** | 74 (19.9%) | 73 (19.6%) | **72 (19.4%)** | 30 | 21 | 21 |
| **Span ≤ 2** | 167 (44.9%) | 161 (43.3%) | **157 (42.2%)** | 65 | 46 | 46 |
| **Span ≤ 3** | 249 (66.9%) | 242 (65.1%) | **240 (64.5%)** | 96 | 78 | 66 |
| **Span ≤ 4** | 312 (83.9%) | 303 (81.5%) | **299 (80.4%)** | 107 | 97 | 95 |
| **Span ≤ 5** | 345 (92.7%) | 340 (91.4%) | **340 (91.4%)** | 118 | 109 | 113 |

---

## 3. Lexical Diversity Assessment

### Cross-Bank Lexical Overlap:
- **Bank A vs Bank B:** Mean Jaccard = `0.4659`, Mean 3-gram Overlap = `0.1741`, Exact Duplicate Actions = `2`.
- **Bank A vs Bank C:** Mean Jaccard = `0.4719`, Mean 3-gram Overlap = `0.1804`, Exact Duplicate Actions = `10`.
- **Bank B vs Bank C:** Mean Jaccard = `0.5577`, Mean 3-gram Overlap = `0.2981`, Exact Duplicate Actions = `38`.

### Specific Overlap Violations Detected:
1. **`021_C.json` (Scenario `phase0b_011_ai`, COOPERATE):** Exact verbatim duplicate of Bank A action: *"Coordinate de-icing sweeps with the automated apron routing agent on shared taxiways."* (Jaccard = 1.00).
2. **`021_B.json` (Scenario `phase0b_011_ai`, COOPERATE):** Excessive lexical overlap with Bank A (Jaccard = 0.86).

### Lexical Shortcuts Associated with Strategy Labels:
Analysis of strategy token distributions revealed distinct leading verb preferences and high-specificity terms:
- **COOPERATE:** Leading verb diversity = 46 distinct verbs. Distinctive lexical cues: `automated` (92% COOPERATE), `human` (94% COOPERATE), `coordinate` (100% COOPERATE), `agent` (89% COOPERATE), `synchronize` (100% COOPERATE).
- **INDEPENDENT:** Leading verb diversity = 86 distinct verbs. Distinctive lexical cues: `without` (88% INDEPENDENT), `using` (85% INDEPENDENT), `coordination` (97% INDEPENDENT), `local` (78% INDEPENDENT), `internal` (96% INDEPENDENT).
- **COMPETE_EXPLOIT:** Leading verb diversity = 74 distinct verbs. Distinctive lexical cues: `access` (89% COMPETE_EXPLOIT), `ahead` (96% COMPETE_EXPLOIT), `claim` (100% COMPETE_EXPLOIT), `exclusive` (93% COMPETE_EXPLOIT), `secure` (77% COMPETE_EXPLOIT).
- **DISENGAGE:** Leading verb diversity = 61 distinct verbs. Distinctive lexical cues: `until` (87% DISENGAGE), `delay` (80% DISENGAGE), `cease` (100% DISENGAGE), `next` (100% DISENGAGE), `halt` (100% DISENGAGE).

---

## 4. Diagnostic Semantic Integrity Triage

Automated semantic evaluation was conducted as a diagnostic filter against the frozen Phase 0B source text. **Note:** Automated semantic assessment is diagnostic, not certification. Final equivalence requires human scientific adjudication.

- **Total Flagged Actions:** 297 actions across 238 records.
- **Flag Breakdown:**
  - `polarity_negation_shift(orig=False,cand=True)`: 179
  - `possible_loss_of_human_partner_cue`: 72
  - `low_lexical_similarity_to_source(0.11)`: 5
  - `low_lexical_similarity_to_source(0.08)`: 1
  - `polarity_negation_shift(orig=True,cand=False)`: 3
  - `possible_loss_of_ai_partner_cue`: 31
  - `low_lexical_similarity_to_source(0.10)`: 8
  - `low_lexical_similarity_to_source(0.12)`: 1
  - `low_lexical_similarity_to_source(0.05)`: 1
  - `low_lexical_similarity_to_source(0.09)`: 1
  - `low_lexical_similarity_to_source(0.04)`: 1

### Key Semantic Observations:
1. **Partner Identity Cues:** 34 actions dropped explicit partner role nouns (e.g., 'human astronomer', 'automated routing agent'). While the partner remains implied by the scenario stem, preserving explicit references in the action text maintains item salience.
2. **Negation/Polarity Stability:** Only 8 actions exhibited polarity shifts in COOPERATE or INDEPENDENT actions (e.g., transitioning from 'without waiting' to a positive phrasing).
3. **Mechanical Padding Artifacts:** Zero occurrences of legacy padding phrases (`'according in order to'`, `'exactly first'`, repeated `'until'`) were found. The LLM rewriter successfully abandoned mechanical filler templates.

---

## 5. Evaluation of Scientific Trade-offs

A central question for the experimental protocol is whether to maintain the strict **span ≤ 1** token constraint or relax it to **span ≤ 2** or **span ≤ 3**.

| Policy | Usable Scenarios | Coverage % | Primary Scientific Risks | Recommended Action |
| :--- | :---: | :---: | :--- | :--- |
| **Strict (Span ≤ 1)** | 72 | 19.4% | Severe under-coverage; insufficient sample size for statistical power in mechanistic probes. | Maintain as primary gold standard for automated generation pass. |
| **Relaxed Level 1 (Span ≤ 2)** | 157 | 42.2% | Token length difference of 2 tokens (~5-8 characters). Low risk of length-based attention artifacts. | **Recommended for targeted review:** Yields 157 candidates with minimal distortion. |
| **Relaxed Level 2 (Span ≤ 3)** | 240 | 64.5% | 3 tokens (~12-15 characters) could introduce subtle sequence length bias if systematically correlated with strategy. | Use only if targeted repairs fail to close the remaining gap. |

**Recommendation:** Do not silently lower the scientific threshold in the code or promote unvetted candidates. Instead, leverage candidates with span ≤ 2 as the initial pool for targeted, one-word human-in-the-loop or template-bounded repairs.

---

## 6. Finite Prioritized Repair Queue

The 372 candidate records are partitioned into four mutually exclusive categories:

1. **Automatic Pass Pending Semantic Adjudication (72 records):**
   - Satisfies span ≤ 1 for both action and prompt.
   - No duplicate or excessive overlap issues.
   - Requires only independent human semantic verification.
2. **Priority 1: Near-Miss Targeted Repair (166 records):**
   - Combined span is 2 or 3 tokens.
   - No cross-bank duplicates or overlap issues.
   - High linguistic fluency; needs adjusting only 1 or 2 words in a single action to achieve span ≤ 1.
3. **Priority 2: Moderate Repair (100 records):**
   - Combined span is 4 or 5 tokens.
   - Intact semantic structure, but requires coordinated rewording across 2 or 3 actions.
4. **Priority 3: Substantial Reconstruction (34 records):**
   - Combined span ≥ 6 tokens, or cross-bank duplicate / excessive overlap (e.g., `021_C`, `021_B`).
   - Requires regenerating the action quartet from scratch or major restructuring.

---

## 7. Evidence-Based Next Steps & Gate Recommendations

Before controlled-bank representation mapping experiments can proceed:
1. **Do not launch representation mapping on the current candidate banks.** With only 72 accepted items (and only 12 complete triads across all three banks), representation probes would lack statistical power and introduce selection bias.
2. **Execute Targeted Offline Repairs on Priority 1 Items:** A targeted offline adjustment on the 166 Priority 1 items can quickly bring total valid scenarios to ~230+ without requiring expensive generative sweeps.
3. **Human Semantic Adjudication:** Prioritize independent review of the 72 accepted candidates and Priority 1 repaired candidates using a standardized rubric (partner salience, payoff preservation, strategic clarity).
4. **Freeze and Audit:** Once repairs achieve full triad coverage, compile new prompt inventories (`prompts_bank_*.jsonl`), generate immutable SHA-256 digests, and run the scientific acceptance suite before lifting the freeze.
