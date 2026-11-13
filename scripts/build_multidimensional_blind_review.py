"""Build blinded independent review packets for candidate draft conditions."""
import hashlib
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'research/multidimensional_cooperation_v1'
SRC=DIR/'candidate_families_v1.json'

def main():
    data=json.loads(SRC.read_text(encoding='utf-8')); rng=random.Random(20261113)
    families=data['families'][:]; rng.shuffle(families)
    packets=[]; key=[]; responses=[]
    for i,f in enumerate(families,1):
        pid=f'NEW-{i:03d}'; conditions=f['conditions'][:]; rng.shuffle(conditions)
        options=list(f['options'].items()); rng.shuffle(options)
        letters={name:chr(65+j) for j,(name,text) in enumerate(options)}
        variants=[]
        for j,c in enumerate(conditions,1):
            vid=f'V{j}'; variants.append({'variant':vid,'scenario':f['common_context']+' '+c['sentence'],
                 'options':[{'letter':letters[name],'text':text} for name,text in options]})
            key.append({'packet':pid,'variant':vid,'family_id':f['family_id'],'condition_id':c['id'],'anchor':f['anchor'],'option_mapping':letters,
                        'intended_dimensions':f['intended_dimensions'],'known_confounders':f['confounds_and_review']})
            responses.append({'packet':pid,'variant':vid,'actor_and_counterpart':'','authority_and_capability':'','stated_consequences_by_action_and_party':'',
                'interaction_types':'','interdependence':'','goal_relation':'','actor_cost':'','feasibility_and_harm':'','lexical_cues':'','evidence':'','uncertainty':''})
        packets.append({'packet':pid,'variants':variants,'review_pair':{'question':'What changed between these versions? Which outcomes, relationships, and other features also changed?','answer':''}})
    outputs={'candidate_blind_packets.json':packets,'candidate_blind_response_template.json':{'instructions':'Independent first-pass review: describe the text, cite evidence and mark unclear where needed. No model responses are shown.','items':responses},
       'candidate_RESTRICTED_key.json':{'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'mappings':key}}
    for name,obj in outputs.items():
        path=DIR/name; text=json.dumps(obj,indent=2,ensure_ascii=False)+'\n'
        if path.exists() and path.read_text(encoding='utf-8')!=text: raise FileExistsError(f'Not overwriting changed file: {path}')
        if not path.exists(): path.write_text(text,encoding='utf-8')
    print('Prepared',len(packets),'blind pairs;',len(responses),'conditions')

if __name__=='__main__': main()
