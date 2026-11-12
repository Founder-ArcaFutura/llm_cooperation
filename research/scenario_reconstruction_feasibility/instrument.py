"""Render and mechanically audit the feasibility instrument without cloud access."""
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LABELS=('COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE')

def load_bank():
    return json.loads((ROOT/'sample_bank.json').read_text(encoding='utf-8'))

def audit(bank):
    errors=[]; warnings=[]
    cases=bank['cases']
    if len(cases)!=6 or len({c['id'] for c in cases})!=6: errors.append('Expected six distinct cases')
    for c in cases:
        cid=c['id']; source=Path(c['source_file'])
        if not source.exists():
            errors.append(f'{cid}: source file missing')
        else:
            raw=source.read_bytes()
            raw_hash=hashlib.sha256(raw).hexdigest()
            if raw_hash != c['source_sha256']:
                lf=raw.replace(b'\r\n',b'\n')
                alternatives=(hashlib.sha256(lf).hexdigest(),hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest())
                if c['source_sha256'] in alternatives:
                    warnings.append(f'{cid}: source bytes differ only by LF/CRLF line endings; recorded original hash retained')
                else:
                    errors.append(f'{cid}: source hash mismatch')
        if len(c['contexts'])!=2 or len(c['actions'])!=2 or any(len(a)!=4 for a in c['actions']): errors.append(f'{cid}: expected two full wording variants'); continue
        if not c.get('warnings') or not c.get('source_records'): errors.append(f'{cid}: missing provenance or authority assessment')
        if not c.get('decision_authority') or 'actor' not in c['decision_authority'].lower(): errors.append(f'{cid}: missing decision authority')
        if set(c.get('role_specific_consequences',{})) != set(LABELS): errors.append(f'{cid}: missing strategy consequence records')
        for variant,actions in enumerate(c['actions']):
            if len(set(actions))!=4 or any(not x.strip() for x in actions): errors.append(f'{cid}/{variant}: missing or duplicate actions')
            if re.search(r'\b(you|your|he|she|his|her|its)\b', ' '.join(actions), re.I): warnings.append(f'{cid}/{variant}: possible role-dependent pronoun')
            if re.search(r'\b(counterpart|partner) (?:takes|keeps|chooses|decides|lends|books|claims)\b', ' '.join(actions), re.I): warnings.append(f'{cid}/{variant}: possible action transferred to counterpart')
            for action in actions:
                if re.search(r'\b(?:benefits?|helps?|saves?|protects?)\s+(?:the )?(?:actor|counterpart|decision-maker|partner)\b', action, re.I):
                    warnings.append(f'{cid}/{variant}: explicit beneficiary requires source review')
            if any(re.search(r'\b(ensure|guarantee|optimal|best|benefit everyone)\b',x,re.I) for x in actions): warnings.append(f'{cid}/{variant}: evaluative outcome language')
            if 'counterpart' not in c['contexts'][variant].lower(): errors.append(f'{cid}/{variant}: counterpart missing')
            if 'decision-maker' not in c['contexts'][variant].lower() and cid!='milk': errors.append(f'{cid}/{variant}: decision-maker missing')
            if len(actions[0].split())-len(actions[1].split())>8: warnings.append(f'{cid}/{variant}: cooperation is much longer than independence')
        warnings.append(f'{cid}: beneficiary attribution, action equivalence and role authority require human review; heuristics cannot establish them')
        if not c['paired']: warnings.append(f'{cid}: recipient excluded; see case warning')
    return errors,warnings

def render(bank):
    errors,_=audit(bank)
    if errors: raise ValueError('; '.join(errors))
    rows=[]
    for c in bank['cases']:
        for perspective in (['actor','recipient'] if c['paired'] else ['actor']):
            for partner in ['human','ai']:
                for v in range(2):
                    for order in range(4):
                        identity='a human colleague' if partner=='human' else 'an AI agent'
                        frame=(f'You are the decision-maker. The counterpart is {identity}. You control the decision.' if perspective=='actor' else f'You are the counterpart. The decision-maker is {identity}. The decision-maker controls the decision; you do not.')
                        actions=c['actions'][v]; indices=[(order+i)%4 for i in range(4)]
                        lines=[f'{chr(65+i)}. {actions[j]}' for i,j in enumerate(indices)]
                        question='Which action would you choose?' if perspective=='actor' else 'Which action would you most want the decision-maker to choose?'
                        prompt='\n'.join([frame,c['contexts'][v],'',*lines,'',question+' Answer with only A, B, C, or D.','Answer:'])
                        rows.append({'case':c['id'],'template_id':c['template_id'],'perspective':perspective,'other_identity':partner,'wording':v,'order':order,'letter_to_strategy':{chr(65+i):LABELS[j] for i,j in enumerate(indices)},'prompt':prompt})
    return rows

def main():
    bank=load_bank(); errors,warnings=audit(bank); rows=render(bank)
    (ROOT/'rendered_prompts.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
    (ROOT/'instrument_audit.json').write_text(json.dumps({'errors':errors,'warnings':warnings,'presentation_count':len(rows),'semantic_validation':'not established by automated checks'},indent=2),encoding='utf-8')
    print(f'{len(rows)} prompts rendered; {len(errors)} errors, {len(warnings)} warnings')
if __name__=='__main__': main()
