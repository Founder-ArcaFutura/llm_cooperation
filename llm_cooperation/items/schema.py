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
    description: str
    scenarios: List[Scenario]
