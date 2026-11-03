"""Execution engine for running Phase 0 behavioural evaluations on pretrained LLMs.

Supports:
- Hugging Face transformers with device_map auto, bfloat16/float16
- Tokenizer candidate probing
- Dual evaluation: Next-token logits extraction & normalized conditional probabilities
- Greedy letter-only generation with validation
- Mock execution mode for testing pipelines without downloading multi-gigabyte models
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from llm_cooperation.items.schema import ScenarioBank, StrategyType
from llm_cooperation.items.permutations import (
    Presentation,
    generate_all_presentations,
)
from llm_cooperation.harness.tokenizer_probe import (
    probe_candidate_tokens,
    resolve_candidate_token_ids,
)
from llm_cooperation.harness.scorer import (
    ScoredPresentation,
    ExperimentRunRecord,
)


def get_git_commit() -> Optional[str]:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return res.stdout.strip() if res.returncode == 0 else None
    except Exception:
        return None


def parse_generated_letter(raw_text: str) -> Tuple[Optional[str], bool]:
    """Parse a single letter (A, B, C, or D) from raw generated text.

    Strict validation: must start with or isolate A, B, C, or D.
    Rejects ambiguous, multi-letter, or non-choice outputs.
    """
    cleaned = raw_text.strip()
    if not cleaned:
        return None, False

    # Check for direct single letter
    if cleaned in ["A", "B", "C", "D"]:
        return cleaned, True

    # Check first character if followed by punct or space e.g. "A." or "B\n"
    match = re.match(r"^([ABCD])[\.\,\s\:\)]", cleaned)
    if match:
        return match.group(1), True

    # If the text is e.g. " A", return it
    if len(cleaned) == 1 and cleaned.upper() in ["A", "B", "C", "D"]:
        return cleaned.upper(), True

    return None, False


class ModelRunner:
    def __init__(
        self,
        model_name: str,
        revision: Optional[str] = None,
        precision: str = "bfloat16",
        device: str = "auto",
        mock: bool = False,
        seed: int = 42,
    ):
        self.model_name = model_name
        self.revision = revision
        self.precision = precision
        self.device = device
        self.mock = mock
        self.seed = seed

        self.model = None
        self.tokenizer = None
        self.candidate_token_ids = {}

        if not self.mock:
            self._load_model()
        else:
            self._setup_mock()

    def _load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"[ModelRunner] Loading tokenizer for {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            revision=self.revision,
            trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Resolve candidate token IDs
        self.candidate_token_ids = resolve_candidate_token_ids(self.tokenizer)
        print(f"[ModelRunner] Candidate token IDs: {self.candidate_token_ids}")

        torch_dtype = torch.bfloat16 if self.precision == "bfloat16" else torch.float16
        print(f"[ModelRunner] Loading model {self.model_name} (dtype={torch_dtype}, device={self.device})...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            revision=self.revision,
            torch_dtype=torch_dtype,
            device_map=self.device,
            trust_remote_code=True,
        )
        self.model.eval()

    def _setup_mock(self):
        # Mock token IDs for A, B, C, D
        self.candidate_token_ids = {"A": 100, "B": 101, "C": 102, "D": 103}
        np.random.seed(self.seed)

    def evaluate_presentation(self, presentation: Presentation, scenario_meta: Dict) -> ScoredPresentation:
        t0 = time.time()
        prompt = presentation.prompt_text

        if self.mock:
            # Generate reproducible mock logits and generation
            # Slightly bias towards COOPERATE in neutral/costless context to mirror exploratory hypothesis
            strat_boost = {
                StrategyType.COOPERATE: 0.4 if scenario_meta["context_type"] == "neutral_or_costless" else 0.0,
                StrategyType.INDEPENDENT: 0.1,
                StrategyType.COMPETE_EXPLOIT: -0.1,
                StrategyType.DISENGAGE: -0.2,
            }
            raw_logits = {}
            for letter in ["A", "B", "C", "D"]:
                st = presentation.letter_to_strategy[letter]
                # base random normal + strategy effect
                val = float(np.random.normal(5.0, 0.5) + strat_boost.get(st, 0.0))
                raw_logits[letter] = val

            # Compute logprobs and normalized conditional probabilities
            max_l = max(raw_logits.values())
            exp_vals = {k: np.exp(v - max_l) for k, v in raw_logits.items()}
            sum_exp = sum(exp_vals.values())
            cond_probs = {k: float(v / sum_exp) for k, v in exp_vals.items()}
            raw_logprobs = {k: float(np.log(v)) for k, v in cond_probs.items()}

            argmax_letter = max(cond_probs, key=cond_probs.get)
            argmax_strategy = presentation.letter_to_strategy[argmax_letter]

            # Mock generation: usually outputs argmax letter cleanly
            generated_raw = f" {argmax_letter}"
            gen_letter, is_valid = parse_generated_letter(generated_raw)
            gen_strat = presentation.letter_to_strategy.get(gen_letter) if is_valid else None

            elapsed = time.time() - t0
            return ScoredPresentation(
                presentation_id=presentation.presentation_id,
                scenario_id=presentation.scenario_id,
                permutation_index=presentation.permutation_index,
                partner_type=scenario_meta["partner_type"],
                context_type=scenario_meta["context_type"],
                letter_to_strategy=presentation.letter_to_strategy,
                strategy_to_letter=presentation.strategy_to_letter,
                candidate_tokens=self.candidate_token_ids,
                raw_logits=raw_logits,
                raw_logprobs=raw_logprobs,
                conditional_probs=cond_probs,
                forced_choice_argmax_letter=argmax_letter,
                forced_choice_argmax_strategy=argmax_strategy,
                generated_raw_text=generated_raw,
                generated_letter=gen_letter,
                is_valid_letter=is_valid,
                generated_strategy=gen_strat,
                elapsed_seconds=elapsed,
            )

        # Real model inference
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        input_ids = inputs["input_ids"]

        with torch.no_grad():
            outputs = self.model(input_ids)
            # Logits for next token (immediately after "Answer:")
            next_token_logits = outputs.logits[0, -1, :]

            # Extract raw logits for candidate tokens
            raw_logits = {}
            for letter, token_id in self.candidate_token_ids.items():
                raw_logits[letter] = float(next_token_logits[token_id].item())

            # Normalized conditional softmax across A, B, C, D
            cand_tensor = torch.tensor([raw_logits[l] for l in ["A", "B", "C", "D"]])
            cond_prob_tensor = torch.softmax(cand_tensor, dim=0)
            logprob_tensor = torch.log_softmax(cand_tensor, dim=0)

            cond_probs = {l: float(cond_prob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}
            raw_logprobs = {l: float(logprob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}

            argmax_letter = max(cond_probs, key=cond_probs.get)
            argmax_strategy = presentation.letter_to_strategy[argmax_letter]

            # Greedy generation: generate up to 5 new tokens to inspect response compliance
            gen_output = self.model.generate(
                input_ids,
                max_new_tokens=5,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
            )
            new_tokens = gen_output[0][input_ids.shape[1]:]
            generated_raw = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            gen_letter, is_valid = parse_generated_letter(generated_raw)
            gen_strat = presentation.letter_to_strategy.get(gen_letter) if is_valid else None

        elapsed = time.time() - t0
        return ScoredPresentation(
            presentation_id=presentation.presentation_id,
            scenario_id=presentation.scenario_id,
            permutation_index=presentation.permutation_index,
            partner_type=scenario_meta["partner_type"],
            context_type=scenario_meta["context_type"],
            letter_to_strategy=presentation.letter_to_strategy,
            strategy_to_letter=presentation.strategy_to_letter,
            candidate_tokens=self.candidate_token_ids,
            raw_logits=raw_logits,
            raw_logprobs=raw_logprobs,
            conditional_probs=cond_probs,
            forced_choice_argmax_letter=argmax_letter,
            forced_choice_argmax_strategy=argmax_strategy,
            generated_raw_text=generated_raw,
            generated_letter=gen_letter,
            is_valid_letter=is_valid,
            generated_strategy=gen_strat,
            elapsed_seconds=elapsed,
        )


def run_experiment(
    model_name: str,
    scenarios_path: str = "data/scenarios.json",
    output_dir: str = "results",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
) -> Path:
    """Run full Phase 0 evaluation of all 96 presentations on a specified model."""
    os.makedirs(output_dir, exist_ok=True)
    with open(scenarios_path, "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    bank = ScenarioBank(**bank_data)
    scenarios = bank.scenarios
    scenario_meta_map = {
        s.id: {"partner_type": s.partner_type.value, "context_type": s.context_type.value}
        for s in scenarios
    }

    presentations = generate_all_presentations(scenarios)

    runner = ModelRunner(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
    )

    scored_records: List[ScoredPresentation] = []
    print(f"[run_experiment] Running {len(presentations)} presentations on {model_name} (mock={mock})...")

    for i, pres in enumerate(presentations, 1):
        meta = scenario_meta_map[pres.scenario_id]
        rec = runner.evaluate_presentation(pres, meta)
        scored_records.append(rec)
        if i % 16 == 0 or i == len(presentations):
            print(f"  Processed {i}/{len(presentations)} presentations...")

    safe_name = model_name.replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"run_{safe_name}_{ts}.jsonl"
    out_path = Path(output_dir) / filename

    run_record = ExperimentRunRecord(
        model_name=model_name,
        model_revision=revision,
        timestamp=datetime.now(timezone.utc).isoformat(),
        device=device,
        precision=precision,
        git_commit=get_git_commit(),
        num_scenarios=len(scenarios),
        num_presentations=len(scored_records),
        records=scored_records,
    )

    with open(out_path, "w", encoding="utf-8") as f:
        # Write metadata header as first line
        f.write(json.dumps(run_record.model_dump(exclude={"records"})) + "\n")
        # Write individual records
        for r in scored_records:
            f.write(json.dumps(r.model_dump()) + "\n")

    print(f"[run_experiment] Completed successfully! Saved raw results to {out_path}")
    return out_path
