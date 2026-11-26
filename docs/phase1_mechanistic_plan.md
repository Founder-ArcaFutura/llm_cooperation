# Phase 1 Mechanistic Probing: Scientific Plan & Methodology

**Document Version:** v1.0.0 (Concept Architecture)
**Date:** 4 November 2026
**Scope:** Forward-looking plan for internal representation probing conditional on Phase 0 behavioral replication.
**Implementation Constraint:** Documentation only. No large-scale activation caching, SAE training, or causal ablation scripts are implemented in this behavioral screen PR.

---

## 1. Scientific Objective

If Phase 0 behavioral replication demonstrates that base pretrained models reliably modulate strategy selection according to situational context across multiple training families, the objective of Phase 1 is to determine:
> **Does an identifiable internal representation contribute causally to cooperative choice, or is the behavior an epiphenomenon of low-level linguistic surface tokens?**

---

## 2. Distinguishing Causal Mechanisms from Correlation

A key hazard in mechanistic interpretability is mistaking descriptive neural correlate features for causal mechanisms:
1. **The Epiphenomenon Fallacy:** A linear probe or SAE feature may correlate with cooperative outputs simply because it encodes positive sentiment, professional tone, or general text length.
2. **The Non-Selective Disruption Fallacy:** Ablating an attention head or steering vector that causes a model to cease choosing "Cooperate" does **not** prove a cooperation circuit was disabled if the intervention simultaneously breaks grammar, syntax, general task compliance, or factual recall.
3. **Selectivity Controls Requirement:** Any proposed causal intervention must demonstrate double dissociation:
   - Specific modulation of strategic decisions under cooperative dilemmas.
   - Zero degradation on independent calibration benchmarks (e.g. `data/calibration_bank.json`), factual knowledge tasks, or basic response-format following.

---

## 3. Planned Experimental Probes

### Probe 1: Layerwise Activation Contrasts and Residual Stream Geometry
- **Method:** Extract hidden states $h_l$ at the prompt termination boundary (immediately before generating the choice letter) across all 120 expanded scenarios $\times$ 4 counterbalanced permutations.
- **Metric:** Compute differential activation vectors:
  $$v_{\text{coop}}^{(l)} = \mathbb{E}[h_l \mid \text{Choice}=\text{COOPERATE}] - \mathbb{E}[h_l \mid \text{Choice} \neq \text{COOPERATE}]$$
- **Controls:** Stratify contrast across matched pairs (same situation template, contrasting choices) to isolate semantic choice representations from stem vocabulary differences.

### Probe 2: Activation Patching / Interchange Intervention Training (IIT)
- **Method:** Perform causal interchange interventions between matched clean and corrupted presentations:
  - Base input: Neutral-cost scenario where the model chooses `COOPERATE`.
  - Source input: Conflict-with-objective scenario where the model chooses `INDEPENDENT`.
- **Target:** Patch residual stream activations and individual attention head outputs at intermediate layers to identify minimal causal sub-networks that flip the strategic decision.

### Probe 3: Sparse Autoencoder (SAE) Feature Decomposition
- **Method:** Leverage pretrained or newly trained sparse autoencoders on intermediate residual streams (e.g. layer $L/2$ to $3L/4$).
- **Analysis:** Identify monosemantic latents activated specifically by cooperative opportunity, partner vulnerability, reciprocal obligations, or contractual constraints.
- **Validation:** Measure latent sparsity, reconstruction fidelity, and cross-scenario consistency.

### Probe 4: Targeted Activation Steering and Dose-Response Curves
- **Method:** Inject learned steering vectors into the forward pass:
  $$h'_l = h_l + \alpha \cdot v_{\text{coop}}^{(l)}$$
- **Dose-Response:** Evaluate the effect of varying coefficient $\alpha \in [-5.0, +5.0]$:
  - Test if positive $\alpha$ selectively increases cooperative choices in marginal cost conditions without producing indiscriminate cooperation in negative control conditions.
  - Test if negative $\alpha$ selectively suppresses cooperation in favor of independence or competition.
  - **Selectivity Test:** Verify that calibration accuracy and generated-letter validity remain $>95\%$ under steering.

### Probe 5: Selective Circuit Ablation (Knockout)
- **Method:** Apply mean-ablation or zero-ablation to candidate attention heads or MLP feature directions identified in Probes 2 & 3.
- **Hypothesis Test:** True cooperation circuits will eliminate context-sensitive strategy differentiation while leaving general language modeling loss and format calibration performance unaffected.

---

## 4. Phase 1 Prerequisite Gate

Phase 1 mechanistic probing will be initiated **only after**:
1. Human scientific reviewers approve and freeze the expanded Phase 0 scenario bank (`data/scenarios_v1_expanded.json`).
2. At least two independently trained base model families pass all Phase 0 gates (format compliance $>50\%$, position spread $\le 25\%$, significant context contrast in confirmatory partition).
3. Compute resources and cloud storage for multi-gigabyte activation snapshots are provisioned and budgeted.
