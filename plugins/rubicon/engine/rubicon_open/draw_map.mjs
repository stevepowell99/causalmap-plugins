// The DOT for a causal map, or for one feedback loop, from the same builder the page draws with (./map-dot.js). The
// report carries it, and Graphviz draws it in the reader's browser (report.js).
//
// stdin:  {"edges": [{"id", "from", "to", "n", "sign"?}, ...]}, or {"loop": {"marker", "links": [...], "drivers": [...]}}
// stdout: {"dot": "digraph ...", "engine": "dot" or "neato"}
import { loopDot, mapDot } from './map-dot.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { edges, loop } = JSON.parse(raw)
process.stdout.write(JSON.stringify(loop ? { dot: loopDot(loop), engine: 'neato' } : { dot: mapDot(edges), engine: 'dot' }))
