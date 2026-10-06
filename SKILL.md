---
name: claude-desktop-theme
description: Theme the Claude Desktop app - apply a colour palette to it, change the palette it uses, or reapply the theme after an app update has reset it. Also for adapting the theme when an update changes how the app defines its colours. Use ONLY when the user explicitly asks to theme, recolour, or fix the theme of Claude Desktop. Noticing that an app looks different, or any other discussion of colours, themes, or CSS, is not by itself a request to run this.
---

# Claude Desktop theme

Claude Desktop ships no colour settings beyond light/dark. This skill applies a
colour palette to it properly.

The palette is data: `themes/*.json` maps ~21 semantic roles to colours, and
`binding.json` maps those roles onto the app's ~131 customisation points. The
theme currently installed is whichever `--theme` was last generated. The one
non-colour choice, the chat text size, is the user's and lives in the local,
untracked `settings.json` - see [Chat text size](#chat-text-size).

`themes/ocean.json` is included as a **worked example** - its palette comes from
t3code's theme of the same name, credited in the file. Do not assume it is what
the user wants; most people bring their own. See
[Changing the theme](#changing-the-theme-the-interactive-flow).

**The window renders claude.ai, not a local bundle.** There is a local renderer
at `resources/ion-dist/`, and patching its CSS does nothing at all — that was a
dead end, confirmed by the app's Local Storage holding `https://claude.ai` and no
`app://` origin. So the theme is injected into the live page by the Electron
main process: a small block prepended to the main entry calls
`webContents.insertCSS()` on every `dom-ready`. That means rebuilding
`app.asar`, which `build_asar.py` does and verifies.

An app update replaces the archive, so the theme has to be reapplied
afterwards. That is the normal reason to run this.

## Two intrusive operations - both need consent

Be straight with the user about both. Neither is routine.

1. **Patching the app.** This replaces `app.asar`, the application's own code
   archive. It edits executable JavaScript, not a stylesheet, so
   a bad patch means the app does not launch - and if the user is talking to you
   from inside it, their window goes with it. It is backed up to
   `app.asar.orig` and `./revert.sh` restores it, but give them that command
   *before* they restart. Never install without an explicit go-ahead.

2. **Reading another application to capture a palette.** Reverse-engineering an
   app the user did not ask you to touch, and potentially hundreds of megabytes
   of extraction. Name the app, say what you will read, ask, and clean up after.

Both are reasonable things to do on someone's own machine when they have asked
for them. Neither should happen quietly.

## Procedure

**`$SKILL_DIR` below means this skill's own directory** - the "Base directory
for this skill" reported when it loads. Do not assume `~/.claude/skills/...`:
it may be installed user-level or inside a project. The scripts resolve their
own location, so they work from anywhere; the `cd` is only for convenience.

**Narrate this skill as you run it.** The user should never have to guess what
has already happened, what is about to happen, or which parts need them. Speak
as the skill: say what you are here to do, lay out the whole plan before
starting, flag up front which steps need their approval, report what each step
returned, and stop where you said you would stop.

Do not collapse the steps into a single silent run, and do not present the
approval step as a surprise at the end.

**Never hand the user commands to run on your behalf.** This skill does the
work; the user approves it. If the session's permission mode blocks a step —
auto mode hard-refuses writes whose content describes replacing a system
archive, with no prompt reaching the user — then say which step is blocked and
ask the user to switch to a permission mode that prompts. Do not paste file
contents for them to save, do not stage files elsewhere for them to copy, and do
not look for a phrasing that slips past the refusal. Asking for the right mode
is the correct move; delegating the work back to the user is not.

### 0. Introduce yourself and the plan

Before running anything, tell the user in a few lines: what this skill does, the
steps it will take, and which of them need their approval. Roughly this shape,
in your own words:

> I'm the Claude Desktop theme skill — I keep the app painted in your chosen
> palette, which an app update resets. Four steps: check which build is
> installed, regenerate
> the stylesheet, build and verify the patched `app.asar`, then install it. The
> first three are read-only as far as your system is concerned — they only write
> inside my own directory — so I'll just run them. The last one replaces the
> app's archive and needs root, so I'll show you the exact command and wait for
> your go-ahead first.

Then run step 1, ask the one question in step 1b, and run step 2 straight
through.

### 1. Check what the app is running

```bash
cd "$SKILL_DIR" && python3 inspect_tokens.py | head -3
```

Compare the reported version against `verified_against` in `binding.json`. If
they differ, note it — the bindings may need re-deriving (see
[When generate.py warns](#when-generatepy-warns)), but a mismatch alone is not a
problem.

### 1b. Confirm the chat text size

Read `settings.json`. If it sets `chat_text_size`, say what it is and keep it -
do not re-ask on every reapply. If the file or the key is missing, ask once:

> Claude's chat text is fairly small - about 15px even on its Large setting. Do
> you want a specific size (17-18px reads comfortably), or keep the app's own?

Write their answer as `{"chat_text_size": <px>}` to `settings.json`; "keep the
app's" means leave the key out. A number in px is all that is needed - see
[Chat text size](#chat-text-size) for what it drives.

### 2. Regenerate the stylesheet

```bash
cd "$SKILL_DIR" && python3 generate.py
```

Unprivileged and deterministic — it only rewrites `claude-theme.css` here.
Resolve any `WARN:` lines before going on. No warnings and a matching version
means nothing needs investigating.

### 2b. Build and verify the patched archive

```bash
cd "$SKILL_DIR" && python3 build_asar.py
```

Still unprivileged: it reads the installed `app.asar` and writes
`app.patched.asar` here. It refuses to emit anything it cannot prove sound —
valid JavaScript, every entry present, only the main entry changed, every
integrity hash matching its payload. If it exits non-zero, stop and report why;
do not proceed to the install.

(`apply.sh` runs this itself, so this step is really a dry run that lets you show
the user a verified result before asking for anything.)

### 3. Report, then show the gated command and wait

Three things, in this order:

1. **What you just ran and what it said** — the installed version, whether it
   matched `verified_against`, whether the CSS regenerated without warnings, and
   the archive verification result.
2. **The command you want to run next, verbatim**, with what it changes and how
   to undo it: it replaces `app.asar` in the discovered installation (`apply.sh`
   prints the path), needs root, backs the original up to `app.asar.orig` first
   and always rebuilds from that original so it cannot stack, and `./revert.sh`
   puts the stock app back.
3. **An explicit ask** — confirm they are ready, and warn that a password prompt
   may appear so it does not catch them mid-sentence.

Also give them the revert command *before* they restart. A bad main-process
patch means the app will not launch, and at that point this session's window is
gone too — they need the way back already in hand.

```bash
cd "$SKILL_DIR" && ./apply.sh
```

Then stop. Do not run it in the same turn.

### 4. Apply

Run it only once the user has agreed.

How root is obtained depends on the system: usually a graphical password
dialog, but nothing at all if sudo credentials happen to be cached. Do not
promise a dialog - say it needs root and that a prompt may appear.

If a dialog appears and they dismiss it, `pkexec` exits 126 with
`Request dismissed`. That is
a cancellation: say so, confirm nothing was changed, and stop. Do not retry, do
not fall back to another escalation route, do not suggest a NOPASSWD rule
unless the user raises it.

### 5. Restart the app

The theme only appears after the process cycles — Electron reads `app.asar`
once at startup.

**On this machine, neither the tray's Quit nor the window's close button
actually kills the app.** Both leave the process running, so the theme appears
not to have applied. Do not tell the user to quit from the tray; it does not
work here. There is also no reload shortcut — the only `reload` calls in the
bundle are internal ones for the Cowork artifact window, and `CmdOrCtrl+R` is
not bound.

Killing it needs care, because the session talking to the user is usually
running *inside* the app: a plain `pkill && relaunch` chain dies halfway,
killing the app but never reaching the relaunch. Detach first, so the restart
survives its own parent being killed:

```bash
setsid bash -c 'sleep 1; pkill -f "$(dirname "$(readlink -f "$(command -v claude-desktop)")")/claude-deskto[p]"; sleep 3; claude-desktop' >/dev/null 2>&1 &
```

The bracket in `deskto[p]` stops the pattern matching its own command line —
`pkill -f` otherwise matches the shell running it and kills that instead.

Warn the user that the window will disappear and come back, and confirm they are
ready before running it.

## Reverting

Same shape — show the command, get agreement, then run it.

```bash
cd "$SKILL_DIR" && ./revert.sh
```

## How root is reached

Only the final install is privileged, and it is isolated in `_root-helper.sh`.
`_escalate.sh` chooses the route:

1. cached `sudo` credentials, if any;
2. otherwise **`pkexec`** when a desktop session is present — it raises a
   graphical dialog, which is what lets an agent run this at all, since `sudo`
   wants a password on stdin that an agent cannot supply;
3. otherwise `sudo`, prompting in the terminal.

`CLAUDE_THEME_FORCE_SUDO=1` skips pkexec for terminal-only use.

## How the pieces divide up

| File | Owns | Changes when |
|---|---|---|
| `themes/*.json` | Palettes: semantic role -> colour, light/dark, in OKLCH | The user wants different colours |
| `binding.json` | Which Claude token each Ocean role drives, and how the chat text size is reached | Claude Desktop renames or restructures its tokens |
| `settings.json` | The user's non-colour choices (`chat_text_size` in px). Local and untracked; absent means app defaults | The user wants a different text size |
| `generate.py` | Rendering one from the other | Rarely |
| `colour.py` | OKLCH ↔ sRGB ↔ HSL maths | Never |
| `app_tokens.py` | Reading the installed build's stylesheet for token names | The app moves its assets |
| `injection.js` | The main-process code that inserts the CSS into the page | Electron's API changes |
| `asarlib.py` | Reading and rewriting .asar archives | The asar format changes |
| `build_asar.py` | Building and verifying the patched archive | The entry point stops being declared in package.json |
| `apply.sh` / `revert.sh` / `_root-helper.sh` | Installing and uninstalling | Never |

Colour *values* live in `themes/*.json` and never move. Only the *binding*
is expected to rot. Keeping those separate is what makes the theme survive
updates: a rename breaks one line in `binding.json`, not the palette.

## When generate.py warns

A `WARN: token --x not found in this build` means the app renamed or dropped
something. Re-derive just that binding:

```bash
python3 inspect_tokens.py                  # semantic surface/text/border tokens
python3 inspect_tokens.py --grep surface   # search by substring
python3 inspect_tokens.py --ramp --cds-gray-
```

Find the token that now plays the old one's role, update `binding.json`, bump
`verified_against` to the version `generate.py` reports, and re-run. Do not
delete a binding just to silence a warning — say which role went unmapped.

## The live stylesheet is the source of truth

**Do not derive bindings from `resources/ion-dist/`.** That bundle is a
different build from the one the window renders, and it contains whole token
families the live app does not have. Mapping `--z0`, `--t1`, `--surface-primary`
and `--fill-assistant-code` from it produced overrides that silently did
nothing, because none of those exist live.

The live sheets come from a CDN and need no auth (a direct fetch of claude.ai
itself gets a 403 from Cloudflare, but the assets do not):

```bash
strings -a ~/.config/Claude/Cache/Cache_Data/* \
  | grep -oaE "https://assets-proxy\.anthropic\.com/[A-Za-z0-9._/-]*\.css" | sort -u
curl -s -o /tmp/live-main.css "https://assets-proxy.anthropic.com/claude-ai/v2/assets/v1/<hash>.css"
```

There are several, and they are not interchangeable: `--cds-*` lives in the big
`c6a992d55-*` chunk, while every `--df-*` token lives in `shared-styles-*`.
Check all of them before concluding a token is absent.

Verify any new binding by loading the live sheets plus `claude-theme.css` in a
browser with a mock DOM (`html.cds-root[data-mode=dark]` > `.dframe-root` >
`.dframe-sidebar`) and reading the computed values. That catches a dead
override in seconds instead of after a restart.

## Overrides must land on the declaring element

Custom properties inherit, but **a declaration on the element itself beats an
inherited one, even an inherited `!important`**. So an override on `<html>` is
useless for any token the app declares further down.

- `--cds-*` are declared on `<html>` itself (it carries `class="cds-root"`), so
  the `selectors` blocks reach them.
- `--df-*` are declared on `.dframe-root`, `.dframe-sidebar`, `.dframe-card`,
  `.dframe-sidebar-body` and `.epitaxy-root .dframe-root`. These need
  `element_pins` in `binding.json`, which emits blocks scoped to those elements.

When an override provably resolves correctly in isolation but changes nothing in
the app, this is the first thing to check.

## What was true of build 1.40609.0

Verify anything here that the current build contradicts; it is a starting point,
not gospel.

- **The window renders `https://claude.ai`.** Local Storage holds only
  `claude.ai` origins and no `app://` one, and the HTTP cache holds claude.ai
  assets. The bundled renderer at `resources/ion-dist/` is registered behind an
  `app://` protocol handler but is not what the user sees — **patching its CSS
  changes nothing**. Do not repeat that experiment.
- `resources/ion-dist/assets/v1/*.css` is still the best *reference* for token
  names, since it is the same design system the live page uses. Read names from
  it; deliver the CSS through the injection.
- Asset filenames there are content hashes (`c6a992d55-iGxCOsRk.css`) and change
  every release. **Locate the stylesheet by a token it declares**, never by name.
- That file is ~1 MB of minified Tailwind v4. **grep it; never Read it** — it
  will swallow the context window for the sake of a few numbers.
- Electron fuses on the binary: `OnlyLoadAppFromAsar` ENABLED (so a
  `resources/app/` directory is never loaded — repacking is the only route) and
  `EnableEmbeddedAsarIntegrityValidation` ENABLED (per Electron's docs that check
  is macOS/Windows only, which is why a repacked archive loads on Linux).
- The main process refuses to start if `argv` contains any of sixteen debugging
  or network-override switches — `remote-debugging-port` among them. The override
  needs `CLAUDE_CDP_AUTH`, a token verified against an ed25519 key compiled into
  the app. **Never attempt to forge it**; CDP injection is not an available route.
- `app.asar` deduplicates identical files by pointing several entries at one
  offset (fonts shared across five renderer bundles). `asarlib.repack` preserves
  that; a naive rebuild inflates the archive by ~2.4 MB.
- Two token systems are live at once, and the UI uses both:
  - **CDS** (`--cds-*`, `data-color-version="v2"`) — plain hex, ~789 tokens.
    Semantic (`--cds-surface-0..3`, `--cds-text-primary`, `--cds-border-*`) over
    primitive ramps (`--cds-gray-*`, 35 steps, plus aqua/blue/violet).
  - **Legacy** (`--bg-*`, `--text-*`, `--border-*`, `--accent-*`, `--brand-*`) —
    bare `H S% L%` triplets, because the app wraps them in `hsl(var(--bg-100))`.
    **Never emit `hsl(...)` for these**, only the three components.
- `<html>` carries `class="cds-root"` *and* `data-theme="claude"` *and*
  `data-mode`, so one selector reaches both systems.
- `data-mode` is `light`, `dark`, or **`system`** — the third follows the OS, so
  it needs a `prefers-color-scheme` guard. All three are emitted.
- Overrides use `!important` rather than out-specifying the app. The app's own
  rules run to 4-attribute selectors, and `!important` keeps working when those
  change. Note that inheritance does not help here: `.cds-root` declares these
  tokens on `<html>` itself, so the override must land on the same element.
- There is a second, unexposed palette in the stylesheet: `[data-theme=console]`.

## Changing the theme: the interactive flow

This is an **interactive** skill, not a config file. When the user wants a
different theme, do not hand them a list of 21 roles to fill in.

### 1. Ask what they want to look like

Offer routes, best fidelity first:

- **Something on this machine.** Highest fidelity and no taste required from
  them - this is how `themes/ocean.json` was captured, exactly, from t3code.

  **This is intrusive: name the app and ask first.** Extracting a palette means
  reverse-engineering another installed application - unpacking its AppImage or
  asar, reading its bundles and sourcemaps. Say which app, what you will read,
  and roughly how much disk it needs, then wait. Do not go looking through
  their filesystem for candidates unprompted.

  Places worth asking about: other Electron apps' bundles, VS Code / shiki theme
  JSONs, terminal configs (Ghostty, Alacritty, Kitty), GTK themes.

  Extraction is best-effort - t3code worked because AppImage -> asar ->
  sourcemap -> `themePalettes.ts` happened to be traceable; another app may
  expose nothing.

  **Clean up afterwards.** Unpacking t3code cost ~745 MB (494 MB AppImage tree +
  251 MB asar) and that was left on disk for the whole build. Delete extracted
  trees once the palette is captured - the palette JSON is all that is needed,
  and it is a few kilobytes.
- **A named theme.** Dracula, Nord, Catppuccin, Gruvbox, Rose Pine - published
  palettes with known values.
- **Their own colours**, however many they have.

### 2. Map what they gave you, and run generate.py

Write the palette to a theme JSON keyed by role name. Whatever roles it does
not define simply go unmapped - that is expected, not a failure.

### 3. Report what could NOT be coloured, and offer to fill it

`generate.py` ends with an `UNMAPPED:` block listing every role the theme does
not define and which tokens or rules it affects. Put that to the user as a
decision, in their terms:

> Your theme covers 14 of the 21 roles. These 7 have no colour in it, so
> they keep Claude's own: `warning`, `success`, `errorSurface`, ...
> Want me to leave them, or derive them from the colours you did give me?

If they want them filled, **derive and write the values into the theme file**,
marked as derived - do not invent them at render time and lose the provenance.
Derive by relating to roles they did give: a surface one step off `canvas`, a
muted text between `text` and the background, an accent hue rotated from theirs.

### 3b. Ask about the text size

If `settings.json` sets no `chat_text_size`, ask as in
[step 1b](#1b-confirm-the-chat-text-size). A new palette is a natural moment to
fix the size too.

### 4. Never reduce what is customisable

Every one of the ~131 customisation points stays individually addressable
through `binding.json`, whatever the theme provides. Derivation only fills what
the user left unspecified; it is a convenience, never a cap. If someone wants
one specific token a specific colour, that must always be possible.

### Before installing, preview

Render a swatch sheet or a mock DOM (see
[Verifying a change without a restart](#verifying-a-change-without-a-restart))
and show it. One confident install beats twenty restarts of guessing.

## Coverage: what this theme does and does not reach

Check this before promising the user anything.

### Working

| Surface | How |
|---|---|
| Main content, sidebar, panels, popovers | `hex_pins` + `element_pins` |
| Window controls (minimise/maximise/close) | `titlebar.json` via `setTitleBarOverlay` |
| Activity dots | `rules` - see states below |
| Inline code chips | `raw_rules`, t3code's values at a larger size |
| Chat text size | `chat_text_size` in `binding.json`, driven by `settings.json` - see [Chat text size](#chat-text-size) |
| Assistant text hierarchy | `rules` on `.prose` |
| Greys, borders, stray hardcoded colours | `ramp_tints`, `triplet_tints`, `rules` |

### Activity dot states

Four `data-kind` values plus a separate three-dot cluster. Only the first two
are themed; `awaiting` keeps its warning amber deliberately, because
yellow-means-attention is real signal, and `clay` is a background image.

| State | Themed to | Motion |
|---|---|---|
| `running` | `accent` `#70b9ee` | blinking |
| `.dframe-dot` (x3 cluster) | `accent` `#70b9ee` | pulsing, staggered |
| `ready` | `messageAction` `#5bd0d6` | solid |
| `awaiting` | left stock (amber) | solid |
| `clay` | left stock (image) | breathing |

Running and ready differ in **hue and motion**, so they stay distinguishable
without relying on colour alone.

### Unreachable - do not re-attempt

- **Terminal panels** (`.group/terminal`, `.xterm-*`): xterm with the WebGL
  renderer. Three canvases; the background is painted INTO the canvas, so CSS
  colours the element underneath for one frame and is overdrawn. No `Terminal`
  instance is exposed on the DOM, only React's private fiber.
- **Chrome DevTools Protocol**: the main process refuses to start if `argv`
  contains any of sixteen debugging switches, and the override needs
  `CLAUDE_CDP_AUTH`, a token verified against an ed25519 key in the binary.
  Never attempt to forge it.

### Unresolved - open, with a starting point

- **Markdown code block background** (`.epitaxy-codeblock`). This is a
  *different component* from the terminal and is ordinary DOM, so it is
  probably reachable - but four probes failed to identify what paints it.
  Walking up from the block finds no opaque ancestor; the only child caught was
  an absolutely-positioned span at `-z-[1]`, and colouring that did nothing.
  If resuming: first confirm the class still exists **and** that the user script
  runs in the frame rendering the conversation. One of those assumptions is
  likely wrong.
- **Comment colour in code** is Claude's stock, deliberately faint. The
  code-theme preference does move it (proven), but `material-theme-ocean` makes
  it dimmer, not brighter. See `claude-theme.js` for the enabled-but-commented
  `setCodeTheme()` helper.

### Untested

**Light mode.** Every value is generated for both modes, but this was built and
judged entirely in dark. Treat the light palette as unverified.

## Answering DOM questions without asking the user

Do not ask the user to open devtools and paste results - that is the skill
doing its work through them. Instead write a probe in `claude-theme.js` that
stores findings in `localStorage`, then read them off disk:

```bash
strings -a ~/.config/Claude/Local\ Storage/leveldb/* | grep -oa '"marker".\{0,2000\}' | tail -1
```

Costs one restart and nothing else. Four probes failed here before one worked;
the traps, all of them cheap to avoid once known:

- `rgba(0,0,0,0)` parses to `[0,0,0,0]`, so a "near-black" test that checks only
  the three colour channels matches every **transparent** element and fills its
  results before seeing anything real. Require alpha.
- The message list **virtualises**: a code block only exists in the DOM while on
  screen. Poll on an interval until found rather than sampling at fixed times.
- The injection runs in **every** webContents, so a later empty view can
  overwrite a good sample. Keep the richest result, never overwrite with worse.
- Confirm the app actually restarted after the probe was written - compare
  `ps -o lstart=` against the file mtime - before concluding it found nothing.

## Platform

**Never assume an installation path.** `app_tokens.install_root()` discovers it:
`CLAUDE_DESKTOP_ROOT` if set, then the launcher on `PATH`
(`claude-desktop`/`claude`) resolved through its symlink, then a short list of
known locations - and a candidate only counts if it really contains
`resources/app.asar`. If none match it says so and asks for the env var rather
than guessing. Everything downstream takes the path from there, including the
privileged helper, which receives it as an argument.

Built and verified on Linux with the `.deb` build. On another platform you may
be able to make it work, but you will have to adapt these instructions to the
user's system yourself - and say so rather than pretending it is supported.
Note that ASAR integrity validation is enforced on macOS and Windows but not
Linux, so a plain repack is rejected there; `platforms/` in the repo has notes.

## Setting this up on a fresh machine

Everything needed is in this directory. **No investigation is required and
no palette capture is needed to get started** - `themes/ocean.json` is already
included as a worked example (57 roles x light/dark, in OKLCH).

Prerequisites: `python3`, `node` (for the syntax check - the build warns and
continues without it), and `pkexec` with a polkit agent, or `sudo`.

```bash
cd "$SKILL_DIR"
python3 inspect_tokens.py | head -3      # confirm the app is found
python3 generate.py --theme ocean        # -> claude-theme.css + titlebar.json
./apply.sh                               # builds, verifies, installs (needs root)
```

Themes live in `themes/`. `--theme NAME` picks one, or pass a path to any palette
JSON. `ocean` is included as a worked example - its palette comes from t3code's
theme of the same name, credited in the file. Offer it, but do not assume it is
what the user wants; most people will bring their own.

Then restart the app (see [Restart the app](#5-restart-the-app)).

Paths are resolved at build time from the skill's own location, so a different
username or install path needs no edits. The only machine-specific assumption
is that the installation can be found - see [Platform](#platform).

If the app has moved on and `binding.json`'s `verified_against` no longer
matches, run `generate.py` and resolve any `WARN:` lines before installing -
those name the tokens that no longer exist.

## Extending the theme: binding.json

Every colour decision lives in `binding.json`. Nothing is hard-coded in the
scripts. Pick the right section for the job - the wrong one fails silently.

| Section | Emits | Use when |
|---|---|---|
| `hex_pins` | `--token: #hex !important` on `<html>` | the app declares the token on `<html>` and consumes it as a full colour |
| `triplet_pins` | `--token: H S% L% !important` | legacy tokens the app wraps in `hsl(var(--x))` - **never emit `hsl(...)` for these** |
| `triplet_tints` | keeps the app's own lightness, swaps hue | alpha-composited tokens such as borders, where a pinned mid-tone would vanish |
| `ramp_tints` | recolours a numbered primitive ramp | `--cds-gray-*` (hex) and `--cds-hsl-gray-*` (triplets); `format` selects which |
| `element_pins` | tokens scoped to a selector | the app declares the token **below** `<html>` - see the inheritance trap |
| `rules` | real property declarations | the value is hard-coded in the app, or the token is shared and cannot be repointed |
| `raw_rules` | verbatim CSS | anything that is not a colour mapping - borders, padding, generated content |

Values are **role names** from the active theme in `themes/` (`canvas`, `sidebar`,
`text`, `codeBackground`, ...) or a literal `#hex`. `rules` accepts either;
`raw_rules` is written out as-is. Add `"modes": ["dark"]` to any rule that
targets a mode-specific utility.

### The inheritance trap

Custom properties inherit, but **a declaration on the element itself always
beats an inherited one - even an inherited `!important`**. So an override on
`<html>` is useless for any token the app declares further down.

- `--cds-*` are declared on `<html>` (it carries `class="cds-root"`) -> `hex_pins`
- `--df-*` are declared on `.dframe-root`, `.dframe-sidebar` and friends ->
  `element_pins`

When a rule provably resolves correctly in isolation but changes nothing in the
app, check this first.

### Verifying a change without a restart

Load the live stylesheets plus `claude-theme.css` in a browser with a mock DOM
and read the computed values. This catches a dead override in seconds instead
of after a restart, and it is how the sidebar and dot rules were confirmed:

```html
<link rel="stylesheet" href="live-shared.css">
<link rel="stylesheet" href="live-main.css">
<link rel="stylesheet" href="theme.css">
<div class="dframe-root"><div class="dframe-sidebar" id="s"></div></div>
<script>
  document.documentElement.className = "cds-root";
  document.documentElement.setAttribute("data-mode", "dark");
  console.log(getComputedStyle(document.getElementById("s"))
    .getPropertyValue("--df-web-sidebar-bg"));
</script>
```

Steps smaller than ~5% OKLCH lightness are **not perceptible** - move in
visible jumps or a restart is wasted.

## Chat text size

The app's own Text size setting (Settings -> Appearance: Small / Medium /
Large) tops out low: at Large, message text renders at **15px**, not the 16px
its stylesheet suggests. `settings.json` replaces it with an exact size:

```json
{ "chat_text_size": 18 }
```

**Changing the size needs no `apply.sh` and no password.** The injection reads
`claude-theme.css` from this directory on every `dom-ready`, so a size change is:

```bash
cd "$SKILL_DIR" && python3 generate.py     # prints "chat text size: 18px"
```

then a restart of the app. `apply.sh` is only for the archive itself (first
install, or after an app update). To go back to the app's own sizes, remove the
key and regenerate.

### How it is reached

Two layers each set their own size, and **both** must be overridden - this
cost two failed restarts to establish:

1. **The transcript container**, `.epitaxy-transcript-typography`, declares
   `--chat-body` (13 / 14 / 16px for Small / Medium / Large, from
   `[data-chat-text-size]` on `<html>`). Tool calls and status lines use it.
2. **Each message**, `[data-cds=AssistantMessage]` / `[data-cds=UserMessage]`,
   re-declares `--chat-body` and its own `--cds-font-size-prose*`,
   `--cds-font-size-body` and `--cds-font-size-heading` tokens. Message text
   reads *these*, so overriding only the container changes the gaps between
   rows and leaves every paragraph exactly where it was.

`generate.py` emits one knob, `--theme-chat-text: <px>` on `body`, and the
rules in `binding.json`'s `chat_text_size` derive everything from it: the
container's `--chat-body`, and on each message the prose/body sizes plus the
smaller (x .9333) and larger (x 1.0667) steps in the app's own Large-setting
ratios. **The app's line heights are fixed rem values**, so the rules rebuild
them from the sizes too (x 1.43-1.5) - otherwise larger text overlaps.

Nothing is emitted when no size is set: the derived rules reference the knob,
and an undefined knob would make every one of those tokens invalid.

The stylesheet is inserted with `cssOrigin: "user"`, so its `!important` beats
the page's own declarations whatever their specificity; the rules need no
selector tricks. Inline code chips keep their own fixed size (`raw_rules`).

### If an update breaks it

The symptom is a size change that moves the spacing but not the text - a new
layer re-declaring the tokens. Probe it (see
[Answering DOM questions](#answering-dom-questions-without-asking-the-user)):
take a `.prose p`, walk up its ancestors, and record each one's computed
`font-size`, `--chat-body` and `--cds-font-size-prose`. The element where the
values change from the knob's to the app's is the one the rules must also
target.

## Where each thing is actually styled

Four independent channels. Knowing which one owns a surface is most of the work.

| Surface | Owned by | Notes |
|---|---|---|
| App chrome, sidebar, surfaces | `--cds-*` / `--df-*` CSS tokens | `claude-theme.css` |
| Window controls | Electron `titleBarOverlay` | `titlebar.json`, set by the injection |
| Code **token** colours | the app's own code-theme preference | `claude-theme.js` |
| Terminal panels | xterm + WebGL canvas | **unreachable** - see below |

### The markdown container is `.prose`

**`.ReactMarkdown` does not exist in this app.** Rules written against it match
nothing and fail *silently* - no warning, no error, just no effect. This cost
several rounds of "make it greyer" that changed nothing at all. Verify a
container exists before trusting a selector.

### Code theme is a real setting, not something to override

The syntax colours come from a built-in preference that ships ~25 themes,
including `material-theme-ocean` - the one t3code uses. There is no picker in
the UI, so the user script sets it directly.

The authoritative store is the zustand-persisted localStorage key
`epitaxy-editor-prefs` = `{state:{...}, version:N}`. The `LSS-epitaxy:*` keys
are **only a one-time migration source** and are skipped entirely once the main
store holds a value - writing them alone does nothing.

Fighting this with CSS is what produced the "correct for a split second, then
black again" symptom. Set the preference instead.

### Terminals cannot be themed

`.group/terminal`, `.xterm-*` are xterm with the WebGL renderer: three canvases,
and the background is painted **into** the canvas. CSS colours the element
underneath for one frame and is then overdrawn. No `Terminal` instance is
exposed on the DOM - only React's private fiber - so changing it would mean
walking React internals, which breaks on any update. Treat as closed.

Note that Material Ocean's own `editor.background` is `#0F111A`, nearly black.
So "the code block is still black" can mean the theme applied *correctly* - not
that an override failed. t3code paints its blocks with its palette colour and
uses the theme only for tokens.

## Text ladder

t3code puts body and headings on one colour and separates them by weight
(`--appearance-contrast-boost` is `0%`). That read too flat here, so this ladder
is **derived**, not a t3code value:

| Element | Colour |
|---|---|
| `.prose h1`-`h6` (and descendants) | the palette's `text` |
| `.prose strong`, `b` | `#e0dce4` |
| `.prose p`, `li`, `td`, `dd` | `#c2c2cb` |
| `.prose blockquote`, footnotes | `#9fa0ac` |

Steps smaller than ~5% OKLCH lightness are **not perceptible** here - move in
visible jumps or a restart is wasted.

## Values taken from t3code verbatim

Resolved through the example palette, not invented:

- inline code chip - `.chat-markdown :not(pre)>code`: background `--muted`
  `#233544`, border `--contrast-border` `#405567`, text `--foreground`
  `#fffaff`, radius `.375rem`, padding `.1rem .35rem` (t3code's font-size
  `.75rem` is raised to `.875rem` - it reads too small beside Claude's body text)
- code block surface - `--code-background` `#252e38`

## Mapping notes worth keeping

- **`--cds-surface-1` is the MAIN content surface, not the sidebar** —
  `<body class="bg-surface-1">`. Getting this backwards inverts the two panels.
  The sidebar is `--df-sidebar-bg` / `--df-web-sidebar-bg`, which Claude
  *derives* by darkening the page:
  `color-mix(in srgb, hsl(var(--df-bg-page-hsl)) 80%, black)`. Ocean's sidebar
  is *lighter* than its canvas, the opposite relationship, so both ends are
  pinned explicitly and the derivation is overridden.
- `--df-*` is the frame-level chrome family — page, sidebar, titlebar. When a
  panel still looks wrong after the surfaces are mapped, look here first.
- The legacy `--bg-*` scale assumes 200/300 are *darker* than 100, so those stay
  at canvas rather than taking Ocean's lighter sidebar.
- Ocean's `textMuted` is darker than its `mutedForeground`, the opposite of
  Claude's secondary/muted order — they are pinned crossed over on purpose.
- Tokens the palette has no equivalent for are **tinted**, not pinned: the app's own
  lightness is kept and only the hue is swapped, so nothing stays warm grey next
  to Ocean's cool surfaces. Borders must be tinted rather than pinned because the
  app alpha-composites them, and a mid-tone at 20% opacity vanishes.
- The `--cds-gray-` ramp is retinted with `C = 0.035·4L(1−L)`, a curve that
  happens to track Ocean's own surface chroma closely across the range.

## Where the example palette came from

t3code ships as an AppImage (wherever it is installed). The palette is in
`packages/shared/src/themePalettes.ts` as `OCEAN_THEME`, recoverable from the
sourcemap of `apps/server/dist/client/assets/textarea-*.js.map` inside its
`app.asar`. Re-extract only if the user wants to resync with a newer t3code.
