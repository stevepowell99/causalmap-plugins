// The DOT for a causal map, or for one feedback loop, from the same builder the page draws with (./map-dot.js). The
// report carries it, and Graphviz draws it in the reader's browser (report.js).
//
// Where opposites were combined, each edge says how many of its `of` rows had the cause, and the effect, coded at the
// opposite pole (`flipped`), and the map is coloured as Causal Map colours one with Together bundling: each arrow's
// tail and head, and each factor's border, from blue (none flipped) to red (all), by Causal Map's own colour function.
//
// stdin:  {"edges": [{"id", "from", "to", "n", "sign"?, "flipped"?: {"cause", "effect", "of"}}, ...]},
//         or {"loop": {"marker", "links": [...], "drivers": [...]}}
// stdout: {"dot": "digraph ...", "engine": "dot" or "neato"}
import { loopDot, mapDot } from './map-dot.js'
import { flippedShareColour, interpolateHexColour } from './cm/link-display-transforms.js'

/** The edges with their Together colours, and each factor's border colour, where any edge carries `flipped`. */
export function oppositesColours(edges) {
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
        const tail = flippedShareColour(of ? cause / of : 0)
        const head = flippedShareColour(of ? effect / of : 0)
        return { ...e, colour: { tail, head, mid: interpolateHexColour(tail, head, 0.5) } }
    })
    const borders = Object.fromEntries([...at].map(([name, t]) => [name, flippedShareColour(t.of ? t.flip / t.of : 0)]))
    return { edges: coloured, borders }
}

if (process.argv[1] && import.meta.url === (await import('node:url')).pathToFileURL(process.argv[1]).href) {
    let raw = ''
    process.stdin.setEncoding('utf8')
    for await (const chunk of process.stdin) raw += chunk
    const { edges, loop } = JSON.parse(raw)
    if (loop) process.stdout.write(JSON.stringify({ dot: loopDot(loop), engine: 'neato' }))
    else {
        const { edges: drawn, borders } = oppositesColours(edges)
        process.stdout.write(JSON.stringify({ dot: mapDot(drawn, { borders }), engine: 'dot' }))
    }
}
