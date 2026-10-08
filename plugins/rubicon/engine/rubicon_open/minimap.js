/**
 * The margin map: the workflow drawn small, beside the document it describes.
 *
 * A workflow reads as one scrolling document now, and a long one runs to several screens,
 * so the shape of it goes off the top as soon as somebody starts reading. The map keeps
 * the shape on the screen the whole way down, and says where in it the reader is.
 *
 * It is one viewport tall and its rows are spaced by graph depth, not aligned to the
 * content. That is the decision worth writing down. A coding step's quote table is a
 * hundred times taller than a sample step's one line, so a content-aligned map would draw
 * how much text each step produced rather than the workflow.
 *
 * Split in two on purpose. `layout` is pure and takes `graph.elementsFor`'s output, so the
 * ranks, lanes and positions are testable under node with no DOM and no canvas. `draw`
 * paints what `layout` worked out and knows nothing about workflows.
 *
 * The map reads the SAME elements the diagram draws, and the same colours, because a
 * second node list is how the status chip and the diagram came to be two different greens.
 */

import { stateWord, nameInWords } from './words.js?v=2026-10-07T08:36:34Z'

/**
 * How hard the map leans on the kind axis: a step sits this far left of centre and an
 * asset this far right of it, as a fraction of the usable width. 0.32 keeps a 14px step
 * box and a ringed asset inside the 132px gutter the map is drawn in.
 */
const KIND_LEAN = 0.32

/** How far below its step a paired result sits, as a fraction of the ordinary rank gap. */
export const PAIR_GAP = 0.5

/** Down-and-up barycentre rounds to try before taking the best ordering any of them found. */
const ROUNDS = 6

/**
 * What the map's marks mean, said once.
 *
 * Fill says the role and nothing else: an instruction (a step) is pale green with a darker
 * green edge, a result is deep green. Shape says what kind of result it is. How a step went
 * is said by its outline, never by its fill. Steve, 17 September 2026, of a map whose steps
 * were filled by status and whose results were all one yellow bead: "the yellow/green/
 * ?brownygrey? colourcoding for results/instructions in each step is not intuitive", and
 * "quotes/source set/table have same formatting?". The brown-grey was a step reused from an
 * earlier run, filled in the status colour for that; the green was a step that ran.
 *
 * Only the kinds worth telling apart at nine pixels are named. Everything else is a disc,
 * and the key is built from the types actually on the map, so a type nobody named still
 * appears in it rather than being silently dropped.
 */
const ASSET_MARKS = {
    judgement: 'diamond',
    note: 'page',
    quotes: 'bubble',
    source_set: 'sheets',
    table: 'grid',
    theory_of_change: 'hexagon',
}

export function markFor(type) { return ASSET_MARKS[type] || 'disc' }

/**
 * How a step's outline says how it went. Fill is never used for this.
 *
 * `edge` names a key of the colours `draw` is given. `dash` is an earlier run's line: a step
 * reused from one, or a step nothing has run yet, which is also drawn hollow. `word` is what
 * the key calls the state, or null where the plain outline needs no entry of its own.
 */
export function stepLook(status) {
    switch (status) {
        case 'succeeded': return { edge: 'instructionEdge', width: 1, dash: [], hollow: false, word: null }
        case 'running': return { edge: 'instructionEdge', width: 1, dash: [], hollow: false, word: 'running' }
        case 'failed': return { edge: 'red', width: 2, dash: [], hollow: false, word: 'failed' }
        case 'waiting': return { edge: 'waiting', width: 1.8, dash: [], hollow: false, word: 'waiting' }
        case 'stale': return { edge: 'stale', width: 1.8, dash: [], hollow: false, word: stateWord('stale') }
        case 'skipped': return { edge: 'instructionEdge', width: 1.2, dash: [2, 1.5], hollow: false,
                                 word: `${stateWord('skipped')} from an earlier run` }
        default: return { edge: 'instructionEdge', width: 1.2, dash: [2, 1.5], hollow: true, word: 'not run yet' }
    }
}

/** A closed polygon through the points, as one path. */
function polygon(ctx, points) {
    for (const [i, [px, py]] of points.entries()) ctx[i ? 'lineTo' : 'moveTo'](px, py)
    ctx.closePath()
}

/** Short strokes drawn over a mark, in one colour: a table's rules, a note's lines. */
function rules(ctx, segments, style, width) {
    ctx.strokeStyle = style
    ctx.lineWidth = width
    for (const [x1, y1, x2, y2] of segments) {
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
    }
}

/**
 * One result's mark, centred on x, y, about 2r across, filled, outlined and detailed.
 *
 * `look` carries the colours: `fill`, `edge`, `detail` (the pale strokes inside a mark),
 * `dash` for the outline, and `back` for the rear sheet of a source set. No part of a mark
 * is a three-point fill, because that is how the tests tell an arrowhead from anything else.
 */
