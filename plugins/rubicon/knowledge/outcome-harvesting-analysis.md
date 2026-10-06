# Answering evaluation questions with a harvest

Step 5 of an outcome harvest: what a finished outcome set can and cannot answer, the denominator problem, the coding frame, counting, trajectories, and combining the harvest with other methods. It is the thinnest part of the published guidance, and the part where most harvests disappoint their commissioners, because the set arrives and nobody has decided in advance what it can be asked.

Back to [outcome harvesting](outcome-harvesting.md).

## What an outcome set actually is

A collection of verified statements about changes that happened, each with attributes, a source, and a claimed contribution.

Formally it is a purposive, non-probability collection of positive-report instances. It records what somebody found by looking. Whatever it contains is a joint product of what occurred, what got written down, who was asked, who replied, and how skilled the harvester was. All five vary. Only the first is about the programme.

Everything below follows from that one sentence.

## The denominator problem

**An outcome set has no natural denominator.** You have a numerator, the outcomes found. There is no population of outcomes-that-occurred to divide by, and there never will be, because the population is unbounded and unobservable.

So three sentences that appear in most harvest reports are meaningless:

- "The programme achieved 78 per cent of its outcomes." Per cent of what.
- "60 per cent of outcomes were policy changes." True of this harvest. It is a fact about search effort as much as about the world. Policy changes get gazetted; changes in how a team runs its week do not. So the finding partly measures which changes leave a paper trail.
- "Outcomes increased by 40 per cent in year three." That is usually the harvester getting better at harvesting.

This is not pedantry. Every commissioner reads a percentage as prevalence, and a harvest cannot supply prevalence.

### The denominators you can actually use

Five, in ascending order of usefulness.

