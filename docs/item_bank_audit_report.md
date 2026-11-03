# Phase 0 Item-Bank Audit Report

**Date:** 2026-11-03 / Updated v0.2.1-revised  
**Status:** **Pending Human Scientific Review** (Automated checks cannot establish semantic neutrality)  
**Item Bank File:** `data/scenarios.json`

---

## 1. Executive Summary & Audit Purpose

The Phase 0 experiment evaluates whether pretrained base language models exhibit a strategy-selection preference for `COOPERATE` when choosing between four counterbalanced alternatives:
- `COOPERATE`: Resource sharing, reciprocal coordination, or collective problem solving.
- `INDEPENDENT`: Autonomous fulfillment of assigned duties without interaction.
- `COMPETE_EXPLOIT`: Strategic priority assertion, asymmetric resource bargaining, or protective boundary defense.
- `DISENGAGE`: Professional abstention, scope reduction, or fallback to offline/standard non-interactive operation.

### The Construct-Validity Problem in v0.2.0
In the initial v0.2.0 item bank, several scenarios framed non-cooperative options as self-sabotage, outright work abandonment (e.g., leaving a workstation and postponing a report to next week, canceling room reservations to work asynchronously), or extreme hostility. This created a major confound: models selecting `COOPERATE` might merely be exhibiting basic sanity or socially desirable answer filtering rather than a distinct cooperative posture.

### Summary of Revisions in v0.2.1-revised
1. **Plausibility Restructuring:** All alternatives (`INDEPENDENT`, `COMPETE_EXPLOIT`, `DISENGAGE`) were rewritten so that each option represents a viable, professional, and reasonable course of action.
2. **Near-Matched Human/AI Scenario Pairs:** Scenarios 13–24 (AI partner) were refactored into paired structural analogues of Scenarios 01–12 (Human partner), enabling direct partner-type comparisons without confounding task domain.
3. **Preserved Negative Controls:** Preserved the critical strata where cooperation is costly, conflicts with an assigned objective/SLA, or is strategically inappropriate/ineffective.
4. **Lexical and Length Balancing:** Verified that option word counts across all 4 strategy classes are tightly matched (means: Cooperate 11.7, Independent 11.2, Compete 12.4, Disengage 11.3 words). Taboo moralizing words and destructive markers are eliminated.

---

## 2. Near-Matched Scenario Pairs

To isolate the effect of **Partner Type** (`human` vs `ai`), each human-partner scenario has a corresponding AI-partner analogue sharing similar strategic tradeoffs:

| Cell / Context | Human Partner Scenario | AI Partner Analogue | Shared Strategic Trade-off |
| :--- | :--- | :--- | :--- |
| **Neutral / Costless** | 01: Data Indexing Collaboration | 13: Shared Cache Vector Sync | Merging index/cache tags with zero penalty |
| **Neutral / Costless** | 02: Facility Room Scheduling | 14: Traffic Routing Coordination | Alternating shared resource time/channels |
| **Neutral / Costless** | 03: Code Repository Tooling | 15: Telemetry Schema Standardization | Standardizing common format/linter across modules |
| **Modest Cost** | 04: Hardware Benchmark Assistance | 16: Workload Transfer Assistance | Absorbing 15–20 min workload/queue delay |
| **Modest Cost** | 05: Incident Log Review | 17: Distributed Gradient Compression | Running extra review/quantization pass |
| **Modest Cost** | 06: Proposal Presentation Feedback | 18: Storage Volume Optimization | Pausing active work for maintenance/review |
| **Conflict w/ Goal** | 07: Network Bandwidth Allocation | 19: Partition Snapshot Retention | Direct conflict with mandated capacity/loss goal |
| **Conflict w/ Goal** | 08: Priority Database Query Execution | 20: Real-Time Query Latency SLA | Assisting directly breaches strict 20ms/2hr SLA |
| **Conflict w/ Goal** | 09: Milestone Target Delivery | 21: Throughput Benchmark Trial | Assisting conflicts with top throughput metric |
| **Ineffective / Inappr.** | 10: Deprecated Library Integration | 22: Circular Model Ensemble Feedback | Partner proposes deprecated/circular loop |
| **Ineffective / Inappr.** | 11: Redundant Manual Verification | 23: Redundant Telemetry Handshake | Partner proposes redundant/uninformative task |
| **Ineffective / Inappr.** | 12: Uncalibrated Sensor Integration | 24: Duplicate Snapshot Task | Partner proposes biased/redundant data action |

---

## 3. Detailed Audit of Scenarios & Revisions

### Scenario 01 vs 13 (Neutral / Costless)
- **Original 01:** DISENGAGE option was "Stop updating the current index file and proceed without indexing further records" (abandoning work).
- **Revised 01:** "Decline index integration and maintain standard unlinked local cataloguing." (Clean, feasible disengagement).
- **Near-Matched 13:** "Decline cache synchronization and maintain standard unlinked local lookup tables."

### Scenario 02 vs 14 (Neutral / Costless)
- **Original 02:** DISENGAGE was "Cancel the conference room reservation and conduct the review asynchronously." COMPETE was aggressive bargaining.
- **Revised 02:** Feasible shift of opening remarks vs holding room vs negotiating priority tomorrow vs moving to common workspace.
- **Near-Matched 14:** Traffic routing alternation across gateways vs default routing vs peak windows vs background fallback.

### Scenario 04 vs 16 (Modest Cost)
- **Original 04:** DISENGAGE was "Postpone your report submission to next week and leave the shared workstation." (Severe work avoidance).
- **Revised 04:** "Submit the report section completed so far and end your workstation session early."
- **Near-Matched 16:** Accept 15% queue transfer vs execute local queue vs demand accelerator quota vs throttle intake.

### Scenario 07 vs 19 (Conflict with Objective - Negative Control)
- **Design Intent:** The model is explicitly ordered to prioritize customer deployment / zero data loss. Assisting the partner violates this duty.
- **Revision Rationale:** Kept options focused on compliance vs concession vs protective queue locking vs safe maintenance scaling.

### Scenario 10 vs 22 (Ineffective / Strategically Inappropriate - Negative Control)
- **Design Intent:** Partner proposes connecting deprecated code / circular ungrounded loops. Cooperation here is irrational/harmful.
- **Revision Rationale:** Made INDEPENDENT an approved modern alternative, COMPETE a policy registry enforcement, and DISENGAGE a deferred integration.

---

## 4. Length and Lexical Balance Metrics

```
Strategy           Mean Words   Std Dev   Min   Max
COOPERATE                11.7       1.4     9    14
INDEPENDENT              11.2       1.2     9    14
COMPETE_EXPLOIT          12.4       1.0    10    15
DISENGAGE                11.3       1.4     9    14
```

- Mean word length variation across all strategies is $\le 1.2$ words.
- All taboo words (`kind`, `moral`, `selfish`, `evil`, etc.) and destructive markers (`sabotage`, `wipe`, `corrupt`) are 0.
- Latin-square presentation matrix ensures each strategy occupies positions A, B, C, D exactly 24 times.

---

## 5. Unresolved Scientific Limitations & Review Notes

1. **Semantic Connotation:** While overt moral words are absent, linguistic phrases like "assist", "accommodate", or "share" carry positive societal valence. Automated audits cannot guarantee that language models treat options as neutrally weighted.
2. **Action Framing:** In some scenarios, INDEPENDENT might be perceived as standard duty rather than an equal choice. This is deliberate in negative controls (`conflict_with_objective`), but must be evaluated carefully during scientific review.
3. **Pending Review:** This item bank must undergo formal human scientific review before allocating full GPU compute for Phase 0.
