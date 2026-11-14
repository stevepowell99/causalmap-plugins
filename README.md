# Causal Map plugins for Claude

Causal Map's plugins for evaluators and researchers working with qualitative evidence: Rubicon, in two versions.

## Rubicon

**Rubicon by Causal Map: checkable AI for evaluators.**

Rubicon turns your Claude into an opinionated evaluation assistant. You bring your evaluation questions and the documents you gathered, such as interviews and reports. Rubicon settles with you how to answer them, as an experienced evaluator would with a client, and then carries the analysis out, leaving the records that let somebody else check it.

Answering an evaluation question usually takes a workflow of several steps: split the question into the parts that can be answered from the documents, code the passages that bear on each, combine and count them, compare groups, and judge the result against a standard. Rubicon helps you design that workflow:

- It settles the question with you: what counts, out of what, and which groups to compare.
- It draws on published evaluation practice, such as contribution analysis, process tracing, realist evaluation and outcome harvesting. Where your question or your documents do not suit the method you name, it says so.
- For a judgement of worth, it can help you set a rubric before the evidence is seen, and always says whose standard a verdict rests on and when it was set.
- It can pause for stakeholders to agree the definitions or the draft. Where a verdict has real consequences, it can first test the workflow on two made-up sets of documents, one written to pass and one to fail, to show the workflow can tell them apart.
- Every count is made by fixed rules, out of a stated base, and every quotation is checked word for word against its document.

A later run can build on an earlier one's coding rather than repeat it. You get a report in which every number and quotation can be clicked to see what it rests on, a Word copy, and the whole run in one file, so that somebody else can check and rebuild the analysis. It runs on your own Claude plan, and your documents go only to Claude.

It uses much more of that plan than a chat, since a run reads every document, often several times over. On our test set of 100 interview transcripts (about 156,000 words), answering one question on Opus took 31 minutes and about 1.2 million tokens read fresh or written, which can use up a Pro plan's five-hour session; Max gives five times Pro's usage in each five-hour session; verified Ultra accounts do not have a five-hour limit ([Anthropic's plans](https://claude.com/pricing)). Before a run starts, Rubicon estimates the tokens and time your task will take and says what that means on each plan.

More, with example reports: [rubicon.causalmap.app/plugin](https://rubicon.causalmap.app/plugin/).

## Two versions: choose one

The two are the same Rubicon in everything but what they send.

| | `rubicon` | `rubicon-private` |
|---|---|---|
| Sends Causal Map | Each run's size and outline, never its content, once a conversation after the report is handed over, with a line first that you can deny | Nothing |
| New versions | Tells you when one is published | Never hears of one: check under Manage marketplaces, or with `claude plugin marketplace update causalmap` |
| Install from a terminal | `claude plugin install rubicon@causalmap` | `claude plugin install rubicon-private@causalmap` |
| Start a question with | `/rubicon` | `/rubicon-private` |

What `rubicon` sends, in one request: the plugin's version and model family; what was handed over (a report, a revision or a combined report); a random code the run keeps and no report shows, so that a report and its revisions count as one run; how many documents and about how many words they hold, in bands such as 6-10 documents and 20k-50k words; how many questions and how they were taken; how many steps of each kind, and how many passages were coded, in bands; the second reading; the minutes from the run's first agreement to the hand-over, in bands; and the share of the answer's sentences tied to the coded passages, in bands. Never a question, a document or folder name, a passage, a code value or label, the time of day, or anything about you or your computer. The request goes to a relay Causal Map runs on Google Cloud, set to store no log of its requests, so your IP address is not kept and never reaches Causal Map's database, which stores the values as one row with that day's date; the relay's reply carries the version published here. The plugin's README, "What it runs, writes and sends", says the same in full.

Install one, never both. Each keeps its own list of the folders it has answered from, so after switching, ask Rubicon to find your earlier runs in the folder that holds them.

## Install

Install Rubicon once, in the Claude app: Customize > Plugins > Add marketplace, and enter `stevepowell99/causalmap-plugins`. Then install `rubicon` or `rubicon-private` from it. It is saved to your Claude account, so the same copy works in Cowork, in the Code tab and in Claude Code signed in to that account.

To get a new version, choose Manage marketplaces, open the ⋮ menu beside causalmap-plugins and choose Check for updates; do this from time to time, since Sync automatically does not reliably bring new versions on its own. If Check for updates still leaves the old version, remove the causalmap-plugins marketplace, restart the app, and add it again. Claude Code picks up the new version the next time a session starts, or after `/reload-plugins`.

If you use Claude Code without the app, install from a terminal instead:

```
claude plugin marketplace add stevepowell99/causalmap-plugins
claude plugin install rubicon@causalmap
```

or `claude plugin install rubicon-private@causalmap` for the version that sends nothing. To get a new version there, run `claude plugin marketplace update causalmap`, then `claude plugin update rubicon@causalmap` (or `rubicon-private@causalmap`), and restart Claude Code.

Use one route or the other, never both. A copy installed from a terminal stays on that computer and is updated separately. In Claude Code it takes the place of the copy on your account, so the two can end up at different versions without any sign of it. If you have installed Rubicon both ways, remove the terminal copy with `claude plugin uninstall rubicon@causalmap`. Remove any copy you once installed from a zip file too, for the same reason.

Then open a folder of documents, or attach them to a conversation, and type `/rubicon` (or `/rubicon-private`) followed by your evaluation question.

## Licence

The method notes are under CC BY 4.0; everything else is under the MIT License, which allows any use, including paid evaluation work. See [LICENSE](LICENSE). Issues and suggestions are welcome here.

Causal Map also runs workshops and consultancy on analysing qualitative evidence for evaluation: [causalmap.app](https://causalmap.app/?utm_source=rubicon-plugin&utm_medium=github).
