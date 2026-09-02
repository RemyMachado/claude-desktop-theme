# macOS

**Status: not implemented.** Contributor notes only - nothing here is verified.

The paths below are inferred from Electron conventions, not tested on a real
install. Correct them rather than trusting them.

Everything about the injection is portable — same asar format, same Electron
main process, same three channels. Two extra steps are needed that Linux does
not require.

| Thing | Expected value |
|---|---|
| Install root | `/Applications/Claude.app/Contents` |
| Archive | `Resources/app.asar` |
| Version | `CFBundleShortVersionString` in `Contents/Info.plist` |
| Updates via | Squirrel.Mac self-updater |
| Escalation | `osascript -e 'do shell script "..." with administrator privileges'` |

## The two extra steps

`EnableEmbeddedAsarIntegrityValidation` is enabled, and **macOS enforces it**.
A repacked archive is rejected and the app terminates on launch. Per Electron's
docs the expected hash lives in `Info.plist` under an `ElectronAsarIntegrity`
dictionary, so:

1. **Update the stored hash.** `asarlib.py` already computes the header hash —
   that is the hard part, and it is done. Write the new value into
   `Contents/Info.plist` under `ElectronAsarIntegrity`.
2. **Re-sign the bundle.** Modifying `Info.plist` or `app.asar` breaks the code
   signature. An ad-hoc re-sign (`codesign -f -s - --deep /Applications/Claude.app`)
   is usually enough for a locally installed app, but this is the step most
   likely to need iteration.

## Dead ends — do not spend time here

- **Chrome DevTools Protocol.** The main process aborts if `argv` contains any
  of sixteen debugging switches. The override needs `CLAUDE_CDP_AUTH`, a token
  verified against an ed25519 key compiled into the binary. Never attempt to
  forge it.
- **`resources/app/` directory.** `OnlyLoadAppFromAsar` is enabled, and unlike
  the integrity fuse that one applies on every platform.
