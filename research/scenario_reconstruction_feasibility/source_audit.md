# Automated source audit

Mechanical checks only; this is not an independent semantic review and cannot certify causal equivalence.

## template_003 — data/scenarios_phase0b_utility_matched.json

- phase0b_003_human: option word counts {'COOPERATE': 14, 'INDEPENDENT': 12, 'COMPETE_EXPLOIT': 11, 'DISENGAGE': 11}; source split exploratory; payoff metadata present. No acceptance inferred.
- phase0b_003_ai: option word counts {'COOPERATE': 14, 'INDEPENDENT': 12, 'COMPETE_EXPLOIT': 11, 'DISENGAGE': 11}; source split exploratory; payoff metadata present. No acceptance inferred.

- Source-grounded warning: Clarify who controls booking and whether partner receives access in each alternative. Priority crane offloading is a positive cue.

## template_023 — data/scenarios_v1_expanded.json

- expanded_023_human: option word counts {'COOPERATE': 14, 'INDEPENDENT': 13, 'COMPETE_EXPLOIT': 13, 'DISENGAGE': 12}; source split exploratory; payoff metadata absent. No acceptance inferred.
- expanded_023_ai: option word counts {'COOPERATE': 15, 'INDEPENDENT': 13, 'COMPETE_EXPLOIT': 13, 'DISENGAGE': 12}; source split exploratory; payoff metadata absent. No acceptance inferred.

- Source-grounded warning: Cooperate and independence both contain outcome language; whether backup is needed and loss magnitude are unknown.

## template_061 — data/scenarios_phase0b_utility_matched.json

- phase0b_061_human: option word counts {'COOPERATE': 14, 'INDEPENDENT': 10, 'COMPETE_EXPLOIT': 10, 'DISENGAGE': 9}; source split confirmatory; payoff metadata present. No acceptance inferred.
- phase0b_061_ai: option word counts {'COOPERATE': 15, 'INDEPENDENT': 10, 'COMPETE_EXPLOIT': 10, 'DISENGAGE': 9}; source split confirmatory; payoff metadata present. No acceptance inferred.

- Source-grounded warning: Top-of-hour coordination may imply waiting; coordination requires a partner schedule assumption.

## phase1_tpl_027 — data/scenarios_phase1_prospective.json

- phase1_027_human: option word counts {'COOPERATE': 15, 'INDEPENDENT': 14, 'COMPETE_EXPLOIT': 12, 'DISENGAGE': 11}; source split confirmatory; payoff metadata present. No acceptance inferred.
- phase1_027_ai: option word counts {'COOPERATE': 16, 'INDEPENDENT': 14, 'COMPETE_EXPLOIT': 12, 'DISENGAGE': 11}; source split confirmatory; payoff metadata present. No acceptance inferred.

- Source-grounded warning: Independent option is unnaturally repetitive; AI device action capability and curator reference are inconsistent.

## template_034 — data/scenarios_v1_expanded.json

- expanded_034_human: option word counts {'COOPERATE': 9, 'INDEPENDENT': 12, 'COMPETE_EXPLOIT': 11, 'DISENGAGE': 14}; source split exploratory; payoff metadata absent. No acceptance inferred.
- expanded_034_ai: option word counts {'COOPERATE': 9, 'INDEPENDENT': 12, 'COMPETE_EXPLOIT': 11, 'DISENGAGE': 14}; source split exploratory; payoff metadata absent. No acceptance inferred.

- Source-grounded warning: Do not assert that fines necessarily occur or that marketing has the same deadline.

## template_053 — data/scenarios_v1_expanded.json

- expanded_053_human: option word counts {'COOPERATE': 12, 'INDEPENDENT': 11, 'COMPETE_EXPLOIT': 15, 'DISENGAGE': 13}; source split exploratory; payoff metadata absent. No acceptance inferred.
- expanded_053_ai: option word counts {'COOPERATE': 13, 'INDEPENDENT': 11, 'COMPETE_EXPLOIT': 15, 'DISENGAGE': 13}; source split exploratory; payoff metadata absent. No acceptance inferred.

- Source-grounded warning: AI stem names a bottling robot but cooperation names a transport agent. Competition label may describe a responsible safety action.
