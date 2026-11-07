import hashlib
import json

import pytest

from llm_cooperation.mechanistic.delayed_mapping import prepare, read_plan
from llm_cooperation.mechanistic.plan_transport import pack_plan, unpack_plan


@pytest.mark.parametrize('ending', [b'\n', b'\r\n'])
def test_plan_bytes_survive_windows_linux_transport(tmp_path, ending):
    source = tmp_path / 'source'
    prepare(source, smoke=True)
    # Explicit newline bytes simulate either OS independently of the test host.
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    for name, key in [('bank.json', 'bank_sha256'), ('presentations.jsonl', 'presentations_sha256')]:
        content = (source / name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', ending)
        (source / name).write_bytes(content)
        manifest[key] = hashlib.sha256(content).hexdigest()
    (source / 'manifest.json').write_bytes(json.dumps(manifest).encode())
    read_plan(source)
    payload = pack_plan(source)
    target = unpack_plan(tmp_path / 'remote', payload)
    read_plan(target)
    assert all((target / name).read_bytes() == (source / name).read_bytes() for name in payload)
    if ending == b'\r\n':
        # This reproduces the old read_text()/write_text() Linux transfer failure.
        old_target = tmp_path / 'old-transport'
        old_target.mkdir()
        for name in payload:
            text = (source / name).read_text(encoding='utf-8')
            (old_target / name).write_bytes(text.encode('utf-8'))
        with pytest.raises(ValueError, match='bank hash mismatch'):
            read_plan(old_target)


def test_invalid_transport_rejected_without_creating_directory(tmp_path):
    target = tmp_path / 'bad'
    with pytest.raises(ValueError, match='binary plan'):
        unpack_plan(target, {'../bank.json': b'{}'})
    assert not target.exists()


def test_tampering_still_rejected(tmp_path):
    source = tmp_path / 'source'
    prepare(source, smoke=True)
    payload = pack_plan(source)
    payload['bank.json'] += b' '
    with pytest.raises(ValueError, match='bank hash mismatch'):
        unpack_plan(tmp_path / 'remote', payload)
