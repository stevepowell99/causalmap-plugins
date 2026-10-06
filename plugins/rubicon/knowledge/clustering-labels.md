# Clustering the labels a coding invents

A coding that lets the model name what it finds coins its labels call by call, so they must be put under one short list before anything is counted by them: a group step finds that list, a closed code step reads every case against it, and the codebook records how it was found.

Read this page before designing a code step whose free-text column a later group or tabulate step will use, and before designing any group step that decides which labels mean the same thing. A group step whose `practice` setting names `codebook-from-the-material` reads it for the steps. The rules for the groups themselves (a ceiling rather than a target, what a group's name must do, opposites kept apart, labels left alone with a reason) are in `consolidating-labels.md`, which is the published garden page and is shared with Causal Map's assistant. What follows is the evidence, how Causal Map does it, and the chain that works in Rubicon's pieces.

## Why free labels do not add up

Letting a model name what it reads is how a concept nobody anticipated gets found, and a list declared in advance cannot do that. The cost arrives later. Each model call sees one chunk of text and names what is in it without seeing what any other call named, so an instruction such as "use the same label for passages that share a chain" can only be kept inside one chunk. Across a corpus nobody holds the vocabulary, and one idea turns up under as many names as there were calls that met it.

More data does not fix it, and neither does a better model. On Causal Map's own AI coding, an eight-source project coded without a codebook produced 318 distinct factor labels, and one of them appeared in more than one source. A 75-source project coded against a codebook that fixed the first level of each label produced 53 first levels, and new ones stopped arriving after about the eighth source, while the free text after the first level never stopped: the 75th source was still adding new ones. The vocabulary converges exactly where something fixes it.

The same thing in Rubicon, on the public example project `example-original-rubicon`. A realist coding of nineteen QuIP household interviews, with a free label naming the context-mechanism-outcome chain each passage belonged to, came back as 967 passages under 423 labels, 242 of them used once. New labels per interview never settled: the first two added 43 and 45, the last added 20. Counted by label, that is a table of 423 rows. Twenty-four of the labels mention hygiene and between them carry 92 passages from 17 of the 19 households, the most widespread pattern in the corpus, and no one of those labels reached more than seven households. Six labels beginning `savings_group` carry 31 passages and were counted as six things. The two configurations the summary called supported rest on four passages from a single household each.

**A label naming a whole chain multiplies.** One that names a context, a mechanism and an outcome together turns every pairing into a new name. Causal Map labels one thing at a time, a factor, and builds chains from links between factors once the factors are clustered, which is why its vocabulary stays small enough to cluster at all. Where a question is about configurations, label each element on its own and assemble the configuration from clustered elements. Where a coding has already recorded whole chains, as a short label or as a sentence stating the rule, a discoverer can still group them, and each item of its codebook can be a merged rule.

## Two decisions, and where the freedom does harm

Clustering is two decisions: **what the groups are**, which is the vocabulary, and **which label goes in which group**, which is membership. A model is good at the first when shown a set of labels and asked what to call them. It is poor at the second at any scale. Asked to sort hundreds of items, it attends to some of them, forms groups from the first few dozen and forces the rest in. The next run gives a different answer, and nothing is recorded that a reader could check item by item.

Four things make a clustering one a reader can trust.

- **The vocabulary is small, and the record says how it was found**, so a person who disagrees with it can have it found again with other settings or with a list of their own.
- **Membership follows a stated rule rather than a model's impression of hundreds of items.** Each row is put under the closed list on its own, by a model reading it against the whole list, or by rule from a record of which labels each item takes.
- **Every row keeps its own words beside the item it was given**, so any merge can be walked back and disagreed with.
- **What fits nothing is reported as a number** rather than forced into the nearest group. How much of the material the list failed to hold says how good the list is.

**The fifty line.** Up to about fifty distinct labels, one model call may propose both the vocabulary and the membership, provided it sees every label, meaning the whole list with how often each was used rather than a sample of the passages. Past fifty, a model's grouping is an impression, so the vocabulary is proposed from the whole list and membership is decided row by row against it.

## How Causal Map does it

Causal Map keeps the two decisions apart.

- **Finding the vocabulary.** Revise codebook, with pre-clustering switched on, groups the labels by their vectors first, and the model only names each group from eight to twenty representative labels. The Auto Recode filter builds a tree the same way, splitting by vectors, with the model naming each new branch while shown the names already given so that they do not overlap. Either way the names are proposals, which go into a codebook a person edits. Its default target is a third of the distinct labels, capped at twenty-five.
- **Assigning against it.** Recoding offers four routes in rising order of cost: magnetic, by each label's vector similarity to each codebook line with a threshold and no model call; semantic, a model mapping each distinct label to its best line; causal, a model reassigning each link after reading its quote; and hard, coding the text again with the codebook as a closed list. Soft Recode Plus works as a filter, so the stored label is never changed, marks which labels were recoded, and keeps or drops what matched nothing, as the user chooses.
- **Fixing the first level.** Labels are hierarchical, `first level; detail`. A codebook fixes the first level and the detail stays free, so the first level is what gets counted and the detail is what gets read.

Its own documentation carries the warning that matters here: a large recode split into batches lets each batch settle on slightly different labels, so the codebook is developed first and the recode then runs against it.

## As a plan

A code step with a free-text column records the label in the speaker's own words, one row per passage. A group step reads that whole column, every row's label and its quotation, and proposes a small codebook (`key_column` the free-text column, `granularity` usually standard, `max_items` the ceiling that comes with it). Past about 1,500 rows, past where the labels with their quotations no longer fit one call, the labels are ordered by embedding and cut into batches, a vocabulary proposed from each batch and merged in a further call, and the assigning that follows is still done over every row in one place, never per batch, which is where a label-by-label clustering drifts between batches. The split this page calls for past fifty labels is how the group piece always works, whatever the count: the vocabulary comes from a strong model reading the whole list, the assigning from a cheap model reading each row on its own.

These are the engine's two routes for turning open labels into counted items. With `assign` set, the group step adds an `item` column to every row, a soft recode, and a tabulate step can count by `item` directly: this reads the documents once and counts only what the open pass happened to notice. Without `assign`, the codebook stands alone for a closed coding to use: a second code step, reading every document again, with a column whose values come from the codebook rather than from the row's own words, a hard recode, the code step run again rather than a piece of its own; this reads the documents twice and counts what every document actually holds against the fixed list, including the documents the open pass said nothing about.

The record keeps the two decisions apart. The group step's codebook carries each item's label, what it means, what counts, the near misses that go to another item instead, and the quotations that illustrate it; its settings say which column fed it and how many rows. What fits nothing is reported as a count of unmatched rows rather than forced into the nearest item, since how much of the material the list failed to hold is a measure of how good the list is.

A `check` on the closed code step gives a second model one more look at every row against the item's own definition, which is the nearest thing here to rereading the cases put under the largest item, where a coarse list is likeliest to have merged two things that were not the same. Running the workflow on a handful of documents with the proposed codebook before the rest is where a list drawn with too few items, or one word away from the evaluator's own, gets caught cheaply, since a trial is a way of running the workflow on fewer documents rather than a step of its own. For a new coding the realist page's own advice holds: code each element of a configuration on its own with a short label, so that each element's list is small.

## What is missing

- **Grouping by vector, and assigning by vector or by rule.** Causal Map groups labels by the arithmetic of their vectors before a model names the groups, and its magnetic route puts each label under its nearest list item by vector similarity, with a threshold and without a model call. Rubicon has neither: every grouping and every placement is a model's reading, of the case or of a row's label and quote, so nothing records a rule a reader could re-run.

The same would serve outcome harvesting's deduplication, which has the same many-to-one form ([outcome harvesting in Rubicon](outcome-harvesting-in-rubicon.md)), where the list is of outcomes rather than themes.

## Pointers

The skill `codebook-from-the-material`, and "Hold material back" in Rubicon's design principles. Causal Map's own account: the Revise codebook, Recode, Soft Recode Plus and Auto Recode sections of the Causal Map app's documentation.
