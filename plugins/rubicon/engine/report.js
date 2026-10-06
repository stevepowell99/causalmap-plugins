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
  function showCell(id) {
    const c = RUN.cells[id];
    if (!c) return;
    const what = Object.entries(c.values).map(([k, v]) => {
      const d = RUN.defs[k + '=' + v];
      return `<li><b>${esc(label(k))}: ${esc(label(v))}</b>${d ? '. ' + esc(d) : ''}</li>`;
    }).join('');
    const rows = c.rows.map(rowShort).join('');
    open(`<h3>${c.n} of ${c.base}</h3><p class="small">Counted by code from the coded passages: the documents where</p><ul>${what}</ul>
      <p class="small">${c.docs.length ? 'Who: ' + c.docs.map(esc).join(', ') : 'Nobody.'}</p>${rows}`);
  }
  function showRows(ids) {
    if (ids.length === 1) return open(rowInPlace(ids[0]));
    open(`<h3>${ids.length} passages</h3>` + ids.map(rowShort).join(''));
  }

  document.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.id === 'panel-close') { panel.hidden = true; return; }
    if (b.dataset.cell) return showCell(b.dataset.cell);
    if (b.dataset.row) return open(rowInPlace(b.dataset.row));
    if (b.dataset.rows) return showRows(b.dataset.rows.split(','));
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') panel.hidden = true; });
})();
