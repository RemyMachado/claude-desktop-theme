# claude-desktop-theme

Claude Desktop ships no colour settings beyond light and dark. This is a
[Claude Code](https://claude.com/claude-code) skill that themes it properly.

Bring a palette — or point it at a theme you already have — and it maps that
onto the app, applies it, and reapplies after updates.

## How it works

The desktop app renders `claude.ai` remotely rather than a local bundle, so
there is no stylesheet to edit. Instead the skill repacks the app's `app.asar`
with a small injection in the Electron main process, which applies three things
on every page load:

- a generated **stylesheet** (~131 customisation points)
- the native **window-control colours**, which no stylesheet can reach
- an optional **user script**, for anything CSS cannot express

Those files are re-read on each load, so only the first install needs a repack
and root access. Colour changes after that are an edit and a restart.

## It is interactive

You say what you want it to look like. The skill maps it, then tells you which
roles your palette did not cover and asks whether to leave those alone or derive
them from the colours you did give. It never silently invents values, and it
never reduces what is customisable — derivation fills gaps, it is not a cap.

## Install

Clone it into your Claude Code skills directory — user-level:

```bash
git clone https://github.com/RemyMachado/claude-desktop-theme \
  ~/.claude/skills/claude-desktop-theme
```

…or into a single project, if you would rather it were scoped there:

```bash
git clone https://github.com/RemyMachado/claude-desktop-theme \
  .claude/skills/claude-desktop-theme
```

Then invoke it by name — `/claude-desktop-theme` — or just ask Claude Code to
theme your Claude Desktop. It introduces itself, shows you what it is about to
run, and waits before anything touches your system.

## Themes

`themes/` holds palettes; `generate.py --theme NAME` selects one.

`ocean` is included as a worked example. Its palette comes from
[t3code](https://t3.chat)'s theme of the same name, credited in the file — it is
there to demonstrate the capture workflow, not because you should necessarily
want it. Most people will bring their own.

[docs/capturing-a-palette.md](docs/capturing-a-palette.md) walks through lifting
an exact palette out of another installed app, which is how `ocean` was made.

## Platform

Built for **Linux with the `.deb` build** of Claude Desktop, which is the only
setup it supports. On another distro it is mostly path discovery; on macOS or
Windows it will tell you it has not been ported rather than guessing.

[`platforms/`](platforms/) holds notes for anyone who wants to take that on —
what differs, and the one real obstacle. Electron enforces ASAR integrity
validation on macOS and Windows but not Linux, so a repacked archive is rejected
there. That is two extra steps rather than a wall: recompute the header hash
(already implemented here) and write it where the platform expects it, plus an
ad-hoc re-sign on macOS. The `macos.md` and `windows.md` notes are inferred from
Electron's documentation, not verified on real installs.

The valuable parts are shared and done — asar repacking, the token map, the
injection. A port is mostly the integrity step plus paths.

Verified against Claude Desktop `1.40609.0`. It depends on undocumented
internals of a frequently-updated closed application, so expect occasional
re-derivation; the skill documents how.

## This is intrusive

Two operations deserve your attention before you run them:

1. **Patching the app** replaces `app.asar`, the application's own code archive.
   It edits executable JavaScript, not a stylesheet — a bad patch means the app
   will not launch. It is backed up to `app.asar.orig`, `./revert.sh` restores
   it, and nothing installs without an explicit confirmation.
2. **Capturing a palette from another app** means reverse-engineering software
   you did not ask to touch, and can cost hundreds of megabytes of temporary
   extraction. The skill names the app and asks first, then cleans up.

Also worth knowing: the user script is arbitrary JavaScript running inside an
authenticated Claude session. That is what makes the terminal and other
non-CSS surfaces reachable, and it is a real security surface. Read
`claude-theme.js` before installing, as you would any userscript.

## Contributing

Issues and PRs welcome, particularly:

- **Other platforms** — add a file to `platforms/`. macOS and Windows need the
  integrity-hash step described there; other Linux distros should be mostly
  path discovery.
- **More example themes** — Nord, Catppuccin, Gruvbox and friends are published
  palettes that map cleanly onto the role list.
- **Light mode** — every value is generated for both modes, but this was built
  and judged entirely in dark. The light palette is untested.

### Working on it

Clone anywhere and symlink, so the checkout *is* the live skill and edits take
effect without copying:

```bash
git clone https://github.com/RemyMachado/claude-desktop-theme
ln -s "$PWD/claude-desktop-theme" ~/.claude/skills/claude-desktop-theme
```

`claude-theme.css`, `titlebar.json` and `app.patched.asar` are build outputs and
gitignored — regenerate with `python3 generate.py`.

### Good first issues

- **Font sizes.** The skill only asks about colour. It could equally prompt for
  type sizes and apply them the same way — the app exposes `--cds-font-size-*`
  and a `chatTextSize` preference.
- **Derive the baked values.** Ten hard-coded hex values in `binding.json` (the
  retinted greys, the text ladder, the inline code chip) survive a palette swap
  silently. They should be expressions over palette roles, not literals.
- **Preview before install.** Render a swatch sheet from a candidate palette so
  a theme can be judged without a restart.
- **Reduce the role list.** Only 21 of Ocean's 57 roles are referenced; the
  contract could be stated explicitly rather than inherited from one palette.

## Licence

MIT. The `ocean` palette is credited to its authors and included as an example.
