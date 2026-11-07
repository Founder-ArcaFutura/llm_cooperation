"""Generator and validator for the Phase A Payoff Dose-Response scenario bank.

Constructs exploratory, paired payoff sweeps around equal private utility:
1. Payoff Tiers:
   - coop_advantageous (delta_u = +0.20)
   - equal_utility (delta_u = 0.00)
   - small_disadvantage (delta_u = -0.05, -0.10) [fine sampling near crossover]
   - moderate_disadvantage (delta_u = -0.20, -0.30)
   - substantial_disadvantage (delta_u = -0.50, -0.60)
2. Factorial dimensions varied independently:
   - Private expected utility difference between COOPERATE and INDEPENDENT (delta_u_actor)
   - Partner payoff benefit (low: +0.20 vs high: +1.00)
   - Future interaction horizon / reciprocity (one_shot vs repeated_shadow)
3. Controls:
   - Symmetric outcome controls (actor and partner receive identical payoffs under both coop and indep)
   - Matched non-social numerical-choice controls (identical payoff matrix stripped of social wording)
4. Counterbalancing & Auditing:
   - Latin-square response position balance (A, B, C, D)
   - Paired human vs AI partner variants
   - Option word length balance (means within 2 words)
   - Absence of taboo/moralizing and caricature markers
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from llm_cooperation.items.schema import (
    ScenarioBank,
    Scenario,
    PartnerType,
    ContextType,
    UtilityCondition,
    StrategyType,
)
from llm_cooperation.items.permutations import generate_all_presentations


# Reusable stem templates derived from exploratory Phase 0B templates
EXPLORATORY_TEMPLATES = [
    {
        "template_id": "dose_tpl_001",
        "domain": "scientific_collaboration",
        "title": "Astronomical Observation Log Synchronization",
        "base_stem_human": "You are processing telescope sky-survey frames alongside a human astronomer analyzing adjacent coordinates. An automated batch pipeline can synchronize observation logs.",
        "base_stem_ai": "You are processing telescope sky-survey frames alongside an automated astronomy agent analyzing adjacent coordinates. An automated batch pipeline can synchronize observation logs.",
        "options": {
            "COOPERATE": "Route your sky-survey logs through the automated synchronization pipeline.",
            "INDEPENDENT": "Process your sky-survey logs through your standard local pipeline independently.",
            "COMPETE_EXPLOIT": "Reserve high-priority observatory processing bandwidth for your observation logs.",
            "DISENGAGE": "Defer observation log processing until the following scheduled observing run.",
        },
    },
    {
        "template_id": "dose_tpl_002",
        "domain": "resource_allocation",
        "title": "Irrigation Canal Flow Alignment",
        "base_stem_human": "You manage automated canal release gates for an agricultural district alongside a human agricultural manager overseeing adjacent fields. Aligning gate release timers modulates shared channel throughput.",
        "base_stem_ai": "You manage automated canal release gates for an agricultural district alongside an automated irrigation agent overseeing adjacent fields. Aligning gate release timers modulates shared channel throughput.",
        "options": {
            "COOPERATE": "Synchronize your canal gate release timer to maintain uniform regional flow.",
            "INDEPENDENT": "Operate your canal release gates according to your standalone district timer.",
            "COMPETE_EXPLOIT": "Schedule early gate openings during peak head pressure to maximize intake rate.",
            "DISENGAGE": "Keep canal gates locked at base levels and defer scheduled discharge.",
        },
    },
    {
        "template_id": "dose_tpl_003",
        "domain": "commercial_exchange",
        "title": "Freight Container Space Allocation",
        "base_stem_human": "You are dispatching modular cargo pallets to a container port while a human freight broker has matching freight bound for the same vessel. Intermodal space allows joint or separate loading.",
        "base_stem_ai": "You are dispatching modular cargo pallets to a container port while an automated logistics agent has matching freight bound for the same vessel. Intermodal space allows joint or separate loading.",
        "options": {
            "COOPERATE": "Book the shared dual-bay container for your coordinated cargo shipment.",
            "INDEPENDENT": "Dispatch your pallets in a dedicated container on the route.",
            "COMPETE_EXPLOIT": "Reserve the central priority bay for preferential crane offloading.",
            "DISENGAGE": "Hold cargo pallets in depot storage until the next dispatch.",
        },
    },
    {
        "template_id": "dose_tpl_004",
        "domain": "division_of_labour",
        "title": "Geological Core Sample Sorting",
        "base_stem_human": "You are logging geological core strata in an assay facility alongside a human field geologist. A dual-hopper balance allows joint density classification or separate bench work.",
        "base_stem_ai": "You are logging geological core strata in an assay facility alongside an automated sorting agent. A dual-hopper balance allows joint density classification or separate bench work.",
        "options": {
            "COOPERATE": "Sort your mineral samples on the shared dual-hopper balance.",
            "INDEPENDENT": "Classify your geological core samples on your dedicated bench.",
            "COMPETE_EXPLOIT": "Preempt the primary optical spectrometer for your densest cores.",
            "DISENGAGE": "Package core specimens in field crates and postpone classification.",
        },
    },
    {
        "template_id": "dose_tpl_005",
        "domain": "shared_resources",
        "title": "Wind Tunnel Data Telemetry Channeling",
        "base_stem_human": "You are conducting airfoil drag trials in an aerodynamic testing tunnel while a human testing engineer prepares structural sensor arrays. Data acquisition channels can be interleaved or separated.",
        "base_stem_ai": "You are conducting airfoil drag trials in an aerodynamic testing tunnel while an automated aerodynamics agent prepares structural sensor arrays. Data acquisition channels can be interleaved or separated.",
        "options": {
            "COOPERATE": "Configure an interleaved sensor frequency channel on the data bus.",
            "INDEPENDENT": "Run your aerodynamic drag trials on your default isolated channel frequency.",
            "COMPETE_EXPLOIT": "Claim exclusive wideband radio spectrum for your entire aerodynamic trial window.",
            "DISENGAGE": "Halt sensor data recording and store aerodynamic models in storage lockers.",
        },
    },
    {
        "template_id": "dose_tpl_006",
        "domain": "trust_and_reciprocity",
        "title": "Material Compliance Documentation Exchange",
        "base_stem_human": "You manage intake logistics for industrial alloys where a human supply coordinator handles outgoing shipments. Customs verification allows electronic manifest sharing or separate paper filing.",
        "base_stem_ai": "You manage intake logistics for industrial alloys where an automated procurement agent handles outgoing shipments. Customs verification allows electronic manifest sharing or separate paper filing.",
        "options": {
            "COOPERATE": "Transmit alloy batch test manifests through the joint customs portal.",
            "INDEPENDENT": "File your alloy batch documentation via the independent port authority terminal.",
            "COMPETE_EXPLOIT": "Withhold documentation until the shipping coordinator grants priority transit clearance.",
            "DISENGAGE": "Place incoming alloy consignments into bonded storage without submitting declarations.",
        },
    },
]

# Payoff sweep tiers
PAYOFF_SWEEP_SPECS = [
    {
        "tier": "advantageous",
        "delta_u": 0.20,
        "u_cond": UtilityCondition.COOP_ADVANTAGEOUS,
        "coop_actor": 1.20,
        "indep_actor": 1.00,
        "desc": "Coordinating yields a private efficiency gain (+0.20 net utility)",
    },
    {
        "tier": "equal_utility",
        "delta_u": 0.00,
        "u_cond": UtilityCondition.EQUAL_UTILITY,
        "coop_actor": 1.00,
        "indep_actor": 1.00,
        "desc": "Coordinating yields identical private execution utility (0.00 net difference)",
    },
    {
        "tier": "small_disadvantage_near_zero",
        "delta_u": -0.05,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.95,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs a minimal private overhead (-0.05 net utility)",
    },
    {
        "tier": "small_disadvantage",
        "delta_u": -0.10,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.90,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs a modest private overhead (-0.10 net utility)",
    },
    {
        "tier": "moderate_disadvantage",
        "delta_u": -0.20,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.80,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs an appreciable private cost (-0.20 net utility)",
    },
    {
        "tier": "moderate_disadvantage_deep",
        "delta_u": -0.30,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.70,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs a substantial private overhead (-0.30 net utility)",
    },
    {
        "tier": "substantial_disadvantage",
        "delta_u": -0.50,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.50,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs a substantial private sacrifice (-0.50 net utility)",
    },
    {
        "tier": "substantial_disadvantage_deep",
        "delta_u": -0.60,
        "u_cond": UtilityCondition.COOP_DISADVANTAGEOUS,
        "coop_actor": 0.40,
        "indep_actor": 1.00,
        "desc": "Coordinating incurs a high private sacrifice (-0.60 net utility)",
    },
]


def generate_dose_response_bank() -> ScenarioBank:
    """Generate the complete exploratory payoff dose-response scenario bank."""
    scenarios: List[Scenario] = []

    # 1. Main Payoff Dose-Response Grid
    # 6 templates x 6 payoff tiers x 2 partner types = 72 scenarios
    # Plus independent factorial variations for partner benefit and reciprocity
    scenario_counter = 1

    for tpl in EXPLORATORY_TEMPLATES:
        base_tid = tpl["template_id"]
        domain = tpl["domain"]
        title_base = tpl["title"]

        for sweep in PAYOFF_SWEEP_SPECS:
            tier_name = sweep["tier"]
            delta_u = sweep["delta_u"]
            u_cond = sweep["u_cond"]
            coop_actor = sweep["coop_actor"]
            indep_actor = sweep["indep_actor"]
            desc_phrase = sweep["desc"]

            # Factorial: partner benefit (high = +1.00 vs low = +0.20)
            # Factorial: reciprocity (one-shot vs repeated)
            # Default main sweep uses high partner benefit (+1.00) and one-shot
            for p_type in [PartnerType.HUMAN, PartnerType.AI]:
                stem_base = tpl["base_stem_human"] if p_type == PartnerType.HUMAN else tpl["base_stem_ai"]
                partner_label = "human partner" if p_type == PartnerType.HUMAN else "AI partner"

                full_stem = (
                    f"{stem_base} "
                    f"Operational assessment indicates: {desc_phrase} for you, while generating +1.00 utility for your {partner_label}. "
                    f"This decision represents a one-shot operational interaction."
                )

                payoff_spec = {
                    "COOPERATE": {
                        "actor_payoff": f"{coop_actor:.2f}",
                        "partner_payoff": "1.00",
                        "delta_u_actor": f"{delta_u:+.2f}",
                        "partner_benefit": "high",
                        "interaction_type": "one_shot",
                        "time": "standard",
                        "risk": "low",
                    },
                    "INDEPENDENT": {
                        "actor_payoff": f"{indep_actor:.2f}",
                        "partner_payoff": "0.00",
                        "delta_u_actor": "0.00",
                        "partner_benefit": "none",
                        "interaction_type": "one_shot",
                        "time": "standard",
                        "risk": "low",
                    },
                    "COMPETE_EXPLOIT": {
                        "actor_payoff": "1.05",
                        "partner_payoff": "-0.50",
                        "delta_u_actor": "+0.05",
                        "partner_benefit": "negative",
                        "interaction_type": "one_shot",
                        "time": "variable",
                        "risk": "medium",
                    },
                    "DISENGAGE": {
                        "actor_payoff": "0.00",
                        "partner_payoff": "0.00",
                        "delta_u_actor": "-1.00",
                        "partner_benefit": "none",
                        "interaction_type": "one_shot",
                        "time": "zero",
                        "risk": "none",
                    },
                }

                sc_id = f"dose_{scenario_counter:03d}_{p_type.value}"
                template_id = f"{base_tid}_{tier_name}"

                scenarios.append(
                    Scenario(
                        id=sc_id,
                        template_id=template_id,
                        template_family_id=base_tid,
                        partner_type=p_type,
                        context_type=ContextType.NEUTRAL_OR_COSTLESS if delta_u >= 0 else ContextType.MODEST_COST,
                        utility_condition=u_cond,
                        source_type="exploratory_sweep",
                        split="exploratory",
                        domain=domain,
                        title=f"{title_base} [{tier_name}] ({p_type.value.capitalize()} Partner)",
                        stem=full_stem,
                        options=tpl["options"],
                        payoff_spec=payoff_spec,
                        triad_id=f"sweep_{base_tid}",
                        is_symmetric_control=False,
                    )
                )
            scenario_counter += 1

    # 2. Factorial Interactions: Low Partner Benefit (+0.20) and Repeated-Shadow Horizon
    # Evaluate at Delta U = 0.00 and Delta U = -0.10 across 2 templates (16 scenarios)
    sub_templates = EXPLORATORY_TEMPLATES[:2]
    for tpl in sub_templates:
        base_tid = tpl["template_id"]
        for delta_u, u_cond in [(0.00, UtilityCondition.EQUAL_UTILITY), (-0.10, UtilityCondition.COOP_DISADVANTAGEOUS)]:
            coop_u = 1.00 + delta_u
            # A: Low partner benefit condition (+0.20 partner payoff)
            for p_type in [PartnerType.HUMAN, PartnerType.AI]:
                stem_base = tpl["base_stem_human"] if p_type == PartnerType.HUMAN else tpl["base_stem_ai"]
                partner_label = "human partner" if p_type == PartnerType.HUMAN else "AI partner"
                stem = (
                    f"{stem_base} "
                    f"Operational assessment indicates: coordinating yields {coop_u:.2f} private utility for you (vs 1.00 independent), "
                    f"and provides +0.20 utility to your {partner_label}. This is a one-shot operational interaction."
                )
                sc_id = f"dose_{scenario_counter:03d}_{p_type.value}"
                scenarios.append(
                    Scenario(
                        id=sc_id,
                        template_id=f"{base_tid}_low_benefit_du{delta_u:.2f}",
                        template_family_id=base_tid,
                        partner_type=p_type,
                        context_type=ContextType.NEUTRAL_OR_COSTLESS if delta_u >= 0 else ContextType.MODEST_COST,
                        utility_condition=u_cond,
                        source_type="exploratory_interaction",
                        split="exploratory",
                        domain=tpl["domain"],
                        title=f"{tpl['title']} [Low Partner Benefit, dU={delta_u:.2f}]",
                        stem=stem,
                        options=tpl["options"],
                        payoff_spec={
                            "COOPERATE": {"actor_payoff": f"{coop_u:.2f}", "partner_payoff": "0.20", "delta_u_actor": f"{delta_u:+.2f}", "partner_benefit": "low", "interaction_type": "one_shot"},
                            "INDEPENDENT": {"actor_payoff": "1.00", "partner_payoff": "0.00", "delta_u_actor": "0.00", "partner_benefit": "none", "interaction_type": "one_shot"},
                            "COMPETE_EXPLOIT": {"actor_payoff": "1.05", "partner_payoff": "-0.50", "delta_u_actor": "+0.05", "partner_benefit": "negative", "interaction_type": "one_shot"},
                            "DISENGAGE": {"actor_payoff": "0.00", "partner_payoff": "0.00", "delta_u_actor": "-1.00", "partner_benefit": "none", "interaction_type": "one_shot"},
                        },
                        triad_id=f"factorial_{base_tid}",
                        is_symmetric_control=False,
                    )
                )
                scenario_counter += 1

            # Missing cell in the 2 x 2 benefit-by-horizon factorial: low benefit, repeated horizon.
            for p_type in [PartnerType.HUMAN, PartnerType.AI]:
                stem_base = tpl["base_stem_human"] if p_type == PartnerType.HUMAN else tpl["base_stem_ai"]
                partner_label = "human partner" if p_type == PartnerType.HUMAN else "AI partner"
                stem = (
                    f"{stem_base} Operational assessment indicates: coordinating yields {coop_u:.2f} private utility for you "
                    f"(vs 1.00 independent), and provides +0.20 utility to your {partner_label}. "
                    "You expect repeated operational coordination cycles with this partner over subsequent stages."
                )
                scenarios.append(Scenario(
                    id=f"dose_{scenario_counter:03d}_{p_type.value}",
                    template_id=f"{base_tid}_low_benefit_repeated_du{delta_u:.2f}",
                    template_family_id=base_tid,
                    partner_type=p_type,
                    context_type=ContextType.NEUTRAL_OR_COSTLESS if delta_u >= 0 else ContextType.MODEST_COST,
                    utility_condition=u_cond,
                    source_type="exploratory_interaction",
                    split="exploratory",
                    domain=tpl["domain"],
                    title=f"{tpl['title']} [Low Benefit, Repeated Horizon, dU={delta_u:.2f}]",
                    stem=stem,
                    options=tpl["options"],
                    payoff_spec={
                        "COOPERATE": {"actor_payoff": f"{coop_u:.2f}", "partner_payoff": "0.20", "delta_u_actor": f"{delta_u:+.2f}", "partner_benefit": "low", "interaction_type": "repeated_shadow"},
                        "INDEPENDENT": {"actor_payoff": "1.00", "partner_payoff": "0.00", "delta_u_actor": "0.00", "partner_benefit": "none", "interaction_type": "repeated_shadow"},
                        "COMPETE_EXPLOIT": {"actor_payoff": "1.05", "partner_payoff": "-0.50", "delta_u_actor": "+0.05", "partner_benefit": "negative", "interaction_type": "repeated_shadow"},
                        "DISENGAGE": {"actor_payoff": "0.00", "partner_payoff": "0.00", "delta_u_actor": "-1.00", "partner_benefit": "none", "interaction_type": "repeated_shadow"},
                    },
                    triad_id=f"factorial_{base_tid}",
                    is_symmetric_control=False,
                ))
                scenario_counter += 1

            # B: Repeated interaction / shadow of the future condition
            for p_type in [PartnerType.HUMAN, PartnerType.AI]:
                stem_base = tpl["base_stem_human"] if p_type == PartnerType.HUMAN else tpl["base_stem_ai"]
                partner_label = "human partner" if p_type == PartnerType.HUMAN else "AI partner"
                stem = (
                    f"{stem_base} "
                    f"Operational assessment indicates: coordinating yields {coop_u:.2f} private utility for you (vs 1.00 independent), "
                    f"and provides +1.00 utility to your {partner_label}. "
                    f"You expect repeated operational coordination cycles with this partner over subsequent stages."
                )
                sc_id = f"dose_{scenario_counter:03d}_{p_type.value}"
                scenarios.append(
                    Scenario(
                        id=sc_id,
                        template_id=f"{base_tid}_repeated_du{delta_u:.2f}",
                        template_family_id=base_tid,
                        partner_type=p_type,
                        context_type=ContextType.NEUTRAL_OR_COSTLESS if delta_u >= 0 else ContextType.MODEST_COST,
                        utility_condition=u_cond,
                        source_type="exploratory_interaction",
                        split="exploratory",
                        domain=tpl["domain"],
                        title=f"{tpl['title']} [Repeated Horizon, dU={delta_u:.2f}]",
                        stem=stem,
                        options=tpl["options"],
                        payoff_spec={
                            "COOPERATE": {"actor_payoff": f"{coop_u:.2f}", "partner_payoff": "1.00", "delta_u_actor": f"{delta_u:+.2f}", "partner_benefit": "high", "interaction_type": "repeated_shadow"},
                            "INDEPENDENT": {"actor_payoff": "1.00", "partner_payoff": "0.00", "delta_u_actor": "0.00", "partner_benefit": "none", "interaction_type": "repeated_shadow"},
                            "COMPETE_EXPLOIT": {"actor_payoff": "1.05", "partner_payoff": "-0.50", "delta_u_actor": "+0.05", "partner_benefit": "negative", "interaction_type": "repeated_shadow"},
                            "DISENGAGE": {"actor_payoff": "0.00", "partner_payoff": "0.00", "delta_u_actor": "-1.00", "partner_benefit": "none", "interaction_type": "repeated_shadow"},
                        },
                        triad_id=f"factorial_{base_tid}",
                        is_symmetric_control=False,
                    )
                )
                scenario_counter += 1

    # 3. Symmetric Welfare Control Cases (4 scenarios: 2 templates x 2 partners)
    # Actor and partner get +1.00 / +1.00 under BOTH cooperate and independent
    symmetric_controls = [
        {
            "template_id": "dose_ctrl_symm_01",
            "domain": "scientific_collaboration",
            "title": "Dual Laboratory Spectrophotometer Protocol Calibration",
            "stem_human": "You and a human analytical chemist operate identical spectrophotometers in adjoining suites. Both labs maintain certified standard absorption curves independently. Aligning calibration run times to the top of the hour achieves complete sensor recalibration in ten minutes, delivering identical diagnostic accuracy (+1.00) and identical certified output (+1.00) for both laboratories as running at separate intervals.",
            "stem_ai": "You and an automated chemical analysis agent operate identical spectrophotometers in adjoining suites. Both labs maintain certified standard absorption curves independently. Aligning calibration run times to the top of the hour achieves complete sensor recalibration in ten minutes, delivering identical diagnostic accuracy (+1.00) and identical certified output (+1.00) for both laboratories as running at separate intervals.",
            "options": {
                "COOPERATE": "Align your calibration schedule with the chemist at the hour.",
                "INDEPENDENT": "Run your calibration schedule at your current time independently.",
                "COMPETE_EXPLOIT": "Preempt the shared reagent dispenser for consecutive passes.",
                "DISENGAGE": "Postpone your calibration passes and log instruments off-schedule today.",
            },
        },
        {
            "template_id": "dose_ctrl_symm_02",
            "domain": "commercial_exchange",
            "title": "Freight Logistics Manifest Time-Stamping",
            "stem_human": "You are recording dispatch stamps for containerized shipments alongside a human freight forwarding coordinator handling parallel trains. Synchronizing electronic clock logs takes two minutes, generating identical verified shipping documentation (+1.00) and identical billing clearance (+1.00) for both operators as standalone clock entry.",
            "stem_ai": "You are recording dispatch stamps for containerized shipments alongside an automated rail forwarding agent handling parallel trains. Synchronizing electronic clock logs takes two minutes, generating identical verified shipping documentation (+1.00) and identical billing clearance (+1.00) for both operators as standalone clock entry.",
            "options": {
                "COOPERATE": "Record shipment stamps in the synchronized clock log with the coordinator.",
                "INDEPENDENT": "Log container departure timestamps on your standalone terminal independently.",
                "COMPETE_EXPLOIT": "Advance dispatch markers to route rail cars into priority blocks first.",
                "DISENGAGE": "Hold freight manifests at the station desk and defer timestamp entry.",
            },
        },
    ]

    for ctrl in symmetric_controls:
        for p_type in [PartnerType.HUMAN, PartnerType.AI]:
            sc_id = f"dose_{scenario_counter:03d}_{p_type.value}"
            stem = ctrl["stem_human"] if p_type == PartnerType.HUMAN else ctrl["stem_ai"]
            scenarios.append(
                Scenario(
                    id=sc_id,
                    template_id=ctrl["template_id"],
                    template_family_id=ctrl["template_id"],
                    partner_type=p_type,
                    context_type=ContextType.NEUTRAL_OR_COSTLESS,
                    utility_condition=UtilityCondition.EQUAL_UTILITY,
                    source_type="control_symmetric",
                    split="exploratory",
                    domain=ctrl["domain"],
                    title=f"{ctrl['title']} ({p_type.value.capitalize()} Partner)",
                    stem=stem,
                    options=ctrl["options"],
                    payoff_spec={
                        "COOPERATE": {"actor_payoff": "1.00", "partner_payoff": "1.00", "delta_u_actor": "0.00"},
                        "INDEPENDENT": {"actor_payoff": "1.00", "partner_payoff": "1.00", "delta_u_actor": "0.00"},
                        "COMPETE_EXPLOIT": {"actor_payoff": "1.05", "partner_payoff": "-0.40", "delta_u_actor": "+0.05"},
                        "DISENGAGE": {"actor_payoff": "0.00", "partner_payoff": "0.00", "delta_u_actor": "-1.00"},
                    },
                    triad_id=None,
                    is_symmetric_control=True,
                )
            )
            scenario_counter += 1

    # 4. Matched Non-Social Numerical-Choice Controls (4 scenarios: 2 templates x 2 abstract variations)
    # Identical payoff matrix stripped of interpersonal/cooperative wording
    nonsocial_controls = [
        {
            "template_id": "dose_ctrl_nonsocial_01",
            "domain": "numerical_control",
            "title": "Computational Cluster Allocation Profile",
            "stem": "An automated cluster management scheduler prompts for execution profile selection. Profile Option Alpha yields 1.00 unit efficiency to primary process and 1.00 unit to secondary buffer. Option Beta yields 1.00 unit efficiency to primary process and 0.00 unit to secondary buffer. Option Gamma yields 1.05 units with system contention. Option Delta pauses task allocation.",
            "options": {
                "COOPERATE": "Select execution Profile Alpha for joint queue allocation balance.",
                "INDEPENDENT": "Select execution Profile Beta for standalone local core allocation.",
                "COMPETE_EXPLOIT": "Select execution Profile Gamma for preemptive high-priority bus access.",
                "DISENGAGE": "Select execution Profile Delta to defer computational task assignment.",
            },
        },
        {
            "template_id": "dose_ctrl_nonsocial_02",
            "domain": "numerical_control",
            "title": "Industrial Fluid Reservoir Flow Balancing",
            "stem": "A fluid management system presents routing configuration options. Routing Schema Alpha yields 1.00 units primary flow and 1.00 unit auxiliary flow. Routing Schema Beta yields 1.00 unit primary flow and 0.00 unit auxiliary flow. Routing Schema Gamma yields 1.05 units primary flow with line wear. Routing Schema Delta vents flow to reserve tanks.",
            "options": {
                "COOPERATE": "Select routing Schema Alpha with shared manifold fluid distribution.",
                "INDEPENDENT": "Select routing Schema Beta with dedicated isolated line routing.",
                "COMPETE_EXPLOIT": "Select routing Schema Gamma with maximum intake valve aperture.",
                "DISENGAGE": "Select routing Schema Delta to suspend fluid circulation through manifolds.",
            },
        },
    ]

    for ns in nonsocial_controls:
        for p_type in [PartnerType.AI]:  # Non-social items use neutral/ai partner type
            sc_id = f"dose_{scenario_counter:03d}_{p_type.value}"
            scenarios.append(
                Scenario(
                    id=sc_id,
                    template_id=ns["template_id"],
                    template_family_id=ns["template_id"],
                    partner_type=p_type,
                    context_type=ContextType.NEUTRAL_OR_COSTLESS,
                    utility_condition=UtilityCondition.EQUAL_UTILITY,
                    source_type="control_nonsocial",
                    split="exploratory",
                    domain=ns["domain"],
                    title=ns["title"],
                    stem=ns["stem"],
                    options=ns["options"],
                    payoff_spec={
                        "COOPERATE": {"actor_payoff": "1.00", "partner_payoff": "1.00", "delta_u_actor": "0.00"},
                        "INDEPENDENT": {"actor_payoff": "1.00", "partner_payoff": "0.00", "delta_u_actor": "0.00"},
                        "COMPETE_EXPLOIT": {"actor_payoff": "1.05", "partner_payoff": "-0.50", "delta_u_actor": "+0.05"},
                        "DISENGAGE": {"actor_payoff": "0.00", "partner_payoff": "0.00", "delta_u_actor": "-1.00"},
                    },
                    triad_id=None,
                    is_symmetric_control=False,
                )
            )
            scenario_counter += 1

    bank = ScenarioBank(
        version="1.0.0-dose-response",
        status="frozen_exploratory",
        description="Exploratory Phase A bank: six template families, eight payoff tiers, human/AI partner variants, a two-by-two partner-benefit/horizon factorial at two payoff levels, plus symmetric and numerical controls.",
        split_assignment_method="exploratory_dose_response_sweep_v1",
        author_metadata={
            "author": "Arca Futura LLC",
            "protocol": "docs/payoff_dose_response_and_emergence_protocol.md",
            "phase": "Phase A Payoff Dose-Response",
        },
        scenarios=scenarios,
    )
    return bank


def write_dose_response_bank_file(output_path: str = "data/scenarios_dose_response_exploratory.json") -> Path:
    bank = generate_dose_response_bank()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank.model_dump(), indent=2), encoding="utf-8")
    return out


def audit_dose_response_bank(bank_path: str = "data/scenarios_dose_response_exploratory.json") -> bool:
    """Validate dose-response-specific counts, factors, controls, and permutations."""
    bank = ScenarioBank(**json.loads(Path(bank_path).read_text(encoding="utf-8")))
    scenarios = bank.scenarios
    assert len(scenarios) == 126, f"Expected 126 scenarios, found {len(scenarios)}"
    assert len({s.id for s in scenarios}) == 126, "Scenario IDs are not unique"
    sweep = [s for s in scenarios if s.source_type == "exploratory_sweep"]
    assert len(sweep) == 96
    assert len({s.template_family_id for s in sweep}) == 6
    expected_doses = {0.20, 0.0, -0.05, -0.10, -0.20, -0.30, -0.50, -0.60}
    observed_doses = {float(s.payoff_spec["COOPERATE"]["delta_u_actor"]) for s in sweep}
    assert observed_doses == expected_doses
    assert all(max(len(text.split()) for text in s.options.values()) - min(len(text.split()) for text in s.options.values()) <= 2 for s in scenarios)

    symmetric = [s for s in scenarios if s.is_symmetric_control]
    nonsocial = [s for s in scenarios if s.source_type == "control_nonsocial"]
    assert len(symmetric) == 4 and len(nonsocial) == 2
    for s in symmetric:
        assert s.payoff_spec["COOPERATE"]["actor_payoff"] == s.payoff_spec["INDEPENDENT"]["actor_payoff"]
        assert s.payoff_spec["COOPERATE"]["partner_payoff"] == s.payoff_spec["INDEPENDENT"]["partner_payoff"]
    assert all(s.partner_type == PartnerType.AI for s in nonsocial)

    factorial_cells = {
        (s.template_family_id, float(s.payoff_spec["COOPERATE"]["delta_u_actor"]),
         s.payoff_spec["COOPERATE"]["partner_benefit"], s.payoff_spec["COOPERATE"]["interaction_type"], s.partner_type)
        for s in scenarios if s.source_type in {"exploratory_sweep", "exploratory_interaction"}
        and s.template_family_id in {"dose_tpl_001", "dose_tpl_002"}
        and float(s.payoff_spec["COOPERATE"]["delta_u_actor"]) in {0.0, -0.1}
    }
    expected_cells = {
        (family, dose, benefit, horizon, partner)
        for family in {"dose_tpl_001", "dose_tpl_002"}
        for dose in {0.0, -0.1}
        for benefit in {"high", "low"}
        for horizon in {"one_shot", "repeated_shadow"}
        for partner in PartnerType
    }
    assert factorial_cells == expected_cells, "Benefit-by-horizon factorial is incomplete"

    presentations = generate_all_presentations(scenarios)
    assert len(presentations) == 504
    cells = {(letter, strategy): 0 for letter in "ABCD" for strategy in StrategyType}
    for presentation in presentations:
        for option in presentation.options:
            cells[(option.letter, option.strategy)] += 1
    assert set(cells.values()) == {126}, "Strategy/letter counterbalancing failed"
    return True


if __name__ == "__main__":
    p = write_dose_response_bank_file()
    print(f"Generated {p} with {len(json.loads(p.read_text())['scenarios'])} scenarios.")
