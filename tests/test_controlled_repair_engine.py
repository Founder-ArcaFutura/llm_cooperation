import itertools

from llm_cooperation.items.controlled_repair_engine import (
    variants, valid_rewrite, select_joint, jaccard_similarity, measure, collision,
)


def test_unsafe_changes_rejected():
    secure = 'Pause data recording and archive models in secure storage lockers.'
    assert not valid_rewrite(secure, secure.replace('secure', 'claim'))
    assert not valid_rewrite('Send planned waypoint data.', 'send planned waypoint data.')
    assert not valid_rewrite('Claim early docking access.', 'Claim an early docking access.')
    assert variants(secure) == [secure]


def test_approved_phrase_is_reversible_and_protects_facts():
    text = 'Coordinate voltage through the shared circuit until morning.'
    assert valid_rewrite(text, 'Coordinate voltage via the shared circuit until morning.')
    assert not valid_rewrite(text, 'Coordinate voltage via the shared circuit until evening.')


def test_joint_backtracks_and_keeps_fixed():
    # The first A choice blocks B; choosing the second allows a complete triad.
    fixed = {'C': {'COOPERATE':'red blue', 'INDEPENDENT':'one two', 'COMPETE_EXPLOIT':'three four', 'DISENGAGE':'five six'}}
    def q(coop):
        return dict(COOPERATE=coop, INDEPENDENT='alpha beta', COMPETE_EXPLOIT='gamma delta', DISENGAGE='epsilon zeta')
    a1, a2, b = q('cat dog'), q('sun moon'), q('cat dog')
    # Give B and A different remaining strategy texts.
    b.update(INDEPENDENT='red green', COMPETE_EXPLOIT='black white', DISENGAGE='near far')
    result = select_joint(fixed, {'A':[a1,a2], 'B':[b]})
    assert result['A'] == a2 and result['B'] == b
    greedy = {}
    for bank, choices in {'A': [a1, a2], 'B': [b]}.items():
        for candidate in choices:
            if not any(collision(candidate, x) for x in list(fixed.values()) + list(greedy.values())):
                greedy[bank] = candidate
                break
    assert list(greedy) == ['A'] and len(result) == 2
    assert fixed['C']['COOPERATE'] == 'red blue'


def test_cross_bank_threshold():
    assert jaccard_similarity('one two three four five six seven', 'one two three four five six seven eight') > .85
    a = dict.fromkeys(('COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE'), 'one two three four five six seven')
    b = dict.fromkeys(a, 'one two three four five six seven eight')
    assert select_joint({'A':a}, {'B':[b]}) == {}


def test_full_prompt():
    class Recorder:
        def __init__(self): self.seen=[]
        def encode(self, text, add_special_tokens=False):
            self.seen.append((text,add_special_tokens)); return [1]
    t=Recorder(); o=dict.fromkeys(('COOPERATE','INDEPENDENT','COMPETE_EXPLOIT','DISENGAGE'),'Action text.')
    measure(t, ' Stem ', o)
    assert ('Stem\n\nAction: Action text.\nDecision:', False) in t.seen


