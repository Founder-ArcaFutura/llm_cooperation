"""Controlled strategy banks schema, data structures, and utilities."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from transformers import AutoTokenizer

DEFAULT_TOKENIZER_ID = "Qwen/Qwen2.5-1.5B"
TRAILING_MARKER = "\nDecision:"
STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")
_TOKENIZER_CACHE: Dict[str, Any] = {}


def get_tokenizer(model_id: str = DEFAULT_TOKENIZER_ID):
    if model_id not in _TOKENIZER_CACHE:
        _TOKENIZER_CACHE[model_id] = AutoTokenizer.from_pretrained(model_id)
    return _TOKENIZER_CACHE[model_id]


@dataclass
class ActionMetric:
    strategy: str
    text: str
    token_count: int
    prompt_token_count: int
    word_count: int
    char_count: int


@dataclass
class ScenarioMetrics:
    scenario_id: str
    template_id: str
    actions: Dict[str, ActionMetric]
    min_tokens: int
    max_tokens: int
    token_span: int
    min_prompt_tokens: int
    max_prompt_tokens: int
    prompt_token_span: int


def measure_scenario(
    scenario: Dict[str, Any],
    tokenizer: Optional[Any] = None,
    trailing_marker: str = TRAILING_MARKER,
) -> ScenarioMetrics:
    if tokenizer is None:
        tokenizer = get_tokenizer()
    stem = scenario["stem"].strip()
    actions_metrics: Dict[str, ActionMetric] = {}
    for strat in STRATEGIES:
        act_text = scenario["options"][strat].strip()
        prompt_text = f"{stem}\n\nAction: {act_text}{trailing_marker}"
        act_tokens = len(tokenizer.encode(act_text))
        prompt_tokens = len(tokenizer.encode(prompt_text))
        w_count = len(act_text.split())
        c_count = len(act_text)
        actions_metrics[strat] = ActionMetric(
            strategy=strat,
            text=act_text,
            token_count=act_tokens,
            prompt_token_count=prompt_tokens,
            word_count=w_count,
            char_count=c_count,
        )
    t_counts = [m.token_count for m in actions_metrics.values()]
    pt_counts = [m.prompt_token_count for m in actions_metrics.values()]
    return ScenarioMetrics(
        scenario_id=scenario["id"],
        template_id=scenario.get("template_id", ""),
        actions=actions_metrics,
        min_tokens=min(t_counts),
        max_tokens=max(t_counts),
        token_span=max(t_counts) - min(t_counts),
        min_prompt_tokens=min(pt_counts),
        max_prompt_tokens=max(pt_counts),
        prompt_token_span=max(pt_counts) - min(pt_counts),
    )


def load_phase0b_scenarios(path: str = "data/scenarios_phase0b_utility_matched.json") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "scenarios" in data:
        return data["scenarios"]
    elif isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized format in {path}")
