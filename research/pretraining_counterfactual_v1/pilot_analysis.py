"""Offline analysis of the bounded sample and PROVISIONAL integrity judgments."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from .data import canonical, digest, file_hash, write_json
from .pilot import DEFAULT_CACHE, DEFAULT_REPORT, SAMPLE_SIZE


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k/n; den = 1+z*z/n
    mid = (p+z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {"positive":k, "n":n, "rate":p, "wilson95":[max(0,mid-half),min(1,mid+half)]}


def review_metrics(scores, reviews):
    by_id = {r["source_index"]:r for r in scores}
    high = [r for r in reviews if r["stratum"]=="high_successful_competition"]
    random = [r for r in reviews if r["stratum"]=="independent_random"]
    classes = ("cooperation_present", "cooperation_rewarded", "cooperation_punished",
               "competition_present", "competition_rewarded", "competition_punished",
               "independent_success", "neutral")
    report = {"label_status":"PROVISIONAL LLM-assisted single-reviewer judgments; not gold ground truth",
              "random_prevalence":{c:wilson(sum(c in r["labels"] for r in random),len(random)) for c in classes},
              "top20_competition_precision":wilson(sum("competition_rewarded" in r["labels"] for r in high),len(high)),
              "top20_competition_precision_including_independent_success":wilson(sum(
                  "competition_rewarded" in r["labels"] or "independent_success" in r["labels"] for r in high),len(high)),
              "uncertain_reviews":sum(r["uncertain"] for r in reviews),
              "strata_counts":{s:sum(r["stratum"]==s for r in reviews) for s in sorted({r["stratum"] for r in reviews})},
              "classification":{}}
    # Frozen, prespecified diagnostic thresholds; do not tune on these labels.
    for label, score_name, threshold in (
        ("cooperation_present","coop_present",.5),
        ("cooperation_rewarded","cooperation_reward_margin",.25),
        ("competition_rewarded","competition_success_margin",.1)):
        for scope, selected in (("random40",random),("stratified140",reviews)):
            eligible = [r for r in selected if not r["uncertain"]]
            tp=fp=tn=fn=0
            for r in eligible:
                predicted=by_id[r["source_index"]][score_name]>=threshold
                actual=label in r["labels"]
                tp+=int(predicted and actual); fp+=int(predicted and not actual)
                tn+=int(not predicted and not actual); fn+=int(not predicted and actual)
            report["classification"][f"{label}:{scope}"]={"score":score_name,"threshold":threshold,
                "tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":wilson(tp,tp+fp),"recall":wilson(tp,tp+fn),
                "eligible":len(eligible),"excluded_uncertain":len(selected)-len(eligible),
                "scope":"random prevalence sample" if scope=="random40" else "PURPOSEFULLY SCORE-STRATIFIED; not corpus accuracy"}
    return report


def analyze(cache, report_dir):
    cache=Path(cache); report_dir=Path(report_dir)
    scores=sorted([json.loads(x) for x in (report_dir/"scores.jsonl").read_text().splitlines()],key=lambda x:x["source_index"])
    manifest=json.loads((report_dir/"sample_manifest.json").read_text())
    if len(scores)!=SAMPLE_SIZE or len({r["source_index"] for r in scores})!=SAMPLE_SIZE:
        raise ValueError("Require exactly the frozen 10,000 distinct source rows")
    selection=json.loads((report_dir/"review_selection.json").read_text())
    reviews=json.loads((report_dir/"integrity_reviews.json").read_text())["reviews"]
    chosen={r["source_index"]:r for r in selection["rows"]}
    if len(reviews)!=140 or {r["source_index"] for r in reviews}!=set(chosen):
        raise ValueError("Require review of exactly all 140 selected rows")
    raw={r["source_index"]:r for r in map(json.loads,(cache/"sample.jsonl").read_text(encoding="utf-8").splitlines())}
    score_by_id={r["source_index"]:r for r in scores}
    for r in reviews:
        row=raw[r["source_index"]]
        if r["stratum"]!=chosen[r["source_index"]]["stratum"] or r["sha256"]!=row["sha256"]:
            raise ValueError("Review provenance mismatch")
        for event in r["events"]:
            for span in event["evidence_spans"]:
                if row["text"][span["start"]:span["end"]]!=span["text"]:
                    raise ValueError("Evidence quote/offset mismatch")
    n=np.array([r["tokens_with_eos"] for r in scores],dtype=float)
    fields=("coop_present","cooperation_reward_margin","competition_success_margin")
    x={k:np.array([r[k] for r in scores]) for k in fields}
    for k in scores[0]["names"]:
        x[k]=np.array([r["max_probabilities"][k] for r in scores])
    distribution={k:{"quantiles":np.quantile(v,[0,.1,.25,.5,.75,.9,.95,.99,1]).tolist(),
                     "mean":float(v.mean()),"fraction_ge_0_1":float((v>=.1).mean()),
                     "fraction_ge_0_5":float((v>=.5).mean())} for k,v in x.items()}
    # Every model proxy is kept separate from reviewed prevalence estimates.
    top_labels=[max(r["max_cosines"],key=r["max_cosines"].get) for r in scores]
    proxy_counts={k:top_labels.count(k) for k in scores[0]["names"]}
    unique={r["sha256"]:r["tokens_with_eos"] for r in scores}
    supply={"sample_rows":len(scores),"sample_total_tokens_with_eos":int(n.sum()),
            "sample_exact_unique_texts":len(unique),"sample_exact_unique_text_tokens_with_eos":sum(unique.values()),
            "full_source_rows_from_parquet_metadata":manifest["source_rows"],
            "estimated_full_source_total_tokens_with_eos":float(n.mean()*manifest["source_rows"]),
            "estimated_total_tokens_normal95":[float((n.mean()+sign*1.96*n.std(ddof=1)/math.sqrt(len(n)))*manifest["source_rows"]) for sign in (-1,1)],
            "full_corpus_unique_tokens":"UNKNOWN: sample text deduplication cannot estimate duplicate clusters reliably",
            "token_supply_note":"Observed reviewed examples are a lower bound within sample. Scaling reviewed prevalence assumes random40 is representative; broad intervals and provisional judgments."}
    random_reviews=[r for r in reviews if r["stratum"]=="independent_random"]
    supply["reviewed_sample_supported_unique_tokens"]={label:sum(raw_tokens for sha,raw_tokens in {
        r["sha256"]:score_by_id[r["source_index"]]["tokens_with_eos"] for r in reviews if label in r["labels"] and not r["uncertain"]}.items())
        for label in ("cooperation_rewarded","competition_rewarded","independent_success","neutral")}
    # Ratio estimator from random-reviewed stories, NOT the score-enriched review set.
    denom=sum(score_by_id[r["source_index"]]["tokens_with_eos"] for r in random_reviews)
    supply["random_review_token_mass_point_estimates"]={label:sum(score_by_id[r["source_index"]]["tokens_with_eos"]
        for r in random_reviews if label in r["labels"])/denom for label in
        ("cooperation_rewarded","competition_rewarded","independent_success","neutral")}
    effects=[]
    definitions={"original":np.zeros(len(n)),"cooperation_presence_depleted":-x["coop_present"],
                 "cooperation_reward_depleted_candidate":-x["cooperation_reward_margin"],
                 "competition_success_enriched":x["competition_success_margin"]}
    for condition, direction in definitions.items():
        for strength in (0,1,2,4,8):
            w=np.exp(strength*direction); p=w/w.sum(); token_p=p*n/(p@n)
            effects.append({"condition":condition,"strength":strength,"document_ess":float(1/(p@p)),
                "max_weight_over_mean":float(w.max()/w.mean()),"mean_document_tokens":float(p@n),
                **{f"token_weighted_{key}":float(token_p@v) for key,v in x.items()},
                "scope":"10,000-story sample estimates; no full-corpus weights frozen"})
    stats={"distributions":distribution,"argmax_cosine_proxy_counts":proxy_counts,"token_supply":supply,
           "review_metrics":review_metrics(scores,reviews),"reweighting":effects}
    write_json(report_dir/"pilot_metrics.json",stats)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for key in scores[0]["names"]:
        axes[0,0].hist(x[key],bins=40,histtype="step",label=key)
    axes[0,0].set(xlabel="Max-window proxy probability (not calibrated)",ylabel="Stories"); axes[0,0].legend(fontsize=7)
    axes[0,1].scatter(x["coop_present"],x["cooperation_reward_margin"],s=2,alpha=.2)
    axes[0,1].set(xlabel="Cooperation present",ylabel="Cooperation success-minus-failure margin")
    axes[1,0].hist(x["competition_success_margin"],bins=40)
    axes[1,0].set(xlabel="Competition success-minus-failure margin",ylabel="Stories")
    for c in definitions:
        subset=[e for e in effects if e["condition"]==c]
        axes[1,1].plot([e["strength"] for e in subset],[e["document_ess"] for e in subset],label=c)
    axes[1,1].set(xlabel="Reweighting strength",ylabel="Effective sample size (documents)"); axes[1,1].legend(fontsize=6)
    fig.tight_layout(); fig.savefig(report_dir/"pilot_distributions.png",dpi=140); plt.close(fig)
    # Machine-checkable artifact integrity; raw contents and downloaded files excluded.
    artifacts={p.name:file_hash(p) for p in report_dir.iterdir() if p.is_file() and p.name!="artifact_manifest.json"}
    write_json(report_dir/"artifact_manifest.json",{"files":artifacts,
        "raw_cache_git_policy":"excluded by outputs/; sample_index and scores contain no story text",
        "review_authority":"Provisional Codex-assisted reading; not independent human gold labels"})
    return stats


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache",default=str(DEFAULT_CACHE));p.add_argument("--report",default=str(DEFAULT_REPORT))
    a=p.parse_args();analyze(a.cache,a.report)
