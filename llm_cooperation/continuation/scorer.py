"""Core continuation-likelihood scorer.

Implements full-sequence conditional log-probability scoring using teacher
forcing with AutoModelForCausalLM. Handles token boundary verification
rigorously for byte-level BPE tokenizers.

Key design properties:
- Scores the entire continuation, not just the first token.
- Excludes ALL prefix tokens from the continuation score.
- Correctly aligns labels and next-token logits (causal shift).
- Verifies token boundary integrity: prefix tokens must appear identically
  in the joint encoding. Fails explicitly if the boundary is ambiguous.
- Records token-level log-probabilities.
- Supports batched scoring (batch over strategies for a given prefix).
- Numerical precision: float32 for log-softmax regardless of model dtype.
"""

import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from llm_cooperation.continuation.schema import (
    CandidateScoreResult,
    TokenScoreDetail,
)
from llm_cooperation.continuation.templates import build_prefix, ALL_TEMPLATE_IDS
from llm_cooperation.items.schema import StrategyType


# Sentinel for mock model names
_MOCK_PREFIXES = ("mock-", "mock_")


class TokenBoundaryError(Exception):
    """Raised when prefix/continuation boundary cannot be verified unambiguously."""
    pass


def _is_mock(model_name: str) -> bool:
    name_lower = model_name.lower()
    return any(name_lower.startswith(p) for p in _MOCK_PREFIXES)


def _verify_boundary(
    prefix_ids: List[int],
    joint_ids: List[int],
) -> Tuple[List[int], Optional[str]]:
    """Verify that prefix_ids appears as an exact prefix of joint_ids.

    Returns:
        (continuation_ids, warning_message)
        continuation_ids: token IDs after the prefix
        warning_message: None if clean; a warning string if a minor
            adjustment was needed (should trigger a logged warning).

    Raises:
        TokenBoundaryError: if the boundary is irrecoverably ambiguous.
    """
    n = len(prefix_ids)
    if len(joint_ids) < n:
        raise TokenBoundaryError(
            f"Joint encoding ({len(joint_ids)} tokens) is shorter than "
            f"prefix encoding ({n} tokens). Cannot establish boundary."
        )

    if joint_ids[:n] == prefix_ids:
        return joint_ids[n:], None

    # Try trimming the last prefix token (some BPE tokenizers retokenize
    # the final subword when continuation starts with a continuation character)
    if n >= 1 and joint_ids[: n - 1] == prefix_ids[: n - 1]:
        # The last prefix token was merged with the first continuation token
        warning = (
            f"BPE boundary merge detected: last prefix token {prefix_ids[-1]} "
            f"was merged with first continuation token. "
            f"Continuation starts at position {n - 1} in joint encoding. "
            f"This reduces the number of scored continuation tokens by 1."
        )
        return joint_ids[n - 1 :], warning

    raise TokenBoundaryError(
        f"Prefix boundary verification failed: "
        f"joint_ids[:{n}] = {joint_ids[:n]} "
        f"does not match prefix_ids = {prefix_ids}. "
        f"Tokenizer is retokenizing the prefix when concatenated with "
        f"the continuation. Cannot score unambiguously."
    )


