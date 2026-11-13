import importlib.util
import json
from pathlib import Path
import pytest

path=Path(__file__).resolve().parents[1]/'scripts'/'audit_luna_construct_pilot.py'
spec=importlib.util.spec_from_file_location('pilot_audit',path)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_kappa_handles_agreement_and_degenerate_cases():
    assert m.kappa([('a','a'),('b','b')])==1
    assert m.kappa([('a','b'),('b','a')])==-1
    assert m.kappa([('a','a'),('a','a')]) is None

def test_evidence_classification_distinguishes_source_and_exact_match():
    sources={'scenario':'The actor saves ten minutes.','target':'Share the resource.','reference':'Work separately.'}
    assert m.quote_reason({'source':'scenario','quote':'saves ten minutes'},sources)=='exact'
    assert m.quote_reason({'source':'target','quote':'saves ten minutes'},sources)=='wrong_source'
    assert m.quote_reason({'source':'scenario','quote':'SAVES TEN MINUTES'},sources)=='normalization_only'
    assert m.quote_reason({'source':'scenario','quote':'saves five minutes'},sources)=='not_found_verbatim'

def test_cluster_intervals_are_reproducible_and_packet_aware():
    rows=[{'packet':'a','agreement':True}]*4+[{'packet':'b','agreement':False}]*4
    assert m.cluster_interval(rows)==m.cluster_interval(rows)
    assert m.cluster_interval(rows)==[0,1]

def test_never_overwrite_modified_artifact(tmp_path):
    target=tmp_path/'review.json'
    m.safe_write(target,'original\n')
    m.safe_write(target,'original\n')
    with pytest.raises(FileExistsError): m.safe_write(target,'changed\n')
    assert target.read_text()=='original\n'

def test_blind_packets_do_not_include_model_outputs():
    packets=json.loads((m.DEST/'blind_review_packets.json').read_text(encoding='utf-8'))
    text=json.dumps(packets).lower()
    assert len(packets)==10 and all(x not in text for x in ('qwen','luna','agreement','forced_choice','source_bank'))
