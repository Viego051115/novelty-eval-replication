# Project layout / 目录导航

Use `project.py` as the command entry point. Python modules now live under `programs/`; previous root-level programs are preserved in `legacy/pre-layout-2026-10-26/` for historical reference.

| Purpose / 用途 | Location / 位置 |
|---|---|
| Experiments / 实验与续跑 | `programs/experiments/` - may call paid APIs |
| Analysis / 统计、派生与进度 | `programs/analysis/` - local CPU only |
| Reporting / 更新图表和英文PDF | `programs/reporting/` - no model calls |
| Checks / 辅助核验 | `programs/maintenance/` - available checks only |
| Shared prompts / 公共提示词与路径 | `programs/core/` and `programs/paths.py` |
| Inputs / 基准输入 | `data/` |
| Predictions and responses / 预测与回答 | `results/` and `results/raw_response_parts/` |
| Statistics and figures / 统计与图表 | `results/analysis/` |
| English deliverable / 当前英文报告 | `docs/DeepSeek_Progress_Brief_EN.pdf` |
| Logs / 执行与更新记录 | `logs/` |

```powershell
python project.py status
python project.py statistics
python project.py refresh-results
```

`refresh-results` updates the coverage checklist, text, figures and PDF from existing metric files. Recompute statistics after source predictions change. `--dry-run` prints the selected commands without executing them; `--skip-pdf` skips PDF generation.

The full local workspace additionally has `programs/finance/`, diagnostic probes and publication helpers. These are excluded from this public code snapshot; personal bills and credentials are never copied here. Some help-menu commands therefore apply only to the full local workspace.

The directory update made no model calls and changed no scientific results or PDF content. Existing data and result paths remain stable. English reports use singular first-person wording (I / my).
