# Rubicon for Claude

Rubicon answers an evaluator's question from a folder of documents, such as interview transcripts, inside your own Claude. It reads the documents, codes the passages that bear on the question, and leaves its work as a workflow that code carries out again, so every count in the answer is made by code from the coded passages and every quotation is checked against its document. The model calls run on your own Claude plan; nothing is sent to Causal Map.

## Install

In the Claude app: Customize > Plugins > Add > Add marketplace, enter `stevepowell99/causalmap-plugins`, then install Rubicon from it, and to get new versions choose Manage marketplaces, open the ⋮ menu beside causalmap-plugins and turn on Sync automatically (Check for updates in the same menu fetches the latest at once; Remove there takes the marketplace and its plugins away). In a terminal: `/plugin marketplace add stevepowell99/causalmap-plugins`, then `/plugin install rubicon@causalmap`.

It needs Python 3.9 or later and Node.js. If any is missing, `/rubicon` says so and offers to install it.

## Use

Open the folder holding your documents in Claude's Code tab or in Cowork, or attach the documents to a chat, and type `/rubicon` followed by your question. Rubicon lists the documents it found and asks you to confirm them, then settles the question with you before it starts. Each question gets a folder of its own beside `corpus/`, which lists the documents and the facts about them; documents added to the folder later are offered for the corpus at the next question, and each question's folder keeps the corpus as it answered from it. In it Rubicon writes three files named from the question and the date: the report (`.html`), where every number and quotation opens what it rests on; the same report for Word (`.doc`); and the whole run in one file (`.zip`), to keep or pass on; it holds your documents, so share it only with people allowed to read them. Where the documents were attached rather than in a folder you opened, the three are handed back where the app puts files for you. The plain answer is `recount/answer.resolved.md`, `work/` holds the audit trail, and `workflow.json` with `coded/` the workflow behind every count.
