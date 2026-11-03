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
    raw_logits: Dict[str, float]
    raw_logprobs: Dict[str, float]
    conditional_probs: Dict[str, float]  # normalized across A, B, C, D
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
    model_name: str
    model_revision: Optional[str] = None
    timestamp: str
    device: str
    precision: str
    git_commit: Optional[str] = None
    num_scenarios: int
    num_presentations: int
    records: List[ScoredPresentation]
