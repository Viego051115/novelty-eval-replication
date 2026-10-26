"""Preserve and independently audit unnecessary fresh repeats; no API calls."""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
from pathlib import Path
import hashlib,json
import pandas as pd
from programs.experiments.run_fig11_fresh import configurations
from programs.core import harness2 as h

ROOT = PROJECT_ROOT
raw={}
for line in (ROOT/'results'/'fig13_api_responses.jsonl').read_text(encoding='utf-8').splitlines():
    r=json.loads(line)
    if 'verdict' in r:raw[r['key']]=r
audit=[]
for config,kind,variant,datafile in configurations():
    path=ROOT/'results'/f'deepseek_{config}.jsonl'
    if not path.exists():continue
    df=pd.read_parquet(ROOT/'data'/datafile)
    rows={r['i']:r for r in (json.loads(l) for l in path.read_text().splitlines() if l)}
    # Recover only already received, explicitly parsed answers matching the prompt.
    if kind=='point':
        prompt='ref_pw' if variant=='plan' else variant
        for i,row in df.iterrows():
            if i in rows:continue
            r=raw.get(f'{config}:{i}:0')
            sha=hashlib.sha256(h.PROMPTS[prompt].format(idea=row['idea']).encode()).hexdigest()
            if r and r.get('verdict') in (0,1) and r.get('prompt_sha256')==sha:
                saved={'i':int(i),'pred':r['verdict'],'votes':[r['verdict']],'expected':int(row['label']=='POSITIVE'),'failed':False,'fresh_noagg':True,'recovered_from_saved_response':True}
                with path.open('a',encoding='utf-8') as f:f.write(json.dumps(saved)+'\n')
                rows[int(i)]=saved
    errors=[]
    for i,r in rows.items():
        v=r['votes'];expected=int(df.iloc[i]['expected_winner']) if kind=='pair' else int(df.iloc[i]['label']=='POSITIVE')
        if len(v)!=(2 if kind=='pair' else 1) or any(x not in (0,1) for x in v):errors.append(i);continue
        wins=int(v[0]==0)+int(v[1]==1) if kind=='pair' else None
        pred=(0 if wins==2 else 1 if wins==0 else None) if kind=='pair' else v[0]
        if pred!=r['pred'] or expected!=r['expected']:errors.append(i)
    audit.append({'config':config,'unique_items':len(rows),'expected_items':len(df),'complete':len(rows)==len(df) and not errors,'errors':errors,'role':'supplementary fresh repeat; not required by author derivation, not added to condition coverage'})
out={'reason_stopped':'Author code derives k=1 results from saved k=3 responses; fresh repeats are optional. Recovered saved responses only; no new calls.','complete_configurations':sum(r['complete'] for r in audit),'partial_configurations':sum(not r['complete'] for r in audit),'configurations':audit}
(ROOT/'results'/'analysis'/'extra_repeat_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Extra repeat audit:',out['complete_configurations'],'complete,',out['partial_configurations'],'partial')
