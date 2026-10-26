"""Free, paired corpus-level BCa analysis of the agreed experiment subset."""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
from pathlib import Path
import json,warnings
import numpy as np
from scipy.stats import bootstrap
ROOT = PROJECT_ROOT
OUT=ROOT/'results'/'analysis';OUT.mkdir(exist_ok=True)
SEED=261002022;N=100000

def load(name):
    p=ROOT/'results'/('deepseek_'+name+'.jsonl')
    d={r['i']:r for r in (json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip())}
    rows=[d[i] for i in range(len(d))]
    if any(r.get('failed') or any(v not in (0,1) for v in r['votes']) for r in rows):raise ValueError('Invalid votes '+name)
    return rows

def f1(y,p,axis=-1,cls=None):
    def one(c):
        tp=np.sum((y==c)&(p==c),axis=axis);fp=np.sum((y!=c)&(p==c),axis=axis);fn=np.sum((y==c)&(p!=c),axis=axis)
        den=2*tp+fp+fn
        return np.divide(2*tp,den,out=np.zeros_like(den,dtype=float),where=den!=0)
    return (one(0)+one(1))/2 if cls is None else one(cls)

def scores(rows,soft=False):
    return np.array([(.5 if soft else 0) if r['pred'] is None else float(r['pred']==r['expected']) for r in rows])

def ci_pair(base,changed,soft=False):
    delta=scores(changed,soft)-scores(base,soft)
    if np.all(delta==delta[0]):lo=hi=float(delta[0])
    else:
        result=bootstrap((delta,),np.mean,vectorized=True,method='BCa',n_resamples=N,batch=1500,confidence_level=.95,rng=np.random.default_rng(SEED))
        lo,hi=map(float,result.confidence_interval)
    return {'difference':float(delta.mean()),'ci_low':lo,'ci_high':hi,'significant_95pct':bool(lo>0 or hi<0)}

def ci_point(base,changed,cls=None):
    y=np.array([r['expected'] for r in base]);a=np.array([r['pred'] for r in base]);b=np.array([r['pred'] for r in changed])
    if np.any(a==None) or np.any(b==None):raise ValueError('Unparsed point verdict')
    def statistic(y,a,b,axis=-1):return f1(y,b,axis,cls)-f1(y,a,axis,cls)
    diff=float(statistic(y,a,b))
    if np.array_equal(a,b):lo=hi=0.
    else:
        result=bootstrap((y,a,b),statistic,paired=True,vectorized=True,method='BCa',n_resamples=N,batch=1000,confidence_level=.95,rng=np.random.default_rng(SEED))
        lo,hi=map(float,result.confidence_interval)
    return {'difference':diff,'ci_low':lo,'ci_high':hi,'significant_95pct':bool(lo>0 or hi<0)}

