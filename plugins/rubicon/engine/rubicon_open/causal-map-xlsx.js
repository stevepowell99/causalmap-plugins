/**
 * A run's coded causal links, and the documents they come from, as a workbook Causal Map's Import XLSX reads
 * (`importProjectFromXLSX` in webapp/js/project-manager.js): a `sources` sheet, a `links` sheet, and for a document
 * longer than one spreadsheet cell holds, a `source_content_chunks` sheet with the marker the importer looks for.
 *
 * The report runs this in the reader's browser when a "Download for Causal Map" button is pressed (render_report.py
 * inlines it beside report.js, with link-rows.js, whose `linksOfRows` is the one place a row becomes links), so the
 * workbook is made from what the report already carries and nothing is sent anywhere. It imports nothing and writes
 * the zip itself, stored rather than compressed, so it needs no library.
 */

/** The most characters the importer takes in a sources cell before it wants the text split (project-manager.js) */
export const CELL_CHARS = 32000
export const LONG_TEXT = 'LONG TEXT - split into source_content_chunks tab'
/** Columns the importer reads as a link's own fields; a coded column of the same name is renamed so it is kept */
const LINK_FIELDS = new Set(['id', 'project_name', 'cause', 'effect', 'sentiment', 'tags', 'source_id', 'selected_text',
    'created_at', 'updated_at', 'metadata', 'package', 'package_type'])
const SOURCE_FIELDS = new Set(['id', 'source_id', 'title', 'content', 'text', 'filename', 'project_name', 'projectname',
    'type', 'size', 'metadata', 'created_at', 'updated_at', 'source_prompt'])

const cellText = v => (Array.isArray(v) ? v.join(', ') : v == null ? '' : String(v))
const keep = (name, taken) => (taken.has(String(name).toLowerCase()) ? `rubicon_${name}` : name)

/**
 * The workbook's sheets as rows of cells, before any XML: what the tests read.
 *   rows:  [{ row, document, step, quote, sentiment, codes: {column: value} }]
 *   ends:  { <code step>: { from, to, sign } }, the columns that are a link's two ends and its sign
 *   docs:  { <id>: { title, file, facts: {column: value} } }
 *   texts: { <id>: the document's text as the run read it }, or no entry where the text is not to hand
 */
