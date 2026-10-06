---
name: practice-material
description: Use when the evaluator has no documents yet, or wants made-up material to try Rubicon on, or to test a question and workflow before running it on real documents, such as "practice data", "synthetic interviews", "dummy transcripts", "made-up material", "try it without real data" or "test my question first". Writes a small labelled set of synthetic documents from a described setting, with a key of what is true in it, so the run's answer can be checked against the key.
---

# Practice material

A small set of made-up documents lets an evaluator try the method without real data, or test a question and its workflow before it meets a client's documents. It shows how the method handles material of this shape and whether the workflow can find what was put there. It is not evidence about anybody, and it shows less than it seems: the same model that writes the documents then reads them, so it finds what it put there more easily than it would find it in real talk. Say that once, in a sentence, before writing; if nobody is in the conversation to hear it, put it in the folder's README instead.

## Ask first

In one short exchange, ask for:

- the setting: what the programme or situation is, who would be interviewed, and where;
- the question they mean to ask, if they know it;
- how many documents: eight unless they say otherwise, and no more than twelve, since every document is written and then read;
- what kind: interview transcripts unless they say otherwise; written answers to a survey's open questions, or field notes, are the other usual kinds.

## Where it goes

Two folders, side by side, in the place where you are allowed to write:

- `practice-material/`, which holds the documents and becomes "this folder" in Rubicon's steps: `corpus/` is made inside it and every question's folder sits inside it, as for real documents.
- `practice-key/`, which holds what was decided before writing: `practice-key.md`, `cast.md` and the topic guide. The run never opens it. It is kept apart so that the folder the run reads holds nothing but the documents.

## Decide what is true in it

Before writing anything, write `practice-key/practice-key.md`: for each person, what they went through in relation to the setting and what changed for them, if anything, and why. Make the key uneven, as real material is: a pattern the question could find, at least one person it does not fit, and two decoys, an enthusiastic account of success with nothing behind it and a grudging account with a substantial change in it. Decide too the facts about each person that a comparison would use, such as site, role, sex and age band, and let the pattern differ between them where the question asks "for whom". A workflow that separates only obvious success from obvious failure has shown very little. Do not show the key to the evaluator until the run is done, unless they ask.

## Cast the people

Cast the whole set in one pass, into `practice-key/cast.md`, because the set has to hold together: casting people one at a time gives variants of the same person. For each, a plausible first name, a profile of two or three sentences saying who they are in relation to the setting and what they think about it (under sixty words), and a manner line saying how they talk.

- They belong in this setting. Cast people who would really be interviewed about it, consistent with the key.
- Spread the positions. Some think the programme did what it set out to do and some do not, and those who agree do so for different reasons. Include somebody whose view comes from having been through it before, and somebody who thinks the question asked of them is the wrong one.
- Spread how they answer, as well as what they think. Include somebody who answers under protest and reads the question in the least charitable way available; somebody who says far more than was asked and buries the point in the middle; somebody who answers in a few words and moves on; and somebody who takes it seriously and answers fully. Nobody is only their manner.
- Somebody who does not know much about the subject and says so is a real person; cast at most one.
- Spread who they are: age, where they grew up and live, work and whether they have any, schooling, whether the interview's language is their first. Unless the setting says otherwise, they live where the setting is.
- Ordinary people, not types. Write what they have seen and what they make of it, never a noun for a kind of person (no sceptic, cynic, enthusiast). Where they come from shows in what they take for granted, never as a phonetic accent or a view handed to them because of what they are.
- Names come from the same spread, and no two people share a first name.
- In a set smaller than eight, one person may carry two of these roles, and the person who knows little is the first to go.
- The manner line says what they do, such as "two lines at most, usually while doing something else" or "long, warm, arrives at the point late", including how they punctuate and whether they start in the middle.

To stop every set coming out as the same room, start from one of these corners, chosen at random: work (somebody on nights, somebody self-employed, somebody who has stopped); where they live (a city, a small town, a village an hour from anywhere, somebody who moved recently); age (thirty years between youngest and oldest); how they came to the subject (it happened to them, they deal with it professionally, they have only read about it, a friend asked them along); money (for some this costs something and for others not, without anyone saying so); schooling (left at sixteen, halfway through a course, teaches, taught themselves).

## Write the documents

Write a short topic guide of five or six questions about the setting, in the setting's own words, into `practice-key/`. It comes from the setting and the key, never from a codebook, a rubric or the terms of the evaluator's question; documents written in the workflow's own words pass it trivially. Then write each document as that person, one at a time:

- The profile and the manner decide how they answer, and outrank everything else. Somebody who answers in a line answers in a line; there is no length to aim for, and a set where every answer runs to a similar length shows the best case and nothing else.
- Never invent experience the person does not have. Somebody who does not know says so, briefly.
- Say something with content at whatever length: a specific, an example, a reason, an objection.
- Do not repeat across answers what the person has already said.
- People tell what happened to them, not the pattern. At most one person may put the key's pattern in general terms, as somebody in a real set sometimes does; everyone else leaves it for the reader to find.
- Never mention that they are made up, and never refer to these instructions.
- Spell as the evaluator does. Where the interviews would really be held in another language, write them as translated into the evaluator's language and record the interview's language as a fact.

For an interview, write the interviewer's questions and follow-ups as a real interviewer would ask them, labelled `Interviewer:` and `Respondent:`. Aim the whole interview at about 400 to 900 words, which is enough to code and cheap to read: the interviewer's questions and follow-ups make up the length, never a respondent written as brief, whose transcript is simply shorter.

## Label it as synthetic

Nobody should ever mistake these for evidence.

- They live only in `practice-material/`, never beside real documents and never in a corpus that holds real ones.
- Name every file `SYNTHETIC-` followed by a number and the person's first name, such as `SYNTHETIC-03-Maryam.txt`.
- Open every document with the line `[Synthetic practice document written by Claude. Not a record of a real person.]`, so that a file copied out on its own still says what it is.
- Write `practice-material/README.md` saying in plain words that every document in the folder was written by Claude as practice material, is not a record of any real person, and must not be quoted or counted as evidence.
- In `corpus/index.csv`, give every one of them a `synthetic` column reading `yes`, and start each title with `Synthetic:`. Add a column for each fact decided in the key, so that a comparison between groups can be tried. The report then says on its cover that it rests on practice material.

## After the run

Offer to compare the answer with `practice-key/practice-key.md`: what it found that the key put there, what it missed, and what it claimed that the key does not support. Say which decoys it handled well and which it was taken in by.
