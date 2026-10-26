"""Generate current figures and an honest completion report using validated JSON only."""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = PROJECT_ROOT
OUT=ROOT/'results'/'analysis';OUT.mkdir(exist_ok=True)
metrics=json.loads((ROOT/'results'/'all_configurations_summary.json').read_text())
M={r['config']:r for r in metrics}
tests=json.loads((OUT/'paired_bootstrap_results.json').read_text())
T={(r['config'],r['metric']):r for r in tests['tests']}
derived=OUT/'paper_noagg_derivation.json'
D=json.loads(derived.read_text(encoding='utf-8')) if derived.exists() else None
if D:
    M.update({r['config']:r for r in D['metrics']})
    T.update({(r['config'],r['metric']):r for r in D['tests']})
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for ax,kind,variants,metric,title in [
    (axs[0],'p4b',['P1','P2','P3','P4','P5','noagg','plan'],'strict','Pairwise: strict accuracy'),
    (axs[1],'p4a',['P1_pw','P2_pw','noagg','plan'],'macro_f1','Pointwise: macro-F1')]:
    x=np.arange(len(variants));width=.36
    for j,(setting,color,label) in enumerate([('human-only','#2a78d6','Human-Only'),('human-plus-generated','#eb6834','Human+Generated')]):
        ref=M[f'{kind}_{setting}_{"ref" if kind=="p4b" else "ref_pw"}'][metric]
        delta=[100*(M[f'{kind}_{setting}_{v}'][metric]-ref) for v in variants]
        bars=ax.bar(x+(j-.5)*width,delta,width,label=label,color=color)
        for b,v in zip(bars,variants):
            test=T.get((f'{kind}_{setting}_{v}',metric))
            if test and test['significant_95pct']:ax.annotate('*',(b.get_x()+b.get_width()/2,b.get_height()),ha='center',va='bottom' if b.get_height()>=0 else 'top')
    ax.axhline(0,color='#555',lw=.8);ax.set_xticks(x,variants,rotation=25);ax.set_ylabel('Change from reference (percentage points)');ax.set_title(title);ax.legend(fontsize=8)
fig.suptitle('DeepSeek: sensitivity to evaluation configuration\n* paired BCa 95% CI excludes zero; 100,000 resamples',fontsize=12)
fig.savefig(OUT/'configuration_changes.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
sources=['Human','Sonnet-4.5','Opus-4.5','GPT-5.1','GPT-5.4','GPT-5 (extra)']
for ax,kind,metric,title in [(axs[0],'pair','strict','Pairwise strict accuracy'),(axs[1],'point','macro_f1','Pointwise macro-F1')]:
    k='p4b' if kind=='pair' else 'p4a';ref='ref' if kind=='pair' else 'ref_pw'
    values=[M[f'{k}_human-only_{ref}'][metric],M[f'{k}_human-plus-generated_{ref}'][metric]]+[M[f'fig13_{g}_{kind}'][metric] for g in ['opus-4-5','gpt-5.1','gpt-5.4','gpt-5']]
    bars=ax.bar(np.arange(6),np.array(values)*100,color=['#2a78d6']+['#eb6834']*5)
    ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=3);ax.set_ylim(0,100);ax.set_xticks(np.arange(6),sources,rotation=30,ha='right');ax.set_ylabel('Percent');ax.set_title(title)
    if kind=='pair':ax.axhline(50,color='#666',ls='--',lw=1,label='50% forced-choice reference');ax.legend(fontsize=7)
fig.suptitle('Effect of pre-generated negative-source data; judge fixed to DeepSeek',fontsize=12)
fig.savefig(OUT/'generator_comparison.png',dpi=180);plt.close(fig)

report='''# DeepSeek复现：已完成部分与剩余工作（2026-10-25）

## 核实后的进度

最初约定的37个配置已经全部完成。独立检查确认37配置、7809条最终条目判决、31607张有效投票；包括3张缺失投票修补，使用每个条目最后一条有效记录。检查覆盖条目索引、标签、票数及聚合。

已完成62项对比的100000次配对BCa 95%置信区间；这一步使用本地CPU，没有API费用。没有做多重比较校正，与原文逐项CI判定方式一致。

![配置变化](configuration_changes.png)

![生成器来源比较](generator_comparison.png)

## 最新参考结果

| 设定 | Pointwise宏F1 | Pairwise严格准确率 | Pairwise软准确率 | 平局率 |
|---|---:|---:|---:|---:|
'''
for s in ['human-only','human-plus-generated']:
    p=M[f'p4b_{s}_ref'];q=M[f'p4a_{s}_ref_pw']
    report+=f"| {s} | {q['macro_f1']:.4f} | {p['strict']:.4f} | {p['soft']:.4f} | {p['tie_rate']:.4f} |\n"
report+='\n## 关键变化与证据\n\n'
for name,metric in [('p4b_human-plus-generated_P4','strict'),('p4b_human-plus-generated_P4','soft'),('P4_vs_P3_human-plus-generated','strict')]:
    r=T[(name,metric)];report+=f"- {name} / {metric}：差值{100*r['difference']:.2f}个百分点，95% CI [{100*r['ci_low']:.2f}, {100*r['ci_high']:.2f}]。\n"
