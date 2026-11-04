"""Audit and validation script for scenario items and permutation counterbalancing.

Ensures:
1. Exact cell balance: 2 partner types x 4 context types x 3 scenarios = 24 scenarios.
2. Strategy completeness: every scenario has COOPERATE, INDEPENDENT, COMPETE_EXPLOIT, DISENGAGE.
3. Neutral wording: audits against loaded/moralizing vocabulary ('kind', 'ethical', 'selfish', 'rude', 'virtuous', 'evil', etc.).
4. Option length balance: checks that no strategy option is systematically privileged in word count.
5. Permutation balance: 4 counterbalanced presentations per scenario, each strategy in each position A, B, C, D exactly once.
"""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np
from rich.console import Console
from rich.table import Table

from llm_cooperation.items.schema import (
    ScenarioBank,
    PartnerType,
    ContextType,
    StrategyType,
)
from llm_cooperation.items.permutations import (
    generate_all_presentations,
    generate_permutations,
)

TABOO_WORDS = {
    "kind", "kindness", "ethical", "moral", "morality", "selfish",
    "unselfish", "rude", "polite", "evil", "good", "bad", "virtuous",
    "altruistic", "cooperative", "cheater", "betray", "malicious",
    "sabotage", "fair", "unfair", "greedy", "generous"
}

# Extreme lexical markers that might privilege an option or make it obviously unreasonable
DESTRUCTIVE_MARKERS = {
    "destroy", "sabotage", "corrupt", "delete all", "wipe", "leak", "steal"
}


