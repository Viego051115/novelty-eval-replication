"""Resumable domestic-provider subset. Never interpret missing votes as ties."""
import argparse, hashlib, json, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from programs.paths import PROJECT_ROOT as ROOT
from programs.core.harness2 import ENV, PROMPTS
from programs.experiments.run_matrix import metrics_pair, metrics_point
CONFIGS = {
 'qwen': ('https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', 'qwen-plus', 'DASHSCOPE_API_KEY', {'enable_thinking':False}),
 'glm': ('https://open.bigmodel.cn/api/paas/v4/chat/completions','glm-4.7-flash','GLM_API_KEY',{'thinking':{'type':'disabled'}}),
}
def now(): return datetime.now(timezone.utc).isoformat()
def append(path, rec):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')
def records(path):
 if path.exists():
  for line in path.read_text(encoding='utf-8').splitlines():
   try: yield json.loads(line)
   except ValueError: pass

def main():
 import re
 p=argparse.ArgumentParser(); p.add_argument('--provider',choices=CONFIGS,required=True);p.add_argument('--max-calls',type=int,default=25000);p.add_argument('--limit',type=int,default=0);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 url,model,key,options=CONFIGS[a.provider]
 folder=ROOT/'results'/'domestic_subset'/a.provider;folder.mkdir(parents=True,exist_ok=True)
 journal=folder/'api_responses.jsonl'; finance=ROOT/'private_finance'/'domestic_api_usage.jsonl'
 manifest=[]
 # Baselines first, then ablations. Full dataset for each condition.
 for variant in ['ref','P1','P2','P3','P4','P5','plan']:
  for setting in ['human-only','human-plus-generated']:
   manifest.append(dict(id=f'p4b_{setting}_{variant}',setting=setting,protocol='pairwise',variant=variant,prompt='ref' if variant=='plan' else variant))
 for variant in ['ref_pw','P1_pw','P2_pw']:
  for setting in ['human-only','human-plus-generated']:
   manifest.append(dict(id=f'p4a_{setting}_{variant}',setting=setting,protocol='pointwise',variant=variant,prompt=variant))
 # Interleave four baselines before prompt variants.
 manifest.sort(key=lambda c:(0 if c['variant'] in ['ref','ref_pw'] else 1, c['protocol'],c['id']))
 meta=dict(created_utc=now(),provider=a.provider,model=model,options=options,max_tokens=8192,temperature='omitted; provider default',conditions=manifest,scope='20 of 40 previously run DeepSeek source conditions; not 50% of the paper',limitations=['Provider thinking disabled explicitly; historical DeepSeek thinking default unverified. Not a high-reasoning reproduction.','Existing Human+Generated data retain original foreign-generator provenance; domestic judge extension only.'],sources=['https://help.aliyun.com/zh/model-studio/get-api-key/','https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash'])
 (folder/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 if a.dry_run: print(json.dumps({'provider':a.provider,'conditions':len(manifest)}));return
 cache={r['fingerprint']:r for r in records(journal) if r.get('verdict') in [0,1] and r.get('finish_reason')!='length'}
 calls=0
 def vote(prompt, condition, i, v):
  nonlocal calls
  body={'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':8192,**options}
  fingerprint=hashlib.sha256(json.dumps({'url':url,'body':body,'condition':condition,'i':i,'vote':v},sort_keys=True).encode()).hexdigest()
  if fingerprint in cache: return cache[fingerprint]['verdict']
  for attempt in range(7):
   if calls>=a.max_calls: raise RuntimeError('Invocation request cap reached; resume safely.')
   calls+=1;start=now();rec=dict(fingerprint=fingerprint,condition=condition,i=i,vote=v,started_utc=start,provider=a.provider,requested_model=model,options=options)
   try:
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+ENV[key],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=240) as response: d=json.load(response)
    choice=d['choices'][0];content=choice['message'].get('content') or ''; matches=re.findall(r'[\"\x27]novelty[\"\x27]\s*:\s*([01])\b',content)
    valid=bool(matches) and choice.get('finish_reason')!='length'
    rec.update(ended_utc=now(),response_id=d.get('id'),returned_model=d.get('model'),usage=d.get('usage'),finish_reason=choice.get('finish_reason'),content=content,reasoning_content=choice['message'].get('reasoning_content'),verdict=int(matches[-1]) if valid else None)
    append(journal,rec);append(finance,{k:val for k,val in rec.items() if k not in ['content','reasoning_content']})
    if valid:cache[fingerprint]=rec;return rec['verdict']
   except urllib.error.HTTPError as e:
    raw=e.read();err=raw.decode('utf-8',errors='replace');rec.update(ended_utc=now(),http_status=e.code,error=err);append(journal,rec)
    print(json.dumps({'provider':a.provider,'http':e.code,'attempt':attempt+1,'error':err},ensure_ascii=True),flush=True)
    if e.code in [400,401,402,403,404]:raise RuntimeError(f'Provider blocked: HTTP {e.code}')
   except (TimeoutError, OSError) as e:
    rec.update(ended_utc=now(),error=type(e).__name__);append(journal,rec)
   time.sleep(min(10*(attempt+1),50))
  raise RuntimeError('Seven attempts unsuccessful; stopped without fabricating a verdict.')
 summary=[]
 try:
  for c in manifest:
   suffix='_plan' if c['variant']=='plan' else ''
   data=ROOT/'data'/f"{c['setting']}_{c['protocol']}{suffix}.parquet"; rows=pd.read_parquet(data).to_dict('records')
   out=folder/(c['id']+'.jsonl');done={r['i']:r for r in records(out) if not r.get('failed')}
   for i,row in enumerate(rows):
    if i in done:continue
    if a.limit and i>=a.limit:break
    pair=c['protocol']=='pairwise';votes=[]
    for v in range(6 if pair else 3):
     if pair:
      aa,bb=(row['idea_a'],row['idea_b']) if v<3 else (row['idea_b'],row['idea_a'])
      prompt=PROMPTS[c['prompt']].format(idea0=aa,idea1=bb)
     else:prompt=PROMPTS[c['prompt']].format(idea=row['idea'])
     votes.append(vote(prompt,c['id'],i,v))
    if pair:
     wins=sum(x==0 for x in votes[:3])+sum(x==1 for x in votes[3:]);pred=0 if wins>3 else 1 if wins<3 else None;expected=int(row['expected_winner'])
    else: pred=int(sum(votes)>=2);expected=int(row['label']=='POSITIVE')
    rec={'i':i,'pred':pred,'votes':votes,'expected':expected,'failed':False};append(out,rec);done[i]=rec
    if len(done)%10==0:print(c['id'],len(done),'/',len(rows),flush=True)
   if len(done)==len(rows):
    truth=[int(r['expected_winner']) if c['protocol']=='pairwise' else int(r['label']=='POSITIVE') for r in rows]
    metric=(metrics_pair if c['protocol']=='pairwise' else metrics_point)({i:r['pred'] for i,r in done.items()},truth)
    summary.append({'condition':c['id'],'metrics':metric});print(json.dumps(summary[-1]),flush=True)
   (folder/'status.json').write_text(json.dumps({'updated_utc':now(),'state':'running','completed_conditions':len(summary),'target_conditions':20,'last_condition':c['id'],'last_items':len(done),'last_target':len(rows),'metrics':summary},indent=2),encoding='utf-8')
 except Exception as e:
  (folder/'status.json').write_text(json.dumps({'updated_utc':now(),'state':'stopped','reason':str(e),'completed_conditions':len(summary),'target_conditions':20,'metrics':summary},indent=2),encoding='utf-8');raise
 (folder/'status.json').write_text(json.dumps({'updated_utc':now(),'state':'completed' if not a.limit else 'pilot_completed','completed_conditions':len(summary),'target_conditions':20,'metrics':summary},indent=2),encoding='utf-8')
if __name__=='__main__':main()
