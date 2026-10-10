---
name: settling-the-question
description: Use when an evaluator's question could be answered differently by two careful readers as put, such as "what are the themes", "summarise this", "was it effective", "what worked", "is this a good project" or "what do people think of X", or whenever a question names a subject without saying what the answer must say. Breaks it into parts others could check, naming the cases, the list, what counts, the base and the comparison, and asks for any standard rather than supplying one.
---

# Settling the question

A question is settled when two careful readers, given the same instruction, would read the material alike, and every number in the answer would lead to quotations a third person could look up. Most questions arrive unsettled, and settling them with the evaluator comes before any plan is costed. Being ill defined is the only ground for refusing a question; a question is never refused for being about feelings, tone or anything else that sounds soft.

## Say why, then break it down

- Say in a sentence or two why the question cannot be checked as put, then offer parts that can. Never answer the vague version, even in passing: a direct answer decides for itself what was meant and says it confidently.
- "Was it effective" wants a verdict before anybody has said what the outcomes were or what would count as enough. "Is this a good project" is four questions: good for whom, compared with what, against whose standard, and how much of that these documents can answer.
- Where the breakdown turns on choices only the evaluator or their stakeholders can make, name those choices.

## Settle the claim underneath first

Each kind of claim rests on the one before it:

- what the thing meant to the people who spoke of it, in their own words;
- what forms it took, and who raised each, which needs cases read against a list;
- how cases differ, and what goes with what, which needs those cells counted by a column the documents carry;
- why it happened, which needs rival explanations or a theory of change read link by link;
- whether it was good enough, which needs a rubric whose standard comes from the evaluator.

A vague question usually asks for a high claim while the one under it is unsettled. Offer the claim the material can carry now, and say what the next would need from the evaluator: usually a list, a base or a standard. Never climb on their behalf.

## Name the four things

Whatever the claim, the plan fixes four things. Describe them as the table the answer will fill, since an evaluator corrects a table in a sentence.

- **The cases.** What one case is: a document, unless `corpus/index.csv` gives several documents one `case`, as with one person interviewed twice. Ask about it only where the documents might not be one case each: several speakers in one transcript, a report covering several projects, the same person in two documents, or a question about units larger than a document (villages, organisations). Then agree the unit, and its name for the reader ("households"), for each count that needs one; parts of one question may count different units. Where one document holds several cases, the coding says which case each passage is about, so its definitions say how to tell. Otherwise say nothing about it: each document is one case.
- **The list** every case is read against: agreed (the evaluator's own, the terms of reference, an interview guide's topics, a theory of change in a background document) or found in the material (skill `codebook-from-the-material`). Never ask the evaluator for a list the documents are there to supply.
- **What counts.** A strict number counts `first_hand` accounts; a broad one names the statuses it adds, such as `near_miss` or `prompted`. Propose how the question's own words map onto these and settle it with the evaluator, for instance whether "from their own experience" admits a saving the speaker saw their team make, so that the answer can commit rather than hand the choice back at the end.
- **The comparison.** A base (eleven of the fourteen partners), an alternative explanation, a written standard, a comparison case in the corpus, what was expected, what would have happened anyway, or the evidence itself. A count that names no base is the commonest way a vague question survives looking answerable.
    - A comparison between groups the index marks (supported or not, completed or not, one round or another) rests on whoever filled in that column, and when. Where the documents themselves speak to it, treat the column as a claim to check: read each document for it, say where the two disagree, and say which the answer uses.

Name also the distinctions the answer must keep apart, such as a barrier against a facilitator, or what caused a change against when it began: a count pooled across them cannot be repaired later.

## Settle on one path

- **Recommend one design and commit to it: the most parsimonious one that answers the question.** Where there are real alternatives, such as another method, a broader or stricter count, or an extra part, set them out briefly with what each would add and what it would cost, recommend the leaner unless the question needs the fuller, and help the evaluator choose. The plan carries the path you recommend, never several at once.
- **Set the question as agreed in as few parts as the evaluator's question needs.** Each further part usually means another reading of every document. A part they did not ask for, however natural, is offered as an option with what it would add, never built into the plan.
- **Ask only what changes the design or its cost substantially**, usually one to three questions, and put the most consequential first. For everything else choose a sensible default, state it in a line, and let the evaluator overrule it.
- **`record/plan.md` holds the path chosen, not the open options.** A table split by every unresolved choice, or a broad and a strict version of the same count kept in case, makes the workflow larger and dearer without giving the evaluator anything to decide with.

## Ask for the standard, never supply it

Where the question asks for a verdict, ask for the standard or the document that holds it. Offer the form of a standard in their terms, two or three of them, without numbers: "at least ___ times as many supporting as contradicting cases", never "eight of ten". A standard chosen after seeing the numbers can be made to fit any of them. Without one, plan up to the table the verdict would read and say that the verdict waits on their standard (skill `rubrics-and-verdicts`).

## Before any reading

- **Plan from the skim.** `corpus/skim.md` maps every document: what it is, what it covers and where. Read it first and plan the workflow from it; it is how you know what the corpus holds, so you never need to open documents to find out. Its first lines say which documents could not be mapped.
- **Check whether it needs reading at all.** A question the index columns answer (interviews per site, by age band) costs nothing.
- **Read cheaply, not raw.** `mcp__rubicon__outline` gives a document's structure and section offsets for nothing, before any model reads a character of it: call it first, on every document you are about to open. For finding where something is said, `mcp__rubicon__read_with` on a cheap model with a brief ("where does the interviewer ask about X", "is there a contribution claim here") costs a fraction of reading it yourself, and what it returns is all that joins your own context; your own `Read` or `Grep` pulls the whole document or file into your context instead, and that cost repeats on every later turn of this conversation. Reach for your own `Read` only once outline and read_with have not settled it, and never grep the same thing twice with a widened pattern: if the first search comes back thin, use read_with with a looser brief rather than retrying the regex yourself.
- **Find out what was asked.** Use `read_with` on the interview guide where the corpus holds one, or on a few transcripts' interviewer turns, with a brief asking what was asked about the topic. A group never asked about a topic cannot be counted as silent on it.
- **Decline the statistics this work does not do**, such as effect sizes, regressions or a number for what would have happened without the programme. Say it needs the data and somebody with a statistics package, and offer the part the documents can answer.
- **A question whose premise may be false** ("how did the programme improve wellbeing?") is read in both directions.

## Write it down

Put the settled question in `record/plan.md`, under the heading "How the question will be answered": the question as the evaluator asked it, how it will be answered, and why that is narrower; the four things; the borderline cases foreseen and how each will be decided; and what the answer's first sentence must state.

For depth: `guidance/knowledge/generic-evaluation.md` for terms of reference built on the OECD-DAC criteria, `guidance/knowledge/generative-and-counterfactual.md` for attribution and "would it have happened anyway", and `guidance/knowledge/reading-enough.md` for what a proportion is out of.
