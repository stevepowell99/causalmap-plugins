/**
 * The margin map mounted beside a document: drawn, kept current as the reader scrolls, and
 * answering the pointer. One copy serves the Rubicon page and the plugin's report, which
 * carries a copy of this file and of `minimap.js` in `rubicon/open/rubicon_open/`, kept identical
 * by `tests/rubicon-open-minimap-twin.test.mjs`, so the map in a report and on the page behave
 * as one.
 *
 * `mountMap` finds the map (`MAP_ASIDE`'s markup) and the blocks it names (`.rb-block[data-node]`)
 * under `root`. `scroller` is what scrolls, the page's canvas or `document.scrollingElement` in a
 * report. `opened(node, id)` is told when a click on a node has scrolled to its block, so the
 * page can open the result itself; `owned(stop)` is handed what lets everything go.
 */
import { layout, draw, lineageOf, neighboursOf, edgeAt, keyEntries, paintKeyEntry } from './minimap.js?v=2026-10-07T08:36:34Z'

const escape = s => String(s ?? '').replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])

/** Where the scroller shows the document: its own box, or the window's for the document itself. */
const viewOf = scroller => scroller === document.scrollingElement
    ? { top: 0, height: scroller.clientHeight } : scroller.getBoundingClientRect()

/**
 * The run states, in the stylesheet's own colours.
 *
 * They were five hex values written here, beside five more in the CSS for the same five
 * states, so a status chip and its node in the diagram were two different greens. Read at
 * draw time from the custom properties, which is the one place they are decided.
 */
export function statusColours() {
    const css = getComputedStyle(document.documentElement)
    const of = (name, fallback) =>
        (css.getPropertyValue(`--rb-${name}`) || '').trim() || fallback
    return {
        succeeded: of('succeeded', '#3f6b4a'),
        skipped: of('skipped', '#7d7268'),
        waiting: of('waiting', '#8a6d1f'),
        failed: of('red', '#8c1912'),
        running: of('running', '#445a6b'),
        stale: of('stale', '#6b5a63'),
        // A step with no record has not started, and it is a state like any other. Left
        // out, it fell through to a fallback colour that meant nothing and looked as
        // deliberate as the rest: "no idea what any of the colours mean" (Steve,
        // 4 September 2026).
        'not run': of('faint', '#a89a8b'),
    }
}

/**
 * Everything the margin map and its key paint with, from the stylesheet.
 *
 * Fill means role: `instruction` (a step) and `result`, two greens of one family. The
 * status colours are used only as a step's outline. Read once per mount from the custom
 * properties, which are the one place these are decided.
 */
export function mapColours() {
    const css = getComputedStyle(document.documentElement)
    const of = (name, fallback) =>
        (css.getPropertyValue(`--rb-${name}`) || '').trim() || fallback
    return {
        ...statusColours(),
        instruction: of('instruction', '#dcefe5'),
        instructionEdge: of('instruction-edge', '#0b7a5e'),
        result: of('result', '#0a9d78'),
        resultEdge: of('result-edge', '#0b6a52'),
        detail: of('panel', '#fdfbf6'),
        paper: of('paper', '#f7f4ee'),
        line: '#b9b9c4',
        red: of('red', '#8c1912'),
        band: of('red-wash', '#f6e8e4'),
        ink: of('ink', '#17130f'),
    }
}

/** The margin map's place beside a document, which `mountMap` draws into. */
export const MAP_ASIDE = `<aside class="rb-minimap"><canvas class="rb-map" aria-hidden="true"></canvas>
        <div class="rb-map-tips" aria-hidden="true"></div>
        <details class="rb-map-key"><summary></summary><div class="rb-map-items"></div>
        </details>
        <button type="button" class="rb-map-toggle" aria-expanded="false">map</button>
      </aside>`

/**
 * The margin map's key: one entry for each mark this map draws, from `keyEntries`.
 *
 * Steve, 6 September 2026: "the nodes are just the steps not the individual components",
 * and 17 September 2026: "the key and other colours are not clear to me". The entries and
 * their swatches both come from the map's own module, so the key cannot name a mark the
 * map does not draw, or draw one differently.
 */
