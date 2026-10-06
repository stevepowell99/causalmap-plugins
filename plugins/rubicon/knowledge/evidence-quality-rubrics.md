# Evidence quality rubrics

Tom Aston and Marina Apgar's *Quality of Evidence Rubrics for Single Cases* (2023) sets out criteria for appraising how good the evidence behind one causal claim is, each written as a five-level rubric. It was written for a person reading a case and deciding whether to believe it.

Rubicon can answer several of those criteria from its own run record before anybody reads anything, which is what makes the framework worth building on rather than citing. This page says which ones, how to brief the review that scores them, and where Rubicon stops.

Back to the [knowledge base index](README.md).

## What it establishes, and what it does not

The framework appraises evidence, never a programme. It says how much confidence a claim deserves given how the material behind it was gathered, by whom, and how well it rules out other explanations. Aston and Apgar are explicit about the boundary: this is internal validity within a single case, mainly qualitative, mainly for theory-based and case-based work such as contribution analysis or realist evaluation. They exclude appraisal of a whole evidence base at portfolio level. Only one of the eight touches external validity.

So the framework fits a Rubicon run almost exactly. One question, one corpus, one verdict.

## The criteria

Eight are presented, in this order, each as a table of five levels. The wording below is compressed; the source document carries the full descriptors.

| Criterion | What it asks | Level 3 reads |
|---|---|---|
| Plausibility | Is the account connecting intervention to outcome clear, logical and temporally consistent? | Clear, logical, temporally consistent, a likely association |
| Uniqueness | How specific is the connection, and what else could explain the outcome? | Ambivalent connection; the claim is as likely valid as invalid |
| Representation | Whose perspectives were included, and did they inform the finding? | Priority groups elicited indirectly, by researchers |
| Triangulation | How many independent lines of evidence corroborate the connection? | Multiple lines of evidence, meaning source types, corroborate |
| Transparency | Do we know where the evidence came from, who collected it and how? | Various sources clearly identified and explained |
| Independence | How far are the sources free of incentives to misreport? | Third parties, partners or independent evaluators; bias unknown |
| Transferability | How well does the case fit another population, setting or period? | Support factors identified; limited similarities |
| Ethics | Was the evidence obtained in a way that neither harmed people nor distorted what they said? | Direct consultation, formal consent, confidentiality secured |

The authors expect you to take a subset rather than score all eight, chosen at the outset with the evaluation's stakeholders. Their own count wobbles between five, seven and eight across the document, which reinforces the point: it is a menu.

### Do not set one target level across the criteria

Aston and Apgar suggest aiming for level 3 to secure credibility. Read the tables and that advice breaks on two of them.

Uniqueness at level 3 says the connection is ambivalent and the claim is as likely to be invalid as valid. Independence at level 3 says the evidence may have come from partners or third parties and that potential bias is unknown. Neither is a passing grade in any ordinary sense. Level 3 on plausibility or triangulation means something a reader would accept; level 3 on uniqueness means the evidence did not settle anything.

Set the target per criterion. For uniqueness and independence, level 4 is the first level that carries a claim. The authors say elsewhere that uniqueness should outweigh plausibility when building confidence in contribution, which points the same way.

## What Rubicon can score from its own record

These are answerable from what a run already stores, without reading the text again. That is unusual. A reviewer scoring a case study normally has to reconstruct all of it from a written report. Mostly they cannot.

A criterion about the method rather than the material is answered from the record and cites no quotation: the reviewer reads what the resolved workflow, each step's record and the model calls behind them say happened, and where the record does not say, the answer is that it does not say. Use this for every criterion in this family, because demanding a quotation for a claim about method refuses a fair question, and whatever quote gets cited to satisfy the demand will be irrelevant.

