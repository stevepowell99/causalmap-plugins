# Networks of actors

How to answer a social network analysis question from documents in Rubicon (who works with whom, who brokers between groups, which actors are isolated, how far a cascade or a piece of information travelled, which actors an influence pathway runs through), by coding ties between actors with the same `links` setting a causal map uses, and what such a network cannot tell you.

Back to [causal mapping in Rubicon](causal-mapping-in-rubicon.md), whose coding, filtering and drawing hold here too.

## What it establishes

A network of the ties the documents report: which actors the speakers say are joined, by what kind of relation, and how many cases report each tie. It is a map of what people said about their relations, in the same way a causal map is a map of claims rather than of the world. It does not establish the network as it is, and it does not establish how central any actor is.

## When it fits, and when it does not

It fits when the question is about relations between actors (people, organisations, teams, offices) rather than about changes in things. Typical questions:

- **Partnership and coherence.** Who works with whom, which partners never meet, and who sits between groups that do not otherwise connect. See [coherence](generic-evaluation-coherence.md).
- **Diffusion.** Who trained, informed or referred whom, and how far a cascade reached before it stopped.
- **Influence pathways.** Programme to partner to official to decision, where the route runs through actors rather than through changes.
- **Network-building as an outcome.** Whether a programme left actors better connected than it found them.
- **Outcome harvesting's actor structure.** Which change agent sits behind which actor's change; see [outcome harvesting in Rubicon](outcome-harvesting-in-rubicon.md).

A causal map is a graph with one relation, "influences", whose nodes are factors. An actor network is a graph whose nodes are actors and whose links carry a relation column. Rubicon has no separate component for it: a code step's `links` names any two of its columns as a link's two ends, so two actor columns work exactly as a cause and an effect do.

It does not fit when the question needs network measures (betweenness, density, components): none is computed, and degree is counted only one direction at a time, by a profile. It does not fit a question about the whole of a population's ties, such as "how connected is the sector", unless the documents cover that population; it does not fit where speakers cannot or will not name the people they deal with; and where the real question is why something happened, the actor network is at best a companion to a causal map, not a substitute.

## The missing-tie problem

A network built from interviews or reports is a sample of the ties people happened to mention. Three things follow, and the answer should say each of them where it applies.

- **Absence of a tie means little.** Two actors with no tie between them may simply not have come up. A tie nobody reports is not a finding, so tabulate with `sparse`, which lists only the ties that occur and never states one as absent.
- **Centrality is fragile.** Which actor looks most connected depends heavily on who was interviewed and what they were asked. An actor who was interviewed reports their own ties and so looks central; an actor nobody interviewed appears only through other people's accounts. Published work on sampled networks finds that centrality rankings move a good deal when even a modest share of ties or actors is missing.
- **The base is what was found.** Any statement about the network is about the actors and ties found in the documents read, never about those that exist. Name who was interviewed and what they were asked about, and say that a tie's count is the cases that report it.

## As a plan

**Code.** One code step reads every document and writes a row for each tie a passage reports between two actors, with the passage as its quotation. Two actor columns, say `from_actor` and `to_actor`, and a nominal `relation` column whose values the question needs, for example `funds`, `trains`, `informs`, `works with`, `refers to`, each with a `means` saying what counts. The step names its ends as `links: {"from": "from_actor", "to": "to_actor"}`. Name the actor columns something other than `from` and `to`, so they are not read as the setting. The coding prompt says what an actor is for this question (a named person, a role such as "the district health officer", an organisation), how to name one consistently (the role or organisation rather than a pronoun, the speaker as themselves where they are one end), which way round to write a directed tie (the actor who trains, funds or informs is `from_actor`), and how to write a tie with no direction, such as `works with`: in one fixed order, for example alphabetical, so that A with B and B with A are not two ties. Where the actors are known beforehand, from a partner list, an attendance list or a register, make both actor columns nominal with that list as their values and an `other` value with its `means`, which skips the grouping below.

**Group.** Where the actor columns are free text, the same actor will be named differently across documents ("the council", "Leeds City Council", "LCC"). A group step with `key_column` over both actor columns (`["from_actor", "to_actor"]`) and `assign` finds one codebook of actors across both ends and gives each row `from_actor_item` and `to_actor_item`, so that the table's links run over the items and one actor named three ways becomes one node. Set `direction` to `none`. Two cautions. This has been tested for factors and not for actor names, so read the codebook before trusting it, especially where two different people share a role title. And a group step finds at most about 30 items at `detailed` granularity, so a network with more distinct actors than that needs an agreed list instead, or a coarser node such as the organisation rather than the person.

**Tabulate.** A tabulate step by the two ends with `sparse` set gives the network as an edge list, each tie with its count, and a map line in the answer draws it as a map whose arrows open the passages behind them. Leave `count` at `cases`, so that a tie counts the cases that report it, not the passages: a case is a document unless the document list's `case` column gives several documents one case (two interviews with the same organisation, say). Do not use the rows' own `case` column for an actor here, since a tie has two. To draw one relation at a time, set `where`, such as `{"relation": "trains"}`, one tabulate step per relation; to compare groups of speakers, add a document attribute to `by` or to `where`.

