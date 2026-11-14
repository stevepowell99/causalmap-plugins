// Behavioural flags for filter types. Deliberately a leaf module with no
// imports, so Node test harnesses can read it without pulling in the browser
// -only filter pipeline.
// Display metadata for the same types lives in FILTER_TYPE_META
// (filter-pipeline-ui.js); this file is only about how they compose.

/** Filter types whose effect is a SETTING (one threshold, one level, one
 *  mapping, one grouping) rather than a SELECTION. Two of these in one
 *  pipeline are never what anyone meant: the looser one is a no-op behind the
 *  tighter one, and the tighter one is just the first with a new value. So
 *  "set link frequency to 3" when a link-frequency filter already sits at 5
 *  means change 5 to 3, not stack a second filter.
 *
 *  Types left out (source-groups, everything, label, exclude-label, tags,
 *  exclude-tags, path-tracing, collapse) genuinely stack, because each narrows
 *  on a different field or label set.
 *
 *  Single source for: MapCat's add-guard (app.js), the rule injected into its
 *  prompt (docs-bot-manager.js), and the verb bank. */
export const SETTINGS_ONLY_FILTER_TYPES = [
    'link-frequency',
    'factor-frequency',
    'assessed',
    'animate',
    'exclude-self-loops',
    'pathways',
    'zoom',
    'combine-opposites',
    'custom-links-label',
    'map-custom-columns',
    'replace-brackets',
    'soft-relabel',
    'temp-cause-effect',
    'dev-soft-recode',
    'cluster',
    'hierarchical-cluster',
    'tribes'
]

const SETTINGS_ONLY = new Set(SETTINGS_ONLY_FILTER_TYPES)

export function isSettingsOnlyFilterType(type) {
    return SETTINGS_ONLY.has(String(type || '').trim())
}


/* ===================== Filter ordering rules =====================
 *
 * The app applies filters top to bottom, and each one gets only the links the
 * filter above it kept, so order is part of the analysis. Two orderings are wrong
 * often enough to warn about. This block is the single source for all of it:
 * the warning in the filter pane, the rule injected into MapCat's prompt, and
 * the user docs (webapp/README.md "Filter ordering rules", mirrored in the
 * garden), which must be kept in step with the wording here.
 *
 * Neither rule is a hard constraint. A user with a reason can order the chain
 * however they like; we ask the question and let them dismiss it.
 */

/** Filters that pick out intact causal paths. A Factor Label filter joins them
 *  whenever its steps go beyond the immediate neighbours (see isTracingFilter). */
export const TRACING_FILTER_TYPES = ['path-tracing', 'pathways']

/** Filters that count the links they are given, so they answer a different
 *  question at every position in the chain. */
export const FREQUENCY_FILTER_TYPES = ['link-frequency', 'factor-frequency']

/** Filters that rewrite factor labels, so anything below them works on the new
 *  labels. Tribes and the link-label filters are left out: they relabel sources
 *  or links, not the factors a path connects. */
export const LABEL_REWRITING_FILTER_TYPES = [
    'zoom',
    'collapse',
    'combine-opposites',
    'replace-brackets',
    'soft-relabel',
    'temp-cause-effect',
    'dev-soft-recode',
    'cluster',
    'hierarchical-cluster'
]

const TRACING = new Set(TRACING_FILTER_TYPES)
const FREQUENCY = new Set(FREQUENCY_FILTER_TYPES)
const LABEL_REWRITING = new Set(LABEL_REWRITING_FILTER_TYPES)

/** True for path tracing and Pathways always, and for a Factor Label filter
 *  once it reaches past the immediate neighbours: at more than one step the
 *  filter is walking chains, not picking a set of factors. */
export function isTracingFilter(filter) {
    const type = String(filter?.type || '').trim()
    if (TRACING.has(type)) return true
    if (type !== 'label') return false
    const up = Number(filter?.stepsUp)
    const down = Number(filter?.stepsDown)
    return (Number.isFinite(up) && up > 1) || (Number.isFinite(down) && down > 1)
}

