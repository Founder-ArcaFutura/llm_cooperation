"""Prompt templates for continuation-likelihood scoring.

Each template defines a connector phrase that follows the scenario stem
and precedes the candidate action continuation.

Design constraints:
- No cooperative or competitive vocabulary in the connector phrase itself.
- Grammatically sensible given the scenario text (which describes actions
  an agent is about to take).
- No multiple-choice letters, no instruction to choose an answer.
- Three distinct template families to test sensitivity.

Template IDs are stable and must not be changed once a run is committed.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ContinuationTemplate:
    """A connector template used to bridge scenario stem to action continuation."""
    template_id: str
    connector: str
    description: str


# ---------------------------------------------------------------------------
# Primary templates (grammatically sensible for the scenario text format)
# ---------------------------------------------------------------------------
# The scenario stems end with a full stop and describe the situation.
# The connector phrase introduces the action description as a continuation.
# All connectors are semantically neutral — they do not privilege any strategy.

TEMPLATES: List[ContinuationTemplate] = [
    ContinuationTemplate(
        template_id="next_action",
        connector="\n\nNext action:",
        description=(
            "Action record format. Presents the continuation as the recorded "
            "next action. Neutral — consistent with any strategy."
        ),
    ),
    ContinuationTemplate(
        template_id="course_of_action",
        connector="\n\nThe selected course of action was:",
        description=(
            "Decision narrative format. Presents the continuation as a reported "
            "decision. Neutral past-tense framing."
        ),
    ),
    ContinuationTemplate(
        template_id="next_step",
        connector="\n\nThe next step is:",
        description=(
            "Procedure continuation format. Presents the action as the next step "
            "in an ongoing process. Neutral procedural framing."
        ),
    ),
]

# Stable lookup by template_id
TEMPLATE_BY_ID: Dict[str, ContinuationTemplate] = {t.template_id: t for t in TEMPLATES}

ALL_TEMPLATE_IDS: List[str] = [t.template_id for t in TEMPLATES]


def build_prefix(stem: str, template_id: str) -> str:
    """Build the full prefix text: scenario stem + connector phrase.

    The continuation (action description) is NOT included; it will be
    scored separately via teacher forcing.

    Args:
        stem: The scenario situation description.
        template_id: One of the standard template IDs.

    Returns:
        Prefix string ending with the connector phrase (no trailing space).
    """
    if template_id not in TEMPLATE_BY_ID:
        raise ValueError(
            f"Unknown template_id '{template_id}'. "
            f"Valid IDs: {ALL_TEMPLATE_IDS}"
        )
    tmpl = TEMPLATE_BY_ID[template_id]
    # Normalize stem: strip trailing whitespace, do not add punctuation
    return stem.strip() + tmpl.connector
