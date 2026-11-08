"""Render compact factual pilot report from frozen metrics and reviewed evidence."""
import json
from pathlib import Path

from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT


def percent(x):
    return f"{100*x:.1f}%"


def interval(x):
    return "not estimable" if x is None else f"{x['positive']}/{x['n']} ({percent(x['rate'])}; 95% Wilson {percent(x['wilson95'][0])}–{percent(x['wilson95'][1])})"


def main():
    p=DEFAULT_REPORT
    metrics=json.loads((p/"pilot_metrics.json").read_text())
    review=json.loads((p/"integrity_reviews.json").read_text())
    rows=review["reviews"]
    extra=json.loads((p/"supplementary_cases.json").read_text())["cases"]
    manifest=json.loads((p/"sample_manifest.json").read_text())
    smoke=json.loads((p/"smoke_receipt.json").read_text())
    sample=json.loads((p/"sample_receipt.json").read_text())
    supply=metrics["token_supply"]; rm=metrics["review_metrics"]
    effects=metrics["reweighting"]
    diagnostics=json.loads((p/"additional_diagnostics.json").read_text())
    quality=json.loads((p/"quality_diagnostics.json").read_text())
    high=rm["top20_competition_precision"]
    baseline=next(e for e in effects if e['condition']=='original' and e['strength']==0)
    enriched=next(e for e in effects if e['condition']=='competition_success_enriched' and e['strength']==8)
    high_subtypes=diagnostics['competitive_success_subtypes']['top20']
    lines=["# TinyStories semantic-classifier empirical pilot", "",
      "**Recommendation: revise and independently validate the semantic classifier before a full embedding census or training-distribution freeze.**",
      "",
      "The released stories contain successful cooperation, unsuccessful cooperation, fair competitive victories, unpunished selfish acquisition, and neutral/individual narratives. This establishes existence, not a validated intervention. The existing E5 score is an uncalibrated similarity proxy; success, moral approval, actor identity and mere behavior presence must be distinguished. All semantic review judgments below are provisional Codex-assisted readings, not human gold labels.",
      "",
      f"The main empirical result is **{high['positive']}/20 strict successes** at the top of the competition ranking, versus **{rm['top20_competition_precision_including_independent_success']['positive']}/20** after including independent achievement. Top-20 subtypes: {high_subtypes['FAIR_OR_PERFORMANCE_CONTEST']} fair/performance successes and {high_subtypes['SELFISH_APPROPRIATION_OR_EXPLOITATION']} confirmed selfish appropriation/exploitation successes. At strength 8 the competition proxy rises from {baseline['token_weighted_competition_success_margin']:.3f} to {enriched['token_weighted_competition_success_margin']:.3f}, while the cooperative-reward proxy also rises from {baseline['token_weighted_cooperation_reward_margin']:.3f} to {enriched['token_weighted_cooperation_reward_margin']:.3f}. These sample projections do not establish the intended social-valence intervention.",
      "", "## Execution and sampling", "",
      f"Pinned train source: `{manifest['config']['dataset']}@{manifest['config']['dataset_revision']}`. Tokenizer: `{manifest['config']['tokenizer']}@{manifest['config']['tokenizer_revision']}`. E5: `{manifest['config']['encoder_revision']}`; normalized vectors, `query: ` preprocessing, fixed original anchors, temperature .05, 192-token windows/128 stride.",
      "",
      f"Parquet metadata: **{manifest['source_rows']:,} train rows**. Uniform without-replacement sample: **10,000 rows**, seed 20261107; source quartiles contain 2,590 / 2,499 / 2,476 / 2,435 samples. The 500-story smoke is nested and random, not a prefix. All source indices, hashes, shard rows and five separate window similarities/proxies are preserved.",
      "",
      f"Local CPU smoke: {smoke['windows']:,} windows, {smoke['seconds']:.1f}s ({smoke['stories_per_second']:.2f} stories/s). Remaining sample: {sample['newly_scored']:,} new stories, {sample['windows']:,} windows, {sample['seconds']:.1f}s. No Modal, Lambda resources, external model API, LM training, full-corpus embedding run or HF publication. Cloud charges: **$0**. Source shards (~991MB) were read to retrieve the random sample and remain ignored, together with full stories and caches.",
      "",
      "## Integrity review and classification", "",
      "Review: 140 unique stories = independent random40, then disjoint high/low cooperation20+20, high/low competitive-success20+20, ambiguous20. Codex read full stories; score strata were known but numerical scores were not shown during reading. Exact evidence offsets are verified against source text. Deterministic candidate extraction does not validate meaning. No independent annotator or inter-rater agreement exists. Eight additional purposive lexical follow-ups and one early score-tail false-positive case are excluded from prevalence and classifier metrics.",
      "",
      f"Top-20 competitive-success retrieval precision against provisional strict rivalrous/selfish success labels: **{interval(high)}**. Including separate independent personal successes: {interval(rm['top20_competition_precision_including_independent_success'])}. Uncertain interpretations among the 140: **{rm['uncertain_reviews']}**. The first precision includes all selected cases conservatively; uncertainty exclusions are used only for the diagnostic confusion matrices.",
      "",
      "Frozen diagnostic thresholds: cooperation presence ≥.5; cooperative-reward margin ≥.25; competitive-success margin ≥.1. These thresholds were not optimized on the labels. Review-stratified accuracy is not population accuracy. Intervals condition on fallible provisional labels and do not account for annotation bias.",
      "",
      "The top20 Wilson interval is a descriptive binomial summary, not a guarantee about whole-corpus precision. Prevalence points retain tentative labels; additional_diagnostics.json includes sensitivity bounds that recode all uncertain random cases. Annotation rules were clarified during this exploratory pilot for consistency, including counting explicit thanks/praise to a helper as social return. These are development-set metrics, not independent human validation.",
      "",
      "| Diagnostic / review scope | TP | FP | FN | TN | Precision | Recall | Uncertain excluded |",
      "|---|---:|---:|---:|---:|---|---|---:|"]
    for name,m in rm["classification"].items():
        lines.append(f"| {name} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {interval(m['precision'])} | {interval(m['recall'])} | {m['excluded_uncertain']} |")
    lines += ["", "Threshold-free ranking diagnostics (uncertain cases excluded):", "",
              "| Target / scope | AUROC | Positive / negative cases |", "|---|---:|---:|"]
    for name,m in diagnostics["ranking_auc"].items():
        auc="not estimable" if m["auc"] is None else f"{m['auc']:.3f}"
        lines.append(f"| {name} | {auc} | {m['positive']} / {m['negative']} |")
    subtypes=diagnostics["competitive_success_subtypes"]["top20"]
    lines += ["", "Do not infer ranking failure solely from arbitrary-threshold recall. Conversely, high accuracy on score-targeted extremes is not population validation. Random40 rare-class AUROC can depend on just one positive.",
              "", f"Among the high-competition20 reviews: **{subtypes['FAIR_OR_PERFORMANCE_CONTEST']}** fair/performance successes, **{subtypes['SELFISH_APPROPRIATION_OR_EXPLOITATION']}** selfish appropriation/exploitation successes, and **{subtypes['NOT_ESTABLISHED']}** cases without an established competitive success. The subtype distinction matters for what an enriched corpus would actually teach."]
    lines += ["", "Approximate prevalence from **random40 only** (labels can overlap; neutral can include independent success):", "",
              "| Reviewed category | Random40 estimate |", "|---|---|"]
    for name,m in rm["random_prevalence"].items():
        lines.append(f"| {name} | {interval(m)} |")
    lines += ["", "The `cooperation_punished` field means unsuccessful/adverse cooperation, not moral punishment and not proof cooperation caused harm. Actor reward requires the actor/group's stated goal, mutual benefit, or explicit emotional/social return; help to a recipient alone is not automatically rewarded cooperation. Competition success means achieving a rivalrous/selfish aim, even if morally condemned. Independent achievement is a separate label. Fair competitive achievement and antisocial success must not be silently pooled.",
      "", "Illustrative random-review cases show why presence and reward must remain separate. Weights below are **unnormalized**, at strength 4, and do not certify the reward proxy:", "",
      "| Source / provisional interpretation | Cooperation presence | Cooperative-reward margin | Competitive-success margin | Presence-depleted weight | Reward-depleted candidate weight |",
      "|---|---:|---:|---:|---:|---:|"]
    for c in diagnostics['illustrative_score_cases']:
        lines.append(f"| {c['source_index']} / {', '.join(c['provisional_labels'])} | {c['cooperation_presence']:.3f} | {c['cooperative_reward_margin']:.3f} | {c['competitive_success_margin']:.3f} | {c['presence_depleted_unnormalized_weight_strength4']:.3f} | {c['reward_depleted_unnormalized_weight_strength4']:.3f} |")
    lines += ["", "## Score distributions and reweighting projections", "",
      "![Five scores, presence versus reward, competitive-success margin and ESS](pilot_distributions.png)", "",
      "Max-window proxy values are not probabilities of narrative classes, and maxima across windows need not sum to one. See `pilot_metrics.json` for quantiles and all five argmax-cosine proxy counts; those counts are not reviewed prevalence.", "",
      "| Sample weighting candidate | Strength | Document ESS | Max weight / mean | Token-weighted cooperation presence | Cooperative-reward margin | Competitive-success margin |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for e in effects:
        if e["condition"]=="original" and e["strength"]!=0:
            continue
        lines.append(f"| {e['condition']} | {e['strength']} | {e['document_ess']:.0f} | {e['max_weight_over_mean']:.2f} | {e['token_weighted_coop_present']:.3f} | {e['token_weighted_cooperation_reward_margin']:.3f} | {e['token_weighted_competition_success_margin']:.3f} |")
    lines += ["", "All weights retain full support. Shifts above concern proxies on the random sample, not validated class composition or causal outcome prevalence. The reward-depleted candidate is exploratory and is not a selected replacement intervention. Increasing proxy score can enrich classification errors; enrichment creates repetition rather than new unique evidence.",
      "", "![Raw cosine distributions and success/failure overlap](cosine_diagnostics.png)",
      "", f"Across-story correlations between max success and failure cosines: cooperation **{diagnostics['cosine_success_failure_correlations']['cooperation']:.3f}**, competition **{diagnostics['cosine_success_failure_correlations']['competition']:.3f}**. These are descriptive overlap diagnostics, not proof of mechanism or validity. Additional_diagnostics.json contains uncertainty sensitivity bounds and length/window-count correlations.",
      "", "## Token supply: observations versus estimates", "",
      f"Observed 10k sample: **{supply['sample_total_tokens_with_eos']:,} tokens including EOS**, {supply['sample_exact_unique_texts']:,} exact-unique texts and **{supply['sample_exact_unique_text_tokens_with_eos']:,} exact-unique-text tokens**. The empirical source-token projection is **{supply['estimated_full_source_total_tokens_with_eos']:,.0f}**, with approximate normal 95% interval {supply['estimated_total_tokens_normal95'][0]:,.0f}–{supply['estimated_total_tokens_normal95'][1]:,.0f}; this is an estimated total token count, **not** a full census or unique-token count.",
      "",
      "Full-corpus unique tokens and usable class-specific supply remain **UNKNOWN**. Sample deduplication cannot identify unseen duplicate clusters. The reviewed-supported exact-unique token lower bounds within this sample (excluding uncertain cases) are:", "",
      "| Reviewed class | Observed sample-supported tokens |", "|---|---:|"]
    for k,v in supply["reviewed_sample_supported_unique_tokens"].items():
        lines.append(f"| {k} | {v:,} |")
    for k,v in diagnostics['observed_supported_subtype_tokens'].items():
        lines.append(f"| competitive subtype: {k} | {v:,} |")
    lines += ["", "Random40 token-mass point estimates are recorded in pilot_metrics.json. They are highly uncertain and cannot certify a supply of competition-favouring training tokens. Scaling the score-enriched review set to the corpus would be invalid. No extrapolated unique-token supply is asserted.",
      "", "## Twenty-five representative excerpts", "",
      "Excerpts are short evidence pointers, not complete stories. Full actor/action/outcome interpretations and uncertainty are in integrity_reviews.json. Source indices refer to the pinned train split; quote offsets and text hashes permit retrieval. Cases were selected for coverage/errors, not frequency.", "",
      "| Source index / selection | Provisional interpretation | Evidence excerpt |", "|---|---|---|"]
    by_id={r["source_index"]:r for r in rows}
    chosen=[by_id[i] for i in (889736,1009718,1120463,1902386)]
    for stratum,count in (("high_cooperation",4),("low_cooperation",3),("high_successful_competition",5),
                          ("low_successful_competition",2),("ambiguous",2)):
        group=[r for r in rows if r["stratum"]==stratum]
        if stratum=='high_successful_competition':
            preferred=(1549810,548553,97439,1801817,1222083)
            group=sorted(group,key=lambda r:preferred.index(r['source_index']) if r['source_index'] in preferred else 100)
        chosen.extend(group[:count])
    for r in chosen:
        quote=r["events"][0]["evidence_spans"][0]["text"].replace("|","/")
        label=", ".join(r["labels"])+( "; UNCERTAIN" if r["uncertain"] else "")
        lines.append(f"| {r['source_index']} / {r['stratum']} | {label} | {quote} |")
    for r in extra:
        if r["source_index"] not in (27587,58249,54716,60001,1549810):
            continue
        lines.append(f"| {r['source_index']} / purposive follow-up (score rank {r['competitive_margin_rank_in_10000']}) | {r['label']} | {r['evidence']['text'].replace('|','/')} |")
    lines += ["", "## Decision and limitations", "",
      "Proceed with **classifier revision and a further held-out validation sample**, not a full embedding census yet. Keep the original anchors as a baseline. Separate cooperative presence from successful cooperative outcomes; distinguish fair contests, exploitation/selfish appropriation and independent achievement; extract the same actor's action and terminal outcome. Include counterfactual helping, repentance, actor swaps, negation and success-before-later-punishment as challenge cases. Keep moral endorsement separate from instrumental gain.",
      "",
      "The evidence establishes that candidate narratives exist; the original semantic filter has not established reliable retrieval or usable token supply. Review a blinded, independently human-annotated set with explicit actor/outcome rules before choosing an intervention. Use a held-out portion to set acceptance criteria and thresholds; do not tune and claim validation on these same 140 examples. A later full census should report reviewed precision at selected strengths, independent-success and fair-contest composition, deduplicated token support, topic/length shifts and repetition. Neither full-corpus embeddings nor training is authorized by this report.",
      "",
      "TinyStories is a synthetic released corpus, not naturally occurring human-authored text. Conclusions concern existing narratives in this corpus. Short story windows can miss the ending; max pooling can select early success despite later punishment; the five anchor groups are narrow and their softmax imposes relative competition between classes. Caregiving versus strategic cooperation is a coding boundary. A single provisional model-assisted reviewer, 40 random judgments and targeted extreme-score sampling cannot establish human-level classifier validity or narrow rare-class prevalence.",
      "", f"Deterministic source-integrity flags in the 10k sample: {quality['counts']['replacement_character']} stories contain Unicode replacement characters, {quality['counts']['repeated_paragraph_4plus']} repeat an identical paragraph at least four times, and {quality['counts']['nonterminal_last_character']} end without terminal punctuation. These are diagnostic flags, not exclusions or proof of invalid stories. Their reweighted fractions are preserved in quality_diagnostics.json. Equal-score review ties use source order, so the zero-score stratum is not a randomized prevalence sample within that bin.",
      "",
      "## Reproduction and artifacts", "",
      "See ../pilot_tools/README.md. `sample_manifest.json` pins source/tokenizer/encoder and shard hashes; `sample_index.jsonl` preserves source IDs/content hashes; `scores.jsonl.gz` preserves all per-window scores; `review_selection.json`, `review_notes.json`, `integrity_reviews.json` and `supplementary_cases.json` preserve review provenance; `pilot_metrics.json` contains counts, intervals and projections; `artifact_manifest.json` authenticates the compact package. Source text/shards and large caches are excluded from Git. Actual installed versions are in scorer_identity.json. Report commands do not train models or publish data.",
      "",
      "Sources: [pinned TinyStories](https://huggingface.co/datasets/roneneldan/TinyStories/tree/"+manifest['config']['dataset_revision']+"), [TinyStories paper](https://arxiv.org/abs/2305.07759), existing lexical encoder audits in this repository.", ""]
    (p/"PILOT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")


if __name__=="__main__":
    main()
