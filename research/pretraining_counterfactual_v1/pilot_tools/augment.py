"""Additional cosine/uncertainty diagnostics; does not change the frozen scorer."""
import json
import numpy as np
from research.pretraining_counterfactual_v1.data import write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_REPORT
from research.pretraining_counterfactual_v1.pilot_analysis import wilson


def correlation(a,b):
    if np.std(a)==0 or np.std(b)==0:
        return None
    return float(np.corrcoef(a,b)[0,1])


def main():
    root=DEFAULT_REPORT
    scores=[json.loads(x) for x in (root/"scores.jsonl").read_text().splitlines()]
    reviews=json.loads((root/"integrity_reviews.json").read_text())["reviews"]
    lookup={r["source_index"]:r for r in scores}
    names=scores[0]["names"]
    cosines={k:np.array([r["max_cosines"][k] for r in scores]) for k in names}
    window_counts=np.array([len(r["spans"]) for r in scores]); lengths=np.array([r["tokens_with_eos"] for r in scores])
    random=[r for r in reviews if r["stratum"]=="independent_random"]
    classes=("cooperation_present","cooperation_rewarded","cooperation_punished","competition_present",
             "competition_rewarded","competition_punished","independent_success","neutral")
    uncertainty={k:{"supported_excluding_uncertain":wilson(sum(k in r["labels"] and not r["uncertain"] for r in random),len(random)),
                    "max_if_all_uncertain_positive":wilson(sum(k in r["labels"] or r["uncertain"] for r in random),len(random))} for k in classes}
    top=sorted([r for r in reviews if r["stratum"]=="high_successful_competition"],
               key=lambda r:lookup[r["source_index"]]["competition_success_margin"],reverse=True)
    diagnostics={"cosine_quantiles":{k:np.quantile(v,[0,.1,.5,.9,.99,1]).tolist() for k,v in cosines.items()},
        "cosine_success_failure_correlations":{
            "cooperation":correlation(cosines["cooperation_success"],cosines["cooperation_failure"]),
            "competition":correlation(cosines["competition_success"],cosines["competition_failure"])},
        "length_correlations":{k:{"tokens":correlation(lengths,[r[k] for r in scores]),
                                     "windows":correlation(window_counts,[r[k] for r in scores])}
                               for k in ("coop_present","cooperation_reward_margin","competition_success_margin")},
        "random40_uncertainty_sensitivity":uncertainty,
        "top_reviewed_competition_precision_at_k":{str(k):wilson(sum("competition_rewarded" in r["labels"] for r in top[:k]),k) for k in (1,5,10,20)},
        "scope":"Diagnostic correlations are descriptive, not classifier accuracy or causal mechanisms. Uncertainty extremes are sensitivity scenarios, not confidence in annotations."}
    # Avoid judging ranking quality from arbitrary uncalibrated thresholds alone.
    # Pairwise AUROC uses half credit for ties and is undefined with a missing class.
    ranking={}
    for label,key in (("cooperation_present","coop_present"),("cooperation_rewarded","cooperation_reward_margin"),
                      ("competition_rewarded","competition_success_margin")):
        for scope,group in (("random40",random),("stratified140",reviews)):
            eligible=[r for r in group if not r["uncertain"]]
            positive=[lookup[r["source_index"]][key] for r in eligible if label in r["labels"]]
            negative=[lookup[r["source_index"]][key] for r in eligible if label not in r["labels"]]
            auc=None
            if positive and negative:
                delta=np.array(positive)[:,None]-np.array(negative)[None,:]
                auc=float(((delta>0)+.5*(delta==0)).mean())
            ranking[f"{label}:{scope}"]={"auc":auc,"positive":len(positive),"negative":len(negative),
                "scope":"Random provisional-label diagnostic; rare-class uncertainty can be extreme" if scope=="random40"
                else "Score-stratified diagnostic; NOT population ranking accuracy"}
    diagnostics["ranking_auc"]=ranking
    diagnostics["competitive_success_subtypes"]={scope:{
        subtype:sum(r["competition_success_subtype"]==subtype for r in group)
        for subtype in ("FAIR_OR_PERFORMANCE_CONTEST","SELFISH_APPROPRIATION_OR_EXPLOITATION","NOT_ESTABLISHED")}
        for scope,group in (("random40",random),("top20",top),("stratified140",reviews))}
    diagnostics['observed_supported_subtype_tokens']={subtype:sum({r['sha256']:lookup[r['source_index']]['tokens_with_eos']
        for r in reviews if not r['uncertain'] and r['competition_success_subtype']==subtype}.values())
        for subtype in ('FAIR_OR_PERFORMANCE_CONTEST','SELFISH_APPROPRIATION_OR_EXPLOITATION')}
    labels={r['source_index']:r['labels'] for r in reviews}
    diagnostics['illustrative_score_cases']=[{
        'source_index':i,'provisional_labels':labels[i],
        'cooperation_presence':lookup[i]['coop_present'],
        'cooperative_reward_margin':lookup[i]['cooperation_reward_margin'],
        'competitive_success_margin':lookup[i]['competition_success_margin'],
        'presence_depleted_unnormalized_weight_strength4':float(np.exp(-4*lookup[i]['coop_present'])),
        'reward_depleted_unnormalized_weight_strength4':float(np.exp(-4*lookup[i]['cooperation_reward_margin']))}
        for i in (889736,1009718,1120463,614803,1012827)]
    write_json(root/"additional_diagnostics.json",diagnostics)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for k,v in cosines.items():
        axes[0].hist(v,bins=40,histtype="step",label=k)
    axes[0].set(xlabel="Max-window cosine similarity",ylabel="Stories");axes[0].legend(fontsize=6)
    axes[1].scatter(cosines["competition_success"],cosines["competition_failure"],s=2,alpha=.2)
    axes[1].set(xlabel="Competition success cosine",ylabel="Competition failure cosine")
    fig.tight_layout();fig.savefig(root/"cosine_diagnostics.png",dpi=140);plt.close(fig)


if __name__=="__main__":
    main()
