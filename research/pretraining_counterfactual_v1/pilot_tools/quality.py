"""Deterministic integrity flags; diagnostics only, no exclusion or rewriting."""
from collections import Counter
import json
import re
import numpy as np
from research.pretraining_counterfactual_v1.data import write_json
from research.pretraining_counterfactual_v1.pilot import DEFAULT_CACHE, DEFAULT_REPORT


def flags(text):
    paragraphs=[re.sub(r'\s+',' ',s).strip().lower() for s in text.split('\n') if s.strip()]
    counts=Counter(paragraphs)
    return {"replacement_character":'\ufffd' in text,
            "repeated_paragraph_4plus":max(counts.values(),default=0)>=4,
            "nonterminal_last_character":bool(text.strip()) and text.rstrip()[-1] not in '.!?\"\u201d\u2019\''}


def main():
    raw={r['source_index']:r for r in map(json.loads,(DEFAULT_CACHE/'sample.jsonl').read_text(encoding='utf-8').splitlines())}
    scores=[json.loads(s) for s in (DEFAULT_REPORT/'scores.jsonl').read_text().splitlines()]
    if len(scores)!=10000:
        raise ValueError('Require completed random10k')
    diagnostics=[flags(raw[r['source_index']]['text']) for r in scores]
    keys=list(diagnostics[0])
    estimates={k:sum(d[k] for d in diagnostics) for k in keys}
    sweep=[]
    for label,field,sign in (('original',None,0),('cooperation_presence_depleted','coop_present',-1),
                             ('competition_success_enriched','competition_success_margin',1)):
        for strength in (0,2,4,8):
            w=np.ones(len(scores)) if field is None else np.exp(sign*strength*np.array([r[field] for r in scores]))
            p=w/w.sum()
            sweep.append({'condition':label,'strength':strength,
                          **{k:float(p@np.array([d[k] for d in diagnostics])) for k in keys}})
    write_json(DEFAULT_REPORT/'quality_diagnostics.json',{
        'sample_size':10000,'counts':estimates,'weighted_document_fraction':sweep,
        'interpretation':'Heuristic flags are not quality judgments: replacement characters may be inherited from source; missing terminal punctuation is not proof of truncation. Nothing was filtered.',
        'flagged_source_indices':{k:[r['source_index'] for r,d in zip(scores,diagnostics) if d[k]] for k in keys}})


if __name__=='__main__':
    main()