export function causalMapSheets({ rows, ends, docs, texts }, linksOfRows) {
    const links = []
    const extra = []
    for (const r of rows) {
        const e = ends[r.step]
        if (!e) continue
        const flat = { row: r.row, document: r.document, ...r.codes }
        for (const l of linksOfRows([flat], { from: e.from, to: e.to })) {
            const out = { cause: l.cause, effect: l.effect, sentiment: r.sentiment || 0, source_id: r.document,
                selected_text: r.quote, rubicon_row: r.row, rubicon_step: r.step }
            for (const [k, v] of Object.entries(r.codes)) {
                if (k === e.from || k === e.to) continue
                const name = keep(k, LINK_FIELDS)
                if (!extra.includes(name)) extra.push(name)
                out[name] = cellText(v)
            }
            links.push(out)
        }
    }
    const used = [...new Set(rows.filter(r => ends[r.step]).map(r => r.document))].sort()
    const facts = []
    for (const d of used) for (const k of Object.keys(docs[d]?.facts || {})) if (!facts.includes(keep(k, SOURCE_FIELDS))) facts.push(keep(k, SOURCE_FIELDS))
    const sources = []
    const chunks = []
    for (const d of used) {
        const doc = docs[d] || {}
        const text = texts[d] ?? ''
        const row = { id: d, title: doc.title || d, content: text.length > CELL_CHARS ? LONG_TEXT : text,
            filename: String(doc.file || '').replace(/^corpus\//, '') }
        for (const [k, v] of Object.entries(doc.facts || {})) row[keep(k, SOURCE_FIELDS)] = cellText(v)
        sources.push(row)
        if (text.length > CELL_CHARS) {
            for (let i = 0, n = 0; i < text.length; i += CELL_CHARS, n++) chunks.push({ source_id: d, chunk_index: n, content_chunk: text.slice(i, i + CELL_CHARS) })
        }
    }
    const sheets = [
        { name: 'sources', columns: ['id', 'title', 'content', 'filename', ...facts], rows: sources },
        { name: 'links', columns: ['cause', 'effect', 'sentiment', 'source_id', 'selected_text', 'rubicon_row', 'rubicon_step', ...extra], rows: links },
    ]
    if (chunks.length) sheets.push({ name: 'source_content_chunks', columns: ['source_id', 'chunk_index', 'content_chunk'], rows: chunks })
    return sheets
}

// ---------- the .xlsx file: a zip of SpreadsheetML ----------

const xml = s => String(s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g, '')
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const colName = i => (i >= 26 ? colName(Math.floor(i / 26) - 1) : '') + String.fromCharCode(65 + (i % 26))

function sheetXml({ columns, rows }) {
    const cell = (v, ref) => (typeof v === 'number' && Number.isFinite(v)
        ? `<c r="${ref}"><v>${v}</v></c>`
        : `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xml(v ?? '')}</t></is></c>`)
    const line = (vals, n) => `<row r="${n}">${vals.map((v, i) => cell(v, colName(i) + n)).join('')}</row>`
    const body = [line(columns, 1), ...rows.map((r, i) => line(columns.map(c => r[c] ?? ''), i + 2))].join('')
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${body}</sheetData></worksheet>`
}

function parts(sheets) {
    const ns = 'http://schemas.openxmlformats.org'
    const sheetRel = `${ns}/officeDocument/2006/relationships/worksheet`
    return [
        ['[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="${ns}/package/2006/content-types">`
            + '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            + '<Default Extension="xml" ContentType="application/xml"/>'
            + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + sheets.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')
            + '</Types>'],
        ['_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="${ns}/package/2006/relationships">`
            + `<Relationship Id="rId1" Type="${ns}/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`],
        ['xl/workbook.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="${ns}/spreadsheetml/2006/main" xmlns:r="${ns}/officeDocument/2006/relationships"><sheets>`
            + sheets.map((s, i) => `<sheet name="${xml(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('') + '</sheets></workbook>'],
        ['xl/_rels/workbook.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="${ns}/package/2006/relationships">`
            + sheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${sheetRel}" Target="worksheets/sheet${i + 1}.xml"/>`).join('')
            + `<Relationship Id="rId${sheets.length + 1}" Type="${ns}/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
        ['xl/styles.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="${ns}/spreadsheetml/2006/main">`
            + '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            + '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf/></cellXfs></styleSheet>'],
        ...sheets.map((s, i) => [`xl/worksheets/sheet${i + 1}.xml`, sheetXml(s)]),
    ]
}

let crcTable = null
function crc32(bytes) {
    if (!crcTable) {
        crcTable = new Uint32Array(256)
        for (let n = 0; n < 256; n++) {
            let c = n
            for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1
            crcTable[n] = c >>> 0
        }
    }
    let c = 0xFFFFFFFF
    for (const b of bytes) c = crcTable[(c ^ b) & 0xFF] ^ (c >>> 8)
    return (c ^ 0xFFFFFFFF) >>> 0
}

/** Files into a zip, stored, each dated 1 January 1980 so the same sheets always make the same bytes. */
function zip(files) {
    const enc = new TextEncoder()
    const local = [], central = []
    let at = 0
    for (const [name, text] of files) {
        const n = enc.encode(name), data = enc.encode(text), crc = crc32(data)
        const head = new DataView(new ArrayBuffer(30))
        head.setUint32(0, 0x04034b50, true); head.setUint16(4, 20, true); head.setUint16(6, 0x0800, true)
        head.setUint16(12, 0x21, true); head.setUint32(14, crc, true)
        head.setUint32(18, data.length, true); head.setUint32(22, data.length, true); head.setUint16(26, n.length, true)
        const dir = new DataView(new ArrayBuffer(46))
        dir.setUint32(0, 0x02014b50, true); dir.setUint16(4, 20, true); dir.setUint16(6, 20, true); dir.setUint16(8, 0x0800, true)
        dir.setUint16(14, 0x21, true); dir.setUint32(16, crc, true)
        dir.setUint32(20, data.length, true); dir.setUint32(24, data.length, true); dir.setUint16(28, n.length, true)
        dir.setUint32(42, at, true)
        local.push(new Uint8Array(head.buffer), n, data)
        central.push(new Uint8Array(dir.buffer), n)
        at += 30 + n.length + data.length
    }
    const size = central.reduce((s, b) => s + b.length, 0)
    const end = new DataView(new ArrayBuffer(22))
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true)
    end.setUint32(12, size, true); end.setUint32(16, at, true)
    const all = [...local, ...central, new Uint8Array(end.buffer)]
    const out = new Uint8Array(all.reduce((s, b) => s + b.length, 0))
    let p = 0
    for (const b of all) { out.set(b, p); p += b.length }
    return out
}

/** The workbook's bytes. */
export function causalMapWorkbook(input, linksOfRows) {
    return zip(parts(causalMapSheets(input, linksOfRows)))
}
