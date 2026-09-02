#!/usr/bin/env python3
"""Render claude-theme.css from the Ocean palette plus the binding map.

Deterministic: same inputs always produce byte-identical output, so re-running
after an app update that changed nothing relevant is a no-op.

    python3 generate.py [-o claude-theme.css]
"""
import argparse, json, os, re, sys
import colour, app_tokens

HERE = os.path.dirname(os.path.abspath(__file__))

def load(name):
    with open(os.path.join(HERE, name), encoding="utf8") as f:
        return json.load(f)

def ramp_colour(stock_hex, cfg):
    """Keep the app's lightness for this ramp step, adopt Ocean's hue/chroma."""
    L, _, _ = colour.rgb_to_oklch(*colour.parse_hex(stock_hex))
    hue = cfg["hue_at_dark_end"] + (cfg["hue_at_light_end"] - cfg["hue_at_dark_end"]) * L
    chroma = cfg["chroma_max"] * 4 * L * (1 - L)
    return colour.to_hex(colour.oklch_to_rgb(L, chroma, hue))

def tint_triplet(stock, hue):
    """Legacy tokens are 'H S% L%'. Keep saturation and lightness, swap hue."""
    parts = stock.split()
    if len(parts) != 3 or not parts[1].endswith('%'):
        return None
    return f"{hue:.1f} {parts[1]} {parts[2]}"


def ramp_triplet(stock, ends):
    """Retint one step of an 'H S% L%' ramp.

    Keeps the app's lightness - the step's job in the scale - and takes hue and
    saturation from Ocean's own canvas at the matching end of the range, so the
    ramp lands on Ocean's colours at both extremes instead of a guessed curve.
    """
    parts = stock.split()
    if len(parts) != 3:
        return None
    lightness = float(parts[2].rstrip('%')) / 100
    (h_dark, s_dark), (h_light, s_light) = ends
    hue = h_dark + (h_light - h_dark) * lightness
    sat = s_dark + (s_light - s_dark) * lightness
    return f"{hue:.1f} {sat:.1f}% {parts[2]}"


def canvas_ends(palettes):
    """Hue and saturation of Ocean's canvas in each mode, as HSL."""
    def hs(oklch):
        h, s, _ = colour.rgb_to_hsl(*colour.oklch_to_rgb(*colour.parse_oklch(oklch)))
        return h, s * 100
    return hs(palettes["dark"]["canvas"]), hs(palettes["light"]["canvas"])

def build_declarations(palette, binding, app_modes, mode, warnings, ends):
    """One mode's worth of '--token: value !important;' lines."""
    stock = app_modes["dark" if mode == "dark" else "light"]
    base = app_modes["light"]
    lines = []

    def role(name, token):
        value = palette.get(name)
        if value is None:
            warnings.append(f"[{mode}] Ocean has no role '{name}' (for {token})")
        return value

    lines.append(f"  /* surfaces, text and accents pinned to Ocean */")
    for token, name in binding["hex_pins"].items():
        v = role(name, token)
        if v:
            lines.append(f"  {token}: {colour.oklch_hex(v)} !important;")

    lines.append(f"")
    lines.append(f"  /* legacy hsl-triplet tokens (the app wraps these in hsl()) */")
    for token, name in binding["triplet_pins"].items():
        v = role(name, token)
        if v:
            lines.append(f"  {token}: {colour.oklch_triplet(v)} !important;")

    # Borders keep the app's own lightness so alpha-composited edges stay visible.
    hue = colour.rgb_to_oklch(*colour.oklch_to_rgb(*colour.parse_oklch(palette["canvas"])))[2]
    hsl_hue = colour.rgb_to_hsl(*colour.oklch_to_rgb(*colour.parse_oklch(palette["border"])))[0]
    tinted = []
    for token in binding["triplet_tints"]:
        raw = app_tokens.resolve(token, stock, base)
        if raw is None:
            warnings.append(f"[{mode}] token {token} not found in this build")
            continue
        t = tint_triplet(raw, hsl_hue)
        if t is None:
            warnings.append(f"[{mode}] {token} is {raw!r}, not an hsl triplet - skipped")
            continue
        tinted.append(f"  {token}: {t} !important;")
    if tinted:
        lines += ["", "  /* borders: app lightness, Ocean hue */"] + tinted

    # Primitive ramps, so anything reading a raw grey shifts cool too. There are
    # two: the hex ramp, and the triplet ramp that feeds --z*/--t* and therefore
    # code blocks, dividers and the window chrome.
    for prefix, cfg in binding["ramp_tints"].items():
        kind = cfg.get("format", "hex")
        steps = app_tokens.ramp(base, prefix, kind)
        if not steps:
            warnings.append(f"[{mode}] ramp {prefix} not found in this build")
            continue
        lines += ["", f"  /* {prefix}* retinted from Ocean ({len(steps)} steps, {kind}) */"]
        for step, value in steps.items():
            new = ramp_colour(value, cfg) if kind == "hex" else ramp_triplet(value, ends)
            if new is None:
                warnings.append(f"[{mode}] {prefix}{step} is {value!r} - skipped")
                continue
            lines.append(f"  {prefix}{step}: {new} !important;")
    return lines

