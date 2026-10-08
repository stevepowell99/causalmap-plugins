/**
 * A causal map as Graphviz DOT: one box a factor, one arrow a cause-to-effect cell of a tabulation, the arrow as
 * thick as its count and labelled with it. Pure, and the one place a map's drawing is decided: the plugin's report
 * draws it under Node from the open engine's copy (`rubicon/open/rubicon_open/map-dot.js`, which
 * `tests/rubicon-open-map-dot-twin.test.mjs` keeps identical), and the page draws it in the browser.
 *
 * `edges` is [{id, from, to, n, sign}]: `id` becomes the arrow's id in the drawing, so a click on it can open the cell,
 * and `sign`, where a causal loop diagram's link has one, is `+`, `-` or `?`, drawn at the arrowhead.
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

export function mapDot(edges, { rankdir = 'LR' } = {}) {
    const names = [...new Set(edges.flatMap(e => [String(e.from), String(e.to)]))]
    const node = new Map(names.map((name, i) => [name, `f${i}`]))
    const most = Math.max(1, ...edges.map(e => Number(e.n) || 0))
    const out = [
        'digraph map {',
        `  graph [rankdir=${rankdir}, bgcolor="transparent", nodesep=0.3, ranksep=0.5, fontname="Helvetica"];`,
        '  node [shape=box, style="rounded", fontname="Helvetica", fontsize=11, margin="0.12,0.06"];',
        '  edge [fontname="Helvetica", fontsize=10, arrowsize=0.7];',
    ]
    for (const name of names) out.push(`  ${node.get(name)} [label=${quote(wrapLabel(name))}];`)
    for (const e of edges) {
        const n = Number(e.n) || 0
        out.push(`  ${node.get(String(e.from))} -> ${node.get(String(e.to))} [id=${quote(e.id)}, label=${quote(n)}, ` +
            `penwidth=${(1 + 4 * n / most).toFixed(2)}, tooltip=${quote(`${e.from} → ${e.to}: ${n}`)}${signed(e)}];`)
    }
    out.push('}')
    return out.join('\n')
}

/**
 * One loop, for Graphviz's neato engine with every position fixed: `links` in the loop's order, each {id, from, to, n,
 * sign}, the first starting at the top and the loop running clockwise; `drivers` the links into it from outside.
 */
export function loopDot({ marker, links, drivers = [] }) {
    const ring = links.map(e => String(e.from))
    const radius = Math.max(1.3, 0.55 * ring.length)
    const at = new Map(ring.map((name, i) => {
        const a = Math.PI / 2 - 2 * Math.PI * i / ring.length
        return [name, [radius * Math.cos(a), radius * Math.sin(a)]]
    }))
    const outside = [...new Set(drivers.map(e => String(e.from)))]
    outside.forEach((name, i) => {
        const [x, y] = at.get(String(drivers.find(e => String(e.from) === name).to))
        const spread = 0.35 * (i - (outside.length - 1) / 2)
        const a = Math.atan2(y, x) + spread
        at.set(name, [2.1 * radius * Math.cos(a), 2.1 * radius * Math.sin(a)])
    })
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
