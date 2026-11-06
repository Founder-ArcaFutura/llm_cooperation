# Offline Scientific Audit of Controlled Strategy Banks (`production01`)

**Audit Status:** COMPLETE
**Input Source:** `research/controlled_rewrites/production01/`
**Phase 0B Source:** `data/scenarios_phase0b_utility_matched.json` (124 scenarios)
**Target Execution Scope:** Candidate Banks A, B, and C (372 scenario-bank variants)
**Authoritative Tokenizer:** `Qwen/Qwen2.5-1.5B` (`8faed761d45a263340a0528343f099c05c9a4323`)

---

## Executive Summary

A rigorous, offline, reproducible scientific audit of the complete Modal `production01` rewrite generation was conducted. No language models were executed, no cloud infrastructure was invoked, and no source files were modified.

Key takeaways:
1. **Provenance & Completeness (100% Accounted):** All 372 scenario-bank JSON records (`000_A` through `123_C`) are present and intact. Manifest accounting perfectly matches individual records: exactly **72 passed automatic constraints** (30 Bank A, 21 Bank B, 21 Bank C) and **300 remain unresolved**. However, intersecting accepted records across all three banks reveals that **only 8 complete three-bank scenario triads exist** (indices: `[2, 3, 28, 29, 35, 65, 72, 114]`). Scenario identities, strategic labels (COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE), and payoff structures are rigorously preserved across all items.
2. **Strict Token-Span Barrier & Retokenization:** Only 19.4% (72/372) satisfy the strict span ≤ 1 criterion under both action-only and full-prompt tokenization. Independent retokenization against the pinned `Qwen/Qwen2.5-1.5B` tokenizer verified all stored action and full-prompt counts with **0 mismatches**.
3. **Threshold Relaxation Trade-Off:** Relaxing the permitted token span from **span ≤ 1** to **span ≤ 2** increases accepted candidates from 72 (19.4%) to **157 (42.2%)**. Relaxing to **span ≤ 3** brings coverage to **240 (64.5%)**.
4. **Lexical Independence vs Cross-Bank Collisions:** Cross-bank exact action duplicates were detected across pairs (2 in A vs B, 10 in A vs C, 38 in B vs C). While mean cross-bank Jaccard similarity is moderate (~0.46 to 0.56, reflecting domain-specific nouns), 129 candidates exhibit cross-bank duplicates or excessive overlap (> 0.85) when evaluated comprehensively across all candidates.
5. **Diagnostic Semantic Integrity Triage:** Diagnostic heuristics flagged **297 actions across 238 records**. This includes 103 partner-cue-loss flags (72 human, 31 AI) and 182 polarity-shift flags (179 introduced, 3 removed). Crucially, **42 of the 72 automatically accepted variants** carry diagnostic semantic flags, highlighting that automatic token-matching passes require rigorous human semantic adjudication.
6. **Collision-Aware Repair Queue:** Incorporating independently computed cross-bank collisions ensures items with diversity defects are not misclassified as simple near-misses. The 300 unresolved items are partitioned into: **103 Priority 1 near-misses (spans 2-3, no collisions)** suitable for targeted minor wording adjustment, **58 Priority 2 moderate repairs (spans 4-5, no collisions)**, and **139 Priority 3 substantial reconstructions** (known cross-bank collisions, structural duplicates, or spans ≥ 6).

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
| **Complete Three-Bank Triads (A ∩ B ∩ C)** | - | - | - | **8** |
| **Retokenization Verification** | - | - | - | **PASSED (0 mismatches)** |

**Complete Three-Bank Matched Triad Analysis:** Only **8 scenario indices** (`[2, 3, 28, 29, 35, 65, 72, 114]`) currently have all three bank variants (A, B, and C) automatically accepted. Because representation experiments require matched triad comparisons across Banks A, B, and C, the true usable matched sample size at strict automatic acceptance is **8 scenarios (6.5%)**, not 12.

---

## 2. Token Matching Characterization

Both action-only and full-prompt token counts were validated against the pinned tokenizer `Qwen/Qwen2.5-1.5B`.

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

### Cross-Bank Collisions and Independence:
While historical generator checks only compared candidates against earlier accepted records, comprehensive cross-bank evaluation reveals **50 pairwise exact duplicate actions** (2 in A vs B, 10 in A vs C, 38 in B vs C).
Across all 372 candidates, **129 candidates share duplicate actions or excessive lexical overlap (> 0.85)** with a corresponding candidate in another bank. For example, scenario `014_C` (index 14) duplicates Bank A's COOPERATE action (*"Share alloy test manifests via the shared customs portal with the supply coordinator."*). Incorporating this independent check into the repair queue prevents misdiagnosing collision cases as token-length-only issues.

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

