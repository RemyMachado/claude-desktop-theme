#!/usr/bin/env python3
"""Show what the installed Claude Desktop build declares, resolved per mode.

Use this when re-deriving bindings after an app update:
    python3 inspect_tokens.py                 # semantic surface/text/border
    python3 inspect_tokens.py --grep accent
    python3 inspect_tokens.py --ramp --cds-gray-
"""
import argparse, re, app_tokens

SEMANTIC = re.compile(r'^--(cds-(surface|text|border|bg|icon)|bg-|text-|border-|accent-|brand-|oncolor-)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--grep")
    ap.add_argument("--ramp")
    args = ap.parse_args()

    path, css = app_tokens.find_stylesheet()
    print(f"# app {app_tokens.app_version()}\n# {path}\n")
    modes = app_tokens.collect(css)
    base = modes["light"]

    if args.ramp:
        names = [f"{args.ramp}{s}" for s in app_tokens.ramp(base, args.ramp)]
    elif args.grep:
        names = sorted(n for n in base if args.grep in n)
    elif args.all:
        names = sorted(base)
    else:
        names = sorted(n for n in base if SEMANTIC.match(n) and "-git-" not in n)

    if not names:
        print("no matching tokens"); return
    w = max(len(n) for n in names)
    print(f"{'token'.ljust(w)}  {'light'.ljust(24)}  dark")
    for n in names:
        lo = app_tokens.resolve(n, base, base) or "-"
        da = app_tokens.resolve(n, modes["dark"], base) or "-"
        print(f"{n.ljust(w)}  {lo[:24].ljust(24)}  {da[:34]}")

if __name__ == "__main__":
    main()
