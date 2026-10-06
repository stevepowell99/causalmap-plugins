# Generic evaluation questions: effectiveness

Read this when a terms of reference asks whether a programme achieved its objectives or intended results, to what extent, for which groups, and what helped or held it back, and the evidence is reports, monitoring narratives, minutes and interviews rather than a dataset. It covers the OECD-DAC effectiveness criterion, and guards against the implementer's report of an achievement taken for the achievement itself.

Back to [generic evaluation questions](generic-evaluation.md), for what the criterion pages share and for the works cited.

## Scope, and the contrast inside the corpus

The 2019 definition asks "Is the intervention achieving its objectives?": the extent to which it achieved, or is expected to achieve, its objectives and its results, "including any differential results across groups", taking account of the relative importance of the objectives (OECD DAC 2019, p. 9). The 2021 guidance names four elements (OECD 2021, pp. 53 to 54).

- **Achievement of the objectives**, at each level of the results chain, usually outputs and outcomes. Where objectives were vague or shifted without the framework being updated, the evaluator reconstructs the logic from documents and interviews and judges against the current objectives.
- **Relative importance.** Where some objectives were met and others not, the conclusion depends on how much each mattered, which the evaluator and commissioner decide.
- **Differential results** across groups, whether or not equity was an objective; the [equity page](generic-evaluation-equity-and-differential-reach.md) carries the disaggregation.
- **Influencing factors** inside and outside the intervention: the enabling-and-constraining question most terms of reference ask, which is a causal question whose readings are on [causal mapping](causal-mapping.md).

Effectiveness concerns "more closely attributable results"; higher-order effects and broader change belong to [impact](generic-evaluation-impact.md) (OECD DAC 2019, p. 9). Terms of reference usually ask the bare criterion question, some version of "to what extent did the programme achieve its intended objectives", without any indicator, threshold or base. Before anything is designed it has to become a question with named objectives, a source for each, and a standard for "to what extent".

The contrast inside the corpus is between **reported** and **claimed** achievement: implementer progress reports and monitoring narratives against what beneficiaries, partners and external reviewers describe. A document attribute recording the kind of document or the speaker's role sets the two side by side.

## As a plan

The plan needs the objectives in writing. Where the results framework is among the documents, or the evaluator supplies it, its objectives become the values of a nominal column. Otherwise an open coding and a group step can find what the documents say the programme was trying to do, reported as objectives stated in the documents, never as its agreed framework.

**Sample.** Every document, unless the corpus is too large to read whole; then stratify by the attribute recording whose account a document gives.

**Code.** One closed step whose columns all take fixed values, so `second_coder` reads every document as well: the objective a passage reports on (the framework's objectives, plus one value for a result outside them); the status it gives (achieved, partly achieved, not achieved, in progress, or a plan or target only); and, where documents mix voices, whose account it is. The coder sees only the prompt and the definitions, so the designer writes into the prompt each objective in the framework's words with what counts as evidence of it; that an activity held or an output delivered is not an outcome achieved; that a target, plan or forecast is recorded as such; and that the status is what this passage says, not what the coder infers from elsewhere, and not whether the programme caused it. What helped or hindered is a separate causal coding (free-text cause and effect, with direction), coded once and grouped with `assign` true. Results the framework did not plan for need an open step (a free-text column for the change, a nominal one for direction) and a group step; open coding comes out low, so those counts are floors.

**Tabulate.** Count documents by objective and status, and by objective, status and whose account it is. The `.within.objective` cells give progress per objective with its own base ("of the documents that report on this objective, 7 of 11 report it achieved"). An objective no document reports on shows as 0, which is a finding about the documents rather than about the objective.

**Judge.** Only with the evaluator's standard for "to what extent", for example that an objective counts as achieved where the progress reports state it met and no beneficiary or external account contradicts it. A rule's share is out of the documents its base names (every document, unless a document attribute narrows it), never out of those that report on the objective, so a threshold among those is written as a count or as a reading. Relative importance is the evaluator's: without their ordering, combine `separate`, since `weakest` would let a minor objective decide the verdict. Without any standard, leave the judge out and offer standards in their terms without numbers: achieved where the implementer's reports and an independent account agree, or where most beneficiaries who speak of it describe the change, or where the framework's indicator is reported met.

**Write.** Name this page in `practice`, and [generative and counterfactual causation](generative-and-counterfactual.md) where the question asks why. Objective by objective: documents reporting each status out of those reporting on it, the implementer's account beside the beneficiaries', objectives nobody reports on named, and differential results where the documents allow.

**What the workflow must say it cannot answer.**

- **Attainment against indicators and targets**, unless the framework and the reported figures are in the documents. A stated figure is quoted, never checked; the evaluator supplies the monitoring data or answers that part outside the workflow.
- **Whether the programme caused an achievement.** The coder records whether a change is reported, apart from what anybody credits for it. Whether the programme contributed is a contribution question: [contribution analysis](contribution-analysis.md) and [causal mapping](causal-mapping.md) set out the ways of reading it (a direct link to each outcome, a theory of change tested link by link, or an open map of every causal claim) and what each needs, and [process tracing](process-tracing.md) tests the mechanism behind the few objectives the evaluation depends on.
- **Whether a reported achievement happened**, without a beneficiary or external account in the corpus or a source outside it.
- **How much each objective matters**, which the evaluator gives.

## What it guards against

The main fault is what might be called report inflation: progress reports written for the funder read as evidence that objectives were met. Counting status by whose account it is puts reported achievement beside what beneficiaries and external reviewers describe, so an objective achieved only in the implementer's documents shows as such. A separate status for targets and plans stops an intention being counted as a result, and keeping status apart from attribution stops "it happened" turning into "the programme did it" unannounced. Reporting objectives separately follows the guidance that an intervention may be "effective in some ways but not others, or effective from the perspective of some stakeholders, but not others" (OECD 2021, p. 54).

## Where Rubicon falls short

- **The numbers usually live outside the documents.** The guidance names missing baselines, mid-term assessments and disaggregated data as a challenge, with a contribution story as one way round it (OECD 2021, p. 55). Narrative documents rarely carry indicators, baselines or targets, so the answer reports what the documents say and states that this is not attainment against the framework.
- **A document is one case.** A report covering a year counts once whatever it reports, and a later report repeating an earlier claim counts again. Where reports form a series, say so and count by the attribute recording the reporting period.
- **Objectives that shifted.** Give the coder the version of the framework that applies to each period, or code against the current one and say so.

## Sources

The works cited for all the criterion pages are on [generic evaluation questions](generic-evaluation.md#works-cited). This page cites two OECD documents by page, each checked at the pages given.

OECD DAC Network on Development Evaluation (2019). *Better Criteria for Better Evaluation: Revised Evaluation Criteria Definitions and Principles for Use*. OECD. Approved by the Network on 20 November 2019 and adopted by the DAC on 10 December 2019. The definition of effectiveness, its note and Box 4 are on p. 9.

OECD (2021). *Applying Evaluation Criteria Thoughtfully*. OECD Publishing, Paris. [doi.org/10.1787/543e84ed-en](https://doi.org/10.1787/543e84ed-en). The effectiveness section starts on p. 52, with its elements for analysis on pp. 53 to 55 and its table of challenges on p. 55. Listed as [19] in the works cited.
