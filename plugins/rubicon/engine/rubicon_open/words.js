/**
 * Words the page says for a fixed value, kept apart from `model.js` and `figures.js`, which
 * re-export them, so that `minimap.js` can be carried by the plugin's report without the model.
 */

/**
 * A step state as the word on its chip.
 *
 * The engine records `skipped` for a step it inherited rather than did, which is a success
 * with no bill attached. On the page the word read as work left undone. Steve, 10
 * September 2026, of a run whose coding and everything below it said Skipped: "skipped
 * makes sense for UPSTREAM steps but not downstream." The results were there and current;
 * the word said otherwise.
 */
export function stateWord(state) {
    // `stale` is how the engine says a run's process went silent. On the page the word means
    // a result that may no longer hold, so a run that stopped reporting is called stopped.
    return state === 'skipped' ? 'reused' : state === 'stale' ? 'stopped' : state
}

/**
 * A figure's name, read rather than typed.
 *
 * `supporting_count` is how the name is written in the workflow, and a heading is not a
 * place anybody types one. Steve, 3 September 2026: "lose the underscores".
 */
export function nameInWords(name) {
    return String(name ?? '').replace(/_/g, ' ')
}
