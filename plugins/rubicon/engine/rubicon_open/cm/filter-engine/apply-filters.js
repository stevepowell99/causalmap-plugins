// Shared, pure filter engine: links + sources tables in, filtered links out.
// No window / DataService / DOM. Imported by BOTH the browser webapp and the Deno edge function,
// so it must stay plain .js (no TypeScript, no build step) and import only pure helpers.
//
// This is the single source of truth for ordered link filtering. The webapp pipeline and the
// app-api edge function both call it; do not reintroduce a parallel copy.
import {
  applyLabelByGroupToFactors,
  attachReservedCmLinkFields,
} from '../link-display-transforms.js'
import { findLinksWithinSteps, findLinksWithinStepsWithThreads, getLinkSourceIdsForTracing } from '../link-traversal.js'
import { applyPathTracingFilter } from './path-tracing.js'

function norm(value) {
  return String(value ?? '').trim().toLowerCase().replace(/\s+/g, ' ')
}

function arr(value) {
  return Array.isArray(value)
    ? value.map((v) => String(v ?? '').trim()).filter(Boolean)
    : String(value ?? '').split(',').map((v) => v.trim()).filter(Boolean)
}

// Canonical (webapp) default is 'start' when no matchMode is given.
function checkTextMatch(value, term, mode) {
  const text = String(value ?? '').toLowerCase()
  const search = String(term ?? '').toLowerCase()
  if (!search) return false
  if (mode === 'anywhere') return text.includes(search)
  if (mode === 'exact') return text === search
  return text.startsWith(search) // 'start' and default
}

// Webapp tag list: array as-is, or comma-split a string (trim + drop empties).
function linkTagsList(link) {
  return Array.isArray(link.tags)
    ? link.tags
    : (link.tags || '').split(',').map((t) => t.trim()).filter((t) => t)
}

/** Match DataService.applySourceJoinInPlace: expose source custom_columns/metadata on each row for label-by-group + map bundles. */
function mergeSourceMetadataOntoLinks(links, sourceById) {
  return links.map((link) => {
    const sid = String(link?.source_id ?? '').trim()
    const source = sourceById.get(sid)
    if (!source || typeof link !== 'object') return link
    const out = { ...link }
    const md = source.metadata && typeof source.metadata === 'object' ? source.metadata : {}
    const cc = md.custom_columns && typeof md.custom_columns === 'object' ? md.custom_columns : {}
    for (const key of Object.keys(cc)) {
      const safeKey = String(key).replace(/[\s/]/g, '_')
      out[`s_${safeKey}`] = cc[key]
    }
    for (const key of Object.keys(md)) {
      if (key === 'custom_columns') continue
      const value = md[key]
      if (typeof value !== 'object' || value === null) {
        out[`source_${key}`] = value
      }
    }
    return out
  })
}

// Factors whose cause/effect matches the filter's selected labels. Exposed so the webapp can reuse
// the exact same matching for its highlight outputs.
export function matchLabelFactors(links, filter) {
  const selected = arr(filter.selectedLabels)
  const mode = filter.matchMode
  const targetFactors = new Set()
  if (!selected.length) return targetFactors
  for (const link of links) {
    const cause = String(link?.cause || '')
    const effect = String(link?.effect || '')
    for (const label of selected) {
      if (checkTextMatch(cause, label, mode)) targetFactors.add(cause)
      if (checkTextMatch(effect, label, mode)) targetFactors.add(effect)
    }
  }
  return targetFactors
}

export function applyLabelFilter(links, filter) {
  const selected = arr(filter.selectedLabels)
  if (!selected.length) return links
  const targetFactors = matchLabelFactors(links, filter)
  if (!targetFactors.size) return []
  if (Number(filter.stepsUp) === 0 && Number(filter.stepsDown) === 0) return []
  // Same-source thread tracing uses getLinkSourceIdsForTracing, which is what the webapp uses.
  if (filter.traceThreads) {
    return findLinksWithinStepsWithThreads(links, targetFactors, filter.stepsUp ?? 1, filter.stepsDown ?? 1)
  }
  return findLinksWithinSteps(links, targetFactors, filter.stepsUp ?? 1, filter.stepsDown ?? 1)
}