def element_blocks(binding, palette, mode, prefix, warnings):
    """Blocks for tokens the app declares on elements below <html>.

    Custom properties inherit, but a declaration on the element itself always
    beats an inherited one - even an inherited !important. The sidebar tokens
    live on .dframe-root / .dframe-sidebar, so an override on <html> never
    reaches them and silently does nothing.
    """
    out = []
    for group in binding.get("element_pins", []):
        sel = ", ".join(f"{prefix} {s}" for s in group["selector"].split(", "))
        kind = group.get("format", "hex")
        lines = []
        for token, role in group["pins"].items():
            value = palette.get(role)
            if value is None:
                warnings.append(f"[{mode}] Ocean has no role '{role}' (for {token})")
                continue
            rendered = colour.oklch_hex(value) if kind == "hex" else colour.oklch_triplet(value)
            lines.append(f"  {token}: {rendered} !important;")
        if lines:
            out.append(f"{sel} {{\n" + "\n".join(lines) + "\n}")
    return out


def rule_blocks(binding, palette, mode, prefix, warnings):
    """Real property declarations, for colours the app hardcodes to a token we
    cannot repoint without collateral damage.

    The pulsing activity dots are the case in point: they take
    `background: var(--cds-text-muted)`, so recolouring them via the token would
    turn every piece of muted text blue too.
    """
    out = []
    for group in binding.get("rules", []):
        # Some rules target a mode-specific utility (e.g. a dark:-only class) and
        # must not be emitted for the other mode, where the element is styled
        # differently and painting it would be wrong.
        if mode not in group.get("modes", ["dark", "light"]):
            continue
        sel = ", ".join(f"{prefix} {s}" for s in group["selector"].split(", "))
        lines = []
        for prop, role in group["declarations"].items():
            # A literal is used where the source is a palette Ocean does not
            # define - the Material Ocean syntax scopes, and greys retinted from
            # the app's own values.
            if isinstance(role, str) and role.startswith("#"):
                lines.append(f"  {prop}: {role} !important;")
                continue
            value = palette.get(role)
            if value is None:
                warnings.append(f"[{mode}] Ocean has no role '{role}' (for {prop})")
                continue
            lines.append(f"  {prop}: {colour.oklch_hex(value)} !important;")
        if lines:
            out.append(f"{sel} {{\n" + "\n".join(lines) + "\n}")
    return out


def raw_blocks(binding, mode, prefix):
    """Verbatim declarations, for anything that is not a colour mapping -
    a generated label, a layout tweak. Emitted as written."""
    out = []
    for group in binding.get("raw_rules", []):
        if mode not in group.get("modes", ["dark", "light"]):
            continue
        sel = ", ".join(f"{prefix} {s}" for s in group["selector"].split(", "))
        out.append(f"{sel} {{\n{group['css']}\n}}")
    return out


