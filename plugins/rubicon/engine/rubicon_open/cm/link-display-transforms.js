// Pure link-display transforms shared by the UI pipeline and the app API.

export function getLinkCustomColumnValue(link, fieldName) {
    const raw = String(fieldName || '').trim()
    if (!raw || !link || typeof link !== 'object') return undefined
    const key = raw.startsWith('l_') ? raw.slice(2) : raw
    const directRaw = link[raw]
    if (directRaw !== undefined && directRaw !== null && directRaw !== '') return directRaw
    const directCanonical = link[`l_${key}`]
    if (directCanonical !== undefined && directCanonical !== null && directCanonical !== '') return directCanonical
    const custom = link.metadata?.custom_columns
    if (custom && typeof custom === 'object') {
        const customVal = custom[key]
        if (customVal !== undefined && customVal !== null && customVal !== '') return customVal
    }
    // Enriched/API links: source metadata merged as `s_<safe>` (slashes/spaces → `_`; `#` kept), same as app-api + DataService.
    const rawTrim = String(raw).trim()
    for (const suf of [rawTrim, rawTrim.replace(/^#/, '').trim()]) {
        if (!suf) continue
        const sk = `s_${suf.replace(/[\s/]/g, '_')}`
        const fromSource = link[sk]
        if (fromSource !== undefined && fromSource !== null && fromSource !== '') return fromSource
    }
    return undefined
}

export function applyLabelByGroupToFactors(links, filter, options = {}) {
    if (!filter?.applyToFactors || !String(filter?.selectedField || '').trim()) return links
    const field = String(filter.selectedField).trim()
    const mode = filter.displayMode || 'tally'
    const which = filter.which || 'sources'
    const sigLevel = (typeof filter.sigLevel === 'number') ? filter.sigLevel : 0.05
    const ordinalCorrection = filter.ordinalCorrection === true
    const isChiMode = isChiSquareMode(mode)
    const chiSqCritical1df = chiSquareCritical1df(sigLevel)
    const trendTest = typeof options.trendTest === 'function' ? options.trendTest : null

    const factorLinks = new Map()
    const addLink = (factor, link) => {
        if (!factor) return
        if (!factorLinks.has(factor)) factorLinks.set(factor, [])
        factorLinks.get(factor).push(link)
    }
    links.forEach(link => {
        addLink(String(link?.cause || '').trim(), link)
        addLink(String(link?.effect || '').trim(), link)
    })

    const buildDisplay = (factorLinksList) => {
        if (!factorLinksList.length) return ''
        return which === 'sources'
            ? labelByGroupSourcesDisplay({ bundleLinks: factorLinksList, allLinks: links, field, mode, sigLevel, ordinalCorrection, chiSqCritical1df, trendTest, factorMode: true })
            : labelByGroupCitationsDisplay({ bundleLinks: factorLinksList, allLinks: links, field, mode, sigLevel, ordinalCorrection, chiSqCritical1df, trendTest, factorMode: true })
    }

    const factorDisplay = new Map()
    factorLinks.forEach((factorLinksList, factor) => {
        const display = buildDisplay(factorLinksList)
        if (display) factorDisplay.set(factor, display)
    })

    return links.map(link => {
        const cause = String(link?.cause || '').trim()
        const effect = String(link?.effect || '').trim()
        const causeDisplay = factorDisplay.get(cause)
        const effectDisplay = factorDisplay.get(effect)
        return {
            ...link,
            cause: causeDisplay ? `${cause} ${causeDisplay}` : cause,
            effect: effectDisplay ? `${effect} ${effectDisplay}` : effect
        }
    })
}

export function computeLabelByGroupEdgeLabel(edgeLinks, allLinks, filter, options = {}) {
    const bundleCount = Array.isArray(edgeLinks) ? edgeLinks.length : 0
    if (!filter || filter.applyToLinks === false || !String(filter.selectedField || '').trim()) return String(bundleCount)
    const mode = filter.displayMode || 'tally'
    const params = {
        bundleLinks: Array.isArray(edgeLinks) ? edgeLinks : [],
        allLinks: Array.isArray(allLinks) ? allLinks : [],
        field: String(filter.selectedField || '').trim(),
        mode,
        sigLevel: (typeof filter.sigLevel === 'number') ? filter.sigLevel : 0.05,
        ordinalCorrection: filter.ordinalCorrection === true,
        chiSqCritical1df: chiSquareCritical1df((typeof filter.sigLevel === 'number') ? filter.sigLevel : 0.05),
        trendTest: typeof options.trendTest === 'function' ? options.trendTest : null,
        factorMode: false
    }
    // Match UI/filter defaults: tally by unique sources unless user chose citations explicitly.
    const label = filter.which !== 'citations'
        ? labelByGroupSourcesDisplay(params)
        : labelByGroupCitationsDisplay(params)
    return label || String(bundleCount)
}

export function getRenderedEdgeBundleGroups(links, filters = []) {
    const combineOppFilter = Array.isArray(filters)
        ? filters.find(f => f?.type === 'combine-opposites' && f.enabled !== false)
        : null
    const separateBundles = !!combineOppFilter && combineOppFilter.bundleStrategy !== 'together'
    const groups = new Map()
    for (const link of (Array.isArray(links) ? links : [])) {
        const cause = String(link?.cause || '').trim()
        const effect = String(link?.effect || '').trim()
        if (!cause || !effect) continue
        const edgeKey = separateBundles
            ? `${cause}|||${effect}|||${link?.flipped_cause === true ? 'F' : '-'}${link?.flipped_effect === true ? 'F' : '-'}`
            : `${cause}|||${effect}`
        if (!groups.has(edgeKey)) groups.set(edgeKey, [])
        groups.get(edgeKey).push(link)
    }
    return groups
}

export function isMapCustomColumnsFilterConfigured(filter) {
    return !!(
        filter?.type === 'map-custom-columns' &&
        (
            String(filter.labelField || '').trim() ||
            String(filter.widthField || '').trim() ||
            String(filter.colourField || '').trim()
        )
    )
}

export function computeMapCustomLabelForLinkBundle(edgeLinks, filter) {
    const field = String(filter?.labelField || '').trim()
    if (!field) return ''
    const aggregation = String(filter?.labelAggregation || 'unique')
    const values = getMapCustomTextValues(edgeLinks, field)
    if (!values.length) return ''
    if (aggregation === 'average' || aggregation === 'sum') {
        const nums = getMapCustomNumericValues(edgeLinks, field)
        if (!nums.length) return ''
        const total = nums.reduce((sum, n) => sum + n, 0)
        return formatMapCustomNumericValue(aggregation === 'sum' ? total : (total / nums.length))
    }
    if (aggregation === 'all') return values.join(', ')
    if (aggregation === 'tally') {
        const counts = new Map()
        values.forEach(value => counts.set(value, (counts.get(value) || 0) + 1))
        return Array.from(counts.entries())
            .sort((a, b) => (b[1] - a[1]) || String(a[0]).localeCompare(String(b[0])))
            .map(([value, count]) => `${value}: ${count}`)
            .join(', ')
    }
    const unique = []
    const seen = new Set()
    values.forEach(value => {
        const lower = value.toLowerCase()
        if (seen.has(lower)) return
        seen.add(lower)
        unique.push(value)
    })
    return unique.join(', ')
}

export function computeMapCustomWidthForLinkBundle(edgeLinks, filter) {
    const field = String(filter?.widthField || '').trim()
    if (!field) return null
    const nums = getMapCustomNumericValues(edgeLinks, field)
    if (!nums.length) return null
    const aggregation = String(filter?.widthAggregation || 'average')
    if (aggregation === 'sum') return nums.reduce((sum, n) => sum + n, 0)
    if (aggregation === 'max') return Math.max(...nums)
    return nums.reduce((sum, n) => sum + n, 0) / nums.length
}

export function computeMapCustomColourForLinkBundle(edgeLinks, allLinks, filter) {
    const field = String(filter?.colourField || '').trim()
    if (!field) return ''
    const values = getMapCustomTextValues(edgeLinks, field)
    if (!values.length) return ''
    const allValues = getMapCustomTextValues(allLinks, field)
    const allNumeric = allValues.length > 0 && allValues.every(value => Number.isFinite(Number(value)))
    if (!allNumeric) return ''
    const nums = getMapCustomNumericValues(edgeLinks, field)
    const allNums = getMapCustomNumericValues(allLinks, field)
    if (!nums.length || !allNums.length) return ''
    const aggregation = String(filter?.colourAggregation || 'mode')
    const aggValue = aggregation === 'max'
        ? Math.max(...nums)
        : aggregation === 'mode'
            ? computeNumericMode(nums)
            : nums.reduce((sum, n) => sum + n, 0) / nums.length
    if (!Number.isFinite(Number(aggValue))) return ''
    return mapNumericValueToMutedDivergingColour(Number(aggValue), Math.min(...allNums), Math.max(...allNums))
}

export function attachReservedCmLinkFields(links, filters = [], options = {}) {
    if (!Array.isArray(links) || !links.length) return links
    const stripped = links.map(link => {
        const out = { ...link }
        delete out._cm_link_label
        delete out._cm_link_width
        delete out._cm_link_colour
        return out
    })
    const activeFilters = Array.isArray(filters) ? filters.filter(filter => filter && filter.enabled !== false) : []
    const bundleGroups = getRenderedEdgeBundleGroups(stripped, activeFilters)
    for (const filter of activeFilters) {
        if (filter.type === 'custom-links-label' && filter.applyToLinks !== false && String(filter.selectedField || '').trim()) {
            for (const bundleLinks of bundleGroups.values()) {
                const label = computeLabelByGroupEdgeLabel(bundleLinks, stripped, filter, options)
                for (const link of bundleLinks) link._cm_link_label = label
            }
        } else if (isMapCustomColumnsFilterConfigured(filter)) {
            for (const bundleLinks of bundleGroups.values()) {
                if (String(filter.labelField || '').trim()) {
                    const label = computeMapCustomLabelForLinkBundle(bundleLinks, filter)
                    for (const link of bundleLinks) link._cm_link_label = label
                }
                if (String(filter.widthField || '').trim()) {
                    const width = computeMapCustomWidthForLinkBundle(bundleLinks, filter)
                    for (const link of bundleLinks) link._cm_link_width = Number.isFinite(Number(width)) ? Number(width) : null
                }
                if (String(filter.colourField || '').trim()) {
                    const colour = computeMapCustomColourForLinkBundle(bundleLinks, stripped, filter)
                    for (const link of bundleLinks) link._cm_link_colour = colour || ''
                }
            }
        }
    }
    return stripped
}

function labelByGroupSourcesDisplay(params) {
    const { bundleLinks, allLinks, field, mode, factorMode } = params
    const valueSets = new Map()
    bundleLinks.forEach(link => {
        const value = getLinkCustomColumnValue(link, field)
        const sourceId = String(link?.source_id || '').trim()
        if (value === undefined || value === null || value === '' || !sourceId) return
        if (!valueSets.has(value)) valueSets.set(value, new Set())
        valueSets.get(value).add(sourceId)
    })
    if (!valueSets.size) return ''
    if (mode === 'tally') return sortedSetCounts(valueSets).map(([value, count]) => `${value}: ${count}`).join(' ')

    const totalSets = new Map()
    allLinks.forEach(link => {
        const value = getLinkCustomColumnValue(link, field)
        const sourceId = String(link?.source_id || '').trim()
        if (value === undefined || value === null || value === '' || !sourceId) return
        if (!totalSets.has(value)) totalSets.set(value, new Set())
        totalSets.get(value).add(sourceId)
    })
    if (mode === 'percentage') {
        return sortedSetCounts(valueSets).map(([value, count]) => {
            const total = totalSets.get(value)?.size ?? count
            const pct = total > 0 ? Math.round((count / total) * 100) : 0
            return `${value}: ${pct}%`
        }).join(' ')
    }
    if (isChiSquareMode(mode)) {
        return chiSquareDisplay({
            ...params,
            observedEntries: sortedSetCounts(valueSets),
            totalCounts: new Map(Array.from(totalSets.entries()).map(([value, set]) => [value, set.size])),
            bundleSize: new Set(bundleLinks.map(link => link?.source_id).filter(Boolean)).size,
            grandTotal: new Set(allLinks.map(link => link?.source_id).filter(Boolean)).size,
            factorMode
        })
    }
    return ''
}

function labelByGroupCitationsDisplay(params) {
    const { bundleLinks, allLinks, field, mode, factorMode } = params
    const valueCounts = countValues(bundleLinks, field)
    if (!valueCounts.size) return ''
    if (mode === 'tally') return sortedCounts(valueCounts).map(([value, count]) => `${value}: ${count}`).join(' ')

    const totalCounts = countValues(allLinks, field)
    if (mode === 'percentage') {
        return sortedCounts(valueCounts).map(([value, count]) => {
            const total = totalCounts.get(value) || count
            const pct = total > 0 ? Math.round((count / total) * 100) : 0
            return `${value}: ${pct}%`
        }).join(' ')
    }
    if (isChiSquareMode(mode)) {
        return chiSquareDisplay({
            ...params,
            observedEntries: sortedCounts(valueCounts),
            totalCounts,
            bundleSize: bundleLinks.length,
            grandTotal: allLinks.length,
            factorMode
        })
    }
    return ''
}

function chiSquareDisplay(params) {
    const { observedEntries, totalCounts, bundleSize, grandTotal, mode, chiSqCritical1df, factorMode } = params
    const ordinal = ordinalTrendDisplay(params)
    if (ordinal !== null) {
        if (!ordinal) return factorMode ? '' : String(bundleSize)
        return factorMode ? ordinal : `${bundleSize} (${ordinal.replace(/^⭐/, '')})`
    }

    const significantValues = []
    observedEntries.forEach(([value, observed]) => {
        const valueTotal = totalCounts.get(value) || 0
        if (valueTotal === 0 || grandTotal === 0) return
        const expected = (bundleSize * valueTotal) / grandTotal
        const chisq = expected > 0 ? Math.pow(observed - expected, 2) / expected : 0
        if (chisq > chiSqCritical1df) {
            const arrow = observed > expected ? '▲' : '▼'
            if (mode === 'chisq-counts') significantValues.push(`${value}: ${observed}${arrow}`)
            else if (mode === 'chisq-counts-totals') significantValues.push(`${value}: ${observed}/${valueTotal}${arrow}`)
            else significantValues.push(`${value}${arrow}`)
        }
    })
    if (factorMode) return significantValues.length ? `⭐${significantValues.join(', ')}` : ''
    return significantValues.length ? `${bundleSize} (${significantValues.join(', ')})` : String(bundleSize)
}

function ordinalTrendDisplay(params) {
    const { ordinalCorrection, trendTest, totalCounts, observedEntries, sigLevel } = params
    if (!ordinalCorrection || !trendTest) return null
    const scored = Array.from(totalCounts.keys()).map(value => ({ value, score: parseLeadingInt(value) }))
    const numericLike = scored.length >= 2 && scored.every(item => item.score !== null)
    if (!numericLike) return null
    const observedMap = new Map(observedEntries)
    scored.sort((a, b) => (a.score - b.score) || String(a.value).localeCompare(String(b.value)))
    const observedCounts = scored.map(item => observedMap.get(item.value) || 0)
    const totals = scored.map(item => totalCounts.get(item.value) || 0)
    const scores = scored.map(item => item.score)
    const result = trendTest(observedCounts, totals, scores)
    if (result?.isValid && result.pValue < sigLevel && (result.direction === 'up' || result.direction === 'down')) {
        return result.direction === 'up' ? '⭐▲' : '⭐▼'
    }
    return ''
}

function getMapCustomTextValues(edgeLinks, fieldName) {
    return (Array.isArray(edgeLinks) ? edgeLinks : [])
        .map(link => getLinkCustomColumnValue(link, fieldName))
        .map(value => String(value ?? '').trim())
        .filter(Boolean)
}

function getMapCustomNumericValues(edgeLinks, fieldName) {
    return getMapCustomTextValues(edgeLinks, fieldName)
        .map(value => Number(value))
        .filter(value => Number.isFinite(value))
}

function countValues(links, field) {
    const counts = new Map()
    links.forEach(link => {
        const value = getLinkCustomColumnValue(link, field)
        if (value !== undefined && value !== null && value !== '') counts.set(value, (counts.get(value) || 0) + 1)
    })
    return counts
}

function sortedCounts(counts) {
    return Array.from(counts.entries()).sort((a, b) => String(a[0]).localeCompare(String(b[0])))
}

function sortedSetCounts(sets) {
    return Array.from(sets.entries())
        .map(([value, set]) => [value, set.size])
        .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
}

function isChiSquareMode(mode) {
    return mode === 'chisq' || mode === 'chisq-counts' || mode === 'chisq-counts-totals'
}

function chiSquareCritical1df(sigLevel) {
    if (sigLevel === 0.1) return 2.71
    if (sigLevel === 0.01) return 6.63
    if (sigLevel === 0.005) return 7.88
    return 3.84
}

function parseLeadingInt(value) {
    const match = String(value ?? '').trim().match(/^([+-]?\d+)/)
    if (!match) return null
    const n = parseInt(match[1], 10)
    return Number.isFinite(n) ? n : null
}

function formatMapCustomNumericValue(value) {
    const n = Number(value)
    if (!Number.isFinite(n)) return ''
    if (Number.isInteger(n)) return String(n)
    return n.toFixed(2).replace(/\.?0+$/, '')
}

function computeNumericMode(values) {
    const counts = new Map()
    values.forEach(value => counts.set(value, (counts.get(value) || 0) + 1))
    return Array.from(counts.entries()).sort((a, b) => (b[1] - a[1]) || (b[0] - a[0]))[0]?.[0] ?? null
}

function mapNumericValueToMutedDivergingColour(value, minValue, maxValue) {
    const valueNum = Number(value)
    const minNum = Number(minValue)
    const maxNum = Number(maxValue)
    const whiteish = { r: 245, g: 245, b: 245 }
    const mutedGreen = { r: 120, g: 155, b: 120 }
    const mutedBlue = { r: 107, g: 140, b: 174 }

    if (!Number.isFinite(valueNum) || !Number.isFinite(minNum) || !Number.isFinite(maxNum)) return interpolateRgbColor(whiteish, whiteish, 0)
    if (minNum === maxNum) {
        if (valueNum > 0) return interpolateRgbColor(mutedGreen, mutedGreen, 0)
        if (valueNum < 0) return interpolateRgbColor(mutedBlue, mutedBlue, 0)
        return interpolateRgbColor(whiteish, whiteish, 0)
    }
    if (minNum < 0 && maxNum > 0) {
        if (valueNum >= 0) return interpolateRgbColor(whiteish, mutedGreen, maxNum === 0 ? 0 : (valueNum / maxNum))
        return interpolateRgbColor(whiteish, mutedBlue, minNum === 0 ? 0 : (valueNum / minNum))
    }
    if (maxNum <= 0) return interpolateRgbColor(whiteish, mutedBlue, (maxNum === minNum) ? 0 : ((valueNum - maxNum) / (minNum - maxNum)))
    return interpolateRgbColor(whiteish, mutedGreen, (maxNum === minNum) ? 0 : ((valueNum - minNum) / (maxNum - minNum)))
}

function interpolateRgbColor(fromRgb, toRgb, t) {
    const tt = Math.max(0, Math.min(1, Number(t) || 0))
    const r = Math.round(fromRgb.r + (toRgb.r - fromRgb.r) * tt)
    const g = Math.round(fromRgb.g + (toRgb.g - fromRgb.g) * tt)
    const b = Math.round(fromRgb.b + (toRgb.b - fromRgb.b) * tt)
    return `rgb(${r}, ${g}, ${b})`
}
