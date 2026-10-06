# Generic evaluation questions: coherence

A plan for judging internal coherence, with the agency's own policies and programmes, and external coherence, with government, other donors and civil society, from reports, minutes and partner interviews. It guards against the commonest fault in coherence findings, taking attendance at coordination meetings for synergy.

Back to [generic evaluation questions](generic-evaluation.md), for what the criterion pages share and for the works cited.

## Scope, and the contrast inside the corpus

The 2019 OECD-DAC revision made coherence a criterion in its own right, because development interventions work inside crowded systems of institutions that affect each other [1]. Terms of reference split it into two domains [9].

- **Internal coherence.** The synergy and consistency between the intervention and the other initiatives, strategies and normative commitments of the same implementing agency, ministry or donor, such as human rights, gender equality and environmental safeguards [9].
- **External coherence.** The consistency, complementarity and harmonisation between the intervention and the work of external actors in the same sector or geography, such as partner governments, bilateral donors and civil society organisations, and in particular whether the project adds something distinct or duplicates what others do and builds parallel administrative structures [9].

The main trap in a qualitative coherence evaluation is taking the absence of conflict for synergy [1]. Interventions often run in separate silos: they avoid open confrontation with other actors while duplicating supply chains, setting up competing local committees or bypassing existing municipal structures [9]. The plan looks for those tensions by contrasting the implementing agency's own records with external sector reviews and partner interviews, on the column that says which stakeholder group each document comes from [4].

## As a plan

A code step reads the strategic and coordination documents together with the partner interviews and government assessments, with one column recording which domain a passage concerns, internal policy synergy or external harmonisation and duplication, and an ordinal column for the interaction, from `friction_or_duplication` through `isolated_coexistence` and `active_coordination` to `programmatic_synergy`, each level's `means` stating what counts as coordination-meeting attendance and what counts as more than that, since the whole point of the ordinal scale is to stop attendance being read as synergy.

A tabulate step counts rows by that column, and by the source's own stakeholder group where the internal-external contrast is wanted, over the passages read rather than a share of a population. The coherence criterion is a rule: its judge step reads that tabulation and holds the verdict at no better than adequate wherever even one passage counted at `friction_or_duplication`, whatever the rest show, a threshold tried before any softer level is reached, which is the worst-first reading the criterion needs, applied by code rather than argued for case by case.

The code step's `check` setting (off by default, and under test) has a second model reread every coded passage in its context against the coding instructions, keeping, recoding or dropping it with a reason. It is worth trying here, since `active_coordination` is the level a coder is likeliest to award for mere attendance where the passage does not show pooled resources or joint delivery. The write step's instructions should say that the friction-and-duplication passages were searched for with the same effort in the implementing agency's own records as in the partner and government material, and that a count of coherence passages is a share of how much of the material records friction, not a count of separate frictions, since two documents describing one duplicated service are two passages rather than two problems.

A trial carries out the workflow on a handful of documents from each side of the contrast before the full corpus runs, mainly to catch an ordinal level worded broadly enough that nothing could fail it.

## What it guards against

The main weakness of coherence evaluations is coordination inflation: evaluators accept a list of working group meetings attended as proof of external coherence [9]. The ordinal levels are the guard: attendance on its own reads as active coordination, while programmatic synergy needs text showing pooled resources, joint delivery or formal data sharing [4]. Counts split by stakeholder group put side by side what implementers say about coordination and what line ministries say about parallel administrative units, so a gap between the two is visible in the table [4]. Read worst-first, strong internal policy compliance cannot make up for serious duplication of services in the field [4].

## Where Rubicon falls short

- **The contrast is between documents rather than speakers.** A count split by stakeholder group puts each document on the side its column names, so a joint review written by the agency and the ministry together counts as one of them. A column on each coded row naming who is speaking would split it.
- **A count of friction passages is not a count of frictions.** Two documents describing one duplicated service are two passages. Read the count as how much of the material records friction, which is what the threshold is about, and not as how many separate problems there were.

## Sources

The numbers in square brackets refer to the works cited on [generic evaluation questions](generic-evaluation.md#works-cited).
