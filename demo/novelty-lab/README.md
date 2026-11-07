# Novelty Lab

An offline, bilingual teaching game built around fifteen selected saved DeepSeek judgments. Open `docs/index.html` directly, or use the repository GitHub Pages site when available. All CSS, scripts and case data are embedded. No API keys, model calls or external scripts are used.

## Three sections

1. Be the judge: choose an idea, reveal P3, predict whether P4 keeps or changes the winner or ties. Points reward predictions of judge behavior, not true novelty judgments. Fifteen selected cases comprise three flips, eight stable results and four cases with at least one tie; they do not estimate a population flip rate.
2. Rule laboratory: display saved aggregate results for prompt framing, voting, idea format and generator source. Benchmark agreement is not verified originality. P3 and P4 differ in target framing as well as wording.
3. Research flow: step through the controlled study, the use case and the proposed follow-up. Future work is marked not validated. Six bilingual SVG files are in `docs/flows`.

## Data provenance

Ideas come from the released noystl/novelty-judge-bench Human+Generated pairwise data. Saved P3/P4 verdicts and votes come from this repository's DeepSeek results. The judge saw full English inputs. Short bilingual summaries are teaching paraphrases. The original benchmark uses generated-negative weak labels. No new foreign-model API calls were made for this demo.

## Development

Source files are in `src/`; `cases.json` supplies the selected inputs and votes. The distributed HTML embeds all three source files and the case JSON. No package installation is needed to run it. SVG export and vote mapping are verified, alongside browser checks of changed, stable and tied cases.
