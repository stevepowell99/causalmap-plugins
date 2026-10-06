# Consolidating overlapping labels into a shorter list

Coding in people's own words, or letting a model name what it finds, leaves many labels that overlap in meaning, and this page says how to turn them into a shorter list without losing what they meant. It is written for anyone doing that job, a researcher, an evaluator or an AI agent, whatever the tool.

The labels may be factors in a causal map, themes, codes or categories. The principles are the same, and they are the ones our own software and assistants are given.

## Why it is needed

Each pass of coding names what it sees without knowing what other passes called the same thing, so one idea turns up under many names. More data does not fix this: in one of our projects, coded freely across eight sources, 318 distinct labels appeared and only one of them was used in more than one source. Counted as they stand, such labels say little, because the same thing is split many ways. Consolidating them is what makes counting possible.

## Two decisions, made in order

Consolidation is two decisions: **what the groups are**, and **which label goes in which group**.

- **Make the list once, from everything.** Whoever proposes the groups, a person or a model, needs to see every label with how often it is used, not a sample. A list made separately for each batch of material settles on slightly different names each time, and the batches no longer add up.
- **Then assign each label against the closed list**, one at a time. A model is good at proposing a list when it is shown the whole set, and poor at sorting hundreds of items at once: it forms groups from the first few dozen and forces the rest in.
- **A rule of thumb:** up to about fifty distinct labels, one pass can do both. Beyond that, make the list first and assign afterwards.

## How many groups: a ceiling, not a target

Ask for at most so many groups, never exactly so many, and expect fewer than feels natural. A group with fifteen labels behind it supports a sentence in a report; eight thin groups are no easier to read than the fifty labels they replace. Twenty distinct labels rarely support more than five or six real groups. A group needs at least two members, ideally from more than one source. Where the material supports fewer groups than were asked for, return fewer and say why.

## What a group's name must do

- **Name what varies, not the topic.** "Quality of pre-visit preparation" names something that can be better or worse; "Programme structure and administration" names a filing drawer. Where the work is causal, the name should read as the subject of a causal sentence: "X led to ...".
- **One idea per name.** A name joining two things with "and" is a sign that two groups have been merged. "X and Y" is acceptable only where X and Y are, in this material, two names for the same thing: Holland and the Netherlands usually go together, though not in every context; Russia and Brazil never do. Never use "X vs Y".
- **Stay close to the words people used.** Reuse an original label where one already covers the group. Concrete and memorable beats abstract and tidy. About eight words at most.

## Opposites stay apart

Words for opposite poles of the same thing sit close in meaning, and closer still in the vector space that similarity tools use, because they turn up in the same contexts: employment and unemployment, wealth and poverty, income and lack of income. Similar is not the same, so keep the two poles in separate groups.

Where one group turns out to hold both poles, split it into a **balanced pair**: "Strong import controls" and "Weak import controls", or "Presence of import controls" and "Absence of import controls", not "Import controls" and "Weak import controls".

Some coding schemes mark the reverse pole in the label itself, so that the two can be shown together or apart at analysis time. How that works, and how to read the result, is on [Combining opposites, sentiment](https://garden.causalmap.app/combining-opposites/).

## Leaving a label alone is an answer

A label that fits no group stays as it is, with a short reason. Forcing it into the nearest group corrupts that group's meaning for every item that carries it. Report how much was left over: the share of the material a list cannot hold is a measure of how good the list is.

## Use the best evidence you have

The wording of a label is the weakest evidence of what it means. Where you can see what each label does in the material (the passages behind it, and in causal work what it leads to and what leads to it), group on that: two labels with similar words that do different work are two groups, and two with different words that do the same work may be one. Where you have only the labels and their counts, keep groups tighter and leave doubtful labels alone, because a wrong merge cannot be seen from the wording.

## Keep the trail

Give each group a name, a one-sentence definition, what does not count (the near misses, and where they belong instead) and its members. Keep every original label beside the group it was given, so that any merge can be checked, disputed and undone. Record how the list was made, so that somebody who disagrees can make it again with other settings or a list of their own.

## Similarity tools find candidates; judgement names and checks

Grouping by vector similarity is fast and repeatable, and good at proposing candidates. It cannot tell opposites apart, and it cannot know that two words are the same thing in one context and different things in another. So let it propose, and have a person or a model name the groups and check them against the rules above, poles first.

## When labels can have levels

Everything above assumes a flat list, where consolidating means replacing many labels with fewer. Labels with levels, written as "general; specific", open up many more approaches, most of which lose less detail. They are covered on their own pages:

- Putting labels under a broader parent and reading the map at whichever level a question needs, with the rules for when a parent is legitimate: [Hierarchical coding](https://garden.causalmap.app/zoom-filter/).
- Fixing the top level with a codebook, leaving the second level in people's own words, and then grouping the second level within each top-level factor: [Grouping the second level](https://garden.causalmap.app/second-level-clusters/).
- Groupings that cut across a hierarchy, kept as tags inside the label: [Factor label tags -- coding factor metadata within its label](https://garden.causalmap.app/label-tags/).

## Related pages

Where consolidation sits in a whole coding workflow: [A workflow for causal coding with and without AI](https://garden.causalmap.app/ai-coding/). Applying these rules with particular tools: [Different kinds of coding and recoding](https://garden.causalmap.app/kinds/).

<!-- Generated by scripts/sync-agent-guidance.js from the garden page "903 Consolidating overlapping labels into a shorter list ((consolidating-labels))" (https://garden.causalmap.app/consolidating-labels/). Edit that page, then run: npm run sync:agent-guidance -->