// Keep links whose tags match ANY selected tag (OR). Links with no tags are dropped.
export function applyTagsFilter(links, filter) {
  const selected = Array.isArray(filter.selectedTags) ? filter.selectedTags : []
  if (!selected.length) return links
  return links.filter((link) => {
    if (!link.tags) return false
    const linkTags = linkTagsList(link)
    return selected.some((selectedTag) =>
      linkTags.some((linkTag) => checkTextMatch(linkTag, selectedTag, filter.matchMode)))
  })
}

// Exclude links whose tags match the selected tags. Default ALL (every); excludeAny uses OR (some).
// Links with no tags are kept.
export function applyExcludeTagsFilter(links, filter) {
  const selected = Array.isArray(filter.selectedTags) ? filter.selectedTags : []
  if (!selected.length) return links
  const excludeAny = filter.excludeAny === true
  return links.filter((link) => {
    if (!link.tags) return true
    const linkTags = linkTagsList(link)
    const tagsMatch = excludeAny
      ? selected.some((et) => linkTags.some((lt) => checkTextMatch(lt, et, filter.matchMode)))
      : selected.every((et) => linkTags.some((lt) => checkTextMatch(lt, et, filter.matchMode)))
    return !tagsMatch
  })
}

// Membership over a resolved link column (the caller resolves filter.selectedField first). No trim.
export function applyEverythingFilter(links, filter) {
  const field = filter.selectedField
  const values = Array.isArray(filter.selectedValues) ? filter.selectedValues : []
  if (!field || !values.length) return links
  return links.filter((link) => {
    const fieldValue = link[field]
    if (fieldValue !== null && fieldValue !== undefined && fieldValue !== '') {
      if (Array.isArray(fieldValue)) return fieldValue.some((v) => values.includes(String(v)))
      return values.includes(String(fieldValue))
    }
    return false
  })
}

// Exclude links whose cause/effect match the selected labels. Default ALL (every); excludeAny uses OR (some).
export function applyExcludeLabelFilter(links, filter) {
  const selected = Array.isArray(filter.selectedLabels) ? filter.selectedLabels : []
  if (!selected.length) return links
  const excludeAny = filter.excludeAny === true
  return links.filter((link) => {
    const cause = link.cause || ''
    const effect = link.effect || ''
    const labelsMatch = excludeAny
      ? selected.some((el) => checkTextMatch(cause, el, filter.matchMode) || checkTextMatch(effect, el, filter.matchMode))
      : selected.every((el) => checkTextMatch(cause, el, filter.matchMode) || checkTextMatch(effect, el, filter.matchMode))
    return !labelsMatch
  })
}

function applySourcesFilter(links, filter) {
  const sourceIds = new Set(arr(filter.sourceIds).map((id) => norm(id)))
  if (!sourceIds.size) return links
  return links.filter((link) => sourceIds.has(norm(link?.source_id)))
}

// Threshold/mode selection shared by both frequency filters (faithful to the webapp).
// mode: 'minimum' keeps metrics >= threshold; anything else is 'top' (default) keeping the
// top-`threshold` by value, ties at the cutoff included. which: 'sources' counts unique sources,
// anything else counts appearances (default).
function frequencyAllowed(metrics, filter) {
  const threshold = filter.threshold || 1
  const allowed = new Set()
  if (filter.mode === 'minimum') {
    metrics.forEach((count, key) => {
      if (count >= threshold) allowed.add(key)
    })
  } else {
    const sorted = Array.from(metrics.entries()).sort((a, b) => b[1] - a[1])
    if (sorted.length > 0) {
      const idx = Math.min(threshold - 1, sorted.length - 1)
      const cutoff = sorted[idx][1]
      sorted.forEach(([key, cnt]) => {
        if (cnt >= cutoff) allowed.add(key)
      })
    }
  }
  return allowed
}

/**
 * Link frequency filter. Bundles links by cause|||effect, optionally separating flipped opposite
 * pairs. `options.separateFlippedBundles` is the resolved combine-opposites bundle decision
 * (strategy === 'separate'); the caller computes it from the active combine-opposites filter and
 * passes it in, so the engine stays free of pipeline-state lookups. The per-link flip flags
 * (flipped_cause / flipped_effect) are already on the link, set upstream by combine-opposites.
 */
