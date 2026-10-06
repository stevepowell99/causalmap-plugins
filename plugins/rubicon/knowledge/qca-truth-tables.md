# QCA: truth tables, thresholds and solutions

The analytical half of QCA, which runs in minutes once the table is calibrated: the truth table, limited diversity, the consistency, PRI and frequency thresholds, necessity, the three solutions, parameters of fit, robustness and the return to the cases. Everything here is arithmetic except the decisions about thresholds and counterfactuals, and those decide the result.

Back to [QCA](qca.md). Before this comes [calibration](qca-calibration.md).

## The truth table

A truth table has one row for every logically possible combination of the conditions. Five conditions give thirty-two rows, six give sixty-four, seven give a hundred and twenty-eight. Rows exist whether or not any case falls in them, which is the point: the table is the space of possibilities, of which the cases occupy a part.

Each case is assigned to exactly one row. In a crisp analysis that is direct. In a fuzzy analysis a case belongs to the corner of the vector space where it holds membership above 0.5 on every condition, taking the condition where its membership exceeds 0.5 and the negation where it does not. A case at exactly 0.5 on any condition belongs nowhere, which is why the calibration page says to move it.

Each populated row then carries a consistency number: how well the cases in that row are a subset of the outcome. For fuzzy sets, sufficiency consistency is the sum across cases of the minimum of condition membership and outcome membership, divided by the sum of condition membership. A row where every case's outcome membership is at least its membership in the combination scores 1.

## Limited diversity is the central fact

Most rows have no cases. Twenty-five cases across five conditions could in principle fill twenty-five of thirty-two rows; in practice they cluster into eight or ten, because the world does not distribute cases evenly across logical possibilities. Everything left over is a **logical remainder**.

Remainders are where counterfactual reasoning enters. They are also the reason one truth table yields three different solutions. This is a property of the world rather than a flaw in anybody's design. No analytical trick removes it. Adding conditions makes it worse at an exponential rate. Reporting the proportion of rows that carry cases is the minimum a reader needs.

## Thresholds, and how to set them

**Consistency.** The floor below which a row is treated as not sufficient. A common starting point is 0.75, with 0.8 more usual and higher preferred. Take the number off a shelf only as a last resort. Sort the populated rows by consistency and look for a gap: where the rows run 0.94, 0.91, 0.88, then 0.62, the threshold belongs in that gap and the data have told you where. Write the threshold down before building the table, or it becomes a dial to turn until the solution reads well.

**PRI.** Proportional reduction in inconsistency guards against a row that is a subset of both the outcome and its negation, which fuzzy sets allow and raw consistency does not catch. A row with high consistency and low PRI is inconsistent in a way the headline number hides. Report both. Treat a large gap between them as a reason to look at the row's cases.

**Frequency.** How many cases a row needs before it counts as observed. With fewer than about thirty cases the threshold is normally one, which means a single case can decide a path. With larger sets, raise it, then say what you raised it to. Rows below the threshold become remainders, so this choice moves cases out of the analysis and should be reported as such.

## Contradictory rows

A contradictory row holds cases with the same configuration and different outcomes. In a crisp analysis they show up plainly; in a fuzzy analysis they appear as a row with low consistency.

Treat a contradiction as information. It says one of four things: a condition is missing from the model, the calibration of some case is wrong, the cases differ in a way the conditions do not capture, or the outcome is measuring more than one thing. All four are worth knowing. All four are found by going back to the cases in that row and reading them.

Never resolve a contradiction by deleting the row or dropping a case. The check a reader can run is whether the number of cases in the truth table matches the number of cases in the study.

## Necessity, separately and first

Necessity is a different relation from sufficiency and is not readable off a sufficiency solution. Run it separately, before the truth table, one condition at a time, plus any theoretically motivated disjunction.

Necessity consistency is the sum across cases of the minimum of condition and outcome membership, divided by the sum of outcome membership. The conventional floor is 0.9, higher than for sufficiency, because a necessary condition claim is strong.

