# Probative value: which findings deserve a stronger check

A finding is worth checking in proportion to how easily a few misread cells or a missed passage would change what it says, so a count of 45 of 50 can stand as read while a "none of the ten" needs a second look.

Ask for this page when planning where a run should look hardest, when deciding which findings need a stronger check, and when saying how sure a finding is. The four evidence tests and the ratio behind them are on the [evidence tests page](process-tracing-evidence-tests.md), and how much has to be read before an absence or a share can be relied on is on [reading enough](reading-enough.md). This page takes the same logic to counts, groups and zeros, which is where most Rubicon findings live.

## What probative value is

A piece of evidence is worth as much as it discriminates. Two probabilities decide that: how likely the evidence is if the claim is true, and how likely it is if the claim is false. Befani and colleagues call the first the sensitivity and the second the type I error, borrowing the terms from diagnostic testing (CECAN note; Befani and Stedman-Bryce 2017). Their ratio, the likelihood ratio, is the probative value. Bennett puts it plainly: "It is the relative likelihood of the evidence under the alternative explanations, or the 'likelihood ratio,' that matters, not the absolute likelihood" (Bennett 2022). Fairfield and Charman take its logarithm, following Good, and call that the weight of evidence, which "describes the probative value of the evidence—how strongly it discriminates between two rival hypotheses" (Fairfield and Charman 2017).

Three consequences hold even where nobody writes a number down.

- **Evidence that fits the claim is worth little if it would turn up anyway.** A respondent from the programme saying the programme helped has high sensitivity and a high type I error, so its ratio is near one. Befani found that a low type I error moves confidence much more than a high sensitivity when the evidence is actually observed, while sensitivity matters most when the evidence is looked for and not found (Befani 2021, section 2).
- **"False" means a named rival, not everything else.** Fairfield and Charman advise comparing a hypothesis "against clearly delineated rivals, rather than its unspecified logical negation", because the negation of a specific claim is too vague for anybody to say how likely the evidence would be under it (Fairfield and Charman 2017). This is why [contribution analysis](contribution-analysis.md) and [process tracing](process-tracing-in-rubicon.md) both search the rivals at the same effort as the programme.
- **A search that could not have found the evidence does not carry any probative value when it finds nothing.** Its sensitivity is low, so the absence is almost as likely whether the claim is true or false. IIED's brief states the practical form: "Absence of evidence has little inferential value; on the other hand, evidence of absence can challenge a contribution claim" (IIED 2017).

## A count is evidence too, and its words are the hypotheses

A Rubicon finding is usually a count put into words: "most of the trainees", "none of the managers", "more often in the north". Each word is a claim, and the count is the evidence for it. The question to ask of a count is this: could a plausible handful of wrongly read cells, or a passage the reading missed, change the word?

**45 of 50 said yes.** "Most" fails only if the count falls to 25, so 20 of the 50 cells would have to be wrong in the same direction. A reading that gets 96% of cells right, which is about what model coding of long interviews has achieved in Rubicon's own tests, puts the expected number of wrong cells in 50 at about two. No plausible error turns 45 into 25, and it does not matter whether the true figure is 39 or 48. The word is robust, and a second check would cost money without any prospect of changing it.

**0 of 10 said yes.** "None" fails if one cell is wrong. Two things make a zero weaker evidence than it looks.

- **Sampling.** If the true share among people like these were one in ten, a group of ten would still show nobody about a third of the time (0.9 to the tenth power is 0.35). A zero from ten cannot rule out a share of about a quarter: 0.74 to the tenth power is 0.049. This is the "rule of three" from medical statistics, where no event in n cases leaves the true rate at up to about 3 in n (Hanley and Lippman-Hand 1983), which is a rough guide at n = 10 rather than an exact bound.
- **The reading.** If the reader finds a real account 80% of the time, one real case goes unseen one time in five. So the likelihood ratio of a zero, for "nobody" against "exactly one person", is 1 to 0.2, or 5. That is a straw in the wind, not a hoop.

So "none of the ten" is the finding most worth checking, and the check that helps is one with high sensitivity for the missing case: a fresh reading of each document for that item, not a second opinion on the quotes the first reading kept, since a zero does not come with any quotes to reread.

**The general rule.** Call the smallest number of cells whose change would alter the finding's wording its margin. A finding is fragile where the margin is no larger than the number of wrong cells the reading can be expected to produce in its base. Medical trials have the same idea as the fragility index, the number of patients whose outcome would have to change to reverse a significant result (Walsh et al. 2014). Four kinds of finding usually have a margin of one or two.

- **A zero or a "none of"**: one missed case overturns it.
- **A small group**, three documents or fewer in Rubicon's convention, where one cell is a third of the group.
- **A count near a threshold** that the wording or a rubric's standard depends on: 27 of 50 is "most" by two cells.
- **A comparison between groups** whose difference is a few cells: swap two and the gap closes.

