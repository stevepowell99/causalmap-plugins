// The DOT for a causal map, or for one feedback loop, from the same builder the page draws with (./map-dot.js). The
// report carries it, and Graphviz draws it in the reader's browser (report.js).
//
// Where opposites were combined, each edge says how many of its `of` rows had the cause, and the effect, coded at the
// opposite pole (`flipped`), and the map is coloured as Causal Map colours one with Together bundling (`oppositesColours`
// in ./map-dot.js, which the page uses too), by Causal Map's own colour function.
//
// stdin:  {"edges": [{"id", "from", "to", "n", "sign"?, "flipped"?: {"cause", "effect", "of"}}, ...]},
//         or {"loop": {"marker", "links": [...], "drivers": [...]}}
// stdout: {"dot": "digraph ...", "engine": "dot" or "neato"}, and for a map its `caption` (`mapCaption`), with
//         *emphasis* marked as markdown marks it
import { loopDot, mapCaption, mapDot, oppositesColours } from './map-dot.js'
import { flippedShareColour } from './cm/link-display-transforms.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { edges, loop } = JSON.parse(raw)
if (loop) process.stdout.write(JSON.stringify({ dot: loopDot(loop), engine: 'neato' }))
else {
    const { edges: drawn, borders } = oppositesColours(edges, { shareColour: flippedShareColour })
    process.stdout.write(JSON.stringify({ dot: mapDot(drawn, { borders }), engine: 'dot', caption: mapCaption(edges) }))
}
