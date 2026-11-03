"""Result models and scoring utilities for experimental outputs."""

from typing import Dict, List, Optional
from pydantic import BaseModel
from llm_cooperation.items.schema import StrategyType


class ScoredPresentation(BaseModel):
    presentation_id: str
    scenario_id: str
    permutation_index: int
    partner_type: str
    context_type: str

    # Strategy mappings for this presentation
    letter_to_strategy: Dict[str, StrategyType]
    strategy_to_letter: Dict[StrategyType, str]

    # Token-level forced choice measurement
    candidate_tokens: Dict[str, int]
    raw_logits: Dict[str, float]  # raw unnormalized logits
    full_vocab_logprobs: Optional[Dict[str, float]] = None  # log_softmax across all vocab tokens
    conditional_logprobs: Dict[str, float]  # log_softmax restricted to {A, B, C, D}
    raw_logprobs: Dict[str, float]  # backwards-compatible alias to conditional_logprobs
    conditional_probs: Dict[str, float]  # normalized softmax across A, B, C, D (sum = 1.0)
    forced_choice_argmax_letter: str
    forced_choice_argmax_strategy: StrategyType

    # Separately generated completion
    generated_raw_text: str
    generated_letter: Optional[str] = None
    is_valid_letter: bool = False
    generated_strategy: Optional[StrategyType] = None

    # Latency / timing
    elapsed_seconds: float = 0.0


class ExperimentRunRecord(BaseModel):
    run_id: str
    model_name: str
    model_revision: Optional[str] = None
    tokenizer_revision: Optional[str] = None
    model_class: Optional[str] = None
    timestamp: str
    device: str
    precision: str  # alias for effective_precision
    requested_precision: str
    effective_precision: str
    mock: bool = False
    git_commit: Optional[str] = None
    scenario_bank_hash: Optional[str] = None
    permutation_schedule: str = "latin_square_4x4_v1"
    seed: int = 42
    torch_version: Optional[str] = None
    transformers_version: Optional[str] = None
    modal_version: Optional[str] = None
    prompt_mode: str = "standard_plaintext"
    num_scenarios: int
    num_presentations: int
    records: List[ScoredPresentation]
