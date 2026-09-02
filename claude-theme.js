/* Ocean theme - user script.
 *
 * Runs in the claude.ai page on every load, via the main-process injection.
 * Re-read each time, so edits here apply on the next restart with no rebuild
 * and no password. This is the channel for anything CSS cannot express.
 *
 * Keep everything defensive: this runs inside the real app, and a throw here
 * must never affect the page. The injection wraps this in try/catch too.
 *
 * ON A FRESH MACHINE this file is intentionally inert. Nothing here is needed
 * for the theme itself - all colour work is CSS, generated from binding.json.
 */

/* ==========================================================================
 * The code-theme preference (available, deliberately NOT enabled)
 * ==========================================================================
 *
 * Claude has a built-in syntax-theme preference that controls the token colours
 * inside code blocks. It ships ~25 themes (material-theme-ocean, github-dark,
 * dracula, one-dark-pro, catppuccin-*, nord, tokyo-night ...) but exposes no
 * picker in this build.
 *
 * The authoritative store is the zustand-persisted localStorage key
 *   "epitaxy-editor-prefs"  =  {state: {...}, version: N}
 * The "LSS-epitaxy:*" keys are ONLY a one-time migration source and are ignored
 * once the main store holds a value for that field - writing them alone does
 * nothing. Both facts cost a lot of time to establish.
 *
 * This mechanism is PROVEN to work: setting it visibly changed comment colours.
 * It is disabled because material-theme-ocean's own comments (#464B5D) are
 * dimmer than Claude's default, which was a net loss. If you want to try a
 * different theme, set WANT below and uncomment the call.
 *
 * Note: this changes token colours only. It does NOT change the code block
 * background - Material Ocean's editor.background is #0F111A, near-black, so
 * enabling it can make the block look *more* black, not less.
 */
function setCodeTheme(WANT) {
  var STORE = "epitaxy-editor-prefs";
  var FIELD = "codeThemeDark";
  var GUARD = "ocean-theme:code-theme-set";
  try {
    var parsed = null;
    try {
      parsed = JSON.parse(window.localStorage.getItem(STORE));
    } catch (_) {}
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      parsed = { state: {}, version: 0 };
    }
    if (!parsed.state || typeof parsed.state !== "object") parsed.state = {};
    if (typeof parsed.version !== "number") parsed.version = 0;
    if (parsed.state[FIELD] === WANT) return;

    parsed.state[FIELD] = WANT;
    window.localStorage.setItem(STORE, JSON.stringify(parsed));

    // Read once at startup, so reload to pick it up. Guarded against looping.
    if (!window.sessionStorage.getItem(GUARD)) {
      window.sessionStorage.setItem(GUARD, "1");
      window.location.reload();
    }
  } catch (_) {}
}

// setCodeTheme("github-dark");   // <- uncomment to enable

/* ==========================================================================
 * Findings - read before adding anything here
 * ==========================================================================
 *
 * Established by diagnostics during the original build. All of these cost
 * multiple restarts to learn; do not re-derive them.
 *
 *  - The markdown container is `.prose`. `.ReactMarkdown` does NOT exist in
 *    this app. Rules written against a non-existent container match nothing
 *    and fail SILENTLY - no warning, no error. Always confirm a container
 *    exists before trusting a selector.
 *
 *  - Terminal panels (.group/terminal, .xterm-*) are xterm with the WebGL
 *    renderer: three canvases, background painted INTO the canvas. CSS colours
 *    the element underneath for one frame and is then overdrawn. No Terminal
 *    instance is exposed on the DOM - only React's private fiber. Unreachable
 *    without walking React internals. Do not re-attempt.
 *
 *  - Markdown code blocks are `.epitaxy-codeblock` - a DIFFERENT component
 *    from the terminal, and ordinary DOM. Its background is NOT on the block
 *    itself; walking up finds no opaque ancestor. UNRESOLVED: four probes
 *    failed to identify what paints it. If resuming, first confirm the class
 *    still exists AND that this script runs in the frame rendering the
 *    conversation - the last failure suggests one of those is wrong.
 *
 * DIAGNOSTIC TECHNIQUE: to answer a DOM question, write a probe here that
 * stores findings via localStorage.setItem, then read them off disk with
 *   strings -a ~/.config/Claude/Local\\ Storage/leveldb/* | grep -oa '<marker>.*'
 * That needs nothing from the user beyond a restart. Two traps: rgba(0,0,0,0)
 * parses as [0,0,0,0] so a "near-black" test must check alpha; and the message
 * list virtualises, so poll rather than sampling at fixed times.
 */
