import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1] / 'research/lexical_strategy_bridge_v1/prepare.py'
spec = importlib.util.spec_from_file_location('bridge_prepare', PATH)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

def test_prepared_inventory_preserves_mapping_and_context():
    raw, canonical, entries = bridge.prepare()
    assert len(entries) == 2000
    assert bridge.digest(canonical) == '748be08068f5631242c1468df94068cfa6fbd8f8140f9fbaf1cc0fd93fee0116'
    assert len({(e['id'],e['language'],e['condition']) for e in entries}) == 2000
    for e in entries:
        a,b=e['lexical_chars']
        assert e['text'][a:b] == e['word']
        assert e['condition'] != 'neutral' or e['text'] == '[ ' + e['word'] + ' ]'

def test_source_identity_mismatch_fails(tmp_path, monkeypatch):
    (tmp_path/'lexicon.json').write_text('[]',encoding='utf-8')
    (tmp_path/'frozen_manifest.json').write_text('{"file_hashes":{"lexicon.json":"wrong"}}',encoding='utf-8')
    monkeypatch.setattr(bridge,'CORPUS',tmp_path)
    with pytest.raises(ValueError,match='frozen'):
        bridge.prepare()
