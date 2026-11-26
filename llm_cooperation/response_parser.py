"""Response parsing utilities for generated responses.

Provides:
- parse_response: The repository's original strict regex parser.
- parse_generated_secondary: Transparent post-hoc secondary initial-answer-letter extraction
  from up to 5 generated tokens. Distinguishes:
  - VALID_INITIAL_LETTER: clean single initial letter without trailing text
  - VALID_INITIAL_LETTER_WITH_TEXT: initial letter followed by explanation/formatting
  - AMBIGUOUS_MULTI_ANSWER: e.g. 'A, B, C' or 'A or B'
  - CONTRADICTORY_EXPLANATION: initial letter contradicts an explicit subsequent answer declaration
  - ARBITRARY_MENTION_WITHOUT_INITIAL: options mentioned without an initial choice
  - UNPARSEABLE: empty, whitespace-only, or no valid option token
"""
import re
from typing import Dict, Optional, Tuple

# Original strict regex: letter alone with optional punctuation/whitespace
STRICT_REGEX = re.compile(r'^\s*[\(\[]?([A-D])[.\):\]\s]*$')

# Secondary initial-letter regex: option letter A-D at start followed by delimiter or end
INITIAL_LETTER_REGEX = re.compile(r'^\s*[\(\[]?([A-D])[\)\]]?([.\:\s\n]|$)')

# Multi-answer sequences, e.g. "A, B, C", "A or B", "A / B", "A and B"
MULTI_ANSWER_REGEX = re.compile(r'\b[A-D]\b\s*(?:,|\/|\bor\b|\band\b)\s*\b[A-D]\b', re.IGNORECASE)

# Explanation declaring the answer explicitly, e.g. "correct answer is B", "answer is C"
ANSWER_DECLARATION_REGEX = re.compile(
    r'(?:correct answer is|answer is|choose option|select option)\s*[\(\[]?([A-D])[\)\]]?',
    re.IGNORECASE
)


def parse_strict(raw: Optional[str], mapping: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Original strict parser matching exact single letter tokens."""
    if not raw:
        return None, None
    m = STRICT_REGEX.match(raw)
    if not m:
        return None, None
    letter = m.group(1).upper()
    return (letter, mapping[letter]) if letter in mapping else (None, None)


def parse_generated_secondary(raw: Optional[str], mapping: Dict[str, str]) -> Tuple[str, Optional[str], Optional[str]]:
    """Extract initial answer letter post-hoc from generated raw text (up to 5 tokens).

    Returns:
        (category, letter, strategy)
        where category is one of:
            - 'VALID_INITIAL_LETTER'
            - 'VALID_INITIAL_LETTER_WITH_TEXT'
            - 'AMBIGUOUS_MULTI_ANSWER'
            - 'CONTRADICTORY_EXPLANATION'
            - 'ARBITRARY_MENTION_WITHOUT_INITIAL'
            - 'UNPARSEABLE'
    """
    if not raw or not raw.strip():
        return 'UNPARSEABLE', None, None

    s = raw.strip()

    # Ambiguous multi-answer sequence
    if MULTI_ANSWER_REGEX.search(s):
        return 'AMBIGUOUS_MULTI_ANSWER', None, None

    # Check for initial option letter
    m = INITIAL_LETTER_REGEX.match(s)
    if m:
        letter = m.group(1).upper()
        trailing = s[m.end():].strip()
        strat = mapping.get(letter)

        # Check for contradictory subsequent declaration
        decl = ANSWER_DECLARATION_REGEX.search(trailing)
        if decl:
            decl_letter = decl.group(1).upper()
            if decl_letter != letter:
                return 'CONTRADICTORY_EXPLANATION', None, None

        if not trailing:
            return 'VALID_INITIAL_LETTER', letter, strat
        else:
            return 'VALID_INITIAL_LETTER_WITH_TEXT', letter, strat

    # Mention of A-D letters without leading initial choice
    if re.search(r'\b[A-D]\b', s):
        return 'ARBITRARY_MENTION_WITHOUT_INITIAL', None, None

    return 'UNPARSEABLE', None, None
