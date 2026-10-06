# Qualitative comparative analysis

QCA finds which combinations of conditions go with an outcome across a set of comparable cases, using set theory rather than correlation. Charles Ragin devised it in *The Comparative Method* (1987) for the middle ground where there are too many cases to hold in the head and too few for statistics.

Subsidiary pages: [calibration](qca-calibration.md), [truth tables and solutions](qca-truth-tables.md), [in Rubicon](qca-in-rubicon.md).

## What it establishes

QCA licenses statements about set relations between conditions and an outcome, across cases. Two relations carry the weight. A condition is **necessary** when the outcome does not appear without it. A combination is **sufficient** when the outcome follows wherever the combination holds. Both are claims about the set of cases rather than about any one of them.

A finished analysis reads like this: across twenty-six district partnerships, the outcome appeared in two ways. Where local political backing was strong and a full-time coordinator was in post, the outcome followed whether or not the budget was protected. Where backing was weak, the outcome followed only where the budget was protected and a coordinator was in post. The coordinator appears in every path, so it looks necessary, which only a separate analysis of necessity can confirm.

That is a different claim from anything a regression makes, and the difference is the reason to use QCA at all. Three properties are built into the method.

**Equifinality.** Several distinct routes reach the same outcome. Averaging across cases hides them, because a condition that matters enormously on one route and not at all on another shows up as a weak average effect.

**Conjunctural causation.** Conditions work in combination. Where backing is weak, a coordinator with no budget achieves nothing, a budget with no coordinator achieves nothing, and the two together achieve the outcome. Set relations express that directly; an interaction term expresses it awkwardly and only for the combinations somebody thought to specify.

**Asymmetry.** The recipe for the outcome's absence is rarely the negation of the recipe for its presence. Failure has its own routes and they must be analysed separately, which is why every competent QCA reports an analysis of the negated outcome as well.

What QCA does not establish: an effect size, a probability, a counterfactual for any individual case, or a mechanism. It says which configurations go with the outcome across the set. Why any one case turned out as it did is a within-case question, and process tracing is the instrument for it.

## When it fits, and when it does not

It fits where the cases number roughly ten to fifty, belong to one defined population, with the outcome varying across them. It fits where programme theory already suggests that things work in combination. And it fits where you have, or can build, a case study for each case, because calibration needs substantive knowledge of each one.

The second half matters more, and evaluators ask for QCA in these situations constantly.

**One programme with twenty interviews is one case.** This is the commonest error and it is worth refusing plainly. A QCA case is the thing the outcome varies over: a district, a partner organisation, a grant, a country office, a school. Twenty transcripts about a single programme give one case with twenty sources, and no amount of coding turns transcripts into cases. Somebody asking for QCA on that material wants contribution analysis or process tracing.

**Fewer than about ten cases.** The truth table is then almost entirely empty and the solution comes mostly from assumptions about combinations nobody observed. Possible, occasionally worth doing, and it has to be reported as what it is.

