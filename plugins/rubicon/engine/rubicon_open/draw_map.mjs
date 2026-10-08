// The DOT for a causal map, from the same builder the page draws with (./map-dot.js). The report carries it, and
// Graphviz draws it in the reader's browser (report.js).
//
// stdin:  {"edges": [{"id", "from", "to", "n"}, ...]}
// stdout: {"dot": "digraph ...", "engine": "dot"}
import { mapDot } from './map-dot.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { edges } = JSON.parse(raw)
process.stdout.write(JSON.stringify({ dot: mapDot(edges), engine: 'dot' }))