Consistency alone is not enough. A condition present in almost every case will pass the test trivially: if every district in the country has a health office, having a health office is necessary for every health outcome and says nothing. Schneider and Wagemann's relevance measure exists for this, and coverage of necessity does similar work. Report one of them alongside consistency. Treat a highly skewed condition as a candidate for trivial necessity before anything else.

## Minimisation and the three solutions

Minimisation applies Boolean algebra to the rows above the consistency threshold, reducing them to the shortest expression that covers them. Where two rows differ in one condition and share the outcome, that condition drops out. The procedure is deterministic, and every standard package implements it the same way.

What varies is the treatment of remainders, and it produces three solutions from one table.

**The complex solution** uses no remainders. It stays inside what was observed, which makes it the most conservative and usually the longest and least interpretable expression.

**The parsimonious solution** uses every remainder that helps to shorten the expression, including combinations nobody would defend as plausible. It is short, readable and rests on assumptions the analyst never inspected. Reporting it alone is a reporting failure.

**The intermediate solution** uses only remainders consistent with stated directional expectations: for each condition, whether its presence or its absence is expected to contribute to the outcome. Those expectations come from theory. Write them down before the minimisation runs. Most published QCA reports the intermediate solution as the main result.

Schneider and Wagemann's **enhanced standard analysis** goes further and rules out remainders that are untenable whatever the directional expectations: those that contradict a claimed necessary condition, those that would require contradictory assumptions across the analysis of the outcome and its negation, and those describing combinations that cannot exist. Use it, then list the assumptions it left in.

The parsimonious solution retains value as a diagnostic. Conditions appearing in it survive every simplifying assumption, so they are the ones the data most insist on. Reporting the intermediate solution with the parsimonious core marked inside it is the convention worth following.

## Parameters of fit

**Consistency** for a term says how far the cases with that combination are a subset of the outcome. It answers whether the path works.

**Coverage** says how much of the outcome the term accounts for. Raw coverage counts the outcome membership the term covers; unique coverage counts what it covers that no other term does. A path with unique coverage near zero is doing no work the other paths were not already doing.

Both matter, and they trade off against each other. A solution with consistency 0.95 and coverage 0.15 describes a route that reliably works and that almost none of the successful cases took. That is a finding, and it is a different finding from the one most readers will take from a high consistency number on its own.

## The negated outcome

Analyse the absence of the outcome separately, with its own truth table and its own solution. Because causation here is asymmetric, the result will rarely be the negation of the first solution, and the differences are often the most useful part of the analysis for a programme deciding what to do.

Running it also catches a class of error. Where the same configuration appears as sufficient for both the outcome and its absence, something is wrong with the model or the calibration.

## Robustness

A QCA solution is a function of the calibration anchors, the consistency threshold, the frequency threshold, the counterfactual stance and the set of cases. Vary each one. Report what moves.

The practical minimum: shift the consistency threshold by a step in each direction; raise the frequency threshold by one; drop each case in turn, or drop a small random subset repeatedly; recalibrate one contested set under its alternative anchors. Where the solution holds through all of that, say so. Where it changes at 0.78 but holds at 0.80, that belongs in the report. A reader is entitled to know the finding sits on a threshold.

Oana and Schneider have set out systematic robustness procedures for QCA, and their `SetMethods` package implements them. Reporting a bare solution formula with no sensitivity work at all is now hard to justify.

## Returning to the cases

The solution names paths. The cases behind each path are what make it meaningful, and QCA is a case-oriented method whatever the algebra suggests.

For each path, identify a **typical** case: high membership in the path and high membership in the outcome. Read it. Check the account makes sense as an instance of the path.

Then identify the **deviant** cases. Deviant for consistency means high in the path and low in the outcome: the recipe was followed and nothing happened. Deviant for coverage means high in the outcome and low in every path: the case succeeded by a route the model does not contain. Both are more informative than the typical cases. The second kind in particular tends to reveal the condition somebody left out.

This is the step most often skipped, and skipping it turns a case-oriented method into a small and badly powered statistical one.
