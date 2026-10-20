# Causal Map plugins for Claude

Causal Map's plugins for evaluators and researchers working with qualitative evidence. There is one so far.

## Rubicon

**Rubicon: checkable AI for evaluators.**

Rubicon turns your Claude into an opinionated evaluation assistant. You bring your evaluation questions and the documents you gathered, such as interviews and reports. Rubicon settles with you how to answer them, as an experienced evaluator would with a client, and then carries the analysis out, leaving the records that let somebody else check it.

Answering an evaluation question usually takes a workflow of several steps: split the question into the parts that can be answered from the documents, code the passages that bear on each, combine and count them, compare groups, and judge the result against a standard. Rubicon helps you design that workflow:

- It settles the question with you: what counts, out of what, and which groups to compare.
- It draws on published evaluation practice, such as contribution analysis, process tracing, realist evaluation and outcome harvesting. Where your question or your documents do not suit the method you name, it says so.
- For a judgement of worth, it can help you set a rubric before the evidence is seen, and always says whose standard a verdict rests on and when it was set.
- It can pause for stakeholders to agree the definitions or the draft. Where a verdict has real consequences, it can first test the workflow on two made-up sets of documents, one written to pass and one to fail, to show the workflow can tell them apart.
- Every count is made by code, out of a stated base, and every quotation is checked word for word against its document.

A later run can build on an earlier one's coding rather than repeat it. You get a report in which every number and quotation can be clicked to see what it rests on, a Word copy, and the whole run in one file, so that somebody else can check and rebuild the analysis. It runs on your own Claude plan; nothing is sent to Causal Map. More, with example reports: [rubicon.causalmap.app/plugin](https://rubicon.causalmap.app/plugin/).

## Install

In the Claude app: Customize > Plugins > Add marketplace, and enter `stevepowell99/causalmap-plugins`. Then install Rubicon from it. To get a new version, choose Manage marketplaces, open the ⋮ menu beside causalmap-plugins and choose Check for updates; do this from time to time, since Sync automatically does not reliably bring new versions on its own. If Check for updates still leaves the old version, remove the causalmap-plugins marketplace, restart the app, and add it again.

In Claude Code:

```
/plugin marketplace add stevepowell99/causalmap-plugins
/plugin install rubicon@causalmap
```

Then open a folder of documents, or attach them to a conversation, and type `/rubicon` followed by your evaluation question.

## Licence

The method notes are under CC BY 4.0; everything else is under the MIT License, which allows any use, including paid evaluation work. See [LICENSE](LICENSE). Issues and suggestions are welcome here.

Causal Map also runs workshops and consultancy on analysing qualitative evidence for evaluation: [causalmap.app](https://causalmap.app/?utm_source=rubicon-plugin&utm_medium=github).
