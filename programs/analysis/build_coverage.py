"""Configuration accounting for one-judge adaptation, not overall paper completion."""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
from pathlib import Path
import json

ROOT = PROJECT_ROOT
OUT=ROOT/'results'/'analysis';OUT.mkdir(exist_ok=True)
aud=json.loads((ROOT/'results'/'configuration_audit.json').read_text(encoding='utf-8'))
valid={x['config'] for x in aud['configurations'] if x['complete_and_valid']}
derived_file=OUT/'paper_noagg_derivation.json'
derived={r['config'] for r in json.loads(derived_file.read_text())['metrics']} if derived_file.exists() else set()
rows=[]
def add(name,figure,required=True):
    rows.append({'config':name,'figure':figure,'paper_listed_source':required,'status':'derived_from_validated_votes' if name in derived else 'validated' if name in valid else 'not_yet_validated'})
for s in ['human-only','human-plus-generated']:
    for v in ['ref','P1','P2','P3','P4','P5','retrieval','low','noagg','plan']:add(f'p4b_{s}_{v}','4b')
    for v in ['ref_pw','P1_pw','P2_pw','retrieval','low','noagg','plan']:add(f'p4a_{s}_{v}','4a')
    for kind,variants in [('pair',['P1','P2','P3','P4','P5','retrieval','low','plan']),('point',['P1_pw','P2_pw','retrieval','low','plan'])]:
        for v in variants:add(f'fig11_{s}_{kind}_{v}_noagg','11')
    for v in ['P3','P4','P5']:add(f'fig12_{s}_{v}_plan','12')
    for evaluator in ['idea_novelty_checker','ai_scientist']:add(f'dedicated_{s}_{evaluator}','6/7')
    add(f'strong_rag_{s}_point','5')
for g in ['opus-4-5','gpt-5.1','gpt-5.4']:
    for kind in ['pair','point']:
        add(f'fig13_{g}_{kind}','13')
        add(f'fig14_{g}_{kind}_retrieval','14')
for kind in ['pair','point']:add(f'fig13_gpt-5_{kind}','extra',False)
assert len(rows)==86
result={'scope':'One DeepSeek judge; configuration count only, excluding dataset reconstruction and expert audit. Fig8/9/10 are derived metrics. Extra GPT-5 source is not part of paper source comparison. Fig11 derives three k=1 subruns from each source as in upstream code; no fresh calls required.','completed':sum(r['status']!='not_yet_validated' for r in rows),'actual_run_configurations':len(valid),'derived_conditions':len(derived),'total_including_two_extras':86,'paper_listed_target':84,'additional_calibration_runs_needed':4,'calibration_note':'Four explicit high-effort references are needed before interpreting four new low-effort conditions. Legacy default effort is unverified. Completion counts do not certify protocol fidelity.','configurations':rows}
(OUT/'experiment_coverage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Configuration accounting:',result['completed'],'/86 incl. 2 extra source conditions; 4 calibration runs not counted')
