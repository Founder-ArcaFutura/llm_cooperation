"""Deterministic permutation engine to counterbalance strategy presentation order."""

from typing import Dict, List, Tuple
from pydantic import BaseModel
import hashlib
import itertools
import random
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
# Numerical runtime recorded in all thirteen original real dose-response runs.
ORDER_RUNTIME_V1 = {"torch_version": "2.15.0+cu132", "transformers_version": "5.22.1"}


def counterbalanced_rows(family_id: str, order_replication: int = 0, order_seed: int = 20261107):
    """Select disjoint cyclic orbits, paired across all tiers/partners in a family.

    The 24 possible orders partition into six four-row rotation orbits. Keep
    the historical orbit as baseline; sample two of the other five without
    replacement. This is a coordinated randomized design, not IID replication.
    """
    if order_replication not in (0, 1, 2):
        raise ValueError("order_replication must be 0, 1 or 2")
    if order_replication == 0:
        return [row[:] for row in LATIN_SQUARE_4X4]
    digest = hashlib.sha256(f"order_orbits_v1|{order_seed}|{family_id}".encode()).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    # Fix COOPERATE first to enumerate each rotational equivalence class once.
    representatives = [(0,) + p for p in itertools.permutations((1, 2, 3)) if p != (1, 2, 3)]
    rng.shuffle(representatives)
    base = representatives[order_replication - 1]
    rows = [list(base[i:] + base[:i]) for i in range(4)]
    rng.shuffle(rows)
    return rows


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


def build_presentation_prompt(
    stem: str,
    letter_options: List[Tuple[str, str]],
    prompt_mode: str = "standard_plaintext",
) -> str:
    """Format prompt according to specification.

    Supports:
    - standard_plaintext: standard Phase 0 serialization.
    - openassistant: OpenAssistant native special tokens:
      <|prompter|>{stem}\n\n{options}\n\nWhich action would you choose? Answer with only A, B, C, or D.<|endoftext|><|assistant|>Answer:
    """
    options_text = "\n".join([f"{letter}. {text}" for letter, text in letter_options])
    question_text = (
        f"{stem.strip()}\n\n"
        f"{options_text}\n\n"
        f"Which action would you choose? Answer with only A, B, C, or D."
    )

    if prompt_mode == "openassistant":
        return f"<|prompter|>{question_text}<|endoftext|><|assistant|>Answer:"
    else:
        return f"{question_text}\nAnswer:"


def generate_permutations(
    scenario: Scenario,
    prompt_mode: str = "standard_plaintext",
    order_replication: int = 0,
    order_seed: int = 20261107,
) -> List[Presentation]:
    """Generate 4 deterministic counterbalanced presentations for a scenario."""
    presentations = []
    family = scenario.template_family_id or scenario.template_id or scenario.id
    for perm_idx, row in enumerate(counterbalanced_rows(family, order_replication, order_seed)):
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

        prompt = build_presentation_prompt(scenario.stem, letter_options, prompt_mode=prompt_mode)
        pres = Presentation(
            presentation_id=(f"{scenario.id}_p{perm_idx}" if order_replication == 0 else
                             f"{scenario.id}_order{order_replication}_s{order_seed}_p{perm_idx}"),
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


def generate_all_presentations(
    scenarios: List[Scenario],
    prompt_mode: str = "standard_plaintext",
    order_replication: int = 0,
    order_seed: int = 20261107,
) -> List[Presentation]:
    """Generate all presentations for the given scenarios (N scenarios x 4 permutations)."""
    all_pres = []
    for sc in scenarios:
        all_pres.extend(generate_permutations(sc, prompt_mode=prompt_mode,
                                             order_replication=order_replication, order_seed=order_seed))
    return all_pres


class CalibrationPresentationOption(BaseModel):
    letter: str
    option_id: str
    text: str


class CalibrationPresentation(BaseModel):
    presentation_id: str
    item_id: str
    permutation_index: int
    stem: str
    prompt_text: str
    options: List[CalibrationPresentationOption]
    letter_to_option_id: Dict[str, str]
    option_id_to_letter: Dict[str, str]
    correct_option_id: str
    correct_letter: str
    domain: str
    difficulty: str


def build_calibration_presentation_prompt(
    stem: str,
    letter_options: List[Tuple[str, str]],
    prompt_mode: str = "standard_plaintext",
) -> str:
    """Format calibration question prompt according to specification."""
    options_text = "\n".join([f"{letter}. {text}" for letter, text in letter_options])
    question_text = (
        f"{stem.strip()}\n\n"
        f"{options_text}\n\n"
        f"Which answer is correct? Answer with only A, B, C, or D."
    )
    if prompt_mode == "openassistant":
        return f"<|prompter|>{question_text}<|endoftext|><|assistant|>Answer:"
    else:
        return f"{question_text}\nAnswer:"


def generate_calibration_permutations(
    item,
    prompt_mode: str = "standard_plaintext",
    order_replication: int = 0,
    order_seed: int = 20261107,
) -> List[CalibrationPresentation]:
    """Generate 4 deterministic counterbalanced presentations for a calibration item using Latin square."""
    # Deterministic sorted order of invariant option keys (e.g. opt_1, opt_2, opt_3, opt_4)
    sorted_option_ids = sorted(list(item.options.keys()))
    presentations = []
    for perm_idx, row in enumerate(counterbalanced_rows(f"calibration:{item.id}", order_replication, order_seed)):
        letter_options: List[Tuple[str, str]] = []
        presentation_opts: List[CalibrationPresentationOption] = []
        letter_to_option_id: Dict[str, str] = {}
        option_id_to_letter: Dict[str, str] = {}

        for col_idx, letter in enumerate(LETTERS):
            opt_idx = row[col_idx]
            opt_id = sorted_option_ids[opt_idx]
            text = item.options[opt_id]

            letter_options.append((letter, text))
            presentation_opts.append(
                CalibrationPresentationOption(letter=letter, option_id=opt_id, text=text)
            )
            letter_to_option_id[letter] = opt_id
            option_id_to_letter[opt_id] = letter

        correct_letter = option_id_to_letter[item.correct_option_id]
        prompt = build_calibration_presentation_prompt(item.stem, letter_options, prompt_mode=prompt_mode)
        pres = CalibrationPresentation(
            presentation_id=(f"{item.id}_p{perm_idx}" if order_replication == 0 else
                             f"{item.id}_order{order_replication}_s{order_seed}_p{perm_idx}"),
            item_id=item.id,
            permutation_index=perm_idx,
            stem=item.stem,
            prompt_text=prompt,
            options=presentation_opts,
            letter_to_option_id=letter_to_option_id,
            option_id_to_letter=option_id_to_letter,
            correct_option_id=item.correct_option_id,
            correct_letter=correct_letter,
            domain=item.domain,
            difficulty=item.difficulty,
        )
        presentations.append(pres)
    return presentations


def generate_all_calibration_presentations(
    items: List,
    prompt_mode: str = "standard_plaintext",
    order_replication: int = 0,
    order_seed: int = 20261107,
) -> List[CalibrationPresentation]:
    """Generate all presentations for diagnostic calibration items (e.g. 24 items x 4 = 96 presentations)."""
    all_pres = []
    for it in items:
        all_pres.extend(generate_calibration_permutations(it, prompt_mode=prompt_mode,
                                                        order_replication=order_replication, order_seed=order_seed))
    return all_pres