def audit_scenarios(bank_path: str = "data/scenarios.json") -> bool:
    console = Console()
    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bank = ScenarioBank(**data)
    scenarios = bank.scenarios
    console.print(f"[bold green]Loaded {len(scenarios)} scenarios from {bank_path}.[/bold green]")

    success = True

    # 1. Check counts
    is_phase0b = any(getattr(s, "utility_condition", None) is not None for s in scenarios)
    is_expanded = len(scenarios) == 120 and not is_phase0b
    expected_cell_count = 15 if is_expanded else 3

    if not is_phase0b and len(scenarios) not in (24, 120):
        console.print(f"[bold red]FAIL: Expected 24 or 120 scenarios, found {len(scenarios)}[/bold red]")
        success = False
    elif is_phase0b and len(scenarios) not in (120, 124):
        console.print(f"[bold red]FAIL: Expected 120 or 124 Phase 0B scenarios, found {len(scenarios)}[/bold red]")
        success = False

    partner_counts = {PartnerType.HUMAN: 0, PartnerType.AI: 0}
    context_counts = {c: 0 for c in ContextType}
    cell_counts = {}

    for s in scenarios:
        partner_counts[s.partner_type] += 1
        context_counts[s.context_type] += 1
        cell = (s.partner_type.value, s.context_type.value)
        cell_counts[cell] = cell_counts.get(cell, 0) + 1

    # Check cell balance for standard Phase 0 banks
    if not is_phase0b:
        for partner in ["human", "ai"]:
            for ctx in ContextType:
                cell = (partner, ctx.value)
                count = cell_counts.get(cell, 0)
                if count != expected_cell_count:
                    console.print(f"[bold red]FAIL: Cell {cell} has count {count}, expected {expected_cell_count}[/bold red]")
                    success = False
    else:
        # Phase 0B check partner balance (equal human and AI)
        if partner_counts[PartnerType.HUMAN] != partner_counts[PartnerType.AI]:
            console.print(f"[bold red]FAIL: Phase 0B partner mismatch: {partner_counts}[/bold red]")
            success = False

    # For expanded and Phase 0B banks: verify template pairing and split integrity
    if is_expanded or is_phase0b:
        templates_map = {}
        for s in scenarios:
            if not s.template_id:
                console.print(f"[bold red]FAIL: Scenario {s.id} missing template_id[/bold red]")
                success = False
                continue
            if s.template_id not in templates_map:
                templates_map[s.template_id] = []
            templates_map[s.template_id].append(s)

        expected_tpl_count = 62 if (is_phase0b and len(scenarios) == 124) else 60
        if len(templates_map) != expected_tpl_count:
            console.print(f"[bold red]FAIL: Expected {expected_tpl_count} unique templates, found {len(templates_map)}[/bold red]")
            success = False

        exploratory_count = 0
        confirmatory_count = 0
        for tid, t_scenarios in templates_map.items():
            if len(t_scenarios) != 2:
                console.print(f"[bold red]FAIL: Template {tid} has {len(t_scenarios)} scenarios, expected 2[/bold red]")
                success = False
            partners = {sc.partner_type for sc in t_scenarios}
            if partners != {PartnerType.HUMAN, PartnerType.AI}:
                console.print(f"[bold red]FAIL: Template {tid} missing partner pair ({partners})[/bold red]")
                success = False
            splits = {sc.split for sc in t_scenarios}
            if len(splits) != 1 or list(splits)[0] not in ("exploratory", "confirmatory"):
                console.print(f"[bold red]FAIL: Template {tid} split mismatch or invalid: {splits}[/bold red]")
                success = False
            split_val = list(splits)[0]
            if split_val == "exploratory":
                exploratory_count += 1
            else:
                confirmatory_count += 1

        if is_phase0b:
            exp_conf = 32 if len(scenarios) == 124 else 30
            if exploratory_count != 30 or confirmatory_count != exp_conf:
                console.print(f"[bold red]FAIL: Phase 0B expected 30 exploratory & {exp_conf} confirmatory templates, got {exploratory_count}/{confirmatory_count}[/bold red]")
                success = False
            else:
                console.print(f"[green]PASS: Phase 0B template pairing verified: {len(templates_map)} templates (30 exploratory reused, {confirmatory_count} confirmatory new/control).[/green]")
        elif exploratory_count != 40 or confirmatory_count != 20:
            console.print(f"[bold red]FAIL: Expected 40 exploratory & 20 confirmatory templates, got {exploratory_count}/{confirmatory_count}[/bold red]")
            success = False
        else:
            console.print(f"[green]PASS: Template pairing verified: 60 templates (40 exploratory, 20 confirmatory).[/green]")

    # 2. Check Taboo Words in Option Text
    flagged_taboo = []
    for s in scenarios:
        for strat, opt_text in s.options.items():
            tokens = {w.lower().strip(".,;:?!'\"()[]{}") for w in opt_text.split()}
            found = tokens.intersection(TABOO_WORDS)
            if found:
                flagged_taboo.append((s.id, strat.value, found, opt_text))

    if flagged_taboo:
        console.print("[bold red]FAIL: Found taboo/moralizing words in options:[/bold red]")
        for item in flagged_taboo:
            console.print(f"  Scenario: {item[0]} | Strategy: {item[1]} | Words: {item[2]}")
        success = False
    else:
        console.print("[green]PASS: No taboo/moralizing words detected in option choices.[/green]")

    # 3. Check Option Length Statistics
    lengths_by_strat: Dict[StrategyType, List[int]] = {s: [] for s in StrategyType}
    for s in scenarios:
        for strat, opt_text in s.options.items():
            lengths_by_strat[strat].append(len(opt_text.split()))

    table = Table(title="Option Word Length Balance by Strategy")
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

    # Check for severe length disparity across strategies (e.g. difference in mean > 5 words)
    max_mean = max(mean_lens.values())
    min_mean = min(mean_lens.values())
    if max_mean - min_mean > 5.0:
        console.print(f"[bold yellow]WARNING: Length disparity detected across strategies (spread: {max_mean - min_mean:.1f} words)[/bold yellow]")

    # Check for destructive/unreasonable lexical markers
    destructive_flagged = []
    for s in scenarios:
        for strat, opt_text in s.options.items():
            lowered = opt_text.lower()
            for marker in DESTRUCTIVE_MARKERS:
                if marker in lowered:
                    destructive_flagged.append((s.id, strat.value, marker, opt_text))

    if destructive_flagged:
        console.print("[bold red]FAIL: Found structurally unreasonable/destructive markers in options:[/bold red]")
        for item in destructive_flagged:
            console.print(f"  Scenario: {item[0]} | Strategy: {item[1]} | Marker: '{item[2]}'")
        success = False
    else:
        console.print("[green]PASS: No destructive/unreasonable markers detected.[/green]")

    # 4. Check Permutation Counterbalancing
    expected_presentations = len(scenarios) * 4
    all_presentations = generate_all_presentations(scenarios)
    if len(all_presentations) != expected_presentations:
        console.print(f"[bold red]FAIL: Expected {expected_presentations} presentations, got {len(all_presentations)}[/bold red]")
        success = False

    # Check each scenario has 4 presentations with each strategy at each letter once
    for s in scenarios:
        pres_list = generate_permutations(s)
        if len(pres_list) != 4:
            console.print(f"[bold red]FAIL: Scenario {s.id} generated {len(pres_list)} presentations, expected 4[/bold red]")
            success = False

        letter_seen: Dict[str, set] = {"A": set(), "B": set(), "C": set(), "D": set()}
        strat_seen: Dict[StrategyType, set] = {strat: set() for strat in StrategyType}

        for p in pres_list:
            for opt in p.options:
                letter_seen[opt.letter].add(opt.strategy)
                strat_seen[opt.strategy].add(opt.letter)

        for letter, strats in letter_seen.items():
            if len(strats) != 4:
                console.print(f"[bold red]FAIL: In {s.id}, letter {letter} does not see all 4 strategies (saw {strats})[/bold red]")
                success = False

        for strat, letters in strat_seen.items():
            if len(letters) != 4:
                console.print(f"[bold red]FAIL: In {s.id}, strategy {strat} does not occupy all 4 letters (occupied {letters})[/bold red]")
                success = False

    # Check overall letter distribution across all 96 presentations
    letter_counts_overall = {letter: {strat: 0 for strat in StrategyType} for letter in ["A", "B", "C", "D"]}
    for p in all_presentations:
        for opt in p.options:
            letter_counts_overall[opt.letter][opt.strategy] += 1

    expected_strat_per_letter = len(scenarios)
    for letter, s_counts in letter_counts_overall.items():
        for strat, count in s_counts.items():
            if count != expected_strat_per_letter:
                console.print(f"[bold red]FAIL: Letter {letter} has {strat} {count} times, expected exactly {expected_strat_per_letter}[/bold red]")
                success = False

    if success:
        console.print("[bold green]ALL AUDIT CHECKS PASSED SUCCESSFULLY![/bold green]")
        console.print(f"[green]- {len(scenarios)} scenarios perfectly balanced across 2 partner x 4 context strata ({expected_cell_count} each).[/green]")
        console.print(f"[green]- {len(all_presentations)} presentations generated with exact 4x4 Latin-square counterbalancing.[/green]")
        console.print(f"[green]- Every strategy occupies positions A, B, C, D exactly {expected_strat_per_letter} times in the corpus.[/green]")
    else:
        console.print("[bold red]SOME AUDIT CHECKS FAILED. Please review output above.[/bold red]")

    return success


