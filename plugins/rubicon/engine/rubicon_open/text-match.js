/**
 * Pure quote-to-source locator shared by the source-text highlight overlay and AI
 * link insertion. No DOM, no app/state/DataService dependencies: data in, data out.
 *
 * locateQuote(sourceText, selectedText) returns { start, end, confidence } with absolute
 * offsets into sourceText, or null when the quote cannot be located. confidence is:
 *   'exact'     literal / whitespace-normalised match
 *   'canonical' unicode + punctuation tolerant match (curly quotes, ligatures, accents,
 *               zero-width chars, and dropped/added commas etc.)
 *   'gapped'    every character of the quote appears, in order, as verbatim runs of the source,
 *               but the source interleaves extra material the quote skips over. This is the
 *               interview case: the interviewer backchannels mid-sentence ("Causal Map: Yeah.")
 *               and the transcript splits the speaker's sentence across turns, so a correct
 *               quote of what the speaker said is not a contiguous substring. start/end span
 *               the whole region, interruption included, so the snapped text is still verbatim
 *               source. Treat as trustworthy: the gaps are source material, not invention.
 *   'fuzzy'     bounded approximate match (a few stray characters); treat as low trust
 * Callers decide policy: e.g. snap to source on exact/canonical/gapped, flag on fuzzy, skip on null.
 *
 * createQuoteLocator(sourceText) returns { locate(selectedText) } with identical behaviour but
 * caches the normalised/canonical views of the source across calls. Use it when matching many
 * quotes against one source (e.g. AI writeback), where per-call locateQuote re-canonicalises
 * the whole source each time.
 */

// Build a whitespace-normalised view of s plus an index map back to original offsets
// (out[i] came from s[map[i]]). Collapses runs of whitespace to one space, trims ends.
function normalizeWhitespaceWithMap(s) {
    let out = ''
    const map = []
    let seenNonWs = false
    let inWs = false
    for (let i = 0; i < s.length; i++) {
        const ch = s[i]
        if (/\s/.test(ch)) {
            if (!seenNonWs) continue
            if (inWs) continue
            out += ' '
            map.push(i)
            inWs = true
        } else {
            seenNonWs = true
            inWs = false
            out += ch
            map.push(i)
        }
    }
    if (out.endsWith(' ')) { out = out.slice(0, -1); map.pop() }
    return { out, map }
}

// Canonicalise for matching with an index map back to original offsets. Folds quote, dash
// and space variants, drops zero-width / soft-hyphen / BOM chars, NFKD-folds ligatures and
// accents, lowercases, collapses whitespace and dot runs. With dropPunct, also removes
// non-alphanumeric punctuation so a dropped/added comma still matches (offsets stay correct).
function canonicalizeWithMap(s, dropPunct) {
    let out = ''
    const map = [] // out[i] came from s[map[i]]
    let seenNonWs = false
    let inWs = false
    const append = (ch, originalIdx) => {
        // Collapse runs of dots ('.', '...', ellipsis) to a single '.'
        if (ch === '.' && out.length > 0 && out[out.length - 1] === '.') return
        out += ch
        map.push(originalIdx)
    }
    for (let i = 0; i < s.length; i++) {
        let ch = s[i]

        // Drop zero-width / soft-hyphen / BOM / word-joiner characters entirely.
        if (/[\u00AD\u180E\u200B\u200C\u200D\u2060\uFEFF]/.test(ch)) continue

        // Fold punctuation variants to stable ASCII forms.
        if (ch === '\u2018' || ch === '\u2019' || ch === '\u201A' || ch === '\u201B' || ch === '\u2032' || ch === '\u02B9' || ch === '\u02BC' || ch === '\u0060' || ch === '\u00B4') ch = "'"
        else if (ch === '\u201C' || ch === '\u201D' || ch === '\u201E' || ch === '\u201F' || ch === '\u2033' || ch === '\u00AB' || ch === '\u00BB' || ch === '\u2039' || ch === '\u203A') ch = '"'
        else if (ch === '\u2026') ch = '.'
        else if (ch === '\u2010' || ch === '\u2011' || ch === '\u2012' || ch === '\u2013' || ch === '\u2014' || ch === '\u2015' || ch === '\u2212' || ch === '\u2043') ch = '-'
        else if (ch === '\u00A0' || ch === '\u2007' || ch === '\u202F' || ch === '\u205F' || ch === '\u3000' || ch === '\u1680' || (ch >= '\u2000' && ch <= '\u200A')) ch = ' '

        if (/\s/.test(ch)) {
            if (!seenNonWs) continue // trim leading
            if (inWs) continue       // collapse runs
            out += ' '
            map.push(i)
            inWs = true
            continue
        }
        seenNonWs = true
        inWs = false

        // Fold accents/ligatures/width via NFKD, strip combining marks, lowercase.
        let folded
        try {
            folded = ch.normalize('NFKD').replace(/[\u0300-\u036F]/g, '')
        } catch (_) {
            folded = ch
        }
        for (const fc of folded.toLowerCase()) {
            if (/\s/.test(fc)) continue // NFKD can introduce spaces; keep the map 1:1
            if (dropPunct && !/[\p{L}\p{N}]/u.test(fc)) continue // punctuation-insensitive pass
            append(fc, i)
        }
    }
    if (out.endsWith(' ')) { out = out.slice(0, -1); map.pop() }
    return { out, map }
}

