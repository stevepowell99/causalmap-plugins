// Filter a code step's rows as causal links with Causal Map's own filter engine, the copy in ./cm, which
// tests/rubicon-open-filter-engine-twin.test.mjs keeps identical to the app's. The rows become links and come back
// as rows in ./link-rows.js, the same file the Rubicon page refilters a map with.
//
// stdin:  {"rows": [...], "ends": {"from", "to"}, "filters": [...], "attributes": {document: {fact: value}}}
// stdout: {"rows": [...], "unsupported": ["<type>", ...], "filtered": {"links_in", "links_out", "rows_out"}}
import { applyOrderedLinkFilters } from './cm/filter-engine/index.js'
import { filterRows } from './link-rows.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { rows, ends, filters, attributes } = JSON.parse(raw)
process.stdout.write(JSON.stringify(filterRows(applyOrderedLinkFilters, rows, ends, filters, attributes)))
