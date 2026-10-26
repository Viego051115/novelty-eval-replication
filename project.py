"""Single entry point for experiment, analysis, reporting and maintenance tasks."""
from pathlib import Path
import argparse,importlib.util,os,shlex,subprocess,sys

ROOT=Path(__file__).resolve().parent
COMMANDS={
    'status':('programs.analysis.build_coverage','查看/更新已有实验进度',False),
    'audit-extras':('programs.maintenance.audit_extra_repeats','核查额外重复实验和已保存回答',False),
    'report-pdf':('programs.reporting.create_progress_pdf','生成当前英文 PDF',False),
    'charts':('programs.reporting.render_paper_figures','更新对应原文的图表',False),
    'report-text':('programs.reporting.report_current_results','更新本地文字成果和对照图',False),
    'finance':('programs.finance.build_cost_ledger','从已有账单/响应更新私有费用台账',False),
    'resume-generators':('programs.experiments.finish_fig13','续跑生成器来源实验（付费）',True),
    'resume-plans':('programs.experiments.run_deepseek_extensions','续跑计划格式实验（付费）',True),
    'probe-options':('programs.diagnostics.probe_deepseek_options','诊断模型参数（付费）',True),
    'repeat-noagg':('programs.experiments.run_fig11_fresh','额外无聚合重复调用（付费；通常不需要）',True),
    'legacy-matrix':('programs.experiments.run_matrix','旧矩阵驱动（付费；续跑需谨慎）',True),
}
BATCHES={
    'refresh-results':('更新已有成果、图表和英文报告',False),
    'statistics':('重新计算配对统计与无聚合派生结果（仅本地CPU）',False),
    'audit-results':('完整核验已有预测，不上传',False),
    'prepare-github':('核验并准备公开快照，不上传',False),
    'sync-github':('核验、打包并同步公开 GitHub（不调用模型）',False),
    'verify-github':('只读核对远端与本地快照',False),
}

def pdf_python():
    configured=os.environ.get('NOVELTY_PDF_PYTHON')
    if configured:return configured
    if importlib.util.find_spec('reportlab') and importlib.util.find_spec('pypdf'):return sys.executable
    bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if bundled.is_file():return str(bundled)
    raise SystemExit('PDF依赖缺失：安装 reportlab 和 pypdf，或设置 NOVELTY_PDF_PYTHON。')

def run(module,extra,*,dry=False,pdf=False):
    try:available=importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:available=False
    if not available:raise SystemExit('此命令只在完整本地工作目录提供，公开快照不含该辅助程序：'+module)
    command=[pdf_python() if pdf else sys.executable,'-m',module,*extra]
    print(('DRY RUN: ' if dry else 'RUN: ')+shlex.join(command),flush=True)
    if not dry:
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
        subprocess.run(command,cwd=ROOT,env=env,check=True)

def main():
    sys.dont_write_bytecode=True
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='实验项目统一入口；结果更新与付费实验分开。',formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='\n'.join(f'  {name:20} {desc}'+(' [会调用付费API]' if paid else ' [无模型API调用]') for name,(_,desc,paid) in COMMANDS.items())+'\n'+
        '\n'.join(f'  {name:20} {desc} [无模型API调用]' for name,(desc,_) in BATCHES.items()))
    parser.add_argument('command',nargs='?',choices=list(COMMANDS)+list(BATCHES))
    parser.add_argument('--dry-run',action='store_true',help='只显示计划命令，不执行')
    parser.add_argument('--skip-pdf',action='store_true',help='refresh-results 时跳过PDF生成')
    parser.add_argument('--include-finance',action='store_true',help='refresh-results 时一起更新本地私有费用台账')
    args,extra=parser.parse_known_args()
    if not args.command:parser.print_help();return
    if args.command in COMMANDS:
        module,_,paid=COMMANDS[args.command]
        if paid:print('此命令会调用付费模型API；请查看该实验的断点和余额规则。',flush=True)
        run(module,extra,dry=args.dry_run,pdf=args.command=='report-pdf');return
    if extra:parser.error('此批处理命令不接受额外参数：'+' '.join(extra))
    steps=[]
    if args.command=='refresh-results':
        steps=[('programs.analysis.build_coverage',[]),('programs.reporting.report_current_results',[]),('programs.reporting.render_paper_figures',[])]
        if args.include_finance:steps.append(('programs.finance.build_cost_ledger',[]))
        if not args.skip_pdf:steps.append(('programs.reporting.create_progress_pdf',[]))
    elif args.command=='statistics':steps=[('programs.analysis.analyze_existing_results',[]),('programs.analysis.derive_noagg_paper',[])]
    elif args.command=='audit-results':steps=[('programs.maintenance.finalize_snapshot',['--audit-only'])]
    elif args.command=='verify-github':steps=[('programs.maintenance.publish_api_snapshot',['--verify-only'])]
    else:
        steps=[('programs.maintenance.finalize_snapshot',[]),('programs.maintenance.split_public_responses',[])]
        if args.command=='sync-github':steps.append(('programs.maintenance.publish_api_snapshot',[]))
    for module,parameters in steps:run(module,parameters,dry=args.dry_run,pdf=module.endswith('.create_progress_pdf'))

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit('命令执行未完成（退出码 '+str(exc.returncode)+'）。请查看上方具体错误；已保存结果和上传缓存会保留。') from None