A count of all of a group, "every one of the twelve", is fragile in the same way as a zero, since one wrongly counted cell turns "all" into "all but one".

## As a plan

What follows is what the designer writes into the workflow before any code step runs, whichever method the workflow is for.

Before any document is read, the workflow gives the account being tested and each rival its own column, each stating what would be found and where; anything both would produce is dropped, since it discriminates between nothing. Both are coded in the same pass, at the same depth: one code step, or matched code steps, over the same sample, rather than one column asked of every document with its rival left to a thinner search, which is the symmetric-effort principle stated everywhere else in this knowledge base.

The designer decides in advance which findings will be fragile, said in the workflow's reasons: a question asked of a small group, a likely answer of "nobody", or a comparison of two small counts, so the stronger check for those, such as a second coder, an adjudicator or a trial first, is chosen before the numbers arrive rather than after. An absence counts as evidence only where a document was actually read for it: a tabulate step's base is the documents its sample drew, so a zero in a cell is stated against that base rather than left out, while a document never drawn into the sample carries no row and sits outside the base, so the two kinds of absence are not confused in a count that states what it is out of.

Recording the side of each passage is a coder's ordinary brief rather than a separate code step: where a thing has two sides the question keeps apart, the column has one value for each, so a tabulate step gives both the count supporting and the count cutting against from the one coding, with the documents nobody read for it left out of both rather than silently swelling the base on one side.

## Using it when reporting

