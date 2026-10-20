# Generic evaluation questions: efficiency and timeliness

A plan for judging how quickly and economically an intervention turned resources into outputs: milestone slippage, procurement and administrative friction, and how fast management moved resources to unblock the work. It reads workplans, progress reports, reviews, partner interviews and procurement audits, and guards against full disbursement taken for delivery on time.

Back to [generic evaluation questions](generic-evaluation.md), for what the criterion pages share and for the works cited.

## Scope, and the contrast inside the corpus

The 2019 definition asks "How well are resources being used?": "The extent to which the intervention delivers, or is likely to deliver, results in an economic and timely way" (OECD DAC 2019, p. 10). Its note defines "economic" as the conversion of inputs ("funds, expertise, natural resources, time, etc.") into outputs, outcomes and impacts "in the most cost-effective way possible, as compared to feasible alternatives in the context"; "timely" delivery as "within the intended timeframe, or a timeframe reasonably adjusted to the demands of the evolving context"; and adds that efficiency "may include assessing operational efficiency (how well the intervention was managed)" (OECD DAC 2019, p. 10). In a qualitative corpus the documents speak mostly to the second and third of these, which this page divides into three dimensions.

- **Timeliness and schedule integrity.** Whether milestones were met as planned, where delivery was delayed, and what the delay did to the quality of the outputs.
- **Procedural and administrative friction.** The transaction costs of the organisation's own bureaucracy, complex procurement, heavy compliance overhead and long donor clearance cycles.
- **Allocative responsiveness.** How quickly and flexibly management moved money and people to clear bottlenecks or respond to changing conditions.

The cost-effectiveness comparison "with feasible alternatives" needs cost data the documents rarely hold; the 2021 guidance sets out the challenges of evaluating efficiency (OECD 2021, pp. 58 to 63, Table 4.4 on p. 61).

A frequent failure in qualitative efficiency reviews is treating disbursement as a proxy for speed. A project can disburse its whole budget and still deliver major infrastructure two years late, too late to serve the season it was built for. The contrast inside the corpus sets the milestone commitments in baseline workplans against the implementation timelines, procurement dates and accounts of friction in progress reports and field transcripts, on the attribute that says which phase each document belongs to.

## As a plan

**Sample.** Every document; where the corpus is too large to read whole, stratify by partner, so each partner's workplans and later reports are both read.

**Code.** A binary column for whether a passage reports a delay against plan; a nominal column for its domain (procurement, staffing, approvals and the like, each defined); an ordinal column for how critical it was to delivery, each level saying what counts; and a nominal column for where the passage puts the cause (the organisation's own procedures, a partner's operational capacity, a disruption from outside), recorded as the passage gives it rather than assumed. The coding prompt searches for delay on its own terms, never through any disbursement figure, so a well-spent budget cannot stand in for an absent search, and asks for the later reports to be read as closely as the inception plan, with the workplan never the default account of what happened. Define the critical levels tightly enough that another coder would place the same passage the same way; where the call is close, the answer says so.

**Tabulate.** Count documents reporting a critical delay by domain and by partner, each partner's count out of that partner's documents, and by phase, so what the inception workplan promised sits beside what the progress reports later recorded. A tabulation of cause by partner shows whether partners in the same setting put their delays down to the same things. Where the standard is about partners rather than documents, count partners (the tabulation's `count` set to the partner column, with "partners" as its unit), so a cell says how many partners reported a critical delay. Where the standard is about milestones, add a column naming the milestone a passage concerns, nominal with the workplan's milestones as its values where the workplan is to hand, and a profile step keyed by that column, with a `holds` column for a critical delay and a `distinct` count of `document`, gives each milestone one row however many reports mention it; a tabulation of the profile, with "milestones" as its unit, counts the milestones reported critically delayed. With the workplan's list as the values, every planned milestone is a row, and one no document mentions is a row of noes, which says nothing was reported about it, never that it was met.

**Judge.** Only with the evaluator's standard. A typical one is a `rule`, read worst-first: the overall reading is held down wherever a partner's documents reporting a critical delay pass the stated threshold, or, counting partners, wherever more than a stated number of partners report one, whatever the disbursement rate shows, because spending cannot outweigh delays that leave outputs unused. Without a standard, leave the judge out and offer standards in their terms without numbers.

**Write.** Each partner and domain with its count and base, the planned beside the reported, delays named with their documents, and causes attributed to whoever states them.

**What the workflow must say it cannot answer** (its `cannot_answer`).

- **Cost-effectiveness against alternatives**, which needs cost data and a comparison the documents do not hold.
- **Dates and money held only in a finance system or tracking sheet**, which the evaluator brings in when the report is written.
- **The share of milestones met**, since a milestone no document mentions is unknown rather than met, and without the workplan's list as the milestone column's values the base is only the milestones found.

Try the definitions on one partner's full set of reports before the rest, since the phasing of delay through a small corpus is where an ambiguous definition, such as what counts as critical, gets caught cheaply.

## What it guards against

Evaluators routinely meet what might be called exogenous excuse bias, where an implementing agency puts every delay down to shocks in the wider context. The cause column records, wherever a passage describes a delay or friction, whether the passage puts its cause in the organisation's own procedures, in a partner's operational capacity or in a disruption from outside. Counts of delay split by implementing partner show how partners differ: where several partners kept to schedule in the same volatile environment, a claim that the context made failure unavoidable is put in doubt. Read worst-first, timely delivery of outputs cannot outweigh serious administrative and financial friction left unresolved.

## Where Rubicon falls short

- **A milestone is a unit only through a profile.** A tabulation counts documents, cases a row names within its document, or the values of a document-list column such as partner, so a milestone that five reports mention counts in five documents. A profile keyed by a coded milestone column counts each milestone once, but its base is the milestones found unless the column's values are the workplan's own list, and even then "over 85% of milestones met" cannot be read from it, since silence about a milestone is not delivery.
- **Dates and money in a finance system are out of scope.** Planned against actual dates held in a tracking sheet, cost per output and disbursement numbers have no words behind them; the answer covers the part the documents speak to, and those numbers are brought in when the report is written. A delay or a cost stated in a report or an interview is in scope, since it has a speaker and a position in a document.

## Sources

The works cited for all the criterion pages are on [generic evaluation questions](generic-evaluation.md#works-cited). This page cites two OECD documents by page. The 2019 quotations and their printed pages were checked word for word against the PDF the New Zealand Ministry of Foreign Affairs and Trade hosts; the 2021 section and table pages were checked against the printed table of contents and the pages themselves in the PDF on oecd.org.

OECD DAC Network on Development Evaluation (2019). *Better Criteria for Better Evaluation: Revised Evaluation Criteria Definitions and Principles for Use*. OECD. The definition of efficiency, its note and Box 5 are on p. 10. Listed as [1] in the works cited.

OECD (2021). *Applying Evaluation Criteria Thoughtfully*. OECD Publishing, Paris. [doi.org/10.1787/543e84ed-en](https://doi.org/10.1787/543e84ed-en). The efficiency section runs from p. 58 to p. 63, with its table of challenges (Table 4.4) on p. 61. Listed as [2] in the works cited.
