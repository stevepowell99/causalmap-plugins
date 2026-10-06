# Causal mapping

Causal mapping records who said what causes what, one causal claim per link with its quote and its source, and answers questions by selecting, tracing and counting those claims: it maps the evidence people give about causes, not the causes themselves.

Subsidiary page: [causal mapping in Rubicon](causal-mapping-in-rubicon.md), which says how a workflow codes, counts and traces causal claims, and what it leaves out. Written from the Causal Map garden (garden.causalmap.app), where each point below is argued at length; the page names are given so a person can follow them up.

## What it establishes

A link from C to E means that a source said, in some sense, that C influenced E. One link is one claim, with the words that carry it and who said it. A coder records the claim without judging whether it is true or how good the evidence behind it is. The garden's working paper on minimalist coding puts the first commitment as "We code claims, not causal truth" (page `minimalist`).

So a causal map is a repository of evidence about causes, and a question put to it is answered in the logic of evidence: is there evidence that X influences Z, directly or through other factors, from how many sources, and how reliable are they (page `logic-of-evidence`). Getting from that evidence to a conclusion about the world is a second step, which causal mapping does not take for you: "Causal mapping, as we practise it, is not a method of causal inference" (page `quality-assurance`). Other methods take that step with what the map assembles, which is why the garden calls causal mapping an "evidence broker" for QuIP, outcome harvesting, process tracing and contribution analysis rather than an evaluation method in itself (page `theses`).

What it cannot establish:

- **How strong an effect is.** Ten mentions of a link are ten pieces of evidence, not a link ten times as strong: "Strong evidence for a link is not evidence of a strong link" (page `granularity`). Nothing is done arithmetically on strengths.
- **What would have happened otherwise.** The counterfactual stays where the speaker left it.
- **How common something is in a population.** A link not mentioned is not a link denied, and the denominator for a share is usually unclear, so a count of sources is a floor on who holds a view, never a prevalence.
- **A high-stakes judgement on one link from a handful of passages.** Where that is the question, a method built for single-case inference, such as [process tracing](process-tracing.md), fits better.

## When it fits, and when it does not

It fits where there is a lot of narrative material from more than one source, where the differences between sources matter, and where nobody knows in advance where the system's boundary lies (page `when-to-use`). "What changed, and why, in the words of the people affected" is its home ground, and so is testing whether a theory of change matches what people describe.

It does not fit where the material is thin, where the question wants a precise or mathematical model, or where somebody only wants to sketch a plan without tracing each link to a source (page `when-not-to-use`). It differs from system dynamics, fuzzy cognitive maps and causal loop diagrams on exactly this point: those treat the diagram as a model of how the world works, where a causal map is a model of what was said, and treats every link as the same simple kind of claim so that it can take in thousands of claims from many sources (page `differs-from-related`).

A theory of change is itself a causal map of a kind, and also a political artefact, but it does not normally record which stakeholder believes which link. A causal map always does.

## What data it needs

Text in which people explain causes: interviews, especially those asking what changed and why; open survey answers; reports and reviews. A study that wants to compare groups needs each source's group recorded. Where the question concerns attribution to a programme, material gathered without naming the programme to respondents (QuIP's blindfolding) reduces confirmation bias and makes an unprompted mention worth more.

## The steps in practice

The garden splits the work into three tasks: gather the material, code the claims into a table of links, and answer questions by transforming that table (page `three-tasks`).

**Coding.** Each link is a cause label, an effect label, the quote and the source. The minimalist rules keep the coding simple enough that coders agree on most explicit claims:

- Record only that C influences E, with no strength, polarity, necessity or sufficiency.
- Code what the speaker says on the surface, not what they might mean.
- Code no absences, and no hypotheticals or wishes.
- Never add a step the source did not state, however tempting when another source mentioned it (page `direct-links`).
- A factor is a proposition, not a variable: "Poverty" and "Wealth" are separate factors.
- A label should make sense with "more of this" in front of it ("Training courses delivered" rather than "Training courses"), and should stay close to the speaker's words without generalising away the content ("Increased household income" rather than "Economic improvement").

Two structures in the labels carry most of the later analysis:

- **Hierarchy.** `General concept; specific concept` means the coder is content for the specific link to count, in summary, as evidence for the general one, so a map can be zoomed out to the first level. A parent must itself be a causal factor, not a theme, and must not mix desirability within it (page `zoom-filter`).
- **Opposites.** A `~` prefix marks a factor as the opposite of another (`~Smoking`), so the two can later be shown as one factor with the flipped links marked. Nothing is lost by combining them; "We don't have evidence for an aggregated strength; we have aggregated evidence for a strength" (page `combine-opposites-filter`).

**With a codebook or without.** Coding against a theory of change's factors tests that theory; coding in the respondents' words finds what nobody anticipated. The garden's practice is mostly to code first without a codebook, since a codebook frames what a coder sees, and there are settings in between: a fixed first level with free detail beneath it is the usual compromise (pages `labels-creative`, `ai-coding`). Free labels leave a vocabulary problem, with one idea under many names, so open coding moves the hard work into recoding rather than removing it.

**Coding with AI.** The task given to a model is narrow and checkable: find each passage saying one thing influenced another, and record the cause, the effect and the exact quote. The garden's experiments (page `coding-experiments`) found that chunk size mattered more than any prompt change, that models stop once they have a plausible handful unless every segment has to be accounted for, that a model judging another model's coding is optimistic and is a relative signal only, and that one prompt serves every model. The prompt is the codebook in another form, so sharing it is sharing the method.

