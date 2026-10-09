/**
 * A causal map as Graphviz DOT: one box a factor, one arrow a cause-to-effect cell of a tabulation, the arrow as
 * thick as its count and labelled with it. Pure, and the one place a map's drawing is decided: the plugin's report
 * draws it under Node from the open engine's copy (`rubicon/open/rubicon_open/map-dot.js`, which
 * `tests/rubicon-open-map-dot-twin.test.mjs` keeps identical), and the page draws it in the browser.
 *
 * `edges` is [{id, from, to, n, sign}]: `id` becomes the arrow's id in the drawing, so a click on it can open the cell,
 * and `sign`, where a causal loop diagram's link has one, is `+`, `-` or `?`, drawn at the arrowhead. Where opposites
 * were combined, `colour` is {tail, head, mid}: the arrow runs from its tail colour to its head colour and its count is
 * written in the colour between, and `borders` gives each factor's border colour, as Causal Map draws Together bundling.
 * Each such arrow and factor carries the class `opp`, so a stylesheet that inks the map leaves their colours alone.
 *
 * `loopDot` draws one feedback loop as causal loop diagrams draw one: its variables round a circle, each arrow's sign at
 * its head, the loop's marker (R1, B1) in the middle, and the links into it from outside drawn in from beyond the circle.
 */

const quote = s => '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'

/** A sign as drawn: a plus, a minus sign, or a question mark where the coding left it unclear. */
const SIGN = { '+': '+', '-': '\u2212', '?': '?' }
const signed = e => (e.sign in SIGN ? `, headlabel=${quote(SIGN[e.sign])}, labelfontsize=14, labeldistance=1.6` : '')

/** A label broken onto lines of about `width` characters, at spaces. */
export function wrapLabel(text, width = 22) {
    const lines = []
    let line = ''
    for (const word of String(text).split(/\s+/).filter(Boolean)) {
        if (line && line.length + 1 + word.length > width) { lines.push(line); line = word }
        else line = line ? `${line} ${word}` : word
    }
    if (line) lines.push(line)
    return lines.join('\n')
}

/**
 * Where any edge carries `flipped` ({cause, effect, of}: of its `of` rows, how many had the cause,
 * and the effect, coded at the opposite pole), each edge's `colour` and each factor's border
 * colour as Causal Map colours Together bundling: from blue, none flipped, through purple, half,
 * to red, all. An arrow's count takes the colour of the mean of its two ends' shares. The caller
 * hands in Causal Map's `flippedShareColour` from `link-display-transforms.js`, so the colours
 * are the app's own.
 */
export function oppositesColours(edges, { shareColour }) {
    if (!edges.some(e => e.flipped)) return { edges, borders: {} }
    const at = new Map()
    const add = (name, flip, of) => {
        const t = at.get(name) || { flip: 0, of: 0 }
        at.set(name, { flip: t.flip + flip, of: t.of + of })
    }
    const coloured = edges.map(e => {
        const { cause = 0, effect = 0, of = 0 } = e.flipped || {}
        add(String(e.from), cause, of)
        add(String(e.to), effect, of)
        const tail = shareColour(of ? cause / of : 0)
        const head = shareColour(of ? effect / of : 0)
        const mid = shareColour(of ? (cause + effect) / (2 * of) : 0)
        return { ...e, colour: { tail, head, mid } }
    })
    const borders = Object.fromEntries([...at].map(([name, t]) => [name, shareColour(t.of ? t.flip / t.of : 0)]))
    return { edges: coloured, borders }
}

/**
 * What a causal map's caption says, in the words the report and the page both use: what an arrow and its number are,
 * what a sign means where the links carry one, how combined opposites are coloured where any were, and what a click
 * opens. `*as labelled*` is emphasis, which each reader of this turns into its own italics.
 */
export const CAPTION = {
    arrows: 'Each arrow is a causal link; its number is how many sources mention it.',
    signs: 'The sign at each arrowhead says whether the two move the same way (+), opposite ways (−) or the '
        + 'source did not say (?).',
    opposites: 'A factor and its opposite share one box, so “Good health” also covers poor health. Colour says '
        + 'which way round: where an arrow’s tail is blue, the factor *as labelled* was the cause; where it is red, its '
        + 'opposite was the cause. The arrowhead says the same about the effect, and shades in between mean a mix. Box '
        + 'borders are coloured the same way.',
    click: 'Click an arrow or a box to read its passages.',
}

/** The caption for a map of these edges, sentence by sentence as `CAPTION` gives them. */
export function mapCaption(edges, { click = CAPTION.click } = {}) {
    return [CAPTION.arrows, edges.some(e => e.sign in SIGN) ? CAPTION.signs : '',
        edges.some(e => e.flipped) ? CAPTION.opposites : '', click].filter(Boolean).join(' ')
}

export function mapDot(edges, { rankdir = 'LR', borders = {} } = {}) {
    const names = [...new Set(edges.flatMap(e => [String(e.from), String(e.to)]))]
    const node = new Map(names.map((name, i) => [name, `f${i}`]))
    const most = Math.max(1, ...edges.map(e => Number(e.n) || 0))
    const out = [
        'digraph map {',
        `  graph [rankdir=${rankdir}, bgcolor="transparent", nodesep=0.3, ranksep=0.5, fontname="Helvetica"];`,
        '  node [shape=box, style="rounded", fontname="Helvetica", fontsize=11, margin="0.12,0.06"];',
        '  edge [fontname="Helvetica", fontsize=10, arrowsize=0.7];',
    ]
    const border = name => (borders[name] ? `, color=${quote(borders[name])}, penwidth=1.5, class="opp"` : '')
    const coloured = e => (e.colour
        ? `, color=${quote(`${e.colour.tail};0.5:${e.colour.head}`)}, fontcolor=${quote(e.colour.mid)}, class="opp"` : '')
    for (const name of names) out.push(`  ${node.get(name)} [label=${quote(wrapLabel(name))}${border(name)}];`)
    for (const e of edges) {
        const n = Number(e.n) || 0
        out.push(`  ${node.get(String(e.from))} -> ${node.get(String(e.to))} [id=${quote(e.id)}, label=${quote(n)}, ` +
            `penwidth=${(1 + 4 * n / most).toFixed(2)}, tooltip=${quote(`${e.from} → ${e.to}: ${n}`)}${signed(e)}${coloured(e)}];`)
    }
    out.push('}')
    return out.join('\n')
}