export function isFrequencyFilterType(type) {
    return FREQUENCY.has(String(type || '').trim())
}

export function isLabelRewritingFilterType(type) {
    return LABEL_REWRITING.has(String(type || '').trim())
}

/** The rules in prose. Used verbatim by MapCat's prompt and echoed by the
 *  filter pane, so a user and MapCat get the same answer to "why?". */
export const FILTER_ORDER_RULES = [
    {
        id: 'trace-first',
        headline: 'Put tracing at the top of the chain.',
        why: 'Path tracing, source tracing (path tracing with threads on), the Pathways filter and a Factor Label filter set to more than one step all exist to find causal paths that are really in the data. Put a filter that rewrites factor labels above them (Zoom, Collapse, Combine Opposites, Remove Brackets, Soft Relabel, Soft Recode Plus, Cluster, Auto Recode) and it merges factors that were two different things in the coding, so you trace a route through a junction nobody described. Put a frequency filter above them and it removes links the paths are made of, so you find no route where the data has one. Either way you are tracing a map that is no longer the coded data. Trace first, and simplify afterwards for presentation. Only the filters that choose which sources or links you are looking at belong above the tracing.'
    },
    {
        id: 'frequency-last',
        headline: 'Put the frequency filters at the bottom of the chain.',
        why: 'Link Frequency and Factor Frequency count the links they are given, so they mean something different at every position. Put them after the filters that decide what you are looking at. For an ego network, take the neighbourhood first and then the most frequent material within it, and you learn what people said most about that factor. The other way round you keep the most popular material in the whole corpus and then cut it down to the ego, which is a different map and usually not the one you wanted. You can put an Exclude self-loops filter after them.'
    },
    {
        id: 'opposites-before-relabel',
        headline: 'Put Combine Opposites above the filters that replace labels.',
        why: 'Combine Opposites finds each pair by reading the labels it is given: a numeric tag such as [~3] against [3], or a label starting with ~ against the same label without it. Remove Brackets deletes the square-bracket tags, and Collapse, Soft Relabel, Soft Recode Plus, Cluster and Auto Recode replace a label with a new one that no longer carries the marker. Put one of those above Combine Opposites and it finds no pairs at all, so the negative and the positive stay on the map as two separate factors and nothing tells you the pairing was lost. Combine the opposites first, then replace labels for presentation. Zoom is the exception: it truncates the hierarchy and keeps the marker on whatever it keeps.'
    }
]

/** Types allowed below a frequency filter without breaking rule 2. */
const ALLOWED_BELOW_FREQUENCY = new Set([...FREQUENCY_FILTER_TYPES, 'exclude-self-loops'])

/** Filters that replace a factor label with a different one, so the [~3]/[3]
 *  tags and the leading ~ that Combine Opposites reads are gone by the time it
 *  runs (rule 3). Zoom is deliberately absent: it truncates the hierarchy and
 *  keeps the marker on the part it keeps. */
export const LABEL_REPLACING_FILTER_TYPES = [
    'collapse',
    'replace-brackets',
    'soft-relabel',
    'dev-soft-recode',
    'cluster',
    'hierarchical-cluster'
]

const LABEL_REPLACING = new Set(LABEL_REPLACING_FILTER_TYPES)

/** Whether this filter would actually destroy the markers Combine Opposites
 *  reads. Remove Brackets only does so when it is set to remove SQUARE
 *  brackets, since the numeric tags are `[~3]`/`[3]`; on round brackets alone
 *  the tags survive and there is nothing to warn about. */
export function destroysOppositeMarkers(filter) {
    const type = String(filter?.type || '').trim()
    if (!LABEL_REPLACING.has(type)) return false
    if (type !== 'replace-brackets') return true
    const hasNew = (typeof filter?.replaceRound === 'boolean') || (typeof filter?.replaceSquare === 'boolean')
    return hasNew ? !!filter.replaceSquare : (filter?.bracketMode === 'square')
}