**Transparency, on the analysis side.** The workflow states which documents are read, how they are chosen, what each step is asked and what standard decides the verdict. Every step's prompt and every model call is stored. Every quotation is located in its document or flagged, so the limitations paragraph writes itself from numbers rather than from memory. Every tabulation carries its own base: what it counted, out of which documents, and which documents it left out because the sample did not draw them. A workflow shown to the evaluator before the run is the protocol the criterion's top level asks for.

Split the criterion in two when you use it here. Transparency of analysis is recorded in full and a Rubicon run sits at the top of it by construction. Transparency of data collection is unknown to Rubicon, which reads documents somebody else gathered and knows nothing about how they were gathered. Scoring one criterion across both halves would hide the half we cannot speak to.

**Coder triangulation.** Shadish's addition to Denzin's four is the one type of triangulation Rubicon measures rather than asserts. On a code step whose column has fixed values, a second coder of another model family reads the same documents, and the two sets of rows are reconciled value by value: a value both place stands, and a value only one places goes to an adjudicator who rules it from the whole document. Two differently worded coding prompts say how much the answer depends on the wording. The same prompt sent to both coders says how much it depends on nothing at all. A value one coder placed and the other did not is silence rather than disagreement until the adjudicator rules it, and the step's record says which reading was silent.

Say plainly what that is worth. Two runs of one model are not two investigators, because they share everything that produced them. Agreement between them is evidence about stability rather than about reliability in Denzin's sense. Two different models are a little better and still not two people. So a second coding bears on coder triangulation and never on investigator triangulation. A report that conflates the two claims more than the run supports.

**Coverage, as the arithmetic half of representation.** A sample step draws with a seed and can stratify by a named document attribute, the step's record names the documents it drew, and every tabulation names the documents its base left out because the sample did not draw them. So the proportion of the available corpus that was read is a number rather than an impression.

## What Rubicon can score if the coding is designed for it

These need an item or a column fixed before the run. None needs new machinery.

**Uniqueness is a plan rather than a criterion scored afterwards.** X is the claim, Y is the rival reading, both searched in the same passes over the same text (skill `rival-explanations`), and the verdict asks which the material better supports on count, bearing and certainty together. Scoring uniqueness at the end of a run that only ever looked for X measures how hard you looked. Searching the rival with the same effort as the claim is what makes the criterion answerable at all, and it has to be built into the code steps' columns and prompts rather than applied to their output.

Where the rival is not a rival, say so. Both readings can hold of different people, which is the commonest way a uniqueness score misleads.

**Independence, through a second count rather than a judgement.** Record who is speaking and their relation to the intervention (programme staff, partner, funder, participant, external, not stated), as a column of the documents where each document has one speaker, then count twice: once out of all cases, once out of the cases with no connection to the programme. If the verdict holds in both, independence did not decide it. If it changes, the finding rests on people with an incentive to report it, and that is worth more than any level on a five-point scale.

Aston and Apgar's list of the incentives at work is the reason to bother: staff describing what they were closest to, partners saying what keeps a contract, evaluators overweighting the intervention because it is what they were hired to look at. Public statements carry more positive bias than confidential ones, so where a source sits on that spectrum belongs on the source rather than in a footnote.

**Data triangulation, which is not a document count.** The temptation is to read a count of documents as the criterion: three documents corroborate, so call it level 3. Resist it. Denzin's data triangulation is about kinds of evidence, primary against secondary, testimonial against administrative against observational, and about proximity to the events described. Three interviews with three people from the same office are one line of evidence however the count reads.

What a count of separate cases does establish is the bottom of the scale, since one case carrying the claim is the paper's level 2 whatever else is true. Above that the criterion needs the source type, and the type has to reach the reviewer: a column of the documents giving each one's kind does that, and a count split by it shows which kinds of evidence carry the claim.

**Support factors, for transferability.** Most of the transferability criterion is outside a single-corpus run, since it compares context A with context B and only A is in the material. One part does map. Cartwright's support factors and derailers, and the assumptions a theory of change makes about them, can be items in the codebook, and a plan ending in that table is finished: it answers what the material can answer and leaves the transfer to a person. Somebody then takes the table to the question of whether the case travels.

