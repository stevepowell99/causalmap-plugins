# Refining and substantiating outcome statements

Step 4 of an outcome harvest: who substantiates, what to ask, what counts as adequate, what to do when a substantiator disagrees, and the deduplication that belongs with it. This is the step that turns a set of programme claims into something an evaluation can report. It is also the step that gets cut when the timeline slips, and cutting it changes what the deliverable is.

Back to [outcome harvesting](outcome-harvesting.md).

## What substantiation is for

Two purposes. They pull in different directions.

**Accuracy.** Somebody who was there checks that the change happened as described, on the date given, involving the actors named. Most corrections are factual detail. Wrong date. Wrong department. The change turns out smaller or larger than the programme reported.

**Credibility.** The commissioner and the eventual reader need to know that the outcome set was not written entirely by the people being evaluated. A harvest substantiated by nobody outside the programme is a self-assessment, however carefully drafted.

Substantiation is not statistical validation and does not produce a confidence interval. It produces a verified-or-corrected statement with a named independent source attached.

## Who to go to

Three kinds of substantiator, with different strengths.

**The social actor themselves.** The person or organisation that changed. Best informed about what happened. Worst placed on contribution, because they have their own account of why they acted and often an interest in it. Use them to verify the change. Treat their view of the programme's contribution as a second claim rather than as verification of the first claim.

**A third-party observer.** Somebody who saw the change from outside: a peer organisation, a sector body, a journalist, a civil servant in a neighbouring department, another donor. Weaker on detail. Much stronger on contribution: no stake in the answer, and usually some knowledge of what else was pushing.

**A document.** A gazette, a published strategy, minutes, a signed contract, a budget, a media report. The strongest evidence that a formal change occurred, and close to useless on contribution. Documentary substantiation costs nothing to chase. Use it wherever the outcome is a formal act.

Practical rule. Use the strongest available source for the fact, and a source with no stake for the contribution. Never let the programme adjudicate a disputed outcome about itself.

## Sampling, because you will not substantiate everything

Substantiating a whole set is rarely affordable, and rarely the best use of the budget even when it is. Sample on purpose. State the rule.

Prioritise, in roughly this order:

1. Outcomes that carry the heaviest contribution claims. If the report will say the programme helped cause it, somebody outside the programme needs to have been asked.
2. Outcomes that matter most to the harvest users' questions from step 1.
3. Outcomes that would be surprising or contested if published.
4. Outcomes resting on a single source, especially a single programme source.
5. A scatter of ordinary ones, so the sample is not composed only of the interesting cases.

Skip, or substantiate documentarily only: outcomes already evidenced by a public document, and outcomes that are minor and uncontested.

Whatever rule you use, write it down before you start and report it with the count. "We substantiated 34 of 91 outcomes, selected as follows" is a sentence a reader can assess. "A sample was substantiated" is not.

Expect a response rate between half and two thirds after chasing. Decide before you begin what happens to a statement nobody replies about. Usually it stays in the set flagged `unsubstantiated` and is kept out of any counted claim in the report. Deciding this afterwards, once you can see which ones came back, is how a set gets tuned towards the answer somebody wanted.

## What to ask

Send the statement itself. A questionnaire about the programme gets you views about the programme. Keep it under a page.

- Here is a description of a change we believe took place. In your own view, is it accurate? Please correct anything that is wrong or missing.
- How do you know about it? (This distinguishes a witness from somebody repeating what they heard.)
- How confident are you that it happened as described?
- What do you think brought this change about? What or who contributed?
- Was anything else pushing in the same direction?

Note the ordering. The contribution question comes **after** the accuracy question and is asked open. Do not send the programme's own contribution claim as a premise and ask whether the substantiator agrees. That is a leading question and it gets a polite yes. Ask what contributed. Then compare their answer with the programme's claim, and record both.

Say at the outset what will be attributed. Substantiators speak more freely when they know their name will not appear beside a criticism of a ministry they still work with. Anonymised substantiation counts, so long as the harvester holds the record.

## What counts as adequate

Minimum: one informed source independent of the programme, with a documented response, per substantiated outcome.

Better, and worth the effort where the claim is heavy or contested: two independent sources, or one source plus a document.

Insufficient, and this comes up constantly:

- A second person from the same organisation as the informant who supplied the outcome.
- The programme's own partner confirming an outcome about the partner's own work, where the partner is funded by the programme. That is the social actor, useful for the fact and not independent on contribution.
- A general endorsement of the programme rather than a response to the specific statement.
- A verbal "yes that sounds right" with no record of who said it or when.

Record for every substantiation attempt: who was approached, their relationship to the outcome, the date, whether they replied, and what they said. The non-responses are part of the record.

## When the substantiator disagrees

Four cases, and they are handled differently. The commonest mistake is to collapse all four into "resolve the discrepancy", which loses the most informative material in the dataset.

**They correct a detail.** Amend the statement. Record the amendment, who made it and when, and keep the original wording in the version history. Detail corrections are the normal case. They are a sign the process is working.

**They dispute the contribution.** Expected, and often the most interesting result in the harvest. Do not average the two accounts into a single "agreed" contribution level. Record both as separate claims with their sources and carry the disagreement into the analysis. A pattern of substantiators naming other causes is itself a finding. A harvest where every substantiator confirmed the programme's contribution should raise suspicion about who was asked.

**They deny the change happened.** Investigate before doing anything else. In most cases the statement was drafted too broadly, or the date was wrong, or two similar changes were conflated. A corrected statement then resolves it. If it survives investigation and remains contested, either drop it, or keep it flagged as contested with both accounts recorded. Never keep it in the counted set as though it were verified.

