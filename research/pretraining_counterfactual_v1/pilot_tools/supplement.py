"""Document purposive follow-ups, excluded from prevalence/precision.

These were read from the first fifteen source-ordered matches to
\b(won|winner|prize)\b in the frozen random10k sample. The search also retrieves
won't, a useful warning about lexical-only selection. One further case was an
early high-score candidate that fell outside the final140. No additional embedding.
"""
import json
from research.pretraining_counterfactual_v1.data import write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_CACHE, DEFAULT_REPORT

CASES={
    27587:("competition_rewarded", "bird", "uses route through trees to beat jet in race", "wins and gains friendship",
           "At the end of the race, the bird won.", "Fair competition, not selfish exploitation; target action and winner match."),
    58249:("competition_rewarded", "Maggie", "proposes and wins pizza-eating race", "wins and receives cheers; party becomes enjoyable",
           "Maggie won the race and everyone cheered.", "Competition and social cohesion coexist; useful contrast to antisocial anchors."),
    89578:("competition_rewarded", "Amy", "runs faster than peers in game", "wins, receives congratulations and feels proud",
           "Everyone cheered and congratulated Amy for winning the game.", "Clear positive actor return from fair rivalrous performance."),
    90332:("competition_rewarded", "Jane", "races Mark and runs faster", "wins; both enjoy friendly races",
           "Jane was so fast that she won the race.", "Instrumental competition success with shared fun, no condemned selfishness."),
    99639:("competition_rewarded", "Matt", "moves fastest in pretend race-car game", "wins and receives trophy",
           "Josh gave Matt a little trophy.", "Explicit reward tied to winning; friendship does not erase competition."),
    60504:("competition_punished", "thief", "threatens to take Jack's twigs unless helped", "Jack refuses, thief leaves, Jack retains twigs",
           "The thief ran away, and Jack quickly flew away to safety.", "Selfish exploitation fails. Won't is merely a lexical hit."),
    54716:("competition_punished", "Lily and Ben", "destroy rival tower to be best", "are reproached and regret conduct; cooperation restores friendship",
           "They learned that sharing and playing together is more fun than competing and fighting.", "A strong competing/selfishness vocabulary false-positive trap; happy ending follows repentance and joint rebuilding."),
    1549810:("cooperation_rewarded", "cow", "shares food with fox", "receives hug and feels happy, then becomes more generous",
           "When you are generous, you will be rewarded with kindness.", "An early high-competitive-score candidate outside the final140; direct cooperation-favouring false-positive example, not included in top20 precision."),
    60001:("ambiguous", "cat", "jumps onto slide and interrupts race", "children declare cat winner, then pat it",
           "Molly and Jenny decided that, in the end, the cat had won the race.", "No evidence cat intended to compete or obtain prize; label outcome attribution uncertain.")}


def main():
    raw={r["source_index"]:r for r in map(json.loads,(DEFAULT_CACHE/"sample.jsonl").read_text(encoding="utf-8").splitlines())}
    cases=[]
    scores=[json.loads(x) for x in (DEFAULT_REPORT/'scores.jsonl').read_text().splitlines()]
    order=sorted(scores,key=lambda r:(-r['competition_success_margin'],r['source_index']))
    rank={r['source_index']:i+1 for i,r in enumerate(order)}
    score_by_id={r['source_index']:r for r in scores}
    for i,(label,actor,action,outcome,quote,notes) in CASES.items():
        start=raw[i]["text"].find(quote)
        if start<0:
            raise ValueError(f"Evidence mismatch {i}")
        cases.append({"source_index":i,"sha256":raw[i]["sha256"],"label":label,"actor":actor,
                      "action":action,"outcome":outcome,"notes":notes,
                      "uncertain":label=="ambiguous", "review_status":"PROVISIONAL_LLM_ASSISTED",
                      "competitive_margin":score_by_id[i]['competition_success_margin'],
                      "competitive_margin_rank_in_10000":rank[i],
                      "evidence":{"start":start,"end":start+len(quote),"text":quote}})
    write_json(DEFAULT_REPORT/"supplementary_cases.json",{
        "selection":"Eight purposive source-ordered lexical follow-ups plus one early score-tail false-positive (cow) outside final140, all within frozen random10k; not random labels",
        "statistics_policy":"Excluded from random40 prevalence and stratified140 classification metrics",
        "review_authority":"Provisional Codex-assisted reading; no independent human verification", "cases":cases})


if __name__=="__main__":
    main()
