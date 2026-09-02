"""Colour-space conversions. Pure functions, no I/O.

Claude Desktop needs two output formats:
  * CDS tokens  -> hex        (#rrggbb)
  * legacy tokens -> "H S% L%" triplets, because the app wraps them in hsl()
"""
import math, re

# ---------- parsing -------------------------------------------------------

def parse_oklch(s):
    m = re.fullmatch(r'oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)\s*\)', s.strip())
    if not m:
        raise ValueError(f"not an oklch() colour: {s!r}")
    l = float(m.group(1).rstrip('%'))
    if m.group(1).endswith('%'):
        l /= 100
    return l, float(m.group(2)), float(m.group(3))

def parse_hex(s):
    s = s.strip().lstrip('#')
    if len(s) == 3:
        s = ''.join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"not a hex colour: {s!r}")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))

# ---------- oklch <-> srgb ------------------------------------------------

def _gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

def _ungamma(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def oklch_to_rgb(L, C, H):
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(min(1.0, max(0.0, _gamma(v))) for v in (r, g, bl))

def rgb_to_oklch(r, g, b):
    r, g, b = _ungamma(r), _ungamma(g), _ungamma(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    C = math.hypot(A, B)
    H = math.degrees(math.atan2(B, A)) % 360
    return L, C, H

# ---------- srgb <-> hsl --------------------------------------------------

def rgb_to_hsl(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, s, l

def hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    hp = (h % 360) / 60
    x = c * (1 - abs(hp % 2 - 1))
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x),
               (0, x, c), (x, 0, c), (c, 0, x)][int(hp) % 6]
    m = l - c / 2
    return r + m, g + m, b + m

# ---------- output --------------------------------------------------------

def to_hex(rgb):
    return '#%02x%02x%02x' % tuple(round(v * 255) for v in rgb)

def to_hsl_triplet(rgb):
    """The bare 'H S% L%' form Claude's legacy tokens expect."""
    h, s, l = rgb_to_hsl(*rgb)
    return f"{h:.1f} {s * 100:.1f}% {l * 100:.1f}%"

def oklch_hex(s):
    return to_hex(oklch_to_rgb(*parse_oklch(s)))

def oklch_triplet(s):
    return to_hsl_triplet(oklch_to_rgb(*parse_oklch(s)))

def retint(value, hue, chroma_scale=1.0):
    """Keep a colour's lightness, adopt another hue. Used for tokens the source
    theme has no direct equivalent for, so nothing stays warm next to cool."""
    rgb = parse_hex(value) if value.lstrip().startswith('#') else None
    if rgb is None:
        raise ValueError(f"cannot retint {value!r}")
    L, C, _ = rgb_to_oklch(*rgb)
    return to_hex(oklch_to_rgb(L, C * chroma_scale, hue))