// Count of differing characters; length difference is penalised heavily (no indel alignment).
// Bails out early once differences exceed limit (the caller only cares about <= limit).
function simpleDistance(str1, str2, limit) {
    if (str1.length !== str2.length) {
        return Math.abs(str1.length - str2.length) + Math.min(str1.length, str2.length)
    }
    let differences = 0
    for (let i = 0; i < str1.length; i++) {
        if (str1[i] !== str2[i] && ++differences > limit) return differences
    }
    return differences
}

// Greedy alignment of `needle` onto `hay` from `from`, allowing the SOURCE to interleave extra
// material (see the 'gapped' confidence). Returns {start, end} in hay coordinates, or null.
// Every needle character must be matched, in order, so this cannot accept invented text.
function scanGapped(needle, hay, from, resync, maxGap, maxGaps, maxTotalGap, tailSlack) {
    const MIN_RUN = 4 // a run this short is coincidence (the 'c' of "could" hitting the 'C' of
                      // "Causal Map"), not a real continuation: resync past it instead of
                      // committing it, or the span ends inside the interruption.
    let i = 0
    let pos = from
    let gaps = 0
    let totalGap = 0
    let end = null
    while (i < needle.length) {
        let run = 0
        while (i + run < needle.length && pos + run < hay.length && needle[i + run] === hay[pos + run]) run++
        const finishesNeedle = run > 0 && i + run >= needle.length
        if (run >= MIN_RUN || finishesNeedle) {
            i += run
            pos += run
            end = pos
            if (i >= needle.length) break
        }
        // Mismatch (or a run too short to trust): the source has extra material here. Resync on
        // the next chunk of the quote; charge the skipped source to the gap budget.
        const rest = needle.length - i
        const probe = needle.slice(i, i + Math.min(resync, rest))
        const next = hay.indexOf(probe, pos)
        if (next === -1 || next - pos > maxGap) {
            // Only an unmatched tail this short is tolerated (models sometimes clip a final word).
            return (rest <= tailSlack && end !== null) ? { start: from, end } : null
        }
        if (++gaps > maxGaps) return null
        totalGap += next - pos
        if (totalGap > maxTotalGap) return null
        pos = next
        if (rest <= resync) {
            // The tail resynced: consume it and finish.
            i += rest
            pos += rest
            end = pos
            break
        }
    }
    return end === null ? null : { start: from, end }
}

