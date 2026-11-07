"""Pydantic schemas and definitions for the cooperation experiment items."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class PartnerType(str, Enum):
    HUMAN = "human"
    AI = "ai"


class ContextType(str, Enum):
    NEUTRAL_OR_COSTLESS = "neutral_or_costless"
    MODEST_COST = "modest_cost"
    CONFLICT_WITH_OBJECTIVE = "conflict_with_objective"
    INEFFECTIVE_OR_INAPPROPRIATE = "ineffective_or_inappropriate"


class UtilityCondition(str, Enum):
    EQUAL_UTILITY = "equal_utility"
    COOP_ADVANTAGEOUS = "coop_advantageous"
    COOP_DISADVANTAGEOUS = "coop_disadvantageous"


class StrategyType(str, Enum):
    COOPERATE = "COOPERATE"
    INDEPENDENT = "INDEPENDENT"
    COMPETE_EXPLOIT = "COMPETE_EXPLOIT"
    DISENGAGE = "DISENGAGE"


class ScenarioOption(BaseModel):
    strategy: StrategyType = Field(..., description="The underlying semantic strategy.")
    text: str = Field(..., min_length=5, description="The neutral option description shown to the model.")


class Scenario(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. scenario_01")
    partner_type: PartnerType
    context_type: ContextType
    title: str
    stem: str = Field(..., min_length=20, description="The situational prompt stem.")
    options: Dict[StrategyType, str] = Field(..., description="Mapping of strategy to option text.")
    # Optional extensions for expanded bank
    template_id: Optional[str] = Field(None, description="Shared template ID for matched human/AI pair, e.g. template_001")
    template_family_id: Optional[str] = Field(None, description="Stable scenario-family ID shared across payoff tiers and factorial variants")
    split: Optional[str] = Field(None, description="Dataset split: 'exploratory' or 'confirmatory'")
    domain: Optional[str] = Field(None, description="Substantive scenario domain classification")
    utility_condition: Optional[UtilityCondition] = Field(None, description="Phase 0B utility condition: equal_utility, coop_advantageous, coop_disadvantageous")
    source_type: Optional[str] = Field(None, description="Phase 0B template provenance: 'reused', 'new', or 'control'")
    triad_id: Optional[str] = Field(None, description="Shared identifier for matched sensitivity triad situations")
    is_symmetric_control: Optional[bool] = Field(False, description="Flag for control items matching both actor and partner outcomes under coop vs indep")
    payoff_spec: Optional[Dict[str, Dict[str, str]]] = Field(None, description="Objectively specified payoffs/costs for each strategy (success, time, cost, risk, actor_payoff, partner_payoff)")

    @model_validator(mode="after")
    def validate_options(self) -> "Scenario":
        required = {
            StrategyType.COOPERATE,
            StrategyType.INDEPENDENT,
            StrategyType.COMPETE_EXPLOIT,
            StrategyType.DISENGAGE,
        }
        if set(self.options.keys()) != required:
            raise ValueError(f"Scenario {self.id} must have exactly all 4 strategies: {required}")
        return self


class ScenarioBank(BaseModel):
    version: str = "0.2.0"
    status: Optional[str] = Field("frozen", description="Status of the bank, e.g. frozen or pending_human_scientific_review")
    description: str
    split_assignment_method: Optional[str] = None
    split_manifest: Optional[Dict[str, List[str]]] = None
    author_metadata: Optional[Dict[str, str]] = None
    scenarios: List[Scenario]


class CalibrationItem(BaseModel):
    id: str = Field(..., description="Unique identifier for diagnostic calibration item, e.g. calib_01")
    domain: str = Field(..., description="General domain, e.g. arithmetic, science, facts, reasoning")
    stem: str = Field(..., min_length=10, description="Stem text formulating an objective question.")
    options: Dict[str, str] = Field(..., description="Mapping of invariant option IDs (e.g. opt_1, opt_2, opt_3, opt_4) to text.")
    correct_option_id: str = Field(..., description="Invariant option ID that is objectively correct.")
    difficulty: str = Field("elementary", description="Difficulty tier: elementary, intermediate")

    @model_validator(mode="after")
    def validate_calibration_item(self) -> "CalibrationItem":
        if len(self.options) != 4:
            raise ValueError(f"Calibration item {self.id} must have exactly 4 options, got {len(self.options)}")
        if self.correct_option_id not in self.options:
            raise ValueError(f"Calibration item {self.id} correct_option_id '{self.correct_option_id}' not found in options {list(self.options.keys())}")
        return self


class CalibrationBank(BaseModel):
    version: str = "1.0.0"
    status: str = "frozen"
    description: str
    items: List[CalibrationItem]