**Answering questions.** Each question is a chain of filters over the links table, and the order is part of the analysis (page `filter-ordering-rules`):

1. Select the sources or factors the question is about.
2. Trace paths from and to the factors named, before anything rewrites a label: "trace first, and simplify afterwards".
3. Combine opposites, above anything that replaces a label.
4. Zoom, collapse or recode labels.
5. Keep the most frequent links or factors last, so they are the most frequent within what the question selected.

Two counts sit on every link. The citation count is how often a link was said; the source count is how many sources said it. Both are "evidence-volume measures, not effect-size measures" (page `bundles`), and the citation count inflates whatever a talkative source repeats, so prefer sources where a few respondents are prolific.

**Paths.** A path from A to C through B, assembled from one source's A to B and another's B to C, is not a claim anybody made. "Transitivity is perhaps the single most important challenge for causal mapping" (page `transitivity-trap`): the two sources may mean different things by B, or speak of different contexts in which the chain does not hold. Thread tracing counts a chain only where one source states every step of it. People seldom report chains longer than four steps, so a longer path is usually stitched.

**Groups.** Draw a map per group, or compare how many sources in each group mention a link against each group's size. Differences found this way point where to look; they are not proof.

## Drawing a map

One arrow per link bundle, with its width by citations or sources; factors as boxes; drivers to the left and outcomes to the right where the structure runs one way, because a circular layout makes everything look like one feedback loop (pages `bundles`, `linearity-first`). An unfiltered map of every link is "a bewildering and useless 'hairball' that includes everything but highlights nothing" (page `evaluation-questions`). Several small maps, each chosen openly to answer one question, say more than one large one, and a map too busy to read calls for a narrower question rather than more formatting (page `howto-map-formatting`). In the Causal Map app a report map shows about a dozen factors and thirty links by default.

Where a coding uses a catch-all value for what fits nowhere, a single "other" factor at both ends of links draws paths nobody stated (A to other to B) and a loop from other to itself. Keep a catch-all at a cause apart from one at an effect: "Other causes" and "Other effects" are just as uninformative, and they do not mislead.

## Traps

- **The transitivity trap**: reading a stitched path as a story somebody told. Say which paths are stitched, or trace within sources.
- **The identity trap**: treating two sources' uses of the same label as the same thing. Zooming out makes both traps worse, since it merges more labels into one.
- **Evidence read as strength.** A thick arrow is much said, not a strong effect.
- **Counts that depend on granularity.** How many links a factor has depends on how finely it was coded, so network statistics are fragile and comparisons across codings mislead.
- **Selection.** Choosing which map to show, or cutting to the most frequent links, can drop the negative story or the unintended consequence. Say what was cut.
- **Filters in the wrong order**, especially frequency before tracing, and combining opposites after the labels have been replaced, which fails silently.
- **Opposites merged by clustering.** Similarity measures treat employment and unemployment as near neighbours, so a clustering can put opposed factors in one group unless it is told not to.
- **Invented intermediate steps**, added to one source's story because another source told a longer one.

## What good looks like

- Every link traces to a quote and a source, and a reader can follow any arrow on a map back to the words.
- The codebook, or the absence of one, is stated, with how labels were grouped and what was left ungrouped.
- Each map answers a stated question, with its filters and their order printed beside it.
- Counts say whether they are citations or sources, and a finding about a path says whether its steps came from one source or several.
- Nothing is claimed about strength, counterfactuals or prevalence that the evidence cannot carry.

## Sources

- Powell, S., Copestake, J., & Remnant, F. (2024). Causal mapping for evaluators. *Evaluation*, 30(1), 100-119. https://doi.org/10.1177/13563890231196601
- Remnant, F., Copestake, J., Powell, S., & Channon, M. (2025). Qualitative causal mapping in evaluations. In A. Kaehne & J. Feather (Eds.), *Handbook of Health Services Evaluation* (pp. 207-227). Springer. https://doi.org/10.1007/978-3-031-87869-5_12
- Powell, S., & Caldas Cabral, G. (2025). AI-assisted causal mapping: a validation study. *International Journal of Social Research Methodology*, 1-20. https://doi.org/10.1080/13645579.2025.2591157
- Powell, S., Caldas Cabral, G., & Mishan, H. (2025). A workflow for collecting and understanding stories at scale, supported by artificial intelligence. *Evaluation*, 31(3), 394-411. https://doi.org/10.1177/13563890251328640
- Powell, S., Larquemin, A., Copestake, J., Remnant, F., & Avard, R. (2023). Does our theory match your theory? Theories of change and causal maps in Ghana. In L. Simeone et al. (Eds.), *Strategic Thinking, Design and the Theory of Change*. Edward Elgar.
- Copestake, J., Morsink, M., & Remnant, F. (2019). *Attributing Development Impact: the Qualitative Impact Protocol case book*. Practical Action Publishing.
- Axelrod, R. (1976). *Structure of Decision: The Cognitive Maps of Political Elites*. Princeton University Press.
- Eden, C., Ackermann, F., & Cropper, S. (1992). The analysis of cause maps. *Journal of Management Studies*, 29(3), 309-324.
- Laukkanen, M. (1994). Comparative cause mapping of organizational cognitions. *Organization Science*, 5, 322-343.
