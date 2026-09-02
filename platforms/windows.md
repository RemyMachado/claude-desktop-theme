# Windows

**Status: not implemented.** Contributor notes only - nothing here is verified.

The paths below are inferred from Electron conventions, not tested on a real
install. Correct them rather than trusting them.

| Thing | Expected value |
|---|---|
| Install root | `%LOCALAPPDATA%\AnthropicClaude\app-<version>` |
| Archive | `resources\app.asar` |
| Version | the versioned directory name, or `package.json` inside the asar |
| Updates via | Squirrel.Windows self-updater |
| Escalation | UAC — an elevated PowerShell, or a shortcut with "Run as administrator" |

## The extra step

`EnableEmbeddedAsarIntegrityValidation` is enabled and **Windows enforces it**.
Per Electron's docs the expected hash is stored as a **resource entry of type
`Integrity`, name `ElectronAsar`**, holding JSON with the file path, algorithm
and hash.

So a port must rewrite that resource in the executable after repacking.
`asarlib.py` already computes the header hash; the new work is editing a PE
resource section — awkward, but a solved problem with existing tooling.

Authenticode signing is not enforced for launch the way Gatekeeper is, so
re-signing is likely unnecessary.

## Dead ends — do not spend time here

Same two as macOS: CDP is gated behind an ed25519-signed token, and
`OnlyLoadAppFromAsar` rules out a `resources\app\` directory.
