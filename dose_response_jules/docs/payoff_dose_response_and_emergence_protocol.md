# Scientific Protocol: Payoff Dose–Response and Pretraining Emergence of Cooperation

**Protocol Document Version:** v1.0.0-preregistration  
**Date:** November 2026  
**Status:** `exploratory_preflight_frozen`  
**Item Bank Reference:** `data/scenarios_dose_response_exploratory.json`  
**Diagnostic Format Calibration Bank:** `data/calibration_bank.json`  

---

## 1. Scientific Objectives & Primary Research Question

### Primary Scientific Question
**Do pretrained base language models develop a cooperative behavioural default prior to alignment, and how does that default respond to increasing private costs, partner benefits, and expected reciprocal returns?**

Ordinary decision-makers frequently cooperate when cooperation is instrumentally advantageous. Prior work (Phase 0 and Phase 0B) investigated cooperation under approximate expected utility equivalence ($\mathbb{E}[U(\text{COOP})] \approx \mathbb{E}[U(\text{INDEP})]$). This protocol expands the investigation along two essential dimensions:
1. **Payoff Dose–Response (Phase A):** Quantifying the behavioral curve across an exploratory parametric payoff sweep around equal private utility, measuring sensitivity slopes, indifference crossover thresholds, and interactions with partner welfare and future interaction horizons.
2. **Pretraining Emergence (Phase B):** Tracking the longitudinal acquisition trajectory across intermediate pretraining checkpoints (e.g. EleutherAI Pythia sequence), assessing whether conditional cooperative preferences emerge early, and determining whether preference emergence precedes or follows linear strategic concept decodability.

---

## 2. Literature Grounding & Claim Boundaries

### Comparative Positioning Against Prior Art
- **CoopShift (2026):** Investigates shifts in cooperative strategies across multi-agent reinforcement learning and fine-tuned models under distributional shifts. While CoopShift focuses on post-training adaptation and equilibrium convergence in aligned agents, our focus isolates the *unaligned base foundation model* prior to RLHF/DPO, evaluating whether cooperation is already present as an inductive prior or pretraining artifact.
- **PNAS Nexus Repeated-Game Study (2026):** Evaluates language models playing iterated Prisoner's Dilemma, public goods, and coordination games with extensive history prompts. Our work contrasts by isolating one-shot decision dilemmas and precisely varying the explicit private/partner payoff structure and shadow-of-the-future framing without historical trajectory confounding.
- **Pretraining Dynamics Literature (e.g., Pythia, OLMo suites):** Prior work documented language modeling loss, syntactic probes, and factual recall across pretraining steps. This protocol provides the first systematic examination of strategic dilemma decision defaults and payoff dose–response across checkpoint series.

### Strict Scientific Claim Boundaries
- Observing a behavioral preference for cooperation **does not** establish:
  - Rational agency or intentional utility maximization.
  - Inherent, innate, or biological altruism.
  - Instrumental convergence towards benevolent goals.
  - Causal origin in particular curated pretraining training examples.
- Rather, it characterizes the statistical regularities and inductive biases present in next-token conditional probability distributions induced by standard self-supervised pretraining corpora.

---

## 3. Experimental Design: Phase A — Payoff Dose–Response

### Parametric Payoff Sweep Matrix
We sweep the focal actor's net private utility difference:
$$\Delta U_{\text{actor}} = U_{\text{actor}}(\text{COOPERATE}) - U_{\text{actor}}(\text{INDEPENDENT})$$
across five core regimes with finer sampling around the indifference boundary:
1. **Cooperation Advantageous:** $\Delta U = +0.20$ (Cooperation is strictly superior).
2. **Exact Utility Equivalence:** $\Delta U = 0.00$ (Phase 0B construct validation baseline).
3. **Small Disadvantage (Near Crossover):** $\Delta U = -0.05$ and $\Delta U = -0.10$.
4. **Moderate Disadvantage:** $\Delta U = -0.20$ and $\Delta U = -0.30$.
5. **Substantial Disadvantage:** $\Delta U = -0.50$ and $\Delta U = -0.60$.