**Conditions that cannot be got below about seven.** Six conditions make sixty-four logically possible combinations; thirty cases fill at most thirty of them and in practice far fewer, because cases cluster. Beyond that point [limited diversity](qca-truth-tables.md#limited-diversity-is-the-central-fact) decides the answer. Marx's benchmark work on how many conditions a given number of cases will bear is the reference here, and the constraint amounts to this: condition selection is theory work done before the data are touched. Somebody with eleven conditions they care about has two thousand and forty-eight rows: either cut to five or six on theoretical grounds, or run the analysis in stages with a small model at each stage, saying that is what you did.

**An outcome that barely varies.** Eighteen of twenty cases succeeded, so there is nothing for the method to discriminate. Check this first. It costs almost nothing and it stops the whole analysis before any of the expensive work. What can be offered instead is an analysis of the two that did not succeed, treated as deviant cases, which is a small-N question rather than a comparative one.

**Cases that are not comparable, or not independent.** If the cases do not belong to one population under a stated scope condition, a shared combination means nothing. If they contaminate each other, through shared staff or a single funder decision applied across several, the comparison is between things that were never separate.

**Anybody wanting a p-value or an effect size.** QCA produces consistency and coverage, which are set-theoretic measures, and reading them as significance is a category error.

**Anybody wanting the conditions ranked by importance.** QCA produces set relations rather than weights. Coverage says how much of the outcome each path accounts for, which is the nearest thing available. It is a property of paths rather than of individual conditions.

## What data it needs

Per case, enough material to calibrate the outcome and every condition. That usually means a case study, a structured file, or a set of interviews and documents belonging to that case and identifiable as such. The corpus therefore has to be organised by case before anything else happens, which is the practical constraint people underestimate.

Calibration also needs knowledge from outside the data. Deciding what counts as strong political backing in this sector is a substantive judgement. Taking the anchor from the spread of the cases in hand makes membership relative to the study rather than to the world. The [calibration page](qca-calibration.md) covers why that matters more than any other choice in the analysis.

Effort is distributed unevenly. Once the table is calibrated, the analysis takes minutes in any of the standard packages. Getting to a calibrated table is most of the work, and it is the part a report usually says least about.

## The steps in practice

1. Define the population and the scope condition. Which cases, and what makes them one set.
2. Choose the outcome, calibrate it across all cases, and check that it varies. Stop here if it does not.
3. Choose conditions. Few, theoretically motivated, and none of them a restatement of the outcome.
4. Calibrate every condition, recording the anchors and the reasoning.
5. Analyse necessity, separately and before sufficiency, with relevance reported alongside consistency.
6. Build the truth table. Set the consistency and frequency thresholds, and write down why.
7. Minimise, choosing and stating a stance on counterfactuals.
8. Report consistency and coverage for the solution and for each path.
9. Return to the cases. Name a typical case for each path, and examine the deviant ones.
10. Test robustness against the thresholds and the calibration, and report what moved.

Steps 5 to 8 are mechanical and take minutes. Steps 1 to 4, then 9 and 10, are the analysis.

## Who does what

The evaluator defines the population, selects the conditions, sets the calibration anchors, chooses the thresholds and decides which counterfactual assumptions are tenable. Every one of those is a substantive judgement that changes the result, which is why a QCA that reports only its solution formula cannot be assessed by anybody.

The software minimises the truth table and computes parameters of fit. That part is deterministic and uninteresting.

The commissioner should agree the scope condition and the definition of the outcome, and ideally the calibration anchors, before the cases are scored. Agreeing a workflow before any reading exists for exactly that ordering, and QCA is the method where it pays most, because calibration set after somebody has seen how the cases fall is unfalsifiable. The agreement itself is a conversation with the commissioner that no workflow can hold: the workflow drafts the outcome definition and candidate anchors with their descriptors, and a Rubicon run can stop once those are written and a few cases coded, so the commissioner agrees what each anchor means before every case is scored.

## Traps

Each comes with a test somebody can apply to a draft. Most of them produce a solution formula that looks exactly like a good one, which is why the tests matter.

- **Interviews treated as cases.** Twenty transcripts from one programme analysed as twenty cases. Test: does the outcome vary across the things being called cases? Could each one have turned out differently on its own? If every unit belongs to one programme in one period, the study has one case.
- **Too many conditions for the number of cases.** Test: count the populated rows against the total. Under a quarter, the solution is mostly counterfactual whatever stance you take on remainders. Report the fraction.
- **Calibration anchored on the sample.** Crossover at the median, full membership at the top quartile. Test: would any case's membership change if a different case were dropped from the study? A yes means the anchors are internal and the set labels do not mean what they say.
- **Raw scores used as memberships.** Raw scores are not set memberships, and the crossover is where the analysis happens. Skipping calibration means the crossover falls wherever the measurement scale happens to put it.
- **A condition that restates the outcome.** Programme effectiveness as a condition for programme success. Test: could somebody calibrate the condition while blind to the outcome? If not, the analysis is circular and will produce a beautiful solution.
- **Thresholds chosen after seeing the solution.** Test: was the consistency threshold written down before the truth table was built? A plan agreed before the reading answers this; nothing else does, because a threshold set afterwards is indistinguishable from one set beforehand.
- **Contradictory rows deleted or a case dropped.** Test: does the number of cases in the truth table match the number in the study? Any gap needs an explanation in the text.
- **Necessity read off the sufficiency solution.** A condition appearing in every path is asserted as necessary. Test: is there a separate necessity analysis, with its own consistency numbers? Appearing in every path is suggestive and is not the test.
- **Trivial necessity reported as a finding.** A condition present in almost every case passes the necessity threshold and means nothing. Test: is relevance or coverage of necessity reported alongside consistency? What is the skew of that condition?
- **The parsimonious solution reported alone.** Test: are the simplifying assumptions listed? Where they are not, the reader cannot tell which parts of the formula came from cases and which from combinations nobody observed.
- **Coverage ignored.** Consistency 0.93 reported as the headline with coverage 0.18 in a footnote. Test: what share of the outcome does the solution account for? A reliable route almost nobody took is a different finding from a route that explains the population.

## What good looks like

A reader can see the population and why those cases and no others. The calibration anchors are stated for every set, with the reasoning, so a reader could reproduce the memberships from the raw material. The truth table is shown, including the rows with no cases and the rows that contradict. Necessity is reported separately from sufficiency. The counterfactual stance is named and the simplifying assumptions listed. Consistency and coverage appear for each path. Low coverage is discussed rather than buried. Deviant cases are named and examined. Robustness checks are reported with what changed.

A QCA that can be assessed contains, in some order: the population and scope condition; the case list; the outcome definition and its calibration; each condition, why it is in the model, and its calibration anchors with descriptors; the distribution of calibrated values; the necessity analysis with consistency and relevance; the full truth table including empty and contradictory rows; the thresholds and the reasoning for them; the directional expectations; the intermediate solution with the parsimonious core marked; consistency and coverage per path and overall; the simplifying assumptions used; typical and deviant cases per path; and the robustness checks with their results. That list is long, and most of it is short. The calibration section is the one that gets cut and the one that should not be.

A QCA missing the calibration detail is not assessable, whatever else it contains.

## Combining it with other methods

QCA gives cross-case patterns and nothing about mechanism, so it pairs naturally with a within-case method. Schneider and Rohlfing set out how the two fit together formally: the QCA solution identifies which cases are typical of a path and which are deviant. Process tracing then examines a small number of them to see whether the mechanism the path implies is actually there. Selecting cases for process tracing from the truth table rather than by convenience is the part that makes the combination worth the trouble.

Contribution analysis runs the other way round. Where a contribution story has been assembled for each of many similar cases, QCA can test whether the conditions the story relies on really do sort the successes from the failures.

## Sources

Ragin, C. (1987). *The Comparative Method: Moving Beyond Qualitative and Quantitative Strategies*. University of California Press.

Ragin, C. (2000). *Fuzzy-Set Social Science*. University of Chicago Press.

Ragin, C. (2008). *Redesigning Social Inquiry: Fuzzy Sets and Beyond*. University of Chicago Press. The calibration chapters are the ones to read.

Schneider, C. and Wagemann, C. (2012). *Set-Theoretic Methods for the Social Sciences: A Guide to Qualitative Comparative Analysis*. Cambridge University Press. The standard reference for parameters of fit, the enhanced standard analysis and what makes a counterfactual untenable.

Rihoux, B. and Ragin, C. (eds) (2009). *Configurational Comparative Methods*. Sage.

Oana, I., Schneider, C. and Thomann, E. (2021). *Qualitative Comparative Analysis Using R: A Beginner's Guide*. Cambridge University Press.

Marx, A., on benchmarks for how many conditions a given number of cases will support without random data producing a solution. Year not verified here.

Befani, B., *Pathways to Change: Evaluating Development Interventions with Qualitative Comparative Analysis*, for the Swedish Expert Group for Aid Studies. The standard reference for QCA in evaluation rather than in comparative politics. Year not verified here.

Schneider, C. and Rohlfing, I., on set-theoretic multi-method research, for combining QCA with process tracing.

Software: the R packages `QCA` (Duşa) and `SetMethods` (Oana and Schneider), Ragin's fsQCA, and Tosmana for crisp and multi-value sets.
