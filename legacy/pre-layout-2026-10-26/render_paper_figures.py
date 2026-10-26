"""Paper-organized figures; missing experiments remain visibly marked."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'analysis'
M={r['config']:r for r in json.loads((ROOT/'results'/'all_configurations_summary.json').read_text())}
B=json.loads((OUT/'paired_bootstrap_results.json').read_text())
T={(r['config'],r['metric']):r for r in B['tests']}
derived=OUT/'paper_noagg_derivation.json'
if derived.exists():
    D=json.loads(derived.read_text(encoding='utf-8'))
    M.update({r['config']:r for r in D['metrics']})
    T.update({(r['config'],r['metric']):r for r in D['tests']})
settings=['human-only','human-plus-generated'];labels=['Human-Only','Human+Generated']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
norm=TwoSlopeNorm(vmin=-40,vcenter=0,vmax=40)
cmap=plt.get_cmap('RdBu').copy();cmap.set_bad('#eeeeee')

def matrix(ax,kind,metric,variants,fresh=False):
    values=np.full((len(variants),2),np.nan);texts={}
    for j,s in enumerate(settings):
        ref=f'{kind}_{s}_{"ref" if kind=="p4b" else "ref_pw"}'
        baseline=M[ref][metric]
        for i,v in enumerate(variants):
            name=f'{kind}_{s}_{v}'
            if fresh and v not in ('ref','ref_pw','noagg'):
                name=f'fig11_{s}_{"pair" if kind=="p4b" else "point"}_{v}_noagg'
            if name not in M:continue
            value=M[name][metric];delta=100*(value-baseline);values[i,j]=delta
            test_metric={'f1_pos':'f1_1','f1_neg':'f1_0'}.get(metric,metric)
            star='*' if T.get((name,test_metric),{}).get('significant_95pct') else ''
            texts[(i,j)]=f'{delta:+.1f}{star}\n({100*value:.1f})' if name!=ref else f'{100*value:.1f}\nreference'
    im=ax.imshow(values,cmap=cmap,norm=norm,aspect='auto')
    for i in range(len(variants)):
        for j in range(2):
            txt=texts.get((i,j),'not run')
            color='white' if abs(values[i,j])>27 else '#172738'
            ax.text(j,i,txt,ha='center',va='center',fontsize=9,color=color)
    ax.set_xticks([0,1],labels,fontsize=8)
    rename={'ref':'Reference','ref_pw':'Reference','P1_pw':'P1','P2_pw':'P2','retrieval':'Related work','low':'Low reasoning','noagg':'No aggregation','plan':'Research plan'}
    ax.set_yticks(range(len(variants)),[rename.get(v,v) for v in variants]);ax.tick_params(length=0)
    return im

pair=['ref','P1','P2','P3','P4','P5','retrieval','low','noagg','plan']
point=['ref_pw','P1_pw','P2_pw','retrieval','low','noagg','plan']
for filename,panels in [
    ('paper_fig4_subset.png',[('p4a','macro_f1',point,'Fig. 4a: pointwise macro-F1'),('p4b','strict',pair,'Fig. 4b: pairwise strict accuracy')]),
    ('paper_fig8_9_subset.png',[('p4b','soft',pair,'Fig. 8: pairwise soft accuracy'),('p4a','f1_pos',point,'Fig. 9a: novel-class F1'),('p4a','f1_neg',point,'Fig. 9b: not-novel-class F1')]),
    ('paper_fig11_subset.png',[('p4a','macro_f1',point,'Fig. 11a: derived no-aggregation'),('p4b','strict',pair,'Fig. 11b: derived no-aggregation')])]:
    fresh='fig11' in filename
    fig,axs=plt.subplots(1,len(panels),figsize=(5*len(panels),7),layout='constrained')
    for ax,(kind,metric,variants,title) in zip(np.atleast_1d(axs),panels):
        im=matrix(ax,kind,metric,variants,fresh);ax.set_title(title,fontsize=11)
    fig.colorbar(im,ax=np.atleast_1d(axs).tolist(),shrink=.65,label='Change from aggregated reference (percentage points)')
    fig.suptitle('One DeepSeek judge; legacy effort not explicitly verified\nAbsolute scores in parentheses; * paired BCa CI excludes zero; grey = not run',fontsize=11)
    fig.savefig(OUT/filename,dpi=180);plt.close(fig)

fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
variants=['ref','P1','P2','P3','P4','P5','noagg','plan'];x=np.arange(len(variants))
for j,(s,label,color) in enumerate(zip(settings,labels,['#2a78d6','#eb6834'])):
    ax.bar(x+(j-.5)*.36,[100*M[f'p4b_{s}_{v}']['tie_rate'] for v in variants],.36,label=label,color=color)
ax.set_xticks(x,variants);ax.set_ylabel('Tie rate (%)');ax.set_title('Fig. 10 / Table 6 subset: observed tie rates');ax.legend()
fig.savefig(OUT/'paper_fig10_tie_rates.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
plan_variants=['ref','plan','P3','P4','P5'];x=np.arange(len(plan_variants))
for j,(s,label,color) in enumerate(zip(settings,labels,['#2a78d6','#eb6834'])):
    names=[f'p4b_{s}_ref',f'p4b_{s}_plan']+[f'fig12_{s}_{v}_plan' for v in ['P3','P4','P5']]
    bars=ax.bar(x+(j-.5)*.36,[100*M[n]['strict'] for n in names],.36,label=label,color=color)
    ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
ax.set_xticks(x,['Abstract reference','Plan reference','Plan + P3','Plan + P4','Plan + P5']);ax.set_ylabel('Strict accuracy (%)');ax.set_ylim(0,100);ax.set_title('Fig. 12: plan-format prompt comparison');ax.legend()
fig.savefig(OUT/'paper_fig12_plan_prompts.png',dpi=180);plt.close(fig)
with (OUT/'table6_tie_rates.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['config','tie','total','tie_rate']);w.writeheader()
    for name,r in M.items():
        if r['kind']=='pair':w.writerow({k:r[k] for k in ['config','tie','total','tie_rate']})
print('Rendered five paper-organized figures and exact tie-rate CSV, zero API calls')
