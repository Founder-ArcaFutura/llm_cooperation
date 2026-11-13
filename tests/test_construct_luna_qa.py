import importlib.util
import json
from pathlib import Path

import pytest

path=Path(__file__).resolve().parents[1]/'scripts'/'construct_luna_qa.py'
spec=importlib.util.spec_from_file_location('construct_luna_qa',path)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_prepare_blinds_and_separates_samples(tmp_path):
    out=tmp_path/'batch'
    m.prepare(out,20261112,3,6,'low')
    manifest=m.read(out/'manifest.json')
    dev=set(manifest['cohorts']['development']['packets']); held=set(manifest['cohorts']['heldout']['packets'])
    assert len(dev)==3 and len(held)==6 and not dev & held
    prior=m.read(m.LEDGER)
    known=set(prior['scope']['previously_reviewed_packet_ids'])|{x['packet_id'] for x in prior['new_diagnostic_sample']}|{'RV-760143'}
    assert not held & known
    requests=[json.loads(x) for x in (out/'development.jsonl').read_text(encoding='utf-8').splitlines()]
    mapping=m.read(out/'development_mapping.json')
    assert len(requests)==3*2*2*len(m.FIELDS)==len(mapping)
    assert len({x['custom_id'] for x in requests})==len(requests)
    for request in requests:
        prompt=json.dumps(request['body']['input']).lower()
        assert 'qwen_label' not in prompt and 'behavioral results' not in prompt
        assert request['body']['model']==m.MODEL and request['url']=='/v1/responses'
    with pytest.raises(FileExistsError): m.prepare(out,20261112,3,6,'low')

def test_import_detects_missing_and_unverified_evidence(tmp_path):
    out=tmp_path/'batch'; m.prepare(out,1,1,0,'low')
    mapping=m.read(out/'development_mapping.json'); cid=next(iter(mapping))
    field=mapping[cid]['field']; answer={'answers':[m.FIELDS[field][1][0]],'evidence':[{'source':'scenario','quote':'not a real quotation'}],'explanation':'test'}
    body={'status':'completed','usage':{'input_tokens':10,'output_tokens':20},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(answer)}]}]}
    result={'custom_id':cid,'response':{'status_code':200,'body':body},'error':None}
    output=tmp_path/'out.jsonl'; output.write_text(json.dumps(result)+'\n',encoding='utf-8')
    m.import_results(out,'development',output)
    report=m.read(out/'development_qa_results.json')
    assert report['summary']['missing']==len(mapping)-1
    assert report['results'][0]['status']=='review_needed'
    assert report['results'][0]['invalid_evidence']
