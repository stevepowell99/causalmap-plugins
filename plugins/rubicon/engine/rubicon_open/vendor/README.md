# Vendored: Viz.js 3.31.0

`viz.js` is the ES module build of [Viz.js](https://github.com/mdaines/viz-js) 3.31.0 (`@viz-js/viz` on npm, `dist/viz.js`), copied unchanged. It is Graphviz compiled to WebAssembly with a small wrapper, in one file with no imports, so the engine can draw a causal map under Node with nothing installed.

Viz.js is under the MIT licence, copyright Michael Daines. It contains Graphviz ([graphviz.org](https://www.graphviz.org), Eclipse Public License 1.0, source at [gitlab.com/graphviz/graphviz](https://gitlab.com/graphviz/graphviz)) and Expat ([libexpat.github.io](https://libexpat.github.io), MIT licence) in object code form.

To update: `npm pack @viz-js/viz@<version>`, copy `package/dist/viz.js` here, and change the version above.