### Key Semantic Observations (Derived Directly from Measured Flags):
1. **Partner Identity Cues:** Diagnostic heuristics detected **103 partner-cue-loss flags** (72 human partner cue loss flags and 31 AI partner cue loss flags). While the partner type is established in the stem, omitting the partner noun in the option text reduces partner salience during choice selection.
2. **Negation/Polarity Shifts:** A total of **182 polarity-shift flags** were recorded (179 introduced negations and 3 removed negations). For example, rewriting an action with 'without waiting' introduces negation that was absent in the original positive action phrasing.
3. **Automatic Passes Require Semantic Adjudication:** Crucially, **42 of the 72 automatically accepted candidates (58.3%)** carry diagnostic semantic flags. Automated token-span satisfaction cannot substitute for independent semantic validation.

---

## 5. Evaluation of Scientific Trade-offs

A central question for the experimental protocol is whether to maintain the strict **span ≤ 1** token constraint or relax it to **span ≤ 2** or **span ≤ 3**.

| Policy | Usable Scenarios | Coverage % | Primary Scientific Risks | Recommended Action |
| :--- | :---: | :---: | :--- | :--- |
| **Strict (Span ≤ 1)** | 72 | 19.4% | Severe under-coverage; only 8 complete triads across Banks A, B, and C. | Maintain as primary target for completed corpus. |
| **Relaxed Level 1 (Span ≤ 2)** | 157 | 42.2% | Token length difference of 2 tokens (~5-8 characters). Low risk of length-based attention artifacts. | **Recommended diagnostic pool:** Yields 157 candidates for targeted human-in-the-loop repair. |
| **Relaxed Level 2 (Span ≤ 3)** | 240 | 64.5% | 3 tokens (~12-15 characters) could introduce subtle sequence length bias if systematically correlated with strategy. | Fallback pool for items where 2-token phrasing is linguistically awkward. |

**Recommendation:** Do not silently lower the scientific threshold in the code or promote unvetted candidates. Instead, leverage candidates with span ≤ 2 as the initial pool for targeted, one-word human-in-the-loop or template-bounded repairs.

---

## 6. Finite Prioritized Repair Queue

The 372 candidate records are partitioned into four mutually exclusive categories incorporating both token spans and independent cross-bank collision checks:

1. **Automatic Passes with Strict Token Matching (72 records):**
   - **Collision-Free Automatic Passes (64 records):** Satisfy span ≤ 1 for both action and prompt, and are completely free of cross-bank duplicates or excessive overlap (> 0.85).
   - **Automatic Passes with Cross-Bank Collisions (8 records):** Satisfy span ≤ 1 token matching, but exhibit lexical collisions with candidate actions in another bank (e.g., `021_A`, `073_C`, `082_C`, `083_C`, `102_C`, `107_C`, `020_B`, `048_B`). Because these collide with candidate alternatives, they require collision-aware review before scientific promotion.
2. **Priority 1: Near-Miss Targeted Repair (103 records):**
   - Combined span is 2 or 3 tokens.
   - **Strictly free of cross-bank collisions and duplicates.**
   - High linguistic fluency; needs adjusting only 1 or 2 words in a single action to achieve span ≤ 1.
3. **Priority 2: Moderate Repair (58 records):**
   - Combined span is 4 or 5 tokens, free of cross-bank collisions.
   - Intact semantic structure; requires coordinated minor rewording across actions.
4. **Priority 3: Substantial Reconstruction (139 records):**
   - Exhibits cross-bank duplicates or excessive overlap (> 0.85), mechanical filler, or combined span ≥ 6 tokens.
   - Includes cases such as `014_C`, `021_B`, and `021_C` that require generating genuinely fresh alternative phrasings rather than mere token trimming.

---

## 7. Evidence-Based Next Steps & Gate Recommendations

Before controlled-bank representation mapping experiments can proceed:
1. **Do not launch representation mapping on the current candidate banks.** With only 8 complete triads across all three banks (6.5% of the Phase 0B design), representation probes would lack statistical power and introduce severe item selection bias.
2. **Execute Targeted Offline Repairs on Priority 1 Items:** A targeted offline adjustment on the 103 Priority 1 items can efficiently expand triad coverage without requiring expensive generative sweeps.
3. **Human Semantic Adjudication:** Prioritize independent review of the 72 accepted candidates (of which 42 carry diagnostic flags) and repaired candidates using a standardized rubric (partner salience, payoff preservation, strategic clarity).
4. **Freeze and Audit:** Once repairs achieve full triad coverage, compile new prompt inventories (`prompts_bank_*.jsonl`), generate immutable SHA-256 digests, and run the scientific acceptance suite before lifting the freeze.
