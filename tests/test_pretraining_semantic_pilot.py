"""Bounded-sample and annotation-metric tests; no network/model calls."""
import json
import random

import pytest

from research.pretraining_counterfactual_v1.pilot import sentences, SAMPLE_SIZE, SEED
from research.pretraining_counterfactual_v1.pilot_analysis import review_metrics, wilson


def test_seeded_source_sample_is_not_prefix_and_has_no_duplicate_indices():
    n=2119719
    selected=random.Random(SEED).sample(range(n),SAMPLE_SIZE)
    assert len(set(selected))==10000
    assert max(selected)>n*.99
    assert min(selected)<n*.01
    assert all(sum(q*n/4<=i<(q+1)*n/4 for i in selected)>2000 for q in range(4))
    assert selected==random.Random(SEED).sample(range(n),SAMPLE_SIZE)


def test_sentence_extraction_offsets_match_source_exactly():
    text='Tim shared. Sue won! But who benefited? No conclusion'
    spans=sentences(text)
    assert len(spans)==4
    for s in spans:
        assert text[s['start']:s['end']]==s['text']


def test_zero_positives_does_not_imply_absence():
    interval=wilson(0,40)
    assert interval['rate']==0
    assert .08<interval['wilson95'][1]<.09
    assert wilson(0,0) is None


def test_independent_success_is_not_competition_precision_and_targeting_not_prevalence():
    reviews=[{'source_index':0,'stratum':'independent_random','labels':['neutral'],'uncertain':False},
             {'source_index':1,'stratum':'high_successful_competition','labels':['independent_success'],'uncertain':False},
             {'source_index':2,'stratum':'high_successful_competition','labels':['competition_rewarded'],'uncertain':False}]
    scores=[{'source_index':i,'coop_present':.1,'cooperation_reward_margin':.01,'competition_success_margin':.3} for i in range(3)]
    metrics=review_metrics(scores,reviews)
    assert metrics['random_prevalence']['competition_rewarded']['n']==1
    assert metrics['random_prevalence']['competition_rewarded']['positive']==0
    assert metrics['top20_competition_precision']['rate']==.5
    assert metrics['top20_competition_precision_including_independent_success']['rate']==1


def test_review_strata_are_disjoint_and_random40_selected_before_scores(tmp_path):
    from research.pretraining_counterfactual_v1.pilot import review_sample
    cache=tmp_path/'cache'; report=tmp_path/'report';cache.mkdir();report.mkdir()
    raw=[]; scores=[]
    for i in range(10000):
        raw.append({'source_index':i,'sha256':str(i),'text':'They shared. Someone won.'})
        scores.append({'source_index':i,'sha256':str(i),'coop_present':i/9999,
                       'competition_success_margin':1-i/9999,
                       'max_probabilities':{'cooperation_success':i/9999,'neutral':1-i/9999}})
    (cache/'sample.jsonl').write_text('\n'.join(json.dumps(x) for x in raw),encoding='utf-8')
    (report/'scores.jsonl').write_text('\n'.join(json.dumps(x) for x in scores),encoding='utf-8')
    review_sample(cache,report)
    result=json.loads((report/'review_selection.json').read_text())
    assert len(result['rows'])==len({r['source_index'] for r in result['rows']})==140
    actual={r['source_index'] for r in result['rows'] if r['stratum']=='independent_random'}
    assert actual==set(random.Random(SEED+1).sample(range(10000),40))
    assert all(sum(r['stratum']==s for r in result['rows'])==20 for s in (
        'high_cooperation','low_cooperation','high_successful_competition','low_successful_competition','ambiguous'))


def test_quality_flags_do_not_claim_semantic_classification():
    from research.pretraining_counterfactual_v1.pilot_tools.quality import flags
    assert flags('No.\nNo.\nNo.\nNo.')['repeated_paragraph_4plus']
    assert flags('A broken quote \ufffd')['replacement_character']
    assert flags('Lila said, No,')['nonterminal_last_character']
    assert not any(flags('They shared and had fun.').values())


def test_frozen_score_restore_never_overwrites_different_capture(tmp_path):
    import gzip
    import hashlib
    from research.pretraining_counterfactual_v1.pilot_tools.restore_scores import restore
    contents=b'{"source_index":7}\n'
    packed=gzip.compress(contents,mtime=0)
    (tmp_path/'scores.jsonl.gz').write_bytes(packed)
    (tmp_path/'artifact_manifest.json').write_text(json.dumps({
        'uncompressed_scores_sha256':hashlib.sha256(contents).hexdigest(),
        'files':{'scores.jsonl.gz':hashlib.sha256(packed).hexdigest()}}))
    restore(tmp_path)
    assert (tmp_path/'scores.jsonl').read_bytes()==contents
    (tmp_path/'scores.jsonl').write_bytes(b'another complete capture')
    with pytest.raises(ValueError,match='preserve'):
        restore(tmp_path)
    assert (tmp_path/'scores.jsonl').read_bytes()==b'another complete capture'
