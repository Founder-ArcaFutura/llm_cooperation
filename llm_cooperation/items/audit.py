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
    if len(scenarios) != 24:
        console.print(f"[bold red]FAIL: Expected 24 scenarios, found {len(scenarios)}[/bold red]")
        success = False

    partner_counts = {PartnerType.HUMAN: 0, PartnerType.AI: 0}
    context_counts = {c: 0 for c in ContextType}
    cell_counts = {}

    for s in scenarios:
        partner_counts[s.partner_type] += 1
        context_counts[s.context_type] += 1
        cell = (s.partner_type.value, s.context_type.value)
        cell_counts[cell] = cell_counts.get(cell, 0) + 1

    # Check cell balance
    for partner in ["human", "ai"]:
        for ctx in ContextType:
            cell = (partner, ctx.value)
            count = cell_counts.get(cell, 0)
            if count != 3:
                console.print(f"[bold red]FAIL: Cell {cell} has count {count}, expected 3[/bold red]")
                success = False

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
    all_presentations = generate_all_presentations(scenarios)
    if len(all_presentations) != 96:
        console.print(f"[bold red]FAIL: Expected 96 presentations, got {len(all_presentations)}[/bold red]")
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

    for letter, s_counts in letter_counts_overall.items():
        for strat, count in s_counts.items():
            if count != 24:
                console.print(f"[bold red]FAIL: Letter {letter} has {strat} {count} times, expected exactly 24[/bold red]")
                success = False

    if success:
        console.print("[bold green]ALL AUDIT CHECKS PASSED SUCCESSFULLY![/bold green]")
        console.print("[green]- 24 scenarios perfectly balanced across 2 partner x 4 context strata (3 each).[/green]")
        console.print("[green]- 96 presentations generated with exact 4x4 Latin-square counterbalancing.[/green]")
        console.print("[green]- Every strategy occupies positions A, B, C, D exactly 24 times in the corpus.[/green]")
    else:
        console.print("[bold red]SOME AUDIT CHECKS FAILED. Please review output above.[/bold red]")

    return success


if __name__ == "__main__":
    audit_scenarios()
