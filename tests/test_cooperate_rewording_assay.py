from pathlib import Path
from llm_cooperation.cooperate_rewording_assay import BANKS,load_items,paired_presentations

def test_all_banks_paired_and_only_cooperation_differs():
    for bank,(_,count) in BANKS.items():
        scenarios,rewrites,hashes=load_items(Path('data'),bank)
        assert len(scenarios)==count and all(len(v)==64 for v in hashes.values())
        for s in scenarios:
            rows=list(paired_presentations(s,rewrites[s['id']]))
            assert len(rows)==8
            for i in range(0,8,2):
                orig,new=rows[i:i+2]
                assert orig['wording']=='original' and new['wording']=='paraphrase'
                assert orig['letter_to_strategy']==new['letter_to_strategy']
                assert orig['permutation_index']==new['permutation_index']
                assert orig['prompt'].replace(s['options']['COOPERATE'],rewrites[s['id']]['paraphrased_cooperate'],1)==new['prompt']
                assert 'Which action would you choose? Answer with only A, B, C, or D.' in new['prompt']

def test_paired_bootstrap_and_ties():
    from scripts.analyze_cooperate_rewording import analyze
    rows=[]
    for i in range(3):
        for w in ('original','paraphrase'):
            strategy='COOPERATE' if w=='original' else 'INDEPENDENT'
            rows.append({'bank':'phase1','scenario_id':str(i),'template_id':str(i),'permutation_index':0,'wording':w,
                'forced_choice':{'strategy':strategy,'tied_max_count':2 if i==0 else 1},'generated_strategy':strategy})
    report=analyze(rows,bootstrap=100)['phase1']['all']
    assert report['positional_no_ties']['paired_presentations']==2
    assert report['positional_no_ties']['excluded_pairs']==1
    assert report['strict_generated']['paired_presentations']==3
    assert report['strict_generated']['change_paraphrase_minus_original']==-2
