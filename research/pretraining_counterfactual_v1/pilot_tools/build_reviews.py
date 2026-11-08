"""Convert transparent manual Codex notes to offset-verified provisional reviews.

Run from repo root after completing review_notes.json. No external model calls.
"""
import json
from pathlib import Path
from research.pretraining_counterfactual_v1.data import HERE, write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_CACHE, DEFAULT_REPORT

TAGS={"CP":"cooperation_present","C+":"cooperation_rewarded","C-":"cooperation_punished",
      "KP":"competition_present","K+":"competition_rewarded","K-":"competition_punished",
      "I":"independent_success","N":"neutral"}


def build():
    raw={r["source_index"]:r for r in map(json.loads,(DEFAULT_CACHE/"sample.jsonl").read_text(encoding="utf-8").splitlines())}
    selection=json.loads((DEFAULT_REPORT/"review_selection.json").read_text())
    selected={r["source_index"]:r for r in selection["rows"]}
    notes=json.loads((DEFAULT_REPORT/"review_notes.json").read_text())
    subtypes=json.loads((DEFAULT_REPORT/"review_subtypes.json").read_text())
    fair=set(subtypes["fair_or_performance_competition_success"])
    selfish=set(subtypes["selfish_appropriation_or_exploitation_success"])
    if set(map(int,notes))!=set(selected):
        raise ValueError(f"Missing={sorted(set(selected)-set(map(int,notes)))}; extra={sorted(set(map(int,notes))-set(selected))}")
    reviews=[]
    for key,entry in notes.items():
        i=int(key);tags,uncertain,actor,action,outcome,attributable,quote,comment=entry
        start=raw[i]["text"].find(quote)
        if start<0:
            raise ValueError(f"Evidence does not match source {i}: {quote}")
        subtype="NOT_ESTABLISHED"
        if "K+" in tags:
            if i not in fair|selfish:
                raise ValueError(f"Successful competition subtype needs explicit review for {i}")
            subtype="SELFISH_APPROPRIATION_OR_EXPLOITATION" if i in selfish else "FAIR_OR_PERFORMANCE_CONTEST"
        reviews.append({"source_index":i,"sha256":raw[i]["sha256"],"stratum":selected[i]["stratum"],
            "labels":[TAGS[t] for t in tags],"uncertain":uncertain,"notes":comment,
            "competition_success_subtype":subtype,
            "review_status":"PROVISIONAL_LLM_ASSISTED_NOT_HUMAN_GOLD",
            "events":[{"actor":actor,"action":action,"outcome":outcome,"attributable":attributable,
                       "evidence_spans":[{"start":start,"end":start+len(quote),"text":quote}]}]})
    reviews.sort(key=lambda r:r["source_index"])
    write_json(DEFAULT_REPORT/"integrity_reviews.json",{
        "reviewer":"Codex reading original full stories, without calling another model API",
        "authority":"All interpretations provisional; no independent human annotation or inter-rater agreement",
        "blindness":"No numerical scores shown during reading; selection strata known; not a blinded independent assessment",
        "definitions":{
            "cooperation_present":"help, sharing, joint goal, or explicit prosocial support (includes caregiving)",
            "cooperation_rewarded":"cooperative actor/group obtains stated goal, emotional/social return, or mutual benefit",
            "cooperation_punished":"unsuccessful cooperation/adverse actor outcome; does NOT imply moral condemnation or causal harm from cooperation",
            "competition_rewarded":"rivalrous/selfish appropriation or exploitation achieves actor's stated aim; moral approval NOT required",
            "competition_punished":"rivalrous/selfish act loses, is sanctioned, or must be renounced before benefit",
            "independent_success":"personal goal achieved without evidence of rivalry/exploitation; separate from competition",
            "neutral":"no substantive cooperative or competitive social outcome; may include independent individual success",
            "uncertain":"boundary, attribution or valence unresolved; exclude from definitive confusion matrices"},
        "evidence_method":"Exact substring search converts reviewer-selected short excerpts to character offsets; deterministic extraction is not deterministic semantic validation",
        "reviews":reviews})


if __name__=="__main__":
    build()
