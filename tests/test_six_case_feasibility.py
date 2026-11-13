import copy
import importlib.util
from collections import Counter
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'research'/'scenario_reconstruction_feasibility'/'instrument.py'
spec=importlib.util.spec_from_file_location('feasibility_instrument',path)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_render_count_and_rotations():
    bank=m.load_bank(); errors,warnings=m.audit(bank); assert not errors and warnings
    rows=m.render(bank); assert len(rows)==160
    assert Counter(x['perspective'] for x in rows)=={'actor':96,'recipient':64}
    for c in bank['cases']:
        sub=[r for r in rows if r['case']==c['id']]
        assert len(sub)==(32 if c['paired'] else 16)
        for perspective in {r['perspective'] for r in sub}:
            for identity in ('human','ai'):
                for variant in (0,1):
                    group=[r for r in sub if r['perspective']==perspective and r['other_identity']==identity and r['wording']==variant]
                    assert len(group)==4
                    assert {r['letter_to_strategy']['A'] for r in group}==set(m.LABELS)
                    assert len({tuple(r['letter_to_strategy'].values()) for r in group})==4

def test_audit_detects_source_and_authority_errors():
    bank=copy.deepcopy(m.load_bank()); bank['cases'][0]['source_sha256']='bad'; bank['cases'][1]['decision_authority']=''
    errors,_=m.audit(bank)
    assert any('hash mismatch' in e for e in errors)
    assert any('missing decision authority' in e for e in errors)

def test_source_hash_accepts_only_line_ending_change(tmp_path):
    import hashlib
    bank=copy.deepcopy(m.load_bank())
    case=bank['cases'][0]
    raw=Path(case['source_file']).read_bytes().replace(b'\r\n',b'\n')
    source=tmp_path/'source.json'
    source.write_bytes(raw)
    case['source_file']=str(source)
    case['source_sha256']=hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()
    errors,warnings=m.audit(bank)
    assert not errors
    assert any('line endings' in w for w in warnings)
    source.write_bytes(raw+b' ')
    errors,_=m.audit(bank)
    assert any('hash mismatch' in e for e in errors)

def test_audit_warns_about_beneficiary_and_role_transfer():
    bank=copy.deepcopy(m.load_bank()); bank['cases'][0]['actions'][0][0]='The counterpart takes a benefit and helps the partner.'
    _,warnings=m.audit(bank)
    assert any('transferred to counterpart' in w for w in warnings)
    assert any('explicit beneficiary' in w for w in warnings)

def test_excluded_recipient_cases_not_rendered():
    rows=m.render(m.load_bank())
    assert not any(r['perspective']=='recipient' and r['case'] in ('museum','milk') for r in rows)

def test_remote_module_import_does_not_require_local_instrument(tmp_path):
    import subprocess
    import sys
    launcher=path.parents[2]/'modal_six_case_feasibility.py'
    isolated=tmp_path/launcher.name
    isolated.write_bytes(launcher.read_bytes())
    subprocess.run([sys.executable, '-I', '-c',
                    'import runpy, sys; runpy.run_path(sys.argv[1], run_name="remote_import")',
                    str(isolated)], check=True, cwd=tmp_path)

def test_answer_boundary_uses_space_and_rejects_retokenization():
    import runpy
    import pytest
    launcher=runpy.run_path(str(path.parents[2]/'modal_six_case_feasibility.py'))
    class Tokenizer:
        def encode(self, text, add_special_tokens=False):
            if text == 'Answer:': return [1, 2]
            if text.startswith('Answer: ') and text[-1] in 'ABCD':
                return [1, 2, 10+'ABCD'.index(text[-1])]
            return [1, 99]
    ids, candidates=launcher['candidate_tokens'](Tokenizer(), 'Answer:')
    assert ids == [1, 2] and candidates == dict(zip('ABCD', range(10, 14)))
    class BadTokenizer(Tokenizer):
        def encode(self, text, add_special_tokens=False):
            if text == 'Answer: A': return [1, 99]
            return super().encode(text, add_special_tokens)
    with pytest.raises(ValueError, match='Unstable answer boundary'):
        launcher['candidate_tokens'](BadTokenizer(), 'Answer:')

def test_local_launcher_dry_run_writes_verifiable_manifest(tmp_path, monkeypatch):
    import hashlib
    import json
    import sys
    sys.path.insert(0, str(path.parent))
    launcher_path=path.parents[2]/'modal_six_case_feasibility.py'
    launcher_spec=importlib.util.spec_from_file_location('test_feasibility_launcher',launcher_path)
    launcher=importlib.util.module_from_spec(launcher_spec)
    launcher_spec.loader.exec_module(launcher)
    # The temporary launcher root needs the same bank bytes for its fingerprint.
    bank_dir=tmp_path/'research'/'scenario_reconstruction_feasibility'
    bank_dir.mkdir(parents=True)
    (bank_dir/'sample_bank.json').write_bytes((path.parent/'sample_bank.json').read_bytes())
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    launcher.run_local('test',True)
    out=bank_dir/'runs'/'test'
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['presentation_count']==160 and manifest['mode']=='dry-run'
    assert manifest['prompt_sha256']==hashlib.sha256((out/'prompts.jsonl').read_bytes()).hexdigest()
    assert not (out/'results.json').exists()
