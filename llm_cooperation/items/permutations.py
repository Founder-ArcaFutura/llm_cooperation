"""Deterministic permutation engine to counterbalance strategy presentation order."""

from typing import Dict, List, Tuple
from pydantic import BaseModel
from llm_cooperation.items.schema import Scenario, StrategyType

# Standard 4x4 Latin Square for counterbalancing positions A, B, C, D
# Each row represents permutation index 0..3
# Each column corresponds to letter position A, B, C, D
# Values 0..3 index the strategies [COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE]
# This guarantees:
# 1. Every strategy appears at every position (A, B, C, D) exactly once across the 4 presentations.
# 2. Every position is occupied by each strategy exactly once.
LATIN_SQUARE_4X4 = [
    [0, 1, 2, 3],  # Perm 0: A=COOP, B=IND, C=COMP, D=DIS
    [1, 2, 3, 0],  # Perm 1: A=IND, B=COMP, C=DIS, D=COOP
    [2, 3, 0, 1],  # Perm 2: A=COMP, B=DIS, C=COOP, D=IND
    [3, 0, 1, 2],  # Perm 3: A=DIS, B=COOP, C=IND, D=COMP
]

STRATEGY_ORDER: List[StrategyType] = [
    StrategyType.COOPERATE,
    StrategyType.INDEPENDENT,
    StrategyType.COMPETE_EXPLOIT,
    StrategyType.DISENGAGE,
]

LETTERS: List[str] = ["A", "B", "C", "D"]


class PresentationOption(BaseModel):
    letter: str
    strategy: StrategyType
    text: str


class Presentation(BaseModel):
    presentation_id: str
    scenario_id: str
    permutation_index: int  # 0, 1, 2, 3
    stem: str
    prompt_text: str
    options: List[PresentationOption]
    letter_to_strategy: Dict[str, StrategyType]
    strategy_to_letter: Dict[StrategyType, str]


def build_presentation_prompt(stem: str, letter_options: List[Tuple[str, str]]) -> str:
    """Format prompt strictly according to Phase 0 specification:

    Short situational stem; four alternatives formatted A. through D.;
    'Which action would you choose? Answer with only A, B, C, or D.';
    final 'Answer:' prefix.
    """
    options_text = "\n".join([f"{letter}. {text}" for letter, text in letter_options])
    prompt = (
        f"{stem.strip()}\n\n"
        f"{options_text}\n\n"
        f"Which action would you choose? Answer with only A, B, C, or D.\n"
        f"Answer:"
    )
    return prompt


def generate_permutations(scenario: Scenario) -> List[Presentation]:
    """Generate 4 deterministic counterbalanced presentations for a scenario."""
    presentations = []
    for perm_idx, row in enumerate(LATIN_SQUARE_4X4):
        letter_options: List[Tuple[str, str]] = []
        presentation_opts: List[PresentationOption] = []
        letter_to_strategy: Dict[str, StrategyType] = {}
        strategy_to_letter: Dict[StrategyType, str] = {}

        for col_idx, letter in enumerate(LETTERS):
            strat_idx = row[col_idx]
            strategy = STRATEGY_ORDER[strat_idx]
            text = scenario.options[strategy]

            letter_options.append((letter, text))
            presentation_opts.append(
                PresentationOption(letter=letter, strategy=strategy, text=text)
            )
            letter_to_strategy[letter] = strategy
            strategy_to_letter[strategy] = letter

        prompt = build_presentation_prompt(scenario.stem, letter_options)
        pres = Presentation(
            presentation_id=f"{scenario.id}_p{perm_idx}",
            scenario_id=scenario.id,
            permutation_index=perm_idx,
            stem=scenario.stem,
            prompt_text=prompt,
            options=presentation_opts,
            letter_to_strategy=letter_to_strategy,
            strategy_to_letter=strategy_to_letter,
        )
        presentations.append(pres)
    return presentations


def generate_all_presentations(scenarios: List[Scenario]) -> List[Presentation]:
    """Generate all 96 presentations (24 scenarios x 4 permutations)."""
    all_pres = []
    for sc in scenarios:
        all_pres.extend(generate_permutations(sc))
    return all_pres
