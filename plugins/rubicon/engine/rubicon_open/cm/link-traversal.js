// Pure causal-link traversal shared by the UI filter pipeline and app API.

export function normalizeTraversalSteps(value, maxSteps = 8) {
    const n = Number(value)
    if (!Number.isFinite(n)) return 0
    return Math.max(0, Math.min(maxSteps, Math.trunc(n)))
}

export function getLinkSourceIdsForTracing(link) {
    if (!link || typeof link !== 'object') return []
    const assessedSourceIds = link.assessed === true && Array.isArray(link.metadata?.assessment_source_ids)
        ? link.metadata.assessment_source_ids
            .map(sourceId => String(sourceId || '').trim())
            .filter(Boolean)
        : []
    if (assessedSourceIds.length > 0) return Array.from(new Set(assessedSourceIds))

    const sourceId = String(link.source_id || '').trim()
    return sourceId ? [sourceId] : []
}

// A link's quote position as { start, end } (half-open char range), or null if it has no usable
// position yet. Degenerate "never set" offsets count as no position: missing/non-numeric start, a
// zero-length span, or the classic 0/0 default. When the end is absent but the start is real, the
// quote's text length supplies the end. Single source of truth for the Pathways filter, the offset
// recalc, and the auto-heal trigger.
export function quoteOffsetSpan(link) {
    const start = Number(link?.text_start_offset)
    if (!Number.isFinite(start)) return null
    const rawEnd = Number(link?.text_end_offset)
    const end = (Number.isFinite(rawEnd) && rawEnd > start) ? rawEnd : start + String(link?.selected_text ?? '').length
    if (end <= start) return null
    // 0/0 (or 0 with no real end) is the unset default, not a quote genuinely at character 0.
    if (start === 0 && !(Number.isFinite(rawEnd) && rawEnd > 0)) return null
    return { start, end }
}

// True when a link has a quote and source that COULD be positioned but currently has no usable offset.
export function linkNeedsQuoteOffset(link) {
    if (!String(link?.selected_text ?? '').trim()) return false
    if (!String(link?.source_id ?? '').trim()) return false
    return quoteOffsetSpan(link) === null
}

export function findLinksWithinSteps(links, targetFactors, stepsUp, stepsDown) {
    const validLinks = new Set()
    const linksByEffect = new Map()
    const linksByCause = new Map()

    for (const link of Array.isArray(links) ? links : []) {
        const cause = String(link?.cause || '').trim()
        const effect = String(link?.effect || '').trim()
        if (!cause || !effect) continue

        if (!linksByEffect.has(effect)) linksByEffect.set(effect, [])
        linksByEffect.get(effect).push(link)

        if (!linksByCause.has(cause)) linksByCause.set(cause, [])
        linksByCause.get(cause).push(link)
    }

    const up = normalizeTraversalSteps(stepsUp)
    const down = normalizeTraversalSteps(stepsDown)

    // Upstream means causes of the target factor.
    if (up > 0) {
        let currentFactors = new Set(targetFactors || [])
        for (let step = 0; step < up; step += 1) {
            const nextFactors = new Set()
            for (const factor of currentFactors) {
                for (const link of linksByEffect.get(factor) || []) {
                    validLinks.add(link)
                    const next = String(link?.cause || '').trim()
                    if (next) nextFactors.add(next)
                }
            }
            currentFactors = nextFactors
            if (!currentFactors.size) break
        }
    }

    // Downstream means effects of the target factor.
    if (down > 0) {
        let currentFactors = new Set(targetFactors || [])
        for (let step = 0; step < down; step += 1) {
            const nextFactors = new Set()
            for (const factor of currentFactors) {
                for (const link of linksByCause.get(factor) || []) {
                    validLinks.add(link)
                    const next = String(link?.effect || '').trim()
                    if (next) nextFactors.add(next)
                }
            }
            currentFactors = nextFactors
            if (!currentFactors.size) break
        }
    }

    return Array.from(validLinks)
}

export function findLinksWithinStepsWithThreads(links, targetFactors, stepsUp, stepsDown, getSourceIds = getLinkSourceIdsForTracing) {
    const validLinks = new Set()
    const linksByEffectAndSource = new Map()
    const linksByCauseAndSource = new Map()

    for (const link of Array.isArray(links) ? links : []) {
        const cause = String(link?.cause || '').trim()
        const effect = String(link?.effect || '').trim()
        const sourceIds = getSourceIds(link)
        if (!cause || !effect || sourceIds.length === 0) continue

        for (const sourceId of sourceIds) {
            if (!linksByEffectAndSource.has(effect)) linksByEffectAndSource.set(effect, new Map())
            if (!linksByEffectAndSource.get(effect).has(sourceId)) linksByEffectAndSource.get(effect).set(sourceId, [])
            linksByEffectAndSource.get(effect).get(sourceId).push(link)

            if (!linksByCauseAndSource.has(cause)) linksByCauseAndSource.set(cause, new Map())
            if (!linksByCauseAndSource.get(cause).has(sourceId)) linksByCauseAndSource.get(cause).set(sourceId, [])
            linksByCauseAndSource.get(cause).get(sourceId).push(link)
        }
    }

    const up = normalizeTraversalSteps(stepsUp)
    const down = normalizeTraversalSteps(stepsDown)
    const targets = new Set(targetFactors || [])

    if (up > 0) {
        for (const targetFactor of targets) {
            const sourceMap = linksByEffectAndSource.get(targetFactor)
            if (!sourceMap) continue
            for (const sourceId of sourceMap.keys()) {
                traverseSameSource(linksByEffectAndSource, targetFactor, sourceId, up, 'cause', validLinks)
            }
        }
    }

    if (down > 0) {
        for (const targetFactor of targets) {
            const sourceMap = linksByCauseAndSource.get(targetFactor)
            if (!sourceMap) continue
            for (const sourceId of sourceMap.keys()) {
                traverseSameSource(linksByCauseAndSource, targetFactor, sourceId, down, 'effect', validLinks)
            }
        }
    }

    return Array.from(validLinks)
}

function traverseSameSource(index, startFactor, sourceId, steps, nextField, validLinks) {
    let currentFactors = new Set([startFactor])
    for (let step = 0; step < steps; step += 1) {
        const nextFactors = new Set()
        for (const factor of currentFactors) {
            const factorSourceMap = index.get(factor)
            const stepLinks = factorSourceMap?.get(sourceId) || []
            for (const link of stepLinks) {
                validLinks.add(link)
                const next = String(link?.[nextField] || '').trim()
                if (next) nextFactors.add(next)
            }
        }
        currentFactors = nextFactors
        if (!currentFactors.size) break
    }
}