export function applyLinkFrequencyFilter(links, filter, options = {}) {
  const separateFlippedBundles = options.separateFlippedBundles === true
  const getBundleKey = (link) => {
    const c = `${(link.cause || '').trim()}`
    const e = `${(link.effect || '').trim()}`
    const hasFlip = (typeof link.flipped_cause === 'boolean') || (typeof link.flipped_effect === 'boolean')
    if (!hasFlip || !separateFlippedBundles) return `${c}|||${e}`
    const fc = link.flipped_cause === true ? 'F' : '-'
    const fe = link.flipped_effect === true ? 'F' : '-'
    return `${c}|||${e}|||${fc}${fe}`
  }

  const linkMetrics = new Map()
  if (filter.which === 'sources') {
    const sourceSets = new Map()
    links.forEach((link) => {
      const key = getBundleKey(link)
      if (!sourceSets.has(key)) sourceSets.set(key, new Set())
      getLinkSourceIdsForTracing(link).forEach((sourceId) => sourceSets.get(key).add(sourceId))
    })
    sourceSets.forEach((set, key) => linkMetrics.set(key, set.size))
  } else {
    links.forEach((link) => {
      const key = getBundleKey(link)
      linkMetrics.set(key, (linkMetrics.get(key) || 0) + 1)
    })
  }

  const allowedKeys = frequencyAllowed(linkMetrics, filter)
  return links.filter((link) => allowedKeys.has(getBundleKey(link)))
}

// Factor frequency filter: count factors (cause/effect) and keep links where BOTH ends pass.
// No flip bundling (factors, not link pairs).
export function applyFactorFrequencyFilter(links, filter) {
  const factorCounts = new Map()
  if (filter.which === 'sources') {
    const factorSourceSets = new Map()
    links.forEach((link) => {
      const sourceIds = getLinkSourceIdsForTracing(link)
      if (sourceIds.length === 0) return
      const cause = (link.cause || '').trim()
      const effect = (link.effect || '').trim()
      if (cause) {
        if (!factorSourceSets.has(cause)) factorSourceSets.set(cause, new Set())
        sourceIds.forEach((sourceId) => factorSourceSets.get(cause).add(sourceId))
      }
      if (effect) {
        if (!factorSourceSets.has(effect)) factorSourceSets.set(effect, new Set())
        sourceIds.forEach((sourceId) => factorSourceSets.get(effect).add(sourceId))
      }
    })
    factorSourceSets.forEach((set, factor) => factorCounts.set(factor, set.size))
  } else {
    links.forEach((link) => {
      const cause = (link.cause || '').trim()
      const effect = (link.effect || '').trim()
      if (cause) factorCounts.set(cause, (factorCounts.get(cause) || 0) + 1)
      if (effect) factorCounts.set(effect, (factorCounts.get(effect) || 0) + 1)
    })
  }

  const allowedFactors = frequencyAllowed(factorCounts, filter)
  return links.filter((link) => allowedFactors.has((link.cause || '').trim()) && allowedFactors.has((link.effect || '').trim()))
}

// Membership over a resolved source-group column flattened onto each link (s_*/source_*).
// The caller resolves filter.selectedField to that key first. Exact value match, trimmed.
export function applySourceGroupsFilter(links, filter) {
  const field = filter.selectedField
  const values = Array.isArray(filter.selectedValues) ? filter.selectedValues : []
  if (!field || !values.length) return links
  return links.filter((link) => {
    const fieldValue = link[field]
    if (fieldValue === null || fieldValue === undefined || fieldValue === '') return false
    if (Array.isArray(fieldValue)) return fieldValue.some((v) => values.includes(String(v).trim()))
    return values.includes(String(fieldValue).trim())
  })
}

export function applyExcludeSelfLoops(links) {
  return links.filter((link) => (link.cause || '').trim() !== (link.effect || '').trim())
}

// Canonical per-label transforms (match the webapp's applyZoomToLabel / applyCollapseToLabel /
// applyBracketReplacement exactly).
export function applyZoomToLabel(label, level) {
  if (!label || level === 0 || level === '0' || level === 'none') return label
  const levelNum = parseInt(level)
  if (isNaN(levelNum) || levelNum <= 0) return label
  const parts = label.split(';').map((p) => p.trim())
  if (parts.length <= levelNum) return label
  return parts.slice(0, levelNum).join('; ')
}

