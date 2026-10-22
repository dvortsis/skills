#!/usr/bin/env python3
"""Project brand resolver shared by the documentation skills (v1.0.0). Byte-identical copies ship in document-builder,
slide-deck and material-composer; their self-tests check that the copies match.

  python3 scripts/brand.py detect [--project DIR] [--out brand.json]   find the project's logo, colors and fonts
  python3 scripts/brand.py show [--source deck.json|doc.json]          print the brand a build of that source will use
  python3 scripts/brand.py check brand.json                            validate a hand-written profile

Every build and lint calls load(), so a deck, a document and a form made in the same project share one brand. Order:
  1. an explicit profile: --brand, the source's meta.brand, or $BRAND_PROFILE
  2. brand.json, .brand.json, .brand/brand.json or brand/brand.json beside the source or at the project root
  3. detected from the project: design tokens, Tailwind/MUI/Chakra theme objects, CSS/SCSS/LESS custom properties,
     Office themes (.potx/.dotx/.thmx), Android colors.xml, web manifest theme_color, then the logo's own colors
  4. neutral defaults (no logo, no footer)
The project root is the nearest folder above the source (or the working directory) that holds .git, package.json,
pyproject.toml or another project marker; $BRAND_PROJECT overrides it. Colors missing from the project are derived
from the primary color, and any color that misses a required text contrast pair is darkened or lightened (hue kept)
until it passes WCAG AA; every change is reported as an adjustment, never made silently.
"""
import argparse, colorsys, datetime, io, json, os, re, sys, zipfile

VERSION = "1.0.0"
PROFILE_NAMES = ("brand.json", ".brand.json", os.path.join(".brand", "brand.json"), os.path.join("brand", "brand.json"))
MARKERS = (".git", "package.json", "pyproject.toml", "setup.py", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
           "composer.json", "Gemfile", "brand.json", ".brand", "deno.json")
SKIP_DIRS = {"node_modules", ".git", "vendor", "third_party", "third-party", "dist", "build", "out", ".next", ".nuxt",
             ".svelte-kit", "coverage", ".venv", "venv", "env", "site-packages", "__pycache__", ".cache", "target",
             "bin", "obj", "Pods", ".gradle", "storybook-static", ".turbo", ".idea", ".vscode", "tmp", "temp",
             "fixtures", "__fixtures__", "test", "tests", "__tests__", "spec", "examples", "e2e", ".pytest_cache"}
MAX_FILES, MAX_BYTES, MAX_DEPTH = 6000, 1_500_000, 7
TEXT_EXT = {".css", ".scss", ".sass", ".less", ".pcss", ".styl", ".js", ".cjs", ".mjs", ".ts", ".cts", ".mts", ".jsx",
            ".tsx", ".json", ".html", ".htm", ".vue", ".svelte", ".astro", ".xml", ".webmanifest", ".toml", ".md"}
IMG_EXT = (".svg", ".png", ".webp", ".jpg", ".jpeg", ".ico")
OFFICE_EXT = (".potx", ".dotx", ".thmx", ".pptx", ".docx")

# Roles every skill uses. Text pairs below must pass in every resolved brand.
ROLES = ("primary", "dark", "secondary", "alert", "alert_text", "text", "muted", "muted_text", "context", "card",
         "callout", "card_line", "track", "white", "black")
LEGACY = {"blue": "primary", "navy": "dark", "light_blue": "secondary", "orange": "alert", "orange_text": "alert_text",
          "mid_gray": "muted", "mid_gray_text": "muted_text"}
DEFAULT_COLORS = {"primary": "1F5FAD", "dark": "1D2A3F", "secondary": "3D8FD9", "alert": "D9480F", "text": "3D3D3D",
                  "muted": "767676", "muted_text": "6B6B6B", "card_line": "DFDFDF", "track": "DFDFDF",
                  "white": "FFFFFF", "black": "000000"}
# Used only when the project names no font anywhere. Both are SIL OFL fonts shipped in assets/fonts (base64 text) by
# the skills that render, so text is measured and PDFs embed the same font on every machine.
FALLBACK_FONTS = {"body": "Inter", "heading": "Inter", "display": "Inter", "mono": "JetBrains Mono"}
FRAMEWORK_FONTS = {"@mui/material": "Roboto", "@material-ui/core": "Roboto", "vuetify": "Roboto", "@angular/material": "Roboto"}
FONT_EXT = (".ttf", ".otf")
PAIRS = [  # (foreground, background, minimum ratio); 3.0 pairs are used only for bold text 14 pt and larger
    ("dark", "white", 4.5), ("text", "white", 4.5), ("primary", "white", 4.5), ("muted_text", "white", 4.5),
    ("muted", "white", 4.5), ("alert", "white", 3.0),  # muted draws source lines and axis labels; alert draws big numbers
    ("alert_text", "white", 4.5), ("dark", "card", 4.5), ("text", "card", 4.5), ("dark", "context", 4.5),
    ("dark", "callout", 4.5), ("alert_text", "card", 4.5), ("primary", "card", 3.0), ("card", "primary", 3.0),
    ("text", "F4F4F4", 4.5),
]
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace",
                 "-apple-system", "blinkmacsystemfont", "segoe ui emoji", "apple color emoji", "noto color emoji",
                 "segoe ui symbol", "inherit", "initial", "cursive", "fantasy", "emoji", "math", "fangsong"}


# ---------------------------------------------------------------- color math
def hex6(v):
    """'#1a73e8', '1A73E8', '#abc', '#1a73e8ff' -> '1A73E8'; None when it is not a hex color."""
    s = str(v or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3,4}", s):
        s = "".join(c * 2 for c in s[:3])
    if re.fullmatch(r"[0-9a-fA-F]{8}", s):
        s = s[:6]
    return s.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", s) else None


