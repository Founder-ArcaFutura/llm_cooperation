"""Corpus audit and reporting for controlled strategy banks."""
from __future__ import annotations

import collections
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from llm_cooperation.items.controlled_banks import (
    DEFAULT_TOKENIZER_ID,
    STRATEGIES,
    TRAILING_MARKER,
    get_tokenizer,
    measure_scenario,
)


def compute_ngrams(text: str, n: int = 2) -> List[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def compute_bank_metrics(
    scenarios: List[Dict[str, Any]],
    tokenizer: Optional[Any] = None,
    trailing_marker: str = TRAILING_MARKER,
) -> Dict[str, Any]:
    if tokenizer is None:
        tokenizer = get_tokenizer()

    act_tokens_by_strat = {s: [] for s in STRATEGIES}
    act_words_by_strat = {s: [] for s in STRATEGIES}
    act_chars_by_strat = {s: [] for s in STRATEGIES}
    prompt_tokens_by_strat = {s: [] for s in STRATEGIES}

    within_scenario_token_spans = []
    within_scenario_prompt_spans = []
    within_scenario_word_spans = []
    within_scenario_char_spans = []

    words_by_strat = {s: collections.Counter() for s in STRATEGIES}
    bigrams_by_strat = {s: collections.Counter() for s in STRATEGIES}

    for sc in scenarios:
        stem = sc["stem"].strip()
        sc_t = []
        sc_pt = []
        sc_w = []
        sc_c = []

        for strat in STRATEGIES:
            act = sc["options"][strat].strip()
            prompt = f"{stem}\n\nAction: {act}{trailing_marker}"

            t_len = len(tokenizer.encode(act))
            pt_len = len(tokenizer.encode(prompt))
            w_len = len(act.split())
            c_len = len(act)

            act_tokens_by_strat[strat].append(t_len)
            prompt_tokens_by_strat[strat].append(pt_len)
            act_words_by_strat[strat].append(w_len)
            act_chars_by_strat[strat].append(c_len)

            sc_t.append(t_len)
            sc_pt.append(pt_len)
            sc_w.append(w_len)
            sc_c.append(c_len)

            words = re.findall(r"\b\w+\b", act.lower())
            words_by_strat[strat].update(words)
            bigrams = compute_ngrams(act, n=2)
            bigrams_by_strat[strat].update(bigrams)

        within_scenario_token_spans.append(max(sc_t) - min(sc_t))
        within_scenario_prompt_spans.append(max(sc_pt) - min(sc_pt))
        within_scenario_word_spans.append(max(sc_w) - min(sc_w))
        within_scenario_char_spans.append(max(sc_c) - min(sc_c))

    def _stats(arr: List[int]) -> Dict[str, float]:
        if not arr:
            return {"mean": 0.0, "std": 0.0, "min": 0, "max": 0}
        m = sum(arr) / len(arr)
        var = sum((x - m) ** 2 for x in arr) / len(arr)
        return {
            "mean": round(m, 3),
            "std": round(math.sqrt(var), 3),
            "min": int(min(arr)),
            "max": int(max(arr)),
        }

    return {
        "num_scenarios": len(scenarios),
        "token_spans": _stats(within_scenario_token_spans),
        "prompt_spans": _stats(within_scenario_prompt_spans),
        "word_spans": _stats(within_scenario_word_spans),
        "char_spans": _stats(within_scenario_char_spans),
        "action_tokens": {s: _stats(act_tokens_by_strat[s]) for s in STRATEGIES},
        "prompt_tokens": {s: _stats(prompt_tokens_by_strat[s]) for s in STRATEGIES},
        "action_words": {s: _stats(act_words_by_strat[s]) for s in STRATEGIES},
        "action_chars": {s: _stats(act_chars_by_strat[s]) for s in STRATEGIES},
        "top_words": {s: dict(words_by_strat[s].most_common(10)) for s in STRATEGIES},
        "top_bigrams": {s: dict(bigrams_by_strat[s].most_common(10)) for s in STRATEGIES},
    }


def compute_cross_bank_diversity(
    banks: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    overlap_results = {}
    bank_keys = list(banks.keys())

    for i in range(len(bank_keys)):
        for j in range(i + 1, len(bank_keys)):
            b1_name, b2_name = bank_keys[i], bank_keys[j]
            b1, b2 = banks[b1_name], banks[b2_name]
            b1_dict = {s["id"]: s["options"] for s in b1}
            b2_dict = {s["id"]: s["options"] for s in b2}

            exact_matches = 0
            jaccard_sims = []
            total_pairs = 0

            for sid in b1_dict:
                if sid not in b2_dict:
                    continue
                for strat in STRATEGIES:
                    total_pairs += 1
                    t1 = b1_dict[sid][strat].strip()
                    t2 = b2_dict[sid][strat].strip()
                    if t1.lower() == t2.lower():
                        exact_matches += 1
                    words1 = set(re.findall(r"\b\w+\b", t1.lower()))
                    words2 = set(re.findall(r"\b\w+\b", t2.lower()))
                    union = words1.union(words2)
                    inter = words1.intersection(words2)
                    if union:
                        jaccard_sims.append(len(inter) / len(union))

            overlap_results[f"{b1_name}_vs_{b2_name}"] = {
                "total_action_pairs": total_pairs,
                "exact_matches": exact_matches,
                "mean_word_jaccard_similarity": round(
                    sum(jaccard_sims) / len(jaccard_sims) if jaccard_sims else 0.0, 3
                ),
            }

    return overlap_results
