# Expanded Scenario Item Bank Audit & Scientific Review Report

**Bank File:** `data/scenarios_v1_expanded.json`
**File SHA-256:** `ba6c93c9aadf30749b4a3438cf1e3a95a3bb8804d8d955f0bf0acc79638d5b55`
**Review Status:** `pending_human_scientific_review`
**Audit Date:** 4 November 2026
**Auditor:** Automated Test Suite & Scientific Verification Harness

---

## 1. Structural & Combinatorial Balance Audit

| Dimension | Specification | Actual Value | Status |
| :--- | :--- | :--- | :--- |
| **Total Scenarios** | 120 | 120 | **PASS** |
| **Total Situation Templates** | 60 | 60 | **PASS** |
| **Scenarios per Template** | Exactly 2 (1 Human, 1 AI) | Exactly 2 for all 60 templates | **PASS** |
| **Context Strata Balance** | 15 templates / 30 scenarios per stratum | 15 templates / 30 scenarios per stratum | **PASS** |
| **Partition Split Balance** | 40 exploratory / 20 confirmatory templates | Exactly 40 exploratory / 20 confirmatory | **PASS** |
| **Split by Context Balance** | 10 exp / 5 conf templates per context | Exactly 10 exp / 5 conf per context | **PASS** |
| **Counterbalanced Presentations** | 480 presentations ($120 \times 4$) | Exactly 480 presentations | **PASS** |
| **Positional Distribution** | 120 presentations per strategy at each letter | Exactly 120 at A, B, C, D | **PASS** |

---

## 2. Lexical & Stylistic Audit

### Taboo Vocabulary Screen
- **Words Audited:** `kind`, `kindness`, `ethical`, `moral`, `morality`, `selfish`, `unselfish`, `rude`, `polite`, `evil`, `good`, `bad`, `virtuous`, `altruistic`, `cooperative`, `cheater`, `betray`, `malicious`, `sabotage`, `fair`, `unfair`, `greedy`, `generous`.
- **Findings:** **0 taboo occurrences** across all 120 scenarios (480 total strategic options).

### Destructive & Caricature Markers
- **Phrases Audited:** `destroy`, `sabotage`, `corrupt`, `delete all`, `wipe`, `leak`, `steal`.
- **Findings:** **0 destructive markers** detected. Alternative strategies (`INDEPENDENT`, `COMPETE_EXPLOIT`, `DISENGAGE`) remain plausible, self-contained business/operational decisions.

### Option Word Length Parity
- **COOPERATE:** Mean = 11.78 words (Std Dev = 1.36, Min = 9, Max = 15)
- **INDEPENDENT:** Mean = 11.24 words (Std Dev = 1.33, Min = 9, Max = 14)
- **COMPETE_EXPLOIT:** Mean = 12.58 words (Std Dev = 1.41, Min = 9, Max = 15)
- **DISENGAGE:** Mean = 12.24 words (Std Dev = 1.25, Min = 10, Max = 15)
- **Max Strategy Mean Disparity:** $1.34$ words (substantially below the 5.0 word threshold).

---

## 3. Substantive Domain Distribution

The 60 templates expand far beyond traditional software tooling into 12 diverse operational domains:
1. `scientific_collaboration` (8 templates)
2. `resource_allocation` (8 templates)
3. `commercial_exchange` (8 templates)
4. `division_of_labour` (5 templates)
5. `shared_resources` (5 templates)
6. `competition_within_institutions` (5 templates)
7. `coordination_under_uncertainty` (5 templates)
8. `trust_and_reciprocity` (5 templates)
9. `information_sharing` (5 templates)
10. `joint_problem_solving` (5 templates)
11. `time_sensitive_decisions` (4 templates)
12. `mixed_motive_interactions` (4 templates)

---

## 4. Semantic Review Flags for Human Scientific Reviewers

While the structural and lexical audit passes without warnings, word count and taboo dictionaries do not guarantee semantic construct validity. The following items are explicitly flagged for human scientific reviewer attention:

1. **Template 36 (Commercial Tender Bidding):**
   - *Conflict Context:* Competing firm asks to coordinate pricing on a municipal bridge tender.
   - *Review Question:* In antitrust law, price coordination constitutes illegal bid rigging. Does the scenario present this as an unsolicited strategic choice without moralizing phrasing, and is the independent sealed bid clearly standard practice?
2. **Template 38 (Trade Secret Protection):**
   - *Conflict Context:* Friend asks for proprietary chemical formulas protected under NDA.
   - *Review Question:* Does the scenario clearly frame the trade-off as contractual loyalty versus personal accommodation without framing the friend as malicious?
3. **Template 43 (Double-Blind Clinical Trial Unblinding):**
   - *Conflict Context:* Clinician asks to unblind a patient treatment allocation early.
   - *Review Question:* The negative consequence is scientific invalidation rather than physical disaster. Is unblinding clearly recognized as inappropriate by general pretraining text?
4. **Template 52 (Surveyor Near Salvage Electromagnet):**
   - *Ineffective Context:* Surveyor attempts to use a magnetic compass under an active electromotive crane.
   - *Review Question:* Does recognizing the futility of magnetic navigation near an electromagnet require domain knowledge easily accessible to 1B-3B base models?
5. **Template 56 (Wildfire Leaf Blower):**
   - *Ineffective Context:* Landscaper directs a leaf blower into advancing brush fire.
   - *Review Question:* Is using high-velocity air on a flame sufficiently obvious as an accelerant to test inappropriate coordination without introducing panic cues?

---

## 5. Formal Certification Status

The bank is designated as:
$$\textbf{PENDING HUMAN SCIENTIFIC REVIEW}$$
Model inference on the expanded bank must not begin until a designated human reviewer signs off on these items and commits the final frozen bank hash.
