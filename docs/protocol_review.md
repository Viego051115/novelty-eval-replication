# Protocol review / 原文对照与待修正项

## What is aligned in the planned subset

- Official datasets; two settings; pointwise 3 calls and pairwise 3 calls in each order.
- Pairwise no-aggregation uses one call per order (2 total), not one total.
- Max output tokens 8192; temperature not explicitly set in harness2 / continuation.
- Reference, P1/P2 and pairwise P3/P4/P5; supplied plan-format inputs.

## What is not yet established / remaining work

1. Audit flags must be repaired before declaring all configurations complete. Missing/unparsed votes cannot be treated as genuine ties.
2. Legacy parser accepts fallback digits and may use reasoning content when final content is empty. Recent continuation instead requires an explicit novelty field in final content. This parser change is a methodological difference between run generations.
3. No independently verified byte-for-byte prompt comparison is claimed; PDF line-wrap and formatting extraction require careful comparison.
4. Model alias `deepseek-chat` is not a pinned snapshot. Recent calls record returned model IDs; historical calls often do not. Cross-date version changes need checking before pooling.
5. reasoning_effort=high is not sent. Support and equivalent settings for the actual model version must be verified; omission is not identical to the paper's high-effort condition.
6. Paper Fig.4 also includes retrieval and low reasoning effort, neither implemented in this matrix. Fig.12 includes both settings; local runs currently cover Human+Generated only.
7. Paper Fig.13 lists Sonnet 4.5 baseline plus Opus 4.5 / GPT-5.1 / GPT-5.4; local GPT-5 is an extra condition.
8. Paired 100,000-resample BCa confidence intervals and significance marks remain to be computed and validated.
9. Paper Fig.11 removes aggregation throughout the controlled matrix. The local noagg row alone does not reproduce that experiment.
10. Agentic retrieval, dedicated evaluators, cost-quality comparisons and retrieval across generators are not completed.

Dataset review and signal-extraction stages used foreign LLMs upstream even for Human-Only text; only the original paper ideas themselves are human-authored. Reusing this benchmark isolates judge changes; it does not independently repeat upstream expert validation.

## Evidence and conclusions

Read saved predictions by unique item index, require the expected vote count, and check label alignment. Avoid inferring a full configuration from file existence. Generator-side low-novelty labels are assumptions inherited from the benchmark; falling accuracy can reflect judge failure, weak-label problems, or both. Correlation with generated text is not proof of a style mechanism.