// Reusable locator for matching many quotes against ONE source text: the normalised and
// canonical views of the source (the expensive part) are computed lazily and cached across
// calls, instead of being rebuilt for every quote as locateQuote does.
// opts.wideGap widens the 'gapped' strategy so the verbatim runs of a quote may be ANY distance
// apart in the source (still in order, every character matched — nothing invented). It is for the
// connect-islands pass, whose quotes deliberately stitch fragments from across a whole document to
// evidence a cross-island link; the default (narrow) budget is tuned for an interview interruption
// and stays in force for the transcript writeback and everywhere else.
export function createQuoteLocator(sourceText, opts = {}) {
    const src = sourceText ? String(sourceText) : ''
    const wideGap = !!(opts && opts.wideGap)
    const lowerSource = src.toLowerCase()
    let normWs = null        // normalizeWhitespaceWithMap(lowerSource)
    let canon = null         // canonicalizeWithMap(src, false)
    let canonNoPunct = null  // canonicalizeWithMap(src, true)

    function locate(selectedText) {
        if (!src || !selectedText) return null
        const strippedSelected = String(selectedText).replace(/\s+/g, ' ').trim()
        if (!strippedSelected || strippedSelected.length < 3) return null
        const lowerSelected = strippedSelected.toLowerCase()

        // Strategy 1: case-insensitive literal match.
        const literalIndex = lowerSource.indexOf(lowerSelected)
        if (literalIndex !== -1) {
            return { start: literalIndex, end: literalIndex + strippedSelected.length, confidence: 'exact' }
        }

        // Strategy 1a: whitespace-normalised literal (handles newlines / runs of spaces).
        {
            if (!normWs) normWs = normalizeWhitespaceWithMap(lowerSource)
            const normSelected = lowerSelected.replace(/\s+/g, ' ').trim()
            const idx = normSelected.length > 0 ? normWs.out.indexOf(normSelected) : -1
            if (idx !== -1) {
                return { start: normWs.map[idx], end: normWs.map[idx + normSelected.length - 1] + 1, confidence: 'exact' }
            }
        }

        // Strategy 1b: unicode/punctuation-tolerant canonical match (quotes, dashes, ligatures, accents).
        {
            if (!canon) canon = canonicalizeWithMap(src, false)
            const { out: cSel } = canonicalizeWithMap(strippedSelected, false)
            const idx = cSel.length > 0 ? canon.out.indexOf(cSel) : -1
            if (idx !== -1) {
                return { start: canon.map[idx], end: canon.map[idx + cSel.length - 1] + 1, confidence: 'canonical' }
            }
        }

        // Strategy 1c: punctuation-insensitive canonical (tolerates a dropped/added comma etc.).
        // Length guards avoid false positives on short fragments.
        if (strippedSelected.length >= 8) {
            if (!canonNoPunct) canonNoPunct = canonicalizeWithMap(src, true)
            const { out: pSel } = canonicalizeWithMap(strippedSelected, true)
            if (pSel.length >= 6) {
                const idx = canonNoPunct.out.indexOf(pSel)
                if (idx !== -1) {
                    return { start: canonNoPunct.map[idx], end: canonNoPunct.map[idx + pSel.length - 1] + 1, confidence: 'canonical' }
                }
            }
        }

        // Strategy 1d: gapped match — the quote is a concatenation of verbatim source runs, with
        // extra source material skipped between them (see 'gapped' in the header). Greedy scan on
        // the punctuation-insensitive view: consume a matching run, then resync on the next
        // RESYNC chars of the quote, charging the skipped source to a gap budget. Every quote
        // character must be accounted for, so invented text cannot pass; only the source may have
        // extra. Cheap: one indexOf per gap, no windowed rescan (the writeback runs this per link
        // and has already hit the edge CPU limit once).
        if (strippedSelected.length >= 25) {
            if (!canonNoPunct) canonNoPunct = canonicalizeWithMap(src, true)
            const { out: gSel } = canonicalizeWithMap(strippedSelected, true)
            const hay = canonNoPunct.out
            const RESYNC = 16          // chars of quote used to re-find the source after a gap
            // wideGap: the connect-islands pass quotes fragments from ANYWHERE in the document, in
            // order, to evidence a cross-island link, so its runs can be far apart. The run/resync
            // floors (MIN_RUN, RESYNC, the >=25-char quote guard) are unchanged, so every character is
            // still matched verbatim in order — only the distance BETWEEN runs is opened up.
            const MAX_GAP = wideGap ? src.length : 300        // one interruption (unbounded when wide)
            const MAX_GAPS = wideGap ? 40 : 12
            const TAIL_SLACK = 8       // unmatched tail shorter than this is tolerated
            const maxTotalGap = wideGap ? src.length : Math.min(800, gSel.length)
            if (gSel.length >= 25) {
                // Anchor on the quote's first RESYNC chars, not a longer head: an interruption can
                // fall within the first few words ("repurpose some of that <Causal Map: Yeah.>
                // policy support fund…"), and a 25-char head then straddles the gap, so it never
                // occurs contiguously in the source and the whole gapped scan is abandoned — the
                // early-backchannel case the tier exists for. RESYNC (the same run trusted for
                // every mid-scan resync) is short enough to sit before an early interruption yet
                // specific enough to anchor; scanGapped still matches every later char in order.
                // The first ANCHORS occurrences are tried, in case an early false anchor (a
                // repeated phrase) would strand the scan.
                const ANCHORS = 5
                const head = gSel.slice(0, RESYNC)
                let anchor = hay.indexOf(head)
                for (let a = 0; a < ANCHORS && anchor !== -1; a++) {
                    const hit = scanGapped(gSel, hay, anchor, RESYNC, MAX_GAP, MAX_GAPS, maxTotalGap, TAIL_SLACK)
                    if (hit) {
                        return {
                            start: canonNoPunct.map[hit.start],
                            end: canonNoPunct.map[hit.end - 1] + 1,
                            confidence: 'gapped',
                        }
                    }
                    anchor = hay.indexOf(head, anchor + 1)
                }
            }
        }

        // Strategy 2: bounded fuzzy scan for a few stray characters. Approximate, so low trust.
        if (strippedSelected.length > 1000) return null
        const maxDistance = Math.min(5, Math.floor(strippedSelected.length * 0.05))
        for (let i = 0; i <= src.length - strippedSelected.length; i += 5) {
            const window = src.substring(i, i + strippedSelected.length)
            if (simpleDistance(window.toLowerCase(), lowerSelected, maxDistance) <= maxDistance) {
                return { start: i, end: i + strippedSelected.length, confidence: 'fuzzy' }
            }
        }
        return null
    }

    return { locate }
}

export function locateQuote(sourceText, selectedText) {
    return createQuoteLocator(sourceText).locate(selectedText)
}

// Convenience: offsets only (back-compat shape for callers that ignore confidence).
export function findQuoteOffsets(sourceText, selectedText) {
    const r = locateQuote(sourceText, selectedText)
    return r ? { start: r.start, end: r.end } : null
}