export function applyCollapseToLabel(label, selectedLabels, separate, matchMode) {
  if (!label || !selectedLabels || selectedLabels.length === 0) return label
  let result = label
  if (separate) {
    // Replace each matching search term with itself (re-checked against the running result).
    selectedLabels.forEach((searchTerm) => {
      if (checkTextMatch(result, searchTerm, matchMode)) result = searchTerm
    })
  } else {
    // Replace any matching label with the first search term.
    if (selectedLabels.some((searchTerm) => checkTextMatch(result, searchTerm, matchMode))) {
      result = selectedLabels[0]
    }
  }
  return result
}

function applyBracketReplacement(label, replaceRound, replaceSquare) {
  if (!label || (!replaceRound && !replaceSquare)) return label
  let result = label
  if (replaceRound) result = result.replace(/\([^)]*\)/g, '').trim()
  if (replaceSquare) result = result.replace(/\[[^\]]*\]/g, '').trim()
  return result
}

/**
 * Shared recoding transform for the label-transform family (zoom / collapse / replace-brackets).
 * Applies `transformLabel` to each cause/effect, tracks `_recoded` provenance (preserving the
 * earliest original), and returns the set of changed (new) labels for highlights.
 * @param {Array} links
 * @param {(label:string)=>string} transformLabel
 * @param {{ setFlags?: boolean }} options  setFlags adds `_recoded_cause`/`_recoded_effect` (collapse,
 *   replace-brackets do; zoom does not).
 * @returns {{ rows: Array, changedFactors: Set<string> }}
 */
export function applyRecodingTransform(links, transformLabel, options = {}) {
  const setFlags = options.setFlags === true
  const changedFactors = new Set()
  const rows = links.map((link) => {
    const originalCause = link.cause
    const originalEffect = link.effect
    const newCause = transformLabel(originalCause)
    const newEffect = transformLabel(originalEffect)
    const recodedCause = newCause !== originalCause
    const recodedEffect = newEffect !== originalEffect
    if (recodedCause) changedFactors.add(newCause)
    if (recodedEffect) changedFactors.add(newEffect)

    // Preserve original labels in _recoded for downstream operations (e.g. rename).
    const recodedMeta = link._recoded || {
      cause: { original: originalCause, recoded: false },
      effect: { original: originalEffect, recoded: false },
    }
    if (recodedCause) {
      if (!recodedMeta.cause) recodedMeta.cause = { original: originalCause, recoded: true }
      else if (!recodedMeta.cause.original) recodedMeta.cause.original = originalCause
      recodedMeta.cause.recoded = true
    }
    if (recodedEffect) {
      if (!recodedMeta.effect) recodedMeta.effect = { original: originalEffect, recoded: true }
      else if (!recodedMeta.effect.original) recodedMeta.effect.original = originalEffect
      recodedMeta.effect.recoded = true
    }

    const out = { ...link, cause: newCause, effect: newEffect, _recoded: recodedMeta }
    if (setFlags) {
      out._recoded_cause = recodedCause || link._recoded_cause === true
      out._recoded_effect = recodedEffect || link._recoded_effect === true
    }
    return out
  })
  return { rows, changedFactors }
}

export function applyZoomFilter(links, filter) {
  if (!(filter.level > 0)) return links
  return applyRecodingTransform(links, (label) => applyZoomToLabel(label, filter.level), { setFlags: false }).rows
}

// Returns { rows, changedFactors }: changedFactors feeds the webapp's collapse highlights.
export function applyCollapseFilter(links, filter) {
  const selected = filter.selectedLabels && filter.selectedLabels.length ? filter.selectedLabels : []
  if (!selected.length) return { rows: links, changedFactors: new Set() }
  return applyRecodingTransform(
    links,
    (label) => applyCollapseToLabel(label, selected, filter.separate, filter.matchMode),
    { setFlags: true }
  )
}