export function paintMark(ctx, mark, x, y, r, look) {
    const outline = () => {
        ctx.fillStyle = look.fill
        ctx.fill()
        ctx.strokeStyle = look.edge
        ctx.lineWidth = 1
        ctx.setLineDash(look.dash || [])
        ctx.stroke()
        ctx.setLineDash([])
    }
    const thin = Math.max(0.7, r / 5)
    ctx.beginPath()
    if (mark === 'page') {
        // A page with its top right corner folded.
        const w = r * 0.8
        const h = r
        const f = r * 0.55
        polygon(ctx, [[x - w, y - h], [x + w - f, y - h], [x + w, y - h + f], [x + w, y + h], [x - w, y + h]])
        outline()
        rules(ctx, [[x + w - f, y - h, x + w - f, y - h + f], [x + w - f, y - h + f, x + w, y - h + f]],
            look.edge, 0.8)
        if (!look.hollow) {
            rules(ctx, [[x - w * 0.5, y + h * 0.05, x + w * 0.5, y + h * 0.05],
                        [x - w * 0.5, y + h * 0.5, x + w * 0.5, y + h * 0.5]], look.detail, thin)
        }
    } else if (mark === 'grid') {
        // A small table: a box ruled into a header row and two columns.
        const s = r * 0.95
        polygon(ctx, [[x - s, y - s], [x + s, y - s], [x + s, y + s], [x - s, y + s]])
        outline()
        if (!look.hollow) {
            rules(ctx, [[x - s, y - s * 0.3, x + s, y - s * 0.3], [x - s, y + s * 0.35, x + s, y + s * 0.35],
                        [x, y - s * 0.3, x, y + s]], look.detail, thin)
        }
    } else if (mark === 'bubble') {
        // A speech bubble, its tail at the lower left, with the two ticks of a quotation.
        const R = r * 0.9
        const cy = y - r * 0.12
        const toward = Math.PI * 0.75
        ctx.arc(x, cy, R, toward + 0.4, toward - 0.4 + Math.PI * 2)
        ctx.lineTo(x + Math.cos(toward) * R * 1.55, cy + Math.sin(toward) * R * 1.55)
        ctx.closePath()
        outline()
        if (!look.hollow) {
            rules(ctx, [[x - R * 0.32, cy - R * 0.35, x - R * 0.42, cy + R * 0.1],
                        [x + R * 0.32, cy - R * 0.35, x + R * 0.22, cy + R * 0.1]], look.detail, thin * 1.2)
        }
    } else if (mark === 'sheets') {
        // A set of documents: one sheet behind another.
        const w = r * 0.7
        const h = r * 0.85
        const o = r * 0.35
        polygon(ctx, [[x - w + o, y - h - o], [x + w + o, y - h - o], [x + w + o, y + h - o], [x - w + o, y + h - o]])
        const front = look.fill
        ctx.fillStyle = look.back || look.fill
        ctx.fill()
        ctx.strokeStyle = look.edge
        ctx.lineWidth = 1
        ctx.setLineDash(look.dash || [])
        ctx.stroke()
        ctx.beginPath()
        polygon(ctx, [[x - w - o, y - h + o], [x + w - o, y - h + o], [x + w - o, y + h + o], [x - w - o, y + h + o]])
        ctx.fillStyle = front
        outline()
    } else if (mark === 'disc') {
        ctx.arc(x, y, r, 0, Math.PI * 2)
        outline()
    } else {
        const sides = mark === 'diamond' ? 4 : 6
        // A diamond stands on its point and a hexagon on a flat side, which is what keeps the
        // two apart at this size.
        const turn = mark === 'diamond' ? -Math.PI / 2 : Math.PI / 6
        const reach = mark === 'diamond' ? r * 1.25 : r * 1.1
        polygon(ctx, Array.from({ length: sides }, (_, i) => {
            const a = turn + (i * 2 * Math.PI) / sides
            return [x + reach * Math.cos(a), y + reach * Math.sin(a)]
        }))
        outline()
    }
    ctx.lineWidth = 1
}

/**
 * One node's mark, at full size times `size`. Shared by `draw` and the key's swatches, so
 * the key cannot come to show a mark the map does not draw.
 *
 * `n` needs only `kind`, and for a step `status`, for a result `type`, `missing` and
 * `upstream`.
 */
export function paintNode(ctx, n, x, y, size, colours) {
    if (n.kind === 'run') {
        // An earlier run: a hollow box with a dashed edge, a step's shape drawn larger and
        // left empty, since it stands for a whole workflow this run did not do.
        ctx.strokeStyle = colours.ink
        ctx.lineWidth = 1.2
        ctx.setLineDash([3, 2])
        box(ctx, x - 9 * size, y - 5 * size, 18 * size, 10 * size, ROUND * size)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.lineWidth = 1
        return
    }
    if (n.kind === 'step') {
        const look = stepLook(n.status)
        box(ctx, x - 7 * size, y - 4 * size, 14 * size, 8 * size, ROUND * size)
        ctx.fillStyle = look.hollow ? colours.paper : colours.instruction
        ctx.fill()
        ctx.strokeStyle = colours[look.edge] || colours.instructionEdge
        ctx.lineWidth = look.width
        ctx.setLineDash(look.dash)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.lineWidth = 1
        return
    }
    // A result nothing has made yet is its shape left empty, dashed; one taken from an
    // earlier run keeps its fill and takes the earlier run's dashed edge.
    paintMark(ctx, markFor(n.type), x, y, 4.5 * size, {
        fill: n.missing ? colours.paper : colours.result,
        back: colours.paper,
        edge: n.missing ? colours.result : colours.resultEdge,
        detail: colours.detail,
        dash: n.missing || n.upstream ? [2, 1.5] : [],
        hollow: !!n.missing,
    })
}

/** The two rings: what the workflow was for, and where the reader is. */
export function paintRing(ctx, x, y, radius, style) {
    ctx.strokeStyle = style
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.stroke()
    ctx.lineWidth = 1
}

/**
 * What the key lists, from what is on this map and nothing else.
 *
 * Each entry carries a pretend node for `paintNode`, or a ring, so a swatch is the mark the
 * map draws rather than a picture of it. Words are for somebody who has never seen the
 * code: "instruction" rather than "step", "result: table" rather than a type name.
 */
