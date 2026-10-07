// Path tracing: keep the links lying on a directed path from a "from" factor to a "to" factor
// within maxSteps. Pure (no window / DataService / DOM). The whole idea, including source tracing:
//
//   - from only:  keep everything reachable FORWARD from the "from" factors within maxSteps.
//   - to only:    keep everything that can reach the "to" factors within maxSteps (backward).
//   - from + to:  keep edges u->v where dist(from..u) + 1 + dist(v..to) <= maxSteps.
//   - onlyIndirect: drop the direct 1-step from->to links.
//   - traceThreads: the whole chain must stay inside one source; run the core per source and union.
//
// Replaces the old findPathFactors/findPathFactorsWithThreads/findPathEdges/bfs* cluster.
import { getLinkSourceIdsForTracing } from '../link-traversal.js'

function checkTextMatch(text, term, mode) {
  const t = String(text ?? '').toLowerCase()
  const s = String(term ?? '').toLowerCase()
  if (!s) return false
  if (mode === 'anywhere') return t.includes(s)
  if (mode === 'exact') return t === s
  return t.startsWith(s) // 'start' and the webapp default
}

const asLabels = (v) => (Array.isArray(v) ? v : v ? [v] : [])
const hasText = (labels) => labels.some((l) => l && typeof l === 'string' && l.trim())
const cause = (l) => String(l?.cause ?? '').trim()
const effect = (l) => String(l?.effect ?? '').trim()

// Min steps from any seed following adjacency `adj` (Map factor -> Set(next)), capped at maxSteps.
function bfsDist(adj, seeds, maxSteps) {
  const dist = new Map()
  let frontier = []
  for (const s of seeds) if (!dist.has(s)) { dist.set(s, 0); frontier.push(s) }
  for (let d = 0; d < maxSteps && frontier.length; d++) {
    const next = []
    for (const node of frontier) {
      for (const nb of adj.get(node) || []) {
        if (!dist.has(nb)) { dist.set(nb, d + 1); next.push(nb) }
      }
    }
    frontier = next
  }
  return dist
}

// Allowed "cause|||effect" edge keys over a given edge list (one source's edges, or all edges).
function allowedEdgeKeys(links, fromFactors, toFactors, maxSteps, onlyIndirect) {
  const forward = new Map()
  const backward = new Map()
  for (const l of links) {
    const c = cause(l), e = effect(l)
    if (!c || !e) continue
    if (!forward.has(c)) forward.set(c, new Set())
    forward.get(c).add(e)
    if (!backward.has(e)) backward.set(e, new Set())
    backward.get(e).add(c)
  }
  const hasFrom = fromFactors.size > 0
  const hasTo = toFactors.size > 0
  const keep = new Set()

  if (hasFrom && hasTo) {
    // Bounded simple-path search: from each "from" factor, walk forward without revisiting a factor
    // (no cycles within a path), and whenever a "to" factor is reached record every edge on that
    // path. Matches the current behaviour on feedback loops and self-loops (walks that revisit a
    // factor are not counted as paths).
    const onPath = new Set()
    const walk = (node, depth, pathEdges) => {
      if (toFactors.has(node) && pathEdges.length > 0) {
        if (!(onlyIndirect && pathEdges.length === 1)) for (const ek of pathEdges) keep.add(ek)
      }
      if (depth >= maxSteps) return
      for (const nb of forward.get(node) || []) {
        if (onPath.has(nb)) continue
        onPath.add(nb)
        pathEdges.push(`${node}|||${nb}`)
        walk(nb, depth + 1, pathEdges)
        pathEdges.pop()
        onPath.delete(nb)
      }
    }
    for (const f of fromFactors) {
      onPath.clear()
      onPath.add(f)
      walk(f, 0, [])
    }
  } else if (hasFrom) {
    const distFrom = bfsDist(forward, fromFactors, maxSteps)
    for (const l of links) {
      const c = cause(l), e = effect(l)
      if (c && e && distFrom.get(c) !== undefined && distFrom.get(c) < maxSteps) keep.add(`${c}|||${e}`)
    }
  } else if (hasTo) {
    const distTo = bfsDist(backward, toFactors, maxSteps)
    for (const l of links) {
      const c = cause(l), e = effect(l)
      if (c && e && distTo.get(e) !== undefined && distTo.get(e) < maxSteps) keep.add(`${c}|||${e}`)
    }
  }
  return keep
}