export function applyReplaceBracketsFilter(links, filter) {
  const hasNew = (typeof filter?.replaceRound === 'boolean') || (typeof filter?.replaceSquare === 'boolean')
  const replaceRound = hasNew ? !!filter.replaceRound : (filter?.bracketMode === 'round')
  const replaceSquare = hasNew ? !!filter.replaceSquare : (filter?.bracketMode === 'square')
  if (!replaceRound && !replaceSquare) return links
  return applyRecodingTransform(
    links,
    (label) => applyBracketReplacement(label, replaceRound, replaceSquare),
    { setFlags: true }
  ).rows
}

// Webapp stripTags: remove bracketed [N] / [~N] tags, collapse whitespace.
function stripCombineTags(text) {
  if (!text) return ''
  return String(text).replace(/\[~\d+\]|\[\d+\]/g, '').replace(/\s+/g, ' ').trim()
}

function normalizeHierarchy(label) {
  return String(label || '').split(';').map((p) => p.replace(/\s+/g, ' ').trim()).filter(Boolean).join('; ')
}

// Faithful port of the webapp's combine-opposites inline branch. Rewrites negative variants
// ([~N] / legacy bareword ~N, and ~prefixed hierarchy labels) to their positive label and sets
// flipped_cause/flipped_effect. Numeric opposites default ON; tilde opposites default OFF.
export function applyCombineOppositesFilter(links, filter) {
  const useNumericOpposites = (filter.useNumericOpposites !== false)
  const useTildeOpposites = (filter.useTildeOpposites === true)

  const labelsSet = new Set()
  for (const link of links) {
    if (link.cause) labelsSet.add(link.cause)
    if (link.effect) labelsSet.add(link.effect)
  }

  // numericMapping: tagNum -> { negativeLabel, positiveLabel }
  const numericMapping = new Map()
  if (useNumericOpposites) {
    const tagPairs = new Map()
    labelsSet.forEach((label) => {
      const negMatch = label.match(/\[~(\d+)\]|~(\d+)/)
      if (negMatch) {
        const num = negMatch[1] || negMatch[2]
        if (!tagPairs.has(num)) tagPairs.set(num, {})
        tagPairs.get(num).negative = label
      }
      const bracketMatch = label.match(/\[(\d+)\]/)
      if (bracketMatch) {
        const matchIndex = label.indexOf(bracketMatch[0])
        if (matchIndex === 0 || label[matchIndex - 1] !== '~') {
          const num = bracketMatch[1]
          if (!tagPairs.has(num)) tagPairs.set(num, {})
          tagPairs.get(num).positive = label
        }
      } else {
        const allNumbers = label.matchAll(/\d+/g)
        for (const match of allNumbers) {
          const num = match[0]
          const matchIndex = match.index
          if (matchIndex === 0 || label[matchIndex - 1] !== '~') {
            if (!tagPairs.has(num)) tagPairs.set(num, {})
            tagPairs.get(num).positive = label
            break
          }
        }
      }
    })
    tagPairs.forEach((pair, num) => {
      if (pair.negative && pair.positive) {
        numericMapping.set(num, { negativeLabel: pair.negative, positiveLabel: pair.positive })
      }
    })
  }

  // tildeMapping: normalized ~label -> preferred opposite (existing original spelling if present).
  const tildeMapping = new Map()
  if (useTildeOpposites) {
    const toggleAllParts = (normalizedLabel) => normalizeHierarchy(normalizedLabel).split(';').map((part) => {
      const s = part.replace(/\s+/g, ' ').trim()
      return /^~\s*/.test(s) ? s.replace(/^~\s*/, '').trim() : `~${s}`
    }).join('; ')
    const normToOriginal = new Map()
    labelsSet.forEach((label) => {
      const orig = String(label || '')
      const norm = normalizeHierarchy(orig)
      if (!norm) return
      if (!normToOriginal.has(norm)) normToOriginal.set(norm, orig)
    })
    labelsSet.forEach((label) => {
      const orig = String(label || '').trim()
      if (!/^\s*~/.test(orig)) return
      const norm = normalizeHierarchy(orig)
      const oppositeNorm = toggleAllParts(norm)
      tildeMapping.set(norm, normToOriginal.get(oppositeNorm) || oppositeNorm)
    })
  }

  return links.map((link) => {
    let newCause = link.cause
    let newEffect = link.effect
    let flippedCause = false
    let flippedEffect = false

    if (useNumericOpposites) {
      if (link.effect) {
        const negTagMatch = link.effect.match(/\[~(\d+)\]|~(\d+)/)
        if (negTagMatch) {
          const mapping = numericMapping.get(negTagMatch[1] || negTagMatch[2])
          if (mapping) { newEffect = mapping.positiveLabel; flippedEffect = true }
        }
      }
      if (link.cause) {
        const negTagMatch = link.cause.match(/\[~(\d+)\]|~(\d+)/)
        if (negTagMatch) {
          const mapping = numericMapping.get(negTagMatch[1] || negTagMatch[2])
          if (mapping) { newCause = mapping.positiveLabel; flippedCause = true }
        }
      }
    }

    if (useTildeOpposites) {
      if (typeof newEffect === 'string' && /^\s*~/.test(newEffect)) {
        const mapped = tildeMapping.get(normalizeHierarchy(newEffect))
        if (mapped) { newEffect = mapped; flippedEffect = true }
      }
      if (typeof newCause === 'string' && /^\s*~/.test(newCause)) {
        const mapped = tildeMapping.get(normalizeHierarchy(newCause))
        if (mapped) { newCause = mapped; flippedCause = true }
      }
    }

    if (filter.stripTags !== false) {
      newCause = stripCombineTags(newCause)
      newEffect = stripCombineTags(newEffect)
    }

    return { ...link, cause: newCause, effect: newEffect, flipped_cause: flippedCause, flipped_effect: flippedEffect }
  })
}

