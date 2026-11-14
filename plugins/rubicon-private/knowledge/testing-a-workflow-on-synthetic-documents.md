# Testing a workflow on synthetic documents

How to design an analysis and show that it can tell success from failure having seen little or nothing of the real documents, by running it on two small made-up corpora whose right answers are known; read it when a verdict has real consequences, when an evaluator wants to fix the analysis in advance as in a pre-registration, or when the real documents are not yet collected or not yet allowed to be read.

Related pages: [evaluative rubrics](evaluative-rubrics.md), since the test needs a rubric agreed first; [process tracing in Rubicon](process-tracing-in-rubicon.md), on why a plan fixed before the reading matters; [probative value](probative-value.md), on findings that hang on one or two documents.

## What it establishes

That a workflow discriminates. Write one corpus in which the programme passes the evaluator's rubric and one in which it fails, run the workflow on both without changing it, and see whether it reaches a pass on the first and a fail on the second. A workflow that cannot tell them apart is found out for the price of two small runs, before it meets any real document. One that can is a fixed plan with evidence that it works, dated before the real documents were read: a pre-registration with a test attached.

What it does not establish: that the workflow is valid on the real documents, that real people talk the way the made-up ones do, or that the rubric is the right standard. Made-up documents are evidence about nothing. They are never counted as cases or quoted in an answer about the real programme.

## When it fits, and when it does not

It fits a summative verdict against a rubric: whether a programme was good enough, whether to fund, scale or stop it, pass or fail against targets. It fits too wherever the evaluator wants to show the analysis was settled before the evidence was seen, and wherever the real documents arrive late: the workflow can be built and tested during the design phase, while interviews are still being planned.

That last case has a second use. If the made-up interviews have to be written in a way the real topic guide would never produce for the workflow to work, for instance because the workflow needs people to say what changed since the programme and the guide never asks, the test has found a fault in the data collection while it can still be fixed.

It does not fit exploratory or formative questions, or questions whose categories are meant to come from the documents themselves. The test needs a known right answer, and an inductive analysis has none to plant.

## Two starting points

**Nothing seen.** Write the corpora from the evaluator's description of the setting: what the programme is, who would be interviewed and where, what was meant to change, and the topic guide if there is one. This gives the strongest claim, since the workflow is provably fixed before any real document was read. The cost is realism: made-up talk is tidier and more on topic than real talk, so a workflow can pass the test and still struggle with rambling, contradictory or off-topic interviews.

**A little seen.** Read two or three real documents as a model for how people there actually talk, for tone and structure only, never copying a passage or a person. The corpora are more realistic. Ask first: a data agreement may not allow it, and reading real documents before the plan is fixed weakens the claim of pre-registration. Record which documents were read, and say so in the report.

## The steps in practice

1. **Settle the question and the rubric** with the evaluator, as for any summative question. The corpora are written to fall either side of the rubric, so it comes first.
2. **Write a key before any document.** It gives the verdict each corpus is written to reach and, for each document, what it shows and a brief of two or three sentences. Keep the facts the question's comparisons use, such as site or role, the same across both corpora, so they differ in what happened and not in who was asked.
3. **Make every brief clear-cut.** Each brief falls clearly on one side of each criterion under the rubric as worded. For each, name the fact that puts it there and ask whether a careful reader could rule that fact the other way. If so, take it out, or settle with the evaluator how the rubric treats it and write that into the rubric. A boundary case left in by accident makes the test measure the key rather than the workflow.
4. **Leave a margin.** Write each corpus so its verdict holds with any one document read the other way. With six documents a corpus, that means at least five passing in the corpus written to pass and at most one in the corpus written to fail, on a rubric whose line is at half.
5. **Plant decoys.** In the passing corpus, a grudging, badly expressed account of real change; in the failing one, a warm, enthusiastic account in which nothing anybody did changed. A workflow that reads both for their substance has shown it reads evidence and not tone.
6. **Write the documents from the setting, never from the workflow's definitions or the rubric's wording.** Documents written in those words pass because they repeat them. Where possible a different model writes them than reads them, which restores some of the independence a same-model test lacks.
7. **Label everything as synthetic**: file names, a first line in every document, a note in each folder and a column in the index, so no report made from them can be mistaken for evidence.
8. **Run and compare.** Build the workflow on the passing corpus, then run it unchanged on the failing one. Compare each verdict with the key, and each decoy with what it was written to show.
9. **Diagnose a miss before changing anything.** A document can land on the wrong side for three reasons: it does not show what its brief says (rewrite it), its brief was a boundary case (fix the key and the rubric, recheck every brief), or the workflow misread a clear document. Only the third counts against the workflow.
10. **Freeze and run.** Save the workflow and both results with the date, then run that workflow unchanged on the real documents.

## Traps

- **Documents that echo the codebook.** They pass the test by repetition. Test: search the documents for the definitions' distinctive phrases.
- **An unnoticed boundary case.** A miss then blames the workflow for the key's ambiguity. Test: step 3, done before the documents are written.
- **No margin.** With four documents and a line at half, one misreading flips either verdict, so a pass shows little and a fail may be noise.
- **The same model writing and reading.** It shares its own sense of what a passage means, so agreement is easier than with real documents. Say so once, and use a different writer where possible.
- **Quiet changes after the real reading.** A workflow revised once the real documents are seen is no longer the tested one. Revisions are fine if recorded as a new version, with the reason, so a reader can see what moved.

## What good looks like

A key dated before any document was written; both verdicts as keyed, with the margin stated; each decoy read for its substance; any miss diagnosed and its cause named; the workflow saved with its date before the real run; and a method section in the real report saying the workflow was tested first on two synthetic corpora, from which starting point, and what it got right.

## As a plan

The test uses the real workflow and nothing else: the same code, tabulate and judge steps, run on three folders kept apart, two synthetic corpora and a key that no run opens. Nothing new is needed in the workflow itself; what the test adds is the key, the labelling and the comparison at the end. In the Rubicon plugin this is the test-corpora step, offered when a settled question asks for a summative verdict with consequences.

## Sources

- Haven, T. L. and Van Grootel, L. (2019). Preregistering qualitative research. *Accountability in Research*, 26(3), 229-244. DOI 10.1080/08989621.2019.1580147. On whether preregistration suits qualitative studies and how the Open Science Framework form could be adapted for them.
- The practice of planting known positive and negative cases to check an instrument before trusting its results is old across the sciences, as positive and negative controls in laboratory work and as test cases with known answers in software; this page carries it over to coding qualitative documents.