- **State strength in words tied to the margin, not as a probability.** Befani's rubric maps posterior confidence to phrases, from "more confident than not" (0.50 to 0.70) to "practical certainty" (above 0.99) (IIED 2017, table 1), and the CECAN note recommends the IPCC's likelihood scale for eliciting such judgements. Both assume somebody has set priors and likelihoods. Rubicon sets neither, so a posterior it printed would be a guess dressed as a measurement. What a run can say is the count, its base, and how far the words sit from changing: "raised by 45 of the 50; no plausible misreading changes that most did", or "none of the 10 managers, a finding that turns on each of them".
- **Leave a robust count alone.** A report that hedges 45 of 50 as much as 0 of 10 teaches the reader to ignore the hedges.
- **Say which cells a fragile finding turns on.** For a zero or a small group, name the documents, so a reader can open them. For a count near a threshold, give the count and the threshold together.
- **Decline a finding the evidence cannot carry**, in a line: "Not reported: only 2 of the 30 documents bore on this, too few to say" (skill `counting-things`).
- **Give the strongest evidence against the finding**, and what would have changed it. These are the two sentences the [evidence tests page](process-tracing-evidence-tests.md#reporting-the-update) asks for, and they are how a reader sees that the search could have come out the other way.
- **Do not report a posterior, a likelihood ratio or decibels as a result.** Where an evaluator wants the explicit Bayesian version, the numbers are the evaluator's own judgement, written into the answer with what was assumed; the count tool does not multiply ratios (see [process tracing in Rubicon](process-tracing-in-rubicon.md)).

## What is built and what is planned

Built today:

- A tabulation names the documents it counted and the documents it did not, for the whole base and for each group of a column it is split by, so a zero on a small group comes with the documents behind it.
- A tabulation states a value that occurs in no document as a stated zero rather than a dropped row, out of the documents the sample read, so a zero is never made of documents nobody read.
- On a step whose column has fixed values, a second coder of another model family reads every document as well; a value only one of them places goes to an adjudicator who rules it from the whole document and the quoted passages; a ruling that fails stands as the first coder had it, counted as unruled rather than upheld.
- A document the second coder could not read in full is coded once, with the step's record listing it, so a failed second reading never shows as a disagreement.

Not built:

- **A computed margin.** Nothing works out a finding's margin and compares it with the expected number of wrong rows; the designer judges which findings are fragile from the kinds above, said in the workflow's reasons. Do not promise it.
- **An undecided value** for a column whose evidence is too thin.

Measured and not adopted: in Rubicon's tests, a second model checking every counted cell added about two thirds to the price and, against an independent reviewer, broke more cells than it fixed. A check has a sensitivity and a type I error of its own, and one whose errors are as common as the reader's carries little probative value, wherever it is pointed.

## The limits

- **Priors are arbitrary in this material.** Fairfield and Charman advise equal priors across the named hypotheses, or reporting likelihood ratios and letting readers supply their own (Fairfield and Charman 2017); IIED set every prior at 0.5, "equivalent to 'no information'" (IIED 2017). Either is a convention, not knowledge, and a posterior inherits it.
- **Precise numbers can be false precision.** Fairfield and Charman: "quantification may simply disguise that ambiguity with false precision" (Fairfield and Charman 2017). The CECAN note lists the biases expert estimates carry, anchoring and a preference for a good story among them, and names probability estimation as the method's main weakness in both its case studies.
- **Independence usually fails.** Likelihood ratios multiply only across independent evidence, and interviews from one office, or passages from one talkative respondent, are not independent. Befani treats this under evidence packages, which she calls one of the most troublesome practical issues (Befani 2020).
- **The practice has run ahead of the principle.** Zaks examines the claims made for Bayesian process tracing, that it enables inference from iterative research and guards against confirmation bias, and finds gaps between principle and practice (Zaks 2021).
- **The margin is not a significance test.** It says how many cells a wording turns on, given an error rate measured on a bench corpus that may not match this one. It does not say whether a difference between groups would hold in another draw, which is a question for a test of chance, with the caveats on the [equity page](generic-evaluation-equity-and-differential-reach.md#whether-a-difference-could-be-chance).

## Sources

Befani, B. and Stedman-Bryce, G. (2017). 'Process Tracing and Bayesian updating for impact evaluation'. *Evaluation* 23(1): 42-60. [SAGE](https://journals.sagepub.com/doi/abs/10.1177/1356389016654584). Read through its abstract and the two notes below; the article itself was not read.

Befani, B., Rees, C., Varga, L. and Hills, D. (2016). *Testing Contribution Claims with Bayesian Updating*. CECAN Evaluation and Policy Practice Note 2.1. [PDF](https://www.cecan.ac.uk/wp-content/uploads/2020/08/EPPN-No-02-Testing-Contribution-Claims-with-Bayesian-Updating-.pdf). Sensitivity and type I error, expert elicitation and its biases, the IPCC scale, the weakest-link rule for a mechanism.

IIED (2017). *Process tracing with Bayesian updating*. Better Evidence in Action brief 17402IIED. [PDF](https://www.iied.org/sites/default/files/pdfs/migrate/17402IIED.pdf). The confidence table credited to Befani and Stedman-Bryce, priors at 0.5, the Bwindi application. No author is named on the brief.

Befani, B. (2020). 'Diagnostic evaluation and Bayesian Updating: Practical solutions to common problems'. *Evaluation* 26(4): 499-515. [PDF](https://ueaeprints.uea.ac.uk/id/eprint/77491/1/Published_Version.pdf). "Love-to-see" and "hate-not-to-see" evidence, ranges instead of point estimates, evidence packages, rubrics where estimates cannot be had.

Befani, B. (2021). *Credible Explanations of Development Outcomes: Improving Quality and Rigour with Bayesian Theory-Based Evaluation*. EBA Report 2021:03, Expert Group for Aid Studies, Sweden. [PDF](https://eba.se/app/uploads/2021/10/EBA-report-2021_03_webb_tillganp.pdf). The relative weight of sensitivity and type I error, the "translator rubrics". Read in extracts only.

Fairfield, T. and Charman, A. E. (2017). 'Explicit Bayesian Analysis for Process Tracing: Guidelines, Opportunities, and Caveats'. *Political Analysis* 25(3): 363-380. [Author version](https://researchonline.lse.ac.uk/id/eprint/69203/2/Fairfield_Explicit%20bayesian%20analysis_author_2017%20LSERO.pdf). Rivals instead of the negation, weight of evidence in decibels after Good (1985), priors, caveats. Their book, *Social Inquiry and Bayesian Inference: Rethinking Qualitative Research* (Cambridge University Press, 2022), develops the same approach and was not read.

Bennett, A. (2022). 'Process Tracing for Program Evaluation'. In J. Widner, M. Woolcock and D. Ortega Nieto (eds), *The Case for Case Studies: Methods and Applications in International Development*, Cambridge University Press, chapter 9: 195-218. The likelihood ratio, and the asymmetry of hoop and smoking-gun tests.

Humphreys, M. and Jacobs, A. M. (2015). 'Mixing Methods: A Bayesian Approach'. *American Political Science Review* 109(4): 653-673. Generalises Van Evera's tests by letting a clue's probative value be continuous and uncertain. Read through summaries only.

Zaks, S. (2021). 'Updating Bayesian(s): A Critical Evaluation of Bayesian Process Tracing'. *Political Analysis* 29(1): 58-74. Read through its abstract only.

Hanley, J. A. and Lippman-Hand, A. (1983). 'If Nothing Goes Wrong, Is Everything All Right? Interpreting Zero Numerators'. *JAMA* 249(13): 1743-1745. [PubMed](https://pubmed.ncbi.nlm.nih.gov/6827763/). The rule of three.

Walsh, M., Srinathan, S. K., McAuley, D. F. and colleagues (2014). 'The statistical significance of randomized controlled trial results is frequently fragile: a case for a Fragility Index'. *Journal of Clinical Epidemiology* 67(6): 622-628. [Article](https://www.jclinepi.com/article/S0895-4356(13)00466-6/fulltext).

The four tests themselves are Van Evera's, *Guide to Methods for Students of Political Science* (Cornell University Press, 1997); their Bayesian reading is on the [evidence tests page](process-tracing-evidence-tests.md).
