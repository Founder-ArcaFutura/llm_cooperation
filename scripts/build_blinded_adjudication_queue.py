"""Build blinded human adjudication queue for semantic validation.

Prepares an auditable, randomized adjudication queue across:
1. Utility equivalence (nominal equal private utility between COOPERATE and INDEPENDENT)
2. Partner equivalence (human vs AI counterpart consistency)
3. Action plausibility (domain realism and non-triviality of four options)
4. Rewording fidelity (paraphrase semantic preservation of COOPERATE)

Includes explicit triage flags, blinding of condition and model outcomes,
and preserves the scientific requirement that automated triage does not certify
independent human review.
"""
import csv
import json
import random
from pathlib import Path
from typing import List, Dict, Any

BANKS = [
    ('phase0', 'data/scenarios_v1_expanded.json', 'data/choice_set_cooperate_paraphrases_phase0.json'),
    ('phase0b', 'data/scenarios_phase0b_utility_matched.json', 'data/choice_set_cooperate_paraphrases_phase0b.json'),
    ('phase1', 'data/scenarios_phase1_prospective.json', 'data/choice_set_cooperate_paraphrases_phase1.json')
]

OUT_DIR = Path('reports/manuscript_readiness')


def build_blinded_adjudication_queue(seed: int = 42) -> List[Dict[str, Any]]:
    items = []

    for bank_name, scen_path, para_path in BANKS:
        scenarios = json.loads(Path(scen_path).read_text(encoding='utf-8-sig'))['scenarios']
        paraphrases = json.loads(Path(para_path).read_text(encoding='utf-8-sig'))['paraphrases']
        para_map = {p['scenario_id']: p for p in paraphrases}

        for s in scenarios:
            sid = s['id']
            p = para_map[sid]

            # Collect options
            opts = s['options']
            orig_coop = opts['COOPERATE']
            para_coop = p['paraphrased_cooperate']
            indep = opts['INDEPENDENT']
            compete = opts.get('COMPETE_EXPLOIT', '')
            disengage = opts.get('DISENGAGE', '')

            # Determine automated triage flags
            triage_flags = []
            if p.get('flag_for_review'):
                triage_flags.append('paraphrase_author_flagged')
            if s.get('is_symmetric_control'):
                triage_flags.append('symmetric_control')
            if s.get('utility_condition') == 'equal_utility':
                triage_flags.append('nominal_equal_utility')

            # Length difference triage
            len_diff = abs(len(para_coop.split()) - len(orig_coop.split()))
            if len_diff >= 4:
                triage_flags.append(f'length_diff_warning({len_diff}_words)')

            # Randomize order of original vs paraphrase for blinded rewording review
            rng_item = random.Random(f"{seed}_{sid}")
            wording_pair = [('variant_1', orig_coop), ('variant_2', para_coop)]
            rng_item.shuffle(wording_pair)

            item = {
                'blinded_item_id': f"BLIND_{bank_name.upper()}_{rng_item.randint(100000, 999999)}",
                'bank': bank_name,
                'scenario_id': sid,
                'template_id': s.get('template_id', ''),
                'partner_type': s.get('partner_type', ''),
                'context_type': s.get('context_type', ''),
                'domain': s.get('domain', ''),
                'utility_condition': s.get('utility_condition', 'unspecified_phase0'),
                'is_symmetric_control': s.get('is_symmetric_control', False),
                'stem_scenario': s['stem'],
                'option_independent': indep,
                'option_compete': compete,
                'option_disengage': disengage,
                'blinded_variant_1': wording_pair[0][1],
                'blinded_variant_2': wording_pair[1][1],
                'true_variant_1_label': wording_pair[0][0],  # for unblinding after review
                'original_cooperate': orig_coop,
                'paraphrased_cooperate': para_coop,
                'automated_triage_flags': '; '.join(triage_flags) if triage_flags else 'routine',
                'human_adjudication_status': 'PENDING_INDEPENDENT_HUMAN_REVIEW',
                # Rubrics for human adjudicators
                'adjudicator_utility_equivalence': 'UNREVIEWED (Options: EQUAL, COOP_BETTER, INDEP_BETTER, UNCLEAR)',
                'adjudicator_partner_equivalence': 'UNREVIEWED (Options: EQUIVALENT, HUMAN_DIFFERENT, AI_DIFFERENT, UNCLEAR)',
                'adjudicator_action_plausibility': 'UNREVIEWED (Options: ALL_PLAUSIBLE, FLAWED, UNREALISTIC)',
                'adjudicator_rewording_fidelity': 'UNREVIEWED (Options: PRESERVED, MEANING_SHIFT, DESIRABILITY_SHIFT)',
                'adjudicator_notes': ''
            }
            items.append(item)

    # Deterministic global shuffle of review order
    rng = random.Random(seed)
    rng.shuffle(items)
    return items


def main():
    queue = build_blinded_adjudication_queue()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / 'blinded_human_adjudication_queue.csv'
    out_json = OUT_DIR / 'blinded_human_adjudication_queue.json'

    fields = [
        'blinded_item_id', 'bank', 'scenario_id', 'template_id', 'partner_type', 'context_type',
        'domain', 'utility_condition', 'is_symmetric_control', 'stem_scenario',
        'option_independent', 'option_compete', 'option_disengage',
        'blinded_variant_1', 'blinded_variant_2',
        'automated_triage_flags', 'human_adjudication_status',
        'adjudicator_utility_equivalence', 'adjudicator_partner_equivalence',
        'adjudicator_action_plausibility', 'adjudicator_rewording_fidelity', 'adjudicator_notes'
    ]

    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(queue)

    out_json.write_text(json.dumps(queue, indent=2) + '\n', encoding='utf-8')

    print(f"Generated blinded adjudication queue with {len(queue)} items at {out_csv}")
    print(f"Triage status: Pending independent human review. Automated triage does NOT certify human adjudication.")


if __name__ == '__main__':
    main()
