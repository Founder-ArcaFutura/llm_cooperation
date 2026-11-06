import itertools

from llm_cooperation.items.controlled_repair_engine import (
    variants, valid_rewrite, select_joint, jaccard_similarity, measure,
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
