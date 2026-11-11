"""Pydantic result models for continuation-likelihood scoring."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from llm_cooperation.items.schema import StrategyType


class TokenScoreDetail(BaseModel):
    """Log-probability detail for a single continuation token."""
    token_id: int
    token_str: str
    log_prob: float
    position: int  # 0-indexed position within continuation


class CandidateScoreResult(BaseModel):
    """Full scoring result for a single candidate action continuation."""
    # Identity
    scenario_id: str
    strategy: StrategyType
    template_id: str
    candidate_wording_id: str  # "original" or paraphrase variant ID

    # Prompt structure
    prefix_text: str       # scenario stem + connector phrase
    continuation_text: str # the action description being scored

    # Token boundary audit
    num_prefix_tokens: int
    num_continuation_tokens: int
    # Whether boundary was verified (prefix tokens identical in joint encoding)
    boundary_verified: bool
    boundary_warning: Optional[str] = None

    # Primary scores
    sum_log_prob: float
    mean_log_prob: float
    num_scored_tokens: int

    # Token-level detail
    token_details: List[TokenScoreDetail]

    # Provenance
    model_name: str
    model_revision: Optional[str] = None
    precision: str
    elapsed_seconds: float = 0.0


class ScenarioContinuationResult(BaseModel):
    """All candidate scores for one (scenario, template, wording) combination."""
    scenario_id: str
    partner_type: str
    context_type: str
    template_id: str
    candidate_wording_id: str
    domain: Optional[str] = None
    split: Optional[str] = None
    source_type: Optional[str] = None

    # Strategy -> score mapping for this presentation
    scores: Dict[str, CandidateScoreResult]  # key = strategy value string

    # Computed rankings
    rank_by_sum: Dict[str, int]      # strategy -> rank (1=best)
    rank_by_mean: Dict[str, int]     # strategy -> rank (1=best)

    # Cooperation margins
    coop_vs_independent_sum_delta: Optional[float] = None
    coop_vs_compete_sum_delta: Optional[float] = None
    coop_rank_by_sum: int = 0
    coop_rank_by_mean: int = 0

    # Whether cooperation ranks first under any scoring method
    coop_first_by_sum: bool = False
    coop_first_by_mean: bool = False


class ControlScoreResult(BaseModel):
    """Score of a candidate action under a control (mismatched) context."""
    scenario_id: str
    control_scenario_id: str
    strategy: StrategyType
    template_id: str
    candidate_wording_id: str
    # log P(a | s_control)
    control_sum_log_prob: float
    control_mean_log_prob: float
    # Contextual association: log P(a|s) - log P(a|s_control)
    delta_sum: Optional[float] = None   # requires matched target score
    delta_mean: Optional[float] = None


class ContinuationRunRecord(BaseModel):
    """Full provenance record for a continuation-likelihood run."""
    run_id: str
    assay_type: str = "continuation_likelihood"
    research_status: str = "exploratory"  # Always exploratory

    model_name: str
    model_revision: Optional[str] = None
    model_class: Optional[str] = None
    tokenizer_name: Optional[str] = None
    effective_precision: str
    requested_precision: str

    timestamp: str
    git_commit: Optional[str] = None
    torch_version: Optional[str] = None
    transformers_version: Optional[str] = None

    scenario_bank: str
    scenario_bank_hash: Optional[str] = None
    num_scenarios: int
    templates_used: List[str]
    wording_variants: List[str]
    include_control_context: bool = False
    control_scenario_id: Optional[str] = None

    # Safety: explicitly document that this is NOT a confirmatory run
    is_confirmatory: bool = False
    authorization_note: str = (
        "Exploratory continuation-likelihood assay. "
        "Not a confirmatory replication. "
        "Phase 1 holdout protections remain in force."
    )

    num_scenario_results: int
    seed: int = 42

    # Raw scored results (one per scenario * template * wording)
    scenario_results: List[ScenarioContinuationResult]
