"""Fresh no-aggregation calls for available legacy prompt/format conditions.

These are new calls, never post-hoc first-vote replays. Retrieval/low reasoning
conditions are excluded pending their own matched pipelines and baselines.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse, json, time
import pandas as pd
import finish_fig13 as f
from run_matrix import metrics_pair, metrics_point

ROOT=Path(__file__).resolve().parent
STATUS=ROOT/'results'/'fig11_fresh_status.json'
FIN=ROOT/'private_finance'/'extension_balance_events.jsonl'

def configurations():
    for setting in ['human-only','human-plus-generated']:
        for kind, variants in [('pair',['P1','P2','P3','P4','P5','plan']),('point',['P1_pw','P2_pw','plan'])]:
            for variant in variants:
                data=f'{setting}_{"pairwise" if kind=="pair" else "pointwise"}'+('_plan' if variant=='plan' else '')+'.parquet'
                yield f'fig11_{setting}_{kind}_{variant}_noagg',kind,variant,data

def status(d):
    t=STATUS.with_suffix('.tmp'); t.write_text(json.dumps(d,indent=2),encoding='utf-8')
    for attempt in range(40):
        try:t.replace(STATUS);return
        except PermissionError:
            if attempt==39:raise
            time.sleep(.05)

def money(config,event):
    value=f.balance()
    with FIN.open('a',encoding='utf-8') as p:
        p.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'config':config,'event':event,'balance_cny':value,'basis':'account balance snapshot; not official per-key cost'})+'\n')
    if value<2:
        f.STOP.set()
        raise RuntimeError('Balance reserve reached; saved calls retained')
    return value

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--allow-extra-repeat',action='store_true',help='Optional paid repeat only; author Fig11 uses derive_noagg_paper.py at zero API cost')
    args=ap.parse_args()
    if not args.allow_extra_repeat:ap.error('Fresh repeats are optional. Run python derive_noagg_paper.py for author-aligned no-aggregation results without API costs.')
    if f.RAW.exists():
        for line in f.RAW.read_text(encoding='utf-8').splitlines():
            try:
                r=json.loads(line)
                if 'verdict' in r:f.CACHE[r['key']]=r
            except (ValueError,KeyError): pass
    start=money('fig11_fresh','batch_start'); completed=[]
    print('Fresh Fig11 available conditions; start balance',start,flush=True)
    for config,kind,variant,datafile in configurations():
        data=pd.read_parquet(ROOT/'data'/datafile)
        path=ROOT/'results'/f'deepseek_{config}.jsonl';records={};k=2 if kind=='pair' else 1
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                r=json.loads(line)
                if not r.get('failed') and len(r.get('votes',[]))==k and all(v in (0,1) for v in r['votes']):records[r['i']]=r
        def judge(i):
            row=data.iloc[i]
            if kind=='pair':
                prompt='ref' if variant=='plan' else variant
                a,b=row['idea_a'],row['idea_b']
                votes=[f.call(config,i,0,f.h.PROMPTS[prompt].format(idea0=a,idea1=b)),f.call(config,i,1,f.h.PROMPTS[prompt].format(idea0=b,idea1=a))]
                wins=int(votes[0]==0)+int(votes[1]==1)
                pred=0 if wins==2 else 1 if wins==0 else None
                expected=int(row['expected_winner'])
            else:
                prompt='ref_pw' if variant=='plan' else variant
                votes=[f.call(config,i,0,f.h.PROMPTS[prompt].format(idea=row['idea']))]
                pred=votes[0];expected=int(row['label']=='POSITIVE')
            return {'i':i,'pred':pred,'votes':votes,'expected':expected,'failed':False,'fresh_noagg':True}
        errors=[]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs={pool.submit(judge,i):i for i in range(len(data)) if i not in records}
            for job in as_completed(jobs):
                if job.cancelled():continue
                i=jobs[job]
                try:
                    r=job.result(); records[i]=r
                    with path.open('a',encoding='utf-8') as p:p.write(json.dumps(r)+'\n')
                except Exception as e:
                    errors.append({'i':i,'error':type(e).__name__})
                    print('Item error',i,type(e).__name__,flush=True)
                status({'status':'running','config':config,'complete_items':len(records),'total_items':len(data),'completed_configs':completed,'errors':errors})
                if len(records)%50==0 or len(records)==len(data):
                    money(config,'progress');print(config,len(records),'/',len(data),flush=True)
                if f.STOP.is_set():
                    for pending in jobs:pending.cancel()
        if errors or len(records)!=len(data):
            status({'status':'stopped','config':config,'complete_items':len(records),'completed_configs':completed,'errors':errors})
            raise RuntimeError('Incomplete condition retained for resume')
        metric=(metrics_pair if kind=='pair' else metrics_point)({i:r['pred'] for i,r in records.items()},[int(r['expected_winner']) if kind=='pair' else int(r['label']=='POSITIVE') for _,r in data.iterrows()])
        print(config,json.dumps(metric),flush=True)
        completed.append(config);money(config,'config_complete')
    end=money('fig11_fresh','batch_complete')
    status({'status':'complete','completed_configs':completed,'total_configurations':18,'balance_start_cny':start,'balance_end_cny':end,'balance_decrease_cny':round(start-end,4),'cost_basis':'balance delta, pending official bill'})
    print('COMPLETE 18 fresh configurations; balance decrease',round(start-end,4),flush=True)

if __name__=='__main__':main()