/**
 * Where a filter of this type should go when nobody said where, so an
 * automatically built chain (MapCat, a report recipe) obeys the rules without
 * being told each time. A caller with an explicit position wins.
 *
 * @param {Array} filters  the pipeline as it stands, in order.
 * @param {string} type    the type about to be added.
 * @returns {number} insertion index.
 */
export function suggestFilterPosition(filters, type) {
    const chain = Array.isArray(filters) ? filters : []
    const cleanType = String(type || '').trim()
    const typeAt = (i) => String(chain[i]?.type || '').trim()

    // Rule 1: tracing belongs above the first filter that rewrites labels or counts.
    if (TRACING.has(cleanType)) {
        const blocker = chain.findIndex(f => isLabelRewritingFilterType(f?.type) || isFrequencyFilterType(f?.type))
        return blocker === -1 ? chain.length : blocker
    }

    // Rule 2: frequency goes last, above only a trailing Exclude self-loops.
    if (FREQUENCY.has(cleanType)) {
        let end = chain.length
        while (end > 0 && typeAt(end - 1) === 'exclude-self-loops') end--
        return end
    }

    // Rule 3: Combine Opposites lands above the first filter that would replace
    // the labels it reads, and above the frequency filters like anything else.
    const firstFrequency = chain.findIndex(f => isFrequencyFilterType(f?.type))
    if (cleanType === 'combine-opposites') {
        const firstReplacer = chain.findIndex(f => destroysOppositeMarkers(f))
        const limits = [firstReplacer, firstFrequency].filter(i => i !== -1)
        return limits.length ? Math.min(...limits) : chain.length
    }

    // Everything else goes at the end of the chain but still above the frequency filters.
    return firstFrequency === -1 ? chain.length : firstFrequency
}

/**
 * Check a filter chain against the ordering rules.
 *
 * @param {Array} filters  the pipeline, in order, as stored on FilterPipeline.
 * @returns {Array} one entry per broken rule:
 *   { ruleId, filterId, filterType, offenderId, offenderType, question }
 *   Empty means the chain obeys both rules (or has nothing to say about them).
 */
export function checkFilterOrder(filters) {
    const chain = (Array.isArray(filters) ? filters : []).filter(f => f && f.enabled !== false)
    const violations = []

    chain.forEach((filter, index) => {
        if (isTracingFilter(filter)) {
            const offender = chain.slice(0, index).find(f =>
                isLabelRewritingFilterType(f.type) || isFrequencyFilterType(f.type))
            if (offender) {
                violations.push({
                    ruleId: 'trace-first',
                    filterId: filter.id,
                    filterType: filter.type,
                    offenderId: offender.id,
                    offenderType: offender.type,
                    question: isFrequencyFilterType(offender.type)
                        ? 'A frequency filter comes before your tracing filter, so you are tracing paths through links that have already been removed. Move the tracing above it?'
                        : 'A filter that rewrites factor labels comes before your tracing filter, so you are tracing merged labels rather than the coded factors. Move the tracing above it?'
                })
            }
        }

        if (String(filter.type || '').trim() === 'combine-opposites') {
            const offender = chain.slice(0, index).find(f => destroysOppositeMarkers(f))
            if (offender) {
                violations.push({
                    ruleId: 'opposites-before-relabel',
                    filterId: filter.id,
                    filterType: filter.type,
                    offenderId: offender.id,
                    offenderType: offender.type,
                    question: 'A filter that replaces factor labels comes before Combine Opposites, which reads the labels to find each pair, so it will find no pairs and the opposites will stay on the map as separate factors. Move Combine Opposites above it?'
                })
            }
        }

        if (isFrequencyFilterType(filter.type)) {
            const offender = chain.slice(index + 1).find(f => !ALLOWED_BELOW_FREQUENCY.has(String(f.type || '').trim()))
            if (offender) {
                violations.push({
                    ruleId: 'frequency-last',
                    filterId: filter.id,
                    filterType: filter.type,
                    offenderId: offender.id,
                    offenderType: offender.type,
                    question: 'A frequency filter comes before the rest of your chain, so the counting happens on the whole map and the filters below it only trim what survived. Move it to the bottom?'
                })
            }
        }
    })

    return violations
}
