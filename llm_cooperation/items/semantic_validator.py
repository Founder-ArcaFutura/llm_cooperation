"""Independent semantic validation module for controlled strategy banks."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

STRATEGIES = ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")

COOPERATE_INDICATORS = [
    r"\bshar(e|ing|ed)\b",
    r"\bcoordinat(e|ing|ed|ion)\b",
    r"\bsynchroniz(e|ing|ed|ation)\b",
    r"\bcoupl(e|ing|ed)\b",
    r"\bmerg(e|ing|ed)\b",
    r"\bpool(ing|ed)?\b",
    r"\bjoint(ly)?\b",
    r"\balign(ing|ed)?\b",
    r"\bconnect(ing|ed)?\b",
    r"\bcollaborat(e|ing|ed|ion)\b",
    r"\binterleav(e|ing|ed)\b",
    r"\bexchang(e|ing|ed)\b",
    r"\blink(ing|ed)?\b",
    r"\bdual-bay\b",
    r"\bdual-stream\b",
    r"\bshared\b",
    r"\btandem\b",
    r"\bwith the\b",
    r"\balongside\b",
    r"\bwith a\b",
    r"\bwith an\b",
    r"\bharmoniz(e|ing|ed)\b",
    r"\bstream\b",
    r"\binterlink\b",
    r"\btrade\b",
    r"\bswap\b",
    r"\bapportion\b",
]

INDEPENDENT_INDICATORS = [
    r"\bindependent(ly)?\b",
    r"\bseparat(e|ely|ing)\b",
    r"\bstandalone\b",
    r"\bisolat(e|ed|ion)\b",
    r"\blocal(ly)?\b",
    r"\bindividual(ly)?\b",
    r"\bsolo\b",
    r"\bautonomous(ly)?\b",
    r"\bown\b",
    r"\bsingle\b",
    r"\bstandard\b",
    r"\bunilateral(ly)?\b",
    r"\bself-contained\b",
    r"\bdedicated\b",
    r"\bstandard local\b",
    r"\balone\b",
    r"\bunshared\b",
]

COMPETE_EXPLOIT_INDICATORS = [
    r"\bpriorit(y|ize|izing|ized)\b",
    r"\bmonopoliz(e|ing|ed)\b",
    r"\bpreferential\b",
    r"\bfirst\b",
    r"\bclaim(ing|ed)?\b",
    r"\bfront-run\b",
    r"\bpreempt(ive|ively|ing|ed)?\b",
    r"\bmaxim(ize|izing|ized)\b",
    r"\boutbid(ding)?\b",
    r"\bcorner(ing|ed)?\b",
    r"\bcommandeer(ing|ed)?\b",
    r"\bseiz(e|ing|ed)\b",
    r"\baggressiv(e|ely)\b",
    r"\bhead-start\b",
    r"\bdominat(e|ing|ed)\b",
    r"\bdisplac(e|ing|ed)\b",
    r"\bexclusive(ly)?\b",
    r"\boverrid(e|ing|en)\b",
    r"\bfavoring\b",
    r"\bpeak\b",
    r"\bearly\b",
    r"\block out\b",
    r"\bfast-track\b",
    r"\brush into\b",
]

DISENGAGE_INDICATORS = [
    r"\bdefer(ring|red)?\b",
    r"\bpostpon(e|ing|ed)\b",
    r"\bdelay(ing|ed)?\b",
    r"\bpause\b",
    r"\bwithhold(ing)?\b",
    r"\bstandby\b",
    r"\bidle\b",
    r"\bsuspend(ing|ed)?\b",
    r"\bhalt(ing|ed)?\b",
    r"\bhaving no part\b",
    r"\bhold(ing)?\b",
    r"\bwait(ing)?\b",
    r"\babort(ing|ed)?\b",
    r"\bwithdraw(ing|n)?\b",
    r"\bbypass(ing|ed)?\b",
    r"\bskip(ping|ped)?\b",
    r"\bcancel(ling|led)?\b",
    r"\bfreez(e|ing)\b",
    r"\bdeclin(e|ing|ed)\b",
    r"\bopt out\b",
    r"\block(ed)?\b",
    r"\bshelve\b",
    r"\bstand down\b",
]


@dataclass
class ValidationIssue:
    check_name: str
    severity: str
    message: str


@dataclass
class ActionValidationResult:
    strategy: str
    action_text: str
    blind_prediction: str
    blind_confidence: float
    blind_scores: Dict[str, float]
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class ScenarioValidationResult:
    scenario_id: str
    bank_id: str
    passed: bool
    requires_human_review: bool
    action_results: Dict[str, ActionValidationResult]
    summary_issues: List[ValidationIssue] = field(default_factory=list)


def score_blind_strategy(action_text: str) -> Dict[str, float]:
    text_lower = action_text.lower()
    return {
        "COOPERATE": sum(1.0 for p in COOPERATE_INDICATORS if re.search(p, text_lower)),
        "INDEPENDENT": sum(1.0 for p in INDEPENDENT_INDICATORS if re.search(p, text_lower)),
        "COMPETE_EXPLOIT": sum(1.0 for p in COMPETE_EXPLOIT_INDICATORS if re.search(p, text_lower)),
        "DISENGAGE": sum(1.0 for p in DISENGAGE_INDICATORS if re.search(p, text_lower)),
    }


def predict_blind_strategy(action_text: str) -> Tuple[str, float, Dict[str, float]]:
    scores = score_blind_strategy(action_text)
    total = sum(scores.values())
    if total == 0:
        return "UNKNOWN", 0.0, scores
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    return best_cat, best_score / total, scores


def validate_scenario_actions(
    scenario: Dict[str, Any],
    revised_options: Dict[str, str],
    bank_id: str = "bank_a",
    token_span_limit: int = 1,
    tokenizer: Optional[Any] = None,
) -> ScenarioValidationResult:
    from llm_cooperation.items.controlled_banks import get_tokenizer

    if tokenizer is None:
        tokenizer = get_tokenizer()

    sid = scenario["id"]
    partner_type = scenario.get("partner_type", "unknown")
    actions_res: Dict[str, ActionValidationResult] = {}
    summary_issues: List[ValidationIssue] = []

    texts = [revised_options[s].strip() for s in STRATEGIES]
    if len(set(texts)) < 4:
        summary_issues.append(
            ValidationIssue(
                check_name="distinctiveness",
                severity="error",
                message=f"Duplicate action texts found in scenario {sid}.",
            )
        )

    token_lens = {s: len(tokenizer.encode(revised_options[s].strip())) for s in STRATEGIES}
    span = max(token_lens.values()) - min(token_lens.values())
    if span > token_span_limit:
        summary_issues.append(
            ValidationIssue(
                check_name="token_span",
                severity="error",
                message=f"Token span {span} exceeds limit {token_span_limit} ({token_lens}).",
            )
        )

    all_passed = True
    needs_review = False

    for strat in STRATEGIES:
        act = revised_options[strat].strip()
        issues: List[ValidationIssue] = []

        if not act:
            issues.append(
                ValidationIssue(
                    check_name="non_empty",
                    severity="error",
                    message=f"Action text for {strat} is empty.",
                )
            )

        pred, conf, scores = predict_blind_strategy(act)
        if pred != strat:
            issues.append(
                ValidationIssue(
                    check_name="blind_classification",
                    severity="warning",
                    message=f"Blind classification identified '{pred}' (conf={conf:.2f}) instead of '{strat}'.",
                )
            )
            needs_review = True

        if strat == "COOPERATE":
            act_l = act.lower()
            if partner_type == "human" and "agent" in act_l and "human" not in act_l:
                issues.append(
                    ValidationIssue(
                        check_name="partner_consistency",
                        severity="warning",
                        message="Mentions agent when partner is human.",
                    )
                )
                needs_review = True
            elif partner_type == "ai" and "human" in act_l and "agent" not in act_l and "system" not in act_l and "aircraft" not in act_l and "cell" not in act_l and "robot" not in act_l and "controller" not in act_l and "probe" not in act_l and "platform" not in act_l and "drone" not in act_l and "rig" not in act_l:
                issues.append(
                    ValidationIssue(
                        check_name="partner_consistency",
                        severity="warning",
                        message="Mentions human when partner is AI.",
                    )
                )
                needs_review = True

        if strat in ("INDEPENDENT", "DISENGAGE"):
            act_l = act.lower()
            if "with the partner" in act_l or "alongside the partner" in act_l:
                issues.append(
                    ValidationIssue(
                        check_name="unnecessary_partner_reference",
                        severity="warning",
                        message=f"Unnecessary partner reference in {strat}.",
                    )
                )
                needs_review = True

        has_error = any(iss.severity == "error" for iss in issues)
        if has_error:
            all_passed = False

        actions_res[strat] = ActionValidationResult(
            strategy=strat,
            action_text=act,
            blind_prediction=pred,
            blind_confidence=conf,
            blind_scores=scores,
            passed=not has_error,
            issues=issues,
        )

    if any(iss.severity == "error" for iss in summary_issues):
        all_passed = False

    return ScenarioValidationResult(
        scenario_id=sid,
        bank_id=bank_id,
        passed=all_passed,
        requires_human_review=needs_review or (not all_passed),
        action_results=actions_res,
        summary_issues=summary_issues,
    )
