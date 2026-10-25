# Protocol review and remaining work

The 40 completed source configurations pass item-count, label, vote-count and aggregation checks. They are a selected single-DeepSeek study, not a complete reproduction of the multi-model paper.

## Aligned elements

- Official English benchmark; two settings; 299/308 pointwise items and 154 pairs per setting.
- Reference sampling: three pointwise votes, or three votes in each pairwise presentation order.
- Reference, P1/P2, pairwise P3/P4/P5, supplied plan-format inputs, and released alternative-source data.
- Human-Only plan P3/P4/P5 supplements completed on October 25.
- Corpus-level paired BCa intervals: 100,000 resamples, shared item indices, no multiple-testing adjustment.

## No-aggregation correction

The authors' README explicitly derives no-aggregation results from saved votes; fresh calls are not required. Their derive_subrun_artifacts.py selects each index k=0,1,2 to create three single-sample subruns. Pairwise subrun k uses one forward and one reverse vote; pointwise uses vote k. Metrics are computed per subrun and then averaged. Fig11 compares with the Fig4 reference, which still aggregates.

derive_noagg_paper.py implements that procedure on the validated local votes: 22 derived conditions, of which 18 add distinct conditions beyond the source matrix. Thus 58 distinct conditions are covered. Source and derived counts are not added without deduplication.

Earlier first-vote diagnostics remain labelled as diagnostics. Seven complete fresh repeats and one partial repeat were additionally obtained before the upstream derivation was checked; they are archived as supplementary repeats, excluded from condition coverage. Further fresh calls were stopped. run_fig11_fresh.py now requires an explicit optional-repeat flag.

Pinned upstream reference: [1db410dc0a57d94e51d57b3e52a03e4f9e0fb578](https://github.com/noy-sternlicht/novelty-eval/tree/1db410dc0a57d94e51d57b3e52a03e4f9e0fb578). This code inspection does not change the experiment's paper target, the user's v1 PDF.

## Limits still requiring resolution

1. Legacy parsers accept fallback digits and sometimes reasoning content when final content is empty. Recent continuation requires an explicit novelty field in final content. Historical answers cannot all be re-parsed because only some raw responses survived.
2. deepseek-chat is an unpinned alias. Returned model names are recorded for recent calls, not all historical ones. No stable historical model snapshot is established.
3. Historical calls omit explicit thinking effort. Current official low/high probes work, but current documentation cannot establish historical default behavior. Four matched explicit-high references are needed before interpreting four explicit-low conditions.
4. No independently verified byte-for-byte prompt identity is claimed. The prompts were checked against the paper text; whitespace and formatting were transcribed.
5. Fig4 still lacks four retrieval and four explicit-low conditions. Eight Fig11 extensions depend on those missing sources and can later be derived without additional judging calls.
6. Cross-source retrieval, agentic retrieval and dedicated evaluators remain unfinished. The authors' retrieval workflow requires a cache built with contributions, five queries, Paper Finder, publication cutoff 2025-03-01 and self-paper exclusion. Generic search would be a changed retrieval protocol.
7. Fig13 paper sources are the Sonnet baseline plus Opus 4.5, GPT-5.1 and GPT-5.4. GPT-5 is an additional condition, not a required paper source.
8. Upstream data construction used foreign LLMs, including signal extraction and text normalization. These runs change the judge, not the entire data pipeline. Expert validation is inherited, not independently repeated.

## Interpretation

Strict accuracy counts ties as failures. Strict accuracy below 50% alone does not establish reversed preferences; inspect soft accuracy and ties. Weak generated-side labels are inherited assumptions. Falling accuracy can reflect judge errors, weak-label errors, or both. Source effects do not establish stylistic causation or self-preference.

Private original invoices, per-key balances and financial ledgers stay local and are excluded from this public repository.
