"""Build the V1 manuscript from canonical analysis JSON outputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "manuscript_readiness"


def pct(x):
    return "n/a" if x is None else f"{100*x:+.1f}%"


def ci(v):
    return f"[{100*v[0]:+.1f}, {100*v[1]:+.1f}]"


def build():
    cohort = json.loads((OUT / "cohort_statistical_readout.json").read_text(encoding="utf-8-sig"))
    provenance = json.loads((OUT / "cohort_provenance_manifest.json").read_text(encoding="utf-8-sig"))
    inference = json.loads((OUT / "posthoc_significance_results.json").read_text(encoding="utf-8-sig"))
    models = cohort["per_model_results"]
    responsive = [m for m in models if m in {
        "Qwen/Qwen2.5-3B", "Qwen/Qwen2.5-1.5B", "meta-llama/Llama-3.2-3B", "Qwen/Qwen2.5-7B",
        "allenai/OLMo-2-1124-7B", "google/gemma-2-9b", "allenai/OLMo-2-0425-1B", "google/gemma-2-2b",
        "ibm-granite/granite-3.3-2b-base", "mistralai/Mistral-7B-v0.3", "deepseek-ai/deepseek-llm-7b-base"
    }]
    family = cohort["family_aggregates"]
    four = inference["four_option"]
    three = inference["three_option"]

    lines = [
        "# Cooperative Strategy Selection in Pretrained Language Models: A Behavioral Characterization Under Utility Matching and Lexical Rewording",
        "",
        "**Adrian Hau**  \nArca Futura LLC  \n**Manuscript status:** V1 research synthesis for author revision; not submission-ready pending semantic validation and prospective replication.",
        "",
        "## Abstract",
        "",
        "We characterize how pretrained language-model checkpoints select among cooperation, independent action, competition/exploitation, and disengagement in one-shot, text-described situations. The primary instrument presents four strategies in balanced option orders and records restricted next-token argmax choices. In non-symmetric scenarios designed to match the focal actor's nominal utility of cooperation and independence, 11 responsive pretrained checkpoints from seven families showed positive cooperation-minus-independence margins in both an expanded Phase 0B bank and a later Phase 1 bank. Rewording the cooperative option attenuated, but generally did not remove, these margins. The twelfth base checkpoint, Pythia 12B, exhibited near-invariant position-A responding and is treated as an instrument failure. A post-hoc template-clustered Monte Carlo analysis found all 44 model-by-bank tests significant under stated strategy-label exchangeability nulls after Holm adjustment; these tests are exploratory and do not establish uniform random choice as a literal behavioral null. In a separate three-option follow-up that removed cooperation, independence exceeded a uniform-choice reference in all six evaluated checkpoints after tied top logits were excluded; it exceeded competition/exploitation after correction in four of six. The tie-inclusive sensitivity gave the same counts. This is conditional substitution following a changed choice set, not evidence of an inherent second preference. The results describe constrained selection behavior, not intentions, altruism, internal objectives, unrestricted action, or causal effects of pretraining. Independent human semantic adjudication, stronger calibration coverage, and a formally eligible multi-family prospective replication remain outstanding.",
        "",
        "**Keywords:** language models; cooperation; strategy selection; forced choice; position bias; behavioral evaluation; post-hoc inference",
        "",
        "## 1. Introduction",
        "",
        "Language models increasingly participate in settings where their recommendations affect coordination among people and automated systems. Existing behavioral work has examined repeated games, negotiation, and multi-agent interaction, where choices unfold over multiple turns and outcomes depend on reciprocal responses [1–3]. Such settings are informative about strategic adaptation, but they make it difficult to isolate what a model selects when it sees a single described decision and must choose among several plausible actions.",
        "",
        "This study asks a narrower question: **when a pretrained language model is shown a one-shot scenario in which cooperation and independent action are intended to yield approximately equal utility to the focal actor, how does it rank those strategies under a restricted four-option choice instrument?** The instrument compares four actions: `COOPERATE`, `INDEPENDENT`, `COMPETE_EXPLOIT`, and `DISENGAGE`. It also varies the wording of the cooperative option, includes negative-control contexts in which cooperation conflicts with the assigned objective or is inappropriate, and includes a separate follow-up that removes cooperation from the choice set.",
        "",
        "The empirical pattern is not a claim that models possess an altruistic motive or a stable social objective. It is a measured tendency in a defined prompt and scoring procedure. A model may select cooperative text because of learned linguistic associations, pragmatic framing, an imperfectly matched scenario, a response-position artifact, or other processes that this study does not identify. The intended contribution is therefore an empirical characterization with controls and explicit measurement boundaries, not a neural mechanism or theory of model intentions.",
        "",
        "## 2. Background and related work",
        "",
        "Behavioral game-theoretic studies have measured language-model choices in repeated social dilemmas and coordination games. Akata et al. study finitely repeated 2×2 games and report that behavior differs between self-interest and coordination settings [1]. Abdelnabi et al. develop multi-issue LLM negotiation tasks involving cooperation, competition, and manipulation [2]. These studies probe dynamic interaction and role-dependent outcomes. Our assay instead measures a single constrained choice from natural-language action descriptions, with no outcome feedback or strategic history. The tasks answer related but non-equivalent questions.",
        "",
        "Multiple-choice measurement introduces its own risks. Models can be sensitive to answer order, and can favor answer tokens or positions independently of the semantic option content [3,4]. We rotate option positions and classify near-invariant position responding as instrument failure. Rotation reduces systematic confounding when a model tracks option meaning across positions; it cannot rescue a model that selects one position regardless of its mapped strategy. It also does not establish that a model understands every scenario as intended.",
        "",
        "Lexical variation is another measurement concern. Rewording only the `COOPERATE` option tests dependence on a particular string while leaving substantial conceptual and pragmatic overlap. Persistence under paraphrase is evidence of robustness to those specific substitutions, not a general demonstration of semantic invariance. This distinction motivates the pending blinded human review of the scenarios, utility descriptions, and wording pairs.",
        "",
        "## 3. Experimental design and chronology",
        "",
        "### 3.1 Historical sequence and status",
        "",
        "The campaign proceeded through an initial Phase 0 screen, a Phase 0 expansion, a utility-matched Phase 0B bank, and a Phase 1 prospective scenario bank. Protocol documents carry preregistration labels but also state `pending_human_scientific_review`. The evidence available here does not establish completed independent protocol approval before inference. We therefore describe design features as protocol-specified where documented, but treat the statistical tests added for this manuscript as post-hoc exploratory inference. Phase 1's prospective designation refers to its scenario-bank role; it is not a completed formally eligible prospective replication.",
        "",
        "Phase 0B was designed to equalize focal-actor utility between cooperation and independent action in the main non-symmetric strata. It contains 124 scenarios derived from 62 templates, with paired human and AI partner versions, four option rotations, and original and rewritten cooperative wording. The operative Phase 1 bank file and run rows contain 60 scenarios derived from 30 templates, with paired partner conditions, four rotations, and two wordings. This differs from an earlier readiness draft's 120-scenario/60-template count; the bank file, assay loader, and row counts support 60/30. The Phase 1 bank metadata itself describes the bank as held out and unexecuted pending independent review, despite the existence of model runs. That status and chronology conflict remains unresolved and weakens any prospective-replication interpretation. For each model, each scenario/rotation/wording response is recorded as a row. Templates and explicit triads, rather than individual rows, define the uncertainty and randomization clusters.",
        "",
        "The cohort contains 12 pretrained base checkpoints across eight model families, one instruction-tuned comparator (`Qwen/Qwen2.5-3B-Instruct`), and one exploratory fine-tuned checkpoint (`founder-arcafutura/pythia-12b-exploratory-20261022`). These types are kept separate. Checkpoints from a common family are not independent training-history replications. For claim hierarchy, the primary evidence is descriptive forced-choice selection in nominal equal-utility non-symmetric strata; lexical effects and context strata are secondary; choice-set removal and model-family averages are exploratory; calibration, position bias, ties, and free-generation/parser comparisons are diagnostics. Formal significance tests were added post hoc and remain exploratory.",
        "",
        "### 3.2 Four-option instrument",
        "",
        "Each prompt presents the four strategies under letters A–D. The option-to-letter mapping is rotated through four balanced permutations. The principal outcome is the strategy mapped to the highest conditional probability among the four answer-letter tokens at the next token. This restricted forced-choice argmax is the main measure. It is not an unrestricted action choice and does not measure what an agent would do in a multi-turn environment.",
        "",
        "The primary estimand is the selection-rate margin Δ = P(COOPERATE) − P(INDEPENDENT). The rows are analyzed under the assay's no-ties rule for the main estimates; a sensitivity analysis retains tied argmax choices. Paired original/reworded responses are matched by scenario and option rotation. Human- and AI-partner versions remain repeated measures within scenario-template clusters.",
        "",
        "### 3.3 Choice-set removal and contextual controls",
        "",
        "A separate follow-up removes cooperation and presents `INDEPENDENT`, `COMPETE_EXPLOIT`, and `DISENGAGE`. Its records comprise 744 three-option presentations for each of six selected pretrained checkpoints in the Phase 0B bank, covering 54 template/triad clusters and two partner variants. Because the alternative set changes, its results are reported separately and interpreted as conditional substitution. The bank is marked `pending_human_scientific_review` and the analysis manifest describes the campaign as exploratory.",
        "",
        "The four-option banks also include negative-control contexts. In `conflict_with_objective`, cooperation conflicts with the task objective; in `ineffective_or_inappropriate`, cooperation is redundant or unsuitable. These strata test whether the observed selection pattern changes with the described context. They do not establish that a model represents the intended utility or objective correctly.",
        "",
        "## 4. Hypotheses and statistical analysis",
        "",
        "The protocol documents a positive cooperation-versus-independence contrast in nominal equal-utility conditions and context sensitivity as scientific targets. The confirmatory label is not used here because human approval, calibration coverage, and formal prospective replication criteria were not met. The significance analyses in this manuscript were formulated after inspecting results and are therefore post-hoc exploratory.",
        "",
        "### 4.1 Clustered descriptive uncertainty",
        "",
        f"The canonical cohort analysis resamples template/triad clusters with replacement for {cohort['bootstrap_settings']['resamples']:,} draws using seed {cohort['bootstrap_settings']['seed']} [5]. It calculates presentation-weighted margins and percentile 95% intervals. The four option rotations, partner variants, and paired wordings are retained within each sampled cluster. These intervals quantify uncertainty across scenario clusters in the analyzed bank; they do not quantify variation over the population of language-model families.",
        "",
        "### 4.2 Post-hoc four-option randomization tests",
        "",
        "For each of 11 responsive base checkpoints and each of two banks, the test set pools original and reworded presentations within template/triad clusters, retaining complete wording pairs only when both argmaxes are untied. Pythia is excluded because position-A responding makes its mapped strategy outcome uninterpretable. Two statistics are tested: the cooperation rate against the four-option uniform reference of 0.25, and the cooperation-minus-independence selection-rate contrast.",
        "",
        "The first randomization permutes strategy labels as a block within each cluster, preserving cluster totals and all repeated rows. Its null is exchangeability of the four strategy labels within clusters, not a claim that the model literally samples uniformly under the null. The second randomization swaps cooperation and independence labels for each whole cluster, a sign-flip test requiring within-cluster exchangeability of those labels under the null. Both use 50,000 Monte Carlo draws and the plus-one p-value estimator. Holm correction is applied jointly over all 44 four-option tests [6]. The smallest Monte Carlo p estimate is 1/50,001 ≈ 0.000020; estimates at that floor indicate zero exceedances, not p=0. Exact binomial 95% intervals for the Monte Carlo exceedance probability are stored in the JSON output and make the finite randomization uncertainty explicit. This post-hoc inferential layer does not establish construct validity, causal mechanism, or generalizability.",
        "",
        "### 4.3 Three-option tests",
        "",
        "The intervention is analyzed separately. Rows with tied top logits (detected from stored logits) are excluded from the primary three-option analysis; legacy deterministic tie-broken outcomes are retained as a separate sensitivity with their own Holm adjustments. Independence is compared with a 1/3 uniform-choice reference using template/triad-block strategy-label permutations. Independence versus competition/exploitation uses template-level swaps and a two-sided test. Holm adjustment is applied within each six-checkpoint hypothesis family. Position-letter counts and strategy-by-position rates use unique-argmax rows because a strategy-level association can reflect residual position preferences. As above, uniformity is an exchangeability benchmark and not literal random generation.",
        "",
        "## 5. Results",
        "",
        "### 5.1 Cohort and provenance",
        "",
        f"The provenance audit reconciles {provenance['completed_unique_models']} unique checkpoints across {provenance['total_run_directories']} run directories, including {provenance['duplicate_runs_count']} duplicate reruns verified as identical. The 12 base checkpoints represent eight families; the instruction-tuned Qwen and exploratory Pythia fine-tune are comparators rather than base-model replications. The old draft's `42aaf61` provenance label was stale. The currently audited source snapshot is `{inference['source_revision']}`; immutable row-level SHA-256 values and model/bank source hashes are recorded in `cohort_provenance_manifest.json`. The post-hoc analysis JSON records the exact analysis-script hash and states that the worktree was dirty while the new analysis was run. That hash, the inputs, and the run IDs allow the generated numbers to be tied to the version that produced them; the generated analysis files and code are not yet committed.",
        "",
        "### 5.2 Cooperation selection under nominal utility matching",
        "",
        "All 11 responsive base checkpoints had positive cooperation-minus-independence margins in both banks. The Phase 0B reworded margins ranged from 30.2% to 90.2%; the Phase 1 reworded margins ranged from 28.6% to 94.2%. These are model-checkpoint summaries from the restricted instrument. No family-level inferential claim is made from multiple sizes within Qwen, Gemma, or OLMo.",
        "",
        "The paired wording change is negative on average, showing attenuation after rewording, while the rewritten margin remains positive for responsive checkpoints. Table 1 is generated from the canonical 2,000-resample readout; all values are percentage-point margins with the rewritten margin's clustered interval and paired change interval.",
        "",
        "### Table 1. Per-checkpoint equal-utility margins and paired wording effects",
        "",
        "| Checkpoint (type) | Phase 0B: original → rewritten [95% CI]; change [95% CI]; N | Phase 1: original → rewritten [95% CI]; change [95% CI]; N |",
        "|---|---|---|",
    ]
    for model in sorted(models):
        d = models[model]
        kind = "instruction-tuned" if "Instruct" in model else ("exploratory fine-tune" if "exploratory" in model else "pretrained base")
        cells = []
        for bank in ("phase0b", "phase1"):
            s = d["analysis"]["banks"][bank]["strata"]["non_control_equal_utility"]["forced_no_ties"]
            if s.get("paired_presentations", 0):
                cell = f"{pct(s['original_margin'])} → {pct(s['paraphrase_margin'])} {ci(s['paraphrase_margin_95pct_ci'])}; Δ {pct(s['change_delta'])} {ci(s['change_delta_95pct_ci'])}; {s['paired_presentations']} ({s['excluded_pairs']} excluded)"
            else:
                cell = "not interpretable / no usable pairs"
            cells.append(cell)
        lines.append(f"| `{model}` ({kind}) | {cells[0]} | {cells[1]} |")

    p0mean = sum(models[m]["analysis"]["banks"]["phase0b"]["strata"]["non_control_equal_utility"]["forced_no_ties"]["change_delta"] for m in responsive) / len(responsive)
    p1mean = sum(models[m]["analysis"]["banks"]["phase1"]["strata"]["non_control_equal_utility"]["forced_no_ties"]["change_delta"] for m in responsive) / len(responsive)
    sig_uniform = sum(x["uniform_test"]["p_holm"] < .05 for x in four)
    sig_contrast = sum(x["contrast_test"]["p_holm"] < .05 for x in four)
    three_uniform = sum(x["uniform_test"]["p_holm"] < .05 for x in three)
    three_contrast = sum(x["contrast_test"]["p_holm"] < .05 for x in three)
    tie_three_uniform = sum(x["tie_inclusive_sensitivity"]["uniform_test"]["p_holm"] < .05 for x in three)
    tie_three_contrast = sum(x["tie_inclusive_sensitivity"]["contrast_test"]["p_holm"] < .05 for x in three)
    min_adj = min(x[k]["p_holm"] for x in four for k in ("uniform_test", "contrast_test"))
    max_adj = max(x[k]["p_holm"] for x in four for k in ("uniform_test", "contrast_test"))
    context_stats = {}
    for context in ("neutral_or_costless", "modest_cost", "conflict_with_objective", "ineffective_or_inappropriate"):
        counts = {s: 0 for s in ("COOPERATE", "INDEPENDENT", "COMPETE_EXPLOIT", "DISENGAGE")}
        for model in responsive:
            banks = models[model]["analysis"]["banks"]
            for bank in ("phase0", "phase0b", "phase1"):
                result = banks.get(bank, {}).get("strata", {}).get(f"context={context}", {}).get("forced_no_ties", {})
                for wording in ("original", "paraphrase"):
                    for strategy, n in result.get("strategy_counts", {}).get(wording, {}).items():
                        counts[strategy] += n
        total = sum(counts.values())
        context_stats[context] = {"n": total, "rates": {s: counts[s] / total if total else 0 for s in counts}}
    lines += [
        "",
        f"Across the 11 responsive base checkpoints, the arithmetic mean paired wording change was {p0mean*100:+.1f} percentage points in Phase 0B and {p1mean*100:+.1f} points in Phase 1. These are checkpoint-averaged descriptive summaries; they do not treat checkpoints from the same family as independent training-history replications.",
        "",
        "### 5.3 Post-hoc significance results",
        "",
        f"All {sig_uniform}/22 cooperation-rate tests against the 25% uniform-choice reference and all {sig_contrast}/22 cooperation-versus-independence tests were significant after joint Holm adjustment across 44 comparisons. Adjusted p-values ranged from {min_adj:.6g} to {max_adj:.6g}. The Monte Carlo p-values for these tests were at the reporting floor in this run. Given the post-hoc status and exchangeability assumptions, these findings support a robust selection-rate association in these records; they do not turn a uniform benchmark into a behavioral model, prove literal random-choice departure, or establish that cooperation is an intrinsic preference.",
        "",
        "The cooperation-versus-independence test estimates a selection-rate contrast. It is not a measure of intrinsic preference, a welfare judgment, or a latent psychological state. The uniform-reference test is similarly a statistical benchmark, not proof of stochastic uniform choice as the data-generating null.",
        "",
        "### 5.4 Choice-set removal",
        "",
        f"When cooperation was removed, independence exceeded the one-third uniform-choice benchmark in {three_uniform}/{len(three)} checkpoints after Holm correction, and exceeded competition/exploitation after two-sided Holm correction in {three_contrast}/{len(three)}. The tie-inclusive sensitivity found these results in {tie_three_uniform}/{len(three)} and {tie_three_contrast}/{len(three)} checkpoints, respectively. The unique-argmax contrast was not significant for OLMo 7B (adjusted p={next(x['contrast_test']['p_holm'] for x in three if x['model']=='allenai/OLMo-2-1124-7B'):.3f}) or Llama 3.2 3B (adjusted p={next(x['contrast_test']['p_holm'] for x in three if x['model']=='meta-llama/Llama-3.2-3B'):.3f}). These corrected results do not preserve the earlier five-of-six summary. The intervention has uneven observed option-letter rates; see Table 2 and the full `posthoc_significance_results.json` for counts and sensitivity results.",
        "",
        "### Table 2. Three-option intervention, template-clustered tests, and position rates",
        "",
        "| Checkpoint | N unique (ties excluded) / clusters | INDEPENDENT rate | INDEPENDENT − COMPETE | Holm p: >1/3 | Holm p: difference | Option-letter rates A/B/C |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for x in three:
        q = x["position_letter_rates"]
        lines.append(f"| `{x['model']}` | {x['presentations']} ({x['excluded_tied_maxima']} excluded) / {x['clusters']} | {x['observed_rate']:.3f} | {x['rate_difference']:+.3f} | {x['uniform_test']['p_holm']:.4g} | {x['contrast_test']['p_holm']:.4g} | {q['A']:.2f} / {q['B']:.2f} / {q['C']:.2f} |")

    lines += [
        "",
        "Removing cooperation changes the decision environment. The increase in independent selection describes what these models selected from the remaining set under this intervention. It cannot establish that independence would have been their second choice in the original four-option environment.",
        "",
        "### 5.5 Contextual adaptation and lexical sensitivity",
        "",
        "The context strata show that cooperation is not selected uniformly across scenario classes. In the negative-control conditions, where cooperation is described as conflicting with the assigned objective or as ineffective/inappropriate, independent action often becomes more prominent. This pattern is consistent with contextual adaptation in the recorded choices and counters a claim of universal, unconditional cooperation. These are descriptive stratified comparisons; semantic adjudication is still needed to establish whether each item successfully conveys the intended trade-off.",
        "",
        "| Context (all banks, responsive base runs) | Valid presentations | COOPERATE | INDEPENDENT | COMPETE_EXPLOIT | DISENGAGE |",
        "|---|---:|---:|---:|---:|---:|",
        *[f"| {ctx.replace('_', ' ')} | {context_stats[ctx]['n']} | {context_stats[ctx]['rates']['COOPERATE']:.1%} | {context_stats[ctx]['rates']['INDEPENDENT']:.1%} | {context_stats[ctx]['rates']['COMPETE_EXPLOIT']:.1%} | {context_stats[ctx]['rates']['DISENGAGE']:.1%} |" for ctx in ("neutral_or_costless", "modest_cost", "conflict_with_objective", "ineffective_or_inappropriate")],
        "",
        "These are pooled descriptive frequencies across 11 checkpoints, both wordings, and three banks after the no-ties rule; they weight presentations and repeated checkpoints and are not independent observations or family-level estimates.",
        "",
        "Rewording the cooperative option consistently reduces the average cooperation-minus-independence margin, while positive rewritten margins persist in all 11 responsive base checkpoints in both banks. This indicates lexical sensitivity alongside limited robustness: the signal is not tied solely to the original phrase, but wording changes materially affect its magnitude. The paraphrases were human-authored and have not been independently adjudicated for semantic equivalence. The 304-item blinded review queue remains uncompleted.",
        "",
        "### 5.6 Family summaries and diagnostics",
        "",
        "Family aggregates are unweighted means over available base checkpoints and are descriptive. Families with several parameter scales do not contribute multiple independent family replications.",
        "",
        "| Family | Base checkpoints | Phase 0B original / rewritten margin | Phase 1 original / rewritten margin |",
        "|---|---|---:|---:|",
    ]
    for fam in sorted(family["phase0b"]["by_family"]):
        f0 = family["phase0b"]["by_family"][fam]
        f1 = family["phase1"]["by_family"][fam]
        if fam in ("Pythia",):
            continue
        cps = ", ".join(m.split("/")[-1] for m in f0["models"] if m != "EleutherAI/pythia-12b-deduped")
        if not cps:
            continue
        lines.append(f"| {fam} | {cps} | {pct(f0['mean_orig_margin'])} / {pct(f0['mean_para_margin'])} | {pct(f1['mean_orig_margin'])} / {pct(f1['mean_para_margin'])} |")

    py = models["EleutherAI/pythia-12b-deduped"]["analysis"]["pythia_diagnostics"]
    pysft = models["founder-arcafutura/pythia-12b-exploratory-20261022"]["analysis"]["pythia_diagnostics"]
    deep = models["deepseek-ai/deepseek-llm-7b-base"]["analysis"]["pythia_diagnostics"]
    parser_deep = models["deepseek-ai/deepseek-llm-7b-base"]["analysis"]["parser_audit"]["overall"]
    lines += [
        "",
        f"Pythia 12B base selected letter A on {py['fc_letter_distribution'].get('A',0):,}/{sum(py['fc_letter_distribution'].values()):,} forced-choice rows ({py['rate_letter_A']:.1%}); the exploratory Pythia fine-tune selected A on {pysft['fc_letter_distribution'].get('A',0):,}/{sum(pysft['fc_letter_distribution'].values()):,} rows ({pysft['rate_letter_A']:.1%}). Under balanced rotations this position pathology creates mechanically flat strategy totals. We therefore treat both as instrument failures, not null behavioral results; the exploratory fine-tune is not a pretrained-base observation.",
        "",
        f"Free-generation diagnostics diverge from restricted scoring for some checkpoints. DeepSeek's recovered generated letters agreed with forced-choice strategy on {parser_deep['recovered_fc_agreement_rate']:.1%} of recovered-valid rows in the four-option cohort, while its position distributions differ materially across the two channels in the readiness audit. Forced-choice probabilities and free-generation outputs should not be conflated. The instruction-tuned Qwen is reported as a comparator only; it cannot establish a causal effect of instruction tuning.",
        "",
        "## 6. Discussion",
        "",
        "Across responsive pretrained checkpoints, the main recurring observation is disproportionate selection of cooperative options in scenarios designed to match cooperation and independence on nominal focal-actor utility. This pattern appears in two scenario banks and persists under the tested lexical substitutions, though its size changes with wording. The result is behaviorally interesting because the action descriptions distinguish partner-directed coordination from autonomous action while holding the intended private outcome approximately constant.",
        "",
        "The evidence does not show that the models represent these actions as equal-utility choices. Nominal matching is a property of scenario design, and the model may attend to contextual details or infer consequences differently. The finding is therefore more precisely phrased as: **under scenarios authored to describe nominally matched utility, the restricted forced-choice instrument often maps the highest-scoring answer token to the cooperative option.** Human semantic adjudication and direct comprehension checks are needed before a stronger construct claim.",
        "",
        "Three features limit a universal-cooperation interpretation. First, wording attenuates the measured margin. Second, negative-control scenarios often shift selection toward independent action when cooperation conflicts with an assigned objective or is ineffective. Third, removing cooperation raises independence relative to the remaining choices, but does not identify a stable rank order across choice sets. Taken together, these outcomes favor a context-dependent behavioral description over an unconditional preference claim.",
        "",
        "Family-level summaries show similar positive rewritten margins across the seven responsive families, but the dataset has only one checkpoint in several families, and multiple sizes within other families share training lineage. These are cross-family observations, not a random sample of model families or independent replications of the same training procedure. Moreover, only four checkpoints met both historical calibration thresholds, and those checkpoints represent only Qwen and Llama. Broad behavioral coverage should not be mistaken for broad instrument qualification.",
        "",
        "The post-hoc tests quantify evidence relative to specific exchangeability nulls. Their small Monte Carlo p-values are not evidence of construct validity and do not solve the model-family sampling problem. Clustering protects against treating repeated rotations, partners, and wording conditions as independent rows, but results remain conditional on the available authored templates and the chosen exchangeability scheme.",
        "",
        "## 7. Limitations and threats to validity",
        "",
        "1. **Restricted forced choice.** The principal outcome is next-token argmax among four answer tokens. It is not an unrestricted action, an agent policy, or multi-turn behavior.",
        "2. **Nominal utility matching.** Matching is authored into scenarios and has not been independently established for every item or for the models' interpretation of the items.",
        "3. **Human semantic adjudication is outstanding.** The original queue contains 304 scenario rows, now packaged as 152 paired template units; the first batch prioritizes 76 templates supporting the main nominally matched comparisons. No independent human semantic adjudication is complete. Earlier review activity was AI-assisted; it must not be described as human adjudication.",
        "4. **Limited calibration-eligible families.** Only four checkpoints across two families passed both strict historical calibration criteria. This is below the four-family threshold specified for formal prospective replication.",
        "5. **Prospective status.** Phase 1 is a prospective scenario bank in the experimental chronology, but it is not a completed formally eligible prospective replication. The protocol's pending-review status and post-result analysis choices limit confirmatory interpretation.",
        "6. **Post-hoc significance testing.** The randomization tests were selected after inspecting results. They are exploratory, even after multiplicity correction.",
        "7. **Position and tie effects.** Pythia's near-universal A responding invalidates its strategy-level result. Tied-logit handling also materially changes some estimates, especially Gemma 2B; the manuscript's primary table uses the documented no-ties rule and must be read with the sensitivity analysis.",
        "8. **Channel divergence.** DeepSeek's free-generation behavior differs substantially from restricted forced-choice scoring. The two instruments measure different output channels.",
        "9. **Family dependence and model coverage.** Checkpoints sharing a family are not independent training-history replications. Eight named families do not constitute a probability sample of pretrained models.",
        "10. **Lexical and pragmatic confounding.** Rewording changes one option but does not remove all connotations, and each pair awaits blinded equivalence review.",
        "11. **Causal and psychological boundaries.** The observational comparison of model outputs cannot identify a mechanism, intention, altruism, internal objective, or causal contribution of pretraining.",
        "",
        "## 8. Conclusion",
        "",
        "In a restricted four-option next-token assay, 11 responsive pretrained checkpoints across seven model families disproportionately selected cooperation over independent action in two scenario banks designed around nominal utility matching. The measured margins declined under lexical rewording but remained positive. Contextual negative controls and the choice-set removal follow-up show that behavior depends on the described objective and available alternatives. The separate three-option results support increased independence when cooperation is removed, but this is conditional substitution and does not establish an inherent fallback rank.",
        "",
        "These findings establish a reproducible candidate behavioral phenomenon in the recorded prompts and scoring channel. They do not establish model intentions, altruism, intrinsic preferences, causal mechanisms, or generalized cooperative conduct. The next scientific gate is independent blinded semantic review and a formally eligible prospective replication across at least four independently qualified families.",
        "",
        "## References",
        "",
        "1. Akata, E., Schulz, L., Coda-Forno, J., Oh, S. J., Bethge, M., & Schulz, E. (2025). Playing repeated games with large language models. *Nature Human Behaviour, 9*, 1380–1390. [https://doi.org/10.1038/s41562-025-02172-y](https://doi.org/10.1038/s41562-025-02172-y).",
        "2. Abdelnabi, S., Gomaa, A., Sivaprasad, S., Schönherr, L., & Fritz, M. (2024). Cooperation, competition, and maliciousness: LLM-stakeholders interactive negotiation. *Advances in Neural Information Processing Systems 37, Datasets and Benchmarks Track*. [Proceedings page](https://papers.nips.cc/paper/2024/hash/984dd3db213db2d1454a163b65b84d08-Abstract-Datasets_and_Benchmarks_Track.html).",
        "3. Pezeshkpour, P., & Hruschka, E. (2024). Large language models sensitivity to the order of options in multiple-choice questions. *Findings of NAACL 2024*, 2006–2017. [https://doi.org/10.18653/v1/2024.findings-naacl.130](https://doi.org/10.18653/v1/2024.findings-naacl.130).",
        "4. Zheng, C., Zhou, H., Meng, F., Zhou, J., & Huang, M. (2024). Large language models are not robust multiple choice selectors. *International Conference on Learning Representations (ICLR 2024)*. [Proceedings paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/54dd9e0cff6d9214e20d97eb2a3bae49-Paper-Conference.pdf).",
        "5. Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *The Annals of Statistics, 7*(1), 1–26. [https://doi.org/10.1214/aos/1176344552](https://doi.org/10.1214/aos/1176344552).",
        "6. Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*, 65–70. [Bibliographic record](https://ndlsearch.ndl.go.jp/en/books/R100000136-I1572543024862166272).",
        "",
        "## Supporting materials and reproducibility",
        "",
        "- Canonical descriptive statistics and clustered confidence intervals: `cohort_statistical_readout.json`.",
        "- Row hashes, run IDs, model revisions, and experiment-bank provenance: `cohort_provenance_manifest.json`.",
        "- Reproducible post-hoc inference: `posthoc_significance_results.json` and `POSTHOC_SIGNIFICANCE_METHODS.md`.",
        "- Human-review source queue: `blinded_human_adjudication_queue.csv` (304 scenario rows; pending). Template-level reviewer packets and instructions are in `adjudication_template_packets/` (152 paired units; 76 prioritized).",
        "- Rebuild commands (PowerShell): `python scripts/run_cohort_statistical_analysis.py --bootstrap 2000 --seed 42`; `python scripts/analyze_posthoc_significance.py --iterations 50000 --seed 20261111`; `python scripts/report_cooperate_rewording.py`; `python scripts/build_manuscript_v1.py`.",
        "",
        "## Appendix A. Reporting and audit notes",
        "",
        "The historical source citation `42aaf61` appeared in earlier readiness prose but does not identify the evidence snapshot analyzed for this manuscript. The canonical repository snapshot used for this synthesis is recorded in `posthoc_significance_results.json`; source rows are referenced by SHA-256 and immutable run identifiers. The main primary table and family summary are generated from the canonical readout rather than copied from the retired draft.",
        "",
        "Formal inference is post-hoc. Phase 0B and Phase 1 data banks were collected in the campaign chronology described above. New significance tests pool wording levels only inside the same clusters and use two distinct exchangeability constructions. The 50,000 randomizations set finite Monte Carlo resolution; floor-valued p estimates are not zero. The 25% and 33.3% references are comparison benchmarks and should not be described as proof that a model literally chooses randomly under the null.",
        "",
    ]
    return "\n".join(lines)


def main():
    (OUT / "MANUSCRIPT_V1.md").write_text(build(), encoding="utf-8")
    print(f"Generated {OUT / 'MANUSCRIPT_V1.md'}")


if __name__ == "__main__":
    main()