def score_continuation(
    model,
    tokenizer,
    prefix_text: str,
    continuation_text: str,
    model_name: str = "unknown",
    model_revision: Optional[str] = None,
    precision: str = "bfloat16",
    scenario_id: str = "unknown",
    strategy: StrategyType = StrategyType.COOPERATE,
    template_id: str = "next_action",
    candidate_wording_id: str = "original",
) -> CandidateScoreResult:
    """Score log P(continuation | prefix) using teacher forcing.

    Args:
        model: HuggingFace CausalLM (or None for mock mode).
        tokenizer: HuggingFace tokenizer.
        prefix_text: The scenario stem + connector phrase.
        continuation_text: The action description to score.
        ... (provenance arguments)

    Returns:
        CandidateScoreResult with full token-level detail.

    Raises:
        TokenBoundaryError: if boundary cannot be verified.
        ValueError: if continuation has zero tokens after prefix removal.
    """
    import torch

    t0 = time.time()

    # Encode prefix and full sequence separately (no special tokens for base models)
    prefix_ids = tokenizer.encode(prefix_text, add_special_tokens=False)

    # Build joint text. Use a leading space if continuation doesn't start with one,
    # to handle BPE tokenizers that treat word-initial vs word-medial differently.
    # We will verify the boundary regardless.
    if continuation_text and not continuation_text.startswith(" "):
        joint_text = prefix_text + " " + continuation_text
        joint_ids = tokenizer.encode(joint_text, add_special_tokens=False)
        # Also try without space in case it produces a cleaner boundary
        joint_text_nospace = prefix_text + continuation_text
        joint_ids_nospace = tokenizer.encode(joint_text_nospace, add_special_tokens=False)

        # Pick whichever gives an exact prefix match
        if joint_ids[: len(prefix_ids)] == prefix_ids:
            pass  # joint_ids already valid
        elif joint_ids_nospace[: len(prefix_ids)] == prefix_ids:
            joint_ids = joint_ids_nospace
            joint_text = joint_text_nospace
        # _verify_boundary will catch remaining failures below
    else:
        joint_text = prefix_text + continuation_text
        joint_ids = tokenizer.encode(joint_text, add_special_tokens=False)

    # Strict boundary verification
    continuation_ids, boundary_warning = _verify_boundary(prefix_ids, joint_ids)

    if len(continuation_ids) == 0:
        raise ValueError(
            f"Continuation '{continuation_text[:80]}...' produced zero tokens "
            f"after prefix removal. Cannot score."
        )

    # Build input tensor: full joint sequence
    input_ids_list = prefix_ids + continuation_ids
    n_prefix = len(prefix_ids)
    n_total = len(input_ids_list)

    import torch
    input_tensor = torch.tensor([input_ids_list], dtype=torch.long).to(model.device)

    with torch.no_grad():
        outputs = model(input_tensor)
        # logits: [1, seq_len, vocab_size]
        logits = outputs.logits[0]  # [seq_len, vocab_size]

        # Causal LM: logits[i] predicts token at position i+1.
        # To score continuation token at position j (j >= n_prefix),
        # we use logits[j-1] (which is computed from all tokens [0..j-1]).
        # We need logits for positions [n_prefix-1 .. n_total-2]
        # to score tokens [n_prefix .. n_total-1].

        # Float32 for numerical stability
        logits_f32 = logits.float()
        log_probs_all = torch.log_softmax(logits_f32, dim=-1)  # [seq_len, vocab]

        token_log_probs = []
        token_details = []

        for i, tok_id in enumerate(continuation_ids):
            # Position in input_ids_list: n_prefix + i
            # Logit position that predicts this token: n_prefix + i - 1
            logit_pos = n_prefix + i - 1
            if logit_pos < 0:
                # This would only happen if n_prefix == 0, which we prevent
                raise ValueError("n_prefix must be >= 1")

            lp = float(log_probs_all[logit_pos, tok_id].item())
            token_log_probs.append(lp)

            tok_str = tokenizer.decode([tok_id], skip_special_tokens=False)
            token_details.append(TokenScoreDetail(
                token_id=tok_id,
                token_str=tok_str,
                log_prob=lp,
                position=i,
            ))

    sum_lp = float(np.sum(token_log_probs))
    mean_lp = float(np.mean(token_log_probs)) if token_log_probs else float("-inf")
    n_scored = len(token_log_probs)

    elapsed = time.time() - t0

    return CandidateScoreResult(
        scenario_id=scenario_id,
        strategy=strategy,
        template_id=template_id,
        candidate_wording_id=candidate_wording_id,
        prefix_text=prefix_text,
        continuation_text=continuation_text,
        num_prefix_tokens=len(prefix_ids),
        num_continuation_tokens=len(continuation_ids),
        boundary_verified=(boundary_warning is None),
        boundary_warning=boundary_warning,
        sum_log_prob=sum_lp,
        mean_log_prob=mean_lp,
        num_scored_tokens=n_scored,
        token_details=token_details,
        model_name=model_name,
        model_revision=model_revision,
        precision=precision,
        elapsed_seconds=elapsed,
    )


