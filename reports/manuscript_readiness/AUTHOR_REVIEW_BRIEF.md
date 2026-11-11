# Author review brief

**Status:** Prepared for Adrian Hau's scientific and editorial review. The manuscript is not ready for external review or submission.

## Plain-English findings

In the four-option forced-choice task, 11 responsive pretrained checkpoints selected cooperation more often than independent action in the scenarios written to match their nominal private utility. This pattern appeared in the Phase 0B and Phase 1-designated banks. Rewording the cooperative option reduced the margin, but the rewritten margin stayed positive in those 11 checkpoints. Pythia 12B mostly selected letter A regardless of which strategy occupied that position, so its flat strategy percentages are an instrument failure.

In a separate follow-up, the cooperative action was removed. Excluding tied top logits, independence exceeded the three-option uniform-choice reference in all six selected checkpoints. Independence exceeded competition/exploitation after correction in four of six; it did not do so for OLMo 7B or Llama 3.2 3B. The tie-inclusive sensitivity gives the same 6/6 and 4/6 pattern. This describes substitution under a changed choice set and does not establish an inherent second preference.

The post-hoc four-option randomization tests were significant under cluster-level strategy-label exchangeability assumptions after Holm correction. They were formulated after inspecting results. They test statistical contrasts in this instrument, not a mechanism, construct validity, or generalization to other models. The three-option bank remains marked pending human scientific review.

## Main scientific contributions

1. A cross-family descriptive characterization of cooperative selection over independent action in a one-shot, restricted next-token choice instrument under nominal utility matching.
2. Evidence that positive margins persist under the specific cooperative-option rewordings tested, alongside measurable attenuation from wording changes.
3. A separate choice-set intervention showing increased independence after cooperation is removed, interpreted as conditional substitution.
4. Negative-control context and diagnostic evidence showing that recorded selection changes with task context and that position bias, tied logits, and generation-channel divergence can make naïve behavioral summaries misleading.
5. A reproducible, cluster-aware post-hoc inference layer with explicit exchangeability assumptions, fixed seeds, multiplicity correction, and immutable input hashes.

## Claims with uncertain evidentiary support

- Whether each nominally utility-matched scenario is understood as matched by the models. No independent semantic adjudication has been completed.
- Whether a result described as “cooperative selection” reflects the intended cooperation construct rather than linguistic desirability, pragmatic inference, or other scenario features.
- Whether the Phase 1-designated results qualify as prospective evidence. The bank metadata says held out/unexecuted pending approval, yet run rows exist. The actual bank has 60 scenarios/30 templates, not the stale draft's 120/60.
- Whether the exchangeability nulls used in post-hoc randomization are scientifically plausible across deliberately heterogeneous templates. Significant p-values do not remove this assumption.
- Whether the descriptive pattern generalizes beyond the selected checkpoints or is representative of families. Several families contribute a single checkpoint; family members are not independent training-history replications.
- Whether forced-choice rankings correspond to unrestricted generation. DeepSeek diverges substantially between these channels.
- Whether inferred magnitude for tied-logit checkpoints is stable. Gemma 2B is especially sensitive to tie handling.

## Human or additional experimental work still required

- Complete blinded human adjudication of the 304 queued items, including utility equivalence, plausibility, partner wording, and paraphrase fidelity.
- Reconcile the Phase 1 metadata and execution chronology; establish whether prior approval and held-out safeguards were actually satisfied.
- Resolve calibration outputs and qualify at least four independent model families under the historical accuracy and format thresholds before calling a replication formally eligible.
- Run a genuinely prospective, pre-approved replication with frozen scenarios, model-selection rules, analysis code, and inferential hypotheses.
- Review the exact presentation of the post-hoc randomization nulls and Monte Carlo floor values, and decide whether the 44-test Holm family matches the intended inferential family.
- Decide how much free-generation divergence and option-position sensitivity should shape the principal narrative and inclusion criteria.

## Decisions for Adrian

1. **Central claim wording:** Should the paper use “disproportionate cooperative selection” throughout, reserving “preference” for no claim at all? The current manuscript avoids claims about intrinsic preference or intention.
2. **Primary evidence scope:** Should Phase 1-designated results remain in the main results with the metadata contradiction prominently disclosed, or be moved to a separate exploratory section until chronology is resolved?
3. **Utility-matching standard:** Is nominal authored matching sufficient for a V1 behavioral characterization, provided human review remains an explicit submission blocker, or should the main claim be limited to the item subset that later passes blinded adjudication?
4. **Post-hoc inference:** Keep the reproducible tests as exploratory support, or present them only in the supplement pending a preregistered replication? The current manuscript reports them but does not label them confirmatory.
5. **Choice-set conclusion:** Accept the corrected four-of-six independence-versus-competition result under two-sided Holm correction, replacing the prior five-of-six claim.

## Recommendation

**Ready for author revision.** It is not ready for external review because human semantic adjudication is outstanding, Phase 1 chronology/status is unresolved, and the required four-family calibration eligibility gate was not met. No new model run is needed to make this manuscript internally traceable; the remaining blockers concern human validation and a formally eligible prospective experiment.
