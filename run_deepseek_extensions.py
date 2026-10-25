"""Checkpointed paper-aligned supplements; no fixed CNY 10 ceiling, CNY 2 balance reserve."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,time,argparse
from datetime import datetime,timezone
import pandas as pd
import finish_fig13 as f
from run_matrix import metrics_pair

ROOT=Path(__file__).resolve().parent
STATUS=ROOT/'results'/'extension_status.json'
FIN=ROOT/'private_finance'/'extension_balance_events.jsonl'

def save_status(d):
    t=STATUS.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(STATUS)
def check_money(config,event):
    value=f.balance();FIN.parent.mkdir(exist_ok=True)
    with FIN.open('a',encoding='utf-8') as p:p.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'config':config,'event':event,'balance_cny':value,'basis':'account balance snapshot; not official per-key cost'})+'\n')
    if value<2:f.STOP.set();raise RuntimeError('Reserve reached; checkpoints retained')
    return value

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    if f.RAW.exists():
        for line in f.RAW.read_text(encoding='utf-8').splitlines():
            try:
                r=json.loads(line)
                if 'verdict' in r:f.CACHE[r['key']]=r
            except (ValueError,KeyError):pass
    data=pd.read_parquet(ROOT/'data'/'human-only_pairwise_plan.parquet')
    completed=[]
    start=check_money('fig12_human-only','batch_start')
    print('Fig12 Human-Only supplement: start balance',start,'CNY; reserve 2 CNY',flush=True)
    for prompt in ['P3','P4','P5']:
        config=f'fig12_human-only_{prompt}_plan';path=ROOT/'results'/f'deepseek_{config}.jsonl'
        records={}
        if path.exists():
            for l in path.read_text(encoding='utf-8').splitlines():
                try:
                    r=json.loads(l)
                    if not r.get('failed') and len(r.get('votes',[]))==6 and all(v in(0,1) for v in r['votes']):records[r['i']]=r
                except ValueError:pass
        def judge(i):
            row=data.iloc[i];votes=[]
            for k in range(6):
                a,b=(row['idea_a'],row['idea_b']) if k<3 else (row['idea_b'],row['idea_a'])
                votes.append(f.call(config,i,k,f.h.PROMPTS[prompt].format(idea0=a,idea1=b)))
            wins=sum(v==0 for v in votes[:3])+sum(v==1 for v in votes[3:])
            return {'i':i,'pred':0 if wins>3 else 1 if wins<3 else None,'votes':votes,'expected':int(row['expected_winner']),'failed':False}
        errors=[]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            jobs={ex.submit(judge,i):i for i in range(len(data)) if i not in records}
            for job in as_completed(jobs):
                i=jobs[job]
                try:
                    r=job.result();records[i]=r
                    with path.open('a',encoding='utf-8') as p:p.write(json.dumps(r)+'\n')
                except Exception as e:
                    errors.append({'i':i,'error':type(e).__name__});print('Item error',i,type(e).__name__,flush=True)
                save_status({'status':'running','config':config,'complete_items':len(records),'total_items':len(data),'completed_configs':completed,'errors':errors})
                if len(records)%25==0 or len(records)==len(data):
                    check_money(config,'progress');print(config,len(records),'/',len(data),flush=True)
                if f.STOP.is_set():
                    for pending in jobs:pending.cancel()
        if errors or len(records)!=len(data):
            save_status({'status':'stopped','config':config,'complete_items':len(records),'errors':errors,'completed_configs':completed});raise RuntimeError('Incomplete config retained for resume')
        completed.append(config)
        metric=metrics_pair({i:r['pred'] for i,r in records.items()},list(data['expected_winner']))
        print(config,json.dumps(metric),flush=True)
        check_money(config,'config_complete')
    end=check_money('fig12_human-only','batch_complete')
    save_status({'status':'complete','completed_configs':completed,'total_configurations':3})
    print('COMPLETE three supplementary configs; balance delta',round(start-end,4),flush=True)
if __name__=='__main__':main()
