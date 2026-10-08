// The margin map beside the annex, mounted by the Rubicon page's own minimap-mount.js over the blocks the annex draws
// (render_report.py `annex`), with the whole report as what scrolls.
const gutter = document.querySelector('.wf-gutter')
if (gutter) {
  gutter.innerHTML = MAP_ASIDE
  mountMap(document.body, ELEMENTS, { scroller: document.scrollingElement })
}