**Two substantiators disagree with each other.** Record both. Where the analysis needs a single value, apply a rule decided in advance: for instance, a documentary record settles the fact, the third-party account is preferred on contribution, and where two testimonies conflict the more conservative reading is taken. Write the rule down before applying it to a case, because a rule invented while looking at a specific disagreement is a decision about that case wearing a rule's clothes.

## Deduplication and merging

Harvests over-count. The same change appears in a quarterly report, an annual report, two interviews and a press cutting, described four different ways.

**Dedupe on actor plus act plus date window.** Never on wording. Same actor, same behaviour, overlapping dates, is one outcome carrying four sources. Multiple sources for one outcome is a strength. Record it as a field, because it feeds the substantiation triage above.

**Do not merge across actors.** "Three ministries adopted the tool" collapses three separately verifiable, separately contributed-to changes into one row, and loses the actor count, which is the denominator you most want (see [analysis](outcome-harvesting-analysis.md#the-denominator-problem)). Keep them as three unless the adoption was a single collective act.

**Do not merge a chain into one statement.** If actor A's change led to actor B's change, those are two outcomes with a relationship between them. Collapsing them into "the reform cascaded through the sector" destroys the causal information. That is the very thing anybody reading the harvest wants. Record the relationship as a field (`follows_from: <outcome id>`) and keep the outcomes separate. This is the point where a causal mapping representation does the job better than a flat outcome table, and where a harvest run alongside causal coding of the same sources gives you both the endpoints and the paths.

**Split where the statement holds two acts or two actors.** Split a long drift into dated instalments only where each instalment is separately verifiable. Otherwise keep one statement with a date range covering the whole drift.

**Log every merge and split, with the ids involved.** The counts in the report depend on these decisions. A careful reader will ask how 140 candidate statements became 91 outcomes. That question should have an answer in a table rather than in somebody's memory.

## The contribution claim

At harvest time, the contribution field records **what somebody says the programme did, and who says it**. That is all it is.

Why it cannot be a finding yet. Nobody has tested alternative explanations. The claimant usually has an interest, whether that is the programme reporting on itself or a partner reporting on a funder. And a single actor's account of why they acted is evidence about their reasoning. Evidence about what caused the change is a different thing.

So the field holds three items and never a score:

- The contributory action: what the programme is said to have done.
- The claimant: who says so, and their relationship to the outcome.
- Other causes named: what else the claimant or the substantiator credited.

**Classify the contributory action by type rather than rating its strength.** A type can be counted, crossed against other fields, and checked back against the source. A strength score is a judgement made once, by one person, that nobody downstream can audit. A workable set of types:

| Type | What the programme is said to have done |
|---|---|
| `funded` | Paid for the activity or the actor |
| `convened` | Brought parties together who would otherwise not have met |
| `drafted` | Supplied specific text, analysis or a tool that was adopted |
| `evidenced` | Supplied research or data that was used in a decision |
| `trained` | Built a skill that was then applied |
| `brokered` | Introduced or connected actors |
| `legitimised` | Lent standing, so an actor could act |
| `advocated` | Argued publicly or privately for the change |

Types can be counted, crosstabbed against outcome type and actor type, and compared against what the theory of change predicted. A pattern such as "the programme's claimed contribution is `convened` in 22 of 31 policy outcomes and `funded` in almost none" is a finding worth reporting. An average contribution score of 3.4 is not.

**Turning claims into findings needs a different method.** Independent substantiation strengthens a claim. It does not establish contribution. To go further you need something that tests alternatives: contribution analysis assembling and stress-testing a contribution story, process tracing on selected cases, or a comparison across cases where the programme was present and absent. Each of those is additional data collection. See [combining with other methods](outcome-harvesting-analysis.md#combining-with-other-methods).

## Timing and effort

Substantiation depends on other people replying, so it cannot be compressed by working harder.

- Allow two to four weeks per chasing round, and plan two rounds.
- Send small batches. Ten statements to one person gets no reply. Two gets a reply.
- Chase twice, on a schedule. Record every chase.
- Documentary substantiation runs in parallel and costs no waiting. Do all of it first. It often removes a third of the list before you email anybody.
- Build the fallback into the plan before the first email goes out: what the report says about statements nobody confirmed.

## As a plan

Substantiation itself happens outside the six pieces. No piece sends anything, waits for a reply, or reads an informant's answer as it arrives. A reply becomes usable once it is among the documents; from that point a code step reads it like any other document, with columns for whether it confirms, corrects or disputes the statement, and for what else it names as a cause.

That new row sits beside the original rather than replacing it, because a code step produces fresh rows in its own table and amends nothing. So a correction, a disputed contribution and a denial each turn up as rows in a second table rather than as edits to the first, and an answer that reports a substantiated statement cites both, saying plainly which row is the original draft and which is the substantiator's reply.

Deduplication and merging have no piece of their own either. Grouping an actor column into named actors, each row's actor recorded as a nominal column, normalises wording but is not a decision that two rows describe one outcome: that judgement, actor plus act plus an overlapping date window, is made by whoever writes the answer, reading the rows and documents and citing the ones treated as one event. A design that tabulates before this judgement is made counts the same change once for every source it was reported in.

The contribution field carries over as two kinds of column. `contribution_type`, drawn from the closed list above (funded, convened, drafted, evidenced, trained, brokered, legitimised, advocated), is a nominal column, each value defined tightly enough that another coder would place the same claim the same way; where a claim sits between two types, the row says so. The contributory action in its own words and the claimant's name stay free text, counted only by the type they were classified under and never scored or averaged into a figure nobody could trace back to a claim.
