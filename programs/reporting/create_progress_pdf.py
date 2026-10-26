"""Brief English research report generated only from audited metrics."""
from programs.paths import PROJECT_ROOT, PUBLIC_ROOT
from pathlib import Path
import json,re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from pypdf import PdfReader

ROOT = PROJECT_ROOT
AN=ROOT/'results'/'analysis'; OUT=ROOT/'output'/'pdf';OUT.mkdir(parents=True,exist_ok=True)
M={r['config']:r for r in json.loads((ROOT/'results'/'all_configurations_summary.json').read_text())}
A=json.loads((ROOT/'results'/'configuration_audit.json').read_text())
B=json.loads((AN/'paired_bootstrap_results.json').read_text())
count=A['valid_configurations']
DER=AN/'paper_noagg_derivation.json'
D=json.loads(DER.read_text(encoding='utf-8')) if DER.exists() else None
comparison_count=len(B['tests'])+(len(D['tests']) if D else 0)
coverage=json.loads((AN/'experiment_coverage.json').read_text(encoding='utf-8'))
p4=next(r for r in B['tests'] if r['config']=='p4b_human-plus-generated_P4' and r['metric']=='strict')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleX',fontName='Helvetica-Bold',fontSize=21,leading=25,textColor=colors.HexColor('#153f62'),spaceAfter=11))
styles.add(ParagraphStyle(name='HeadX',fontName='Helvetica-Bold',fontSize=12,leading=15,textColor=colors.HexColor('#153f62'),spaceBefore=10,spaceAfter=6))
styles.add(ParagraphStyle(name='BodyX',fontName='Helvetica',fontSize=9.5,leading=13,spaceAfter=6))
styles.add(ParagraphStyle(name='SmallX',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=5,textColor=colors.HexColor('#425166')))
P=lambda text:Paragraph(text,styles['BodyX'])
S=lambda text:Paragraph(text,styles['SmallX'])
H=lambda text:Paragraph(text,styles['HeadX'])
def table(rows,widths):
    t=Table([[P(str(c)) for c in r] for r in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf1f7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#8ba7bd')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d6e0e8')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    return t

story=[Paragraph('DeepSeek Novelty Judging',styles['TitleX']),P('<b>Updated progress report and new results</b>'),
H('Research purpose and design'),
P('Test whether the sensitivity of LLM novelty judgments extends to a Chinese-model judge. I retain the authors\' English benchmark and change the judge to DeepSeek. The data include Human-Only and Human+Generated settings; this is not a wholly Chinese-model data-generation pipeline.'),
P('Pointwise evaluation asks whether one idea is novel (299 / 308 items); pairwise evaluation chooses between two ideas (154 pairs per setting). The legacy reference uses three pointwise votes or three votes per presentation order for pairwise evaluation. Prompt wording, aggregation, input format and pre-generated negative sources are varied.'),
H('Additions since the earlier 37-configuration stage'),
P('I completed three Human-Only plan-format conditions (P3, P4 and P5), bringing the source matrix to 40 configurations. Following the authors\' code, I derived 22 no-aggregation conditions from the saved votes; 18 add distinct conditions after deduplication. I also completed the associated statistics and figures. This document refresh itself adds no new model calls or experimental conditions.'),
H('Verified results'),P(f'<b>{count} completed configurations</b> pass item-index, label, vote-count and aggregation checks. The original 37 configurations and three Human-Only plan-prompt supplements are complete. '+('The authors\' three-subrun procedure yields 22 no-aggregation conditions, covering 18 additional conditions after deduplication (58 conditions in total).' if D else 'No-aggregation results are being derived from existing votes.')),
table([['Setting','Pointwise macro-F1','Pairwise strict','Pairwise soft','Tie rate']]+[[label,f"{M[f'p4a_{s}_ref_pw']['macro_f1']:.3f}",f"{M[f'p4b_{s}_ref']['strict']:.3f}",f"{M[f'p4b_{s}_ref']['soft']:.3f}",f"{100*M[f'p4b_{s}_ref']['tie_rate']:.1f}%"] for s,label in [('human-only','Human-Only'),('human-plus-generated','Human+Generated')]], [43*mm,37*mm,31*mm,31*mm,26*mm]),
Spacer(1,5*mm),Image(str(AN/'configuration_changes.png'),width=168*mm,height=68.7*mm),
S('Figure 1. Changes from the reference. Stars indicate paired BCa 95% intervals excluding zero; 100,000 resamples per comparison, without multiple-testing correction.'),
P(f"On Human+Generated data, P4 reduces strict accuracy by <b>{-100*p4['difference']:.2f} percentage points</b> (95% CI: {100*p4['ci_low']:.2f} to {100*p4['ci_high']:.2f}). This supports prompt sensitivity for this judge and benchmark; it does not establish the true novelty of individual ideas."),
PageBreak(),
H('Source effects and progress against the paper'),Image(str(AN/'generator_comparison.png'),width=168*mm,height=61.1*mm),
S('Figure 2. DeepSeek is the fixed judge; the pre-generated negative-source data change. GPT-5 is an extra source. These archived data were reused without calling foreign-model APIs.'),
H('Newly completed Human-Only plan results'),
table([['Plan prompt','Human-Only strict','Human-Only soft','Human+Generated strict']]+[[v,f"{M[f'fig12_human-only_{v}_plan']['strict']:.3f}",f"{M[f'fig12_human-only_{v}_plan']['soft']:.3f}",f"{M[f'fig12_human-plus-generated_{v}_plan']['strict']:.3f}"] for v in ['P3','P4','P5']],[30*mm,44*mm,44*mm,50*mm]),
S('The Human+Generated plan results were already available. The new Human-Only results complete both settings for Fig. 12; cross-setting differences alone do not identify a causal mechanism.'),
H('Remaining work'),
P(f"The checklist covers <b>{coverage['completed']} distinct conditions</b> out of {coverage['total_including_two_extras']} (including two extra GPT-5 source conditions). The remaining 28 comprise eight main ablations, eight no-aggregation derivations dependent on them, six cross-source retrieval conditions, four dedicated-evaluator conditions and two strong-retrieval conditions. Four matched explicit-high references are also needed. This count is not overall paper completion."),
H('Current problems and next steps'),
P('<b>Reasoning control:</b> historical calls used an unpinned alias without explicit effort. Low/high probes cannot establish historical behavior; matched references are required.'),
P('<b>Retrieval fidelity:</b> the original pipeline uses contributions, five queries, Paper Finder and a 2025-03-01 cutoff. Retrieval and dedicated evaluators still need implementation and cost measurement.'),
P('<b>Evidence limits:</b> labels and expert validation are inherited; some historical responses are missing and parsers changed. Strict accuracy counts ties as zero, so scores below 0.5 alone do not prove reversed preferences.'),
S(f'Archive: {comparison_count} paired BCa comparisons, 100,000 resamples each; no multiple-testing adjustment. Source runs, three-subrun derivations and supplementary fresh repeats remain separate. This is a selected single-judge replication.'),
S('Source: Sternlicht et al., Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation, arXiv:2610.02022v1. Benchmark: huggingface.co/datasets/noystl/novelty-judge-bench. Code: github.com/Viego051115/novelty-eval-replication.')]

path=OUT/'DeepSeek_Progress_Brief_EN.pdf'
def footer(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#65758a'));canvas.drawRightString(190*mm,12*mm,str(doc.page))
SimpleDocTemplate(str(path),pagesize=(210*mm,297*mm),rightMargin=21*mm,leftMargin=21*mm,topMargin=17*mm,bottomMargin=19*mm,title='DeepSeek novelty judging: replication progress').build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(path);assert len(reader.pages)==2, len(reader.pages)
text='\n'.join(p.extract_text() for p in reader.pages)
assert str(count)+' completed configurations' in text and '24.68' in text and 'Newly completed Human-Only plan results' in text
assert not re.search(r'\b(?:we|our|ours|ourselves|us)\b',text,re.I), 'Report must use singular first-person wording'
print(path,'2 pages, extracted text verified')
