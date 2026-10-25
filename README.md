# Novelty evaluation replication with Chinese LLMs

使用国产大模型评判科研想法新颖性的复现实验。当前评判器为 DeepSeek；复用原作者的英文基准，**不是全部由国产模型生成的数据流水线**。

## Status / 当前状态

- Verified snapshot UTC: `2026-10-25T13:24:35.970660+00:00`.
- All **40/40 completed local configurations** pass unique-item count, label alignment, valid-vote count and aggregation checks. These include the original 37 and 3 Human-Only plan-prompt supplements; fresh Fig11 conditions are included only after their full batch completes.
- This is one DeepSeek judge on a selected experiment matrix; it is **not** a completed reproduction of all experiments in the paper.
- Results: [all configuration metrics](results/all_configurations_summary.json); [integrity audit](results/configuration_audit.json).
- Paired 100,000-resample BCa tests are available in `results/analysis/paired_bootstrap_results.json`. Additional judges, retrieval and dedicated evaluators remain unfinished.
- Author-aligned no-aggregation derivation: `results/analysis/paper_noagg_derivation.json` contains 22 conditions using all three k=1 subruns and 52 additional BCa comparisons. These add 18 distinct conditions to the 40 actual-run conditions (58 covered conditions); four reference noagg rows overlap. Extra fresh repeats were stopped as unnecessary and are excluded from this coverage count.
- Model versions, parser differences and other protocol limitations are documented below and in `docs/protocol_review.md`.
- Private financial ledgers and original billing exports are excluded from this public repository.

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
| `results/raw_response_parts/` | Recent final response texts, timestamps, model IDs and token usage |
| `logs/legacy/` | Historical logs; may include interrupted or failed runs |
| `docs/` | Audit and protocol limitations |

## Setup and reproduction

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Fill API keys locally. Never commit .env.
python -u finish_fig13.py
```

`finish_fig13.py` calls paid DeepSeek APIs, resumes valid saved votes/items, checks balance, uses four workers and a per-invocation CNY 5 default stopping threshold (adjustable via NOVELTY_MAX_SPEND_CNY) plus a CNY 2 reserve. **Restarting resets the per-invocation budget.** Balance reporting can lag and in-flight calls can overshoot the threshold. It operates on the four pre-generated sources in the local data (GPT-5 is an extension beyond the paper's listed generator comparison).

The other drivers are archived implementations, not recommended for blind reruns: `run_matrix.py` can discard an incomplete configuration and repeat paid calls. Read the audit first.

## Interpretation limits

This repository records exploratory replication work. Results are not a validated full replication. Legacy reports/plots were not included because some contain outdated counts or overstrong conclusions. Do not infer true novelty, self-preference, or stylistic causation from judge/weak-label disagreement alone. Strict accuracy below 50% must be interpreted with tie rate and soft accuracy. Paired BCa significance tests for completed configurations are supplied in results/analysis; these are unadjusted per-comparison intervals.

## Attribution

- Sternlicht et al., *Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation*, arXiv:2610.02022v1: https://arxiv.org/abs/2610.02022
- Original dataset: https://huggingface.co/datasets/noystl/novelty-judge-bench
- Dataset license reported by its upstream card: CC BY 4.0. Retain attribution and verify the upstream card before redistribution outside this research repository.
- Dataset files are copied without modification. Original paper PDFs and unrelated personal files are excluded.

No project-wide license is asserted for upstream materials. API keys are excluded.

Raw responses are gzip-compressed without content changes. Before resuming, decompress results/raw_response_parts/ to results/fig13_api_responses.jsonl.

The gzip response archive is split into small lossless parts for reliable upload. Run `python restore_response_log.py` before resuming to restore and SHA-256-verify the original response log. No API requests are made by that restore script.

The gzip response archive is split into small lossless parts for reliable upload. Run `python restore_response_log.py` before resuming to restore and SHA-256-verify the original response log. No API requests are made by that restore script.
