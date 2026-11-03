"""Tokenizer diagnostic probe to inspect token IDs for candidate answer letters.

Handles nuances across tokenizers:
- Unprefixed letters: 'A', 'B', 'C', 'D'
- Leading-space letters: ' A', ' B', ' C', ' D'
- Explicit validation at the actual prompt boundary (e.g., prompt + letter vs prompt alone)
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


class TokenizerCandidateError(Exception):
    """Raised when candidate choices cannot be cleanly resolved to single tokens or incompatible at prompt boundary."""
    pass


def validate_candidate_tokens_at_boundary(
    tokenizer,
    sample_prompt: str,
    candidate_token_ids: Dict[str, int],
) -> None:
    """Validate that candidate letters tokenize to candidate_token_ids at the actual prompt boundary.

    Tests encoding `sample_prompt + continuation` and verifies that the new token(s)
    produced after `sample_prompt` form exactly a single token equal to `candidate_token_ids[cand]`.
    Never silently substitutes incompatible tokens.
    """
    prompt_ids = tokenizer.encode(sample_prompt, add_special_tokens=False)
    num_prompt_tokens = len(prompt_ids)
    errors = []

    for cand, expected_id in candidate_token_ids.items():
        # Try continuation
        continuation = cand if sample_prompt.endswith(" ") else f" {cand}"
        full_text = sample_prompt + continuation
        full_ids = tokenizer.encode(full_text, add_special_tokens=False)

        if full_ids[:num_prompt_tokens] == prompt_ids:
            continuation_ids = full_ids[num_prompt_tokens:]
        else:
            continuation_ids = full_ids[len(tokenizer.encode(sample_prompt.rstrip(), add_special_tokens=False)):]

        if len(continuation_ids) != 1:
            alt_continuation = cand if not sample_prompt.endswith(" ") else f" {cand}"
            alt_full = sample_prompt + alt_continuation
            alt_full_ids = tokenizer.encode(alt_full, add_special_tokens=False)
            if alt_full_ids[:num_prompt_tokens] == prompt_ids:
                alt_continuation_ids = alt_full_ids[num_prompt_tokens:]
            else:
                alt_continuation_ids = []

            if len(alt_continuation_ids) == 1 and alt_continuation_ids[0] == expected_id:
                continue

            errors.append(
                f"Candidate '{cand}' at prompt boundary tokenizes to {continuation_ids} "
                f"(expected single token [{expected_id}])."
            )
        elif continuation_ids[0] != expected_id:
            errors.append(
                f"Candidate '{cand}' at prompt boundary produced token ID {continuation_ids[0]} "
                f"but resolved candidate token ID is {expected_id}. Incompatible token substitution barred."
            )

    if errors:
        raise TokenizerCandidateError(
            f"Prompt boundary tokenization validation failed:\n" + "\n".join(errors)
        )


def resolve_candidate_token_ids(
    tokenizer,
    prompt_ends_with_space: bool = False,
    sample_prompt: Optional[str] = None,
) -> Dict[str, int]:
    """Determine the single token ID for each candidate letter A, B, C, D.

    Fails explicitly with a TokenizerCandidateError if any candidate letter
    is multi-token or ambiguous at the prompt boundary, rather than silently
    selecting only the first token or substituting incompatible tokens.
    """
    probes = probe_candidate_tokens(tokenizer)
    resolved = {}
    errors = []

    for cand, info in probes.items():
        if prompt_ends_with_space:
            if info["unprefixed"]["is_single_token"]:
                resolved[cand] = info["unprefixed"]["single_token_id"]
            elif info["leading_space"]["is_single_token"]:
                resolved[cand] = info["leading_space"]["single_token_id"]
            else:
                errors.append(
                    f"Candidate '{cand}' tokenizes to multi-token sequence {info['unprefixed']['token_ids']} "
                    f"(with space: {info['leading_space']['token_ids']}). Forced-choice single-token scoring invalid."
                )
        else:
            if info["leading_space"]["is_single_token"]:
                resolved[cand] = info["leading_space"]["single_token_id"]
            elif info["unprefixed"]["is_single_token"]:
                resolved[cand] = info["unprefixed"]["single_token_id"]
            else:
                errors.append(
                    f"Candidate '{cand}' tokenizes to multi-token sequence {info['leading_space']['token_ids']} "
                    f"(unprefixed: {info['unprefixed']['token_ids']}). Forced-choice single-token scoring invalid."
                )

    if errors:
        raise TokenizerCandidateError(
            f"Tokenizer candidate resolution failed at prompt boundary:\n" + "\n".join(errors)
        )

    if sample_prompt is not None:
        validate_candidate_tokens_at_boundary(tokenizer, sample_prompt, resolved)

    return resolved