1. **Outcomes harvested (n statements).** Legitimate for describing the set. Never for any claim about the world. Always report the raw n.
2. **Social actors (n distinct actors who changed).** Better, because it does not reward the talkative. One partner who describes eleven changes counts once. This is the right default for any question about reach. A tabulate step counts documents or rows, never a distinct value spread across several of them, so where one actor is named in three documents a count by actor gives a document total for that actor rather than the single actor the question wants. A true actor count needs a person to read the per-actor cells of a full tabulation, which drops no combination for being zero, and say how many are non-zero, since nothing in the engine counts cells. See [what the engine still leaves to a person](outcome-harvesting-in-rubicon.md#as-a-plan).
3. **Sources read (30 of 75 documents).** Tells you about search effort. Occasionally worth reporting for that reason alone.
4. **Time periods (outcomes per quarter).** A rate, comparable within one programme over time if the harvesting effort was constant. It rarely was, so state the effort alongside it.
5. **A declared external frame.** The 40 partner organisations in the grant agreement. The 12 districts. The 22 fellows on the cohort list. This is the one denominator that supports a real claim: "of the 40 partners, 17 are recorded as having changed a practice."

**The rule that follows, and it is the single most useful sentence on this page.** A percentage means something only when the denominator is a set you set out to look at all of. That set has to be built in step 1 of the harvest design, because at analysis time it is far too late. If the commissioner wants a proportion, settle during inception which bounded population it will be a proportion of. Cover that population exhaustively. Then say in the report that you did.

The corollary is worth saying to a commissioner early. Asking a harvest for a percentage converts it into a census of a defined frame, which costs more and constrains the search. That is a legitimate design and it is a different design.

## What a harvest can answer

- **What changed, for whom, where and when.** The primary deliverable. Often the entire deliverable, and enough.
- **What kinds of change happened, and where they cluster.** Name the base every time.
- **Which parts of the system show change and which show none among the actors covered.** Absence is only interpretable within a frame somebody covered.
- **Whether change reached beyond direct partners.** Second and third order outcomes. This is a strong OH answer and one few other methods produce cheaply.
- **What went wrong, backwards or sideways.** Only if negatives were collected properly.
- **What the programme is said to have done, by whom, in what pattern.** The contribution-type distribution described on the [substantiation page](outcome-harvesting-substantiation.md#the-contribution-claim).
- **Whether outcomes appeared where the theory of change predicted, and where they turned up that it did not.** See below.
- **Sequences.** Which changes preceded which, where the dates are good enough to tell.

## What it cannot answer

State these in the inception report, and again in the limitations paragraph, because they will be asked.

- **Did the programme cause this.** No counterfactual exists anywhere in the data.
- **How much change occurred.** No denominator, no baseline, and positive-report bias throughout.
- **Would it have happened anyway.** Nothing in a harvest addresses this.
- **Is the programme value for money.** Outcome counts are not commensurable. One policy change is not a tenth of ten meeting attendances, and adding them up implies it is.
- **Did the programme meet its targets.** Forcing a harvest into a logframe produces a poor indicator report and destroys the method's one real advantage, which is finding what nobody predicted.
- **Which of two programmes did better.** Different harvesters, different access and different document sets produce different counts. Comparing harvests compares harvests.
- **Is this outcome significant.** Not from the set alone. Significance is an evaluative judgement. It needs a rubric whose criteria the harvest users agreed.

## Building the coding frame

Once the set is verified, code every statement on every dimension. Miss some and the crosstabs carry unequal bases, which makes all of them unreadable.

Derive the categories from the statements themselves in a first pass. Reconcile with the theory of change afterwards. Start from the logframe's categories instead and everything unpredicted lands in "other" and is never looked at again, which is the exact material the harvest exists to find.

Dimensions worth having in almost every harvest:

| Dimension | Values |
|---|---|
| `actor_type` | government, CSO, private, donor, community, media, academic |
| `level` | individual, team, organisation, network, sector, policy |
| `change_type` | formal rule, practice or procedure, resource allocation, relationship, discourse, capability in use |
| `direction` | positive, negative, mixed, against the users' stated intent |
| `intended` | intended, unintended |
| `order` | first (direct partner), second, third |
| `persistence` | one-off, repeated, institutionalised |
| `contribution_type` | funded, convened, drafted, evidenced, trained, brokered, legitimised, advocated |
| `substantiation` | documentary, independent testimony, actor only, unsubstantiated, contested |
| `date`, `location` | as recorded |

Two of these carry most of the analytical weight and are the two most often skipped: `order`, because it answers the reach question that other methods cannot; and `direction` crossed with `intended`, because the unintended-positive and intended-negative cells are where the interesting material sits.

## Counting sensibly

- **Count actors for any reach question.** Count statements only when describing the set.
- **Report the raw n beside every percentage**, and the base in the same sentence.
- **Do not rank categories by count without saying what count reflects.** Visibility differs by change type. A ranking by frequency partly ranks documentability.
- **Use crosstabs.** A single distribution rarely says much. Change type by actor type. Order by contribution type. Direction by level. The finding is usually in the cross. Crosses also expose empty cells, which are informative wherever the frame was covered.
- **Where a cell holds fewer than about five statements, print the statements.** A percentage over four cases misleads. The four cases themselves are more use to a reader.
- **Report the substantiation status alongside every count.** "17 actors, of which 11 independently substantiated" is a different claim from "17 actors".

## Grouping into trajectories

The most useful analytical move, and the one that turns a table into something a commissioner reads.

Group outcomes into a small number of **change trajectories**: sets of outcomes involving overlapping actors, over time, that plausibly form a sequence. Each becomes a short dated case of a few hundred words. Three to six trajectories is the right number for a report body.

How to build one:

1. Sort the set by actor and by date.
2. Look for outcomes where one actor's change is named in another's account. Also where dates and subject matter line up.
3. Write the sequence with dates, naming the actors, keeping the contribution claims attributed.
4. Note where the sequence has a gap, meaning a step you would expect and did not harvest.
5. Then, and only then, compare with the theory of change.

That ordering matters. Building trajectories from the outcomes and their dates finds sequences nobody predicted. Sorting outcomes into theory-of-change boxes finds only what the theory already contained. The rest gets discarded without anybody noticing.

A trajectory is also the unit you would hand to process tracing if a causal question has to be answered, so building them well makes the next phase cheaper.

## Testing a theory of change with a harvest

Legitimate, and limited. Be precise about which of these you are doing.

**What you can do.**

- Check whether outcomes appear at each link the theory predicts. Presence at a link is supporting evidence of modest strength.
- Check for outcomes the theory did not predict at all. This is the strongest test a harvest supports. Unpredicted outcomes are positive evidence that the theory was incomplete, and search failure cannot explain them away.
- Check the ordering of dates against the theory's ordering. A predicted intermediate outcome dated after the outcome it was supposed to produce is a real problem for the theory. Report it.

**What you cannot do.**

- Conclude that the theory held. The evidence is presence-only and uncontrolled.
- Treat absence at a link as disconfirmation. Nobody may have looked there. Absence is interpretable only where the harvest covered a declared frame relevant to that link. Even then it is weak.

Write the strength of each conclusion into the sentence. "Outcomes were harvested at every link except the third" is reportable. "The theory of change was validated" is not.

## Combining with other methods

A harvest supplies verified results. Every causal question needs something else on top, and that something else always means more data collection. Say so when the design is agreed, not when the draft report comes back.

**With contribution analysis.** The natural pairing. OH supplies the observed results and the raw contribution claims. Contribution analysis supplies the structure: set out the theory, gather evidence on each link, assemble the contribution story, and then test the rival explanations. That last step is the one doing the work. A harvest contains almost nothing that speaks to it, because harvesters ask what contributed rather than pursuing what else could account for the change. Budget for it separately. John Mayne is the reference for the approach.

**With process tracing.** Select two or three outcomes that carry the weight of the evaluation and treat each as a case. Specify the rival explanations up front. Then go back for evidence that discriminates between them: a hoop test needs evidence whose absence kills a hypothesis, a smoking gun needs evidence whose presence confirms one. **A harvest will not have collected that evidence.** Harvesting collects reports that a change occurred. Process tracing needs evidence that separates competing mechanisms, which usually sits in different documents and with different informants. Treating an existing harvest as a process-tracing dataset is the standard mistake. It produces a case narrative dressed in evidence-test vocabulary with no evidence tests in it. Beach and Pedersen is the reference for the tests.

**With causal mapping and QuIP-style causal coding.** These are complementary rather than competing, and the combination is underused. An outcome statement usually contains a short causal chain in the informant's own words. The flat outcome table throws the chain away. Coding the same sources causally gives you the paths between changes; harvesting gives you the verified endpoints with dates and independent corroboration. Where both run on one corpus, code causally first, because path tracing needs the original wording before any relabelling. Harvest from the same passages afterwards. The result is an outcome set whose statements can be located in a causal map, which answers "how did this come about" and "did it really happen" at the same time.

**With rubrics.** A harvest can be judged against an evaluative rubric, and it must be a rubric whose criteria are worded over a base you actually have. "Of the 40 partners, how many changed a practice" works. "What share of outcomes were significant" does not, because the denominator is the harvest. Agree the criteria before the analysis. Record when they were written relative to the evidence.

**With most significant change.** MSC selects and deliberates on stories through a participatory filter; OH verifies changes through independent sources. Running both on one programme produces two sets that will not match. The mismatch is informative rather than a fault. Do not merge them into one table.

## Writing it up

- The complete outcome table goes in an annex. All of it, including dropped statements with the reason, and substantiation status per row.
- The body carries three to six trajectories with dates and named actors.
- One paragraph states the coverage: what was searched, over what period, who was asked, who was not, plus the response rate on substantiation.
- Every percentage names its base in the same sentence.
- Contribution appears as attributed claims throughout.
- Never present outcome counts as programme performance.

More on reporting, and the failure modes to check a draft against, under [Traps on the main page](outcome-harvesting.md#traps).

## As a plan

Once outcomes are drafted rows, classification is either columns on that same code step or a second code step over the harvested table: `actor_type`, `level`, `change_type`, `direction`, `intended`, `order`, `persistence` and `contribution_type` are all closed sets, so each is a nominal or ordinal column with its values spelled out, derived from the statements themselves in a first pass and reconciled against the theory of change afterwards, never the other way round, so unpredicted material is not filtered out before anybody looks at it.

A tabulate step gives every crosstab this page wants (change type by actor type, order by contribution type, direction by level), each cell stated out of its own base: documents or rows for outcomes when describing the set as it stands. Where a tabulation is by more than one coded column, a cell can also be stated within a group another column defines (`<cell>.within.<column>`), which is the mechanism behind "of the households whose health improved, 13 of 15" rather than 13 of every household read. What tabulate cannot do is turn a document or row count into a count of distinct actors, which stays the gap this page's denominator section already names: the base an outcome harvest most wants, a declared external population such as the forty partner organisations in the grant agreement, is not a document attribute any tabulate step can read, so the write step has to state that frame, and whether the search covered it, as a sentence rather than a computed share.

Building trajectories has no piece of its own: it is the write step's own synthesis, reading the coded rows and, within its reading budget, the documents themselves, for one actor's change named in another's account, and writing the sequence with both cited. That is prose composed from what the write step is given, not a count any tabulate step produces, and a workflow should put it after the crosstabs in its instructions rather than instead of them, matching the ordering this page insists on: theory-of-change comparison comes last, so an unpredicted sequence is found before it is read into the theory's own boxes.

Where the question is causal rather than descriptive, a workflow should say under `cannot_answer` that this method's rows do not support a causal conclusion and name the further work this page proposes, contribution analysis or process tracing, rather than having the write step read one into the tables anyway.
