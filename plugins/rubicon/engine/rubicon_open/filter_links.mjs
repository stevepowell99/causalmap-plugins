// Filter a code step's rows as causal links with Causal Map's own filter engine, the copy in ./cm, which
// tests/rubicon-open-filter-engine-twin.test.mjs keeps identical to the app's. The rows become links and come back
// as rows in ./link-rows.js, the same file the Rubicon page refilters a map with.
//
// A map of causal links (`map`: true) combines opposites by default, as Causal Map's Combine Opposites filter does with
// Together bundling: a factor coded with a leading `~` is counted with its plain partner, and each row says which of its
// ends was flipped. `chainFor` in ./link-rows.js, which the page uses too, makes the chain, with the filter placed where
// the filter-ordering rules put it (`suggestFilterPosition`).
//
// stdin:  {"rows": [...], "ends": {"from", "to"}, "filters": [...], "attributes": {document: {fact: value}}, "map"?}
// stdout: {"rows": [...], "unsupported": ["<type>", ...], "filtered": {"links_in", "links_out", "rows_out"},
//          "filters": [the chain applied]}
//
// With `chains` (a list of filter lists) in place of `filters`, each chain is applied to the same rows and the reply is
// {"each": [{"rows": [[row, document], ...], "unsupported": [...]}, ...]}: the rows each chain keeps, named by id and
// document only. A table that needs one filtered view for every pair of values, such as the paths each pair has, asks
// for all of them in one run of Node.
import { applyOrderedLinkFilters } from './cm/filter-engine/index.js'
import { suggestFilterPosition } from './cm/filter-type-flags.js'
import { chainFor, filterRows } from './link-rows.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { rows, ends, filters, attributes, map, chains } = JSON.parse(raw)
if (chains) {
  const each = chains.map((list) => {
    const got = filterRows(applyOrderedLinkFilters, rows, ends, chainFor(list, false, suggestFilterPosition), attributes)
    return { rows: got.rows.map((r) => [r.row, r.document]), unsupported: got.unsupported }
  })
  process.stdout.write(JSON.stringify({ each }))
} else {
  const chain = chainFor(filters, map, suggestFilterPosition)
  process.stdout.write(JSON.stringify({ ...filterRows(applyOrderedLinkFilters, rows, ends, chain, attributes), filters: chain }))
}