def rgb_of(h):
    h = hex6(h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def to_hex(rgb):
    return "".join("%02X" % max(0, min(255, round(c * 255))) for c in rgb)


def luminance(h):
    def ch(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb_of(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    """t of color a over (1 - t) of color b: mix(primary, 'FFFFFF', 0.25) is the primary at a 25% tint."""
    return to_hex(tuple(x * t + y * (1 - t) for x, y in zip(rgb_of(a), rgb_of(b))))


def saturation(h):
    return colorsys.rgb_to_hls(*rgb_of(h))[2]


def hue(h):
    return colorsys.rgb_to_hls(*rgb_of(h))[0] * 360


def shift_lightness(h, step):
    """Lighten (step > 0) or darken (step < 0) in HLS, keeping hue and saturation."""
    hh, l, s = colorsys.rgb_to_hls(*rgb_of(h))
    return to_hex(colorsys.hls_to_rgb(hh, max(0.0, min(1.0, l + step)), s))


def parse_color(raw, var_lookup=None, depth=0):
    """Hex, rgb()/rgba(), hsl()/hsla(), bare 'H S% L%' (shadcn), oklch() and var() references -> 'RRGGBB' or None."""
    if raw is None or depth > 6:
        return None
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    if isinstance(raw, dict):
        raw = raw.get("$value", raw.get("value"))
    s = str(raw or "").strip().strip("'\"").strip()
    s = re.sub(r"\s*!important$", "", s)
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", s)
    if m:
        if var_lookup and m.group(1) in var_lookup:
            return parse_color(var_lookup[m.group(1)], var_lookup, depth + 1)
        return parse_color(m.group(2), var_lookup, depth + 1) if m.group(2) else None
    m = re.fullmatch(r"\{([\w.-]+)\}", s)  # design-token alias {color.blue.600}
    if m and var_lookup and m.group(1) in var_lookup:
        return parse_color(var_lookup[m.group(1)], var_lookup, depth + 1)
    if s.startswith("#"):
        return hex6(s)
    num = r"(-?[\d.]+)(%|deg|turn|rad)?"
    m = re.fullmatch(r"rgba?\(\s*%s[\s,]+%s[\s,]+%s(?:\s*[,/]\s*[\d.]+%%?)?\s*\)" % (num, num, num), s, re.I)
    if m:
        vals = []
        for i in (0, 2, 4):
            v = float(m.group(i + 1)); vals.append(v / 100 if m.group(i + 2) == "%" else v / 255)
        return to_hex(vals)
    m = re.fullmatch(r"(?:hsla?\(\s*)?%s[\s,]+([\d.]+)%%[\s,]+([\d.]+)%%(?:\s*[,/]\s*[\d.]+%%?)?\s*\)?" % num, s, re.I)
    if m:
        hdeg = float(m.group(1)) * {"turn": 360, "rad": 57.2958}.get(m.group(2), 1)
        return to_hex(colorsys.hls_to_rgb((hdeg % 360) / 360, float(m.group(4)) / 100, float(m.group(3)) / 100))
    m = re.fullmatch(r"oklch\(\s*([\d.]+)(%?)\s+([\d.]+)%?\s+([\d.]+)(?:deg)?(?:\s*/\s*[\d.]+%?)?\s*\)", s, re.I)
    if m:
        return oklch_hex(float(m.group(1)) / (100 if m.group(2) else 1), float(m.group(3)), float(m.group(4)))
    return None


def oklch_hex(L, C, H):
    import math
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lin = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    return to_hex(tuple(12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0) ** (1 / 2.4) - 0.055 for c in lin))


# ---------------------------------------------------------------- project walk
def project_root(start=None):
    env = os.environ.get("BRAND_PROJECT")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    cur = os.path.abspath(start or os.getcwd())
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    first, home = cur, os.path.abspath(os.path.expanduser("~"))
    while True:
        if any(os.path.exists(os.path.join(cur, m)) for m in MARKERS):
            return cur
        up = os.path.dirname(cur)
        if up == cur or cur == home:
            return first
        cur = up


def walk(root):
    """Project files in a stable order, skipping dependencies, build output and test fixtures."""
    n = 0
    for d, dirs, files in os.walk(root):
        depth = os.path.relpath(d, root).count(os.sep)
        if d != root and "SKILL.md" in files:  # an installed skill inside the project: its themes aren't the project's brand
            dirs[:] = []
            continue
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith(".") or x == ".brand")
        if depth >= MAX_DEPTH:
            dirs[:] = []
        for f in sorted(files):
            n += 1
            if n > MAX_FILES:
                return
            yield os.path.join(d, f)


def read_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def read_text(p):
    try:
        if os.path.getsize(p) > MAX_BYTES:
            return ""
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- parsers
def css_declarations(text):
    """(selector chain, property, value) for every declaration outside dark-mode blocks. Handles nesting and @media."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    out, stack, buf = [], [], ""

    def flush(chunk):
        for decl in chunk.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                k = k.strip()
                if re.fullmatch(r"(--|\$|@)?[\w-]+", k):
                    out.append((tuple(stack), k, v.strip()))
    for ch in text:
        if ch == "{":
            head, _, sel = buf.rpartition(";")
            flush(head)
            stack.append(sel.strip()); buf = ""
        elif ch == "}":
            flush(buf); buf = ""
            if stack:
                stack.pop()
        else:
            buf += ch
    flush(buf)
    dark = re.compile(r"(?i)dark|prefers-color-scheme\s*:\s*dark|high-contrast|forced-colors")
    return [(s, k, v) for s, k, v in out if not any(dark.search(x) for x in s)]


def js_objects(text):
    """Flatten every object literal in a JS/TS theme or config file into {'a.b.c': 'value'} (strings and numbers only)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)(^|[^:\"'])//.*$", r"\1", text)
    tok = re.compile(r"""\s*(?:(?P<s>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`[^`$]*`)|(?P<id>[A-Za-z_$][\w$-]*)|(?P<n>-?\d+(?:\.\d+)?)|(?P<p>[{}\[\]:,()]))""")
    toks, pos = [], 0
    while pos < len(text):
        m = tok.match(text, pos)
        if not m:
            pos += 1; continue
        pos = m.end()
        if m.group("s"):
            toks.append(("s", m.group("s")[1:-1]))
        elif m.group("id"):
            toks.append(("id", m.group("id")))
        elif m.group("n"):
            toks.append(("n", m.group("n")))
        else:
            toks.append(("p", m.group("p")))
    flat = {}

    def parse_obj(i, prefix):
        # toks[i] is '{'; returns index after the matching '}'
        i += 1
        while i < len(toks) and toks[i] != ("p", "}"):
            t = toks[i]
            if t[0] in ("s", "id", "n") and i + 1 < len(toks) and toks[i + 1] == ("p", ":"):
                key = prefix + ("." if prefix else "") + t[1]
                i = parse_val(i + 2, key)
            else:
                i += 1
            if i < len(toks) and toks[i] == ("p", ","):
                i += 1
        return i + 1

    def parse_val(i, key):
        if i >= len(toks):
            return i
        t = toks[i]
        if t == ("p", "{"):
            return parse_obj(i, key)
        if t == ("p", "["):
            i += 1; k = 0
            while i < len(toks) and toks[i] != ("p", "]"):
                if toks[i][0] in ("s", "n"):
                    flat.setdefault("%s[%d]" % (key, k), toks[i][1]); k += 1
                elif toks[i] == ("p", "{"):
                    i = parse_obj(i, "%s[%d]" % (key, k)) - 1; k += 1
                i += 1
            return i + 1
        if t[0] in ("s", "n"):
            flat.setdefault(key, t[1])
            return i + 1
        depth = 0  # identifiers, calls and expressions: skip to the next top-level ',' or '}'
        while i < len(toks):
            if toks[i] in (("p", "("), ("p", "["), ("p", "{")):
                depth += 1
            elif toks[i] in (("p", ")"), ("p", "]"), ("p", "}")):
                if depth == 0:
                    return i
                depth -= 1
            elif toks[i] == ("p", ",") and depth == 0:
                return i
            i += 1
        return i
    i = 0
    while i < len(toks):
        if toks[i] == ("p", "{"):
            i = parse_obj(i, "")
        else:
            i += 1
    return flat


def json_flat(data, prefix="", out=None):
    out = {} if out is None else out
    if isinstance(data, dict):
        if ("$value" in data or "value" in data) and not isinstance(data.get("$value", data.get("value")), (dict, list)):
            out[prefix] = data.get("$value", data.get("value"))
            return out
        for k, v in data.items():
            if not str(k).startswith("$"):
                json_flat(v, prefix + ("." if prefix else "") + str(k), out)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            json_flat(v, "%s[%d]" % (prefix, i), out)
    elif isinstance(data, (str, int, float)):
        out[prefix] = data
    return out


def office_theme(path):
    """accent1/dk2/accent2 colors and major/minor fonts from an Office template or document theme. Files these skills
    built (core properties say "Built by ...") or that python-docx/python-pptx made carry only library defaults: skipped."""
    try:
        z = zipfile.ZipFile(path)
        core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in z.namelist() else ""
        if re.search(r"Built by [\w-]+|python-docx|python-pptx", core):
            return {}
        name = next((n for n in sorted(z.namelist()) if re.search(r"theme/theme\d*\.xml$", n)), None)
        x = z.read(name).decode("utf-8", "replace") if name else ""
    except (OSError, zipfile.BadZipFile, KeyError):
        return {}
    out = {}
    for slot in ("accent1", "accent2", "accent3", "dk2"):
        m = re.search(r"<a:%s>\s*<a:(?:srgbClr val|sysClr [^>]*lastClr)=\"([0-9A-Fa-f]{6})\"" % slot, x)
        if m:
            out[slot] = m.group(1).upper()
    for slot in ("majorFont", "minorFont"):
        m = re.search(r"<a:%s>\s*<a:latin typeface=\"([^\"]+)\"" % slot, x)
        if m:
            out[slot] = m.group(1)
    return out


# ---------------------------------------------------------------- role matching
SHADE_PREF = {"": 0, "default": 0, "main": 0, "base": 0, "600": 1, "500": 2, "700": 3, "400": 5, "800": 5}


def segments(path):
    return [s for s in re.split(r"[.\-_/\s\[\]]+|(?<=[a-z])(?=[A-Z])", str(path).lstrip("-$@")) if s]


STRUCTURAL = {"theme", "extend", "color", "colors", "colour", "colours", "palette", "tokens", "token", "semantic",
              "global", "sys", "ref", "md", "bs", "tw", "value", "values", "schemes", "scheme", "default", "main", "base",
              "light", "vars", "variables", "root", "app", "ui", "system"}
ROLE_NAMES = {  # token name (structural words removed) -> score; lower wins
    "primary": {("primary",): 0, ("brand",): 0, ("brand", "primary"): 0, ("primary", "brand"): 0, ("accent",): 30,
                ("accent1",): 30, ("key",): 30},
    "dark": {("primary", "dark"): 0, ("brand", "dark"): 0, ("primary", "darker"): 1, ("dark",): 10, ("navy",): 10,
             ("heading",): 12, ("headings",): 12},
    "secondary": {("secondary",): 0, ("brand", "secondary"): 0, ("secondary", "brand"): 0, ("accent",): 20,
                  ("accent2",): 20, ("tertiary",): 25},
    "alert": {("warning",): 0, ("warn",): 0, ("caution",): 0, ("danger",): 10, ("error",): 10, ("destructive",): 10,
              ("critical",): 12},
    "text": {("text",): 0, ("foreground",): 0, ("text", "primary"): 0, ("text", "default"): 0, ("body",): 2,
             ("on", "background"): 1, ("on", "surface"): 1, ("body", "color"): 1, ("text", "body"): 1},
}
ROLE_WORDS = {w for t in ROLE_NAMES.values() for k in t for w in k}


def role_score(role, path):
    """Lower is better; None when the token name doesn't name that role. Shades pick the brand's main step:
    'colors.primary.DEFAULT', '--color-primary-600' and 'palette.primary.main' name the primary; '--primary-foreground',
    'primary-light', 'dark.primary' (a dark-mode value) and 'primary-100' don't."""
    segs = [s.lower() for s in segments(path)]
    shade = next((s for s in reversed(segs) if s.isdigit() or s in ("default", "main", "base")), "")
    first_role = next((i for i, s in enumerate(segs) if s in ROLE_WORDS and s != "dark"), len(segs))
    if "dark" in segs[:first_role] or "night" in segs[:first_role]:
        return None  # dark-mode container
    words = tuple(s for i, s in enumerate(segs) if not s.isdigit() and s not in STRUCTURAL - ({"light"} if i > first_role else set()))
    pref = SHADE_PREF.get(shade, 6)
    if role == "dark" and words in (("primary",), ("brand",)) and shade in ("800", "900", "950"):
        return {"900": 0, "800": 1, "950": 2}[shade]
    score = ROLE_NAMES[role].get(words)
    if score is None:
        return None
    if role in ("primary", "secondary", "alert") and shade in ("50", "100", "200", "300", "800", "900", "950"):
        return None  # tints and deep shades are not the main color
    return score + pref


def plausible(role, h):
    """Reject values that can't serve the role: a near-white 'accent', a pale 'foreground', a gray 'warning'."""
    if not h:
        return False
    if role == "primary":
        return (saturation(h) >= 0.15 and 0.02 < luminance(h) < 0.85) or contrast(h, "FFFFFF") >= 4.5
    if role == "secondary":
        return luminance(h) < 0.8 and (saturation(h) >= 0.12 or contrast(h, "FFFFFF") >= 3)
    if role in ("dark", "text"):
        return contrast(h, "FFFFFF") >= 7
    if role == "alert":
        return saturation(h) >= 0.35 and luminance(h) < 0.8
    return True


def font_role(path):
    segs = [s.lower() for s in segments(path)]
    if not any(s.startswith("font") or s in ("typeface", "typography", "family") for s in segs):
        return None
    if any(s in ("size", "sizes", "weight", "weights", "height", "spacing", "letter", "line", "feature", "settings",
                 "smoothing", "variant", "stretch", "style", "styles", "optical") for s in segs):
        return None
    if any(s in ("mono", "code", "monospace") for s in segs):
        return "mono"
    if any(s in ("heading", "headings", "display", "title", "headline", "brand") for s in segs):
        return "display"
    if any(s in ("sans", "body", "base", "text", "default", "primary", "family", "fontfamily") for s in segs):
        return "body"
    return None


def first_family(value):
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    for part in re.split(r",", str(value or "")):
        f = part.strip().strip("'\"").strip()
        if not f or f.lower() in GENERIC_FONTS or f.startswith(("var(", "$", "@", "{", "theme(")) or "(" in f:
            continue
        if re.fullmatch(r"[A-Za-z][\w .\-]{1,40}", f) and not re.fullmatch(r"__\w+", f):
            return f
    return None


# ---------------------------------------------------------------- detection
class Found:
    """Best candidate per role: (priority, score, depth, value, where)."""
    def __init__(self):
        self.best = {}

    def add(self, role, value, priority, score, where, depth=0):
        if value is None or (not role.startswith("font_") and not plausible(role, value)):
            return
        cand = (-priority, score, depth, str(where), value)
        cur = self.best.get(role)
        if cur is None or cand < cur:
            self.best[role] = cand

    def get(self, role):
        c = self.best.get(role)
        return (c[4], c[3]) if c else (None, None)


def rel(root, p):
    try:
        return os.path.relpath(p, root).replace(os.sep, "/")
    except ValueError:
        return p


def detect(root):
    """Scan a project; return a profile dict with colors, fonts, logo files, name, org and sources."""
    found, logos, names, font_files = Found(), [], {}, []
    for p in walk(root):
        base = os.path.basename(p).lower()
        ext = os.path.splitext(base)[1]
        r = rel(root, p)
        if ext in FONT_EXT:  # fonts the project ships are its standard fonts and the files to measure and embed
            font_files.append(p)
            continue
        depth = r.count("/")
        if base in ("brand.json", ".brand.json") and depth <= 1:
            continue  # explicit profiles are handled by load()
        if ext in IMG_EXT:
            logos.append(p)
            continue
        if ext in OFFICE_EXT:
            if ext in (".pptx", ".docx") and not re.search(r"(?i)templ|brand|theme|master", base):
                continue
            th = office_theme(p)
            for slot, role in (("accent1", "primary"), ("dk2", "dark"), ("accent2", "secondary")):
                if th.get(slot):
                    found.add(role, th[slot], 60, 0, "%s (theme %s)" % (r, slot), depth)
            if th.get("minorFont"):
                found.add("font_body", th["minorFont"], 60, 0, "%s (minor font)" % r, depth)
            if th.get("majorFont"):
                found.add("font_display", th["majorFont"], 60, 0, "%s (major font)" % r, depth)
            continue
        if ext not in TEXT_EXT and base not in ("license", "license.txt", "copying", "readme", "readme.md"):
            continue
        if base.endswith((".min.css", ".min.js", ".map", "lock.json")) or base in ("package-lock.json", "tsconfig.json"):
            continue
        text = read_text(p)
        if not text:
            continue
        if base in ("license", "license.txt", "license.md", "copying"):
            m = re.search(r"(?im)^\s*copyright\s*(?:\(c\)|©)?\s*(?:\d{4}(?:\s*[-–,]\s*\d{4})*\s*,?\s*)?(.+)$", text)
            holder = re.sub(r"(?i)[\s,.]*all rights reserved\.?", "", m.group(1)).strip(" ,") if m else ""
            if not re.search(r"(?i)\b(inc|ltd|co|corp|llc|plc|gmbh|s\.a|n\.v|pty|l\.p)\.$", holder):
                holder = holder.rstrip(".")
            if holder and not re.search(r"(?i)\b(holders?|contributors|the authors)\b|[<{]", holder):
                names.setdefault("org", (holder, r))
            continue
        if base == "package.json" and depth == 0:
            try:
                pj = json.loads(text)
            except ValueError:
                pj = {}
            for k in ("displayName", "productName"):
                if isinstance(pj.get(k), str):
                    names.setdefault("name", (pj[k], "package.json %s" % k))
            if isinstance(pj.get("name"), str):
                names.setdefault("pkg", (pj["name"], "package.json name"))
            a = pj.get("author")
            a = a.get("name") if isinstance(a, dict) else a
            if isinstance(a, str) and a.strip():
                names.setdefault("author", (re.sub(r"\s*[<(].*$", "", a).strip(), "package.json author"))
            deps = {}
            for k in ("dependencies", "devDependencies", "peerDependencies"):
                if isinstance(pj.get(k), dict):
                    deps.update(pj[k])
            for dep in sorted(deps):
                m = re.match(r"^@fontsource(?:-variable)?/([a-z0-9-]+)$", dep)
                if m:  # a font package the project installs: its standard font
                    fam = " ".join(w.capitalize() for w in m.group(1).split("-"))
                    mono = re.search(r"mono|code|courier|consol|hack|iosevka", m.group(1))
                    found.add("font_mono" if mono else "font_body", fam, 55, 0, "package.json %s" % dep, depth)
                elif dep in FRAMEWORK_FONTS:  # the UI framework's default font
                    found.add("font_body", FRAMEWORK_FONTS[dep], 35, 0, "package.json %s (framework default)" % dep, depth)
            continue
        if base == "pyproject.toml" and depth == 0:
            m = re.search(r"(?ms)^\[(?:project|tool\.poetry)\].*?^name\s*=\s*[\"']([^\"']+)", text)
            if m:
                names.setdefault("pkg", (m.group(1), "pyproject.toml name"))
            continue
        if base.startswith("readme") and depth == 0:
            m = re.search(r"(?m)^#\s+(.+?)\s*#*\s*$", text)
            if m and len(m.group(1)) <= 60:
                names.setdefault("readme", (re.sub(r"[\[\]!`*_]|\(.*?\)|<[^>]+>", "", m.group(1)).strip(), "README title"))
            continue
        if ext in (".css", ".scss", ".sass", ".less", ".pcss", ".styl", ".vue", ".svelte", ".astro", ".html", ".htm"):
            decls = css_declarations(text if ext not in (".vue", ".svelte", ".astro", ".html", ".htm")
                                     else "\n".join(re.findall(r"(?is)<style[^>]*>(.*?)</style>", text)))
            variables = {k: v for _, k, v in decls if k.startswith(("--", "$", "@"))}
            for sel, k, v in decls:
                rootish = not sel or any(re.search(r":root|^html$|^body$|@theme|^\*$|^:host", x) for x in sel)
                if k.startswith(("--", "$", "@")):
                    for role in ("primary", "dark", "secondary", "alert", "text"):
                        sc = role_score(role, k)
                        if sc is not None:
                            found.add(role, parse_color(v, variables), 70 if rootish else 65, sc, "%s %s" % (r, k), depth)
                    fr = font_role(k)
                    if fr:
                        found.add("font_" + fr, first_family(v), 70, 0, "%s %s" % (r, k), depth)
                elif k == "font-family":
                    fam = first_family(re.sub(r"var\((--[\w-]+)[^)]*\)", lambda m: variables.get(m.group(1), ""), v))
                    if any(re.search(r"(?i)^(html|body|:root)$", x.strip()) for x in sel):
                        found.add("font_body", fam, 66, 0, "%s %s font-family" % (r, ",".join(sel)), depth)
                    elif any(re.search(r"(?i)\bh1\b|heading|display|title", x) for x in sel):
                        found.add("font_display", fam, 66, 0, "%s %s font-family" % (r, ",".join(sel)), depth)
            if ext in (".html", ".htm"):
                m = re.search(r"(?i)<meta[^>]+name=[\"']theme-color[\"'][^>]+content=[\"']([^\"']+)", text)
                if m:
                    found.add("primary", parse_color(m.group(1)), 50, 0, "%s meta theme-color" % r, depth)
                for fam in re.findall(r"fonts\.googleapis\.com/css2?\?family=([\w+]+)", text):
                    found.add("font_body", fam.replace("+", " "), 40, 0, "%s Google Fonts link" % r, depth)
            continue
        if ext in (".js", ".cjs", ".mjs", ".ts", ".cts", ".mts", ".jsx", ".tsx"):
            themeish = re.search(r"(?i)tailwind\.config|theme|palette|tokens|colors|brand|styles", base)
            if themeish or re.search(r"createTheme|extendTheme|defineConfig\(|theme\s*:\s*\{", text[:200000]):
                prio = 80 if base.startswith("tailwind.config") else 72
                flat = js_objects(text)
                for k, v in flat.items():
                    if not re.search(r"(?i)colou?rs?|palette|primary|secondary|brand|warning|text|font", k):
                        continue
                    for role in ("primary", "dark", "secondary", "alert", "text"):
                        sc = role_score(role, k)
                        if sc is not None:
                            found.add(role, parse_color(v), prio, sc, "%s %s" % (r, k), depth)
                    fr = font_role(k)
                    if fr:
                        found.add("font_" + fr, first_family(v), prio, 0 if k.endswith("[0]") else 1, "%s %s" % (r, k), depth)
            for fam in re.findall(r"import\s*\{([^}]+)\}\s*from\s*['\"]next/font/google['\"]", text):
                for f in fam.split(","):
                    f = f.split(" as ")[0].strip()
                    if f:
                        found.add("font_body", f.replace("_", " "), 45, 0, "%s next/font" % r, depth)
            continue
        if ext == ".json" or ext == ".webmanifest":
            if base in ("manifest.json", "site.webmanifest", "manifest.webmanifest") or ext == ".webmanifest":
                try:
                    mj = json.loads(text)
                except ValueError:
                    mj = {}
                if isinstance(mj, dict):
                    found.add("primary", parse_color(mj.get("theme_color")), 50, 0, "%s theme_color" % r, depth)
                    if isinstance(mj.get("name"), str):
                        names.setdefault("manifest", (mj["name"], "%s name" % r))
                continue
            if not re.search(r"(?i)token|theme|brand|palette|colou?r|style", base):
                continue
            try:
                flat = json_flat(json.loads(text))
            except ValueError:
                continue
            lookup = {k: v for k, v in flat.items()}
            for k, v in flat.items():
                for role in ("primary", "dark", "secondary", "alert", "text"):
                    sc = role_score(role, k)
                    if sc is not None:
                        found.add(role, parse_color(v, lookup), 90, sc, "%s %s" % (r, k), depth)
                fr = font_role(k)
                if fr:
                    found.add("font_" + fr, first_family(v), 90, 0, "%s %s" % (r, k), depth)
            continue
        if ext == ".xml" and base == "colors.xml":
            for nm, v in re.findall(r"<color\s+name=\"([^\"]+)\"\s*>\s*([^<]+)<", text):
                role = {"colorprimary": "primary", "primary": "primary", "brand": "primary", "colorprimarydark": "dark",
                        "primary_dark": "dark", "primarydark": "dark", "coloraccent": "secondary", "secondary": "secondary"}.get(nm.lower())
                if role:
                    found.add(role, parse_color(v), 60, 0, "%s %s" % (r, nm), depth)
    prof = {"colors": {}, "fonts": {}, "sources": {}}
    for role in ("primary", "dark", "secondary", "alert", "text"):
        v, where = found.get(role)
        if v:
            prof["colors"][role], prof["sources"][role] = v, where
    for fr in ("body", "display", "mono"):
        v, where = found.get("font_" + fr)
        if v:
            prof["fonts"][fr], prof["sources"]["font_" + fr] = v, where
    if font_files:
        prof["font_files"] = [rel(root, p) for p in font_files[:40]]
        fams = {}
        for p in font_files:
            fam = font_name(p)[0]
            if fam:
                fams.setdefault(fam, rel(root, p))
        for fr, want_mono in (("body", False), ("mono", True)):  # shipped files name the font when nothing else does
            if fr not in prof["fonts"]:
                pick = next((f for f in sorted(fams) if bool(re.search(r"(?i)mono|code|courier|consol", f)) == want_mono), None)
                if pick:
                    prof["fonts"][fr], prof["sources"]["font_" + fr] = pick, "font file %s" % fams[pick]
    logo, on_dark, why = pick_logos(root, logos)
    if logo:
        prof["logo"], prof["sources"]["logo"] = rel(root, logo), why
    if on_dark:
        prof["logo_on_dark"] = rel(root, on_dark)
    name = names.get("name") or names.get("manifest") or names.get("readme") or names.get("pkg")
    if name:
        n = name[0]
        if name is names.get("pkg"):
            n = re.sub(r"^@[^/]+/", "", n)
            n = " ".join(w[:1].upper() + w[1:] for w in re.split(r"[-_]+", n) if w)
        prof["name"], prof["sources"]["name"] = n, name[1]
    org = names.get("org") or names.get("author")
    if org:
        prof["org"], prof["sources"]["org"] = org[0], org[1]
    return prof


def pick_logos(root, files):
    """The main logo and a light-on-dark variant. Names score: brand/logo folders and 'logo' names first, then icons."""
    scored = []
    for p in files:
        b = os.path.basename(p).lower()
        stem, ext = os.path.splitext(b)
        r = rel(root, p).lower()
        if not re.search(r"(^|[-_.@ ])(logo|logotype|wordmark|lockup|brand)([-_.@ ]|$)", stem) and not re.search(r"(^|/)(logos?|brand)/", r):
            continue
        if re.search(r"(?i)(^|[-_.])(partner|client|sponsor|vendor|google|github|apple|microsoft|facebook|twitter|linkedin|slack|stripe|aws|vercel|nextjs|next|react|vue|vite|svelte|angular|tailwind|npm|docker)([-_.]|$)", stem):
            continue
        s = 0
        s -= 30 if re.fullmatch(r"(logo|logotype|wordmark|brand[-_]?logo|[\w]+[-_]logo|logo[-_][\w]+)", stem) else 0
        s -= 15 if re.search(r"(^|/)(brand|logos?)/", r) else 0
        s -= 10 if ext == ".svg" else 5 if ext == ".png" else 0
        s += 25 if re.search(r"(icon|mark|symbol|favicon|glyph|avatar|small|sm|mini|\d+x\d+)", stem) else 0
        s += 40 if ext == ".ico" else 0
        s += r.count("/") * 2
        scored.append((s, r, p))
    for p in files:  # last resort: app icons
        b = os.path.basename(p).lower()
        if re.fullmatch(r"(apple-touch-icon|icon-512x512|icon-512|android-chrome-512x512|icon|favicon)\.(png|svg)", b):
            scored.append((80, rel(root, p).lower(), p))
    scored.sort()
    if not scored:
        return None, None, None
    light = [x for x in scored if not ink_is_light(x[2])]
    darkv = [x for x in scored if ink_is_light(x[2])]
    main = (light or scored)[0]
    on_dark = darkv[0][2] if darkv and darkv[0][0] < 60 else None
    why = "logo file" if main[0] < 60 else "app icon (no logo file found; low resolution possible)"
    return main[2], on_dark, why


_INK = {}


def _pixels(im):
    """RGBA tuples of an RGBA image (Image.getdata is deprecated in recent Pillow)."""
    raw = im.tobytes()
    return (tuple(raw[i:i + 4]) for i in range(0, len(raw), 4))


def ink_is_light(path):
    """True when the logo's visible pixels are light (a version made for dark backgrounds)."""
    if path in _INK:
        return _INK[path]
    _INK[path] = False
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    named = re.search(r"(white|inverse|inverted|reverse[d]?|negative|knockout|on[-_]?dark|for[-_]?dark|light)", stem)
    png = raster(path, 200)
    if png is None:
        _INK[path] = bool(named)
        return _INK[path]
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        px = [p for p in _pixels(im) if p[3] > 128]
        if px and len(px) < im.width * im.height * 0.97:  # transparent background: judge the ink
            lum = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b, _ in px) / len(px) / 255
            _INK[path] = lum > 0.75
        else:
            _INK[path] = bool(named) and "light" not in stem
    except Exception:
        _INK[path] = bool(named)
    return _INK[path]


