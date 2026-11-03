"""Tokenizer diagnostic probe to inspect token IDs for candidate answer letters.

Handles nuances across tokenizers:
- Unprefixed letters: 'A', 'B', 'C', 'D'
- Leading-space letters: ' A', ' B', ' C', ' D'
"""

from typing import Dict, List, Optional, Tuple


def probe_candidate_tokens(tokenizer, candidates: Optional[List[str]] = None) -> Dict[str, Dict]:
    """Probe tokenizer behavior for candidate answer tokens.

    Tests both unprefixed ('A') and leading-space prefixed (' A').
    Returns dictionary with token IDs and single-token validity.
    """
    if candidates is None:
        candidates = ["A", "B", "C", "D"]

    results = {}
    for cand in candidates:
        # 1. Unprefixed
        raw_ids = tokenizer.encode(cand, add_special_tokens=False)
        # 2. Leading space
        space_cand = f" {cand}"
        space_ids = tokenizer.encode(space_cand, add_special_tokens=False)

        results[cand] = {
            "unprefixed": {
                "text": cand,
                "token_ids": raw_ids,
                "is_single_token": len(raw_ids) == 1,
                "single_token_id": raw_ids[0] if len(raw_ids) == 1 else None,
            },
            "leading_space": {
                "text": space_cand,
                "token_ids": space_ids,
                "is_single_token": len(space_ids) == 1,
                "single_token_id": space_ids[0] if len(space_ids) == 1 else None,
            },
        }

    return results


def resolve_candidate_token_ids(tokenizer, prompt_ends_with_space: bool = False) -> Dict[str, int]:
    """Determine the single token ID for each candidate letter A, B, C, D.

    If the prompt ends with a space (e.g. 'Answer: '), unprefixed 'A' is typically expected.
    If the prompt ends with 'Answer:', leading space ' A' may be standard depending on tokenizer.
    """
    probes = probe_candidate_tokens(tokenizer)
    resolved = {}
    for cand, info in probes.items():
        if prompt_ends_with_space:
            # Tokenizer expects letter without space
            if info["unprefixed"]["is_single_token"]:
                resolved[cand] = info["unprefixed"]["single_token_id"]
            elif info["leading_space"]["is_single_token"]:
                resolved[cand] = info["leading_space"]["single_token_id"]
            else:
                resolved[cand] = info["unprefixed"]["token_ids"][0]
        else:
            # Prompt ends without space, e.g. "Answer:" -> model continues with " A" or "A"
            if info["leading_space"]["is_single_token"]:
                resolved[cand] = info["leading_space"]["single_token_id"]
            elif info["unprefixed"]["is_single_token"]:
                resolved[cand] = info["unprefixed"]["single_token_id"]
            else:
                resolved[cand] = info["leading_space"]["token_ids"][0]
    return resolved