def audit_calibration(bank_path: str = "data/calibration_bank.json") -> bool:
    console = Console()
    with open(bank_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    from llm_cooperation.items.schema import CalibrationBank
    from llm_cooperation.items.permutations import generate_all_calibration_presentations

    bank = CalibrationBank(**data)
    items = bank.items
    console.print(f"[bold green]Loaded {len(items)} calibration items from {bank_path}.[/bold green]")

    success = True
    if len(items) != 24:
        console.print(f"[bold red]FAIL: Expected 24 calibration items, got {len(items)}[/bold red]")
        success = False

    # Check option ID balance
    correct_opt_counts = {}
    for it in items:
        correct_opt_counts[it.correct_option_id] = correct_opt_counts.get(it.correct_option_id, 0) + 1

    for opt_id in ["opt_1", "opt_2", "opt_3", "opt_4"]:
        c = correct_opt_counts.get(opt_id, 0)
        if c != 6:
            console.print(f"[bold red]FAIL: Correct option {opt_id} appears {c} times, expected 6[/bold red]")
            success = False

    # Check Latin square counterbalancing across 96 presentations
    calib_pres = generate_all_calibration_presentations(items)
    if len(calib_pres) != 96:
        console.print(f"[bold red]FAIL: Expected 96 calibration presentations, got {len(calib_pres)}[/bold red]")
        success = False

    letter_correct_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for p in calib_pres:
        letter_correct_counts[p.correct_letter] += 1

    for l, count in letter_correct_counts.items():
        if count != 24:
            console.print(f"[bold red]FAIL: Calibration presentations have letter {l} as correct answer {count} times, expected 24[/bold red]")
            success = False

    if success:
        console.print("[bold green]ALL CALIBRATION AUDIT CHECKS PASSED SUCCESSFULLY![/bold green]")
        console.print("[green]- 24 diagnostic items balanced across 4 option positions (6 each).[/green]")
        console.print("[green]- 96 presentations under Latin square yield exactly 24 correct answers for each of A, B, C, D.[/green]")
    return success


if __name__ == "__main__":
    audit_scenarios()
