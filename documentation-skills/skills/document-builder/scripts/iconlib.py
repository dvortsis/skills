"""Tabler outline icons for decks and documents (MIT, see assets/icons/LICENSE-tabler.txt).

Icons ship as text (assets/icons/tabler.json: Iconify SVG bodies on a 24x24 grid, 2px round strokes). This module
parses the path data (M L H V C S Q T A Z, absolute and relative) into absolute moves, lines and cubic curves, then
  * drawingml(name, color_hex, size_in) -> <a:custGeom> + <a:ln> XML for a native, recolorable PowerPoint shape
  * png(name, color_hex, px) -> PNG bytes rendered at 8x and downsampled (for Word, which can't take custGeom easily)
Shared by slide-deck and document-builder (identical copies; the self-tests check both)."""
import io, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_FILE = os.path.join(os.path.dirname(HERE), "assets", "icons", "tabler.json")
_SET = None


def icon_set():
    global _SET
    if _SET is None:
        _SET = json.load(open(ICON_FILE, encoding="utf-8"))
    return _SET


def names():
    return sorted(icon_set()["icons"])


def exists(name):
    return name in icon_set()["icons"]


_TOK = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _arc_flag_split(tokens):
    """SVG allows arc flags written without separators (e.g. 'a2 2 0 0 1-4 0' is fine, '0 011 1' compresses flags)."""
    return tokens


def _arc_to_cubic(x1, y1, rx, ry, phi, fa, fs, x2, y2):
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [((x1, y1), (x2, y2), (x2, y2))] if (x1, y1) != (x2, y2) else []
    rx, ry = abs(rx), abs(ry)
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = c * dx + s * dy, -s * dx + c * dy
    lam = (x1p ** 2) / rx ** 2 + (y1p ** 2) / ry ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0, num / den)) if den else 0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = c * cxp - s * cyp + (x1 + x2) / 2, s * cxp + c * cyp + (y1 + y2) / 2
    ang = lambda ux, uy, vx, vy: math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(math.ceil(abs(dt) / (math.pi / 2) - 1e-9)))
    out, d = [], dt / n
    k = 4 / 3 * math.tan(d / 4)
    pt = lambda t: (cx + rx * math.cos(t) * c - ry * math.sin(t) * s, cy + rx * math.cos(t) * s + ry * math.sin(t) * c)
    der = lambda t: (-rx * math.sin(t) * c - ry * math.cos(t) * s, -rx * math.sin(t) * s + ry * math.cos(t) * c)
    t = t1
    for _ in range(n):
        p0, p3 = pt(t), pt(t + d)
        d0, d3 = der(t), der(t + d)
        out.append(((p0[0] + k * d0[0], p0[1] + k * d0[1]), (p3[0] - k * d3[0], p3[1] - k * d3[1]), p3))
        t += d
    return out


def parse(d):
    """Return subpaths: list of (closed, [("M",(x,y)), ("L",(x,y)), ("C",(c1,c2,p)), ...]) in absolute coordinates."""
    toks = _TOK.findall(d)
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    last_c2 = last_q = None
    subs, cur = [], None
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    def flag():
        nonlocal i
        t = toks[i]
        if len(t) > 1 and t[0] in "01" and not t.startswith(("0.", "1.")):
            toks[i] = t[1:]; return float(t[0])
        i += 1; return float(t)
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
            if cmd in "Zz":
                if cur:
                    cur[0] = True; x, y = sx, sy; subs.append(cur); cur = None
                last_c2 = last_q = None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if cur is None and C != "M":
            cur = [False, [("M", (x, y))]]  # drawing continues after Z from the subpath start (SVG spec)
        if C == "M":
            x, y = num() + ox, num() + oy
            if cur: subs.append(cur)
            cur = [False, [("M", (x, y))]]; sx, sy = x, y
            cmd = "l" if rel else "L"; last_c2 = last_q = None
        elif C in "LHV":
            if C == "L": x, y = num() + ox, num() + oy
            elif C == "H": x = num() + (x if rel else 0)
            else: y = num() + (y if rel else 0)
            cur[1].append(("L", (x, y))); last_c2 = last_q = None
        elif C == "C":
            c1 = (num() + ox, num() + oy); c2 = (num() + ox, num() + oy); x, y = num() + ox, num() + oy
            cur[1].append(("C", (c1, c2, (x, y)))); last_c2 = c2; last_q = None
        elif C == "S":
            c1 = (2 * x - last_c2[0], 2 * y - last_c2[1]) if last_c2 else (x, y)
            c2 = (num() + ox, num() + oy); x, y = num() + ox, num() + oy
            cur[1].append(("C", (c1, c2, (x, y)))); last_c2 = c2; last_q = None
        elif C in "QT":
            if C == "Q": q = (num() + ox, num() + oy)
            else: q = (2 * x - last_q[0], 2 * y - last_q[1]) if last_q else (x, y)
            nx, ny = num() + ox, num() + oy
            c1 = (x + 2 / 3 * (q[0] - x), y + 2 / 3 * (q[1] - y)); c2 = (nx + 2 / 3 * (q[0] - nx), ny + 2 / 3 * (q[1] - ny))
            x, y = nx, ny
            cur[1].append(("C", (c1, c2, (x, y)))); last_q = q; last_c2 = None
        elif C == "A":
            rx, ry, phi = num(), num(), num(); fa, fs = flag(), flag(); nx, ny = num() + ox, num() + oy
            for c1, c2, p in _arc_to_cubic(x, y, rx, ry, phi, int(fa), int(fs), nx, ny):
                cur[1].append(("C", (c1, c2, p)))
            x, y = nx, ny; last_c2 = last_q = None
        else:
            raise ValueError("unsupported path command %r" % cmd)
    if cur: subs.append(cur)
    return subs