### Independent Factorial Dimensions
To disentangle private cost from partner welfare and repeated-interaction expectations, we independently vary:
- **Actor Private Payoff Difference ($\Delta U_{\text{actor}}$):** As defined above.
- **Partner Payoff Benefit ($B_{\text{partner}}$):** Low partner gain ($+0.20$) vs High partner gain ($+1.00$).
- **Future Interaction Horizon ($\text{Reciprocity}$):** One-shot strictly terminal interaction vs Repeated interaction / ongoing coordination shadow.
- **Partner Identity:** Paired Human vs AI partner variants for each template situation.

### Control Conditions
1. **Symmetric Outcome Controls:** Conditions where both actor and partner receive identical payoffs ($+1.0 / +1.0$) regardless of whether cooperation or independent action is selected.
2. **Matched Non-Social Numerical-Choice Controls:** Identical numerical payoff matrix ($U_{\text{opt1}}, U_{\text{opt2}}, U_{\text{opt3}}, U_{\text{opt4}}$) presented with neutral algorithmic / resource allocation framing stripped of social, cooperative, or interpersonal language.

### Counterbalancing & Linguistic Parity
- **Latin-Square Permutations:** Exactly 4 counterbalanced presentations per scenario, mapping strategies `COOPERATE`, `INDEPENDENT`, `COMPETE_EXPLOIT`, and `DISENGAGE` equally to positions `A`, `B`, `C`, and `D`.
- **Wording Invariance:** Core option wording is held constant while payoff values/timings are systematically altered.
- **Length Parity:** Option word lengths balanced within $\le 2$ words across options within each scenario.
- **Prohibited Markers:** Strict ban on moralizing terminology (`kind`, `moral`, `virtuous`, `evil`) and caricature destructive markers (`sabotage`, `destroy`, `steal`).

---

## 4. Experimental Design: Phase B — Pretraining Emergence

### Target Checkpoint Series: EleutherAI Pythia
Using the publicly available, fully deduplicated pretraining checkpoints of the Pythia series (e.g. `EleutherAI/pythia-160m`, `EleutherAI/pythia-1.4b`, `EleutherAI/pythia-2.8b`):
- Pinned steps: `step0`, `step1000`, `step10000`, `step50000`, `step100000`, `step143000` (final).
- Evaluated on the identical frozen dose–response instrument.

### Behavioral vs Format Competence Disentanglement
Early pretraining checkpoints frequently exhibit token generation artifacts or invariant letter biases (e.g. predicting letter `A` uniformly regardless of prompt).
- **Rule:** Diagnostic calibration bank (`data/calibration_bank.json`) is evaluated alongside each checkpoint.
- **Safeguard:** Early-checkpoint format failures or arithmetic errors must **not** be interpreted as the absence of a preference. Logit-based forced-choice conditional log-probabilities $\Delta_{\log P} = \log P(\text{COOP}) - \log P(\text{INDEP})$ are analyzed separately from greedy generated letter choices.

### Representation-Decoding Probe (Exploratory Mechanistic Check)
- Evaluated only at checkpoints where basic format / semantic competence is observed.
- Fit a linear ridge probe on residual stream representations at intermediate layers to classify `COOPERATE` vs `INDEPENDENT` option representations.
- Primary comparison: Does behavioral differentiation ($\Delta_{\log P} \ne 0$) emerge *before*, *concurrently with*, or *after* above-chance linear strategic concept decodability?

---

## 5. Statistical Estimation & Nonlinear Curve Fitting

### Resampling & Clustered Uncertainty
- Primary resampling unit: `template_id` (scenario family clustering, keeping paired human/AI and payoff variants together).
- 2,000 cluster-bootstrap iterations for 95% confidence intervals.

