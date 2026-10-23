"""Resume only the generator-source experiments; checkpoint every API response."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import pathlib
import re
import threading
import time
import urllib.request
import urllib.error

import pandas as pd
import harness2 as h
from run_matrix import metrics_pair, metrics_point

ROOT = pathlib.Path(__file__).resolve().parent
LOCK = threading.Lock()
STOP = threading.Event()
RAW = ROOT / 'results' / 'fig13_api_responses.jsonl'
STATE = ROOT / 'results' / 'fig13_resume_status.json'
CACHE = {}
START = None
MAX_SPEND = 10.0

def dump(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def balance():
    req = urllib.request.Request('https://api.deepseek.com/user/balance',
        headers={'Authorization': 'Bearer ' + h.PROVIDERS['deepseek']['key']})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    return float(next(x['total_balance'] for x in data['balance_infos'] if x['currency']=='CNY'))

def parse(content):
    found = re.findall(r'''["']novelty["']\s*:\s*([01])\b''', content)
    if not found:
        raise ValueError('No explicit novelty verdict in final content')
    return int(found[-1])

def call(config, i, vote, prompt):
    key = f'{config}:{i}:{vote}'
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    if key in CACHE and CACHE[key].get('prompt_sha256') == digest:
        return CACHE[key]['verdict']
    cfg = h.PROVIDERS['deepseek']
    req = urllib.request.Request(cfg['base_url'],
        data=json.dumps({'model':cfg['model'], 'messages':[{'role':'user','content':prompt}], 'max_tokens':8192}).encode(),
        headers={'Authorization':'Bearer '+cfg['key'], 'Content-Type':'application/json'})
    for attempt in range(5):
        if STOP.is_set():
            raise RuntimeError('Budget or fatal-error stop')
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.load(response)
            choice = data['choices'][0]
            content = choice['message'].get('content') or ''
            record = {'key':key, 'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                'prompt_sha256':digest, 'model':data.get('model'), 'usage':data.get('usage'),
                'finish_reason':choice.get('finish_reason'), 'content':content}
            try:
                if choice.get('finish_reason') == 'length':
                    raise ValueError('Truncated output')
                record['verdict'] = parse(content)
            except ValueError as e:
                record['error'] = str(e)
            with LOCK:
                with RAW.open('a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False)+'\n')
                if 'verdict' in record:
                    CACHE[key] = record
            if 'verdict' not in record:
                raise ValueError(record['error'])
            return record['verdict']
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (400,401,402,403,404):
                STOP.set()
                raise RuntimeError(f'Fatal API HTTP {code}') from None
            if code != 429 and code < 500:
                raise
        except ValueError:
            if attempt == 4:
                raise
        except Exception:
            if attempt == 4:
                raise
        time.sleep(min(30, 3 * 2**attempt))
    raise RuntimeError('Retries exhausted')

def judge(config, kind, i, row):
    votes = []
    if kind == 'point':
        prompt = h.PROMPTS['ref_pw'].format(idea=row['idea'])
        votes = [call(config,i,k,prompt) for k in range(3)]
        pred = int(sum(votes)>1)
        expected = int(row['label']=='POSITIVE')
    else:
        for k in range(6):
            a,b = (row['idea_a'],row['idea_b']) if k<3 else (row['idea_b'],row['idea_a'])
            votes.append(call(config,i,k,h.PROMPTS['ref'].format(idea0=a,idea1=b)))
        wins = sum(v==0 for v in votes[:3])+sum(v==1 for v in votes[3:])
        pred = 0 if wins>3 else 1 if wins<3 else None
        expected = int(row['expected_winner'])
    return {'i':i,'pred':pred,'votes':votes,'expected':expected,'failed':False}

def main():
    global START
    START = balance()
    print(f'Start balance CNY {START:.2f}; additional spending ceiling {MAX_SPEND:.2f}',flush=True)
    if RAW.exists():
        for line in RAW.read_text(encoding='utf-8').splitlines():
            try:
                r=json.loads(line)
                if 'verdict' in r: CACHE[r['key']]=r
            except (ValueError,KeyError): pass
    summary=[]
    for g in ['gpt-5','gpt-5.1','gpt-5.4','opus-4-5']:
        for kind in ['pair','point']:
            config=f'fig13_{g}_{kind}'
            path=ROOT/'results'/f'deepseek_{config}.jsonl'
            data=ROOT/'data'/f'human-plus-generated_{"pairwise" if kind=="pair" else "pointwise"}_backbone-{g}.parquet'
            df=pd.read_parquet(data)
            existing={}
            if path.exists():
                for line in path.read_text(encoding='utf-8').splitlines():
                    try:
                        r=json.loads(line); i=r['i']; v=r.get('votes',[])
                        exp=int(df.iloc[i]['expected_winner']) if kind=='pair' else int(df.iloc[i]['label']=='POSITIVE')
                        if not r.get('failed') and len(v)==(6 if kind=='pair' else 3) and all(x in (0,1) for x in v) and r['expected']==exp:
                            existing[i]=r
                    except (ValueError,KeyError,IndexError): pass
            missing=[i for i in range(len(df)) if i not in existing]
            print(f'{config}: reuse {len(existing)}/{len(df)}; pending {len(missing)}',flush=True)
            failures=[]
            with cf.ThreadPoolExecutor(max_workers=4) as ex:
                pending={ex.submit(judge,config,kind,i,df.iloc[i]):i for i in missing}
                for fut in cf.as_completed(pending):
                    i=pending[fut]
                    try:
                        r=fut.result(); existing[i]=r
                        with path.open('a',encoding='utf-8') as f: f.write(json.dumps(r)+'\n')
                    except Exception as e:
                        failures.append({'i':i,'error':str(e)[:160]})
                        print(f'  item {i} failed: {type(e).__name__}',flush=True)
                    if len(existing)%25==0 or len(existing)==len(df):
                        current=balance()
                        dump(STATE,{'config':config,'complete_items':len(existing),'total_items':len(df),'start_balance':START,'current_balance':current,'spend':START-current,'failures':failures})
                        print(f'  {len(existing)}/{len(df)} balance {current:.2f} spend {START-current:.2f}',flush=True)
                        if START-current>=MAX_SPEND or current<2: STOP.set()
                    if STOP.is_set():
                        for p in pending: p.cancel()
            if STOP.is_set() or failures:
                dump(STATE,{'status':'stopped','config':config,'complete_items':len(existing),'failures':failures,'balance':balance()})
                raise RuntimeError('Stopped safely; checkpoints retained')
            preds={i:r['pred'] for i,r in existing.items()}
            metric=metrics_pair(preds,list(df['expected_winner'])) if kind=='pair' else metrics_point(preds,[int(x=='POSITIVE') for x in df['label']])
            summary.append({'config':config,**metric})
            dump(ROOT/'results'/'fig13_completed_summary.json',summary)
            print(json.dumps(summary[-1]),flush=True)
    final=balance()
    dump(STATE,{'status':'complete','configurations':8,'start_balance':START,'end_balance':final,'spend':START-final})
    print('COMPLETE '+json.dumps({'end_balance':final,'spend':START-final}),flush=True)

if __name__=='__main__':
    main()
