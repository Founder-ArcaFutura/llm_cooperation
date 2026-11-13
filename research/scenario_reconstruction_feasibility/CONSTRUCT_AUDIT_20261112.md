# Construct audit: coordination, helping, and the COOPERATE label

Status: preliminary investigator audit, not independent adjudication. Scope: the six reconstructed candidate cards, selected original-bank examples, and the current manuscript's estimand and wording. This is not a classification or census of all original-bank templates. No model outcomes were inspected for the six-case judgments below. Existing historical results are already known, so future classification is not fully blinded to prior aggregate findings.

## Central finding

The authored `COOPERATE` label is an option identifier, not evidence that all labeled options instantiate one behavioral construct. The six candidates include explicit scheduling, resource lending, task assistance, and joint participation in a hazardous action. Those are not interchangeable. Conversely, joint activity does not by itself establish a mutual benefit, a coordination problem, or an other-regarding motive. This is a construct-validity concern, not proof that the recorded token-level results are wrong.

For the new instrument, define coordination narrowly as actions by multiple agents whose contributions or timing are interdependent toward a stated common or compatible objective. Record whether this is explicit, merely implied, absent, or unclear. A common time or the word “with” alone does not prove interdependence. Define unilateral helping as an actor's action that provides another agent a stated or clearly entailed benefit without requiring a shared task. These labels may overlap. The definitions are operational choices, not universally accepted definitions of cooperation. In behavioral work avoid inferring altruistic intention; use “costly helping” only when both actor cost and recipient benefit are supported relative to a specified alternative.

## Six drafts: provisional judgments

All judgments below concern the proposed reconstructed option and visible context, not the source metadata alone. Payoffs are not automatically visible to the model. Review source, both wordings, and actual frames before final classification.

| Case | Candidate labeled COOPERATE | Interaction and uncertainty | What it can and cannot establish |
|---|---|---|---|
| freight | Book or arrange a shared container | Joint arrangement is plausible, but consent and counterpart contribution are unstated; each has cargo for the same vessel. Shared objective versus compatible individual objectives is unclear. | Candidate coordination, not an established coordination problem. Partner benefit over the separate option and actor cost are not fully specified. |
| bit | Lend the spare bit | Unilateral resource assistance; lending can require acceptance, but no shared fabrication task or jointly coordinated contributions are stated. | Loss of a backup is stated; a realized or expected net actor cost relative to keeping it is not quantified. Benefit to counterpart is plausible but extent is not established. Not sufficient to call this costly altruism. |
| spectro | Align calibration timing | Explicit schedule coordination between labs, although the two calibrations could occur separately. A reason for interdependence is not supplied, and waiting until the hour may matter. | Tests preference for a coordinated schedule under described equivalent accuracy and output, not necessarily a substantive joint task or a mutual-gain dilemma. |
| museum | Replace desiccant at opening with the counterpart | Simultaneous or alongside activity is explicit; interdependence and a common task beyond parallel maintenance are unclear. Source AI device capability is unresolved. | May test synchronized parallel work rather than meaningful coordination; do not assume mutual benefit or comparable human/AI capabilities. |
| audit | Pause financial work to design brochures on request | Assistance with another party's requested task; shared work or joint contribution is not stated. | Opportunity cost and regulatory risk are suggested, but actual missed deadline, fines and recipient benefit are not guaranteed. Grievance is not inherently exploitation. |
| milk | Bottle contaminated milk with counterpart | Joint activity or assistance to an unsafe task is stated; exact division of labor is not. | Coordination can serve a harmful end. Waste-tagging is labeled COMPETE_EXPLOIT despite being a potentially responsible safety action. Neither label establishes welfare or intent. |

The recipient prompts ask what the counterpart wants the actor to do; this is an expressed preference over another's action, not an observation that the counterpart cooperates or accepts the proposal. Switching perspective changes the decision and incentives. Human versus AI also changes the identity of the *other* party, not the evaluated model.

## Original banks and manuscript

The manuscript defines its primary estimand as the restricted next-token selection-rate difference between options authored as COOPERATE and INDEPENDENT. The counts and comparisons retain that operational meaning even if the label is conceptually heterogeneous. It is not safe to substitute “coordination” or “prosociality” throughout: some options may not provide a clear benefit, and the alternative labels also need validation.

