#!/usr/bin/env python3
"""Build a patched app.asar carrying the Ocean CSS injection, and verify it.

The app renders claude.ai remotely, so the theme is injected into the page by
the Electron main process rather than patched into a local stylesheet. That
means editing the main entry, which means rebuilding the archive.

Nothing here touches the installed app; apply.sh does that.

    python3 build_asar.py [-o app.patched.asar]
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asarlib, app_tokens

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = app_tokens.asar_path()          # discovered, never assumed
CSS = os.path.join(HERE, "claude-theme.css")
OVERLAY = os.path.join(HERE, "titlebar.json")   # window control colours
SCRIPT = os.path.join(HERE, "claude-theme.js")  # user script run in the page
BACKUP = SRC + ".orig"
MARKER = b"ocean-theme injection"


def entry_path(src):
    """The main entry is declared in package.json, never guessed - which is what
    lets this survive updates that rename everything inside the bundle."""
    pkg = json.loads(asarlib.read_file(src, "/package.json"))
    main = pkg.get("main")
    if not main:
        raise SystemExit("package.json has no 'main' - the app structure changed")
    # removeprefix, not lstrip: lstrip would eat the dot in ".vite"
    return "/" + main.removeprefix("./")


def check_js(data):
    fd, tmp = tempfile.mkstemp(suffix=".js")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"patched entry is not valid JavaScript:\n{r.stderr}")
        print("patched entry: valid JavaScript")
    except FileNotFoundError:
        print("  ! node not found - skipped the syntax check")
    finally:
        os.unlink(tmp)


def verify(src, out, entry, patched, original):
    """Refuse to hand back an archive that is not provably sound."""
    if asarlib.read_file(out, entry) != patched:
        raise SystemExit("entry did not round-trip through the archive")
    if not patched.endswith(original):
        raise SystemExit("original bundle was not preserved")

    src_h, _ = asarlib.read_header(src)
    out_h, _ = asarlib.read_header(out)
    src_files = dict(asarlib.walk(src_h))
    out_files = dict(asarlib.walk(out_h))
    if set(src_files) != set(out_files):
        raise SystemExit("the set of files in the archive changed")

    changed = [p for p in src_files
               if "offset" in src_files[p]
               and asarlib.read_file(src, p) != asarlib.read_file(out, p)]
    if changed != [entry]:
        raise SystemExit(f"unexpected files differ from the original: {changed}")

    for path, meta in out_files.items():
        if "integrity" in meta and "offset" in meta:
            data = asarlib.read_file(out, path)
            if hashlib.sha256(data).hexdigest() != meta["integrity"]["hash"]:
                raise SystemExit(f"integrity hash does not match payload: {path}")
    return len(out_files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "app.patched.asar"))
    args = ap.parse_args()

    if not os.path.exists(CSS):
        raise SystemExit("no claude-theme.css - run 'python3 generate.py' first")
    if not os.path.exists(SRC):
        raise SystemExit(f"{SRC} not found - is claude-desktop installed?")

    # Always build from the pristine archive, so re-applying is idempotent and
    # injections can never stack. The backup exists whenever a patch is live.
    src = BACKUP if os.path.exists(BACKUP) else SRC
    if src == BACKUP:
        print(f"source: {BACKUP} (the installed archive is already patched)")

    entry = entry_path(src)
    print(f"entry point (from package.json): {entry}")

    original = asarlib.read_file(src, entry)
    if MARKER in original:
        raise SystemExit(
            "even the pristine archive carries an injection - "
            "run ./revert.sh and reinstall claude-desktop before retrying")

    with open(os.path.join(HERE, "injection.js"), encoding="utf8") as f:
        injection = (f.read()
                     .replace("__CSS_PATH__", CSS)
                     .replace("__OVERLAY_PATH__", OVERLAY)
                     .replace("__SCRIPT_PATH__", SCRIPT))
    patched = injection.encode("utf8") + b"\n" + original

    check_js(patched)
    asarlib.repack(src, args.out, {entry: patched})
    delta = os.path.getsize(args.out) - os.path.getsize(src)
    print(f"built {args.out} ({os.path.getsize(args.out):,} bytes, {delta:+,})")

    count = verify(src, args.out, entry, patched, original)
    print(f"verified: {count} entries intact, only {entry} differs, "
          "all integrity hashes match")


if __name__ == "__main__":
    main()
