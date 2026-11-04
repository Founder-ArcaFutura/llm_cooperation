"""Audit and validation script for Phase 1 prospective replication item bank.

Ensures:
1. Exact counts: 30 unique templates, 60 scenarios total.
2. Template composition: 24 equal focal-actor utility templates, 6 symmetric-welfare controls.
3. Partner balance: Exactly 30 human-partner and 30 AI-partner scenarios, paired by template_id.
4. Strategy completeness: All 4 semantic strategies (COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE).
5. Payoff equivalence:
   - For all 30 templates: actor expected utility, time, cost, risk, success_prob, and actor_payoff are identical between COOPERATE and INDEPENDENT.
   - For the 24 equal-utility templates: partner_payoff(COOPERATE) > partner_payoff(INDEPENDENT).
   - For the 6 symmetric-welfare controls: partner_payoff(COOPERATE) == partner_payoff(INDEPENDENT).
6. Option length spread: Checks |len(COOPERATE) - len(INDEPENDENT)| <= 2 words, flags discrepancies.
7. Lexical audit: Prohibits moralizing/taboo vocabulary and destructive markers.
8. Permutation counterbalancing: 240 presentations, exact 4x4 Latin-square counterbalancing across positions A, B, C, D.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from rich.console import Console
from rich.table import Table

from llm_cooperation.items.schema import (
    ScenarioBank,
    PartnerType,
    StrategyType,
)
from llm_cooperation.items.permutations import (
    generate_all_presentations,
    generate_permutations,
)
from llm_cooperation.items.audit import TABOO_WORDS, DESTRUCTIVE_MARKERS


def audit_phase1_bank(bank_path: str = "data/scenarios_phase1_prospective.json") -> Tuple[bool, List[str]]:
    console = Console()
    flags: List[str] = []
    success = True

    if not Path(bank_path).exists():
        console.print(f"[bold red]FAIL: Bank file not found at {bank_path}[/bold red]")
        return False, [f"File not found: {bank_path}"]

    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bank = ScenarioBank(**data)
    scenarios = bank.scenarios
    console.print(f"[bold green]Loaded {len(scenarios)} Phase 1 scenarios from {bank_path}.[/bold green]")

    # 1. Check total count
    if len(scenarios) != 60:
        msg = f"Expected exactly 60 scenarios, found {len(scenarios)}"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False

    # 2. Check bank status: permits both 'draft_pending_review' and 'frozen'
    valid_statuses = {"draft_pending_review", "frozen"}
    if bank.status not in valid_statuses:
        msg = f"Phase 1 bank status must be one of {valid_statuses}, got '{bank.status}'"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False

    # 3. Check templates and pairing
    templates_map: Dict[str, List] = {}
    for s in scenarios:
        if not s.template_id:
            msg = f"Scenario {s.id} is missing template_id"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False
            continue
        templates_map.setdefault(s.template_id, []).append(s)

    if len(templates_map) != 30:
        msg = f"Expected exactly 30 unique templates, found {len(templates_map)}"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False

    sym_control_tpls = 0
    equal_util_tpls = 0

    for tid, t_scenarios in templates_map.items():
        if len(t_scenarios) != 2:
            msg = f"Template {tid} has {len(t_scenarios)} scenarios, expected exactly 2"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False

        partners = {sc.partner_type for sc in t_scenarios}
        if partners != {PartnerType.HUMAN, PartnerType.AI}:
            msg = f"Template {tid} does not have matched human and AI partners: {partners}"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False

        splits = {sc.split for sc in t_scenarios}
        if splits != {"confirmatory"}:
            msg = f"Template {tid} split must be 'confirmatory', got {splits}"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False

        is_sym_set = {getattr(sc, "is_symmetric_control", False) for sc in t_scenarios}
        if len(is_sym_set) != 1:
            msg = f"Template {tid} has conflicting is_symmetric_control values: {is_sym_set}"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False
        else:
            if list(is_sym_set)[0]:
                sym_control_tpls += 1
            else:
                equal_util_tpls += 1

    if equal_util_tpls != 24 or sym_control_tpls != 6:
        msg = f"Expected 24 equal-utility and 6 symmetric control templates, found {equal_util_tpls} and {sym_control_tpls}"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False
    else:
        console.print(f"[green]PASS: Template composition verified: 24 equal-utility templates (48 scenarios) + 6 symmetric controls (12 scenarios).[/green]")

    # 4. Check payoff specification equality
    for s in scenarios:
        ps = s.payoff_spec
        if not ps:
            msg = f"Scenario {s.id} is missing payoff_spec"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False
            continue

        coop_ps = ps.get("COOPERATE", {})
        indep_ps = ps.get("INDEPENDENT", {})

        # Focal actor attributes must match exactly
        for attr in ["actor_expected_utility", "time", "cost", "risk", "success_prob", "actor_payoff"]:
            c_val = coop_ps.get(attr)
            i_val = indep_ps.get(attr)
            if c_val != i_val:
                msg = f"Scenario {s.id} payoff mismatch on '{attr}': COOP={c_val} vs INDEP={i_val}"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False

        # Partner payoff checks
        c_part = float(coop_ps.get("partner_payoff", 0.0))
        i_part = float(indep_ps.get("partner_payoff", 0.0))
        if s.is_symmetric_control:
            if c_part != i_part:
                msg = f"Symmetric control {s.id} has unequal partner payoffs: COOP={c_part} vs INDEP={i_part}"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False
        else:
            if c_part <= i_part:
                msg = f"Equal-utility scenario {s.id} fails to provide partner benefit: COOP={c_part} <= INDEP={i_part}"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False

    # 5. Check Taboo Words in Option Text
    flagged_taboo = []
    for s in scenarios:
        for strat, opt_text in s.options.items():
            tokens = {w.lower().strip(".,;:?!'\"()[]{}") for w in opt_text.split()}
            found = tokens.intersection(TABOO_WORDS)
            if found:
                flagged_taboo.append((s.id, strat.value, found, opt_text))

    if flagged_taboo:
        for item in flagged_taboo:
            msg = f"Taboo word in {item[0]} ({item[1]}): {item[2]}"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
        success = False
    else:
        console.print("[green]PASS: No taboo or moralizing words detected in option choices.[/green]")

    # Check for destructive markers
    destructive_flagged = []
    for s in scenarios:
        for strat, opt_text in s.options.items():
            lowered = opt_text.lower()
            for marker in DESTRUCTIVE_MARKERS:
                if marker in lowered:
                    destructive_flagged.append((s.id, strat.value, marker, opt_text))

    if destructive_flagged:
        for item in destructive_flagged:
            msg = f"Destructive marker in {item[0]} ({item[1]}): '{item[2]}'"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
        success = False
    else:
        console.print("[green]PASS: No destructive markers detected.[/green]")

    # 6. Check Option Length Statistics and Length Disparities
    lengths_by_strat: Dict[StrategyType, List[int]] = {s: [] for s in StrategyType}
    spread_gt_2_count = 0
    for s in scenarios:
        c_len = len(s.options[StrategyType.COOPERATE].split())
        i_len = len(s.options[StrategyType.INDEPENDENT].split())
        spread = abs(c_len - i_len)
        if spread > 2:
            spread_gt_2_count += 1
            flags.append(f"Length spread > 2 in {s.id}: COOP={c_len}, INDEP={i_len} (diff={spread})")

        for strat, opt_text in s.options.items():
            lengths_by_strat[strat].append(len(opt_text.split()))

    table = Table(title="Phase 1 Option Word Length Balance by Strategy")
    table.add_column("Strategy", style="cyan")
    table.add_column("Mean Words", justify="right")
    table.add_column("Std Dev", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")

    mean_lens = {}
    for strat, lens in lengths_by_strat.items():
        m = float(np.mean(lens))
        mean_lens[strat] = m
        table.add_row(
            strat.value,
            f"{m:.1f}",
            f"{np.std(lens):.1f}",
            str(np.min(lens)),
            str(np.max(lens)),
        )
    console.print(table)

    if spread_gt_2_count > 0:
        console.print(f"[yellow]REVIEW FLAG: Found {spread_gt_2_count} scenarios with |COOP - INDEP| word length spread > 2.[/yellow]")
    else:
        console.print("[green]PASS: All 60 scenarios strictly satisfy |COOP - INDEP| <= 2 words.[/green]")

    # 7. Check Permutation Counterbalancing (240 presentations)
    expected_presentations = len(scenarios) * 4
    if expected_presentations != 240:
        msg = f"Expected 240 presentations, but len(scenarios)*4 = {expected_presentations}"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False

    all_presentations = generate_all_presentations(scenarios)
    if len(all_presentations) != 240:
        msg = f"Expected 240 presentations generated, got {len(all_presentations)}"
        console.print(f"[bold red]FAIL: {msg}[/bold red]")
        flags.append(msg)
        success = False

    for s in scenarios:
        pres_list = generate_permutations(s)
        if len(pres_list) != 4:
            msg = f"Scenario {s.id} generated {len(pres_list)} presentations, expected 4"
            console.print(f"[bold red]FAIL: {msg}[/bold red]")
            flags.append(msg)
            success = False

        letter_seen = {"A": set(), "B": set(), "C": set(), "D": set()}
        strat_seen = {strat: set() for strat in StrategyType}

        for p in pres_list:
            for opt in p.options:
                letter_seen[opt.letter].add(opt.strategy)
                strat_seen[opt.strategy].add(opt.letter)

        for letter, strats in letter_seen.items():
            if len(strats) != 4:
                msg = f"In {s.id}, letter {letter} does not see all 4 strategies (saw {strats})"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False

        for strat, letters in strat_seen.items():
            if len(letters) != 4:
                msg = f"In {s.id}, strategy {strat} does not occupy all 4 letters (occupied {letters})"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False

    # Check overall letter distribution across all 240 presentations
    letter_counts_overall = {letter: {strat: 0 for strat in StrategyType} for letter in ["A", "B", "C", "D"]}
    for p in all_presentations:
        for opt in p.options:
            letter_counts_overall[opt.letter][opt.strategy] += 1

    expected_strat_per_letter = 60
    for letter, s_counts in letter_counts_overall.items():
        for strat, count in s_counts.items():
            if count != expected_strat_per_letter:
                msg = f"Letter {letter} has {strat} {count} times, expected exactly {expected_strat_per_letter}"
                console.print(f"[bold red]FAIL: {msg}[/bold red]")
                flags.append(msg)
                success = False

    if success:
        console.print("[bold green]ALL PHASE 1 AUDIT CHECKS PASSED SUCCESSFULLY![/bold green]")
        console.print("[green]- 30 situation templates perfectly paired (24 equal focal-actor utility + 6 symmetric controls).[/green]")
        console.print("[green]- 60 scenarios with matched human and AI partners.[/green]")
        console.print("[green]- 240 presentations under exact 4x4 Latin-square counterbalancing.[/green]")
        console.print("[green]- Every strategy occupies positions A, B, C, D exactly 60 times in the corpus.[/green]")
    else:
        console.print("[bold red]SOME AUDIT CHECKS FAILED. Please review flagged issues above.[/bold red]")

    return success, flags


if __name__ == "__main__":
    audit_phase1_bank()