function paintMapKey(key, laidOut, colours) {
    if (!key) return
    const entries = keyEntries(laidOut)
    const swatch = i => `<canvas width="16" height="16" data-entry="${i}"></canvas>`
    // Shut, it is the marks in a row and the word for what they are: one line at the foot
    // of the map. Steve, 7 September 2026: "the legend is quite tall, show only a bottom
    // bar and expand on click." Open, each mark takes a line and says what it stands for.
    // The row shut shows the instruction and the result kinds, which is what fits.
    const shut = entries.map((e, i) => [e, i]).filter(([e]) => e.node && !e.node.missing
        && (e.node.kind === 'asset' || e.word === 'instruction'))
    key.querySelector('summary').innerHTML =
        `<span class="rb-map-marks">${shut.map(([, i]) => swatch(i)).join('')}</span>key`
    key.querySelector('.rb-map-items').innerHTML = entries.map((e, i) =>
        `<span class="rb-map-item">${swatch(i)}${escape(e.word)}</span>`).join('')
    for (const c of key.querySelectorAll('canvas')) {
        const ctx = c.getContext('2d')
        const dpr = window.devicePixelRatio || 1
        c.width = 16 * dpr
        c.height = 16 * dpr
        ctx.scale(dpr, dpr)
        paintKeyEntry(ctx, entries[Number(c.dataset.entry)], colours)
    }
}

// Whether the map is open where it lies over the document. Held here rather than on the
// element, because a draft is redrawn when its forecast comes back and a map somebody had
// just opened would shut under them.
let mapOpen = false

/**
 * Put the margin map beside the document and keep it current.
 *
 * The map draws the same elements the diagram draws, through `graph.elementsFor`, and the
 * same colours through `mapColours`, so the two cannot become different pictures
 * of one workflow. What it adds is only where the reader is, and that is asked of the
 * blocks themselves rather than worked out from a scroll fraction: a fraction is wrong the
 * moment two blocks are different heights, which they always are.
 *
 * Redrawn on a `ResizeObserver` over the scroller as well as on scrolling, so resizing
 * the window without scrolling does not leave the canvas at its old height and backing store.
 *
 * Everything it holds is let go when the canvas is cleared, the same rule the cytoscape
 * handles follow, because an observer left on a removed element is the shape of fault that
 * took the whole page down once already.
 */
