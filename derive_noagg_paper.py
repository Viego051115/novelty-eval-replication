"""Author-aligned three k=1 subruns from saved k=3 votes; zero API calls."""
from pathlib import Path
import json
import numpy as np
from scipy.stats import bootstrap
from analyze_existing_results import load, f1, scores, ci_pair, SEED, N
from run_matrix import metrics_pair, metrics_point

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'analysis'
DER=ROOT/'results'/'derived_noagg';DER.mkdir(exist_ok=True)
COMMIT='1db410dc0a57d94e51d57b3e52a03e4f9e0fb578'

def point_ci(base,runs,cls=None):
    y=np.array([r['expected'] for r in base]);a=np.array([r['pred'] for r in base])
    p=[np.array([r['pred'] for r in run]) for run in runs]
    def statistic(y,a,p0,p1,p2,axis=-1):
        return (f1(y,p0,axis,cls)+f1(y,p1,axis,cls)+f1(y,p2,axis,cls))/3-f1(y,a,axis,cls)
    delta=float(statistic(y,a,*p))
    if all(np.array_equal(a,v) for v in p):lo=hi=0.
    else:
        ci=bootstrap((y,a,*p),statistic,paired=True,vectorized=True,n_resamples=N,batch=1000,method='BCa',rng=np.random.default_rng(SEED)).confidence_interval
        lo,hi=map(float,ci)
    return {'difference':delta,'ci_low':lo,'ci_high':hi,'significant_95pct':bool(lo>0 or hi<0)}

def main():
    metrics=[];tests=[];audit=[]
    for setting in ['human-only','human-plus-generated']:
        for kind,variants in [('pair',['ref','P1','P2','P3','P4','P5','plan']),('point',['ref_pw','P1_pw','P2_pw','plan'])]:
            family='p4b' if kind=='pair' else 'p4a'
            reference=f'{family}_{setting}_{"ref" if kind=="pair" else "ref_pw"}'
            base=load(reference)
            for variant in variants:
                source=f'{family}_{setting}_{variant}';rows=load(source)
                assert len(rows)==len(base)
                target=f'{family}_{setting}_noagg' if variant in ('ref','ref_pw') else f'fig11_{setting}_{kind}_{variant}_noagg'
                runs=[];run_metrics=[]
                for k in range(3):
                    run=[]
                    for r in rows:
                        assert len(r['votes'])==(6 if kind=='pair' else 3)
                        votes=[r['votes'][k],r['votes'][k+3]] if kind=='pair' else [r['votes'][k]]
                        if kind=='pair':
                            wins=int(votes[0]==0)+int(votes[1]==1)
                            pred=0 if wins==2 else 1 if wins==0 else None
                        else:pred=votes[0]
                        run.append({'i':r['i'],'pred':pred,'expected':r['expected'],'votes':votes,'failed':False})
                    runs.append(run)
                    run_metrics.append((metrics_pair if kind=='pair' else metrics_point)({r['i']:r['pred'] for r in run},[r['expected'] for r in run]))
                mean={key:float(np.mean([m[key] for m in run_metrics])) for key in run_metrics[0]}
                entry={'config':target,'source_config':source,'kind':kind,'provenance':'derived from existing votes; three k=1 subruns, mean of metrics across subruns','subruns':3,**mean}
                metrics.append(entry)
                (DER/(target+'.json')).write_text(json.dumps({'source_config':source,'target_config':target,'upstream_commit':COMMIT,'runs':runs,'run_metrics':run_metrics,'mean_metrics':entry},indent=2),encoding='utf-8')
                if kind=='pair':
                    for soft in [False,True]:
                        diff=np.mean([scores(run,soft) for run in runs],axis=0)-scores(base,soft)
                        if np.all(diff==diff[0]):lo=hi=float(diff[0])
                        else:
                            ci=bootstrap((diff,),np.mean,vectorized=True,n_resamples=N,batch=1500,method='BCa',rng=np.random.default_rng(SEED)).confidence_interval
                            lo,hi=map(float,ci)
                        tests.append({'config':target,'reference':reference,'metric':'soft' if soft else 'strict','difference':float(np.mean(diff)),'ci_low':lo,'ci_high':hi,'significant_95pct':bool(lo>0 or hi<0),'derived_three_subruns':True})
                else:
                    for cls in [None,0,1]:tests.append({'config':target,'reference':reference,'metric':'macro_f1' if cls is None else f'f1_{cls}','derived_three_subruns':True,**point_ci(base,runs,cls)})
                audit.append({'source':source,'target':target,'source_items':len(rows),'subruns':3,'valid':True})
                print('Derived',target,flush=True)
    assert len(metrics)==22 and len(tests)==52
    result={'method':'For each k=0,1,2 select pointwise vote k or pairwise votes k and k+3; compute three subrun metrics then average. Paired corpus-level BCa resamples items jointly, not subruns. Reference keeps aggregation (paper Fig11).','upstream_source':f'https://github.com/noy-sternlicht/novelty-eval/blob/{COMMIT}/src/novelty_eval/ablation/derive_subrun_artifacts.py','n_resamples':N,'metrics':metrics,'tests':tests,'audit':audit}
    (OUT/'paper_noagg_derivation.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print('Complete: 22 derived conditions, 52 BCa comparisons, zero API calls',flush=True)

if __name__=='__main__':main()
