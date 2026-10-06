# QCA in Rubicon

Where the method maps onto a workflow of the six pieces (sample, code, group, tabulate, judge, write), where it does not, and what the workflow must say it cannot answer.

Back to [QCA](qca.md).

## As a plan

A QCA case is the unit the outcome varies over, not a document, so the corpus has to carry a document attribute naming the case before anything else runs; sampling or coding without it reads one programme's many documents as one case, the commonest error the method warns against. Where the evaluator has not said what the cases are, that is settled before a workflow is written rather than discovered by a group step reading the documents.

Calibration is a closed code step, one per condition and one for the outcome, whose column is ordinal with the rubric's anchors as its values, each defined by the descriptor a case must show to belong there, following the [calibration page](qca-calibration.md#calibration-is-rubric-work). The coder reads every document once for the condition and returns a row quoting the passage behind whichever anchor it supports; an anchor no passage reaches for a case is not a row, and the tabulation below is what turns that into a stated zero rather than a line left out. A case's own documents disagreeing about which anchor fits is a finding to keep rather than a tie to break by picking one row. Every anchor column has fixed values, so a second coder and an adjudicator apply: two coders who disagree will cluster near the crossover, where the descriptors are hardest to tell apart, and the adjudicator's ruling there is the second look the method already asks for near that point. The anchors and their descriptors are written before any case is read, from the evaluator's own standard or from literature; a four-value or six-value scale, the method's own preference for anything calibrated from text, is what an ordinal column's fixed values already are.

Group does not calibrate. A group step proposes items from the patterns in this corpus, which is exactly what the method calls anchoring on the sample: a case's membership would then depend on which other cases happened to be read, and the method's own test, whether a case's membership would change if another case were dropped, fails by construction. Group has a place only before calibration exists at all, drafting candidate conditions or a first sense of the population from open coding, never setting the anchors themselves.

Tabulate gives the raw truth table: a count of cases by their calibrated values on every condition and the outcome, each combination a cell, with a count of none included so an empty corner shows as zero rather than vanishing, and the distribution of each condition on its own for checking skew. That is the table's population, out of how many cases were read for that condition, which is as far as counting goes: it does not compute consistency, PRI or coverage, which are arithmetic over membership values rather than counts of cases sharing one, and it does not minimise the table into a solution.

Judge only applies where the evaluator layers a worth question on top of the calibrated conditions, with a standard of their own. The method's own verdict is the minimised solution with its parameters of fit, not a rubric reading, and pieces do not minimise.

Write reports the calibration, the anchors, their descriptors, the distribution, any case hard to place, and the truth table's population from the tabulation, and says plainly that the solution, its consistency and coverage, and the choice between the complex, parsimonious and intermediate forms are not computed here: the evaluator takes the calibrated table into a QCA package, such as R's `QCA` or `SetMethods`, fsQCA or Tosmana, for that, then brings the solution back for the pieces to read the cases it names.

## What the workflow must say it cannot answer

- Boolean minimisation and the three solutions: the pieces count and write, and do not run set-theoretic algebra on the calibrated table.
- Consistency, PRI and coverage, for necessity and for sufficiency: these need the membership values themselves, not a count of how many cases share one, and are the evaluator's to compute once the table is exported.
- A continuous fuzzy score: a coding column takes fixed values, so calibration here is the four- or six-value kind the method already recommends for text, never a score read to two decimal places.
- Selecting typical and deviant cases by path: that needs the minimised solution first; once it exists, a further code step can read the cases it names for what a path does or does not capture.