def test_report_provenance_and_derived_counts():
    import hashlib, json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name, expected in [('pilot',14), ('full_scan',124)]:
        report = json.loads((root/f'reports/controlled_repair_conservative_{name}.json').read_text(encoding='utf8'))
        assert len(report['results']) == expected
        assert report['summary']['new_variants'] == sum(len(r['selected']) for r in report['results'])
        assert report['summary']['new_triads'] == sum(len(r['initial_accepted']) < 3 and len(r['initial_accepted']) + len(r['selected']) == 3 for r in report['results'])
        assert report['summary']['collision_count'] == sum(len(r['final_collisions']) for r in report['results'])
        p = report['provenance']
        assert hashlib.sha256((root/'data/scenarios_phase0b_utility_matched.json').read_bytes().replace(b'\r\n', b'\n')).hexdigest() == p['frozen_source_canonical_sha256'] == 'b460e60657392ded9e781428517b33adfe5bd32d4e7d9ee5b883ac8647bc7bf0'
        overlay=root/'research/controlled_rewrites/production01_repaired/repaired_records.json'
        assert hashlib.sha256(overlay.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == p['overlay_canonical_sha256']
        assert len(json.loads(overlay.read_text(encoding='utf8'))['repaired_records']) == 7
        for path, digest in p['production_files_canonical_sha256'].items():
            assert hashlib.sha256((root/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
        assert not p['scientific_use_allowed'] and not p['paid_inference']


def test_exact_pinned_tokenizer():
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    p = snapshot_download('Qwen/Qwen2.5-1.5B', revision='8faed761d45a263340a0528343f099c05c9a4323', local_files_only=True)
    tok = AutoTokenizer.from_pretrained(p, local_files_only=True)
    assert tok.encode('Secure lockers.', add_special_tokens=False) == [49813, 5296, 388, 13]
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'reports/controlled_repair_quarantine_diagnostics.json').read_text(encoding='utf8'))
    scenarios=json.loads((root/'data/scenarios_phase0b_utility_matched.json').read_text(encoding='utf8'))['scenarios']
    for row in report['pilot']:
        options={s:item['candidate'] for s,item in row['actions'].items()}
        action, prompt=measure(tok,scenarios[int(row['record_id'][:3])]['stem'],options)
        assert action==row['action_tokens'] and prompt==row['prompt_tokens']
        assert max(action.values())-min(action.values()) <= 1
        assert max(prompt.values())-min(prompt.values()) <= 1


def test_quarantined_pilot_and_real_joint_search():
    import json
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/'reports/controlled_repair_quarantine_diagnostics.json'
    d=json.loads(p.read_text(encoding='utf8'))
    pilot={r['record_id']:r for r in d['pilot']}
    assert len(pilot)==13 and all(r['mechanical_token_pass'] for r in pilot.values())
    assert pilot['009_A']['confirmed_fact_violation']
    assert not pilot['013_B']['grammar_screen_pass']
    assert not pilot['013_A']['grammar_screen_pass']
    assert all(r['semantic_status']=='UNADJUDICATED' and r['acceptance_status']=='QUARANTINED' for r in pilot.values())
    outcome=next(r for r in d['pilot_augmented_joint_search'] if r['scenario_index']==12)
    assert all(outcome['pool_sizes'][b]['searched']>1 for b in ('A','B','C'))
    assert set(outcome['joint_selected_quarantined'])=={'A','B','C'}
    assert not outcome['joint_collisions']
    source_row=next(r for r in d['pool_scan'] if r['scenario_index']==12)
    for bank, options in outcome['joint_selected_quarantined'].items():
        for strategy, text in options.items():
            raw=[x['text'] for x in source_row['banks'][bank]['actions'][strategy]]
            assert text in raw or text == pilot[f'012_{bank}']['actions'][strategy]['candidate']
    assert select_joint({}, {b:[v] for b,v in outcome['joint_selected_quarantined'].items()}) == outcome['joint_selected_quarantined']
    assert all(not r['joint_selected_quarantined'] for r in d['pool_scan'])
    funnels=[v['funnel'] for r in d['pool_scan'] for v in r['banks'].values()]
    assert len(funnels)==293 and sum(f['raw_combinations'] for f in funnels)==2889
    assert sum(f['token_span_failed_combinations'] for f in funnels)==2889


def test_quarantine_screen_rejects_known_defects():
    from scripts.diagnose_controlled_repair_quarantine import grammar_flags, fact_findings
    assert grammar_flags('send planned waypoint coordinates.')
    assert grammar_flags('Claim an early docking access.')
    violations, _ = fact_findings('Store models in storage lockers.', 'Store models in claim lockers.', 'DISENGAGE', 'ai')
    assert 'storage_resource_corrupted_claim_lockers' in violations
