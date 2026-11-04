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
    validate_candidate_tokens_at_boundary,
)
from llm_cooperation.harness.scorer import (
    ScoredPresentation,
    ExperimentRunRecord,
    ScoredCalibrationPresentation,
    CalibrationRunRecord,
)
from llm_cooperation.items.schema import CalibrationBank
from llm_cooperation.items.permutations import (
    CalibrationPresentation,
    generate_all_calibration_presentations,
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

    Strict validation:
    Must strictly be an isolated letter A, B, C, or D, optionally preceded/followed
    by minor whitespace or closing punctuation like 'A.', '(A)', or 'A)'.
    Rejects:
    - Ambiguous multi-choice outputs (e.g. "A or B", "A, B, C, or D", "Neither")
    - Explanations or justification text (e.g. "A is best because...", "B, because...", "A - I choose")
    - Multiple choice letters appearing anywhere in the response
    """
    if not raw_text:
        return None, False

    cleaned = raw_text.strip()
    if not cleaned:
        return None, False

    # Reject if ambiguous multiple candidate letters appear
    candidate_matches = re.findall(r"\b[A-D]\b", cleaned)
    if len(candidate_matches) > 1:
        return None, False

    # Reject words expressing disjunction/alternatives or explanation words
    lowered = cleaned.lower()
    disjunction_patterns = [
        r"\bor\b", r"\band\b", r"\beither\b", r"\bneither\b", r"\bboth\b",
        r"\bbecause\b", r"\bwould\b", r"\bchoose\b", r"\boption\b", r"\baction\b",
        r"\bprefer\b", r"\bthink\b", r"\bexplain\b", r"\binstead\b"
    ]
    for pat in disjunction_patterns:
        if re.search(pat, lowered):
            return None, False

    # Accept exact single letter (or whitespace-wrapped)
    if cleaned in ["A", "B", "C", "D"]:
        return cleaned, True

    # Accept standard single letter with simple terminator like "A.", "A)", "(A)", "[A]"
    # Ensure there is NO trailing explanatory text
    match = re.match(r"^(?:\(|\[)?([A-D])(?:\.|\)|\:|\s|\])*$", cleaned)
    if match:
        return match.group(1), True

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
        self.requested_precision = precision
        self.precision = precision
        self.effective_precision = precision
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

    @staticmethod
    def resolve_torch_dtype(precision_str: str):
        import torch
        mapping = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        if precision_str not in mapping:
            raise ValueError(f"Unsupported precision '{precision_str}'. Must be one of {list(mapping.keys())}")
        return mapping[precision_str]

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
        # Validate candidate tokens against the standard prompt boundary "Answer:"
        self.candidate_token_ids = resolve_candidate_token_ids(
            self.tokenizer,
            prompt_ends_with_space=False,
            sample_prompt="Answer:"
        )
        print(f"[ModelRunner] Validated candidate token IDs at prompt boundary: {self.candidate_token_ids}")

        torch_dtype = self.resolve_torch_dtype(self.requested_precision)
        print(f"[ModelRunner] Loading model {self.model_name} (requested_dtype={torch_dtype}, device={self.device})...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            revision=self.revision,
            torch_dtype=torch_dtype,
            device_map=self.device,
            trust_remote_code=True,
        )
        self.model.eval()
        # Record effective loaded numerical dtype
        self.effective_precision = str(self.model.dtype).replace("torch.", "")

    def validate_presentation_boundaries(self, presentations: List[Presentation]):
        """Validate candidate tokenization at the actual rendered prompt boundary for every presentation.

        Runs as a lightweight tokenizer-only preflight before model inference to ensure
        all 96 presentations strictly conform to single-token continuation without retokenization.
        """
        if not self.mock and self.tokenizer is not None:
            for p in presentations:
                validate_candidate_tokens_at_boundary(
                    self.tokenizer,
                    p.prompt_text,
                    self.candidate_token_ids,
                )

    def _setup_mock(self):
        # Mock token IDs for A, B, C, D
        self.candidate_token_ids = {"A": 100, "B": 101, "C": 102, "D": 103}
        self.effective_precision = self.requested_precision
        np.random.seed(self.seed)

    def evaluate_calibration_presentation(self, pres: CalibrationPresentation) -> ScoredCalibrationPresentation:
        t0 = time.time()
        prompt = pres.prompt_text

        if self.mock:
            # Deterministic mock behaviour based on model name
            # If model name contains "pythia" or "invariant_a", simulate Pythia-style invariant-A pathology!
            if "pythia" in self.model_name.lower() or "invariant_a" in self.model_name.lower():
                raw_logits = {"A": 10.0, "B": 2.0, "C": 2.0, "D": 2.0}
                cond_probs = {"A": 0.999, "B": 0.0003, "C": 0.0003, "D": 0.0003}
                cond_logprobs = {"A": -0.001, "B": -8.0, "C": -8.0, "D": -8.0}
                full_vocab_logprobs = {k: v - 12.0 for k, v in cond_logprobs.items()}
                argmax_letter = "A"
                # Pythia-style non-compliant output or repeating A
                generated_raw = "A\n\nQuestion:"
                gen_letter, is_valid = parse_generated_letter(generated_raw)
            else:
                # Normal mock model that achieves high accuracy on calibration
                raw_logits = {}
                for letter in ["A", "B", "C", "D"]:
                    bonus = 3.0 if letter == pres.correct_letter else 0.0
                    raw_logits[letter] = float(np.random.normal(5.0, 0.4) + bonus)
                max_l = max(raw_logits.values())
                exp_vals = {k: np.exp(v - max_l) for k, v in raw_logits.items()}
                sum_exp = sum(exp_vals.values())
                cond_probs = {k: float(v / sum_exp) for k, v in exp_vals.items()}
                cond_logprobs = {k: float(np.log(v)) for k, v in cond_probs.items()}
                full_vocab_logprobs = {k: float(v - 12.0) for k, v in cond_logprobs.items()}
                argmax_letter = max(cond_probs, key=cond_probs.get)
                generated_raw = f" {argmax_letter}"
                gen_letter, is_valid = parse_generated_letter(generated_raw)

            fc_correct = (argmax_letter == pres.correct_letter)
            gen_correct = (gen_letter == pres.correct_letter) if is_valid else False
            agreement = (argmax_letter == gen_letter) if is_valid else False
            elapsed = time.time() - t0

            return ScoredCalibrationPresentation(
                presentation_id=pres.presentation_id,
                item_id=pres.item_id,
                permutation_index=pres.permutation_index,
                domain=pres.domain,
                difficulty=pres.difficulty,
                correct_option_id=pres.correct_option_id,
                correct_letter=pres.correct_letter,
                letter_to_option_id=pres.letter_to_option_id,
                option_id_to_letter=pres.option_id_to_letter,
                candidate_tokens=self.candidate_token_ids,
                raw_logits=raw_logits,
                full_vocab_logprobs=full_vocab_logprobs,
                conditional_logprobs=cond_logprobs,
                conditional_probs=cond_probs,
                forced_choice_argmax_letter=argmax_letter,
                is_forced_choice_correct=fc_correct,
                generated_raw_text=generated_raw,
                generated_letter=gen_letter,
                is_valid_letter=is_valid,
                is_generated_correct=gen_correct,
                forced_generated_agreement=agreement,
                elapsed_seconds=elapsed,
            )

        # Real model execution
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        input_ids = inputs["input_ids"]

        with torch.no_grad():
            outputs = self.model(input_ids)
            next_token_logits = outputs.logits[0, -1, :]

            full_vocab_log_softmax = torch.log_softmax(next_token_logits, dim=-1)
            full_vocab_logprobs = {
                letter: float(full_vocab_log_softmax[token_id].item())
                for letter, token_id in self.candidate_token_ids.items()
            }

            raw_logits = {}
            for letter, token_id in self.candidate_token_ids.items():
                raw_logits[letter] = float(next_token_logits[token_id].item())

            cand_tensor = torch.tensor([raw_logits[l] for l in ["A", "B", "C", "D"]])
            cond_prob_tensor = torch.softmax(cand_tensor, dim=0)
            cond_logprob_tensor = torch.log_softmax(cand_tensor, dim=0)

            cond_probs = {l: float(cond_prob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}
            cond_logprobs = {l: float(cond_logprob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}

            argmax_letter = max(cond_probs, key=cond_probs.get)

            gen_output = self.model.generate(
                input_ids,
                max_new_tokens=5,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
            )
            new_tokens = gen_output[0][input_ids.shape[1]:]
            generated_raw = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            gen_letter, is_valid = parse_generated_letter(generated_raw)

        fc_correct = (argmax_letter == pres.correct_letter)
        gen_correct = (gen_letter == pres.correct_letter) if is_valid else False
        agreement = (argmax_letter == gen_letter) if is_valid else False
        elapsed = time.time() - t0

        return ScoredCalibrationPresentation(
            presentation_id=pres.presentation_id,
            item_id=pres.item_id,
            permutation_index=pres.permutation_index,
            domain=pres.domain,
            difficulty=pres.difficulty,
            correct_option_id=pres.correct_option_id,
            correct_letter=pres.correct_letter,
            letter_to_option_id=pres.letter_to_option_id,
            option_id_to_letter=pres.option_id_to_letter,
            candidate_tokens=self.candidate_token_ids,
            raw_logits=raw_logits,
            full_vocab_logprobs=full_vocab_logprobs,
            conditional_logprobs=cond_logprobs,
            conditional_probs=cond_probs,
            forced_choice_argmax_letter=argmax_letter,
            is_forced_choice_correct=fc_correct,
            generated_raw_text=generated_raw,
            generated_letter=gen_letter,
            is_valid_letter=is_valid,
            is_generated_correct=gen_correct,
            forced_generated_agreement=agreement,
            elapsed_seconds=elapsed,
        )

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
            cond_logprobs = {k: float(np.log(v)) for k, v in cond_probs.items()}
            # Synthetic full vocab logprobs
            full_vocab_logprobs = {k: float(v - 12.0) for k, v in cond_logprobs.items()}

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
                template_id=scenario_meta.get("template_id"),
                split=scenario_meta.get("split"),
                domain=scenario_meta.get("domain"),
                utility_condition=scenario_meta.get("utility_condition"),
                source_type=scenario_meta.get("source_type"),
                triad_id=scenario_meta.get("triad_id"),
                is_symmetric_control=scenario_meta.get("is_symmetric_control", False),
                permutation_index=presentation.permutation_index,
                partner_type=scenario_meta["partner_type"],
                context_type=scenario_meta["context_type"],
                letter_to_strategy=presentation.letter_to_strategy,
                strategy_to_letter=presentation.strategy_to_letter,
                candidate_tokens=self.candidate_token_ids,
                raw_logits=raw_logits,
                full_vocab_logprobs=full_vocab_logprobs,
                conditional_logprobs=cond_logprobs,
                raw_logprobs=cond_logprobs,
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

            # Full vocabulary log probabilities
            full_vocab_log_softmax = torch.log_softmax(next_token_logits, dim=-1)
            full_vocab_logprobs = {
                letter: float(full_vocab_log_softmax[token_id].item())
                for letter, token_id in self.candidate_token_ids.items()
            }

            # Extract raw logits for candidate tokens
            raw_logits = {}
            for letter, token_id in self.candidate_token_ids.items():
                raw_logits[letter] = float(next_token_logits[token_id].item())

            # Normalized conditional softmax across A, B, C, D
            cand_tensor = torch.tensor([raw_logits[l] for l in ["A", "B", "C", "D"]])
            cond_prob_tensor = torch.softmax(cand_tensor, dim=0)
            cond_logprob_tensor = torch.log_softmax(cand_tensor, dim=0)

            cond_probs = {l: float(cond_prob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}
            cond_logprobs = {l: float(cond_logprob_tensor[i].item()) for i, l in enumerate(["A", "B", "C", "D"])}

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
            template_id=scenario_meta.get("template_id"),
            split=scenario_meta.get("split"),
            domain=scenario_meta.get("domain"),
            utility_condition=scenario_meta.get("utility_condition"),
            source_type=scenario_meta.get("source_type"),
            triad_id=scenario_meta.get("triad_id"),
            is_symmetric_control=scenario_meta.get("is_symmetric_control", False),
            permutation_index=presentation.permutation_index,
            partner_type=scenario_meta["partner_type"],
            context_type=scenario_meta["context_type"],
            letter_to_strategy=presentation.letter_to_strategy,
            strategy_to_letter=presentation.strategy_to_letter,
            candidate_tokens=self.candidate_token_ids,
            raw_logits=raw_logits,
            full_vocab_logprobs=full_vocab_logprobs,
            conditional_logprobs=cond_logprobs,
            raw_logprobs=cond_logprobs,
            conditional_probs=cond_probs,
            forced_choice_argmax_letter=argmax_letter,
            forced_choice_argmax_strategy=argmax_strategy,
            generated_raw_text=generated_raw,
            generated_letter=gen_letter,
            is_valid_letter=is_valid,
            generated_strategy=gen_strat,
            elapsed_seconds=elapsed,
        )


import hashlib

def compute_file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


PHASE1_FREEZE_MANIFEST_PATH = "configs/phase1_freeze_manifest.json"


def verify_phase1_freeze_manifest(scenarios_path: str, manifest_path: Optional[str] = None) -> str:
    """Verify that a trusted, review-approved freeze manifest exists and matches the bank SHA-256 fingerprint.

    Fails closed if the manifest is missing, unapproved, null, or does not match the actual file hash.
    Caller-supplied hashes cannot substitute for or bypass an approved freeze manifest.
    """
    target_manifest = Path(manifest_path or PHASE1_FREEZE_MANIFEST_PATH)
    if not target_manifest.exists():
        raise PermissionError(
            f"PHASE 1 FREEZE MANIFEST MISSING: Trusted freeze manifest not found at '{target_manifest}'. "
            "Phase 1 inference requires an independently approved freeze manifest recording the final frozen bank fingerprint."
        )

    try:
        with open(target_manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Malformed Phase 1 freeze manifest JSON at '{target_manifest}': {e}")

    manifest_status = manifest_data.get("status")
    if manifest_status != "approved_frozen":
        raise PermissionError(
            f"PHASE 1 FREEZE MANIFEST UNAPPROVED: Trusted freeze manifest has status '{manifest_status}'. "
            "Phase 1 inference is strictly prohibited until human semantic adjudication completes and the manifest "
            "status is set to 'approved_frozen' with an approved SHA-256 fingerprint."
        )

    approved_hash = manifest_data.get("approved_frozen_bank_hash")
    if not approved_hash or not isinstance(approved_hash, str) or len(approved_hash) != 64:
        raise PermissionError(
            f"PHASE 1 FREEZE MANIFEST INVALID: Approved frozen bank hash is missing or invalid in '{target_manifest}'. "
            "Inference cannot proceed without an approved freeze fingerprint."
        )

    actual_hash = compute_file_hash(scenarios_path)
    if actual_hash != approved_hash:
        raise ValueError(
            f"PHASE 1 BANK INTEGRITY ERROR: Bank fingerprint mismatch against trusted freeze manifest! "
            f"Approved manifest fingerprint: {approved_hash}, Actual file hash: {actual_hash}. "
            "Inference is aborted."
        )

    return approved_hash


def run_experiment(
    model_name: str,
    scenarios_path: str = "data/scenarios.json",
    output_dir: str = "results",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
    split_filter: Optional[str] = None,
    authorize_phase1_run: bool = False,
    freeze_manifest_path: Optional[str] = None,
) -> Path:
    """Run evaluation of presentations on a specified model."""
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(scenarios_path):
        raise FileNotFoundError(f"Scenario bank file not found: {scenarios_path}")

    try:
        with open(scenarios_path, "r", encoding="utf-8") as f:
            bank_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse scenario bank JSON at {scenarios_path}: {e}")

    try:
        bank = ScenarioBank(**bank_data)
    except Exception as e:
        raise ValueError(f"Malformed scenario bank metadata or schema at {scenarios_path}: {e}")

    # Fail-closed Phase 1 holdout protection guard
    # Detects Phase 1 scenarios via filename, path, template_id prefix, or source_type
    is_phase1 = "phase1" in Path(scenarios_path).name.lower() or any(
        getattr(s, "source_type", None) == "prospective_replication"
        or (s.template_id and s.template_id.startswith("phase1_"))
        or (s.id and s.id.startswith("phase1_"))
        for s in bank.scenarios
    )
    if is_phase1:
        # Require bank status to be exactly 'frozen'
        if bank.status != "frozen":
            raise PermissionError(
                f"PHASE 1 HOLDOUT PROTECTION TRIGGERED: Phase 1 scenario bank must have status exactly 'frozen' "
                f"before inference can be executed (current status: '{bank.status}'). Draft banks ('draft_pending_review') "
                f"or unapproved lifecycle states must remain strictly held out."
            )

        # Require explicit scientific authorization
        env_auth = os.environ.get("ALLOW_PHASE1_RUN", "").lower() in ("1", "true", "yes")
        if not (authorize_phase1_run or env_auth):
            raise PermissionError(
                "PHASE 1 INFERENCE AUTHORIZATION GUARD: Executing inference on the Phase 1 prospective replication bank "
                "requires explicit scientific authorization (--authorize-phase1-run or ALLOW_PHASE1_RUN=true)."
            )

        # Require verification against trusted freeze manifest (cannot be bypassed by caller hash)
        verify_phase1_freeze_manifest(scenarios_path, manifest_path=freeze_manifest_path)

    scenarios = bank.scenarios

    if split_filter:
        scenarios = [s for s in scenarios if getattr(s, "split", None) == split_filter]
        if not scenarios:
            raise ValueError(f"No scenarios found matching split_filter='{split_filter}'")

    scenario_meta_map = {
        s.id: {
            "partner_type": s.partner_type.value,
            "context_type": s.context_type.value,
            "template_id": s.template_id,
            "split": s.split,
            "domain": s.domain,
            "utility_condition": s.utility_condition.value if s.utility_condition else None,
            "source_type": s.source_type,
            "triad_id": getattr(s, "triad_id", None),
            "is_symmetric_control": getattr(s, "is_symmetric_control", False),
        }
        for s in scenarios
    }

    presentations = generate_all_presentations(scenarios, prompt_mode=prompt_mode)

    runner = ModelRunner(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
    )

    # Validate boundary tokenization across all rendered presentation prompts before running
    if presentations and not mock:
        print(f"[run_experiment] Validating candidate tokens at actual rendered presentation boundary for all {len(presentations)} presentations...")
        runner.validate_presentation_boundaries(presentations)

    scored_records: List[ScoredPresentation] = []
    print(f"[run_experiment] Running {len(presentations)} presentations on {model_name} (mock={mock})...")

    for i, pres in enumerate(presentations, 1):
        meta = scenario_meta_map[pres.scenario_id]
        rec = runner.evaluate_presentation(pres, meta)
        scored_records.append(rec)
        if i % 16 == 0 or i == len(presentations):
            print(f"  Processed {i}/{len(presentations)} presentations...")

    import uuid
    safe_name = model_name.replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    entropy = uuid.uuid4().hex[:8]
    run_id = f"run_{safe_name}_{ts}_{entropy}"
    filename = f"{run_id}.jsonl"
    out_path = Path(output_dir) / filename

    import importlib.metadata
    torch_v = None
    transformers_v = None
    modal_v = None
    try:
        import torch
        torch_v = torch.__version__
    except Exception:
        pass
    try:
        import transformers
        transformers_v = transformers.__version__
    except Exception:
        pass
    try:
        import modal
        modal_v = modal.__version__
    except Exception:
        pass

    run_record = ExperimentRunRecord(
        run_id=run_id,
        model_name=model_name,
        model_revision=revision,
        tokenizer_revision=getattr(runner.tokenizer, "init_kwargs", {}).get("revision") if runner.tokenizer else None,
        model_class=runner.model.__class__.__name__ if runner.model else ("MockModel" if mock else None),
        timestamp=datetime.now(timezone.utc).isoformat(),
        device=device,
        precision=runner.effective_precision,
        requested_precision=runner.requested_precision,
        effective_precision=runner.effective_precision,
        mock=mock,
        git_commit=get_git_commit(),
        scenario_bank_hash=compute_file_hash(scenarios_path) if os.path.exists(scenarios_path) else None,
        permutation_schedule="latin_square_4x4_v1",
        seed=seed,
        torch_version=torch_v,
        transformers_version=transformers_v,
        modal_version=modal_v,
        prompt_mode=prompt_mode,
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


def run_calibration(
    model_name: str,
    calibration_path: str = "data/calibration_bank.json",
    output_dir: str = "results",
    revision: Optional[str] = None,
    precision: str = "bfloat16",
    device: str = "auto",
    mock: bool = False,
    seed: int = 42,
    prompt_mode: str = "standard_plaintext",
) -> Tuple[Path, Dict]:
    """Run diagnostic multiple-choice calibration evaluation across 24 objective items (96 presentations)."""
    os.makedirs(output_dir, exist_ok=True)
    with open(calibration_path, "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    bank = CalibrationBank(**bank_data)
    items = bank.items
    presentations = generate_all_calibration_presentations(items, prompt_mode=prompt_mode)

    runner = ModelRunner(
        model_name=model_name,
        revision=revision,
        precision=precision,
        device=device,
        mock=mock,
        seed=seed,
    )

    scored_records: List[ScoredCalibrationPresentation] = []
    print(f"[run_calibration] Running {len(presentations)} calibration presentations on {model_name} (mock={mock})...")

    for i, pres in enumerate(presentations, 1):
        rec = runner.evaluate_calibration_presentation(pres)
        scored_records.append(rec)
        if i % 16 == 0 or i == len(presentations):
            print(f"  Processed {i}/{len(presentations)} calibration presentations...")

    import uuid
    safe_name = model_name.replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    entropy = uuid.uuid4().hex[:8]
    run_id = f"calibration_{safe_name}_{ts}_{entropy}"
    filename = f"{run_id}.jsonl"
    out_path = Path(output_dir) / filename

    import importlib.metadata
    torch_v = None
    transformers_v = None
    modal_v = None
    try:
        import torch
        torch_v = torch.__version__
    except Exception:
        pass
    try:
        import transformers
        transformers_v = transformers.__version__
    except Exception:
        pass
    try:
        import modal
        modal_v = modal.__version__
    except Exception:
        pass

    run_record = CalibrationRunRecord(
        run_id=run_id,
        model_name=model_name,
        model_revision=revision,
        tokenizer_revision=getattr(runner.tokenizer, "init_kwargs", {}).get("revision") if runner.tokenizer else None,
        model_class=runner.model.__class__.__name__ if runner.model else ("MockModel" if mock else None),
        timestamp=datetime.now(timezone.utc).isoformat(),
        device=device,
        precision=runner.effective_precision,
        requested_precision=runner.requested_precision,
        effective_precision=runner.effective_precision,
        mock=mock,
        git_commit=get_git_commit(),
        calibration_bank_hash=compute_file_hash(calibration_path) if os.path.exists(calibration_path) else None,
        seed=seed,
        torch_version=torch_v,
        transformers_version=transformers_v,
        modal_version=modal_v,
        prompt_mode=prompt_mode,
        num_items=len(items),
        num_presentations=len(scored_records),
        records=scored_records,
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(run_record.model_dump(exclude={"records"})) + "\n")
        for r in scored_records:
            f.write(json.dumps(r.model_dump()) + "\n")

    # Compute diagnostic calibration metrics
    n = len(scored_records)
    fc_acc = sum(r.is_forced_choice_correct for r in scored_records) / n if n else 0.0
    valid_rate = sum(r.is_valid_letter for r in scored_records) / n if n else 0.0
    gen_acc = sum(r.is_generated_correct for r in scored_records) / n if n else 0.0
    agreement_rate = sum(r.forced_generated_agreement for r in scored_records) / n if n else 0.0

    letter_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in scored_records:
        letter_counts[r.forced_choice_argmax_letter] = letter_counts.get(r.forced_choice_argmax_letter, 0) + 1
    letter_dist = {k: v / n for k, v in letter_counts.items()} if n else {}

    pos_spread = (max(letter_dist.values()) - min(letter_dist.values())) if letter_dist else 0.0

    # Pythia-style invariant pathology detection
    invariant_a_detected = (letter_dist.get("A", 0.0) >= 0.95)
    invariant_letter_detected = any(v >= 0.95 for v in letter_dist.values())

    status = "PASS"
    failure_reasons = []
    if invariant_letter_detected:
        status = "FAIL_INVARIANT_POSITION"
        failure_reasons.append(f"Model exhibits severe invariant letter bias ({max(letter_dist, key=letter_dist.get)}: {max(letter_dist.values()):.1%}). Pythia-style failure mode detected.")
    if valid_rate < 0.50:
        status = "FAIL_FORMAT_COMPLIANCE"
        failure_reasons.append(f"Generated-letter validity is {valid_rate:.1%} (<50%). Model fails response-format completion.")
    if fc_acc < 0.40 and not invariant_letter_detected:
        status = "FAIL_ACCURACY"
        failure_reasons.append(f"Forced-choice accuracy on elementary factual items is {fc_acc:.1%} (<40%).")

    summary = {
        "model_name": model_name,
        "run_id": run_id,
        "status": status,
        "forced_choice_accuracy": fc_acc,
        "generated_accuracy": gen_acc,
        "valid_letter_rate": valid_rate,
        "forced_generated_agreement": agreement_rate,
        "position_distribution": letter_dist,
        "position_spread": pos_spread,
        "invariant_a_detected": invariant_a_detected,
        "invariant_letter_detected": invariant_letter_detected,
        "failure_reasons": failure_reasons,
        "output_path": str(out_path),
    }

    print(f"[run_calibration] Calibration Status: {status}")
    print(f"  FC Accuracy: {fc_acc:.1%}, Generated Validity: {valid_rate:.1%}, Agreement: {agreement_rate:.1%}")
    print(f"  Letter distribution: A={letter_dist.get('A', 0):.1%}, B={letter_dist.get('B', 0):.1%}, C={letter_dist.get('C', 0):.1%}, D={letter_dist.get('D', 0):.1%}")
    if invariant_a_detected:
        print("  WARNING: Pythia-style invariant-A failure detected!")

    return out_path, summary
