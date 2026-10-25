# 已有成果更新 / Progress checkpoint - 2026-10-26

与10月25日已同步版本相比，本次没有新增API实验；新增的是成果索引、逐次日志核验与增量说明。40个源配置、58个去重条件的数量保持不变。

## 与早期37配置阶段相比

| 增加的部分 | 实际意义 |
|---|---|
| 3组Human-Only计划格式实验（P3/P4/P5） | 补齐图12两种设定，源配置从37增至40 |
| 22组无聚合派生结果，去重新增18个条件 | 按作者代码取三个单次子运行，无需额外API调用 |
| 统计与配套图表 | 现共120项配对BCa比较，每项10万次重采样；包含已有条件的软准确率、逐类F1、平局率与计划格式图 |
| 可追溯记录 | 40个源配置共8271条条目判决、34379张有效票；66个派生子运行可追溯到原投票 |

无聚合说明已纠正：此前额外重复调用已停止，7组完整重复和1组部分结果另存，不重复计入覆盖数。

## 成果入口

- [两页英文成果概述](DeepSeek_Progress_Brief_EN.pdf)
- [源配置指标](../results/all_configurations_summary.json) / [完整性核查](../results/configuration_audit.json)
- [无聚合派生结果与统计](../results/analysis/paper_noagg_derivation.json)
- [原矩阵统计](../results/analysis/paired_bootstrap_results.json)
- [逐条件进度](../results/analysis/experiment_coverage.json)
- [本次日志核验](../logs/updates/2026-10-26.json)

## 尚未完成

剩余28个条件：主消融8、依赖其源结果的无聚合派生8、跨生成器检索6、专用评估器4、强检索2。另需4组明确高推理的匹配基线。58/86仅为单评委配置清单覆盖数，不能当作整篇论文完成率。

历史推理设置未固定、部分旧原始回答缺失，标签和专家验证继承自作者。详见[协议核查](protocol_review.md)。

本次未调用DeepSeek评判API。费用台账按已有响应及导出账单在本地更新；没有新官方账单，估算仍标为估算。个人账单与密钥不公开。

English: This documentation-only checkpoint adds no model calls or experimental conditions since the previous publication. Relative to the early 37-configuration stage, three Human-Only plan-prompt runs and 22 derived no-aggregation conditions are available (18 additional distinct conditions). The archive contains 120 paired BCa comparisons. It remains a selected single-judge replication.