## What sits outside

**Ethics.** Consent, confidentiality, ethical approval and situated practice are properties of how the material was gathered. Rubicon arrives afterwards and can neither observe nor improve any of it. Do not put an ethics criterion in a Rubicon verdict, because a model scoring it from transcripts would be guessing.

One part of the criterion is Rubicon's own problem, and it runs against the design. Rubicon's central rule is that a claim must cite the quotes it rests on. But a verbatim quote from a small population identifies its speaker, and the more traceable the chain, the more identifying it becomes. Anonymising the quote breaks the trace; keeping it risks the confidentiality the speaker was promised. There is no setting that resolves both, so whoever plans a run over sensitive material has to decide which they are giving up, and say so in the report. Worth settling in the plan rather than leaving to the moment somebody publishes.

**Representation above level 3.** Levels 4 and 5 describe priority groups generating their own evidence and running their own analysis. A run over transcripts collected by evaluators cannot reach either, whatever the analysis does afterwards. So a Rubicon run has a structural ceiling of level 3 on representation, and reporting that ceiling as a finding is more use than scoring the criterion.

## As a plan

The second judgement is a separate reading of a finished run's own record: once a workflow has answered the question, whoever is asked how much the answer deserves to be believed reads the run's resolved workflow (every step as it actually ran, with the reasons for each), each step's record (the rows and their quotations, each column's definitions, every tabulation cell with its base, and the write step's draft, review and trail), and writes a verdict at the five levels this page sets out, each with a description a reader could dispute rather than a bare number.

Transparency of analysis is answered from the record rather than from the material: whether the workflow was shown to the evaluator and priced before any document was read, which steps ran and on what settings, and what each one's reasons were. Triangulation, independence, plausibility and representation need a fresh reading of a sample of rows: how many kinds of evidence corroborate the claim, whether the claim survives when documents with an interest in it are set aside (which needs a document attribute recording who is speaking, decided when the workflow was designed), and how far a second coder and an adjudicator ran on the coding and where they disagreed.

The run then carries two judgements: the write step's answer to the question and this separate verdict on how much of it to trust, both traceable to the same quotations, the second written without seeing how the first was received.

A trial is less useful here than elsewhere, since the rubric is applied once, at the end, over a finished record. What is worth doing early is checking that the workflow's columns record what the rubric will need, the speaker's relation above all, since a column not coded at the time cannot be reconstructed once this review is reading.

The levels, and three of the criteria written out, after Aston and Apgar. Ethics is left out because a model scoring it from transcripts would be guessing, and transferability because it compares two contexts and only one is in the corpus; both are reported in prose instead.

- **The levels.** 1: the criterion is failed in a way that undermines the claim. 2: partly met, with a weakness a reader should discount for. 3: the middle of the paper's scale, acceptable on some criteria and an explicit shrug on others, so read it against the criterion rather than as a general pass. 4: met to a standard a sceptical reader would accept. 5: the strongest standard this criterion describes.
- **Triangulation.** How many independent lines of evidence corroborate the claim, counting kinds of evidence rather than documents, and was a second coding run and compared?
    - 5: several kinds of evidence from separate studies or periods corroborate the claim, and a second coding was compared with its disagreements reported.
    - 4: several kinds of evidence corroborate the claim and the sources closest to the events are among them.
    - 3: more than one kind of evidence corroborates the claim, meaning source types rather than several documents of one type.
    - 2: one case, or several of one kind, carries the claim.
    - 1: nothing corroborates the claim, or other passages contradict it.
