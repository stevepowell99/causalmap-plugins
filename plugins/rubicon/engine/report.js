(() => {
  const panel = document.getElementById('panel');
  const pbody = document.getElementById('panel-body');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const label = v => { const s = String(v).replace(/_/g, ' ').trim(); return s.charAt(0).toUpperCase() + s.slice(1); };
  const group = d => (RUN.docs[d] && RUN.docs[d].group) ? label(RUN.docs[d].group) : '';

  function codes(r) {
    return '<div class="codes">' + Object.entries(r.codes).map(([k, v]) => `<span title="${esc(RUN.defs[k + '=' + v] || '')}">${esc(label(k))}: ${esc(label(v))}</span>`).join('') + '</div>';
  }
  function rowInPlace(id) {
    const r = RUN.rows[id];
    if (!r) return `<p>No passage ${esc(id)}.</p>`;
    return `<p class="doc-tag">${esc(r.doc)} · ${esc(group(r.doc))}</p>${codes(r)}<p class="ctx">${esc(r.ctx[0])}<mark>${esc(r.ctx[1])}</mark>${esc(r.ctx[2])}</p>` +
      (r.at ? `<p><button class="rowlink" data-doc="${esc(r.doc)}" data-from="${esc(id)}">whole interview</button></p>` : '');
  }

  // A document read whole, with every passage this run coded in it marked: a colour for each coding step, stripes
  // where two steps' passages overlap, and a click on a mark opening the passages under it. The texts come from the
  // report itself (TEXTS, gzipped), or for a corpus too large to carry, from the run's zip, which the reader chooses.
  const LAYERS = ['rgb(214 80 60 / .28)', 'rgb(60 120 214 / .28)', 'rgb(60 170 110 / .30)', 'rgb(200 150 30 / .32)', 'rgb(150 80 200 / .28)', 'rgb(40 170 180 / .30)'];
  const steps = [...new Set(Object.values(RUN.rows).map(r => r.step))];
  const layer = s => LAYERS[steps.indexOf(s) % LAYERS.length];
  let carried = null;
  async function unpack(bytes, how) {
    const out = new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream(how)));
    return new Uint8Array(await out.arrayBuffer());
  }
  async function carriedText(doc) {
    if (!carried) {
      const bytes = Uint8Array.from(atob(TEXTS), c => c.charCodeAt(0));
      carried = JSON.parse(new TextDecoder().decode(await unpack(bytes, 'gzip')));
    }
    return carried[doc];
  }
  let zipped = null;
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
    open(`<p class="doc-tag">${esc(doc)} · ${esc(group(doc))}</p><p>This report leaves its documents out because together they are too large. Choose the run's zip, ${esc(RUN.zip || 'saved beside this report')}, to read this one whole.</p><input type="file" accept=".zip" id="zip-pick">`);
    document.getElementById('zip-pick').addEventListener('change', async e => {
      const f = e.target.files[0];
      if (!f) return;
      zipped = new Uint8Array(await f.arrayBuffer());
      showDoc(doc, from);
    });
  }
  async function showDoc(doc, from) {
    let text;
    if (TEXTS) text = await carriedText(doc);
    else if (zipped) text = await zipText(RUN.docs[doc].file);
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
    const used = steps.filter(s => marks.some(([, r]) => r.step === s));
    open(`<p class="doc-tag">${esc(doc)} · ${esc(group(doc))}</p><h3>${esc(RUN.docs[doc].title || doc)}</h3>` +
      `<p class="layers">${used.map(s => `<span><i style="background:${layer(s)}"></i>${esc(label(s))}</span>`).join('')}</p>` +
      `<p class="small">${marks.length} coded passage${marks.length === 1 ? '' : 's'}. Click one to see how it was coded.</p><div class="whole">${body}</div>`);
    pbody.querySelector('.span.from')?.scrollIntoView({ block: 'center' });
  }
  function rowShort(id) {
    const r = RUN.rows[id];
    if (!r) return '';
    return `<div class="item"><p class="doc-tag">${esc(r.doc)} · ${esc(group(r.doc))}</p><q>${esc(r.ctx[1])}</q> <button class="rowlink" data-row="${esc(id)}">in context</button></div>`;
  }
  function open(html) {
    pbody.innerHTML = html;
    panel.hidden = false;
    panel.scrollTop = 0;
  }
  function showCell(id, within) {
    const c = RUN.cells[id];
    if (!c) return;
    if (!Object.keys(c.values).length) {
      return open(`<h3>${c.n} documents</h3><p class="small">Every document this count was made from:</p>` +
        c.docs.map(d => `<div class="item"><p class="doc-tag">${esc(d)} · ${esc(group(d))}</p></div>`).join(''));
    }
    const base = within && within in c.within ? c.within[within] : c.base;
    const what = Object.entries(c.values).map(([k, v]) => {
      const d = RUN.defs[k + '=' + v];
      return `<li><b>${esc(label(k))}: ${esc(label(v))}</b>${d ? '. ' + esc(d) : ''}</li>`;
    }).join('');
    const rows = c.rows.map(rowShort).join('');
    open(`<h3>${c.n} of ${base}</h3><p class="small">Counted by code from the coded passages: the documents where</p><ul>${what}</ul>
      <p class="small">${c.docs.length ? 'Who: ' + c.docs.map(esc).join(', ') : 'Nobody.'}</p>${rows}`);
  }
  // What a finding rests on: the numbers it states, each opening who it counts, the passages it quotes, and the
  // workflow steps they came from, each opening its block under How this was made.
  function showBased(key) {
    const f = RUN.based[key] || {};
    const cells = (f.cells || []).filter(id => RUN.cells[id]);
    const rows = (f.rows || []).filter(id => RUN.rows[id]);
    const steps = [...new Set([...(f.steps || []), ...cells.map(id => RUN.cells[id].step), ...rows.map(id => RUN.rows[id].step)])]
      .filter(id => document.querySelector(`.annex [data-node="step:${CSS.escape(id)}"]`));
    const said = id => { const c = RUN.cells[id]; const v = Object.entries(c.values).map(([k, x]) => `${label(k)}: ${label(x)}`).join(', ');
      return `<div class="item"><button class="n" data-cell="${esc(id)}">${c.n} of ${c.base}</button> ${esc(v || 'documents read')}</div>`; };
    open('<h3>What this rests on</h3>' +
      (cells.length ? `<p class="small">${cells.length} number${cells.length === 1 ? '' : 's'}, counted by code</p>` + cells.map(said).join('') : '') +
      (rows.length ? `<p class="small">${rows.length} quoted passage${rows.length === 1 ? '' : 's'}</p>` + rows.map(rowShort).join('') : '') +
      (steps.length ? '<p class="small">From these steps</p><p>' + steps.map(s => `<button class="rowlink" data-step="${esc(s)}">${esc(label(s))}</button>`).join('') + '</p>' : ''));
  }
  function showStep(id) {
    const block = document.querySelector(`.annex [data-node="step:${CSS.escape(id)}"]`);
    if (!block) return;
    for (let d = block.closest('details'); d; d = d.parentElement.closest('details')) d.open = true;
    block.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function showRows(ids) {
    if (ids.length === 1) return open(rowInPlace(ids[0]));
    open(`<h3>${ids.length} passages</h3>` + ids.map(rowShort).join(''));
  }

  // Hand the run to the Rubicon page in this browser: the page says it is ready, and this answers
  // with the zip (webapp/rubicon/js/receive.js). Nothing goes to a server.
  function openInCausalMap() {
    const said = document.getElementById('open-in-cm-said');
    const page = window.open(RUN_ZIP.page + '?receive=1', '_blank');
    if (!page) {
      said.hidden = false;
      said.textContent = 'This viewer cannot open the page. Open this report in your web browser and click again.';
      return;
    }
    const origin = new URL(RUN_ZIP.page, location.href).origin;
    addEventListener('message', e => {
      if (e.source === page && e.data && e.data.type === 'rubicon-ready') {
        page.postMessage({ type: 'rubicon-run', name: RUN_ZIP.name, folder: RUN_ZIP.folder, zip: RUN_ZIP.zip }, origin);
      }
    });
  }

  document.addEventListener('click', e => {
    const edge = e.target.closest('.map g.edge');
    if (edge) return showCell(edge.id);
    const span = e.target.closest('.whole .span');
    if (span) return showRows(span.dataset.rows.split(','));
    const b = e.target.closest('button');
    if (!b) return;
    if (b.id === 'panel-close') { panel.hidden = true; return; }
    if (b.id === 'open-in-cm') return openInCausalMap();
    if (b.dataset.cell) return showCell(b.dataset.cell, b.dataset.within);
    if (b.dataset.row) return open(rowInPlace(b.dataset.row));
    if (b.dataset.rows) return showRows(b.dataset.rows.split(','));
    if (b.dataset.based) return showBased(b.dataset.based);
    if (b.dataset.doc) return showDoc(b.dataset.doc, b.dataset.from);
    if (b.dataset.step) return showStep(b.dataset.step);
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') panel.hidden = true; });

  // Each map is carried as DOT and drawn here by Graphviz (Viz.js), which the page loads at a fixed version
  // (`GRAPHVIZ` in render_report.py); a reader offline sees the words under each figure and its counts, and no map.
  const dots = [...document.querySelectorAll('pre.dot')];
  if (dots.length) {
    (window.Viz ? Viz.instance() : Promise.reject()).then(viz => {
      for (const pre of dots) {
        const svg = viz.renderSVGElement(pre.textContent, { engine: pre.dataset.engine });
        pre.parentElement.replaceWith(svg);
      }
    }).catch(() => {
      for (const p of document.querySelectorAll('.graph .drawing')) {
        p.textContent = 'The map could not be drawn: Graphviz loads from cdn.jsdelivr.net, which this computer could not reach. Open the report again when it is online.';
      }
    });
  }
})();
