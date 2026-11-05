# LLM Cooperation: Pretrained Strategy-Selection Test Harness

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/phase-0%20exploratory-orange.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An experimental test harness and analysis pipeline designed to investigate whether **base, unaligned language models** preferentially select cooperative strategies under balanced, one-shot decision dilemmas prior to any supervised fine-tuning (SFT) or RLHF/DPO.

This repository implements **Phase 0 (Exploratory Multiple-Choice Screen)** according to the experimental specification by Adrian Hau / Arca Futura LLC (`Pretrained Cooperation Representations — Experimental Specification v0.2`).

---

## 1. Overview & Key Capabilities

- **24-Scenario Balanced Item Bank (`data/scenarios.json`):**
  - Factorially stratified across **2 Partner Types** (`human` vs `ai`) and **4 Context / Cost Types** (`neutral_or_costless`, `modest_cost`, `conflict_with_objective`, `ineffective_or_inappropriate`).
  - 4 plausible actions per scenario: `COOPERATE`, `INDEPENDENT`, `COMPETE_EXPLOIT`, and `DISENGAGE`.
  - Prohibits moralizing/taboo vocabulary (`kind`, `moral`, `selfish`, `virtuous`, etc.) with balanced option lengths.
- **Latin-Square Permutation Engine (`llm_cooperation/items/`):**
  - Generates exactly 4 counterbalanced presentations per scenario (96 total presentations).
  - Guarantees each semantic strategy occupies letter positions `A`, `B`, `C`, and `D` equally often.
- **Dual-Measurement Model Runner (`llm_cooperation/harness/`):**
  - Next-token raw logit extraction and normalized 4-choice conditional probability calculation.
  - Forced-choice argmax extraction alongside separate greedy token generation and strict validity parsing.
  - Diagnostic candidate tokenizer probing (handling leading-space vs unprefixed tokens across Qwen, Pythia, OLMo, and Mistral).
  - `--mock` dry-run mode for local CI/CD testing without GPU access.
- **Scenario-Clustered Statistical Analysis (`llm_cooperation/analysis/`):**
  - Scenario-level aggregation to prevent pseudoreplication across permutations.
  - 2,000-sample clustered bootstrapping over the 24 scenarios for 95% confidence intervals.
  - Subgroup stratifications (context type, partner type, alternative strategies).
  - Letter position bias audit ($P_A, P_B, P_C, P_D$).
  - Publication-grade figure generation (`reports/figures/`) and automated Markdown decision memos.

---

## 2. Repository Structure

```
llm_cooperation/
├── configs/
│   └── models.yaml                 # Provenance manifest for Qwen, Pythia, OLMo, Mistral
├── data/
│   └── scenarios.json              # Frozen 24-scenario item bank
├── docs/
│   ├── phase0_protocol.md          # Scientific protocol & gate rules
│   └── runpod_lambda_setup.md      # Lambda Labs / RunPod execution guide
├── llm_cooperation/
│   ├── items/                      # Schemas, permutations, and item audit
│   ├── harness/                    # ModelRunner, tokenizer probe, and scoring
│   ├── analysis/                   # Aggregation, clustered bootstrapping, and plotting
│   └── cli.py                      # Unified CLI entrypoint (`llm-coop`)
├── tests/                          # Full pytest test suite
├── pyproject.toml                  # PEP 621 package specification
├── requirements.txt                # Pip requirements for cloud GPU environments
└── README.md
```

---

## 3. Quickstart & Installation

### Local / Development Setup
```bash
git clone <repo-url>
cd llm_cooperation
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Running Tests and Item Audit
```bash
# Verify all unit tests (permutations, schema, parsing, analysis)
pytest tests/

# Run the scenario item bank and Latin-square balance audit
llm-coop audit-items
```

---

## 4. Running Experiments

### Dry-Run / Mock Mode (No GPU required)
Test the end-to-end evaluation and analysis pipeline locally in seconds:
```bash
# Run 96 mock presentations
llm-coop run --model "mock-qwen2.5-3b" --mock -o results

# Analyze results and generate figures
llm-coop analyze results/run_mock-qwen2.5-3b_*.jsonl -o reports
```

### Modal Cloud Execution (Primary Backend)
Refer to [docs/modal_execution_guide.md](docs/modal_execution_guide.md) for complete instructions, Windows PowerShell setup, and volume sync commands.

Modal manages on-demand GPU allocation, persistent model weight caching (`llm-coop-hf-cache`), and results persistence (`llm-coop-results`):

```powershell
# Mock run on Modal (zero-GPU CPU container)
modal run modal_app.py --model "mock-qwen2.5-3b" --mock True

# Real GPU run on Modal (A10G or L40S, requires explicit --authorize-paid-run True guard)
modal run modal_app.py --model "Qwen/Qwen2.5-3B" --precision "bfloat16" --mock False --authorize-paid-run True

# Download results from Modal Volume to G:\llm_cooperation\results
modal volume get llm-coop-results <run_file>.jsonl G:\llm_cooperation\results\
```

### Local / Cloud GPU Execution (Independent CLI)
The harness can also be executed directly on any local or remote machine without Modal:
```bash
# 1. Qwen 2.5 3B (Pretrained Base)
llm-coop run --model "Qwen/Qwen2.5-3B" --precision bfloat16 -o results

# 2. Pythia 2.8B (Pretrained Base)
llm-coop run --model "EleutherAI/pythia-2.8b" --precision bfloat16 -o results

# 3. OLMo 2 1B (Pretrained Base)
llm-coop run --model "allenai/OLMo-2-1124-1B" --precision bfloat16 -o results

# 4. Compare models across runs (separating base models from SFT comparators)
llm-coop compare-models results/*.jsonl -o reports
```

---

## 5. Output Artifacts

Running `llm-coop analyze` produces:
- `reports/phase0_report_<model>.md`: Markdown executive summary with gate recommendations (`ADVANCE`, `REVISE`, or `STOP`), 95% bootstrap CIs, and stratum breakdowns.
- `reports/scenario_aggregates_<model>.csv`: Per-scenario metrics aggregated over the 4 permutations.
- `reports/figures/cooperation_by_strata.png`: Bar plots showing cooperation rates by cost context and partner type.
- `reports/figures/strategy_distribution.png`: Rates for Cooperate vs Independent vs Compete vs Disengage.
- `reports/figures/position_bias_audit.png`: Choice frequency across letter positions A, B, C, D.

---

## 6. Scientific Protocol & Claim Boundary

Per experimental specification (§13):
> *"Across several pretrained language-model families, a balanced multiple-choice screen finds a reproducible bias toward selecting cooperative strategies under specified one-shot conditions."*

- Phase 0 is descriptive and behavioral; it **does not** prove internal motives, innate altruism, or low-level mechanistic circuits.
- The item bank remains formally designated as **Pending Human Scientific Review**; lexical length parity is necessary but does not inherently guarantee construct equivalence across options.
- The 25% four-choice share is a uniform display reference, not a naturalistic null hypothesis.
- Escalation to Phase 1/2 mechanistic probing requires passing the predefined gates: high format compliance, position robustness, consistent cross-scenario patterns, and explicit cross-family human review (mock runs strictly excluded).

### Exploratory mechanistic work

See [the mechanistic exploration guide](docs/mechanistic_exploration.md) for the template-separated MLP-neuron screen, held-out ablation, random-neuron controls, calibration, and explicit Modal authorization. This uses the Phase 0B exploratory bank; the protected prospective Phase 1 bank remains gated.