def raster(path, width=1200):
    """PNG bytes for an SVG, PNG, WebP, JPEG or ICO file, at most `width` px wide; None when it can't be read."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if path.lower().endswith(".svg"):
        try:
            import fitz  # PyMuPDF opens SVG
        except ImportError:
            try:
                import pymupdf as fitz
            except ImportError:
                return None
        try:
            doc = fitz.open(stream=data, filetype="svg")
            page = doc[0]
            z = max(0.1, min(8.0, width / max(page.rect.width, 1)))
            return doc[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=True).tobytes("png")
        except Exception:
            return None
    try:
        from PIL import Image
    except ImportError:
        return data if data[:8] == b"\x89PNG\r\n\x1a\n" else None
    try:
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGBA")
        if im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))))
        out = io.BytesIO(); im.save(out, "PNG")
        return out.getvalue()
    except Exception:
        return None


def knockout(png):
    """A white version of a logo on a transparent background (for dark slides); None if the logo has no transparency."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:
        return None
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] > 200:
        return None
    white = Image.new("RGBA", im.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    out = io.BytesIO(); white.save(out, "PNG")
    return out.getvalue()


def logo_color(png):
    """The logo's most common strong color, for projects with a logo and no color tokens."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        im.thumbnail((120, 120))
        counts = {}
        for r, g, b, a in _pixels(im):
            if a < 200:
                continue
            h = "%02X%02X%02X" % (r // 16 * 16, g // 16 * 16, b // 16 * 16)
            counts[h] = counts.get(h, 0) + 1
        best = [h for h, _ in sorted(counts.items(), key=lambda kv: -kv[1]) if saturation(h) > 0.3 and 0.02 < luminance(h) < 0.7]
        return best[0] if best else None
    except Exception:
        return None


# ---------------------------------------------------------------- fonts
BUNDLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")


def font_name(path):
    """(family, style) from a .ttf/.otf name table, e.g. ('Inter', 'Bold Italic'); (None, None) when unreadable."""
    try:
        from PIL import ImageFont
        fam, style = ImageFont.truetype(path, 10).getname()
        return fam, style or "Regular"
    except Exception:
        stem = os.path.splitext(os.path.basename(path))[0]
        m = re.match(r"^(.+?)[-_ ]?(Regular|Bold|Italic|BoldItalic|Medium|SemiBold|Light)?$", stem)
        if not m:
            return None, None
        fam = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m.group(1)).strip()
        return fam, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m.group(2) or "Regular")


def bundled_dir():
    """The fallback fonts decoded from assets/fonts/*.b64 into a cache folder (checked against fonts.json); None
    when this skill ships none. Decoded once per machine; a damaged file is skipped, never half-written."""
    manifest = os.path.join(BUNDLED, "fonts.json")
    if not os.path.isfile(manifest):
        return None
    try:
        info = read_json(manifest)
    except ValueError:
        return None
    import base64, hashlib, tempfile
    key = hashlib.sha256(json.dumps(info, sort_keys=True).encode()).hexdigest()[:12]
    out = os.path.join(tempfile.gettempdir(), "brand-fonts-" + key)
    os.makedirs(out, exist_ok=True)
    for name, meta in info.get("files", {}).items():
        dst = os.path.join(out, name)
        if os.path.isfile(dst) and os.path.getsize(dst) == meta.get("bytes"):
            continue
        src = os.path.join(BUNDLED, name + ".b64")
        try:
            with open(src, encoding="ascii") as fh:
                raw = base64.b64decode("".join(fh.read().split()), validate=True)
        except (OSError, ValueError):
            continue
        if hashlib.sha256(raw).hexdigest() != meta.get("sha256"):
            continue
        tmp = dst + ".part"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, dst)
    return out


def system_font_dirs():
    home = os.path.expanduser("~")
    if os.name == "nt":
        return [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
                os.path.join(os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local")), "Microsoft", "Windows", "Fonts")]
    if sys.platform == "darwin":
        return ["/System/Library/Fonts", "/Library/Fonts", os.path.join(home, "Library", "Fonts")]
    return ["/usr/share/fonts", "/usr/local/share/fonts", os.path.join(home, ".fonts"), os.path.join(home, ".local", "share", "fonts")]


_INDEX = {}


def font_index(dirs):
    """{(family lower, style lower): path} for the .ttf/.otf files under dirs. Installed-font folders are cached on
    disk by folder and modification time, so a build doesn't reread hundreds of fonts."""
    import tempfile
    out = {}
    cache_path = os.path.join(tempfile.gettempdir(), "brand-font-index.json")
    try:
        cache = read_json(cache_path)
    except (OSError, ValueError):
        cache = {}
    dirty = False
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        if d in _INDEX:
            out.update(_INDEX[d]); continue
        try:
            stamp = os.path.getmtime(d)
        except OSError:
            continue
        hit = cache.get(d)
        if hit and hit.get("mtime") == stamp:
            entries = {tuple(k.split("|", 1)): v for k, v in hit["fonts"].items()}
        else:
            entries = {}
            n = 0
            for sub, _dirs, files in os.walk(d):
                for f in files:
                    if not f.lower().endswith(FONT_EXT):
                        continue
                    n += 1
                    if n > 4000:
                        break
                    p = os.path.join(sub, f)
                    fam, style = font_name(p)
                    if fam:
                        entries.setdefault((fam.lower(), style.lower()), p)
            cache[d] = {"mtime": stamp, "fonts": {"%s|%s" % k: v for k, v in entries.items()}}
            dirty = True
        _INDEX[d] = entries
        out.update({k: v for k, v in entries.items() if k not in out})
    if dirty:
        try:
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump(cache, fh)
        except OSError:
            pass
    return out


def find_font(family, bold=False, italic=False, extra_dirs=()):
    """Path of the font file for family in that style: the project's own files first, then the bundled fallback
    fonts, then installed fonts. None when no file exists (the output still names the family)."""
    if not family:
        return None
    want = ("bold italic" if bold and italic else "bold" if bold else "italic" if italic else "regular")
    near = {"bold": ["semibold", "semi bold", "extrabold"], "regular": ["book", "normal", "medium"], "italic": ["oblique"],
            "bold italic": ["semibold italic", "bold oblique"]}
    groups = [list(extra_dirs), [bundled_dir()], system_font_dirs()]
    for dirs in groups:
        idx = font_index([d for d in dirs if d])
        for style in [want] + near.get(want, []):
            p = idx.get((family.lower(), style))
            if p:
                return p
    return None


_METRICS = {}


def font_metrics(path):
    """Vertical metrics of a .ttf/.otf as fractions of the font size, read from its head, hhea and OS/2 tables:
      line   single line spacing as Office and LibreOffice lay it out (win ascent + descent; hhea when larger)
      ascent / descent / cap / x   distances from the baseline
      first  optical center of a first line below the top of its box (ascent minus half the cap height)
    Layout code uses these instead of constants tuned to one typeface. Falls back to typical sans-serif values."""
    if path in _METRICS:
        return _METRICS[path]
    m = {"line": 1.2, "ascent": 0.95, "descent": 0.25, "cap": 0.7, "x": 0.5, "first": 0.6, "source": "typical"}
    try:
        import struct
        with open(path, "rb") as fh:
            data = fh.read()
        n = struct.unpack(">H", data[4:6])[0]
        tables = {}
        for i in range(n):
            tag, _sum, off, ln = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
            tables[tag.decode("latin-1")] = (off, ln)
        upm = struct.unpack(">H", data[tables["head"][0] + 18:tables["head"][0] + 20])[0]
        ho = tables["hhea"][0]
        h_asc, h_desc, h_gap = struct.unpack(">hhh", data[ho + 4:ho + 10])
        oo, oln = tables["OS/2"]
        version = struct.unpack(">H", data[oo:oo + 2])[0]
        win_asc, win_desc = struct.unpack(">HH", data[oo + 74:oo + 78])
        cap = struct.unpack(">h", data[oo + 88:oo + 90])[0] if version >= 2 and oln >= 90 else 0.7 * upm
        xh = struct.unpack(">h", data[oo + 86:oo + 88])[0] if version >= 2 and oln >= 88 else 0.5 * upm
        asc = max(win_asc, h_asc)
        desc = max(win_desc, -h_desc)
        line = max(win_asc + win_desc, h_asc - h_desc + h_gap)
        m = {"line": line / upm, "ascent": asc / upm, "descent": desc / upm, "cap": cap / upm, "x": xh / upm,
             "first": (asc - cap / 2.0) / upm, "source": os.path.basename(path)}
    except Exception:
        pass
    _METRICS[path] = m
    return m


def fontconfig_env(extra_dirs=(), env=None):
    """Environment for LibreOffice (Linux, macOS) that also sees the bundled and project fonts, through a private
    fontconfig file: nothing is installed. On Windows, or without fontconfig, the environment is returned unchanged."""
    import tempfile
    env = dict(os.environ if env is None else env)
    if os.name == "nt":
        return env
    dirs = [d for d in list(extra_dirs) + [bundled_dir()] if d and os.path.isdir(d)]
    if not dirs:
        return env
    conf = os.path.join(tempfile.gettempdir(), "brand-fonts.conf")
    base = env.get("FONTCONFIG_FILE") or "/etc/fonts/fonts.conf"
    body = "<?xml version=\"1.0\"?>\n<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n<fontconfig>\n"
    if os.path.isfile(base):
        body += "  <include ignore_missing=\"yes\">%s</include>\n" % base
    body += "".join("  <dir>%s</dir>\n" % d.replace("&", "&amp;").replace("<", "&lt;") for d in dirs) + "</fontconfig>\n"
    with open(conf, "w", encoding="utf-8") as fh:
        fh.write(body)
    env["FONTCONFIG_FILE"] = conf
    return env


# ---------------------------------------------------------------- resolve
class Brand:
    def __init__(self, profile, base, origin):
        self.origin, self.base = origin, base
        self.notes, self.sources = [], dict(profile.get("sources") or {})
        self.name = str(profile.get("name") or "").strip()
        self.org = str(profile.get("org") or "").strip()
        self._footer = profile.get("footer")
        self.classification = str(profile.get("classification") or "").strip()
        given = {k: v.strip() for k, v in (profile.get("fonts") or {}).items() if isinstance(v, str) and v.strip()}
        self.fonts = dict(FALLBACK_FONTS)
        self.fonts.update(given)
        if given.get("body") and not given.get("heading"):
            self.fonts["heading"] = self.fonts["body"]
        if (given.get("body") or given.get("heading")) and not given.get("display"):
            self.fonts["display"] = self.fonts["heading"]
        for role in ("body", "heading", "display", "mono"):
            if role not in given and not (role in ("heading", "display") and (given.get("body") or given.get("heading"))):
                self.sources.setdefault("font_" + role, "fallback (the project names no font)")
        self.font_files = [p for p in (self._path(f) for f in (profile.get("font_files") or [])) if p]
        self.logo = self._path(profile.get("logo"))
        self.logo_on_dark = self._path(profile.get("logo_on_dark"))
        self.terminology = self._path(profile.get("terminology"))
        self.colors = self._palette(profile.get("colors") or {})
        self._png = {}

    def _path(self, p):
        if not p:
            return None
        q = p if os.path.isabs(p) else os.path.join(self.base, p)
        if os.path.isfile(q):
            return q
        self.notes.append("file not found: %s" % p)
        return None

    def _palette(self, given):
        c, derived = {}, []
        for k, v in given.items():
            role = LEGACY.get(k, k)
            h = parse_color(v) if not hex6(v) else hex6(v)
            if role in ROLES and h:
                c[role] = h
        if "primary" not in c and self.logo:
            lc = logo_color(raster(self.logo, 300) or b"")
            if lc:
                c["primary"] = lc; self.sources["primary"] = "logo's main color"
        if "primary" not in c:  # no brand color at all: the neutral palette, nothing derived
            c.update({k: v for k, v in DEFAULT_COLORS.items() if k not in c})
        for k, v in DEFAULT_COLORS.items():
            if k not in c and k not in ("dark", "secondary"):
                c[k] = v
        p = c["primary"]
        if "dark" not in c:
            d = p
            while contrast(d, "FFFFFF") < 11 and luminance(d) > 0.005:
                d = mix(d, "000000", 0.92)
            c["dark"] = d; derived.append("dark")
        if "secondary" not in c:
            c["secondary"] = mix(p, "FFFFFF", 0.7) if luminance(p) < 0.25 else p; derived.append("secondary")
        if abs((hue(c["alert"]) - hue(p) + 180) % 360 - 180) < 25 and saturation(p) > 0.3 and "alert" not in given:
            c["alert"] = "B42318"  # a red alert when the brand itself is orange
        if "alert_text" not in c:
            c["alert_text"] = c["alert"]; derived.append("alert_text")
        if "context" not in c:
            c["context"] = mix(p, "FFFFFF", 0.5); derived.append("context")
        if "card" not in c:
            c["card"] = mix(c["secondary"], "FFFFFF", 0.25); derived.append("card")
        if "callout" not in c:
            c["callout"] = c["card"]
        for role in derived:
            self.sources.setdefault(role, "derived from primary" if role in ("dark", "secondary", "context") else
                                    "derived from secondary" if role == "card" else "derived from alert")
        self._fix(c, given)
        for old, new in LEGACY.items():
            c[old] = c[new]
        return c

    def _fix(self, c, given):
        """Darken or lighten until every text pair passes; report each change against the project's own value."""
        movers = {"dark": -1, "text": -1, "primary": -1, "muted": -1, "muted_text": -1, "alert": -1, "alert_text": -1,
                  "card": 1, "context": 1, "callout": 1}
        start = dict(c)
        for _ in range(200):
            bad = [(f, b, m) for f, b, m in PAIRS if contrast(c.get(f, f), c.get(b, b)) < m]
            if not bad:
                break
            for f, b, m in bad:
                # Text-only roles move first; brand colors keep their value and the tint behind them lightens instead.
                tint_first = b in ("card", "context", "callout") and f in ("dark", "primary")
                for role in (b, f) if tint_first else (f, b):
                    if role in movers:
                        c[role] = shift_lightness(c[role], 0.02 * movers[role])
                        if c[role] in ("000000", "FFFFFF"):
                            continue
                        break
            if c["callout"] != c["card"] and "callout" not in given:
                c["callout"] = c["card"]
        for role in sorted(c):
            if c[role] != start.get(role) and role in start:
                was = given.get(role) or given.get(next((o for o, n in LEGACY.items() if n == role), ""), None)
                what = "project value" if was else "derived value"
                self.notes.append("adjusted %s %s -> %s (%s missed a contrast pair)" % (role, start[role], c[role], what))
        if c["primary"] != start["primary"] and "secondary" not in given:
            c["secondary"] = start["primary"]  # keep the brand's own color for rules and bars, never for text
            self.notes.append("secondary set to the original primary %s for decorative use" % start["primary"])

    def failures(self):
        return [(f, b, m, round(contrast(self.colors.get(f, f), self.colors.get(b, b)), 2)) for f, b, m in PAIRS
                if contrast(self.colors.get(f, f), self.colors.get(b, b)) < m]

    def footer(self, year=None):
        y = str(year or datetime.date.today().year)
        if self._footer is not None:
            org = self.org or self.name
            text = str(self._footer).replace("{year}", y)
            if org.endswith("."):
                text = text.replace("{org}.", "{org}")  # "Northwind Ltd." + "." would print "Ltd.."
            return text.replace("{org}", org).strip()
        parts = ["\u00a9" + y + " " + self.org] if self.org else []
        if self.classification:
            parts.append(self.classification)
        return " ".join(parts) if parts else ""

    @property
    def display_name(self):
        return self.name or self.org or ""

    def logo_png(self, on="light", width=1200):
        """PNG bytes of the logo for a light or dark background, or None (never a guess: no logo means none drawn)."""
        key = (on, width)
        if key not in self._png:
            png = None
            if on == "dark":
                if self.logo_on_dark:
                    png = raster(self.logo_on_dark, width)
                elif self.logo:
                    src = raster(self.logo, width)
                    png = knockout(src) if src else None
            elif self.logo:
                png = raster(self.logo, width)
            self._png[key] = png
        return self._png[key]

    def logo_size(self, on="light"):
        png = self.logo_png(on)
        if not png:
            return None
        try:
            from PIL import Image
            return Image.open(io.BytesIO(png)).size
        except Exception:
            import struct
            return struct.unpack(">II", png[16:24]) if png[:8] == b"\x89PNG\r\n\x1a\n" else None

    def font_dirs(self):
        """Folders holding the project's own font files (for measuring, embedding and LibreOffice)."""
        return sorted({os.path.dirname(p) for p in self.font_files})

    def font_path(self, role="body", bold=False, italic=False):
        """The file for a role's font in that style, or None when it isn't available on this machine."""
        return find_font(self.fonts.get(role) or self.fonts["body"], bold, italic, self.font_dirs())

    def measure_path(self, role="body", bold=False, italic=False):
        """A file to measure text with: the role's own font, else the bundled fallback (close metrics, never a guess)."""
        return self.font_path(role, bold, italic) or find_font(FALLBACK_FONTS["mono" if role == "mono" else "body"], bold, italic)

    def metrics(self, role="body", bold=False):
        """font_metrics() for the file a role is measured with: what layouts use for line height and first-line centers."""
        p = self.measure_path(role, bold)
        return font_metrics(p) if p else font_metrics("")

    def font_status(self):
        """{role: 'project file' | 'bundled' | 'installed' | 'missing'}: where each role's font file comes from."""
        out, bdir = {}, bundled_dir()
        for role in ("body", "display", "mono"):
            p = self.font_path(role, bold=role == "display")
            out[role] = ("missing" if not p else "project file" if any(p.startswith(d) for d in self.font_dirs())
                         else "bundled" if bdir and p.startswith(bdir) else "installed")
        return out

    def logo_alt(self):
        return "%s logo" % self.display_name if self.display_name else "Logo"

    def apply(self, theme):
        """Overlay this brand on a skill theme dict (colors and fonts), keeping keys the theme defines."""
        cols = theme.setdefault("colors", {})
        for k in list(cols) + [r for r in ROLES if r not in cols]:
            if k in self.colors:
                cols[k] = self.colors[k]
        fonts = theme.setdefault("fonts", {})
        for k in set(fonts) | {"body", "heading", "display", "mono"}:  # every role, so themes never need to name a font
            if k in self.fonts:
                fonts[k] = self.fonts[k]
        return theme

    def as_profile(self):
        r = lambda p: rel(self.base, p) if p else None
        out = {"format": "brand-profile", "version": 1, "name": self.name or None, "org": self.org or None,
               "footer": self._footer, "classification": self.classification or None, "logo": r(self.logo),
               "logo_on_dark": r(self.logo_on_dark), "terminology": r(self.terminology),
               "colors": {k: "#" + self.colors[k] for k in ROLES}, "fonts": self.fonts, "font_files": [r(p) for p in self.font_files],
               "sources": self.sources,
               "adjustments": self.notes, "origin": self.origin}
        return {k: v for k, v in out.items() if v not in (None, [], {})}

    def lines(self):
        logo = self.logo and rel(self.base, self.logo)
        out = ["BRAND: %s (%s)" % (self.display_name or "unnamed", self.origin)]
        for role in ("primary", "dark", "secondary", "alert", "text"):
            out.append("  %-9s #%s  %s" % (role, self.colors[role], self.sources.get(role, "default")))
        st = self.font_status()
        out.append("  fonts     body %s, display %s, mono %s  %s" % (self.fonts["body"], self.fonts["display"], self.fonts["mono"],
                                                                   self.sources.get("font_body", "profile")))
        missing = [r for r, s in st.items() if s == "missing"]
        if missing:
            out.append("  note      no font file on this machine for %s: outputs still name the font; text is measured with "
                       "the bundled %s and PDFs embed what the converter finds" % (", ".join("%s (%s)" % (r, self.fonts[r]) for r in missing), FALLBACK_FONTS["body"]))
        if logo:
            dark = ("variant " + rel(self.base, self.logo_on_dark)) if self.logo_on_dark else ("white knockout" if self.logo_png("dark") else "none (light slides only)")
            ok = "" if self.logo_png("light") else " (could not be read: install PyMuPDF for SVG; no logo will be drawn)"
            out.append("  logo      %s%s; on dark: %s  %s" % (logo, ok, dark, self.sources.get("logo", "profile")))
        else:
            out.append("  logo      none (nothing found; add brand.json or a logo file to brand the cover)")
        out.append("  footer    %s" % (repr(self.footer()) if self.footer() else "none"))
        for n in self.notes:
            out.append("  note      " + n)
        bad = self.failures()
        out.append("BRAND_CONTRAST: %d pairs, %d failed%s" % (len(PAIRS), len(bad), "".join(" [%s on %s %.2f < %.1f]" % (f, b, r_, m) for f, b, m, r_ in bad)))
        return out


def _explicit(source=None, brand=None):
    if brand:
        return os.path.abspath(brand)
    if source and os.path.isfile(source) and source.lower().endswith(".json"):
        try:
            m = (read_json(source) or {}).get("meta") or {}
        except (ValueError, OSError, AttributeError):
            m = {}
        if isinstance(m.get("brand"), str) and m["brand"] != "auto":
            q = m["brand"] if os.path.isabs(m["brand"]) else os.path.join(os.path.dirname(os.path.abspath(source)), m["brand"])
            return q
    env = os.environ.get("BRAND_PROFILE")
    return os.path.abspath(env) if env else None


_CACHE = {}


def load(source=None, brand=None, project=None):
    """The brand for a build: explicit profile > brand.json beside the source or at the project root > detected > defaults."""
    key = (source and os.path.abspath(source), brand, project, os.environ.get("BRAND_PROFILE"), os.environ.get("BRAND_PROJECT"))
    if key in _CACHE:
        return _CACHE[key]
    exp = _explicit(source, brand)
    src_dir = os.path.dirname(os.path.abspath(source)) if source else None
    root = os.path.abspath(project) if project else project_root(src_dir)
    paths = [exp] if exp else []
    for d in [x for x in (src_dir, root) if x]:
        paths += [os.path.join(d, n) for n in PROFILE_NAMES]
    for p in paths:
        if p and os.path.isfile(p):
            try:
                prof = read_json(p)
            except ValueError as e:
                raise SystemExit("STOPPED: brand profile %s is not valid JSON (%s)" % (p, e))
            if prof.get("detect", False):
                det = detect(root)
                det.update({k: v for k, v in prof.items() if k not in ("colors", "fonts", "sources")})
                det["colors"] = dict(det.get("colors", {}), **prof.get("colors", {}))
                det["fonts"] = dict(det.get("fonts", {}), **prof.get("fonts", {}))
                prof = det
            b = Brand(prof, os.path.dirname(p), "profile " + p)
            _CACHE[key] = b
            return b
        if p == exp:
            raise SystemExit("STOPPED: brand profile %s not found" % p)
    prof = detect(root)
    has = prof.get("colors") or prof.get("logo") or prof.get("fonts")
    b = Brand(prof, root, ("detected in " + root) if has else "neutral defaults; nothing found in " + root)
    _CACHE[key] = b
    return b


def check_profile(path):
    errs = []
    try:
        prof = read_json(path)
    except (OSError, ValueError) as e:
        return ["BRAND_SCHEMA: %s can't be read (%s)" % (path, e)]
    known = {"format", "version", "name", "org", "footer", "classification", "logo", "logo_on_dark", "terminology",
             "colors", "fonts", "font_files", "sources", "adjustments", "origin", "detect", "$schema", "_about"}
    for k in prof:
        if k not in known:
            errs.append("BRAND_SCHEMA: unknown key %r" % k)
    for k, v in (prof.get("colors") or {}).items():
        if LEGACY.get(k, k) not in ROLES:
            errs.append("BRAND_SCHEMA: unknown color role %r (roles: %s)" % (k, ", ".join(ROLES)))
        elif not parse_color(v):
            errs.append("BRAND_SCHEMA: colors.%s %r is not a color" % (k, v))
    for k in ("logo", "logo_on_dark", "terminology"):
        if prof.get(k) and not os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(path)), prof[k])):
            errs.append("BRAND_SCHEMA: %s file %r not found" % (k, prof[k]))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect"); d.add_argument("--project"); d.add_argument("--out")
    s = sub.add_parser("show"); s.add_argument("--source"); s.add_argument("--brand"); s.add_argument("--project")
    c = sub.add_parser("check"); c.add_argument("profile")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        errs = check_profile(a.profile)
        b = None if errs else load(brand=a.profile)
        for e in errs:
            print("FAIL [%s] %s" % tuple(e.split(": ", 1)))
        if b:
            print("\n".join(b.lines()))
        n = len(errs) + (len(b.failures()) if b else 0)
        print("BRAND_CHECK: %d failed" % n)
        return 1 if n else 0
    if a.cmd == "detect":
        root = os.path.abspath(a.project) if a.project else project_root()
        prof = detect(root)
        b = Brand(prof, root, "detected in " + root if (prof.get("colors") or prof.get("logo")) else "neutral defaults; nothing found in " + root)
        print("\n".join(b.lines()))
        if a.out:
            out = b.as_profile()
            outdir = os.path.dirname(os.path.abspath(a.out))
            for k in ("logo", "logo_on_dark", "terminology"):
                p = getattr(b, k)
                if p:
                    out[k] = os.path.relpath(p, outdir).replace(os.sep, "/")
            out.pop("origin", None)
            with open(a.out, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2, ensure_ascii=False)
            print("wrote " + a.out + " (edit it to correct anything above; builds use it from now on)")
        return 0
    b = load(source=a.source, brand=a.brand, project=a.project)
    print("\n".join(b.lines()))
    return 1 if b.failures() else 0


if __name__ == "__main__":
    sys.exit(main())