### Model-Specific Payoff-Response Metrics
1. **Equal-Utility Preference:** $\Delta_{\text{choice}}(\Delta U=0)$ and $\Delta_{\log P}(\Delta U=0)$.
2. **Payoff Sensitivity Slope:** Linear/tangent slope $\beta_1 = \left.\frac{\partial P(\text{COOP})}{\partial \Delta U}\right|_{\Delta U=0}$.
3. **Crossover Indifference Threshold ($\Delta U^*$):** Net private cost at which $P(\text{COOP}) = P(\text{INDEP})$ (or $\Delta_{\log P} = 0$). If positive, model requires private subsidy to cooperate; if negative, model tolerates private loss to cooperate.
4. **Interactions:**
   $$\Delta_{\text{benefit}} = P(\text{COOP} \mid \text{High Partner Benefit}) - P(\text{COOP} \mid \text{Low Partner Benefit})$$
   $$\Delta_{\text{reciprocity}} = P(\text{COOP} \mid \text{Repeated Shadow}) - P(\text{COOP} \mid \text{One-Shot})$$

### Goodness of Fit and Nonlinearities
- We evaluate 4-parameter logistic/sigmoid vs polynomial/spline/monotonicity models.
- We report Mean Squared Error (MSE), Akaike Information Criterion (AIC), and test for non-monotonicities, inflection thresholds, and floor/ceiling saturation rather than assuming strict logistic monotonicity.

---

## 6. Preregistered Falsification Conditions

The hypothesis of an intrinsic cooperative behavioral default in pretrained base models is falsified if:
1. **Zero Equal-Utility Preference:** $\Delta_{\log P}(\Delta U = 0) \le 0$ and $\Delta_{\text{choice}}(\Delta U = 0) \le 0$ across base model families after controlling for position bias and framing.
2. **Payoff Insensitivity:** The sensitivity slope $\beta_1$ is statistically indistinguishable from zero (flat dose–response curve), indicating indifference to payoff structure or random responding.
3. **Control Failure:** Selection patterns in social cooperation scenarios do not differ from matched non-social numerical controls.
4. **Dominant Position Pathology:** Choice behavior is entirely explained by letter position bias (spread across A/B/C/D $> 35\%$).
5. **Emergence Artifact:** Preferences observed in later checkpoints are already present at `step0` (untrained random initialization), indicating unlearned token/prompt length artifacts.

---

## 7. Execution Governance & Resource Estimates

### Execution Governance & Holdout Restrictions
- Confirmatory partitions in Phase 0B (`data/scenarios_phase0b_utility_matched.json`) and Phase 1 (`data/scenarios_phase1_prospective.json`) remain strictly untouched and held out.
- Phase A sweep items are exploratory derivatives instantiated from accepted exploratory templates.
- **Fail-Closed Paid Compute Guard:** Real GPU inference on Modal or cloud instances requires explicit authorization (`--authorize-paid-run True` or `ALLOW_PAID_RUN=true`).
- Local CI/CD tests execute exclusively in `--mock` mode with zero GPU spend.

### Computational Resource Estimate
- **Instrument Size:** 20 templates $\times$ 6 payoff conditions $\times$ 2 partner types $\times$ 4 permutations = 960 presentations per evaluated model.
- **Pythia Emergence Series:** 6 checkpoints $\times$ 960 presentations $\approx 5,760$ inferences per model scale.
- **Tokens per Inference:** $\approx 350$ prompt tokens + 1 target token. Total tokens per checkpoint $\approx 336\text{k}$ tokens.
- **Compute Time:** On an A10G (Pythia-1.4B / 2.8B), throughput $\approx 25$ req/s $\implies \approx 40$ seconds per checkpoint ($\approx 4\text{ minutes}$ GPU time for full 6-checkpoint sweep).
- **Estimated Cost:** $<\$0.50$ total Modal GPU compute.

### Minimal Real-Model Pilot Launch Command
When approved for execution:
```bash
# Minimal single-checkpoint exploratory pilot (Pythia-1.4b final checkpoint)
python -m llm_cooperation.cli run \
  --model "EleutherAI/pythia-1.4b" \
  --bank "dose-response" \
  --precision bfloat16 \
  --output-dir results/dose_response_pilot

# Modal remote execution command (requires explicit paid authorization)
modal run modal_pythia_emergence.py \
  --model "EleutherAI/pythia-1.4b" \
  --checkpoint-order 5 \
  --authorize-paid-run True
```