def main():
    tests=[];metrics=[];replays=[]
    for setting in ['human-only','human-plus-generated']:
        base=load(f'p4b_{setting}_ref')
        for variant in ['ref','P1','P2','P3','P4','P5','noagg','plan']:
            rows=load(f'p4b_{setting}_{variant}')
            metrics.append({'config':f'p4b_{setting}_{variant}','strict':float(scores(rows).mean()),'soft':float(scores(rows,True).mean()),'tie_rate':float(np.mean([r['pred'] is None for r in rows]))})
            if variant!='ref':
                for soft in [False,True]:
                    tests.append({'config':f'p4b_{setting}_{variant}','reference':f'p4b_{setting}_ref','metric':'soft' if soft else 'strict',**ci_pair(base,rows,soft)})
            if variant!='noagg':
                replay=[]
                for r in rows:
                    v=r['votes'];n=len(v)//2;wins=int(v[0]==0)+int(v[n]==1)
                    replay.append({**r,'pred':0 if wins==2 else 1 if wins==0 else None})
                replays.append({'config':f'p4b_{setting}_{variant}','method':'post-hoc first vote per order; no new calls; not a fresh Fig11 rerun','strict':float(scores(replay).mean()),'soft':float(scores(replay,True).mean())})
        a=load(f'p4b_{setting}_P3');b=load(f'p4b_{setting}_P4')
        disagreement=sum(x['pred']!=y['pred'] for x,y in zip(a,b));opposite=sum(x['pred'] is not None and y['pred'] is not None and x['pred']!=y['pred'] for x,y in zip(a,b))
        for soft in [False,True]:tests.append({'config':f'P4_vs_P3_{setting}','metric':'soft' if soft else 'strict','reference':'P3','aggregate_disagreement':disagreement,'opposite_non_tie':opposite,'n':len(a),**ci_pair(a,b,soft)})
        base=load(f'p4a_{setting}_ref_pw')
        for variant in ['ref_pw','P1_pw','P2_pw','noagg','plan']:
            rows=load(f'p4a_{setting}_{variant}');y=np.array([r['expected'] for r in rows]);p=np.array([r['pred'] for r in rows])
            metrics.append({'config':f'p4a_{setting}_{variant}','macro_f1':float(f1(y,p)),'f1_pos':float(f1(y,p,cls=1)),'f1_neg':float(f1(y,p,cls=0))})
            if variant!='ref_pw':
                for cls in [None,0,1]:tests.append({'config':f'p4a_{setting}_{variant}','reference':f'p4a_{setting}_ref_pw','metric':'macro_f1' if cls is None else f'f1_{cls}',**ci_point(base,rows,cls)})
            if variant!='noagg':
                first=np.array([r['votes'][0] for r in rows])
                replays.append({'config':f'p4a_{setting}_{variant}','method':'post-hoc first vote; no new calls; not a fresh Fig11 rerun','macro_f1':float(f1(y,first)),'f1_pos':float(f1(y,first,cls=1)),'f1_neg':float(f1(y,first,cls=0))})
        for variant in ['P3','P4','P5']:
            name=f'fig12_{setting}_{variant}_plan'
            if not (ROOT/'results'/('deepseek_'+name+'.jsonl')).exists():continue
            rows=load(name);base=load(f'p4b_{setting}_ref')
            if len(rows)!=len(base):continue
            for soft in [False,True]:tests.append({'config':name,'reference':f'p4b_{setting}_ref','metric':'soft' if soft else 'strict',**ci_pair(base,rows,soft)})
        (OUT/'bootstrap_progress.json').write_text(json.dumps({'last_setting':setting,'tests':len(tests)}),encoding='utf-8')
        print('Completed statistics for '+setting,flush=True)

    fresh=ROOT/'results'/'fig11_fresh_status.json'
    if fresh.exists() and json.loads(fresh.read_text(encoding='utf-8')).get('status')=='complete':
        from programs.experiments.run_fig11_fresh import configurations
        for name,kind,variant,_ in configurations():
            rows=load(name)
            # Appendix C.2: Fig11 reference still aggregates, as in Fig4.
            reference=f'p4b_{name.split("fig11_",1)[1].split("_pair_",1)[0]}_ref' if kind=='pair' else f'p4a_{name.split("fig11_",1)[1].split("_point_",1)[0]}_ref_pw'
            base=load(reference)
            if kind=='pair':
                metrics.append({'config':name,'strict':float(scores(rows).mean()),'soft':float(scores(rows,True).mean()),'tie_rate':float(np.mean([r['pred'] is None for r in rows]))})
                for soft in [False,True]:tests.append({'config':name,'reference':reference,'metric':'soft' if soft else 'strict','fresh_noagg':True,**ci_pair(base,rows,soft)})
            else:
                y=np.array([r['expected'] for r in rows]);p=np.array([r['pred'] for r in rows])
                metrics.append({'config':name,'macro_f1':float(f1(y,p)),'f1_pos':float(f1(y,p,cls=1)),'f1_neg':float(f1(y,p,cls=0))})
                for cls in [None,0,1]:tests.append({'config':name,'reference':reference,'metric':'macro_f1' if cls is None else f'f1_{cls}','fresh_noagg':True,**ci_point(base,rows,cls)})
        print('Completed fresh Fig11 statistics against aggregated Fig4 reference',flush=True)
    result={'method':'two-sided inference via paired corpus-level BCa 95% CI, excludes zero for significance; no multiple-testing correction (paper protocol)','n_resamples':N,'seed':SEED,'metrics':metrics,'tests':tests,'no_aggregation_replay':replays,'scope':'Only existing validated configurations; replay is separately labelled and is not fresh Fig11 calls.'}
    (OUT/'paired_bootstrap_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Saved '+str(len(tests))+' BCa comparisons; zero API calls',flush=True)

if __name__ == '__main__':
    main()
