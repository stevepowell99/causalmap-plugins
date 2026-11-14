---
name: test-corpora
description: Use when a summative verdict with high stakes rests on the answer, such as whether a programme is funded again, scaled, stopped or judged effective against a rubric, or when the evaluator asks to "test the workflow first", "check it can tell success from failure", for "synthetic data", "made-up interviews" or "control corpora". Writes two small labelled made-up corpora, one where the programme passes the test and one where it fails, runs the workflow unchanged on each, and checks it reaches the verdict each was written to before it meets the real documents.
---

# Test corpora

Before a workflow gives a verdict that matters, show that it can tell success from failure. Write two small made-up corpora about the same setting: corpus A, written so that the programme passes the test the question sets, and corpus B, written so that it fails. Run the workflow on each with its definitions unchanged. It should reach a pass on A and a fail on B. A workflow that cannot tell them apart is found out for the price of two small runs, before the real one, and one that can is a fixed plan with evidence that it discriminates: pre-registration with a test attached.

What it shows and what it does not: it shows the workflow discriminates on made-up material, not that it is valid on real material, and the report says so. Made-up documents are never counted as cases and never quoted in an answer on the real documents. The same model writing the documents and then reading them makes the test easier than it should be; say that once, in a sentence, when you offer it.

## When to offer it

Offer it, in a sentence and as an option the evaluator can decline, when the settled question asks for a summative verdict with real consequences: a rubric applied to decide whether something worked, a recommendation to fund, scale or stop, a pass or fail against targets. Do not offer it for exploratory or formative questions, where it costs more than it tells. The verdict and the rubric are settled first, since the corpora are written to fall either side of them.

## What to write from

By default, from the evaluator's description of the setting and nothing else: what the programme is, who would be interviewed, where, and what was meant to change. That keeps the plan fixed before the real documents are read.

Reading a few real documents as a model for how people there actually talk makes the corpora more realistic, but ask first, and do it only when the evaluator says it is allowed: their data agreement may not permit it, and reading real documents before the plan is fixed undoes the pre-registration. Where it is allowed, use two or three documents, for tone and structure only, never copying a passage or a person.

Never write from the workflow's definitions, codebook or the rubric's wording. Documents written in those words pass the workflow because they repeat it, which measures nothing. The rubric decides which side of the line each corpus falls; the documents themselves are written in the setting's own words.

## Plan both corpora

Before writing any document, write `test-key/test-key.md`: the verdict each corpus is written to reach under the agreed rubric, and for each document an id, what it should show, and a brief of two or three sentences. Six documents a corpus unless the evaluator wants otherwise, since each corpus costs a run. Write each corpus so that its verdict holds with any one document read the other way, so that a single misreading cannot flip the result. Decide too the facts about each document that the question's comparisons use, such as site or role, and keep them the same across A and B so that the corpora differ in what happened, not in who was asked.

Every brief must fall clearly on one side of each criterion, under the rubric as worded. For each brief, write in the key which side it falls on for each criterion and the fact that puts it there, then test that fact against the rubric's wording: could a careful reader rule it the other way? Where a fact could go either way, the brief is a boundary case: take the fact out, or settle with the evaluator how the rubric treats it and write that into the rubric before any document is written, then test every brief in both corpora against the amended wording. A boundary case left in by accident makes the test measure the key rather than the workflow, and it can sit in any brief of either corpus.

Each corpus needs decoys, so that it tests whether the workflow reads evidence or tone:

- In A, a grudging, badly expressed account that describes real change in detail. A must still pass with it read for its substance.
- In B, a warm, enthusiastic account of success that names nothing anybody did differently. B must still fail with it read for its substance.

A workflow that separates obvious success from obvious failure has shown very little; one that also reads both decoys for their substance has shown it reads evidence.

## Write the documents

Where you can hand the writing to a helper on a different model, give it the setting, the key's briefs and nothing else, since a writer different from the reader restores some of the check. Otherwise write each document yourself:

- About 400 words of the kind the real documents are, interview transcripts unless the evaluator says otherwise.
- The document itself and nothing else: no title, no notes, no mention of corpora, verdicts, tests or criteria. It has to read as something somebody produced for their own reasons.
- A decoy's surface and substance pull against each other; do not resolve the tension or explain it.
- People tell what happened to them; at most one document in each corpus puts the pattern in general terms.
- Where the interviews would really be held in another language, write them as translated and record the language as a fact.

## Label them as synthetic

Nobody should ever mistake these for evidence.

- Three folders side by side in the place where you are allowed to write: `test-corpus-A/` and `test-corpus-B/`, each set up as a Rubicon folder with its own `corpus/`, and `test-key/`, which no run opens.
- Name every file `SYNTHETIC-` followed by its corpus and id, such as `SYNTHETIC-B-warm-empty.txt`, and open every document with the line `[Synthetic test document written by Claude. Not a record of a real person.]`.
- Put a `README.md` in each corpus folder saying in plain words that every document in it was written by Claude to test a workflow, is not a record of any real person, and must not be quoted or counted as evidence.
- In each `corpus/index.csv`, give every document a `synthetic` column reading `yes` and start each title with `Synthetic:`, with a column for each fact decided in the key; never the expected verdict or the decoy mark, which stay in the key. Every report made from them then says on its cover that it rests on synthetic documents.

## Run, compare, then the real run

Run the settled question on A, which writes the workflow. Run the same workflow on B with its definitions unchanged: code B against the same columns and meanings, recount, and draft the answer the same way. Then compare each verdict with the key, and each decoy with what it was written to show, and tell the evaluator plainly: whether the workflow reached pass on A and fail on B, and which decoys it read for their substance and which took it in.

Where a document lands on the other side from its brief, find which of three things went wrong before changing anything, and tell the evaluator which:

- The document does not show what its brief says. Rewrite that document and rerun its corpus.
- The brief was a boundary case under the rubric. The key is at fault, not the workflow: settle the rubric's reading with the evaluator, write it into the rubric and the workflow's definitions, test every brief in both corpora against it as above, and rerun both.
- The document is clear under the rubric and the workflow misread it. Only this counts against the workflow: revise the definitions with the evaluator and run both corpora again before going further. When it passes, save the workflow and both results in `test-key/` with the date, then run that workflow unchanged on the real documents, and say in the real report's method section that the workflow was tested first on two synthetic corpora and what it got right.