// Match the filter's from/to labels against the links to get the from/to factor sets.
// Exposed so the webapp can reuse the exact same matching for its highlight outputs.
export function matchPathFactors(links, filter) {
  const fromLabels = asLabels(filter.fromLabels)
  const toLabels = asLabels(filter.toLabels)
  const hasFromLabels = hasText(fromLabels)
  const hasToLabels = hasText(toLabels)
  const mode = filter.matchMode
  const fromFactors = new Set()
  const toFactors = new Set()
  for (const l of links) {
    const c = l?.cause || ''
    const e = l?.effect || ''
    for (const label of fromLabels) {
      if (!label || typeof label !== 'string' || !label.trim()) continue
      if (checkTextMatch(c, label, mode)) fromFactors.add(c)
      if (checkTextMatch(e, label, mode)) fromFactors.add(e)
    }
    for (const label of toLabels) {
      if (!label || typeof label !== 'string' || !label.trim()) continue
      if (checkTextMatch(c, label, mode)) toFactors.add(c)
      if (checkTextMatch(e, label, mode)) toFactors.add(e)
    }
  }
  return { fromFactors, toFactors, hasFromLabels, hasToLabels }
}

export function applyPathTracingFilter(links, filter, getSourceIds = getLinkSourceIdsForTracing) {
  if (!filter) return links
  const { fromFactors, toFactors, hasFromLabels, hasToLabels } = matchPathFactors(links, filter)
  if (!hasFromLabels && !hasToLabels) return links // inactive
  // Labels given but nothing matched: no paths from/to nothing.
  if (hasFromLabels && fromFactors.size === 0) return []
  if (hasToLabels && toFactors.size === 0) return []

  return tracePaths(links, fromFactors, toFactors, {
    maxSteps: filter.maxSteps,
    onlyIndirect: filter.onlyIndirect,
    traceThreads: filter.traceThreads,
    getSourceIds,
  })
}

/**
 * Core path tracing over already-matched factor sets. Pure. The webapp passes its own matched
 * fromFactors/toFactors (so it keeps its own highlight outputs) and uses this for the link result.
 * @param {object} opts  maxSteps, onlyIndirect, traceThreads, getSourceIds
 */
export function tracePaths(links, fromFactors, toFactors, opts = {}) {
  const maxStepsRaw = Number(opts.maxSteps)
  const steps = Number.isFinite(maxStepsRaw) && maxStepsRaw > 0 ? maxStepsRaw : 3
  const onlyIndirect = opts.onlyIndirect === true
  const getSourceIds = opts.getSourceIds || getLinkSourceIdsForTracing

  if (opts.traceThreads) {
    // Same-source only: run the core on each source's sub-graph; keep a link if any of its
    // source ids yields an allowed edge in that source's sub-graph.
    const linksBySource = new Map()
    for (const l of links) {
      for (const sid of getSourceIds(l)) {
        if (!linksBySource.has(sid)) linksBySource.set(sid, [])
        linksBySource.get(sid).push(l)
      }
    }
    const allowedBySource = new Map()
    for (const [sid, sourceLinks] of linksBySource) {
      allowedBySource.set(sid, allowedEdgeKeys(sourceLinks, fromFactors, toFactors, steps, onlyIndirect))
    }
    return links.filter((l) => {
      const key = `${cause(l)}|||${effect(l)}`
      return getSourceIds(l).some((sid) => allowedBySource.get(sid)?.has(key))
    })
  }

  const allowed = allowedEdgeKeys(links, fromFactors, toFactors, steps, onlyIndirect)
  return links.filter((l) => allowed.has(`${cause(l)}|||${effect(l)}`))
}
