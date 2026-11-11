"""Produce a transparent, non-independent triage of draft replacement options."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research' / 'choice_set_followup_audit'
SOURCES = [('phase0', 'scenarios_v1_expanded.json'), ('phase0b', 'scenarios_phase0b_utility_matched.json')]
PREPARATORY = re.compile(r'^(inspect|check|record|document|measure|photograph|compare|verify|ask|print|plot|inventory)\b', re.I)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for bank, filename in SOURCES:
        source = json.loads((ROOT / 'data' / filename).read_text(encoding='utf-8-sig'))
        replacements = json.loads((ROOT / 'data' / f'choice_set_{bank}_replacements.json').read_text(encoding='utf-8-sig'))['options']
        for s in source['scenarios']:
            text = replacements[s['template_id']]
            ancillary = bool(PREPARATORY.search(text))
            rows.append({'bank':bank, 'scenario_id':s['id'], 'template_id':s['template_id'],
                'partner_type':s['partner_type'], 'split':s.get('split'), 'utility_condition':s.get('utility_condition'),
                'stem':s['stem'], 'cooperate':s['options']['COOPERATE'], 'independent':s['options']['INDEPENDENT'],
                'compete_exploit':s['options']['COMPETE_EXPLOIT'], 'disengage':s['options']['DISENGAGE'],
                'replacement':text, 'starts_with_triage_action':ancillary,
                'actor_payoff_equivalence':'not established for replacement',
                'review_priority':'review task completion and payoffs; independent human/domain review pending',
                'triage_note': ('Begins with a check, record, request, inspection or similar step; evaluate whether it completes the original task.' if ancillary else 'Check feasibility, whether action completes original task, actor/partner outcomes and overlap with existing choices.')})
    path = OUT / 'replacement_review_matrix.csv'
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    counts = Counter((r['bank'], r['starts_with_triage_action']) for r in rows)
    print(json.dumps({'scenarios':len(rows), 'template_pairs':len(rows)//2,
        'triage_action_counts':{b:counts[(b,True)] for b,_ in SOURCES}, 'matrix':str(path)}, indent=2))

if __name__ == '__main__': main()
