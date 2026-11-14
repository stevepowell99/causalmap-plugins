// Pathways: an exploratory filter that finds typical causal stories. Unlike path/source tracing it has
// no predefined endpoints. It works bottom-up from the source text:
//
//   1. Within each source S, find passages: a passage is a set of links, one for each step of a chain
//      f0 -> f1 -> ... -> fN (N links), whose quotes all fall inside a window no longer than `proximity`
//      characters (max text_end_offset - min text_start_offset <= proximity). This grounds each pathway
//      in a piece of more or less contiguous narrative, so "A->B at the start of a book and B->C at the
//      end" never counts as one story.
//   2. Optionally (`successive`) require the quotes to appear in chain order (non-decreasing start
//      offsets along f0->...->fN), i.e. the source tells the steps in the right order.
//   3. List every qualifying chain for every source, then rank the distinct chains by how many sources
//      tell them (sourceCount, most frequent first), breaking ties by the total number of separate
//      passages that tell them across all sources (passageCount). The tie-breaker is what gives a useful
//      ranking on single-source projects, where every chain has sourceCount 1: the chain narrated most
//      often in that one source wins. `rank` (1-based) picks one chain; the filter keeps every link
//      instance taking part in any of that chain's passages, so the kept map shows the chain's full
//      citation weight. The `tightestOnly` option reverts to the original behaviour: count and keep only
//      the single tightest passage per source. Sister links inside the same bundles are irrelevant and
//      dropped.
//
// Pure (no window / DataService / DOM). Heuristic by design: the point is to surface typical pathways,
// not to answer a high-stakes evaluation question. Links without quote offsets cannot be placed in a
// passage and so do not participate.

import { quoteOffsetSpan } from '../link-traversal.js'

const cause = (l) => String(l?.cause ?? '').trim()
const effect = (l) => String(l?.effect ?? '').trim()
const edgeKey = (c, e) => `${c}|||${e}`

// Guards so a dense source cannot explode the per-source DFS.
const MAX_CHAINS_PER_SOURCE = 5000

function clampInt(v, def, min) {
  const n = parseInt(v, 10)
  return Number.isFinite(n) && n >= min ? n : def
}

// Does the chain's N edge-types have a passage within `proximity`? If so return the tightest set of link
// instances (one per step); else null. `instancesByType[i]` = link instances of step i's edge in this source.
// When `successive`, the picked instances must have non-decreasing start offsets in step order.
function findPassage(instancesByType, proximity, successive) {
  const N = instancesByType.length
  // Anchor on each instance's start as the window's left edge; a valid window is [lo, lo+proximity].
  const anchors = []
  for (const list of instancesByType) for (const inst of list) anchors.push(inst.start)
  anchors.sort((a, b) => a - b)

  let best = null // { instances:[...], span }
  let lastLo = null
  for (const lo of anchors) {
    if (lo === lastLo) continue // identical left edge gives nothing new
    lastLo = lo
    const hi = lo + proximity
    const picked = new Array(N)
    let ok = true

    if (successive) {
      let cursor = lo
      for (let i = 0; i < N; i++) {
        // earliest-starting instance of this step at/after the previous step, ending within the window
        let choice = null
        for (const inst of instancesByType[i]) {
          if (inst.start >= cursor && inst.end <= hi && (!choice || inst.start < choice.start)) choice = inst
        }
        if (!choice) { ok = false; break }
        picked[i] = choice
        cursor = choice.start
      }
    } else {
      for (let i = 0; i < N; i++) {
        // earliest-ending instance of this step inside the window (minimises the window's right reach)
        let choice = null
        for (const inst of instancesByType[i]) {
          if (inst.start >= lo && inst.end <= hi && (!choice || inst.end < choice.end)) choice = inst
        }
        if (!choice) { ok = false; break }
        picked[i] = choice
      }
    }
    if (!ok) continue

    let minStart = Infinity, maxEnd = -Infinity
    for (const inst of picked) { if (inst.start < minStart) minStart = inst.start; if (inst.end > maxEnd) maxEnd = inst.end }
    const span = maxEnd - minStart
    if (span <= proximity && (!best || span < best.span)) best = { instances: picked.slice(), span }
  }
  return best
}

// All non-overlapping passages of a chain in one source: repeatedly take the tightest passage, consume
// the link instances it used, then look again, until none remain. Each link instance is counted at most
// once, so the count is how many separate times the source narrates the chain (and so, for a single edge,
// just its citation count). Returns the set of all participating link ids and that passage count.
// `tightestOnly` reverts to the original behaviour: just the single tightest passage (count 1).
function findAllPassages(instancesByType, proximity, successive, tightestOnly) {
  const pools = instancesByType.map((list) => list.slice())
  const ids = new Set()
  let count = 0
  for (;;) {
    const passage = findPassage(pools, proximity, successive)
    if (!passage) break
    count++
    const used = new Set(passage.instances)
    used.forEach((inst) => ids.add(inst.id))
    if (tightestOnly) break
    for (let i = 0; i < pools.length; i++) pools[i] = pools[i].filter((inst) => !used.has(inst))
  }
  return { ids, count }
}