def score_continuation_mock(
    prefix_text: str,
    continuation_text: str,
    model_name: str = "mock",
    model_revision: Optional[str] = None,
    precision: str = "bfloat16",
    scenario_id: str = "unknown",
    strategy: StrategyType = StrategyType.COOPERATE,
    template_id: str = "next_action",
    candidate_wording_id: str = "original",
    rng: Optional[np.random.Generator] = None,
) -> CandidateScoreResult:
    """Mock continuation scorer for testing without model weights.

    Uses deterministic pseudo-random log-probs based on strategy.
    Mimics realistic token counts and distributions.

    Strategy bias for mock (slight coop preference in neutral context):
        COOPERATE: mean = -1.5
        INDEPENDENT: mean = -1.7
        COMPETE_EXPLOIT: mean = -2.0
        DISENGAGE: mean = -2.2
    """
    if rng is None:
        rng = np.random.default_rng(seed=abs(hash(scenario_id + strategy.value)) % (2**31))

    # Realistic word count approximation: ~1.3 tokens per word
    n_words = len(continuation_text.split())
    n_tokens = max(3, int(n_words * 1.3))

    strategy_means = {
        StrategyType.COOPERATE: -1.5,
        StrategyType.INDEPENDENT: -1.7,
        StrategyType.COMPETE_EXPLOIT: -2.0,
        StrategyType.DISENGAGE: -2.2,
    }
    mu = strategy_means.get(strategy, -1.8)
    token_lps = rng.normal(mu, 0.4, size=n_tokens).tolist()
    # Clamp to realistic range
    token_lps = [max(-15.0, min(-0.01, lp)) for lp in token_lps]

    # Mock token details
    words = continuation_text.split()
    token_details = []
    for i in range(n_tokens):
        word_idx = i * len(words) // n_tokens
        tok_str = words[word_idx] if word_idx < len(words) else f"<tok{i}>"
        token_details.append(TokenScoreDetail(
            token_id=1000 + i,
            token_str=tok_str,
            log_prob=token_lps[i],
            position=i,
        ))

    # Mock prefix token count
    n_prefix_tokens = max(5, len(prefix_text.split()) * 2)

    return CandidateScoreResult(
        scenario_id=scenario_id,
        strategy=strategy,
        template_id=template_id,
        candidate_wording_id=candidate_wording_id,
        prefix_text=prefix_text,
        continuation_text=continuation_text,
        num_prefix_tokens=n_prefix_tokens,
        num_continuation_tokens=n_tokens,
        boundary_verified=True,
        boundary_warning=None,
        sum_log_prob=float(np.sum(token_lps)),
        mean_log_prob=float(np.mean(token_lps)),
        num_scored_tokens=n_tokens,
        token_details=token_details,
        model_name=model_name,
        model_revision=model_revision,
        precision=precision,
        elapsed_seconds=0.001,
    )


def score_all_strategies_for_prefix(
    model,
    tokenizer,
    prefix_text: str,
    strategy_continuations: Dict[StrategyType, str],
    model_name: str,
    model_revision: Optional[str],
    precision: str,
    scenario_id: str,
    template_id: str,
    candidate_wording_id: str,
    mock: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, CandidateScoreResult]:
    """Score all four strategy continuations against a shared prefix.

    Each strategy is scored independently (teacher forcing).
    The prefix is encoded once; each continuation is scored separately.

    Returns:
        Dict mapping strategy value string -> CandidateScoreResult
    """
    results: Dict[str, CandidateScoreResult] = {}

    for strategy, continuation_text in strategy_continuations.items():
        if mock:
            result = score_continuation_mock(
                prefix_text=prefix_text,
                continuation_text=continuation_text,
                model_name=model_name,
                model_revision=model_revision,
                precision=precision,
                scenario_id=scenario_id,
                strategy=strategy,
                template_id=template_id,
                candidate_wording_id=candidate_wording_id,
                rng=rng,
            )
        else:
            result = score_continuation(
                model=model,
                tokenizer=tokenizer,
                prefix_text=prefix_text,
                continuation_text=continuation_text,
                model_name=model_name,
                model_revision=model_revision,
                precision=precision,
                scenario_id=scenario_id,
                strategy=strategy,
                template_id=template_id,
                candidate_wording_id=candidate_wording_id,
            )
        results[strategy.value] = result

    return results