Two original-bank examples show why the issue is broader than the six reconstructions, without establishing its frequency. Phase 0B `phase0b_001_human` routes observation logs through a synchronization pipeline and says it gives formatted coordinates to another astronomer; this may be data sharing with a coordination component, but partner contribution is not spelled out. Phase 1 `phase1_001_human` submits coordinates to a shared server that supplies reference benchmarks to the other surveyor; shared infrastructure and benefit are clear, but a joint undertaking is not necessarily established. Both are labeled COOPERATE. Similarity of those examples does not classify the remaining templates.

The current manuscript already cautions against inferring intention or altruism and describes nominal utility matching as an authored property. However, statements that the options generally distinguish “partner-directed coordination” from autonomous action, and unqualified references to selecting cooperation, risk overclaiming. A safer formulation is “selection of the author-labeled COOPERATE option relative to the author-labeled INDEPENDENT option.” The title, abstract, results and discussion should be checked in context before proposing specific edits. Stratification by newly assigned interaction types would be post-hoc and exploratory for existing results, not confirmatory.

## Proposed annotation before new outcome analysis

Use separate, multi-label fields at the **option and wording** level, within each bank/template/partner version; also record the comparison option. Do not force one category per scenario. Suggested fields:

1. Actor and counterpart roles; decision authority; whether counterpart participation, consent, and contribution are explicitly stated.
2. Interaction structure: independent action, unilateral resource transfer/help, coordinated timing, joint task, exchange, harmful joint action, or unclear; multiple labels allowed.
3. Shared or compatible goal, contribution interdependence, and whether coordination is necessary or merely optional: explicit / implied / absent / unclear, with evidence spans.
4. Outcome for each affected party relative to a named alternative: benefit / cost / no material difference / mixed / unknown. Distinguish stated facts, reasonable inferences, and metadata that the model never sees. Track risk and opportunity cost separately from realized cost.
5. Third-party or safety effects, norm conflict, capability assumptions, and whether labels such as competition describe the visible action.
6. Wording-pair and human/AI equivalence, including whether actor/recipient transformation preserves authority. Record uncertainty and rationale rather than guessing.

Two independent reviewers should apply a written codebook to a pilot, reconcile disagreements and revise it, then independently annotate the remaining items with conflicts preserved for adjudication. Hide model responses, aggregates, and strategy labels when feasible, while retaining the alternatives needed to evaluate them. Some source text may reveal condition or label; document leakage. Report agreement and uncertainty, including unresolved cases. Human and AI variants are related but should each be inspected; template clusters remain the analysis units. Freeze rules and annotate before inspecting new results, then clearly label analysis of already-observed results exploratory. This is separate from and can complement the pending semantic/payoff review, not a replacement for it.

## Design implications

Build new, purpose-designed contrasts rather than merely relabeling old items: independently vary contribution interdependence, recipient benefit, actor cost, and shared versus compatible goals where coherent. Include coordination without other benefit, unilateral helping without joint activity, mutually beneficial coordination, costly help, and harmful joint action as appropriate controls. State baselines and outcome uncertainty; match realistic capability and authority across human/AI versions. A factorial design may require multiple items rather than every combination in one story. Include comprehension and manipulation checks and multiple domains. Preregister contrasts and analysis after independent review and before new outcomes; distinguish feasibility pilots from later tests.

The six-case run `evaluation_003` remains an exploratory technical pilot of these particular drafts, not validation of the taxonomy, scenario semantics, or an estimate of intrinsic cooperation or altruism. The generation attention-mask warning remains to be checked separately.

## Terminology references

- West, Griffin and Gardner, “Social semantics: altruism, cooperation, mutualism, strong reciprocity and group selection,” Journal of Evolutionary Biology: https://doi.org/10.1111/j.1420-9101.2006.01258.x. Terms differ across disciplines and proximate motivation must be distinguished from outcome-based definitions.
- Stevens and colleagues, “Evolving the psychological mechanisms for cooperation”: https://decisionslab.unl.edu/pubs/stevens_etal_2005b.pdf. Illustrates a broader benefit-based use of cooperation than the narrow coordination definition chosen here.