/**
 * A box's size in inches, as Graphviz draws a label of 11-point Helvetica wrapped at `width` characters with the
 * margins `loopDot` sets, rounded up a little so that boxes kept this far apart never touch.
 */
function boxSize(name, width) {
    const lines = wrapLabel(name, width).split('\n')
    return [0.092 * Math.max(...lines.map(l => l.length)) + 0.34, 0.19 * lines.length + 0.22]
}

/** How far apart two box centres must be for boxes of these sizes never to overlap, whatever their angle. */
const clearance = sizes => Math.hypot(Math.max(...sizes.map(s => s[0])), Math.max(...sizes.map(s => s[1]))) + 0.15

/**
 * One loop, for Graphviz's neato engine with every position fixed: `links` in the loop's order, each {id, from, to, n,
 * sign}, the first starting at the top and the loop running clockwise; `drivers` the links into it from outside.
 *
 * The loop's variables sit round a circle, and the variables outside it round a wider one, evenly spaced, in the order
 * of the loop variables they drive and turned to sit as near them as they can. Each circle is made wide enough that
 * neighbouring boxes, and an outside box and the ring, cannot touch, so however many drivers a loop has no box is drawn
 * over another.
 */
export function loopDot({ marker, links, drivers = [] }) {
    const ring = links.map(e => String(e.from))
    const outside = [...new Set(drivers.map(e => String(e.from)))]
    const gap = clearance(ring.map(n => boxSize(n, 18)))
    const radius = Math.max(1.3, 0.55 * ring.length, ring.length > 1 ? gap / (2 * Math.sin(Math.PI / ring.length)) : 0)
    const angle = new Map(ring.map((name, i) => [name, Math.PI / 2 - 2 * Math.PI * i / ring.length]))
    const at = new Map(ring.map(name => [name, [radius * Math.cos(angle.get(name)), radius * Math.sin(angle.get(name))]]))
    if (outside.length) {
        const far = clearance([...ring, ...outside].map(n => boxSize(n, 18)))
        const outer = Math.max(2.1 * radius, radius + far,
            outside.length > 1 ? clearance(outside.map(n => boxSize(n, 18))) / (2 * Math.sin(Math.PI / outside.length)) : 0)
        // where each outside variable would like to be: towards the loop variables it drives
        const wants = new Map(outside.map(name => {
            const to = drivers.filter(e => String(e.from) === name).map(e => angle.get(String(e.to)))
            return [name, Math.atan2(to.reduce((t, a) => t + Math.sin(a), 0), to.reduce((t, a) => t + Math.cos(a), 0))]
        }))
        const order = [...outside].sort((p, q) => wants.get(p) - wants.get(q))
        const step = 2 * Math.PI / order.length
        const off = (a, b) => { const d = Math.abs(a - b) % (2 * Math.PI); return Math.min(d, 2 * Math.PI - d) }
        let best = null
        for (let k = 0; k < 360; k++) {
            const turn = k * step / 360 + wants.get(order[0])
            const cost = order.reduce((t, name, i) => t + off(turn + i * step, wants.get(name)) ** 2, 0)
            if (!best || cost < best.cost) best = { cost, turn }
        }
        order.forEach((name, i) => {
            const a = best.turn + i * step
            at.set(name, [outer * Math.cos(a), outer * Math.sin(a)])
        })
    }
    const node = new Map([...at.keys()].map((name, i) => [name, `v${i}`]))
    const most = Math.max(1, ...links.concat(drivers).map(e => Number(e.n) || 0))
    const out = [
        'digraph loop {',
        '  graph [bgcolor="transparent", splines=curved, fontname="Helvetica"];',
        '  node [shape=box, style="rounded", fontname="Helvetica", fontsize=11, margin="0.12,0.06"];',
        '  edge [fontname="Helvetica", fontsize=10, arrowsize=0.7];',
        `  centre [shape=plaintext, label=${quote(`\u21bb ${marker}`)}, fontsize=16, pos="0,0!"];`,
    ]
    for (const [name, [x, y]] of at) {
        const extra = ring.includes(name) ? '' : ', style="rounded,dashed"'
        out.push(`  ${node.get(name)} [label=${quote(wrapLabel(name, 18))}, pos="${x.toFixed(2)},${y.toFixed(2)}!"${extra}];`)
    }
    // a loop of two would draw its arrows on top of each other and of the marker, so they leave and arrive by the right
    // side going down and the left side coming back up
    const side = (e, i) => (ring.length === 2 && i < 2 ? `:${i ? 'w' : 'e'}` : '')
    links.concat(drivers).forEach((e, i) => {
        const n = Number(e.n) || 0
        out.push(`  ${node.get(String(e.from))}${side(e, i)} -> ${node.get(String(e.to))}${side(e, i)} [id=${quote(e.id)}, label=${quote(n)}, ` +
            `penwidth=${(1 + 3 * n / most).toFixed(2)}, tooltip=${quote(`${e.from} → ${e.to}: ${n}`)}${signed(e)}];`)
    })
    out.push('}')
    return out.join('\n')
}
