// Draw a causal map as SVG, under Node, with Graphviz (the vendored Viz.js) from the same DOT the page draws
// (./map-dot.js).
//
// stdin:  {"edges": [{"id", "from", "to", "n"}, ...]}
// stdout: {"svg": "<svg ...>"}
import { mapDot } from './map-dot.js'
import { instance } from './vendor/viz.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { edges } = JSON.parse(raw)
const viz = await instance()
process.stdout.write(JSON.stringify({ svg: viz.renderString(mapDot(edges), { format: 'svg' }) }))
