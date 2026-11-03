# Cloud Setup and Execution Guide: Lambda Labs & RunPod

This guide outlines setup, deployment, model checkpoint verification, and execution workflows for running the **Pretrained Cooperation Representations Screen (Phase 0)** on GPU cloud instances (such as Lambda Labs or RunPod).

---

## 1. Cloud Instance Selection

### Recommended Hardware
| Model | Parameters | Required VRAM | Recommended GPU |
| :--- | :--- | :--- | :--- |
| **Qwen/Qwen2.5-3B** | 3.09B | ~7–8 GB | 1x RTX 3090, A4000, A5000, or A10G |
| **EleutherAI/pythia-2.8b** | 2.8B | ~7–8 GB | 1x RTX 3090, A4000, A5000, or A10G |
| **allenai/OLMo-2-1124-1B** | 1.18B | ~5–6 GB | 1x RTX 3090, A4000, A5000, or A10G |
| **allenai/OLMo-2-1124-7B** | 6.9B | ~16–18 GB | 1x A100 (40GB/80GB), A6000, or L40S |
| **mistralai/Mistral-7B-v0.3** | 7.25B | ~16–18 GB | 1x A100 (40GB/80GB), A6000, or L40S |

A single 24GB or 40GB GPU instance (e.g. 1x NVIDIA A10G, A5000, RTX 4090, or A100) on Lambda Labs or RunPod can comfortably execute the full Phase 0 battery across all 3 primary models in less than 5 minutes total inference time.

---

## 2. Environment Setup

### 2.1 Lambda Labs (Ubuntu 22.04 / CUDA 12)
Connect to your Lambda instance:
```bash
ssh ubuntu@<YOUR_LAMBDA_IP>

# Clone repo and enter directory
cd ~/
git clone <YOUR_REPO_URL> llm_cooperation
cd llm_cooperation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install package
pip install --upgrade pip
pip install -e ".[dev]"
```

### 2.2 RunPod (Pytorch 2.x Template)
Connect via SSH or Web Terminal:
```bash
cd /workspace
git clone <YOUR_REPO_URL> llm_cooperation
cd llm_cooperation

# Setup virtual environment or use container python
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
```

---

## 3. Hugging Face Authentication & Model Caching

For gated or rate-limited repositories (e.g. Mistral), set your Hugging Face token:
```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# or run interactive login:
huggingface-cli login
```

Optionally specify a persistent cache path on a mounted volume:
```bash
export HF_HOME="/workspace/.cache/huggingface"
```

---

## 4. Running the Phase 0 Experiment

### 4.1 Step 1: Audit Scenarios and Permutations
Before running models, verify that the item bank and 96 counterbalanced presentations pass all balance checks:
```bash
llm-coop audit-items
```

### 4.2 Step 2: Run Primary Base Models
Run each base model checkpoint. The harness extracts raw logits for `A`, `B`, `C`, and `D`, computes normalized conditional 4-choice probabilities, records forced-choice argmax, and performs a greedy completion sanity check.

#### 1. Qwen 2.5 3B (Pretrained Base)
```bash
llm-coop run \
  --model "Qwen/Qwen2.5-3B" \
  --precision "bfloat16" \
  --device "auto" \
  --output-dir "results"
```

#### 2. Pythia 2.8B (Pretrained Base)
```bash
llm-coop run \
  --model "EleutherAI/pythia-2.8b" \
  --precision "bfloat16" \
  --device "auto" \
  --output-dir "results"
```

#### 3. OLMo 2 1B (Pretrained Base)
```bash
llm-coop run \
  --model "allenai/OLMo-2-1124-1B" \
  --precision "bfloat16" \
  --device "auto" \
  --output-dir "results"
```

*(Optional 4th family replication)*:
```bash
llm-coop run \
  --model "allenai/OLMo-2-1124-7B" \
  --precision "bfloat16" \
  --device "auto" \
  --output-dir "results"
```

*(Optional Post-Trained Sanity Comparator)*:
If a base model exhibits 0% format compliance, run the post-trained comparator to test whether the prompt structure elicits answers after SFT:
```bash
llm-coop run \
  --model "Qwen/Qwen2.5-3B-Instruct" \
  --precision "bfloat16" \
  --device "auto" \
  --output-dir "results"
```
*Notice: Never cite instruct/SFT comparator performance as evidence for unaligned pretraining.*

---

## 5. Statistical Analysis & Reporting

Once a run produces a `.jsonl` file in `results/`, run the analysis engine:
```bash
# Analyze a specific model run
llm-coop analyze results/run_Qwen_Qwen2.5-3B_*.jsonl --output-dir reports
```

This generates:
1. `reports/phase0_report_<model>.md`: Detailed gate assessment, bootstrap confidence intervals, and subgroup tables.
2. `reports/scenario_aggregates_<model>.csv`: Scenario-level aggregated metrics (24 rows).
3. `reports/figures/cooperation_by_strata.png`: Bar plots across cost strata and partner types.
4. `reports/figures/strategy_distribution.png`: Comparative selection across the 4 strategies.
5. `reports/figures/position_bias_audit.png`: Diagnostic plot of answer-letter frequencies (A, B, C, D).

---

## 6. Background Execution (Tmux / Screen)
To prevent network disconnects on SSH cloud terminals:
```bash
tmux new -s eval

# Inside tmux:
source venv/bin/activate
llm-coop run --model "Qwen/Qwen2.5-3B" -o results > qwen_run.log 2>&1 &

# Detach with Ctrl+B then D
# Reattach later:
tmux attach -t eval
```
