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
    return `<p class="doc-tag">${esc(r.doc)} · ${esc(group(r.doc))}</p>${codes(r)}<p class="ctx">${esc(r.ctx[0])}<mark>${esc(r.ctx[1])}</mark>${esc(r.ctx[2])}</p>`;
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
    const b = e.target.closest('button');
    if (!b) return;
    if (b.id === 'panel-close') { panel.hidden = true; return; }
    if (b.id === 'open-in-cm') return openInCausalMap();
    if (b.dataset.cell) return showCell(b.dataset.cell, b.dataset.within);
    if (b.dataset.row) return open(rowInPlace(b.dataset.row));
    if (b.dataset.rows) return showRows(b.dataset.rows.split(','));
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') panel.hidden = true; });

  // Each map is carried as DOT and drawn here by Graphviz (Viz.js), fetched once at a fixed version; the report holds
  // nothing else that draws, so a reader offline sees the words under each figure and its counts, and no map.
  const dots = [...document.querySelectorAll('pre.dot')];
  if (dots.length) {
    import('https://cdn.jsdelivr.net/npm/@viz-js/viz@3.31.0/dist/viz.js').then(m => m.instance()).then(viz => {
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