**Degree, as a profile.** The number of different partners an actor has is a profile step over the group step (or over the code step, where the actor columns are nominal) keyed by one end, with a `distinct` column over the other end. A tie has two actor columns, so say which end the count is from: keyed by `from_actor_item` with `distinct` over `to_actor_item`, it counts the partners an actor trains, funds or informs, its outgoing ties only, and a second profile keyed by `to_actor_item` with `distinct` over `from_actor_item` counts those it hears from. Neither is an actor's partners in every direction, and a tie with no direction, written in one fixed order, falls under one end or the other by its name, so for `works with` the answer reads both. A tabulation of a profile by its key and that column, with `sparse` set and `unit` such as "actors", lists each actor beside its number of partners; by that column alone, it counts the actors with one partner, two and so on. The number is of partners reported, so the missing-tie problem above applies to it in full.

**Graph questions, as filters.** A tabulate step with `filters` puts the ties through Causal Map's own link filters before counting, and these answer most of the questions above as views of the merged network:

- **An actor's neighbourhood (ego network).** The Factor Label filter, naming the actor, with steps up and down set to how far out to go: the ties within one or two steps of that actor.
- **Influence pathways and reach.** The Path Tracing filter from one set of actors to another, such as from the programme's trainers to anybody, gives every route between them and so shows how far a cascade went.
- **The main structure.** The Link Frequency and Factor Frequency filters keep the ties reported by more cases, or the actors with more ties, for a readable map of a large network. Order the filters as the filter-ordering rules say: tracing first, frequency last.

Where actors were grouped, a filter names an actor by its item as the table holds it, so those steps are written once the codebook exists.

**Tracing within one document, and across documents.** The `paths` setting joins links only within one document (source tracing). That is right for causal claims and undercounts routes in a network, where the tie from A to B comes from one interview and the tie from B to C from another, and together they do show a route. So for reach and pathways use the Path Tracing filter, which traces over the merged ties from every document, and keep `paths` for the rarer question of what one speaker's own account connects.

**Judge.** Only where the evaluator gives a standard, for example a threshold on how many attenders' organisations report onward training. A rule tests a count of cases in a cell, never a network measure.

**Write.** The answer describes the network as reported: the ties, by relation, with the cases behind each; who sits between groups on the map; which actors appear only at one end of other people's accounts. It names the actors who were interviewed and states the missing-tie problem in a sentence. It does not rank actors by centrality, and where it states how many partners an actor has, the number comes from a profile, says which direction it counts, and the partners are named.

## What a workflow cannot do

- **Network measures beyond degree.** Betweenness, closeness, density and components are not computed. Degree, the number of different partners an actor has, is counted by a profile, one direction at a time, as above.
- **One actor across documents, at scale.** Beyond about 30 actors, or where names are ambiguous, the grouping above does not hold; an agreed list is the route.
- **The actors that exist.** A profile keyed by an actor end counts the actors found, each once, so "how many organisations does the network reach" is answered as the organisations the documents name, never those the network actually reaches.
- **Change over time.** A before-and-after network needs a column saying when each tie held (`before`, `during`, `after`), coded from what speakers recall, with `where` on it in two tabulate steps. Recalled ties are thinner than current ones, so a denser "after" network is partly an artefact of memory, and the answer says so.

## A worked design: the MECC cascade

A design, not a run that has happened. The corpus is the public MECC train-the-trainer interviews: thirteen people who attended a session meant to equip them to deliver the training in their own organisations, with the document list recording whether each went on to cascade it. The evaluator asks how far the training travelled, and through whom.

The code step writes a row for each tie between the programme's trainers, the attenders, and the colleagues, managers and other organisations they mention, with `relation` valued `trained`, `supported`, `managed` and `asked to deliver`. The actors are grouped across both ends, with the attenders as themselves and other people by role and organisation, since the transcripts anonymise names. Three tabulate steps follow: the whole network with `sparse`; the `trained` ties alone, through a Path Tracing filter from the programme's trainers outward, which shows how many steps the cascade reached and where it stopped; and the same view with the cascade attribute in `by`, so the attenders who cascaded and those who did not are compared. Why it stopped is a causal question, so a separate causal coding over the same documents answers it, as on [causal mapping in Rubicon](causal-mapping-in-rubicon.md), and the answer reads the two together: where the network stops, and what the speakers at that point say stopped it. The answer states that the network is the ties thirteen attenders mentioned, so the colleagues they trained are seen only through the attenders' own accounts.

## Sources

- Borgatti, S. P., Everett, M. G., and Johnson, J. C. *Analyzing Social Networks*. Sage.
- Wasserman, S., and Faust, K. (1994). *Social Network Analysis: Methods and Applications*. Cambridge University Press.
- Davies, R. Network perspectives in the evaluation of development interventions: more than a metaphor. Conference paper.
- Costenbader, E., and Valente, T. W. The stability of centrality measures when networks are sampled. *Social Networks*.
- Kossinets, G. Effects of missing data in social networks. *Social Networks*.