/**
 * Apply an ordered list of link filters. Pure: data in, data out.
 * @param {Array} links   Enriched link rows.
 * @param {Array} filters Ordered filter configs ({ id, type, enabled?, ...cfg }).
 * @param {Array} sources Source rows (id, metadata.custom_columns); used by source-based filters.
 * @returns {{ rows: Array, unsupported: string[] }}
 */
export function applyOrderedLinkFilters(links, filters, sources = []) {
  const sourceById = new Map(sources.map((source) => [String(source?.id ?? ''), source]))
  let rows = Array.isArray(links) ? mergeSourceMetadataOntoLinks(links.slice(), sourceById) : []
  const list = Array.isArray(filters) ? filters : []
  const unsupported = []

  for (const raw of list) {
    const filter = raw && typeof raw === 'object' ? raw : null
    if (!filter || filter.enabled === false) continue
    const type = String(filter.type || '').trim()
    if (type === 'sources') rows = applySourcesFilter(rows, filter)
    else if (type === 'everything') rows = applyEverythingFilter(rows, filter)
    else if (type === 'label') rows = applyLabelFilter(rows, filter)
    else if (type === 'exclude-label') rows = applyExcludeLabelFilter(rows, filter)
    else if (type === 'path-tracing') rows = applyPathTracingFilter(rows, filter)
    else if (type === 'tags') rows = applyTagsFilter(rows, filter)
    else if (type === 'exclude-tags') rows = applyExcludeTagsFilter(rows, filter)
    else if (type === 'source-groups') rows = applySourceGroupsFilter(rows, filter)
    else if (type === 'link-frequency') rows = applyLinkFrequencyFilter(rows, filter)
    else if (type === 'factor-frequency') rows = applyFactorFrequencyFilter(rows, filter)
    else if (type === 'custom-links-label') rows = applyLabelByGroupToFactors(rows, filter)
    else if (type === 'map-custom-columns') {
      // Reserved map columns are attached after ordered row filters have run.
    }
    else if (type === 'exclude-self-loops') rows = applyExcludeSelfLoops(rows)
    else if (type === 'zoom') rows = applyZoomFilter(rows, filter)
    else if (type === 'collapse') rows = applyCollapseFilter(rows, filter).rows
    else if (type === 'replace-brackets') rows = applyReplaceBracketsFilter(rows, filter)
    else if (type === 'combine-opposites') rows = applyCombineOppositesFilter(rows, filter)
    else unsupported.push(type || '(missing type)')
  }

  rows = attachReservedCmLinkFields(rows, list.filter((filter) => filter && typeof filter === 'object'))
  return { rows, unsupported }
}
