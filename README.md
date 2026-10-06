# Causal Map plugins for Claude

Causal Map's plugins for evaluators and researchers working with qualitative evidence. There is one so far.

**Rubicon** answers an evaluation question from a folder of documents, such as interview transcripts, inside your own Claude. It settles the question with you, codes the passages that bear on it, and writes a report in which every number is counted by code and every quotation is checked word for word against its document. It runs on your own Claude plan; nothing is sent to Causal Map. More: [rubicon.causalmap.app/plugin](https://rubicon.causalmap.app/plugin/).

## Install

In the Claude app: Customize > Plugins > Add marketplace, and enter `stevepowell99/causalmap-plugins`. Then install Rubicon from it.

In Claude Code:

```
/plugin marketplace add stevepowell99/causalmap-plugins
/plugin install rubicon@causalmap
```

Then open a folder of documents, or attach them to a conversation, and type `/rubicon` followed by your evaluation question.

## Licence

The method notes are under CC BY 4.0; everything else is under the PolyForm Shield License 1.0.0, which allows any use, including paid evaluation work, except building a competing product. See [LICENSE](LICENSE). Issues and suggestions are welcome here.

Causal Map also runs workshops and consultancy on analysing qualitative evidence for evaluation: [causalmap.app](https://causalmap.app/?utm_source=rubicon-plugin&utm_medium=github).
