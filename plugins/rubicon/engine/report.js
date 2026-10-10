(() => {
  const panel = document.getElementById('panel');
  const pbody = document.getElementById('panel-body');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // A count with its unit, "2 of 18 households", or "1 passage" where it has no base: the twin of count_said in
  // rubicon_open/units.py, which tests/rubicon-open-units-twin.test.mjs holds it to
  function countSaid(n, base, noun) {
    const one = k => (k === 1 && ['cases', 'documents', 'passages'].includes(noun) ? noun.slice(0, -1) : noun);
    return base == null ? `${n} ${one(n)}` : `${n} of ${base} ${one(base)}`;
  }
  // A value as a reader sees it (render_report.label says the same). A factor's opposite pole keeps its leading ~, as
  // Causal Map writes it ("~Hygiene and sanitation"), and `named` marks that ~ wherever a page names a coded value; the
  // leading # Causal Map's export puts on a document's column is dropped
  const label = v => {
    const s = String(v).replace(/_/g, ' ').trim().replace(/^#\s*/, ''), pole = s.startsWith('~'), t = pole ? s.slice(1).trim() : s;
    return (pole ? '~' : '') + t.charAt(0).toUpperCase() + t.slice(1);
  };
  // A coded value as HTML, with an opposite pole's ~ marked: pointing at it, tabbing to it or tapping it opens the
  // popover below, which says what the pole means (render_report.named draws the same mark)
  const named = (v, col = '') => {
    const words = label(v);
    if (!words.startsWith('~')) return esc(words);
    return `<span class="tilde" tabindex="0" role="button" data-code="${esc(String(v).trim())}" data-col="${esc(col)}" ` +
      `aria-label="The opposite of ${esc(words.slice(1))}">~</span>${esc(words.slice(1))}`;
  };
  // a document's group, named with its column, since a value alone ("No") does not say what it is a value of
  const group = d => (RUN.docs[d] && RUN.docs[d].group) ? (RUN.group ? label(RUN.group) + ': ' : '') + label(RUN.docs[d].group) : '';

  const coded = codes => Object.entries(codes).filter(([, v]) => v != null && v !== '');
  const isPole = v => /^~/.test(String(v));
  const stepName = s => label(s.replace(/^c_/, ''));
  // a step as the annex heads it, its kind in words then its name (render_report.step_said)
  const stepSaid = s => (RUN.steps && RUN.steps[s]) || label(s);
  const andList = xs => xs.length < 2 ? xs.join('') : xs.slice(0, -1).join(', ') + ' and ' + xs[xs.length - 1];
  const times = n => n === 1 ? 'once' : n === 2 ? 'twice' : `${n} times`;
  // A passage's codes as chips, each opening every passage given the same code in that step (showCode), from the keys
  // render_report.build_data gives each row; `still` draws them as plain chips, for the tip, which nothing can click
  function codes(r, still) {
    const keys = r.keys || {};
    return '<div class="codes">' + coded(r.codes).map(([k, v]) => {
      const words = `${esc(label(k))}: ${named(v, k)}`, title = esc(RUN.defs[k + '=' + v] || '');
      return !still && RUN.codes && RUN.codes[keys[k]] ? `<button class="code" data-code="${esc(keys[k])}" title="${title}">${words}</button>`
        : `<span title="${title}">${words}</span>`;
    }).join('') + '</div>';
  }
  // How one passage was coded: the step, whether it counts or was only hinted at, its codes, and what the second
  // coder, coding blind, made of the same place: agreed, did not code it, or only the codes they gave it otherwise
  // (render_report.second_reading, which compares the values)
  function coding(id, still) {
    const r = RUN.rows[id];
    if (!r) return '';
    const s = r.second;
    let second = '';
    if (s) {
      const differ = Object.entries(s.differ);
      const said = !s.coded ? 'did not code this passage'
        : !differ.length ? 'agreed'
        : differ.map(([c, theirs]) => `${esc(label(c))}: ${theirs.length ? theirs.map(x => named(x, c)).join(' or ') : 'not coded'} instead of ${named(r.codes[c], c)}`).join('; ');
      second = `<p class="second"><b>Second coder</b> (blind): ${said}.</p>`;
    }
    return `<div class="coding"><p class="doc-tag">${esc(stepSaid(r.step))} · ${r.weak ?'only hinted at, so left out of the counts' : 'counted'}</p>${codes(r, still)}${second}</div>`;
  }
  const wholeLink = (id, words = 'whole interview') => {
    const r = RUN.rows[id];
    return r && r.at ? `<button class="rowlink" data-doc="${esc(r.doc)}" data-from="${esc(id)}">${words}</button>` : '';
  };
  const docLink = d => RUN.docs[d] ? `<button class="doclink" data-doc="${esc(d)}" title="Read ${esc(d)} whole">${esc(d)}</button>` : esc(d);
  const docTag = (d, link = true) => `<p class="doc-tag">${link ? docLink(d) : esc(d)}${group(d) ? ' · ' + esc(group(d)) : ''}</p>`;
  const head = (what, why, whatHtml) => `<h3>${whatHtml || esc(what)}</h3>` + (why ? `<p class="small why">${esc(why)}</p>` : '');

  // The rows at one place: the same document and the same stretch of it, or where a row was not placed, the same
  // quotation. One passage coded more than once, in one step or in several, is drawn once with every coding under
  // it, never as identical quotations one after another.
  const placeOf = id => { const r = RUN.rows[id]; return r.doc + '\u0001' + (r.at ? r.at.join('-') : r.ctx[1]); };
  function byPlace(ids) {
    const at = new Map();
    for (const id of ids) if (RUN.rows[id]) { const k = placeOf(id); at.has(k) ? at.get(k).push(id) : at.set(k, [id]); }
    return [...at.values()];
  }
  // Why one passage carries several codings: in which steps, or within one step, which of its codes differ
  function twice(ids) {
    const steps = [...new Set(ids.map(id => RUN.rows[id].step))];
    let how;
    if (steps.length > 1) {
      how = (steps.length === ids.length ? 'once in each of the ' : 'in the ') + andList(steps.map(stepName)) + ' codings';
    } else {
      const cols = [...new Set(ids.flatMap(id => coded(RUN.rows[id].codes).map(([k]) => k)))]
        .filter(k => new Set(ids.map(id => String(RUN.rows[id].codes[k] ?? ''))).size > 1);
      how = `in the ${stepName(steps[0])} coding, ` + (cols.length ? `with a different ${andList(cols.map(k => label(k).toLowerCase()))} each time` : 'the same way each time');
    }
    return `<p class="small twice">This one passage was coded ${times(ids.length)}, ${esc(how)}. Each coding is shown below.</p>`;
  }
  const passagesSaid = groups => {
    const n = groups.length, more = groups.filter(g => g.length > 1).length;
    return `${n} passage${n === 1 ? '' : 's'}` + (!more ? '' : n === 1 ? `, coded ${times(groups[0].length)}` : `, ${more} of them coded more than once`);
  };
  // One passage as every mode of the panel draws it: its document, the quotation (in its context where it is the
  // panel's only one), the ways into its context and the whole interview, and each coding it carries
  function passage(ids, { full = false } = {}) {
    const r = RUN.rows[ids[0]];
    const quote = full ? `<p class="ctx">${esc(r.ctx[0])}<mark>${esc(r.ctx[1])}</mark>${esc(r.ctx[2])}</p>` : `<p><q>${esc(r.ctx[1])}</q></p>`;
    const links = [full ? '' : `<button class="rowlink" data-rows="${esc(ids.join(','))}">in context</button>`, wholeLink(ids[0])].filter(Boolean).join('');
    const how = (ids.length > 1 ? twice(ids) : '') + ids.map(id => coding(id)).join('');
    // in its context the quotation runs long, so how it was coded comes first, where it is seen without scrolling
    return `<div class="item">${docTag(r.doc)}${full ? how + quote : quote}${links ? `<p class="links">${links}</p>` : ''}${full ? '' : how}</div>`;
  }

  // A document read whole, with every passage this run coded in it marked: a colour for each coding step, stripes
  // where two steps' passages overlap, and a click on a mark opening the passages under it. The texts come from the
  // report itself (TEXTS, gzipped), or for a corpus too large to carry, from the run's zip, which the reader chooses.
  const LAYERS = ['rgb(214 80 60 / .28)', 'rgb(60 120 214 / .28)', 'rgb(60 170 110 / .30)', 'rgb(200 150 30 / .32)', 'rgb(150 80 200 / .28)', 'rgb(40 170 180 / .30)'];
  // Read from RUN each time, since a combined report of several runs (bind.py) points RUN at the run being read
  const stepsOf = () => [...new Set(Object.values(RUN.rows).map(r => r.step))];
  const layer = s => LAYERS[stepsOf().indexOf(s) % LAYERS.length];
  let carried = null, carriedFrom = null;
  async function unpack(bytes, how) {
    const out = new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream(how)));
    return new Uint8Array(await out.arrayBuffer());
  }
  async function carriedText(doc) {
    if (!carried || carriedFrom !== TEXTS) {
      const bytes = Uint8Array.from(atob(TEXTS), c => c.charCodeAt(0));
      carried = JSON.parse(new TextDecoder().decode(await unpack(bytes, 'gzip')));
      carriedFrom = TEXTS;
    }
    return carried[doc];
  }
  let zipped = null, zippedFor = null;  // the zip chosen, and the run it was chosen for
  async function zipText(name) {
    const v = new DataView(zipped.buffer, zipped.byteOffset, zipped.byteLength);
    let end = zipped.length - 22;
    while (end >= 0 && v.getUint32(end, true) !== 0x06054b50) end--;
    if (end < 0) return null;
    let at = v.getUint32(end + 16, true);
    for (let i = 0, n = v.getUint16(end + 10, true); i < n; i++) {
      const method = v.getUint16(at + 10, true), size = v.getUint32(at + 20, true);
      const nameLen = v.getUint16(at + 28, true), extra = v.getUint16(at + 30, true), note = v.getUint16(at + 32, true);
      const local = v.getUint32(at + 42, true);
      if (new TextDecoder().decode(zipped.subarray(at + 46, at + 46 + nameLen)) === name) {
        const start = local + 30 + v.getUint16(local + 26, true) + v.getUint16(local + 28, true);
        const data = zipped.subarray(start, start + size);
        return new TextDecoder().decode(method === 8 ? await unpack(data, 'deflate-raw') : data);
      }
      at += 46 + nameLen + extra + note;
    }
    return null;
  }
  function chooseZip(doc, from) {
    open(`${docTag(doc, false)}<p>This report leaves its documents out because together they are too large. Choose the run's zip, ${esc(RUN.zip || 'saved beside this report')}, to read this one whole.</p><input type="file" accept=".zip" id="zip-pick">`);
    document.getElementById('zip-pick').addEventListener('change', async e => {
      const f = e.target.files[0];
      if (!f) return;
      zipped = new Uint8Array(await f.arrayBuffer());
      zippedFor = RUN;
      showDoc(doc, from);
    });
  }
  async function showDoc(doc, from) {
    let text;
    if (TEXTS) text = await carriedText(doc);
    // read as the recount read it, line endings made one newline, since every passage's offsets count that text
    else if (zipped && zippedFor === RUN) text = (await zipText(RUN.docs[doc].file))?.replace(/\r\n?/g, '\n');
    else return chooseZip(doc, from);
    if (text == null) return open(`<p>${esc(doc)} is not in ${TEXTS ? 'this report' : 'that zip'}.</p>`);
    const marks = Object.entries(RUN.rows).filter(([, r]) => r.doc === doc && r.at);
    const cuts = [...new Set([0, text.length, ...marks.flatMap(([, r]) => r.at)])].sort((a, b) => a - b);
    let body = '';
    for (let i = 0; i < cuts.length - 1; i++) {
      const [a, b] = [cuts[i], cuts[i + 1]];
      const under = marks.filter(([, r]) => r.at[0] <= a && r.at[1] >= b);
      const piece = esc(text.slice(a, b));
      if (!under.length) { body += piece; continue; }
      const cols = [...new Set(under.map(([, r]) => layer(r.step)))];
      const bg = cols.length === 1 ? cols[0] : `repeating-linear-gradient(135deg, ${cols.map((c, j) => `${c} ${j * 6}px ${(j + 1) * 6}px`).join(', ')})`;
      const ids = under.map(([id]) => id);
      // a span rather than a button, which a browser always draws as a box and so breaks the line around it
      body += `<span class="span${ids.includes(from) ? ' from' : ''}" role="button" tabindex="0" data-rows="${esc(ids.join(','))}" style="background:${bg}">${piece}</span>`;
    }
    const used = stepsOf().filter(s => marks.some(([, r]) => r.step === s));
    open(`${docTag(doc, false)}<h3>${esc(RUN.docs[doc].title || doc)}</h3>` +
      `<p class="layers">${used.map(s => `<span><i style="background:${layer(s)}"></i>${esc(label(s))}</span>`).join('')}</p>` +
      `<p class="small">${marks.length} coded passage${marks.length === 1 ? '' : 's'}. Point at one, or tab to it, to see how it was coded; click it for the passage.</p><div class="whole">${body}</div>`);
    const at = pbody.querySelector('.span.from');
    if (at) found(at);
  }
  // Pointing at a coded stretch of a whole interview, or tabbing to it, says how each passage under it was coded; a
  // tap or Enter opens the passages, which say the same, so touch and keyboard reach it too
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  panel.appendChild(tip);
  // An opposite pole's ~ (`named`) says what it means: "The opposite of X", and the pole's own meaning where the
  // codebook gives one. Pointing, tabbing and tapping all open it, so it works on a phone; a tap elsewhere closes it.
  const pop = document.createElement('div');
  pop.className = 'tilde-pop';
  pop.setAttribute('role', 'tooltip');
  pop.hidden = true;
  document.body.appendChild(pop);
  const poleSaid = el => {
    const code = el.dataset.code || '';
    const col = el.dataset.col || (Object.keys(RUN.defs).find(k => k.endsWith('=' + code)) || '').split('=')[0];
    const means = poleMeans(col, code);
    const of = label(code).replace(/^~/, '');
    return `The opposite of ${of}` + (means ? `: ${means.charAt(0).toLowerCase() + means.slice(1)}.` : '.');
  };
  function showPop(el) {
    pop.textContent = poleSaid(el);
    pop.hidden = false;
    const r = el.getBoundingClientRect();
    pop.style.left = Math.max(8, Math.min(r.left + scrollX - 12, scrollX + innerWidth - pop.offsetWidth - 8)) + 'px';
    pop.style.top = (r.bottom + scrollY + 6) + 'px';
  }
  const hidePop = () => { pop.hidden = true; };
  document.addEventListener('mouseover', e => { const t = e.target.closest?.('.tilde'); if (t) showPop(t); });
  // a mouse leaving the ~ closes it; after a touch it stays until a tap elsewhere, since a tap ends with the pointer moving off
  let touch = false;
  document.addEventListener('pointerdown', e => { touch = e.pointerType !== 'mouse'; }, true);
  document.addEventListener('mouseout', e => { if (!touch && e.target.closest?.('.tilde')) hidePop(); });
  document.addEventListener('focusin', e => { const t = e.target.closest?.('.tilde'); if (t) showPop(t); });
  document.addEventListener('focusout', e => { if (e.target.closest?.('.tilde')) hidePop(); });
  // capture, so a tap on the ~ inside a chip opens the popover rather than the chip's passages
  document.addEventListener('click', e => {
    const t = e.target.closest?.('.tilde');
    // a tap fires mouseover and focus before the click, so the click only ever opens it, never toggles it shut
    if (t) { e.preventDefault(); e.stopPropagation(); showPop(t); return; }
    if (!pop.hidden) hidePop();
  }, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hidePop(); });
  const MOST_SHOWN = 4;
  function showTip(span) {
    const ids = span.dataset.rows.split(',');
    tip.innerHTML = ids.slice(0, MOST_SHOWN).map(id => coding(id, true)).join('') +
      (ids.length > MOST_SHOWN ? `<p class="small">and ${ids.length - MOST_SHOWN} more; click for all of them</p>` : '');
    tip.hidden = false;
    const p = panel.getBoundingClientRect(), s = span.getBoundingClientRect();
    const below = s.bottom - p.top + panel.scrollTop + 6;
    tip.style.top = (s.bottom + tip.offsetHeight + 12 > innerHeight ? s.top - p.top + panel.scrollTop - tip.offsetHeight - 6 : below) + 'px';
  }
  const hideTip = () => { tip.hidden = true; };
  pbody.addEventListener('mouseover', e => { const s = e.target.closest('.whole .span'); if (s) showTip(s); });
  pbody.addEventListener('mouseout', e => { if (e.target.closest('.whole .span')) hideTip(); });
  pbody.addEventListener('focusin', e => { const s = e.target.closest('.whole .span'); if (s) showTip(s); });
  pbody.addEventListener('focusout', hideTip);
  // The annex of the run being read: the report's one, or in a combined report the one of the part RUN points at (SCOPE)
  const annexBlock = id => document.querySelector(`.annex${typeof SCOPE === 'string' ? SCOPE : ''} [data-node="step:${CSS.escape(id)}"]`);
  // Where opposites were combined (filter_links.mjs), a cell holds passages coded at either pole of each end: a
  // passage's own code for an end is the cell's value, or its opposite written with a leading ~
  const isOpposite = (code, value) => code != null && String(code) !== String(value)
    && String(code).replace(/^~/, '') === String(value).replace(/^~/, '');
  const oppositeEnds = (c, id) => { const r = RUN.rows[id]; return r ? Object.keys(c.values).filter(k => isOpposite(r.codes[k], c.values[k])) : []; };
  const combined = c => c && c.rows.some(id => oppositeEnds(c, id).length);
  // What the codebook says a code at the opposite pole means, without its "The opposite pole of X:" lead or its full stop
  const poleMeans = (k, code) => (RUN.defs[k + '=' + code] || '').replace(/^The opposite pole of [^:]+:\s*/, '').replace(/\.\s*$/, '');
  function open(html) {
    hideTip();
    pbody.innerHTML = html;
    panel.hidden = false;
    panel.scrollTop = 0;
  }
  // What a cell's or a code's values mean: each value with its definition, and where opposites were combined, how many
  // of the passages hold that end at its opposite pole
  function meaning(values, c) {
    const flips = k => c ? c.rows.filter(id => oppositeEnds(c, id).includes(k)).length : 0;
    return '<ul>' + Object.entries(values).map(([k, v]) => {
      const d = isPole(v) ? poleMeans(k, v) : RUN.defs[k + '=' + v], n = flips(k);
      if (!n) return `<li><b>${esc(label(k))}: ${named(v, k)}</b>${d ? '. ' + esc(d) : ''}</li>`;
      // an end some passages hold as its opposite: the factor as labelled and its opposite, a line each with its own meaning
      const plain = String(v).replace(/^~/, ''), od = poleMeans(k, '~' + plain);
      return `<li>${esc(label(k))}<br><b>${esc(label(plain))}</b>${d ? ': ' + esc(String(d).replace(/\.\s*$/, '')) : ''}.` +
        `<br><b>${named('~' + plain, k)}</b> (the opposite, in ${n} of these ${c.rows.length} passages)${od ? ': ' + esc(od) : ''}.</li>`;
    }).join('') + '</ul>';
  }
  // The passages behind a count, a code or a factor, each place once: who holds them firmly and their passages, then
  // the documents and passages held only through rows the coder marked weak, which no count stands on
  function listing(ids, docs, weakDocs) {
    const isWeak = id => (RUN.rows[id] || {}).weak;
    const firmDocs = docs.filter(d => !weakDocs.includes(d));
    const drawn = keep => byPlace(ids.filter(keep)).map(g => passage(g)).join('');
    const firm = drawn(id => !isWeak(id)), weak = drawn(isWeak);
    return `<p class="small">${firmDocs.length ? 'Who: ' + firmDocs.map(docLink).join(', ') : 'Nobody firmly.'}</p>${firm}` +
      (weak ? `<p class="small">Only hinted at, so left out of the counts${weakDocs.length ? ': ' + weakDocs.map(docLink).join(', ') : ''}</p>${weak}` : '');
  }
  function showCell(id, within) {
    const c = RUN.cells[id];
    if (!c) return;
    if (!Object.keys(c.values).length) {
      return open(head(c.said, `Every one of the ${c.unit || 'documents'} this count was made from, by document`) +
        c.docs.map(d => `<div class="item">${docTag(d)}</div>`).join(''));
    }
    const said = within && within in c.within ? countSaid(c.n, c.within[within], c.unit || 'documents') : c.said;
    const both = combined(c) ? '<p class="small">Opposites are combined here, so a passage coded as a factor or as its opposite counts towards this link. Passages coded as an opposite come first, their codes marked ~; the rest were coded as labelled.</p>' : '';
    // passages coded at an opposite pole first, since they are the few a reader looks for
    const listed = c.rows.filter(id => oppositeEnds(c, id).length).concat(c.rows.filter(id => !oppositeEnds(c, id).length));
    open(head(said, c.question ? `Judged by rule: ${c.question}` : '') +
      (c.told ? `<p class="small">Counted by code from the coded passages: the ${esc(c.unit || 'documents')} ${esc(c.told)}.</p>`
        : `<p class="small">Counted by code from the coded passages: the ${c.base == null ? 'passages' : esc(c.unit || 'documents')} where</p>${meaning(c.values, c)}`) + both +
      listing(listed, c.docs, c.weak_docs || []));
  }
  // A code's chip: what the code means and every passage given it in its step. Where a table counts that code alone,
  // its cell holds exactly those passages and opens as it does from the table; otherwise the same view, without a count.
  function showCode(key) {
    const k = RUN.codes && RUN.codes[key];
    if (!k) return;
    if (k.cell && RUN.cells[k.cell]) return showCell(k.cell);
    const isWeak = id => (RUN.rows[id] || {}).weak;
    const docsOf = ids => [...new Set(ids.map(id => RUN.rows[id].doc))];
    const firmDocs = docsOf(k.rows.filter(id => !isWeak(id)));
    const weakDocs = docsOf(k.rows.filter(isWeak)).filter(d => !firmDocs.includes(d));
    const places = byPlace(k.rows.filter(id => !isWeak(id)));
    open(head('', `Every passage given this code in the ${stepName(k.step)} coding: ` +
      `${passagesSaid(places)}, from ${firmDocs.length} document${firmDocs.length === 1 ? '' : 's'}`, `${esc(label(k.col))}: ${named(k.value, k.col)}`) +
      meaning({ [k.col]: k.value }) + listing(k.rows, firmDocs.concat(weakDocs), weakDocs));
  }
  // A factor in a map opens the passages behind every link into and out of it, each once: the cells of the arrows
  // Graphviz drew to or from it, whose titles read "from->to" with the node's own title at either end.
  function factorCells(node) {
    const name = node.querySelector('title').textContent;
    const ends = t => t.split('->').map(x => x.replace(/:\w+$/, ''));
    return [...node.closest('svg').querySelectorAll('g.edge')]
      .filter(e => ends(e.querySelector('title').textContent).includes(name)).map(e => RUN.cells[e.id]).filter(c => c && c.rows.length);
  }
  function showFactor(node) {
    const cells = factorCells(node);
    const ids = [...new Set(cells.flatMap(c => c.rows))], groups = byPlace(ids);
    if (!groups.length) return;
    const text = [...node.querySelectorAll('text')].map(t => t.textContent).join(' ');
    const docs = [...new Set(cells.flatMap(c => c.docs))], weakDocs = [...new Set(cells.flatMap(c => c.weak_docs || []))]
      .filter(d => !cells.some(c => c.docs.includes(d) && !(c.weak_docs || []).includes(d)));
    open(head(text, `Behind the ${cells.length} link${cells.length === 1 ? '' : 's'} into and out of this factor: ${passagesSaid(groups)}`) +
      listing(ids, docs, weakDocs));
  }
  // What a finding rests on: the numbers it states, each opening who it counts, the passages it quotes, and the
  // workflow steps they came from, each opening its block under How this was made.
  function showBased(key) {
    const f = RUN.based[key] || {};
    const cells = (f.cells || []).filter(id => RUN.cells[id]);
    const groups = byPlace(f.rows || []);
    const steps = [...new Set([...(f.steps || []), ...cells.map(id => RUN.cells[id].step), ...groups.flat().map(id => RUN.rows[id].step)])]
      .filter(id => annexBlock(id));
    const said = id => { const c = RUN.cells[id]; const v = Object.entries(c.values).map(([k, x]) => `${esc(label(k))}: ${named(x, k)}`).join(', ');
      return `<div class="item"><button class="n" data-cell="${esc(id)}">${esc(c.said)}</button> ${c.question || c.told ? esc(c.question || c.told) : v || 'documents read'}</div>`; };
    open(head('What this rests on') +
      (cells.length ? `<p class="small">${cells.length} number${cells.length === 1 ? '' : 's'}, counted by code</p>` + cells.map(said).join('') : '') +
      (groups.length ? `<p class="small">${passagesSaid(groups)}, quoted</p>` + groups.map(g => passage(g)).join('') : '') +
      (steps.length ? '<p class="small">From these steps</p><p>' + steps.map(s => `<button class="rowlink" data-step="${esc(s)}">${esc(stepSaid(s))}</button>`).join('') + '</p>' : ''));
  }
  // Brings a target into view and marks it for a few seconds, the one way the report shows where a click took the
  // reader: a step, a section, a passage in a whole interview. The margin map's own reveal marks its blocks with the
  // same class. Removed and added again so a second visit marks it again.
  // The scroll eases in and out with the margin map's own glide (minimap-mount.js `glide`, same curve and timing),
  // so every jump in the report moves the same way; a reader who asks for less motion gets the jump.
  let gliding = 0;
  function glide(scroller, by) {
    cancelAnimationFrame(gliding);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { scroller.scrollTop += by; return; }
    const from = scroller.scrollTop, span = Math.min(700, 300 + Math.abs(by) / 6), start = performance.now();
    const step = now => {
      const t = Math.min(1, (now - start) / span);
      scroller.scrollTop = from + by * (t < 0.5 ? 4 * t ** 3 : 1 - (2 - 2 * t) ** 3 / 2);
      if (t < 1) gliding = requestAnimationFrame(step);
    };
    gliding = requestAnimationFrame(step);
  }
  function found(el, block = 'center') {
    for (let d = el.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
    // inside the side panel the panel scrolls; anywhere else the page does
    const scroller = el.closest('#panel') || document.scrollingElement;
    const top = scroller === document.scrollingElement ? 0 : scroller.getBoundingClientRect().top;
    const view = scroller === document.scrollingElement ? innerHeight : scroller.clientHeight;
    const seat = el.getBoundingClientRect();
    const lift = block === 'start' ? Math.min(32, view / 10) : seat.height < view ? (view - seat.height) / 2 : view / 3;
    glide(scroller, seat.top - top - lift);
    el.classList.remove('rb-found');
    void el.offsetWidth;
    el.classList.add('rb-found');
  }
  function showStep(id) {
    const block = annexBlock(id);
    if (block) found(block);
  }
  // Passages opened by id: a citation, a mark in the evidence matrix, a coded stretch of a whole interview, a passage
  // listed under How this was made, or "in context". A single place is shown in its context.
  function showRows(ids, why = '') {
    const groups = byPlace(ids);
    if (!groups.length) return open(`<p>No passage ${esc(ids.join(', '))}.</p>`);
    open(head(passagesSaid(groups), why) + groups.map(g => passage(g, { full: groups.length === 1 })).join(''));
  }
  // Why the passages a button opens are these ones, said under the panel's heading
  function whyOf(b) {
    if (b.dataset.why) return b.dataset.why;
    if (b.classList.contains('cite')) return 'Cited in the answer';
    if (b.closest('.annex')) return 'Listed with the coded passages under How this was made';
    return '';
  }
  const spanRows = span => {
    const ids = span.dataset.rows.split(',');
    showRows(ids, RUN.rows[ids[0]] ? `Coded at this point of ${RUN.rows[ids[0]].doc}` : '');
  };

  document.addEventListener('click', e => {
    // a link to a section of the report (the contents, a "§" reference) takes the reader there and marks its heading
    const to = e.target.closest('a[href^="#"]');
    if (to) {
      const t = document.getElementById(decodeURIComponent(to.getAttribute('href').slice(1)));
      if (!t) return;
      e.preventDefault();
      history.replaceState(null, '', to.getAttribute('href'));
      return found(t.matches('h2, h3') ? t : t.querySelector('h2, h3') || t, 'start');
    }
    const edge = e.target.closest('.map g.edge');
    if (edge) return showCell(edge.id);
    const factor = e.target.closest('.map g.node:not(.inert)');
    if (factor) return showFactor(factor);
    const span = e.target.closest('.whole .span');
    if (span) return spanRows(span);
    const b = e.target.closest('button');
    if (!b) return;
    if (b.id === 'panel-close') { panel.hidden = true; return; }
    if (b.dataset.cell) return showCell(b.dataset.cell, b.dataset.within);
    if (b.dataset.code) return showCode(b.dataset.code);
    if (b.dataset.row) return showRows([b.dataset.row], whyOf(b));
    if (b.dataset.rows) return showRows(b.dataset.rows.split(','), whyOf(b));
    if (b.dataset.based) return showBased(b.dataset.based);
    if (b.dataset.doc) return showDoc(b.dataset.doc, b.dataset.from);
    if (b.dataset.step) return showStep(b.dataset.step);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') panel.hidden = true;
    // a coded stretch is a span, which a browser does not press on Enter or Space as it presses a button
    const span = e.target.closest && e.target.closest('.whole .span');
    if (span && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); spanRows(span); }
  });

  // Each map is carried as DOT and drawn here by Graphviz (Viz.js), which the page loads at a fixed version
  // (`GRAPHVIZ` in render_report.py); a reader offline sees the words under each figure and its counts, and no map.
  const dots = [...document.querySelectorAll('pre.dot')];
  if (dots.length) {
    (window.Viz ? Viz.instance() : Promise.reject()).then(viz => {
      for (const pre of dots) {
        const svg = viz.renderSVGElement(pre.textContent, { engine: pre.dataset.engine });
        pre.parentElement.replaceWith(svg);
        // a node no counted link runs into or out of, such as a loop diagram's marker, opens nothing, so it does not
        // offer a click (report.css)
        for (const n of svg.querySelectorAll('g.node')) if (!factorCells(n).length) n.classList.add('inert');
      }
    }).catch(() => {
      for (const p of document.querySelectorAll('.graph .drawing')) {
        p.textContent = 'The map could not be drawn: Graphviz loads from cdn.jsdelivr.net, which this computer could not reach. Open the report again when it is online.';
      }
    });
  }

  // The floating contents (report.css shows it on wide screens): the section the reader is in is marked as they scroll
  const toc = document.querySelector('.toc');
  if (toc) {
    const links = [...toc.querySelectorAll('a[href^="#"]')];
    const at = links.map(a => [a, document.getElementById(a.getAttribute('href').slice(1))]).filter(([, t]) => t);
    let queued = false;
    const mark = () => {
      queued = false;
      let on = null;
      for (const [a, t] of at) if (t.getBoundingClientRect().top < innerHeight * 0.3) on = a;
      for (const a of links) a.classList.toggle('on', a === on);
    };
    addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
  }
})();
