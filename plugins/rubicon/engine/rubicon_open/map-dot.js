/**
 * A causal map as Graphviz DOT: one box a factor, one arrow a cause-to-effect cell of a tabulation, the arrow as
 * thick as its count and labelled with it. Pure, and the one place a map's drawing is decided: the plugin's report
 * draws it under Node from the open engine's copy (`rubicon/open/rubicon_open/map-dot.js`, which
 * `tests/rubicon-open-map-dot-twin.test.mjs` keeps identical), and the page draws it in the browser.
 *
 * `edges` is [{id, from, to, n}]: `id` becomes the arrow's id in the drawing, so a click on it can open the cell.
 */

const quote = s => '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'

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
            `penwidth=${(1 + 4 * n / most).toFixed(2)}, tooltip=${quote(`${e.from} → ${e.to}: ${n}`)}];`)
    }
    out.push('}')
    return out.join('\n')
}
