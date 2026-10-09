// Filter a code step's rows as causal links with Causal Map's own filter engine, the copy in ./cm, which
// tests/rubicon-open-filter-engine-twin.test.mjs keeps identical to the app's. The rows become links and come back
// as rows in ./link-rows.js, the same file the Rubicon page refilters a map with.
//
// A map of causal links (`map`: true) combines opposites by default, as Causal Map's Combine Opposites filter does with
// Together bundling: a factor coded with a leading `~` is counted with its plain partner, and each row says which of its
// ends was flipped. The filter goes where the filter-ordering rules put it (`suggestFilterPosition`), unless the step
// already has one. A Combine Opposites filter that leaves a setting out takes the app's default for it, since the
// engine itself reads a missing `useTildeOpposites` as off.
//
// stdin:  {"rows": [...], "ends": {"from", "to"}, "filters": [...], "attributes": {document: {fact: value}}, "map"?}
// stdout: {"rows": [...], "unsupported": ["<type>", ...], "filtered": {"links_in", "links_out", "rows_out"},
//          "filters": [the chain applied]}
import { applyOrderedLinkFilters } from './cm/filter-engine/index.js'
import { suggestFilterPosition } from './cm/filter-type-flags.js'
import { filterRows } from './link-rows.js'
import { pathToFileURL } from 'node:url'

export const OPPOSITES = { type: 'combine-opposites', useNumericOpposites: true, useTildeOpposites: true,
                           bundleStrategy: 'together', labelDetail: 'simple' }

export function chainFor(filters = [], map = false) {
    const chain = filters.map(f => (f?.type === 'combine-opposites' ? { ...OPPOSITES, ...f } : f))
    if (map && !chain.some(f => f?.type === 'combine-opposites')) {
        chain.splice(suggestFilterPosition(chain, 'combine-opposites'), 0, { ...OPPOSITES })
    }
    return chain
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    let raw = ''
    process.stdin.setEncoding('utf8')
    for await (const chunk of process.stdin) raw += chunk
    const { rows, ends, filters, attributes, map } = JSON.parse(raw)
    const chain = chainFor(filters, map)
    process.stdout.write(JSON.stringify({ ...filterRows(applyOrderedLinkFilters, rows, ends, chain, attributes), filters: chain }))
}