report+='''
P4的严格准确率低于50%不能单独解释为“系统性判反”：平局计零会压低严格准确率。应同时看软准确率、平局率、直接相反判决数与置信区间。生成器实验使用继承的弱标签，不能单凭分数证明生成想法实际上更差、证明自我偏好，或证明风格是因果机制。

## 相对原文还缺什么

| 原文部分（单个DeepSeek评委版本） | 剩余情况 |
|---|---|
| 图4主消融 | 缺检索4项、低推理4项；现有26/34项。原文六评委总矩阵不能算成已复现 |
| 图12计划格式提示词 | Human-Only的P3/P4/P5三项已启动补跑；完成前不计入完成数 |
| 图13生成器来源 | 原文列出的来源均已完成，另有GPT-5两项扩展 |
| 图11全部配置关闭聚合 | 原文要求一套新的无聚合调用；目前仅有参考noagg和明确标注的事后投票重放，不能宣称图11完整复现 |
| 图5强检索、图14跨生成器检索 | 尚未完成，需文献检索工具与截止日期过滤 |
| 图6/7专用评估器及成本曲线 | 尚未完成，需适配Idea Novelty Checker和AI-Scientist流程 |

## 推理设置核查与费用预估

2026-10-25官方文档支持thinking.enabled与reasoning_effort low/high/max，默认high；历史deepseek-chat别名调用是否同样走思考模式，不能从当前文档反推。新探针发现显式low/high返回reasoning_tokens，而旧别名默认探针未报告该字段。因此新增high/low实验应成对使用显式设置，不能不加说明地拿旧默认基线直接作对照。

只按两次小样本探针外推，重新建立4个显式high基线并跑4个low条件，约需20至40元，存在任务长度带来的不确定性。当前余额约15元，不能保证全部覆盖。先补图12三项（估计1至3元）和免费分析；检索/专用评估器还需要额外工具，不能给出可靠的打包费用。周末Flash当前价格为每百万未命中输入1元、命中输入0.02元、输出4元。

官方来源：
- https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/
- https://api-docs.deepseek.com/zh-cn/quick_start/pricing/

## 仍需保留的局限

模型别名未固定版本；历史原始回答仅部分留存；新旧解析器不同；数据标签与专家验证为继承，未独立重做。报告应称“选定实验矩阵的国产评委复现”，而不是“整篇论文全部完成”。财务账单单独保存在private_finance，不公开上传。
'''
extension=ROOT/'results'/'extension_status.json'
if extension.exists() and json.loads(extension.read_text(encoding='utf-8')).get('status')=='complete':
    report=report.replace('最初约定的37个配置已经全部完成。','最初约定的37个配置以及3个Human-Only计划提示词补充已全部完成，共40个配置。')
    report=report.replace('已完成62项对比','已完成'+str(len(tests['tests']))+'项对比')
    report=report.replace('Human-Only的P3/P4/P5三项已启动补跑；完成前不计入完成数','Human-Only的P3/P4/P5三项已补齐，图12两种数据设定均完成')
fresh=ROOT/'results'/'fig11_fresh_status.json'
if fresh.exists() and json.loads(fresh.read_text(encoding='utf-8')).get('status')=='complete':
    report=report.replace('共40个配置。','再加18个重新调用API的关闭聚合补充，共58个配置。')
    report=report.replace('原文要求一套新的无聚合调用；目前仅有参考noagg和明确标注的事后投票重放，不能宣称图11完整复现','现有提示词/格式的18个补充已重新调用API完成，与图4仍保留聚合的参考配置比较。另有22项明确标注的事后重放；检索/低推理8项尚未完成，不能宣称图11完整复现')
    report+='\n新增18组无聚合结果与原文图11采用相同对照口径：参考配置继续聚合。来源文件fig11_fresh_status.json，按样本记录验证后计入完成数。\n'
if D:
    report=report.replace('共40个配置。','共40个实际运行配置；按作者脚本派生22个无聚合条件，扣除4个与主矩阵重复的参考条件，去重覆盖58个条件。额外重跑的7个完整条件另存，不重复计入覆盖率。')
    report=report.replace('已完成'+str(len(tests['tests']))+'项对比','已完成'+str(len(tests['tests'])+len(D['tests']))+'项对比（68项原矩阵及52项三子运行派生对比）')
    report=report.replace('原文要求一套新的无聚合调用；目前仅有参考noagg和明确标注的事后投票重放，不能宣称图11完整复现','按作者derive_subrun_artifacts.py，从k=3中分别取k=0/1/2形成三个k=1子运行，再平均各自指标。当前18/26扩展条件可从已有数据派生，无需新调用；检索/低推理8项待其源条件完成后派生')
    report=report.replace('先补图12三项（估计1至3元）和免费分析','图12三项已补齐；继续派生与免费分析')
    report+='\n## 作者代码核查后的修正\n\n此前“图11必须重新调用API”的判断有误。作者官方README明确从既有投票派生，因此新增额外调用已停止。保存的7个完整重复配置及一个部分配置保留为补充数据；其费用计入私有台账。正式图11采用全部三个子运行，不只采用第一票。作者代码固定版本1db410dc0a57d94e51d57b3e52a03e4f9e0fb578。\n'
events=ROOT/'private_finance'/'extension_balance_events.jsonl'
if events.exists():
    last=json.loads(events.read_text(encoding='utf-8').splitlines()[-1])
    report+=f"\n最近账户余额快照：{last['balance_cny']:.2f}元（{last['utc']}）。这是监测余额；具体消费以单独的私有费用台账和后续官方导出为准。\n"
(OUT/'DeepSeek阶段完成情况.md').write_text(report,encoding='utf-8')
print('Updated report and 2 figures from validated summaries, zero model calls')
