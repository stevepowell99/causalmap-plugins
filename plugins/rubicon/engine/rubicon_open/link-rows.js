/**
 * A code step's rows as causal links, for Causal Map's own filter engine, and back.
 *
 * One owner for both places that filter a run's links: the plugin's recount, which runs this
 * file's copy in `rubicon/open/rubicon_open/` under Node (`filter_links.mjs`), and the Rubicon
 * page, which refilters a map in the browser. `tests/rubicon-open-link-rows-twin.test.mjs`
 * keeps the two copies identical. It imports nothing, so each caller hands it the engine's
 * `applyOrderedLinkFilters` from wherever its own copy of the engine sits.
 *
 * `ends` is the code step's `links`, {from, to}: the two columns that are a link's two ends.
 * `attributes` gives each document's facts, which become the link source's custom columns, so
 * a filter reads `s_<fact>` for one.
 */

const valuesOf = (row, column) => {
    const v = row[column]
    return (Array.isArray(v) ? v : [v]).filter(x => x !== null && x !== undefined && x !== '').map(String)
}

/** Each row gives a link for every pair of its two end values; its other columns ride on the link. */
export function linksOfRows(rows, ends) {
    const links = []
    for (const r of rows) {
        const { quote, ...rest } = r
        let n = 0
        for (const x of valuesOf(r, ends.from)) {
            for (const y of valuesOf(r, ends.to)) {
                links.push({ ...rest, id: `${r.row}#${n++}`, source_id: r.document, cause: x, effect: y })
            }
        }
    }
    return links
}

/**
 * The rows put through `filters` in order, and back as rows: a surviving link comes back as its
 * row with the two ends as the filters left them, since a filter such as zoom renames a factor,
 * and once only where a renaming made two of a row's links one.
 */
export function filterRows(apply, rows, ends, filters, attributes = {}) {
    const links = linksOfRows(rows, ends)
    const docs = [...new Set(rows.map(r => r.document))].sort()
    const sources = docs.map(d => ({ id: d, metadata: { custom_columns: { ...(attributes[d] || {}) } } }))
    const got = apply(links, filters, sources)
    const byRow = new Map(rows.map(r => [String(r.row), r]))
    const out = []
    const seen = new Set()
    for (const link of got.rows) {
        const row = String(link.id).slice(0, String(link.id).lastIndexOf('#'))
        const key = JSON.stringify([row, link.cause, link.effect])
        if (seen.has(key)) continue
        seen.add(key)
        out.push({ ...byRow.get(row), [ends.from]: link.cause, [ends.to]: link.effect })
    }
    return { rows: out, unsupported: got.unsupported || [],
             filtered: { links_in: links.length, links_out: got.rows.length, rows_out: new Set(out.map(r => r.row)).size } }
}

/** The links the rows make, each with the documents that mention it and its rows: `n` counts documents. */
export function edgesOf(rows, ends) {
    const at = new Map()
    for (const r of rows) {
        for (const x of valuesOf(r, ends.from)) {
            for (const y of valuesOf(r, ends.to)) {
                const key = JSON.stringify([x, y])
                if (!at.has(key)) at.set(key, { from: x, to: y, documents: new Set(), rows: [] })
                const e = at.get(key)
                e.documents.add(r.document)
                e.rows.push(r)
            }
        }
    }
    return [...at.values()].map(e => ({ ...e, documents: [...e.documents].sort(), n: e.documents.size }))
}

/** The filters a map's controls set, which replace any of the same kind in the step's own list. */
const CONTROLLED = new Set(['path-tracing', 'zoom', 'link-frequency'])
const labels = text => String(text || '').split(',').map(s => s.trim()).filter(Boolean)

/** A map's controls read from a step's filters: tracing, zoom and the fewest documents a link needs. */
export function controlsOf(filters = []) {
    const find = type => filters.find(f => f?.type === type) || {}
    const trace = find('path-tracing')
    const freq = find('link-frequency')
    return {
        from: (trace.fromLabels || []).join(', '), to: (trace.toLabels || []).join(', '),
        steps: Number(trace.maxSteps) || 3, zoom: Number(find('zoom').level) || 0,
        least: freq.which === 'sources' && freq.mode === 'minimum' ? Number(freq.threshold) || 1 : 1,
    }
}

/**
 * The filters a map's controls make, in the order the filter-ordering rules give: tracing first,
 * then the step's other filters as it set them, then zoom, then frequency last.
 */
export function chainOf(filters = [], c = {}) {
    const from = labels(c.from)
    const to = labels(c.to)
    return [
        ...(from.length || to.length ? [{ type: 'path-tracing', fromLabels: from, toLabels: to, maxSteps: Number(c.steps) || 3 }] : []),
        ...filters.filter(f => !CONTROLLED.has(f?.type)),
        ...(Number(c.zoom) > 0 ? [{ type: 'zoom', level: Number(c.zoom) }] : []),
        ...(Number(c.least) > 1 ? [{ type: 'link-frequency', which: 'sources', mode: 'minimum', threshold: Number(c.least) }] : []),
    ]
}