def render(palettes, binding, app_modes, version, warnings):
    ends = canvas_ends(palettes)
    sel = binding["selectors"]
    out = [
        "/* Claude Desktop - Ocean theme (from t3code's OCEAN_THEME).",
        " * GENERATED FILE - do not edit by hand.",
        " * Edit binding.json (or ocean-source.json) and re-run generate.py.",
        f" * Bindings verified against claude-desktop {binding['verified_against']};",
        f" * generated against {version}.",
        " */",
        "",
    ]
    for mode, palette in (("dark", palettes["dark"]), ("light", palettes["light"])):
        body = "\n".join(build_declarations(palette, binding, app_modes, mode, warnings, ends))
        prefix = f'html[data-mode="{mode}"]'
        blocks = [f"{', '.join(sel[mode])} {{", body, "}"]
        blocks += element_blocks(binding, palette, mode, prefix, warnings)
        blocks += rule_blocks(binding, palette, mode, prefix, warnings)
        blocks += raw_blocks(binding, mode, prefix)
        out += blocks + [""]

        # data-mode=system follows the OS, so guard that copy with a media query.
        query = "dark" if mode == "dark" else "light"
        sys_prefix = 'html[data-mode="system"]'
        inner = [f"{', '.join(sel['system'])} {{", body, "}"]
        inner += element_blocks(binding, palette, mode, sys_prefix, warnings)
        inner += rule_blocks(binding, palette, mode, sys_prefix, warnings)
        inner += raw_blocks(binding, mode, sys_prefix)
        out += [f"@media (prefers-color-scheme: {query}) {{"] + inner + ["}", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "claude-theme.css"))
    ap.add_argument("-t", "--theme", default=os.environ.get("CLAUDE_THEME", "ocean"),
                    help="theme name in themes/, or a path to a palette JSON")
    args = ap.parse_args()

    theme_path = (args.theme if os.path.sep in args.theme
                  else os.path.join(HERE, "themes", args.theme + ".json"))
    if not os.path.exists(theme_path):
        avail = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "themes"))
                       if f.endswith(".json"))
        raise SystemExit(f"no theme {args.theme!r}. Available: {', '.join(avail)}")
    with open(theme_path, encoding="utf8") as f:
        palettes = json.load(f)
    print(f"theme: {os.path.basename(theme_path)}"
          f"{' - ' + palettes['_name'] if '_name' in palettes else ''}")
    binding = load("binding.json")
    _, css = app_tokens.find_stylesheet()
    app_modes = app_tokens.collect(css)
    version = app_tokens.app_version()

    warnings = []
    text = render(palettes, binding, app_modes, version, warnings)
    with open(args.out, "w", encoding="utf8") as f:
        f.write(text)

    # The window control buttons (minimise / maximise / close) are drawn by
    # Electron, not the page, so no stylesheet can reach them. They are set
    # through titleBarOverlay, which the injection calls at runtime - so emit
    # their colours here, driven by the same palette as everything else.
    overlay = {
        mode: {
            "color": colour.oklch_hex(palettes[mode]["canvas"]),
            "symbolColor": colour.oklch_hex(palettes[mode]["text"]),
        }
        for mode in ("dark", "light")
    }
    overlay_path = os.path.join(os.path.dirname(args.out), "titlebar.json")
    with open(overlay_path, "w", encoding="utf8") as f:
        json.dump(overlay, f, indent=2)
        f.write("\n")

    print(f"wrote {args.out} ({len(text)} bytes) for claude-desktop {version}")
    print(f"wrote {overlay_path} (window controls: "
          f"{overlay['dark']['color']} / {overlay['dark']['symbolColor']})")
    if version != binding["verified_against"]:
        print(f"NOTE: bindings were verified against {binding['verified_against']}, "
              f"app is now {version} - check the result looks right.")
    # Roles the palette does not define are reported SEPARATELY from real
    # problems. They are not errors - they are the list of things this theme
    # cannot colour, which the skill puts to the user as a decision: leave the
    # app's own colour, or derive a value from the roles the theme does have.
    missing = {}
    other = []
    for w in dict.fromkeys(warnings):
        m = re.search(r"no role '([^']+)' \(for ([^)]+)\)", w)
        if m:
            missing.setdefault(m.group(1), set()).add(m.group(2))
        else:
            other.append(w)

    for w in other:
        print("WARN:", w)

    if missing:
        total = sum(len(v) for v in missing.values())
        print(f"\nUNMAPPED: the theme defines no colour for {len(missing)} role(s), "
              f"affecting {total} token(s)/rule(s):")
        for role in sorted(missing):
            targets = ", ".join(sorted(missing[role])[:6])
            more = len(missing[role]) - 6
            print(f"  {role:<22} -> {targets}{f' (+{more} more)' if more > 0 else ''}")
        print("These keep the app's own colour. Ask the user whether to leave them "
              "or fill them from the theme's other roles.")

    return 1 if other else 0

if __name__ == "__main__":
    sys.exit(main())