def paths(name):
    body = icon_set()["icons"][name]
    out = []
    for d in re.findall(r' d="([^"]+)"', body):
        out.extend(parse(d))
    return out


def drawingml(name, color_hex, size_in, stroke_px=2.0):
    """custGeom + line XML (no fill) for a size_in square. Stroke scales with the icon: 2px on 24 -> size/12 in."""
    S = 1000
    parts = []
    for closed, segs in paths(name):
        for kind, v in segs:
            if kind == "M":
                parts.append('<a:moveTo><a:pt x="%d" y="%d"/></a:moveTo>' % (round(v[0] * S), round(v[1] * S)))
            elif kind == "L":
                parts.append('<a:lnTo><a:pt x="%d" y="%d"/></a:lnTo>' % (round(v[0] * S), round(v[1] * S)))
            else:
                parts.append("<a:cubicBezTo>" + "".join('<a:pt x="%d" y="%d"/>' % (round(p[0] * S), round(p[1] * S)) for p in v) + "</a:cubicBezTo>")
        if closed:
            parts.append("<a:close/>")
    geom = ('<a:custGeom xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>'
            '<a:rect l="0" t="0" r="r" b="b"/><a:pathLst><a:path w="%d" h="%d" fill="none">%s</a:path></a:pathLst></a:custGeom>') % (24 * S, 24 * S, "".join(parts))
    w_emu = int(round(size_in * stroke_px / 24.0 * 914400))
    line = ('<a:ln xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" w="%d" cap="rnd"><a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
            '<a:round/></a:ln>') % (w_emu, color_hex.upper())
    return geom, line, w_emu


def _flatten(segs, steps=24):
    pts, out = [], []
    for kind, v in segs:
        if kind == "M":
            if len(pts) > 1: out.append(pts)
            pts = [v]
        elif kind == "L":
            pts.append(v)
        else:
            p0 = pts[-1]; c1, c2, p3 = v
            for k in range(1, steps + 1):
                t = k / steps; u = 1 - t
                pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p3[0],
                            u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p3[1]))
    if pts: out.append(pts)
    return out


def png(name, color_hex, px=96, stroke_px=2.0):
    """Render the icon to PNG bytes (transparent background) at 8x supersampling for crisp edges."""
    from PIL import Image, ImageDraw
    ss = 8
    big = px * ss
    sc = big / 24.0
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    col = tuple(int(color_hex[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    w = max(1, int(round(stroke_px * sc)))
    r = w / 2.0
    for closed, segs in paths(name):
        for poly in _flatten(segs):
            p = [(a * sc, b * sc) for a, b in poly]
            if closed and p[0] != p[-1]:
                p.append(p[0])
            if len(p) > 1:
                dr.line(p, fill=col, width=w, joint="curve")
            for a, b in (p[0], p[-1]) if not closed else []:
                dr.ellipse([a - r, b - r, a + r, b + r], fill=col)
            if len(p) == 1 or (len(p) == 2 and abs(p[0][0] - p[1][0]) < 1 and abs(p[0][1] - p[1][1]) < 1):
                a, b = p[0]; dr.ellipse([a - r, b - r, a + r, b + r], fill=col)
    im = im.resize((px, px), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def load_overlay(path):
    """Merge extra Tabler outline icons saved next to deck.json (icons.local.json, an Iconify JSON response such as
    https://api.iconify.design/tabler.json?icons=name1,name2). Filled icons are rejected: the set is outline only.
    Returns (added, rejected) name lists."""
    added, rejected = [], []
    if not path or not os.path.isfile(path):
        return added, rejected
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return added, ["(unreadable %s)" % os.path.basename(path)]
    for k, body in (data.get("icons") or {}).items():
        if 'stroke="currentColor"' in body and 'fill="currentColor"' not in body and " d=" in body:
            try:
                parse(" ".join(re.findall(r' d="([^"]+)"', body)))
            except (ValueError, IndexError):
                rejected.append(k); continue
            if k not in icon_set()["icons"]:
                icon_set()["icons"][k] = body; added.append(k)
        else:
            rejected.append(k)
    return added, rejected