export function keyEntries(laidOut) {
    const nodes = laidOut?.nodes || []
    const entries = []
    const steps = nodes.filter(n => n.kind === 'step')
    if (steps.length) entries.push({ word: 'instruction', node: { kind: 'step', status: 'succeeded' } })
    const results = nodes.filter(n => n.kind === 'asset')
    for (const type of [...new Set(results.map(n => n.type || ''))].sort()) {
        entries.push({ word: `result: ${type ? nameInWords(type) : 'other'}`,
                       node: { kind: 'asset', type } })
    }
    if (results.some(n => n.missing)) {
        entries.push({ word: 'result not made yet', node: { kind: 'asset', type: '', missing: true } })
    }
    const said = new Set()
    for (const n of steps) {
        const look = stepLook(n.status)
        if (!look.word || said.has(look.word)) continue
        said.add(look.word)
        entries.push({ word: look.word, node: { kind: 'step', status: n.status }, halo: n.status === 'running' })
    }
    if (nodes.some(n => n.kind === 'run')) entries.push({ word: 'earlier run', node: { kind: 'run' } })
    if (nodes.some(n => n.terminal)) entries.push({ word: 'the answer', ring: 'red' })
    entries.push({ word: 'where you are reading', ring: 'ink' })
    return entries
}

/** One key entry, painted on a 16px swatch's context. */
export function paintKeyEntry(ctx, entry, colours) {
    if (entry.ring) {
        paintRing(ctx, 8, 8, 6.5, colours[entry.ring])
        return
    }
    if (entry.halo) {
        ctx.globalAlpha = 0.3
        ctx.fillStyle = colours.red
        ctx.beginPath()
        ctx.arc(8, 8, 7.5, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalAlpha = 1
    }
    paintNode(ctx, entry.node, 8, 8, entry.node.kind === 'run' ? 0.8 : 1, colours)
}

/**
 * Where every node sits: its rank down the map, its lane across it, and its x.
 *
 * Rank is longest-path depth from the roots, rather than shortest. Shortest path puts a
 * step beside the earliest thing that reaches it, so a judging step that reads both the
 * sample and a table three steps later would be drawn level with the sample and its edges
 * would run backwards up the map. Longest path puts everything below everything it reads.
 *
 * A cycle cannot happen in a declared workflow, since the runner refuses one, but a
 * workflow rewritten between runs can leave an asset whose producer is gone. Anything the
 * ordering cannot place goes in a rank of its own at the bottom, rather than being dropped:
 * a node missing from the map is a block the reader cannot reach.
 *
 * `x` is a fraction of the usable width, 0 at the left and 1 at the right, so this decides
 * the shape and the drawing decides the pixels. Two rules make it, and the second is the
 * one worth arguing about.
 *
 * A rank holding MORE THAN ONE thing spreads evenly across the whole width, in an order
 * chosen to cross as little as possible: the standard layered sweep, ordering each rank by
 * the barycentre of its neighbours above, then of its neighbours below, and keeping
 * whichever ordering crossed least. `crossings` counts them, so "it fell" is checkable
 * rather than asserted.
 *
 * A rank holding ONE thing is placed by its kind: a step left of centre, an asset right of
 * it. That is the rule Steve's complaint turns on. Measured over the 40 newest runs in the
 * ledger, 20 of the 23 that draw anything put exactly one node in every rank, so the
 * commonest workflow by far is step, asset, step, asset straight down, and centring each
 * of those drew the vertical line he saw: "spread out the nodes and their curves to use
 * maximum width with fewest crossovers" (5 September 2026). The obvious alternative,
 * placing a lone node at the barycentre of its neighbours, does nothing whatever to those
 * 20: a chain of single nodes has no fan anywhere to take a position from, so every
 * barycentre resolves to the middle and the line stays a line. Kind was taken over lineage
 * because it also gives the horizontal axis a meaning a reader can name. Left is what
 * somebody asked for and right is what came back, so the zigzag is the alternation of
 * instruction and result rather than decoration.
 *
 * "Thing" rather than "node" above because an edge that skips a rank takes a seat in every
 * rank it passes, and is drawn through those seats. That is what stops it cutting across
 * the zigzag: 14 of those 23 runs have such an edge, and left to run straight from end to
 * end they crossed the chain twice per workflow. Given a column of their own they cross
 * nothing. The waypoints come back on the edge as `via`, so `draw` follows the route the
 * count was taken over rather than guessing a curve of its own.
 */
export function layout(elements, { rounds = ROUNDS } = {}) {
    const all = elements || []
    const nodes = all.filter(e => e?.data?.kind).map(e => e.data)
    const edges = all
        .filter(e => e?.data?.source && e?.data?.target)
        .map(e => ({ from: e.data.source, to: e.data.target }))

    const known = new Set(nodes.map(n => n.id))
    const real = edges.filter(e => known.has(e.from) && known.has(e.to))

    const into = new Map(nodes.map(n => [n.id, []]))
    const outOf = new Map(nodes.map(n => [n.id, []]))
    for (const e of real) {
        into.get(e.to).push(e.from)
        outOf.get(e.from).push(e.to)
    }

    // Kahn's order, then longest path over it. Taking the nodes in topological order means
    // every parent's rank is final before its child is looked at, so one pass is enough.
    const left = new Map(nodes.map(n => [n.id, into.get(n.id).length]))
    const queue = nodes.filter(n => left.get(n.id) === 0).map(n => n.id)
    const rank = new Map(queue.map(id => [id, 0]))
    const order = []
    for (let i = 0; i < queue.length; i++) {
        const id = queue[i]
        order.push(id)
        for (const next of outOf.get(id)) {
            rank.set(next, Math.max(rank.get(next) ?? 0, (rank.get(id) ?? 0) + 1))
            left.set(next, left.get(next) - 1)
            if (left.get(next) === 0) queue.push(next)
        }
    }
    // Whatever the ordering could not place, which means a cycle or an edge into a node
    // nothing produces. Put at the bottom and kept, because losing one silently is worse.
    const stranded = nodes.filter(n => !order.includes(n.id))
    if (stranded.length) {
        const below = Math.max(-1, ...[...rank.values()]) + 1
        for (const n of stranded) rank.set(n.id, below)
    }

    const laid = nodes.map(n => ({
        id: n.id,
        kind: n.kind,
        // Carried so the drawing can mark a result by what kind of result it is. A step's
        // own type is not marked: its outline says how it went and its place in the chain
        // says what it did.
        type: n.kind === 'asset' ? (n.type || '') : null,
        // And which result it is, so pressing it can open the thing rather than scroll to
        // the step that made it.
        assetId: n.assetId || null,
        label: n.label || n.id,
        status: n.kind === 'step' ? (n.status || 'not run') : null,
        missing: !!n.missing,
        // An earlier run, or a result that belongs to one, which the map draws apart from
        // this run's own work: `graph.upstreamElements`.
        upstream: n.kind === 'run' || !!n.upstream,
        terminal: !!n.answer,
        rank: rank.get(n.id) ?? 0,
        lane: 0,
        x: 0.5,
    }))
    const by = new Map(laid.map(n => [n.id, n]))

    // Every node takes a seat in its rank, and so does every rank an edge merely passes
    // over. A long edge given no seat is drawn from end to end across whatever the ranks
    // in between are doing; given one, it runs down a column nothing else is using and the
    // ranks it passes are pushed aside to make room, which is where its room comes from.
    const seat = new Map()
    for (const n of laid) seat.set(n.id, { rank: n.rank, x: 0.5, kind: n.kind, node: n })
    const above = new Map()
    const below = new Map()
    const join = (top, bottom) => {
        if (!below.has(top)) below.set(top, [])
        if (!above.has(bottom)) above.set(bottom, [])
        below.get(top).push(bottom)
        above.get(bottom).push(top)
    }
    const routed = real.map((e, i) => {
        const a = by.get(e.from)
        const b = by.get(e.to)
        const top = a.rank <= b.rank ? a : b
        const end = a.rank <= b.rank ? b : a
        const via = []
        for (let r = top.rank + 1; r < end.rank; r++) {
            const id = `via:${i}:${r}`
            seat.set(id, { rank: r, x: 0.5, kind: 'via', node: null })
            via.push(id)
        }
        const path = [top.id, ...via, end.id]
        for (let k = 0; k < path.length - 1; k++) join(path[k], path[k + 1])
        // Handed back in the edge's own direction, so `draw` walks it from `from` to `to`.
        return { ...e, seats: a.rank <= b.rank ? via : [...via].reverse() }
    })

    // Each rank, nodes first in the order the elements were declared, which is the order
    // the document draws its blocks in, then the passing edges. That is the order every
    // sweep below starts from and falls back to.
    const rows = []
    const sit = id => {
        const r = seat.get(id).rank
        while (rows.length <= r) rows.push([])
        rows[r].push(id)
    }
    for (const n of laid) sit(n.id)
    for (const [id, s] of seat) if (s.kind === 'via') sit(id)

    const place = () => {
        for (const row of rows) {
            for (const [i, id] of row.entries()) {
                const s = seat.get(id)
                s.x = row.length > 1
                    ? (i + 0.5) / row.length
                    : s.kind === 'step' ? 0.5 - KIND_LEAN
                    : s.kind === 'asset' ? 0.5 + KIND_LEAN
                    : 0.5
                if (s.node) {
                    s.node.x = s.x
                    s.node.lane = i
                }
            }
        }
    }
    const shape = () => ({
        nodes: laid,
        edges: routed.map(e => ({
            from: e.from,
            to: e.to,
            via: e.seats.map(id => ({ rank: seat.get(id).rank, x: seat.get(id).x })),
        })),
    })
    place()

    if (rows.length > 1 && rounds > 0) {
        // Ordering a rank by the mean position of what it reads, then by the mean position
        // of what reads it, is the usual way to take crossings out of a layered drawing. A
        // seat with nothing on the side being swept keeps where it is, and the sort is
        // stable, so declared order survives every tie and a fan-out stays in its own
        // order rather than being shuffled for no gain.
        const meanOf = (id, side) => {
            const near = (side === 'up' ? above.get(id) : below.get(id)) || []
            const xs = near.map(other => seat.get(other)?.x).filter(x => x != null)
            return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : seat.get(id).x
        }
        let best = rows.map(row => [...row])
        let fewest = crossings(shape())
        for (let round = 0; round < rounds; round++) {
            const was = fewest
            for (const side of ['up', 'down']) {
                const sweep = rows.map((_, r) => side === 'up' ? r : rows.length - 1 - r)
                for (const r of sweep) {
                    if (rows[r].length < 2) continue
                    const key = new Map(rows[r].map(id => [id, meanOf(id, side)]))
                    rows[r].sort((a, b) => key.get(a) - key.get(b))
                    place()
                }
                const now = crossings(shape())
                if (now < fewest) {
                    fewest = now
                    best = rows.map(row => [...row])
                }
            }
            if (fewest >= was) break     // a whole round bought nothing, so stop asking
        }
        for (const [r, row] of best.entries()) rows[r] = row
        place()
    }

    // A result that is the one thing its step made hangs tight under that step, so the pair
    // reads as one unit: nearly every result is the work of a single instruction, and the
    // instruction and the thing it produced are one idea.
    //
    // Whether that happens is the pair's own business, and one condition decides it: the
    // step made nothing else. What reads the result afterwards has nothing to do with it,
    // and neither has anything else sharing the rank. The first version asked all three,
    // and a rank-wide gap is what forced the other two: gaps belong to rows, so a row could
    // only move as a whole and any one member that did not qualify held the rest at the full
    // gap. On a real MECC run that fired exactly once, because most results feed more than
    // one later step and most rows also hold an earlier run's box or a seat reserved for an
    // edge passing through. Steve, 17 September 2026: "instruction/result closeness only
    // succeeded once here."
    //
    // So position is a node's own, in gaps below the top of the map, and a rank keeps only
    // the y that everything unpaired in it sits at. Three things follow, and the last two
    // are what stops a tightened pair landing on anything.
    //
    //   - A tightened result sits PAIR_GAP below its step, wherever its neighbours are.
    //   - Everything else in that rank, an earlier run's box or a passing edge's seat
    //     included, stays on the rank's own y, a full gap below the rank above. So a
    //     tightened result is always strictly above them and cannot collide with one.
    //   - The rank below starts a full gap under the LOWEST thing actually drawn in this
    //     one. Where the whole row moved up that is the tightened result, so a row of pairs
    //     still shortens the map; where anything stayed put it is the rank's own y, so the
    //     row below clears the thing that stayed.
    for (const n of laid) {
        const from = into.get(n.id)
        const maker = from.length === 1 ? by.get(from[0]) : null
        n.paired = n.kind === 'asset' && !!maker && maker.kind === 'step'
            && maker.rank === n.rank - 1 && outOf.get(maker.id).length === 1
    }
    const ranks = Math.max(1, ...laid.map(n => n.rank + 1))
    // `base[r]` is rank r's own y, in gaps. A step is never paired, so a paired result's
    // maker is always on its rank's own y and `base[r - 1]` is where it sits.
    const base = [0]
    for (let r = 0; r < ranks; r++) {
        const inRank = laid.filter(n => n.rank === r)
        for (const n of inRank) n.y = n.paired ? base[r - 1] + PAIR_GAP : base[r]
        const seats = (rows[r] || []).some(id => seat.get(id)?.kind === 'via')
        const held = seats || !inRank.length || inRank.some(n => !n.paired)
        base.push(Math.max(...inRank.map(n => n.y), ...(held ? [base[r]] : [])) + 1)
    }
    // The lowest thing drawn, which becomes the bottom of the map: y is handed out as a
    // fraction of it, so the drawing multiplies by a height and knows nothing about gaps.
    const deep = base[ranks] - 1
    const share = y => (deep > 0 ? y / deep : 0)
    for (const n of laid) n.y = share(n.y)

    return {
        ...shape(),
        ranks,
        // Where a rank's own y falls, which is what a seat reserved for a passing edge is
        // drawn at. A node carries its own `y` and does not read this.
        levels: base.slice(0, ranks).map(share),
        widest: Math.max(1, ...rows.map(row => row.length)),
    }
}

/** Which side of the line ab the point c falls: -1, 0 or 1. */
function whichSide(ax, ay, bx, by, cx, cy) {
    return Math.sign((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
}

/**
 * How many pairs of edges cross, over the positions `layout` gave the nodes.
 *
 * The measure the sweep is trying to lower, and the only reason it can be said to have
 * worked. Counted over the route each edge is actually drawn along, waypoints included,
 * with rank standing in for y: it measures the picture rather than an abstraction of it.
 *
 * Two edges meeting at a node do not cross, and neither do two lying along each other. So
 * a workflow drawn as one straight column scores zero, which is true and is exactly why
 * the count on its own was never the thing to work against: an unreadable line is the
 * cheapest drawing there is, and the width the nodes use is the other half of the job.
 */
export function crossings(laidOut) {
    const by = new Map(laidOut.nodes.map(n => [n.id, n]))
    const segs = []
    for (const [i, e] of laidOut.edges.entries()) {
        const a = by.get(e.from)
        const b = by.get(e.to)
        if (!a || !b) continue
        const points = [
            { id: e.from, x: a.x, y: a.rank },
            ...(e.via || []).map((v, k) => ({ id: `via:${i}:${k}`, x: v.x, y: v.rank })),
            { id: e.to, x: b.x, y: b.rank },
        ]
        for (let k = 0; k < points.length - 1; k++) {
            if (points[k].y !== points[k + 1].y) segs.push([points[k], points[k + 1]])
        }
    }
    let count = 0
    for (let i = 0; i < segs.length; i++) {
        for (let j = i + 1; j < segs.length; j++) {
            const [p1, p2] = segs[i]
            const [q1, q2] = segs[j]
            if (p1.id === q1.id || p1.id === q2.id || p2.id === q1.id || p2.id === q2.id) continue
            const a = whichSide(p1.x, p1.y, p2.x, p2.y, q1.x, q1.y)
            const b = whichSide(p1.x, p1.y, p2.x, p2.y, q2.x, q2.y)
            const c = whichSide(q1.x, q1.y, q2.x, q2.y, p1.x, p1.y)
            const d = whichSide(q1.x, q1.y, q2.x, q2.y, p2.x, p2.y)
            if (a * b < 0 && c * d < 0) count++
        }
    }
    return count
}

/**
 * What a node reads and what reads it: the step either side of an asset, or the assets
 * either side of a step.
 *
 * The lineage below is everything a node reaches, all the way to the ends of the workflow,
 * and on the commonest shape there is that is the whole map. Measured over the ten
 * workflows in `rubicon/workflows`, six of them return every node from every node, so
 * pointing at the verdict dimmed nothing and the map answered "what does this rest on?"
 * with "everything". That is Steve's complaint of 6 September 2026 in its exact form: the
 * verdict "depends on steps 2 and 3 but actually on the results of them", and the map knew
 * as much and could not say it.
 *
 * So this is the near answer and `lineageOf` is the far one. The drawing used to use both,
 * the near one at full strength and the far one behind it; since 7 September 2026 it draws
 * the lineage alone, at Steve's instruction, and this answer is what the map SAYS in words
 * when you point at a node: what it reads and what reads it, named.
 *
 * Named by direction rather than by kind, because the same two lists read differently
 * depending on which end you are standing at. For a step `before` is what it read and
 * `after` is what it made; for an asset `before` is the step that made it and `after` is
 * every step that read it. The caller says which, since only the caller knows the words.
 */
export function neighboursOf(laidOut, id) {
    const before = []
    const after = []
    for (const e of laidOut.edges) {
        if (e.to === id && !before.includes(e.from)) before.push(e.from)
        if (e.from === id && !after.includes(e.to)) after.push(e.to)
    }
    return { before, after }
}

/** Which nodes an id can reach, and which reach it, over the edges layout returned. */
export function lineageOf(laidOut, id) {
    const up = new Map()
    const down = new Map()
    const add = (map, key, value) => {
        if (!map.has(key)) map.set(key, [])
        map.get(key).push(value)
    }
    for (const e of laidOut.edges) {
        add(down, e.from, e.to)
        add(up, e.to, e.from)
    }
    const walk = (start, way) => {
        const seen = new Set()
        const todo = [start]
        while (todo.length) {
            const here = todo.pop()
            for (const next of way.get(here) || []) {
                if (seen.has(next)) continue
                seen.add(next)
                todo.push(next)
            }
        }
        return seen
    }
    return new Set([id, ...walk(id, up), ...walk(id, down)])
}

const ROUND = 3

/** A rounded rectangle, since a step is drawn as one in the diagram too. */
function box(ctx, x, y, w, h, r) {
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.arcTo(x + w, y, x + w, y + h, r)
    ctx.arcTo(x + w, y + h, x, y + h, r)
    ctx.arcTo(x, y + h, x, y, r)
    ctx.arcTo(x, y, x + w, y, r)
    ctx.closePath()
}

/**
 * The edge nearest a point, or nothing.
 *
 * Steve, 7 September 2026: "on mouse over node or edge in margin map". A node is a disc to
 * aim at and an edge was not aimable at all, so the chain a person could see was the one
 * thing they could not ask about.
 *
 * Measured to the straight segment between the two ends rather than to the drawn curve.
 * The bow is a few pixels in a column 140 wide, and being a few pixels out on which line
 * you meant is not a fault a reader can see, where solving a cubic per edge per mousemove
 * is a cost they can feel. Ends are excluded by `from`: within that many pixels of either
 * node the node is what was meant, and the node hit-test has already answered.
 */
export function edgeAt(laidOut, seats, x, y, { within = 5, from = 7 } = {}) {
    let best = null
    for (const e of laidOut.edges) {
        const a = seats.get(e.from)
        const b = seats.get(e.to)
        if (!a || !b) continue
        const dx = b.x - a.x
        const dy = b.y - a.y
        const len = dx * dx + dy * dy
        if (!len) continue
        // Where the point falls along the segment, clamped to it.
        const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / len))
        const px = a.x + t * dx
        const py = a.y + t * dy
        const away = Math.hypot(x - px, y - py)
        if (away > within) continue
        if (Math.hypot(x - a.x, y - a.y) < from || Math.hypot(x - b.x, y - b.y) < from) continue
        if (!best || away < best.away) best = { edge: e, away }
    }
    return best ? best.edge : null
}

/**
 * A point on the last leg of a route, `back` pixels short of where that leg ends.
 *
 * Walked along the curve rather than measured down the straight line between the ends,
 * because the leg bows: an edge given a column of its own comes into its target from the
 * side, and a point taken off the chord would sit beside the line rather than on it.
 * Sampled rather than solved, since a cubic has no closed-form arc length and the answer
 * is wanted to the nearest pixel in a column 140 wide.
 *
 * The control points are the ones `draw` uses, and they have to stay the ones `draw` uses:
 * they are what makes this the curve on the screen rather than a second guess at it.
 *
 * Exported only so it can be tested. `draw` needs a canvas and is checked in a browser,
 * but the fault this had was arithmetic and silent, and a browser could not have shown it:
 * every arrowhead was skipped and a map with no arrowheads on it looks exactly like a map
 * nobody had drawn any on.
 */
export function alongCurve(p, q, back, steps = 24) {
    const mid = (p.y + q.y) / 2
    const at = t => {
        const u = 1 - t
        return {
            x: u * u * u * p.x + 3 * u * u * t * p.x + 3 * u * t * t * q.x + t * t * t * q.x,
            y: u * u * u * p.y + 3 * u * u * t * mid + 3 * u * t * t * mid + t * t * t * q.y,
        }
    }
    let last = { x: q.x, y: q.y }
    let gone = 0
    for (let i = 1; i <= steps; i++) {
        const here = at(1 - i / steps)
        const leg = Math.hypot(here.x - last.x, here.y - last.y)
        // Within the step rather than at the near end of it. Snapping to whichever sample
        // first went far enough drew nothing at all: a leg the height of one rank moves
        // about six pixels per sample, the tip and the tail of a head are three and a half
        // apart, so both landed on the same sample, the direction came out as zero length
        // and every head was skipped by the guard below. Nothing on the screen said so,
        // since a missing arrowhead looks exactly like an arrowhead nobody drew.
        if (gone + leg >= back) {
            const part = leg ? (back - gone) / leg : 0
            return { x: last.x + (here.x - last.x) * part,
                     y: last.y + (here.y - last.y) * part }
        }
        gone += leg
        last = here
    }
    return last
}

/**
 * Which way the work went, said on the line itself.
 *
 * Steve, 6 September 2026: "add small downward arrowheads to the minimap edges." Every
 * edge runs from what made a thing to what read it, and nothing on the line said so.
 *
 * The head goes at the target end and points along the curve where it arrives, taken from
 * the curve rather than assumed to be straight down. With the present routing those come
 * to the same thing, since the last control point shares the target's x so every leg
 * arrives vertically; the difference is that a head drawn down the screen by fiat would
 * start lying the day the routing changes, and an edge coming in from the side would then
 * carry a head pointing at a node it does not touch.
 *
 * Small on purpose. The tip clears the node's own mark by two pixels and the whole head is
 * about half the width of a result dot: the map is a narrow column and its point is the
 * shape, so a dozen heads competing with the nodes would cost more than they say.
 */
function arrowhead(ctx, route, clear, length, spread) {
    const p = route[route.length - 2]
    const q = route[route.length - 1]
    const tip = alongCurve(p, q, clear)
    const tail = alongCurve(p, q, clear + length)
    const dx = tip.x - tail.x
    const dy = tip.y - tail.y
    const run = Math.hypot(dx, dy)
    // Both ends in one place, which a rank holding a node nothing could order can produce.
    // Nothing to point along, so nothing is drawn rather than a triangle facing anywhere.
    if (run < 0.5) return
    const ux = dx / run
    const uy = dy / run
    ctx.beginPath()
    ctx.moveTo(tip.x, tip.y)
    ctx.lineTo(tip.x - ux * length - uy * spread, tip.y - uy * length + ux * spread)
    ctx.lineTo(tip.x - ux * length + uy * spread, tip.y - uy * length - ux * spread)
    ctx.closePath()
    ctx.fill()
}

/**
 * Paint it.
 *
 * `colours` comes from the stylesheet, through `minimap-mount.js`'s `mapColours`, so the map, its key
 * and the status chips stay one decision rather than three.
 *
 * `here` is the set of node ids whose blocks are on the screen, found by asking which
 * blocks intersect rather than from a scroll fraction. A fraction is wrong the moment two
 * blocks are different heights, which they always are.
 *
 * `current` is the one node whose block is being read, ringed. `lit` is the lineage of the
 * node in hand: everything it came from, however far back, and everything made from it,
 * however far on. All of it is drawn at full strength and everything else drops away.
 *
 * There was a third strength between them, `near`, for what the node directly reads and
 * directly made, on the argument that a lineage is often the whole workflow and dimming
 * nothing says nothing. Steve, 7 September 2026: "the whole ancestry and descendents
 * should be highlighted, not just 1 generation away". A lineage that turns out to be
 * everything IS the answer where the workflow is a chain, and saying so plainly beats
 * ranking the chain by distance from the pointer.
 *
 * `beat` is where a running step is in its pulse, 0 to 1, or null for no pulse at all.
 * A phase rather than a clock: this has to be callable twice for the same picture, which
 * a function reading the time is not, and the page is the thing that knows whether it may
 * animate and when to stop.
 *
 * Returns where every node was put, in canvas pixels, which is what the page hit-tests a
 * click and a hover against. A canvas has nothing to aim at otherwise.
 */
export function draw(canvas, laidOut, { colours, here = new Set(), lit = null,
                                        current = null, beat = null } = {}) {
    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    if (!w || !h) return new Map()
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    const pad = 10
    const rows = Math.max(1, laidOut.ranks)
    // `layout` decided the spacing down the map too, and per node rather than per row,
    // since a result its step alone made hangs tight under that step whatever else shares
    // its rank. A seat reserved for a passing edge has no node, so it takes its rank's own
    // level, which is the y everything unpaired in that rank sits at.
    const level = r => laidOut.levels?.[r] ?? r / (rows - 1)
    const down = f => rows > 1 ? pad + f * (h - pad * 2) : h / 2
    const rowY = r => down(level(r))
    const nodeY = n => down(n.y ?? level(n.rank))
    // `layout` decided the shape, as a fraction of the width; here it becomes pixels. A
    // rank of four is four dots side by side across the whole gutter, and a rank of one is
    // off to its own side rather than dead centre, which is what made a step-asset-step
    // workflow one vertical line with faint bows on it.
    const across = x => pad + x * (w - pad * 2)
    // A node shrinks where its rank is crowded, so a workflow eight things wide is eight
    // things rather than one smear. Measured over the 147 newest runs the widest rank is
    // 8, which at this gutter is where a full-size box would start touching its neighbour.
    const pitch = (w - pad * 2) / Math.max(1, laidOut.widest)
    const size = Math.max(0.55, Math.min(1, pitch / 16))

    const at = new Map(laidOut.nodes.map(n =>
        [n.id, { x: across(n.x), y: nodeY(n), n }]))

    // The band saying where the reader is, drawn under everything so the nodes stay legible
    // on top of it.
    const seen = laidOut.nodes.filter(n => here.has(n.id)).map(n => nodeY(n))
    if (seen.length) {
        const top = Math.min(...seen) - 7
        const bottom = Math.max(...seen) + 7
        ctx.fillStyle = colours.band
        ctx.fillRect(0, top, w, Math.max(14, bottom - top))
    }

    ctx.lineWidth = 1
    for (const e of laidOut.edges) {
        const a = at.get(e.from)
        const b = at.get(e.to)
        if (!a || !b) continue
        // An edge is in the lineage when both its ends are: the chain the pointer is on
        // is drawn as a line and everything else fades to a shading of one.
        const close = lit && lit.has(e.from) && lit.has(e.to)
        ctx.strokeStyle = close ? colours.ink : colours.line
        ctx.lineWidth = close ? 1.8 : 1
        ctx.globalAlpha = close ? 0.9 : lit ? 0.14 : 0.6
        // An edge that skips a rank bows out through the seats `layout` reserved for it,
        // rather than being drawn end to end across whatever the ranks between are doing.
        // Without a bow of some kind it ran straight down the same column as the chain
        // edges and was invisible: a judging step reading a table AND the quotes three
        // ranks above it looked exactly like a step reading only the table. Measured over
        // the 40 newest runs in the ledger, 14 of the 23 that draw anything have such an
        // edge, so those maps were drawing a straight line for a workflow that is not one.
        // Steve, 5 September 2026: "all the margin maps seem to just show a linear flow
        // a --> b --> c --> d, are u sure?" Where the bow goes is `layout`'s to decide,
        // because it is the only thing that knows which column is free.
        const route = [a, ...(e.via || []).map(v => ({ x: across(v.x), y: rowY(v.rank) })), b]
        // What an earlier run gave is drawn dashed, all the way back, so the line from
        // somebody else's work into this run's reads as a different kind of line from the
        // lines inside it.
        ctx.setLineDash(a.n.kind === 'run' ? [3, 2] : [])
        ctx.beginPath()
        ctx.moveTo(route[0].x, route[0].y)
        for (let i = 0; i < route.length - 1; i++) {
            const p = route[i]
            const q = route[i + 1]
            const mid = (p.y + q.y) / 2
            ctx.bezierCurveTo(p.x, mid, q.x, mid, q.x, q.y)
        }
        ctx.stroke()
        ctx.setLineDash([])
        // Ink, at the line's own alpha. Filling it in the line's colour was the first
        // try and it could not be seen: measured on a recording canvas, all nine heads
        // were painted, 3.4px long and 4.4px wide, in exactly the `#b9b9c4` of the 1px
        // line they sat on, so each was a slight thickening rather than an arrow. Steve,
        // 6 September 2026: "i don't see the downward arrows in margin map?" The alpha is
        // still the line's, set above and not touched here, so a dimmed edge cannot carry
        // a bright head and an edge drawn as the answer matches its head exactly.
        ctx.fillStyle = colours.ink
        // Held above the node scale. A node shrinks when its rank is crowded ACROSS the
        // map, and a head runs along the edge, which is down it, so the two have no
        // reason to shrink together and a head at 0.55 was invisible again.
        const nib = Math.max(0.8, size)
        arrowhead(ctx, route, (b.n.kind === 'step' ? 4 : 5.5) * size + 2,
            6 * nib, 3.2 * nib)
    }
    ctx.globalAlpha = 1
    ctx.lineWidth = 1

    for (const { x, y, n } of at.values()) {
        ctx.globalAlpha = !lit ? 1 : lit.has(n.id) ? 1 : 0.16
        // A step that is working, pulsing. Steve, 6 September 2026: "when a node is
        // running, pulse it in the margin map."
        //
        // A halo behind the node rather than a ring around it. The map already rings a
        // node twice, in red for what the workflow was for and in ink for where the
        // reader is, so a third ring would be a third thing to learn and, held still for
        // somebody who has asked not to see motion, would be the red one exactly. A
        // filled disc is a different kind of mark and cannot be mistaken for either.
        //
        // Red, which is what the rest of the page uses for anything live: the busy bar
        // across the top of the window and the bar on a working column are the same red,
        // so working looks like one thing rather than three. The phase comes in as an
        // argument, because a drawing function that owned a clock could not be called
        // twice for the same picture.
        if (n.kind === 'step' && n.status === 'running' && beat !== null) {
            const held = ctx.globalAlpha
            // Multiplied by the node's own alpha, so a running step outside the lineage
            // being read pulses as quietly as it is drawn.
            // Twice as strong and twice as wide as it first was, which was too quiet to be
            // seen at a glance (Steve, 21 September 2026): a solid disc that swells, and a ring
            // that runs out ahead of it.
            ctx.globalAlpha = held * 0.84 * (1 - beat)
            ctx.fillStyle = colours.red
            ctx.beginPath()
            ctx.arc(x, y, (7 + 14 * beat) * size, 0, Math.PI * 2)
            ctx.fill()
            ctx.globalAlpha = held * (1 - beat)
            ctx.strokeStyle = colours.red
            ctx.lineWidth = 2 * size
            ctx.beginPath()
            ctx.arc(x, y, (9 + 18 * beat) * size, 0, Math.PI * 2)
            ctx.stroke()
            ctx.lineWidth = 1
            ctx.globalAlpha = held
        }
        // Fill for role, shape for kind, outline for how it went: `paintNode`.
        paintNode(ctx, n, x, y, size, colours)
        // What the workflow was for, ringed in red. A failed step's red is its box outline,
        // and only results are ever ringed, so the two cannot be taken for each other.
        if (n.terminal) paintRing(ctx, x, y, 7.5 * size, colours.red)
        // Where the reader is, or what the pointer is over: a ring in the ink colour, so
        // it cannot be mistaken for the red one that says what the workflow was for.
        if (current && n.id === current) paintRing(ctx, x, y, 9.5 * size, colours.ink)
    }
    ctx.globalAlpha = 1
    return at
}
