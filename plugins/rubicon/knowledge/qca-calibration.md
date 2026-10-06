# QCA: calibration

Calibration in QCA turns raw material into set membership; this page covers what a membership score means, crisp and fuzzy sets, the direct and indirect methods, calibration as rubric work, and how it goes wrong. Calibration is where a QCA result is made. It is also the step reports say least about, and the one where writing the anchors down before scoring, and citing the passages behind each score, does most for a reader.

Back to [QCA](qca.md).

## What a membership score means

A set membership runs from 0 to 1, and the numbers are qualitative anchors rather than a scale. Full membership is 1: the case is unambiguously in the set of cases with strong political backing. Full non-membership is 0. The crossover at 0.5 is the point of maximum ambiguity, where a case is neither more in than out nor more out than in.

Read that again, because it is where people go wrong. **0.5 is not a midpoint on a measurement scale.** It is the qualitative threshold separating in from out. A case at 0.51 belongs to the set; a case at 0.49 does not. Everything downstream turns on which side of the crossover a case falls, because truth table rows are corners of the vector space and a case is assigned to the corner where it holds membership above 0.5 on every condition.

A case sitting at exactly 0.5 cannot be assigned at all. Move it, then say in the write-up that you moved it and why.

## Crisp and fuzzy

A crisp set takes 0 or 1 only. Membership is a yes or a no, which suits conditions that really are binary: the law passed or it did not, the post was filled or it was vacant. Crisp sets make truth tables easy to read at the cost of every gradation.

A fuzzy set takes any value in between, and in practice most analysts use a small number of anchors rather than a continuum. A four-value set uses 0, 0.33, 0.67 and 1. Ragin's six-value set uses 0, 0.1, 0.4, 0.6, 0.9 and 1: fully out, mostly out, more or less out, more or less in, mostly in, fully in. Both give the analyst somewhere to put "mostly in but with reservations" without pretending to a precision the evidence will not support.

Take the four-value or six-value route for anything calibrated from text. A continuous score derived from qualitative material implies a resolution the material does not have, and it invites the reader to compare 0.71 with 0.68 as though the difference meant something.

## The direct and indirect methods

The direct method fixes three anchors on an underlying measure and interpolates between them: the value at which a case is fully in, the value at which it is fully out, and the crossover. Ragin's implementation uses a log-odds transformation between the anchors. It suits conditions with a numeric base, such as GDP per head or the share of a budget disbursed.

The indirect method assigns cases to qualitative levels first and fits a function to those assignments afterwards. It suits conditions calibrated from judgement.

For evaluation work over interviews and documents, neither of those is quite what happens. What happens is that somebody reads each case and decides which level it belongs to against a description of what each level looks like. That is a rubric, and calling it one changes what can be asked of it.

## Calibration is rubric work

A fuzzy set with six values and a description of each is a rubric with six levels and descriptors. The correspondence is exact, and it matters for three reasons.

A rubric can be written before the cases are scored, with a version history showing that it was. Calibration set after somebody has seen how the cases fall is the deepest problem in QCA practice, because the anchors can be moved until the solution comes out interpretable and nobody reading the report can tell.

A rubric can be argued with. An anchor stated as a number in a spreadsheet column is unarguable, because there is nothing to disagree with. An anchor stated as "the case is in this set when the responsible minister has publicly committed to the programme and officials at director level attend its meetings" is a claim somebody can dispute. That dispute is the useful part.

A rubric can cite. Where each case's level points at the passages behind it, a reader can check the calibration rather than taking it on trust. That is what [a coded row citing its passages](qca-in-rubicon.md) does, and it is the argument for calibrating that way rather than in a spreadsheet.

### A worked anchor set

The condition is local political backing, across district partnerships, calibrated as a six-value fuzzy set.

| Value | Descriptor |
|---|---|
| 1.0 | The district head has made a public commitment, budget has been allocated from district funds, and senior officials attend routinely. |
| 0.9 | Senior officials attend and act on what is agreed. No district money, but no obstruction either. |
| 0.6 | Officials attend when invited and the partnership is referred to approvingly in district documents. Attendance drops when other demands arrive. |
| 0.4 | Attendance is by junior staff and sporadic. The partnership is tolerated. |
| 0.1 | The district is aware of the partnership and takes no part in it. |
| 0.0 | The district has declined to take part, or has obstructed it. |

The crossover falls between 0.4 and 0.6, and the descriptors are written so that the difference between the two is the one a reader would care about: whether the district acts on the partnership or merely tolerates it. Write the crossover descriptors first and the extremes afterwards. The extremes are easy. They also carry almost no analytical weight.

## Where calibration goes wrong

**Anchors taken from the sample.** Setting the crossover at the median, or full membership at the 90th percentile, makes each case's membership depend on which other cases are in the study. Add a case and the memberships of cases already scored will move. Ragin's point is that calibration uses external standards, meaning knowledge about the world rather than about the sample, and the test is simple: would this case's membership change if a different case were dropped? If it would, the anchors are internal and the sets do not mean what their labels say.

There is a partial exception. Where no external standard exists, some analysts anchor on the observed distribution and say so explicitly. That is a weaker analysis reported accurately, which beats the same analysis reported as though the anchors came from theory.

**Skew.** After calibrating, look at the distribution. If nineteen of twenty cases sit above the crossover, the condition is close to constant and can discriminate almost nothing; it will also appear trivially necessary for everything. Skew is not a reason to move the anchor until it looks better. It is a finding about the population, and sometimes a reason to drop the condition.

**Calibrating the outcome carelessly.** Everything hangs on the outcome, and it deserves more argument than any condition. Where the outcome is itself contested, calibrate it more than once under different reasonable definitions, then see whether the solution survives.

**Letting the condition absorb the outcome.** If calibrating a condition requires knowing whether the case succeeded, the condition is a restatement of the outcome and the analysis is circular. The test is whether somebody could score the condition while blind to the outcome.

**Not reporting the anchors.** A QCA whose calibration is not reported cannot be assessed, whatever else it contains. This is the commonest reporting failure and the easiest to fix.

## What to record

For every set, including the outcome: the anchors with their descriptors, the reasoning behind the crossover, the source of any external standard, the distribution of the calibrated values, and any case that had to be moved off exactly 0.5. Where a case was hard to place, record why. Those are the cases a robustness check will come back to.

Record the version too. Recalibrating is legitimate and often necessary. A second version carrying a note that says what changed and why is the difference between revision and fudging.
