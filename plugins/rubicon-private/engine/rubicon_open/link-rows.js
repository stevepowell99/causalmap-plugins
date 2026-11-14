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
 * and once only where a renaming made two of a row's links one. Where Combine Opposites rewrote
 * an end, the row says so in `flipped_cause` or `flipped_effect`: that end was coded at the
 * opposite pole, as a `~` label, and is now counted with its plain partner.
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
        const flips = { ...(link.flipped_cause ? { flipped_cause: true } : {}), ...(link.flipped_effect ? { flipped_effect: true } : {}) }
        out.push({ ...byRow.get(row), [ends.from]: link.cause, [ends.to]: link.effect, ...flips })
    }
    return { rows: out, unsupported: got.unsupported || [],
             filtered: { links_in: links.length, links_out: got.rows.length, rows_out: new Set(out.map(r => r.row)).size } }
}

/**
 * Causal Map's Combine Opposites as a map applies it by default: Together bundling, counts as
 * the link labels, and both kinds of opposite on, as the app sets them when the filter is added.
 */
export const OPPOSITES = { type: 'combine-opposites', useNumericOpposites: true, useTildeOpposites: true,
                           bundleStrategy: 'together', labelDetail: 'simple' }

/**
 * The filters a map applies: a Combine Opposites filter that leaves a setting out takes the
 * app's default for it (the engine reads a missing `useTildeOpposites` as off), and a map
 * (`map` true: a table by two unsigned link ends, not paths, told sequences or loops) without
 * one gets one, placed where the caller's `place` puts it, which is Causal Map's
 * `suggestFilterPosition` from `filter-type-flags.js`.
 */
export function chainFor(filters = [], map = false, place = chain => chain.length) {
    const chain = filters.map(f => (f?.type === 'combine-opposites' ? { ...OPPOSITES, ...f } : f))
    if (map && !chain.some(f => f?.type === 'combine-opposites')) {
        chain.splice(place(chain, 'combine-opposites'), 0, { ...OPPOSITES })
    }
    return chain
}

/**
 * The links the rows make, each with the documents that mention it and its rows: `n` counts
 * documents. Where any row had an end flipped by Combine Opposites, each link also says how
 * many of its `of` rows had the cause, and the effect, flipped.
 */
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
    const flips = rows.some(r => r.flipped_cause || r.flipped_effect)
    return [...at.values()].map(e => ({ ...e, documents: [...e.documents].sort(), n: e.documents.size,
        ...(flips ? { flipped: { cause: e.rows.filter(r => r.flipped_cause).length,
                                 effect: e.rows.filter(r => r.flipped_effect).length, of: e.rows.length } } : {}) }))
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
