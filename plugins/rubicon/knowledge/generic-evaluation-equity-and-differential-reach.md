# Generic evaluation questions: equity and differential reach

A plan for judging whether access, retention and outcomes were shared fairly across vulnerable and marginalised groups, and whether the barriers they met were lowered. It reads field interviews, focus groups, beneficiary surveys and monitoring reports, and guards against a high aggregate count of participants hiding who was left out.

Back to [generic evaluation questions](generic-evaluation.md), for what the criterion pages share and for the works cited.

## Scope, and the contrast inside the corpus

Equity, and the principle of leaving no one behind, are standard requirements in current terms of reference, grounded in UN evaluation norms and in bilateral value for money frameworks [3]. Appraising equity means examining how the intervention's opportunities, resources and effects were distributed across groups in the population [6].

- **Differential access, participation and retention.** Whether marginalised cohorts, by gender, disability, indigenous identity, remoteness or economic status, reached services in proportion to their need [12].
- **Identifying and lowering structural barriers.** Whether the project's management looked for and reduced the obstacles to taking part, such as indirect costs, caring responsibilities, discriminatory social norms, physical inaccessibility and language [6].
- **The distribution of benefits and unintended burdens.** Whether marginalised groups gained something meaningful and lasting rather than a token place, and whether the intervention put unpaid labour or social risk on vulnerable cohorts without meaning to [3].

The critical failure in a qualitative equity assessment is what might be called aggregate masking: an evaluation reports that an intervention beat its enrolment target by 30%, and passes over the fact that participants came almost entirely from accessible urban elites while structurally disadvantaged groups were left out [9]. The plan disaggregates within the corpus [4]. A code step's column records which cohort each passage is about, and a tabulate step compares barriers, mitigation and outcomes across those cohorts, and across the columns the sources carry, such as gender, disability status and economic vulnerability tier [4]. How far such a comparison can be trusted is under [whether a difference could be chance](#whether-a-difference-could-be-chance).

## As a plan

A code step reads the same material for two cohorts, majority participants and the vulnerable cohort the plan names, with one coding prompt covering both so that the two cohorts are searched with the same depth rather than the vulnerable cohort's material being read more thinly because there is less of it, and columns recording a barrier, whether it was mitigated, and who benefited. A tabulate step gives mitigation and benefit by cohort, and the share of named barriers left unmitigated, against the number of passages or documents read for each cohort rather than a shared aggregate, which is what stops a high overall participation count masking a cohort left out.

A tabulation does not test whether a difference between cohorts could be chance. The write step states each cohort's count against its own base, which it does by construction, and does not report a gap between two small counts as a finding on its own.

Equity is a rule, worst-first, as the criterion requires: a judge step holds the reading at no better than tokenistic once more than a handful of barriers are left unmitigated, whatever the aggregate participation figure shows, because elite capture inside an aggregate is exactly the failure this criterion exists to catch, and a high overall count is never read as evidence against it.

The code step's `check` setting (off by default, and under test) has a second model reread every coded passage in its context against the coding instructions, keeping, recoding or dropping it with a reason. For it to catch a barrier coded as mitigated on the strength of a general programme activity, the coding instructions must say that the passage has to describe the mitigation reaching the cohort named. The coding prompt should ask that the vulnerable cohort's material be searched as hard as the majority's, and the write step's instructions should say that one cohort's larger base is never read as a stronger finding on its own, since every count already carries its own base.

A trial carries out the workflow on a handful of documents from each cohort before the full corpus runs, to catch a barrier definition too broad to fail.

## What it guards against

The central trap in equity evaluation is superficial representation: taking a name on an attendance register for meaningful inclusion [12]. A column records whether support was improvised by somebody or built into the programme, and counts split by cohort show the two apart, so that support somebody improvised is not counted as a barrier the programme lowered [4]. Counts of benefit by cohort and by gender show whether women or people with disabilities cluster among the marginal gains while men make up most of the substantive ones, as counts a reader can check against their bases [4]. Read worst-first, an intervention that reached high aggregate numbers while leaving barriers unmitigated is held at tokenistic inclusion [4].

## Whether a difference could be chance

Nothing in a tabulation tests whether a difference between groups could be chance. Where each case is one participant, such as one interview each, an exact test on the two counts (Fisher's, say) can be run by hand and means what it says, within the limit below. Where the count is of coded passages, several of which come from one focus group or interview, a difference between groups is not a difference between people at all, because a test would take each passage for another person, so no test applies. That is the answer to read before writing that women gained less than men.

The comparison an equity finding usually wants, completion or outcome across gender, is a count of cases split by the gender column where each source is one participant and the outcome is recorded for each.

The test assumes separate cases drawn from somewhere, and a corpus chosen for variety was not drawn. A difference the test calls possible chance is not established, however it looks in the table, and a sample of nineteen households that shows no difference is not evidence that the groups are alike [8].

## Where Rubicon falls short

- **A source column describes the source.** A column such as gender, disability status or economic vulnerability describes one person only where a source is one person's interview. A case is one document by default, so a project whose cases are really people, with several people to a source, cannot yet say so [4]. A cohort recorded on each coded row is the disaggregation that survives a focus group.
- **Access in proportion to need needs a denominator the documents rarely hold.** Whether a cohort reached services at a rate matching its need calls for the size of the cohort and the number served, which are usually recorded in monitoring data rather than in anything somebody said. The answer shows what the material says about access; the rates are brought in when the report is written [4].

## Sources

The numbers in square brackets refer to the works cited on [generic evaluation questions](generic-evaluation.md#works-cited).