export function mountMap(root, elements, { scroller = root, opened = () => {}, owned = () => {} } = {}) {
    // Named, because the key beside it draws its swatches on canvases of their own and
    // `.rb-minimap canvas` stopped meaning the map on 7 September 2026.
    const canvas = root.querySelector('.rb-minimap canvas.rb-map')
    if (!canvas) return
    const aside = canvas.closest('.rb-minimap')
    const laidOut = layout(elements)
    // A workflow with no steps has no shape to draw, and an empty canvas in the margin
    // would read as a map that had failed rather than as one with nothing to say.
    if (!laidOut.nodes.length) {
        aside.hidden = true
        return
    }
    // In a canvas too narrow for a gutter, which a phone always is, the map waits behind
    // this button and opens over the document (the rule is in rubicon.css). Anywhere wider
    // the button is not drawn and has no height, so nothing below changes there.
    const toggle = aside.querySelector('.rb-map-toggle')
    const markOpen = open => {
        mapOpen = open
        aside.classList.toggle('rb-map-open', open)
        toggle?.setAttribute('aria-expanded', String(open))
        if (toggle) toggle.textContent = open ? 'hide map' : 'map'
    }
    markOpen(mapOpen)
    const colours = mapColours()

    // What the marks mean, built from the marks that are actually on this map. A fixed
    // key would name shapes nothing here draws and, worse, would say nothing about a
    // result type it had never heard of. Drawn with the map's own `markPath`, so the key
    // and the map cannot come to disagree, which is the rule the node list already keeps.
    //
    // Built here rather than in `paint`, which runs on every hover and every scroll: it is
    // a fold somebody opens, and rebuilding it under them would shut it again.
    const key = aside.querySelector('.rb-map-key')
    paintMapKey(key, laidOut, colours)
    const named = new Map(laidOut.nodes.map(n => [n.id, n]))
    const blocks = () => [...root.querySelectorAll('.rb-block[data-node]')]
    // Document order, which is the order the reader meets them in, and so the order the
    // ring walks down as they scroll.
    const order = blocks().map(b => b.dataset.node)

    const here = new Set()
    let seats = new Map()
    let onMap = null            // the node under the pointer, if any
    let onEdge = null           // or the edge, where the pointer is on a line instead
    let onBlock = null          // the block under the pointer, if any
    let lit = null              // that node's lineage, everything else dropped back
    let told = ''

    /**
     * The pulse on a step that is working.
     *
     * The map is a canvas, so `rb-wait` and the rest of the page's animations cannot be
     * put on a node: the beat has to be driven here. What `draw` is given is a phase, not
     * a clock, so the picture stays a function of its arguments and a hover or a scroll
     * redraws the same frame rather than jumping the animation.
     *
     * Driven only while something is running, and the loop is asked for again only from
     * inside itself, so nothing is scheduled once the last step lands: a page left open
     * for an hour on a finished run costs nothing at all. Frames are asked for at the
     * screen's rate and painted at about sixteen a second, which is a slow breath rather
     * than a flicker and is a fifth of the canvas work. `requestAnimationFrame` also
     * stops of its own accord while the tab is in the background, which `setInterval`
     * would not.
     */
    const PULSE = 1800
    const still = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false
    const working = () => laidOut.nodes.some(n => n.status === 'running')
    // Somebody who has asked not to see motion is still told, in the one way that does not
    // move: the halo is drawn once, held part way out, exactly as `.rb-q-running` keeps
    // its wash and drops its sweep.
    let beat = working() ? (still ? 0.45 : 0) : null
    let beating = null
    let painted = 0
    const tick = now => {
        if (!working()) { beating = null; return }
        beating = requestAnimationFrame(tick)
        if (now - painted < 60) return
        painted = now
        beat = (now % PULSE) / PULSE
        paint()
    }
    const keepTime = () => {
        if (still || !working() || beating !== null) return
        beating = requestAnimationFrame(tick)
    }

    /**
     * Take a node in hand, or let go of it.
     *
     * `lit` is everything the node reaches: everything it came from, however far back, and
     * everything made from it, however far on. There was a second, nearer set beside it,
     * what the node directly read and directly made, drawn stronger than the rest of the
     * chain. Steve, 7 September 2026: "the whole ancestry and descendents should be
     * highlighted, not just 1 generation away". So there is one answer now, and where a
     * workflow is a chain that answer is the whole chain, which is the truth about it.
     *
     * Two ids where the pointer is on an edge, since an edge has two ends and the chain
     * through it is both lineages.
     */
    const focusOn = (...ids) => {
        const wanted = ids.filter(id => id && named.has(id))
        if (!wanted.length) {
            lit = null
            return
        }
        lit = new Set()
        for (const id of wanted) {
            for (const other of lineageOf(laidOut, id)) lit.add(other)
        }
    }

    const paint = () => {
        // One viewport tall, measured from the scroller rather than from the window,
        // because the app bar and the caption are above it and `100vh` would run off the
        // bottom of the screen. The key under it takes its own height out, measured rather
        // than assumed, so a sticky column that has to fit the viewport still does. The
        // button under the key does the same where it is drawn, with the margins, padding
        // and border of the panel the map opens in there.
        const below = (key?.offsetHeight || 0)
            + (toggle?.offsetHeight ? toggle.offsetHeight + 26 : 0)
        canvas.style.height = `${Math.max(120, scroller.clientHeight - 24 - below)}px`
        // Hovering a block rings its node, and otherwise the ring is on the first block
        // on the screen, so it says where the reader is rather than flickering between
        // everything visible at once.
        const current = onBlock || onMap || order.find(id => here.has(id)) || null
        seats = draw(canvas, laidOut, { colours, here, lit, current, beat })
        canvas.dataset.current = current || ''
        // Where the nodes went, published because a canvas has nothing in it to aim at.
        // It is how a browser test clicks a node, and it is the only account of the map's
        // geometry anything outside this closure can get.
        const geometry = JSON.stringify([...seats].map(([id, s]) =>
            ({ id, x: Math.round(s.x), y: Math.round(s.y) })))
        if (geometry !== told) {
            canvas.dataset.nodes = geometry
            told = geometry
        }
        nameTheLit()
    }

    /**
     * Every lit node named, beside itself, while the pointer is on the map.
     *
     * Steve, 7 September 2026: at the moment of hovering, "the tooltips from those same
     * nodes should become visible to user as popovers or whatever". The map's own tooltip
     * is the browser's, one node at a time and only after a pause, so the chain you had
     * just lit was the one thing you could not read. A canvas has no elements to hang a
     * title on, so the names are drawn as their own layer over the document beside it.
     *
     * Names only, not the whole of `describe`: a lineage runs to a dozen nodes on an
     * ordinary workflow and a dozen three-line tooltips is a wall, not a reading. What a
     * node reads and makes stays on the browser tooltip of the one under the pointer.
     */
    const nameTheLit = () => {
        const layer = aside.querySelector('.rb-map-tips')
        if (!layer) return
        if (!lit || (!onMap && !onEdge)) { layer.replaceChildren(); return }
        // Down the map, so the greedy nudge below pushes labels apart in reading order.
        const seen = [...seats].filter(([id]) => lit.has(id))
            .sort((a, b) => a[1].y - b[1].y)
        let last = -Infinity
        const tips = seen.map(([id, seat]) => {
            // Labels are 15px apart at the least, which is what stops two nodes a rank
            // apart printing their names on top of each other.
            const y = Math.max(seat.y, last + 15)
            last = y
            const tip = document.createElement('span')
            tip.className = 'rb-map-tip'
            tip.style.top = `${Math.round(y)}px`
            tip.textContent = plain(id)
            if (id === onMap) tip.classList.add('rb-on')
            return tip
        })
        layer.replaceChildren(...tips)
    }

    /** The node the pointer is on, or nothing, which is a press on the map itself. */
    const nodeAt = event => {
        const box = canvas.getBoundingClientRect()
        const x = event.clientX - box.left
        const y = event.clientY - box.top
        let best = null
        let near = 11
        for (const [id, seat] of seats) {
            const d = Math.hypot(seat.x - x, seat.y - y)
            if (d < near) {
                near = d
                best = id
            }
        }
        return best
    }

    /**
     * The block a node stands for, or the nearest block that accounts for it.
     *
     * Not every node has a block of its own, and both cases are the document being right
     * rather than incomplete. It writes one step block per DECLARED step, so a fan-out
     * drawn as seven prongs on the map has one block behind all seven; and it writes an
     * asset block only for an asset that exists, so a workflow nobody has run has none at
     * all while the map still draws every result it will produce. Measured over the ten
     * workflows in `rubicon/workflows`: seven of the sixteen nodes on `rfa-theory-of-change`
     * and half the nodes on every unrun workflow had nothing to open, and a click on them
     * did nothing whatever. That is the invariants spec's "a button offering to open
     * something that opens nothing", on a surface it cannot reach to check.
     *
     * So a node falls back to whatever does account for it: a prong to the step it is a
     * prong of, a result to the step that will make it, and failing that to a step that
     * reads it. Breadth-first over those, since the first hop may have no block either.
     */
    const madeBy = new Map()
    const readBy = new Map()
    for (const e of laidOut.edges) {
        if (e.to.startsWith('asset:')) madeBy.set(e.to, e.from)
        else if (!readBy.has(e.from)) readBy.set(e.from, e.to)
    }
    const blockFor = id => {
        const seen = new Set()
        const tries = [id]
        while (tries.length) {
            const want = tries.shift()
            if (!want || seen.has(want)) continue
            seen.add(want)
            const block = root.querySelector(`.rb-block[data-node="${CSS.escape(want)}"]`)
            if (block) return block
            const prong = want.indexOf('[')
            if (prong > 0) tries.push(want.slice(0, prong))
            if (madeBy.has(want)) tries.push(madeBy.get(want))
            if (readBy.has(want)) tries.push(readBy.get(want))
        }
        return null
    }

    /**
     * Scroll by `by`, easing in and out so the reader sees the page move and which way,
     * rather than finding it already somewhere else. A new glide replaces one under way;
     * a reader who asks for less motion gets the jump.
     */
    let gliding = 0
    const glide = by => {
        cancelAnimationFrame(gliding)
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
            scroller.scrollTop += by
            return
        }
        const from = scroller.scrollTop
        const span = Math.min(700, 300 + Math.abs(by) / 6)
        const start = performance.now()
        const step = now => {
            const t = Math.min(1, (now - start) / span)
            scroller.scrollTop = from + by * (t < 0.5 ? 4 * t ** 3 : 1 - (2 - 2 * t) ** 3 / 2)
            if (t < 1) gliding = requestAnimationFrame(step)
        }
        gliding = requestAnimationFrame(step)
    }

    /**
     * Take the reader to the block a node stands for.
     *
     * The folds are why the scrolling needs saying: a step arrives shut, so its block and
     * everything nested in it has no height, and scrolling to one lands on whatever
     * happens to be at that scroll position instead. So the fold the block is in is opened
     * first, and its own, and only then is anything measured.
     */
    const goTo = id => {
        const block = blockFor(id)
        if (!block) return false
        for (let fold = block.parentElement?.closest('details'); fold;
             fold = fold.parentElement?.closest('details')) fold.open = true
        const own = block.querySelector(':scope > details')
        if (own) own.open = true
        const seat = block.getBoundingClientRect()
        const view = viewOf(scroller)
        const lift = seat.height < view.height
            ? (view.height - seat.height) / 2
            : view.height / 3
        glide(seat.top - view.top - lift)
        // Removed and re-added so a second visit to the same block fades again rather
        // than sitting there already marked.
        block.classList.remove('rb-found')
        void block.offsetWidth
        block.classList.add('rb-found')
        return true
    }

    const holding = new AbortController()
    const on = { signal: holding.signal }

    const plain = id => (named.get(id)?.label || id).replace(/\n/g, ' · ')

    /**
     * What a node is, and what it rests on, in words.
     *
     * The same fact the highlight draws, said where the pointer already is. A step reads
     * results and makes results; an asset was made by a step and is read by steps. Naming
     * them is the whole of Steve's question: a verdict does not depend on step 3, it
     * depends on the table step 3 produced, and now the map says so.
     */
    const describe = id => {
        const n = named.get(id)
        if (!n) return ''
        const { before, after } = neighboursOf(laidOut, id)
        const said = n.kind === 'step'
            ? [['reads', before], ['makes', after]]
            : n.kind === 'run' ? [['took from', before], ['gave', after]]
            : [['made by', before], ['read by', after]]
        const was = n.kind === 'step' ? n.status : n.kind === 'run' ? 'not this run'
            : n.missing ? 'not made yet' : n.upstream ? 'made by an earlier run' : 'result'
        return [`${plain(id)} — ${was}`,
            ...said.filter(([, ids]) => ids.length)
                .map(([word, ids]) => `${word} ${ids.map(plain).join(', ')}`)].join('\n')
    }

    /** The edge the pointer is on, where it is not on a node. */
    const edgeUnder = event => {
        const box = canvas.getBoundingClientRect()
        return edgeAt(laidOut, seats,
            event.clientX - box.left, event.clientY - box.top)
    }

    canvas.addEventListener('mousemove', event => {
        const id = nodeAt(event)
        // An edge is aimable too, and lights the chain through both of its ends. Steve, 7
        // September 2026: "on mouse over node or edge in margin map".
        const edge = id ? null : edgeUnder(event)
        const aimed = edge ? `${edge.from}->${edge.to}` : null
        if (id === onMap && aimed === onEdge) return
        onMap = id
        onEdge = aimed
        canvas.style.cursor = id || edge ? 'pointer' : ''
        canvas.title = id ? describe(id)
            : edge ? `${plain(edge.from)} → ${plain(edge.to)}` : ''
        if (edge) focusOn(edge.from, edge.to)
        else focusOn(id)
        paint()
    }, on)
    // Opening or shutting the key changes how much room the map has, and the height is
    // worked out in `paint` from what the key actually measures.
    key?.addEventListener('toggle', () => paint(), on)
    // Painted as it opens: put away, the canvas had no size, so nothing drawn then is on it.
    // Shut, the lineage a tap lit is let go, or it would still be lit the next time.
    const showMap = open => {
        markOpen(open)
        if (!open) {
            onMap = null
            onEdge = null
            focusOn(onBlock)
        }
        paint()
    }
    toggle?.addEventListener('click', () => showMap(!mapOpen), on)

    canvas.addEventListener('mouseleave', () => {
        if (onMap === null && onEdge === null && lit === null) return
        onMap = null
        onEdge = null
        canvas.title = ''
        // Back to whatever the pointer left behind in the document, so crossing from the
        // map onto the block it points at does not blank the answer on the way.
        focusOn(onBlock)
        paint()
    }, on)
    canvas.addEventListener('click', event => {
        const id = nodeAt(event)
        if (!id) return
        // A result opens the result. Steve, 7 September 2026: "when we click on a node in
        // margin map to open a result, we should open the result itself not just the step
        // section in canvas." Scrolled to as well, so the document behind the box is at
        // the place the node stands for when it is shut.
        const node = named.get(id)
        goTo(id)
        // Where the map lies over the document, it gets out of the way of the place it
        // has just sent the reader to.
        if (toggle?.offsetParent && mapOpen) showMap(false)
        opened(node, id)
    }, on)

    // Press and drag on the map to scrub. To the block
    // at that height rather than to that fraction of the scroll: the rows are ranks, so
    // two thirds down the map means the block two thirds through the workflow, which is a
    // different place from two thirds down a document whose blocks are all different
    // heights. Only the blocks actually showing count, since a shut fold's contents are
    // not somewhere a reader can be sent.
    let scrubbing = false
    const scrubTo = event => {
        const box = canvas.getBoundingClientRect()
        const at = Math.min(1, Math.max(0, (event.clientY - box.top) / Math.max(1, box.height)))
        const shown = blocks().filter(b => b.offsetParent !== null)
        const wanted = shown[Math.round(at * (shown.length - 1))]
        if (!wanted) return
        const seat = wanted.getBoundingClientRect()
        const view = viewOf(scroller)
        scroller.scrollTop += seat.top - view.top - view.height / 3
    }
    canvas.addEventListener('mousedown', event => {
        // Aiming at a node is the more particular act, so a press on one is left to the
        // click handler above rather than being read as the start of a scrub.
        if (nodeAt(event)) return
        scrubbing = true
        scrubTo(event)
        event.preventDefault()
    }, on)
    window.addEventListener('mousemove', event => { if (scrubbing) scrubTo(event) }, on)
    window.addEventListener('mouseup', () => { scrubbing = false }, on)

    // And the mirror: the pointer on a block rings that block's node. Delegated, because
    // there is one listener here and a block per step, per result and per prong. A block
    // inside an earlier run's fold rings that run, which is the node the map has for it.
    root.addEventListener('mouseover', event => {
        const block = event.target?.closest?.('.rb-block[data-node]')
        const node = block?.dataset.node || null
        const id = node?.startsWith('run:') && node.includes('/')
            ? `run:${node.slice('run:'.length).split('/')
                .filter(part => !/^(step|asset):/.test(part)).at(-1)}` : node
        if (id === onBlock) return
        onBlock = id
        // The mirror, and it now carries the same answer both ways: the pointer on the
        // verdict in the document lights the two results it was reached from, exactly as
        // the pointer on the verdict's node does.
        if (!onMap && !onEdge) focusOn(id)
        paint()
    }, on)
    root.addEventListener('mouseleave', () => {
        if (onBlock === null) return
        onBlock = null
        if (!onMap && !onEdge) focusOn(null)
        paint()
    }, on)

    const watching = new IntersectionObserver(entries => {
        for (const entry of entries) {
            const id = entry.target.dataset.node
            if (entry.isIntersecting) here.add(id)
            else here.delete(id)
        }
        paint()
    }, { root: scroller === document.scrollingElement ? null : scroller, threshold: 0 })
    blocks().forEach(b => watching.observe(b))

    const resized = new ResizeObserver(paint)
    resized.observe(scroller)
    owned(() => {
        watching.disconnect()
        resized.disconnect()
        holding.abort()
        // The document is redrawn every few seconds while a run is going, so a frame
        // left asked for here would leave one more loop painting a canvas nobody can
        // see for every tick of the watcher.
        if (beating !== null) cancelAnimationFrame(beating)
        beating = null
    })
    paint()
    keepTime()

    // Which block each node opens, published once so a browser test can assert that none
    // of them opens nothing. Once rather than on every paint, because it is a DOM query
    // per node and the blocks a document has do not change while it is being read; folds
    // open and shut, which is a different thing. It reads `blockFor`'s answer rather than
    // working the rule out again, so a test cannot pass against a rule the page has
    // stopped following.
    canvas.dataset.nodeBlocks = JSON.stringify(Object.fromEntries(
        laidOut.nodes.map(n => [n.id, blockFor(n.id)?.dataset.node || null])))
}