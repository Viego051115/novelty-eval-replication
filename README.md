# Novelty evaluation replication with Chinese LLMs

使用国产大模型评判科研想法新颖性的复现实验。当前评判器为 DeepSeek；复用原作者的英文基准，**不是全部由国产模型生成的数据流水线**。

## Status / 当前状态

- Snapshot UTC: `2026-10-23T06:25:07.529730+00:00`
- Agreed local matrix: 37 configurations. This is a subset/extension of the paper, not all paper experiments.
- Files in this snapshot: 35; configurations passing item-count and full-vote checks: 31.
- Exact per-configuration counts and invalid item indices: [snapshot audit](docs/snapshot_audit.json).
- A snapshot is static. A running experiment may have progressed beyond it; commit a fresh snapshot to update GitHub.

## Research question

Does novelty judging remain sensitive to prompt wording and input distribution when the judge is a Chinese LLM?

## Layout

| Path | Contents |
|---|---|
| `data/` | Original benchmark Parquet files, with attribution below |
| `harness2.py` | Legacy prompt templates and majority / order-balanced judging |
| `run_matrix.py` | Legacy driver for the agreed 37-configuration matrix |
| `finish_fig13.py` | Item/vote-level checkpointed generator-source continuation |
| `results/deepseek_*.jsonl` | Item indices, labels, predictions and votes |
| `results/fig13_api_responses.jsonl` | Recent final response texts, timestamps, model IDs and token usage |
| `logs/legacy/` | Historical logs; may include interrupted or failed runs |
| `docs/` | Audit and protocol limitations |

## Setup and reproduction

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Fill API keys locally. Never commit .env.
python -u finish_fig13.py
```

`finish_fig13.py` calls paid DeepSeek APIs, resumes valid saved votes/items, checks balance, uses four workers and a per-invocation CNY 10 stopping threshold plus a CNY 2 reserve. **Restarting resets the per-invocation budget.** Balance reporting can lag and in-flight calls can overshoot the threshold. It operates on the four pre-generated sources in the local data (GPT-5 is an extension beyond the paper's listed generator comparison).

The other drivers are archived implementations, not recommended for blind reruns: `run_matrix.py` can discard an incomplete configuration and repeat paid calls. Read the audit first.

## Interpretation limits

This repository records exploratory replication work. Results are not a validated full replication. Legacy reports/plots were not included because some contain outdated counts or overstrong conclusions. Do not infer true novelty, self-preference, or stylistic causation from judge/weak-label disagreement alone. Strict accuracy below 50% must be interpreted with tie rate and soft accuracy. No completed significance test is claimed.

## Attribution

- Sternlicht et al., *Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation*, arXiv:2610.02022v1: https://arxiv.org/abs/2610.02022
- Original dataset: https://huggingface.co/datasets/noystl/novelty-judge-bench
- Dataset license reported by its upstream card: CC BY 4.0. Retain attribution and verify the upstream card before redistribution outside this private research repository.
- Dataset files are copied without modification. Original paper PDFs and unrelated personal files are excluded.

No project-wide license is asserted for upstream materials. API keys are excluded.
