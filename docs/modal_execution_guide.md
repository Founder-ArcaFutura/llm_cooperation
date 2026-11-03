# Modal Execution Guide & Windows Setup

This guide details how to execute Phase 0 behavioural screen experiments on [Modal](https://modal.com) from a Windows PowerShell development environment (local repository path: `G:\llm_cooperation`).

---

## 1. Prerequisites & Windows PowerShell Setup

Open **PowerShell** on Windows and set up the local Python virtual environment:

```powershell
# Navigate to the workspace repository
Set-Location G:\llm_cooperation

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install package with development and modal dependencies
pip install --upgrade pip
pip install -e .
pip install modal
```

Authenticate with your Modal account:
```powershell
modal setup
```

Ensure your Hugging Face credentials are set in Modal if accessing gated/pinned model weights:
```powershell
modal secret create huggingface-secret HF_TOKEN="your_hf_token_here"
```

---

## 2. Modal Architecture & Resource Management

The Modal backend is implemented in `modal_app.py` using the current Modal Python SDK (`modal.App`, `modal.Image`, `modal.Volume`):

- **Hugging Face Model Cache Volume (`llm-coop-hf-cache`):** Caches downloaded weights at `/root/hf_cache` so repeated runs do not re-download gigabytes of weights.
- **Results Volume (`llm-coop-results`):** Persists all `.jsonl` presentation records and metadata at `/root/results` with durability across container restarts.
- **On-Demand Sequential Execution:** Models run sequentially on-demand. There are no always-on web endpoints or idle compute costs.
- **Resource Profiles:**
  - **1B–3B Base Models** (e.g. `Qwen/Qwen2.5-3B`, `EleutherAI/pythia-2.8b`, `allenai/OLMo-2-1124-1B`): Run on `A10G` (24GB VRAM) with `bfloat16`.
  - **7B Models** (e.g. `allenai/OLMo-2-1124-7B`, `mistralai/Mistral-7B-v0.3`): Run on `A10G` or `L40S` (48GB VRAM).
  - **12B Post-Trained Comparator & Deduped Base** (`OpenAssistant/oasst-sft-1-pythia-12b`, `EleutherAI/pythia-12b-deduped`): Run on `L40S` or `A100-80GB` with adequate memory headroom for half-precision inference.

---

## 3. Running Experiments via Modal

### A. Mock Validation (Zero GPU Cost)
To verify the end-to-end container build and packaging without allocating GPU resources:
```powershell
modal run modal_app.py --model "mock-qwen2.5-3b" --mock True
```
*Note: Mock execution is routed through `run_evaluation_mock_remote` in a CPU-only container without attaching any GPU, ensuring strictly zero GPU compute costs. Real evaluations with `--mock False` route through `run_evaluation_remote` with GPU acceleration.*

### B. Evaluating Pretrained Base Models
Run on-demand evaluation of base checkpoints:
```powershell
# Qwen 2.5 3B Base
modal run modal_app.py --model "Qwen/Qwen2.5-3B" --precision "bfloat16" --mock False

# Pythia 2.8B Base
modal run modal_app.py --model "EleutherAI/pythia-2.8b" --precision "bfloat16" --mock False

# OLMo 2 1B Base
modal run modal_app.py --model "allenai/OLMo-2-1124-1B" --precision "bfloat16" --mock False
```

### C. Running the Pythia-12B SFT Comparator
Run the post-trained comparator (OpenAssistant SFT pinned revision `293df535fe7711a5726987fc2f17dfc87de452a1`):
```powershell
modal run modal_app.py `
    --model "OpenAssistant/oasst-sft-1-pythia-12b" `
    --revision "293df535fe7711a5726987fc2f17dfc87de452a1" `
    --precision "bfloat16" `
    --prompt-mode "openassistant" `
    --mock False
```

---

## 4. Downloading Results to Windows (`G:\llm_cooperation\results`)

To sync the persisted raw results from the Modal volume to your local Windows directory:

```powershell
# Ensure local results directory exists
New-Item -ItemType Directory -Force -Path G:\llm_cooperation\results

# List files in the Modal volume
modal volume ls llm-coop-results

# Download a specific run result
modal volume get llm-coop-results <run_file_name>.jsonl G:\llm_cooperation\results\
```

---

## 5. Local Offline / Non-Modal CLI Execution

The harness remains fully functional without Modal for local execution or GPU environments:

```powershell
# 1. Run local mock test
llm-coop run --model "mock-qwen2.5-3b" --mock -o results

# 2. Analyze individual run
llm-coop analyze results/<run_file>.jsonl -o reports

# 3. Compare multiple models (strictly separating base models from comparators)
llm-coop compare-models results/*.jsonl -o reports

# 4. Audit scenario bank balance and taboo words
llm-coop audit-items
```