- **Transparency of analysis**, answered from the record. Does the record show which documents were read and how they were chosen, what each coder was asked, how much of each document it accounted for, which quotations could not be located, and what base every count was out of?
    - 5: all of it is in the record, and the plan was agreed before the run, so the standard demonstrably predates the evidence.
    - 4: all of it is in the record. The plan was written after somebody had seen how the material fell.
    - 3: documents, sample and briefs are recorded. Coverage or the unlocated quotations are missing.
    - 2: the documents are identifiable and how they were read is not.
    - 1: a share is reported without its base, or part of the record is absent.
- **Independence.** Do the cases carrying the claim have incentives to report it, and does the claim survive when those cases are set aside?
    - 5: the speaker's relation to the programme is recorded, the claim holds among cases with no connection to the programme, and the remaining bias is named.
    - 4: the speaker's relation is recorded and the claim holds among unconnected cases.
    - 3: the speaker's relation is recorded. Whether the claim depends on connected sources is not tested.
    - 2: the claim rests mostly on people with an interest in it, which is stated.
    - 1: the speaker's relation is not recorded, so who had an incentive to say this is unknown.

## Where Rubicon falls short

**Nothing thresholds the record by rule.** The counts are exact and so is the agreement between two codings, but a verdict on method is a model reading those numbers back, and a model reading numbers back is a weaker instrument than arithmetic. A threshold on a count is applied in the answer's own words rather than by code.

**Kinds of evidence are countable only where the documents carry them.** A case is one document, or the documents the index gives one `case`, so two interviews with the same person corroborate each other unless the index says they are one case. The kind of each document has to be a column of the documents before a count can split by it.

**No weighting across criteria, which is correct.** Aston and Apgar say the criteria carry different weight, that uniqueness should outweigh plausibility, and then leave aggregate scoring to the reader. Rubicon does the same: nothing averages verdicts. Keep it that way. A single number over six criteria hides exactly the disagreements a reader needs, and the paper's own refusal to supply one is the strongest thing in it.

## Traps

**Scoring the evidence rubric with the same model that produced the evidence.** The reviewer reads quotes the coders selected, so a reading that missed contrary material produces a record in which contrary material is absent, and the criterion scores the absence as a good result. Write two criteria to catch this, one asking whether contrary evidence was sought and one asking what it showed, split so that nobody looking is distinguishable from looking and finding nothing; asked as one, they fuse two findings a reader needs apart. It only works if the coders were actually briefed to search for the contrary case.

**Reporting a high transparency score as though it were a high evidence score.** A run can be fully recorded and rest on two self-interested interviews. Transparency is about whether a reader can see what happened, and it says nothing about whether what happened was any good. The criterion Rubicon scores best is the one that carries least.

**Treating run-to-run agreement as reliability.** Covered above under coder triangulation, and worth repeating because the number is easy to produce and reads like an inter-coder number.

**Applying the framework to a portfolio.** The authors exclude it. The exclusion holds: these rubrics appraise the evidence behind one claim about one case. Scoring twenty outcome statements and averaging produces a number about nothing.

## When to say the framework does not apply

Somebody asking whether a body of evidence across a programme is strong enough wants a different instrument, and this one will give them a plausible answer to a question it was not built for.

Somebody asking Rubicon to score ethics, or representation at levels 4 and 5, is asking about data collection that happened before the corpus existed. Report the ceiling instead, and say why it is a ceiling.

Somebody wanting a single quality score to put in a table is asking for the thing the authors declined to provide. Give them the six bands, and the sentence saying which two matter most for their question.

## Sources

Aston, T. and Apgar, M. (2023). *Quality of Evidence Rubrics for Single Cases*.

Works cited within it, listed here because they were read in its bibliography rather than in the original: Denzin on the four types of triangulation (1970); Shadish on coder and analyst triangulation (1993); Beach and Pedersen on process tracing (2019); Mayne on contribution analysis (2019); Cartwright on support factors and derailers (2020); Lincoln and Guba on transferability (1985); Guest et al. and Hennink and Kaiser on saturation; Davies on weighted checklists (2020); UNEG's ethical guidelines (2020). Check any of them before citing it in a deliverable.
