// Locate quotes in a source text with THE production matcher, and return offsets.
//
// scripts/quote_verify.mjs already exists and returns the tier alone, which is all
// prompt_ab_test.py needs to score a prompt. Rubicon stores text_start_offset and
// text_end_offset, so it needs the positions too. Rather than widen the shared
// script's contract while other work is in flight, this is a second thin caller of
// the SAME single-source matcher, exactly as ai-writeback imports it.
//
// One locator per source, never one per quote: the per-quote form blew the edge
// function's CPU limit on long sources.
//
// stdin:  {"sourceText": "...", "quotes": ["...", ...], "wideGap": false}
// stdout: {"results": [{"tier":"exact","start":12,"end":40} | null, ...]}
import { createQuoteLocator } from './text-match.js'

let raw = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) raw += chunk
const { sourceText, quotes, wideGap } = JSON.parse(raw)
const locator = createQuoteLocator(sourceText, wideGap ? { wideGap: true } : undefined)
const results = (quotes || []).map((q) => {
  const s = String(q ?? '').trim()
  if (!s) return null
  const m = locator.locate(s)
  if (!m || !m.confidence || m.confidence === 'none') return null
  return { tier: m.confidence, start: m.start, end: m.end }
})
process.stdout.write(JSON.stringify({ results }))
