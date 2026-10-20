---
name: codebook-from-the-material
description: Use when a question asks what the material holds and nobody has an agreed list, such as "what are the themes", "emerging themes", "what reasons do people give", "in their own words", "what did people raise", "what helped or hindered" or "build a codebook". Builds a codebook by reading several documents across the groups, writes each item to codebook quality, pilots it on documents it was not built from, and records where it came from.
pieces: [group]
---

# Building a codebook from the material

Every count over a codebook is only as good as its items, and a codebook built from one document carries one speaker's concerns into every number. So read enough of the material first, across the groups; write each item so that two careful readers would code a passage alike; and try the codebook on documents it was not built from before anything is counted. The record shows the basis, and the evaluator sees a warning on any codebook built from fewer than three documents or never piloted.

## Choose the documents

- Draw a build set with `mcp__rubicon__sample`, seeded and stratified by the column that divides the groups the question compares (skill `drawing-a-sample`). Take several, at least one from each group and more where groups are large or documents vary.
- Draw a pilot set from the rest, passing `among` the documents outside the build set, again one or more per group. A pilot on documents the codebook was built from tests nothing.

## Discover in the speakers' words

- Brief one or more `discoverer`s over the build set, each reading its documents whole, with the question and any items the evaluator already has. Each records mentions with a `label` in the speaker's own words, in a set such as `discovery`, and a line in `record/read.jsonl` for each document read.
- A label names one specific thing with its direction: "managers gave no time to deliver", not "management issues"; "income rose", not "income". A label that has to list its contents ("X and Y", "X issues") is two labels or a topic. Label one thing at a time, never a whole chain of context, mechanism and outcome, which turns every pairing into a new name.

## Group the labels into items

Grouping is two decisions: what the items are, and which label goes under which. Up to about fifty distinct labels, one agent shown every label with how often it was used can make both. Past that, an agent sorting hundreds of labels at once forms groups from the first few dozen and forces the rest in, so keep the decisions apart: have it propose the items from the whole list of labels, then place every label against the fixed items in a second pass, and report the labels that fit none. What fits nothing stays a number, never forced into the nearest item.

Write each item with an `id`, a `label`, and:

- `means`: what the item stands for, in a sentence;
- `counts`: the kinds of account that belong, concretely;
- `does_not_count`: each near miss named, such as the neighbouring item it is easily confused with, a general remark on the topic, the same words used about something else, or a look-alike activity. "Anything unrelated" says nothing; "watching a colleague deliver is not rehearsing delivery oneself" does;
- `directions`, naming the side the item records where the question has sides. Where a thing has two sides the question keeps apart, such as a barrier and a facilitator, make one item for each side, since a count reads items and cannot split one.

Keep apart what a careful reader keeps apart: what caused a change and when it began, the speaker's own experience and a general view, the heading a topic came under and what was said under it. Keep an item only where a passage read supports it, and note how many documents each was seen in. Take the number of items from the question, a handful for headline themes and more for detail, and say which you chose.

Write `record/codebooks/<name>.json` at `version` 1, with `built_from` listing exactly the documents read whole to make it, `piloted_on` empty, and `made_by` naming the discoverer.

## Pilot, revise, freeze

- Brief a `coder` to read the pilot documents whole against version 1 and write cells for every case and item in a set such as `pilot`, listing every borderline passage with its two readings and every passage that fits no item.
- Read every pilot cell and borderline case yourself. Tighten `does_not_count` where near misses were coded as the item; split an item collecting two things; merge two a reader cannot tell apart; add an item for material that fitted nothing and bears on the question.
- Raise `version`, say in `notes` what changed and why, and list the pilot documents in `piloted_on`. Where the revision was large, pilot again on fresh documents and add them.
- Show the evaluator the codebook before the full reading (skill `trial-runs`); they can change a definition in a sentence.
- Pilot cells are never counted. Once the codebook is settled, the pilot documents are coded again under the final version with the rest.
- Once coding of the whole has begun, a change to any item raises the version, is explained in `notes`, gets a line in `record/changes.jsonl`, and the cells already coded are coded again for the items it changed.

## Traps

- A codebook drafted from part of one transcript: it looks complete and misses what the other groups raise.
- Items named for a topic ("partnership", "communication"), which collect whatever anybody said near the word.
- Items tuned to the pilot's counts rather than its borderline cases: the pilot tests the definitions, and its numbers are not findings.

For depth, give `guidance/knowledge/clustering-labels.md` to the discoverer grouping the labels; `guidance/knowledge/framework-analysis.md` says what a list read against every case can and cannot establish.
