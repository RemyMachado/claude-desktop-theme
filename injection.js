/* >>> ocean-theme injection (claude-desktop-theme) */
/* Prepended to the Electron main entry.
 *
 * Three jobs, because the window is not styled from one place:
 *
 *  1. The page renders claude.ai remotely, so the theme is inserted into it
 *     with insertCSS rather than patched into a local stylesheet.
 *  2. The minimise / maximise / close buttons are drawn by Electron itself
 *     through titleBarOverlay - no stylesheet can reach them - so their colours
 *     are set through the same public API the app already uses.
 *  3. A user script runs in the page for what CSS cannot express: the app's own
 *     code-theme preference, and anything drawn to a canvas rather than styled.
 *
 * The three paths below are substituted when the archive is built. All three
 * files are re-read on each page load, so editing them and restarting applies
 * the change WITHOUT rebuilding the archive.
 */
try {
  const { app, nativeTheme } = require("electron");
  const fs = require("fs");
  const CSS_PATH = "__CSS_PATH__";
  const OVERLAY_PATH = "__OVERLAY_PATH__";
  const SCRIPT_PATH = "__SCRIPT_PATH__";

  const readFile = (p) => {
    try {
      return fs.readFileSync(p, "utf8");
    } catch (_) {
      return null;
    }
  };

  const paintWindowControls = (win) => {
    // Throws if the window has no title bar overlay, which is expected for
    // plain windows - skip those rather than guessing.
    try {
      const raw = readFile(OVERLAY_PATH);
      if (!raw || win.isDestroyed()) return;
      const overlay = JSON.parse(raw);
      const colours = overlay[nativeTheme.shouldUseDarkColors ? "dark" : "light"];
      if (colours) win.setTitleBarOverlay(colours);
    } catch (_) {}
  };

  app.on("browser-window-created", (_event, win) => {
    paintWindowControls(win);
    win.once("ready-to-show", () => paintWindowControls(win));
    const onThemeChange = () => paintWindowControls(win);
    nativeTheme.on("updated", onThemeChange);
    win.on("closed", () => nativeTheme.removeListener("updated", onThemeChange));
  });

  app.on("web-contents-created", (_event, contents) => {
    contents.on("dom-ready", () => {
      const css = readFile(CSS_PATH);
      if (css) {
        // 'user' origin outranks the page's own !important rules in the cascade.
        contents.insertCSS(css, { cssOrigin: "user" }).catch(() => {});
      }
      const script = readFile(SCRIPT_PATH);
      if (script) {
        // Wrapped so a script error can never surface as an unhandled rejection
        // or interfere with the page.
        contents
          .executeJavaScript(`(function(){try{${script}\n}catch(e){}})();`, true)
          .catch(() => {});
      }
    });
  });
} catch (_) {
  // A broken theme must never stop the app from starting.
}
/* <<< ocean-theme injection */
