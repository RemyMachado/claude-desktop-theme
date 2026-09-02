"""Read the design tokens out of the installed Claude Desktop build.

Single responsibility: know where the app keeps its stylesheet and what is
currently declared in it. Nothing here knows about Ocean or about theming.
"""
import os, re, glob, shutil, subprocess

# --- finding the installation ------------------------------------------------
# Nothing here assumes a path. The install root is discovered, because Claude
# Desktop lives in different places per platform and packaging.
#
# Order: an explicit override, then the launcher on PATH, then known locations.
# A candidate only counts if it actually contains resources/app.asar.

ENV_OVERRIDE = "CLAUDE_DESKTOP_ROOT"

# Hints, not assumptions - checked only after following the launcher.
CANDIDATES = [
    "/usr/lib/claude-desktop",              # Debian/Ubuntu .deb
    "/opt/Claude",
    "/opt/claude-desktop",
    "/usr/share/claude-desktop",
    os.path.expanduser("~/.local/share/claude-desktop"),
    "/Applications/Claude.app/Contents",    # macOS layout (untested)
]

LAUNCHERS = ["claude-desktop", "claude"]


def _looks_like_install(root):
    return os.path.isfile(os.path.join(root, "resources", "app.asar"))


def install_root():
    """Absolute path to the Claude Desktop installation.

    Raises with a useful message rather than guessing, so a user on an
    unfamiliar layout is told what to set instead of getting a confusing
    failure further down.
    """
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        if not _looks_like_install(override):
            raise SystemExit(
                f"{ENV_OVERRIDE}={override} does not contain resources/app.asar")
        return os.path.realpath(override)

    for name in LAUNCHERS:
        exe = shutil.which(name)
        if not exe:
            continue
        # The launcher is usually a symlink into the install directory.
        root = os.path.dirname(os.path.realpath(exe))
        if _looks_like_install(root):
            return root

    for root in CANDIDATES:
        if _looks_like_install(root):
            return os.path.realpath(root)

    raise SystemExit(
        "Could not find the Claude Desktop installation.\n"
        "Looked for a launcher on PATH (" + ", ".join(LAUNCHERS) + ") and in:\n  "
        + "\n  ".join(CANDIDATES) + "\n"
        f"Set {ENV_OVERRIDE} to the directory containing resources/app.asar.")


def resources_dir():
    return os.path.join(install_root(), "resources")


def asar_path():
    return os.path.join(resources_dir(), "app.asar")


def assets_dir():
    """Where the bundled renderer's stylesheets live.

    Only a REFERENCE for token names - the app renders claude.ai remotely, so
    nothing here is what the user sees. See SKILL.md.
    """
    return os.path.join(resources_dir(), "ion-dist", "assets", "v1")
# The asset filename is a content hash and changes every release, so the
# stylesheet is located by a token it is known to declare, never by name.
SENTINELS = ("--cds-surface-0", "--bg-000")

def find_stylesheet(assets=None):
    assets = assets or assets_dir()
    for path in sorted(glob.glob(f"{assets}/*.css")):
        text = open(path, encoding="utf8", errors="replace").read()
        if all(s in text for s in SENTINELS):
            return path, text
    raise SystemExit(
        "Could not find the token stylesheet.\n"
        f"Looked in {assets} for a .css declaring {' and '.join(SENTINELS)}.\n"
        "The app's style structure has probably changed — re-derive the bindings."
    )

def app_version():
    """The claude-desktop package version (NOT resources/version, which is
    Electron's)."""
    try:
        out = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "claude-desktop"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"

def _rules(css):
    for m in re.finditer(r'([^{}]+)\{([^{}]*--[a-z_][^{}]*)\}', css):
        yield m.group(1).strip(), m.group(2)

def _mode_of(selector):
    if "[data-mode=dark]" in selector:   return "dark"
    if "[data-mode=light]" in selector:  return "light"
    if "[data-mode=system]" in selector or "not([data-mode])" in selector:
        return "system"
    if "prefers-color-scheme" in selector: return "dark"
    return "light"

def collect(css):
    """{mode: {token: raw declared value}} — last declaration per mode wins."""
    out = {"light": {}, "dark": {}, "system": {}}
    for selector, body in _rules(css):
        mode = _mode_of(selector)
        for d in re.finditer(r'(--[a-z_][a-z0-9_-]*)\s*:\s*([^;]+)', body):
            out[mode][d.group(1)] = d.group(2).strip()
    return out

def resolve(name, table, fallback, depth=0):
    """Follow var() chains until something literal falls out."""
    if depth > 12:
        return None
    value = table.get(name, fallback.get(name))
    if value is None:
        return None
    chain = re.fullmatch(r'var\((--[a-z_][a-z0-9_-]*)\)', value.strip())
    if chain:
        return resolve(chain.group(1), table, fallback, depth + 1)
    return value

TRIPLET = re.compile(r'[\d.]+ [\d.]+% [\d.]+%$')

def ramp(css_tokens, prefix, kind="hex"):
    """{step: value} for a numbered primitive ramp.

    The app keeps two parallel grey ramps: --cds-gray-* in hex, and
    --cds-hsl-gray-* as bare 'H S% L%' triplets. The triplet one feeds
    --_gray-* -> --z0..z6 (surfaces) and --t0..t7 (alpha tints), which is what
    paints code blocks, dividers and the window chrome.
    """
    keep = (lambda v: v.startswith('#')) if kind == "hex" else \
           (lambda v: bool(TRIPLET.fullmatch(v.strip())))
    out = {}
    for name, value in css_tokens.items():
        m = re.fullmatch(re.escape(prefix) + r'(\d+)', name)
        if m and keep(value):
            out[int(m.group(1))] = value.strip()
    return dict(sorted(out.items()))
