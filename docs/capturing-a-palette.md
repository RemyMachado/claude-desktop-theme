# Capturing a palette from another app

The highest-fidelity way to theme this is to lift an exact palette out of
something you already like the look of. This is how the included `ocean` theme
was produced, and it doubles as the worked example.

**Ask first.** This means reverse-engineering another installed application and
can cost hundreds of megabytes of temporary extraction. Name the app, say what
you will read, and clean up afterwards.

## Worked example: t3code's Ocean

t3code ships as an AppImage. The palette turned out to be a plain TypeScript
object, reachable in four steps:

```bash
# 1. Unpack the AppImage (~500 MB extracted - clean up after)
/path/to/t3code.AppImage --appimage-extract

# 2. The renderer lives in an asar; extract it (~250 MB)
#    asarlib.py in this repo reads asar archives without Node.

# 3. The bundle ships sourcemaps, which carry the ORIGINAL TypeScript.
#    Search sourcesContent for a themes file:
#      apps/server/dist/client/assets/textarea-*.js.map
#      -> packages/shared/src/themePalettes.ts

# 4. That file defines OCEAN_THEME as ~57 named roles in OKLCH.
```

Sourcemaps are the trick worth remembering: a minified bundle often carries the
unminified source, so a palette that looks buried is frequently one `JSON.parse`
away.

## Other places worth trying

| Source | Where the colours live |
|---|---|
| VS Code / Cursor themes | `*.json` with `colors` + `tokenColors` |
| shiki / TextMate themes | same shape, often bundled in Electron apps |
| Terminals (Ghostty, Alacritty, Kitty) | plain config, 16 ANSI colours + fg/bg |
| GTK themes | CSS with `@define-color` |
| Published palettes | Nord, Catppuccin, Gruvbox, Rose Pine - documented hex |

## Mapping to roles

The palette needs the role names in `binding.json` (21 are referenced).
Anything missing is reported by `generate.py` as `UNMAPPED:` - that is a
decision to put to the user, not an error. See SKILL.md.

A terminal config gives you fg/bg/accent but no `surfaceRaised` or
`messageAction`; derive those from what you have, write them into the theme
file, and mark them derived so the provenance survives.
