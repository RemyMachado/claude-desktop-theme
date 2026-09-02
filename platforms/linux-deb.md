# Linux — Debian/Ubuntu (.deb)

**Status: reference implementation.** Fully working and verified against
Claude Desktop `1.40609.0`.

| Thing | Value |
|---|---|
| Install root | `/usr/lib/claude-desktop` |
| Archive | `resources/app.asar` |
| Launcher | `/usr/bin/claude-desktop` → `../lib/claude-desktop/claude-desktop` |
| Version | `dpkg-query -W -f='${Version}' claude-desktop` |
| Updates via | apt (`/etc/apt/sources.list.d/claude-desktop.list`) — replaces the archive |
| Escalation | `pkexec` (GUI dialog), falling back to `sudo` |
| ASAR integrity | fuse enabled but **not enforced on Linux** — repack works as-is |

## Restarting

Neither the tray's Quit nor the window close button kills the app, and there is
no reload shortcut. Detach before killing, or the restart dies with its parent:

```bash
setsid bash -c 'sleep 1; pkill -f "/usr/lib/claude-desktop/claude-deskto[p]"; sleep 3; claude-desktop' >/dev/null 2>&1 &
```

## Other distros

Should be straightforward — same archive format, same injection. Re-derive the
install root by following the launcher (`readlink -f $(which claude-desktop)`),
and the version from the package manager or from `package.json` inside the asar.
