# Causal Map plugins for Claude

Causal Map's plugins for evaluators and researchers working with qualitative evidence. There is one so far.

## Rubicon

Rubicon turns your Claude into an opinionated evaluation assistant. You bring one key evaluation question and the documents you gathered, such as interviews and reports. Rubicon argues out with you how to answer it, as an experienced evaluator would with a client, and then carries the analysis out.

Answering an evaluation question is rarely a single coding task. It usually takes a workflow: split the question into the parts that can be answered from the documents, code the passages that bear on each, combine and count them, compare groups, and judge the result against a standard agreed in advance. Rubicon helps you design that workflow and holds you to it:

- It settles the question with you before anything is read: what the answer will feed, whether it is really several questions, which groups to compare.
- It draws on published evaluation practice, such as contribution analysis, process tracing, QCA, realist evaluation and outcome harvesting. Where your question or your documents do not suit the method you name, it says so.
- It helps you set a rubric for a judgement of worth before the evidence is seen, and never supplies the standard itself.
- It can pause for stakeholders to agree the definitions or the draft. Where a verdict has real consequences, it can first test the workflow on two made-up sets of documents, one written to pass and one to fail, to show the workflow can tell them apart.
- Every count is made by code, out of a stated base, and every quotation is checked word for word against its document.

Each run answers one question; it is not a summary of everything in your documents. You get a report in which every number and quotation can be clicked to see what it rests on, a Word copy, and the whole run in one file, so that somebody else can check and rebuild the analysis. It runs on your own Claude plan; nothing is sent to Causal Map. More, with example reports: [rubicon.causalmap.app/plugin](https://rubicon.causalmap.app/plugin/).

## Install

In the Claude app: Customize > Plugins > Add marketplace, and enter `stevepowell99/causalmap-plugins`. Then install Rubicon from it. To get new versions as they are released, choose Manage marketplaces, open the ⋮ menu beside causalmap-plugins and turn on Sync automatically; Check for updates in that menu fetches the latest at once.

In Claude Code:

```
/plugin marketplace add stevepowell99/causalmap-plugins
/plugin install rubicon@causalmap
```

Then open a folder of documents, or attach them to a conversation, and type `/rubicon` followed by your evaluation question.

## Licence

The method notes are under CC BY 4.0; everything else is under the MIT License, which allows any use, including paid evaluation work. See [LICENSE](LICENSE). Issues and suggestions are welcome here.

Causal Map also runs workshops and consultancy on analysing qualitative evidence for evaluation: [causalmap.app](https://causalmap.app/?utm_source=rubicon-plugin&utm_medium=github).