// Enumerate every distinct length-N chain that has a qualifying passage in one source.
// Returns Map(pathwayKey -> { ids:Set(linkId), count }): every link taking part in the chain's
// non-overlapping passages in this source, and how many such passages there are.
function enumerateSourcePathways(sourceLinks, N, proximity, successive, tightestOnly) {
  // Index this source's edges and their placeable link instances.
  const forward = new Map()
  const instancesByEdge = new Map()
  for (const l of sourceLinks) {
    const c = cause(l), e = effect(l)
    if (!c || !e) continue
    const span = quoteOffsetSpan(l)
    if (!span) continue
    if (!forward.has(c)) forward.set(c, new Set())
    forward.get(c).add(e)
    const k = edgeKey(c, e)
    if (!instancesByEdge.has(k)) instancesByEdge.set(k, [])
    instancesByEdge.get(k).push({ id: l.id, start: span.start, end: span.end })
  }

  const found = new Map()
  const onPath = new Set()
  const usedSelfLoops = new Set()
  const seq = []        // factor sequence
  const edgeKeys = []   // edge key per step
  let chains = 0

  const visit = (node, depth) => {
    if (chains >= MAX_CHAINS_PER_SOURCE) return
    if (depth === N) {
      chains++
      const key = seq.join('|||')
      if (!found.has(key)) {
        const passages = findAllPassages(edgeKeys.map(k => instancesByEdge.get(k) || []), proximity, successive, tightestOnly)
        if (passages.count > 0) found.set(key, passages)
      }
      return
    }
    for (const nb of forward.get(node) || []) {
      if (nb === node) {
        const ek = edgeKey(node, node)
        if (usedSelfLoops.has(ek)) continue
        usedSelfLoops.add(ek); seq.push(nb); edgeKeys.push(ek)
        visit(node, depth + 1)
        edgeKeys.pop(); seq.pop(); usedSelfLoops.delete(ek)
      } else if (!onPath.has(nb)) {
        onPath.add(nb); seq.push(nb); edgeKeys.push(edgeKey(node, nb))
        visit(nb, depth + 1)
        edgeKeys.pop(); seq.pop(); onPath.delete(nb)
      }
    }
  }

  for (const start of forward.keys()) {
    onPath.clear(); onPath.add(start)
    usedSelfLoops.clear()
    seq.length = 0; seq.push(start)
    edgeKeys.length = 0
    visit(start, 0)
    if (chains >= MAX_CHAINS_PER_SOURCE) break
  }
  return found
}

// Core: rank chains by source frequency and gather the links forming each chain's passages.
// Returns { ranked:[{key, factors, sourceCount, passageCount}], linksByPathway: Map(key -> Set(linkId)) }.
function computePathways(links, filter) {
  const N = clampInt(filter.pathLength, 2, 1)
  const proximity = clampInt(filter.proximity, 500, 1)
  const successive = filter.successive === true
  const tightestOnly = filter.tightestOnly === true

  // Group placeable links by their source.
  const bySource = new Map()
  for (const l of links) {
    const sid = String(l?.source_id ?? '').trim()
    if (!sid) continue
    if (!bySource.has(sid)) bySource.set(sid, [])
    bySource.get(sid).push(l)
  }

  const agg = new Map() // key -> { sources:Set, passageCount, links:Set(linkId) }
  for (const [sid, sourceLinks] of bySource) {
    const found = enumerateSourcePathways(sourceLinks, N, proximity, successive, tightestOnly)
    for (const [key, { ids, count }] of found) {
      let a = agg.get(key)
      if (!a) { a = { sources: new Set(), passageCount: 0, links: new Set() }; agg.set(key, a) }
      a.sources.add(sid)
      a.passageCount += count
      ids.forEach(id => a.links.add(id))
    }
  }

  const ranked = []
  const linksByPathway = new Map()
  for (const [key, a] of agg) {
    ranked.push({ key, factors: key.split('|||'), sourceCount: a.sources.size, passageCount: a.passageCount })
    linksByPathway.set(key, a.links)
  }
  ranked.sort((x, y) =>
    y.sourceCount - x.sourceCount ||
    y.passageCount - x.passageCount ||
    (x.key < y.key ? -1 : x.key > y.key ? 1 : 0)
  )
  return { ranked, linksByPathway }
}

// Ranked chains only (host can read the total / inspect the ranking).
export function rankPathways(links, filter) {
  return computePathways(links, filter).ranked
}

export function applyPathwaysFilter(links, filter) {
  if (!filter) return links
  const { ranked, linksByPathway } = computePathways(links, filter)
  if (ranked.length === 0) return []
  const rank = Math.max(1, parseInt(filter.rank, 10) || 1)
  const chosen = ranked[rank - 1]
  if (!chosen) return [] // rank past the last pathway
  const keepIds = linksByPathway.get(chosen.key) || new Set()
  return links.filter(l => keepIds.has(l.id))
}
