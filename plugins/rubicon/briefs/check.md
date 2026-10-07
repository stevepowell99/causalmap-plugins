An evaluator asks: "{{question}}" The documents are in corpus/ (corpus/index.csv lists them). Read every document in full.

answer.md is a report someone wrote answering this question. Please check every statement and every quotation in it against the documents, and give me a corrected version of the whole report: fix anything that is wrong, overstated or misquoted, and leave the rest as it is.

Check it also against these rules for claims, and correct any claim that breaks them, keeping the report's own form otherwise:
- A number of people is counted only from what they say of their own case, with the documents named; what someone reports of others is said separately.
- A difference between groups is called clear only where it would survive one document being read the other way; otherwise it is unclear with this few documents. No p-values or statistical tests.
- A finding names the documents whose accounts go against it.
- Every quotation is the speaker's own words, exactly, with their id.

The report's numbers are made by code from coded rows, so you correct a number by correcting the rows, never by writing it. workflow.json holds the definitions the rows were coded to and coded/<step id>.json the rows; contract/pieces.md describes the format. In answer.md a count is a cell id in braces and a citation is a row id in square brackets; recount/answer.resolved.md is the report as the evaluator reads it, recount/rows.md every row with its id and recount/tables.md every table.

Before you check the report, rule on the coding. A second coder coded the same documents to the same definitions without seeing these rows, and recode/disagreements.md lists every document and value the two placed differently, with both coders' passages. For each, read the passage in the document with enough around it to see who is speaking and what was asked, and decide against the column's definition. Where the rows are wrong, correct coded/<step id>.json, quoting the document exactly. Where the definition does not settle it, tighten it in workflow.json and recode every document it affects.

Then check and correct answer.md as asked above. Where a claim is wrong because a row is wrong, correct the row. Keep counts as cell ids and citations as row ids, and quote documents exactly. Run python "${CLAUDE_PLUGIN_ROOT}/engine/recount.py" . --answer answer.md and fix what it reports until the report is clear.

Put the answer to the question at the top of the report, stated plainly, and cut padding: restating the question, narrating method, repeating a point, and material that does not bear on the question. There is no word limit; do not shorten what the question needs.

Last, write check.md: the counts first (disagreements ruled for the rows, for the second coder and as unsettled; rows changed; sentences changed), then a line for each ruling and each change, with the document, the passage and why.

On a corpus too large to read whole, read the documents behind each disagreement and each cited row, and search the rest with scripts for accounts that go against each finding.
