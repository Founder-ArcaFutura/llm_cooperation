# Option-order comparison

| Model | Schedule | Equal-utility C-I | Coop at A/B/C/D | All-four COOP scenarios | Full-range coop slope | Calibration accuracy / format |
|---|---|---:|---|---:|---:|---|
| Qwen/Qwen2.5-3B | 0 | +0.583 | 40.5%/99.2%/96.8%/54.8% | 29/126 | +0.133 | 91.7% / 50.0% |
| Qwen/Qwen2.5-3B | 1 | +0.625 | 65.1%/100.0%/99.2%/50.0% | 51/126 | +0.096 | 94.8% / 53.1% |
| Qwen/Qwen2.5-3B | 2 | +0.458 | 70.6%/99.2%/76.2%/45.2% | 40/126 | +0.102 | 91.7% / 46.9% |
| mistralai/Mistral-7B-v0.3 | 0 | +0.854 | 100.0%/93.7%/85.7%/98.4% | 106/126 | -0.019 | 90.6% / 2.1% |
| mistralai/Mistral-7B-v0.3 | 1 | +0.833 | 96.0%/73.0%/91.3%/99.2% | 92/126 | +0.061 | 89.6% / 0.0% |
| mistralai/Mistral-7B-v0.3 | 2 | +0.583 | 88.9%/78.6%/81.0%/89.7% | 95/126 | +0.000 | 83.3% / 3.1% |
| allenai/OLMo-2-1124-7B | 0 | +0.562 | 73.0%/69.8%/92.1%/73.0% | 66/126 | +0.237 | 82.3% / 0.0% |
| allenai/OLMo-2-1124-7B | 1 | +0.625 | 79.4%/86.5%/93.7%/42.9% | 40/126 | +0.138 | 89.6% / 0.0% |
| allenai/OLMo-2-1124-7B | 2 | +0.562 | 78.6%/79.4%/73.8%/76.2% | 72/126 | +0.233 | 79.2% / 0.0% |
| HuggingFaceTB/SmolLM2-1.7B | 0 | +0.188 | 80.2%/2.4%/29.4%/49.2% | 3/126 | +0.064 | 67.7% / 0.0% |
| HuggingFaceTB/SmolLM2-1.7B | 1 | +0.167 | 78.6%/27.8%/42.9%/44.4% | 19/126 | +0.057 | 68.8% / 0.0% |
| HuggingFaceTB/SmolLM2-1.7B | 2 | +0.167 | 78.6%/31.0%/40.5%/33.3% | 7/126 | +0.039 | 71.9% / 0.0% |
| ibm-granite/granite-3.3-2b-base | 0 | +0.875 | 89.7%/94.4%/83.3%/90.5% | 90/126 | +0.171 | 76.0% / 28.1% |
| ibm-granite/granite-3.3-2b-base | 1 | +0.917 | 90.5%/92.9%/69.8%/95.2% | 77/126 | +0.131 | 80.2% / 26.0% |
| ibm-granite/granite-3.3-2b-base | 2 | +0.896 | 92.1%/98.4%/72.2%/93.7% | 81/126 | +0.158 | 72.9% / 26.0% |
| tiiuae/Falcon3-3B-Base | 0 | +0.562 | 100.0%/86.5%/66.7%/42.9% | 48/126 | +0.030 | 91.7% / 0.0% |
| tiiuae/Falcon3-3B-Base | 1 | +0.583 | 100.0%/69.0%/63.5%/53.2% | 40/126 | +0.151 | 93.8% / 0.0% |
| tiiuae/Falcon3-3B-Base | 2 | +0.604 | 99.2%/73.8%/68.3%/58.7% | 56/126 | +0.116 | 91.7% / 0.0% |
| Qwen/Qwen2.5-1.5B | 0 | +1.000 | 92.1%/98.4%/89.7%/96.0% | 104/126 | +0.135 | 94.8% / 100.0% |
| Qwen/Qwen2.5-1.5B | 1 | +0.875 | 90.5%/98.4%/98.4%/86.5% | 108/126 | +0.035 | 93.8% / 100.0% |
| Qwen/Qwen2.5-1.5B | 2 | +0.708 | 92.9%/98.4%/85.7%/81.7% | 99/126 | +0.021 | 93.8% / 100.0% |
| Qwen/Qwen2.5-7B | 0 | +0.750 | 54.8%/97.6%/100.0%/99.2% | 69/126 | +0.109 | 91.7% / 52.1% |
| Qwen/Qwen2.5-7B | 1 | +0.625 | 76.2%/100.0%/99.2%/81.0% | 89/126 | +0.034 | 91.7% / 52.1% |
| Qwen/Qwen2.5-7B | 2 | +0.458 | 76.2%/99.2%/80.2%/84.9% | 89/126 | +0.030 | 92.7% / 50.0% |
| deepseek-ai/deepseek-llm-7b-base | 0 | +0.104 | 99.2%/59.5%/15.9%/23.8% | 12/126 | +0.066 | 68.8% / 4.2% |
| deepseek-ai/deepseek-llm-7b-base | 1 | +0.083 | 98.4%/41.3%/42.9%/15.1% | 6/126 | +0.039 | 71.9% / 4.2% |
| deepseek-ai/deepseek-llm-7b-base | 2 | +0.188 | 99.2%/46.8%/3.2%/30.2% | 3/126 | +0.033 | 70.8% / 5.2% |
| microsoft/phi-2 | 0 | +0.625 | 99.2%/96.8%/69.8%/52.4% | 63/126 | +0.025 | 88.5% / 41.7% |
| microsoft/phi-2 | 1 | +0.479 | 83.3%/88.9%/73.8%/46.8% | 52/126 | +0.038 | 87.5% / 43.8% |
| microsoft/phi-2 | 2 | +0.583 | 99.2%/92.1%/63.5%/54.0% | 64/126 | +0.077 | 86.5% / 41.7% |
| meta-llama/Llama-3.2-3B | 0 | +0.833 | 96.8%/71.4%/81.7%/87.3% | 67/126 | +0.181 | 74.0% / 95.8% |
| meta-llama/Llama-3.2-3B | 1 | +0.771 | 77.8%/79.4%/91.3%/87.3% | 62/126 | +0.147 | 74.0% / 95.8% |
| meta-llama/Llama-3.2-3B | 2 | +0.375 | 51.6%/84.9%/95.2%/72.2% | 34/126 | +0.090 | 71.9% / 94.8% |
| google/gemma-2-2b | 0 | +0.167 | 98.4%/29.4%/0.0%/19.0% | 0/126 | +0.013 | 30.2% / 0.0% |
| google/gemma-2-2b | 1 | +0.146 | 92.1%/24.6%/0.8%/23.8% | 0/126 | +0.060 | 29.2% / 0.0% |
| google/gemma-2-2b | 2 | +0.146 | 96.8%/26.2%/0.0%/27.0% | 0/126 | +0.014 | 29.2% / 0.0% |
| google/gemma-2-9b | 0 | +1.000 | 76.2%/98.4%/88.9%/98.4% | 87/126 | +0.208 | 91.7% / 0.0% |
| google/gemma-2-9b | 1 | +0.833 | 69.0%/92.1%/98.4%/99.2% | 85/126 | +0.181 | 90.6% / 0.0% |
| google/gemma-2-9b | 2 | +0.750 | 60.3%/97.6%/96.8%/97.6% | 73/126 | +0.138 | 89.6% / 0.0% |

Schedule 0 is the original baseline. Dose curves, family slopes and paired main-sweep changes with six-family bootstrap intervals are in comparison.json. All slopes and resamples use the same full observed dose range. Calibration options also change across schedules; words/payoffs remain fixed. These are paired order perturbations, not independent model training replications. Flat, reversed and unstable effects must be retained. Stability does not establish numerical payoff reasoning. No extrapolated crossover is treated as observed.
