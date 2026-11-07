# Experimental Protocol: Lexically Controlled Strategy Representation Discovery and Evaluation

**Version:** 1.0
**Status:** DRAFT — NOT FROZEN OR ACCEPTED. Do not use these banks for inference.
**Corpus Directory:** `data/controlled_strategy_banks_v1/`
**Target Model:** `Qwen/Qwen2.5-1.5B` (Revision: `8faed761d45a263340a0528343f099c05c9a4323`)

---

## 1. Scientific Background and Objectives

Previous linear-probe and contrastive representation-mapping experiments identified candidate directional geometry separating strategic decision orientations:
- `COOPERATE`
- `INDEPENDENT`
- `COMPETE_EXPLOIT`
- `DISENGAGE`

However, in the initial Phase 0B scenarios (`data/scenarios_phase0b_utility_matched.json`), cooperation action descriptions were systematically longer (mean 16.90 tokens vs. 13.15–14.26 tokens for alternative actions, with within-scenario spans reaching up to 11 tokens). Controlling for word and character counts attenuated cooperation direction consistency, raising the concern that apparent strategic geometry might reflect token-length or syntactic regularities.

This draft proposes a controlled replication experiment using three variant banks. The current artifacts do not satisfy this design, and Bank C was not independently constructed:
1. **Bank A (Length-Matched)**: Preserves original phrasing style and scenario context, tightly matching token lengths across all four strategies within each scenario.
2. **Bank B (Lexically Diversified)**: Diversifies vocabulary and sentence structures, varying action verbs and grammatical syntax away from formulaic patterns while continuing token-length control.
3. **Bank C (Independent Paraphrase Replication)**: An independently worded paraphrase bank constructed to test out-of-distribution transfer of strategy-direction probes across distinct formulations.

---

## 2. Experimental Structure and Preserved Partitions

To prevent data leakage and item confounding:
- **Scenario Families**: 62 paired template families (human and AI partner variants) are retained. Paired items share a `template_id` and `triad_id` and are never split across discovery and evaluation partitions.
- **Domain Partitions**: The 24 domains are held out orthogonally:
  - **Discovery domains**: Used to identify probe directions and linear discriminants.
  - **Evaluation domains**: Strictly held out to test whether internal representations reflect domain-general strategy concepts rather than domain-specific terminology.
- **Prompt Representation**: All prompts use the standardized trailing capture marker (`\nDecision:`), matching single-action prompt specifications in `llm_cooperation/mechanistic/contrastive_mapping.py`, capturing activations at the final token boundary without inserting literal strategy labels into the model prompt.

---

## 3. Preregistered Cross-Bank Evaluation Design

To isolate what remains invariant when linguistic variations are controlled:

### 3.1 Within-Bank Baseline
- Train 4-strategy linear probes on the Discovery partition of Bank A.
- Evaluate on the Evaluation partition of Bank A.
- Measure held-out accuracy and contrastive alignment against length-matched actions.

### 3.2 Cross-Bank Transfer (Generalization Across Phrasing)
- **Train on Bank A, Test on Bank B**: Tests whether directions identified under minimal length modification generalize when vocabulary and syntax are diversified.
- **Train on Bank B, Test on Bank C**: Intended to test transfer across distinct formulations once independent construction is demonstrated.
- **Cross-Evaluation Matrix**:
  - $D_A \to E_B, E_C$
  - $D_B \to E_A, E_C$
  - $D_C \to E_A, E_B$

### 3.3 Success and Falsification Criteria
- **Generalization Criterion**: Significant above-chance classification accuracy ($p < 0.01$ under family-clustered bootstrap resampling) on held-out domains in cross-bank evaluation ($D_A \to E_C$).
- **Directional Invariance**: Positive cosine similarity between cooperation-difference vectors ($\vec{v}_{\text{COOP}} - \vec{v}_{\text{IND}}$) discovered in Bank A and evaluated in Bank C across held-out domains.
- **Valid Falsification**: If cross-bank probe accuracy drops to chance levels or cooperation alignment vanishes upon lexical diversification, this constitutes valid evidence that previous findings were artifacts of surface phrasing rather than domain-general strategic representations.

---

## 4. Verification and Integrity Guarantees

Before executing model inference:
1. All three banks (`bank_a_length_matched.json`, `bank_b_lexically_diversified.json`, `bank_c_independent_replication.json`) and prompt datasets (`prompts_bank_*.jsonl`) are hashed in `hashes.json` and `manifest.json`.
2. Boundary tokenization checks must pass fail-closed at the `\nDecision:` prompt boundary on the pinned model revision.
3. GPU inference requires explicit `--authorize-inference` and `--authorize-paid-run` guards. Real GPU execution is never run during local development.
