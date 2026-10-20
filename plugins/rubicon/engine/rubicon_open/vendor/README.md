# Vendored assets

Third-party files that a report carries inside itself, so one report file opens, looks right and draws its maps on a network that reaches nothing. `rubicon_open/assets.py` reads them into the page; nothing here is fetched at run time. Each sits with its licence, which any copy of the engine (the Claude plugin included) must keep beside it.

## Typefaces: `fonts/`

- **Libre Franklin** (the report's sans-serif) and **Newsreader** (its serif, roman and italic), both under the SIL Open Font Licence 1.1, which allows redistribution and embedding provided the licence text travels with the fonts (`LibreFranklin-OFL.txt`, `Newsreader-OFL.txt`) and the fonts are not sold on their own.
- Taken from Google Fonts on 20 October 2026 (`fonts.gstatic.com`, Libre Franklin v20 and Newsreader v26), the files the report's stylesheet request used to receive: one variable woff2 per script and style, which `fonts.css` declares with a weight range in place of one face per weight.
- Scripts kept: latin, latin-ext and vietnamese. Text in another script (Cyrillic, Greek, Arabic and so on) falls back to the reader's system fonts, as it does for any font that lacks the character.
- `fonts.css` names each file by relative `url()`; `assets.fonts_css` replaces each with a data URI. To change a typeface, replace the woff2 files, keep `fonts.css` in step, and change the report's stylesheet (`report.css`) only if a family name changes.

## Graphviz: `graphviz/`

- `viz-global.js` is `@viz-js/viz` **3.31.0**, `dist/viz-global.js`, byte for byte as jsDelivr served it (1,329,882 bytes). Its SHA-384 is `iX6VK6ib27dxYB4T470zbHOsDDoLewuYvrIgv2B3XXe8kgfKsGMf8QIleFy6VPi4`, the value the report's script tag used for its integrity check; `tests/test_a_report_loads_nothing_from_the_internet.py` holds it.
- Licences: Viz.js is MIT (`Viz.js-LICENSE-MIT.txt`); the file also holds Graphviz in object form, under the Eclipse Public Licence 2.0 (`Graphviz-LICENSE-EPL-2.0.txt`; the source is at https://gitlab.com/graphviz/graphviz), and Expat, under MIT (`Expat-COPYING-MIT.txt`).
- The file holds no `</script` and no `<!--`, so it can be written into a `<script>` element unchanged; the test checks that too.
- To upgrade, replace the file, update the version and hash here and in the test, and draw a report with a map in a browser with the network blocked before trusting it.
