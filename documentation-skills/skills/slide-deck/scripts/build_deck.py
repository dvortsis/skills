#!/usr/bin/env python3
"""Build a modern, minimal deck (.pptx) in the project's brand from deck.json (schema: references/deck-schema.md).

  python3 scripts/build_deck.py deck.json --out out/Deck.pptx [--draft] [--brand brand.json]

The brand (logo, colors, fonts, footer) comes from scripts/brand.py: --brand, meta.brand, a brand.json in the project,
or what the project's own files define. Every slide sits on a master generated from that brand (scripts/master.py), so
the logo, footer line and slide numbers come from the master. Content is drawn as native, editable shapes and charts: rounded cards,
pill bars on light tracks, tinted callouts, ring-node timelines, rounded screenshots with numbered callouts.
The design gate (lint_deck.py, deck.json phase) runs first and blocks the build on any FAIL. --draft draws a
labelled frame for a missing screenshot and writes <deck>.shotlist.md beside deck.json (ID, what to capture, screen state,
target slide, up to three callout positions, capture rules). Never hand-edit the .pptx; edit deck.json.
"""
import argparse, json, os, re, sys
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_MARK, XL_MARKER_STYLE
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
sys.path.insert(0, HERE)
from lint_deck import T, Fit, LH, FL, proper, normalize, use_brand, widow, STATUS_AT_START, STATUSES  # noqa: E402  (one theme, measurer, font metrics and Proper Case rule for build and lint)
import brand as BR  # noqa: E402  (project brand: logo, colors, fonts, footer)
import iconlib  # noqa: E402  (Tabler outline icons as native vector shapes)
import master  # noqa: E402  (the generated, brand-colored slide master)
C, S, F, R, G = T["colors"], T["sizes_pt"], T["fonts"], T["radius_in"], T["slide"]
MIN = T["min_pt"]
FIT = Fit()
W, H = G["width_in"], G["height_in"]
LX, RX = G["left_in"], G["right_in"]
CW = RX - LX
TT, BT, BB = G["title_top_in"], G["body_top_in"], G["body_bottom_in"]
CHARTS = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED, "line": XL_CHART_TYPE.LINE,
          "stacked_bar": XL_CHART_TYPE.BAR_STACKED, "stacked_column": XL_CHART_TYPE.COLUMN_STACKED}
DARK = {"cover_primary", "cover_dark", "section", "dark", "hero"}
TAKE_TOP, TAKE_H = 5.4, 0.9  # insight box band; visuals above it end at TAKE_TOP - 0.2

INSET = 0.04      # text-box inner margin: a text's ink starts INSET in from its box


def first_line_center(top, size_pt, font=None):
    """Y of the optical center of the first line in a top-anchored text box at `top` (inches). The offset comes from
    the font file (ascent minus half the cap height; 0.62 of the size for Lato, 0.60 for Inter, 0.73 for Segoe UI),
    so markers, icons and dots line up with the text in whatever font the project uses."""
    return top + INSET + FL(font) * size_pt / 72.0


def rgb(name):
    return RGBColor.from_string(C.get(name, name))


def fmt(v, f):
    f = f or "General"
    cur = "$" if "$" in f else ""
    if "%" in f:
        dec = f.split(".")[1].count("0") if "." in f else 0
        return ("{:.%df}%%" % dec).format(v * 100)
    if '"M"' in f:
        return "%s%.1fM" % (cur, v / 1e6)
    if '"K"' in f:
        return "%s%.0fK" % (cur, v / 1e3)
    if "," in f:
        return cur + "{:,.0f}".format(v)
    return cur + (str(int(v)) if float(v).is_integer() else str(v))


GENERIC_SHOT = "The screen this slide walks through"
STATUS_MULTI = sorted((s for s in STATUSES if " " in s), key=len, reverse=True)


class Builder:
    def __init__(self, deck, base, draft, brand=None):
        self.deck, self.base, self.draft = deck, base, draft
        self.meta = deck.get("meta", {})
        self.brand = use_brand(brand or BR.load(project=base))
        self.prs, self.layouts = master.build(T, self.brand, logo=self.meta.get("logo") != "none")
        self.shots, self.n = [], 0
        self.cur, self.ui_slides, self.deck_path, self.by_n, self.shotlist_kept = {}, [], None, {}, False

    def missing_images(self):
        return [d for d in self.deck.get("slides", []) if d.get("image") and not os.path.isfile(os.path.join(self.base, d["image"]))]

    def shot(self, file, alt):
        """Record a missing screenshot with up to three callout positions for the shot list."""
        pos = [c for c in (self.cur.get("callouts") or []) + (self.cur.get("annotations") or []) if isinstance(c, dict) and "x" in c and "y" in c][:3]
        self.shots.append((self.n, file, alt, ", ".join("%d at %d%%, %d%%" % (i, round(100 * c["x"]), round(100 * c["y"])) for i, c in enumerate(pos, 1)) or "none"))

    def write_shotlist(self, path):
        """<deck>.shotlist.md: one row per missing screenshot and per slide that walks through a screen without one."""
        if os.path.isfile(path):
            old = open(path, encoding="utf-8").read()
            if re.search(r"(?m)^\| S\d+ \|", old) and GENERIC_SHOT not in old:
                self.shotlist_kept = True  # a specific, screen-by-screen shot list is never replaced by a generated one
                return len(re.findall(r"(?m)^\| S\d+ \|", old))
        rows = [(n, f, a, c) for n, f, a, c in self.shots]
        have = {r[0] for r in rows}
        for n, t in self.ui_slides:
            if n in have:
                continue
            d = self.by_n.get(n, {})
            steps = [x.get("label", "") for x in (d.get("steps") or (d.get("diagram") or {}).get("nodes") or []) if isinstance(x, dict)]
            state = ("After '%s', showing %s" % (steps[-1], ", ".join(steps[:-1]) or "the controls used")) if steps else "Showing what the slide titled '%s' describes" % t
            callouts = ", ".join("%d %s" % (i, s) for i, s in enumerate(steps[:3], 1)) or "1 the control named in the slide title"
            rows.append((n, t, state, callouts))
        lines = ["# Shot List: %s" % self.meta.get("title", "deck"), "", "Screenshots: pending. Supply these, then rebuild without --draft.", "",
                 "| ID | Shows | Screen State | Used In | Callouts |", "|---|---|---|---|---|"]
        lines += ["| S%d | %s | %s | slide %d | %s |" % (k, (f or "").replace("|", "/"), (a or "").replace("|", "/"), n, c) for k, (n, f, a, c) in enumerate(sorted(rows), 1)]
        lines += ["", "Capture rules: light mode; at least 1,600 px wide; PNG; no PHI or real patient data; employee and partner names masked "
                  "(placeholder names or blurred); full window unless the row says otherwise.", ""]
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        return len(rows)

    # ---------------- primitives ----------------
    def new(self, key):
        s = self.prs.slides.add_slide(self.layouts[key])
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        self.n += 1
        return s

    def text(self, box, x, y, w, h, paras, name, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, fit=None):
        """paras: [{t | runs:[(text, color)], size, font, bold, italic, color, bullet, after}].
        fit: a min_pt key; text starts at its template size and steps down 1pt at a time until it fits the box."""
        paras = [self.glue(p) for p in paras]
        if fit:
            paras = self.autofit(paras, w - 0.08, h - 0.08, MIN[fit])
        if name in self.ORPHAN_NAMES and len(paras) == 1 and paras[0].get("size"):
            floor = MIN[fit] if fit else max(9, paras[0]["size"] - 2)  # unfitted labels may give up two points at most
            paras = self.no_orphan(paras, w - 0.08, h - 0.08, floor, name)
        tb = box.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tb.name = name
        tf = tb.text_frame
        tf.word_wrap, tf.auto_size, tf.vertical_anchor = True, MSO_AUTO_SIZE.NONE, anchor
        for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, side, Inches(0.04))
        for i, p in enumerate(paras):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = p.get("align", align)
            if p.get("after") is not None:
                par.space_after = Pt(p["after"])
            runs = p.get("runs") or [(p["t"], p.get("color", "text"))]
            breaks = set()
            if name == "title" and len(paras) == 1:
                full = "".join(str(t) for t, _c in runs)
                wl = FIT.render_wrap(full, p.get("size", S["body"]), p.get("font", F["body"]), p.get("bold", False), w - 0.08)  # D-25: break where the render would
                pos = 0
                for line in wl[:-1]:
                    pos = full.index(line, pos) + len(line)
                    breaks.add(pos)
            gpos = 0
            for txt, col in runs:
                txt = str(txt)
                pieces, start = [], 0
                for k, ch in enumerate(txt):
                    if gpos + k in breaks and ch == " ":
                        pieces.append(txt[start:k]); start = k + 1
                pieces.append(txt[start:])
                gpos += len(txt)
                for pi, piece in enumerate(pieces):
                    if pi:
                        par.add_line_break()
                    if not piece:
                        continue
                    r = par.add_run()
                    r.text = piece
                    f = r.font
                    f.name = p.get("font", F["body"])
                    f.size = Pt(p.get("size", S["body"]))
                    f.bold = p.get("bold", False)
                    f.italic = p.get("italic", False)
                    f.color.rgb = rgb(col)
            if p.get("bullet"):
                self._bullet(par, p.get("size", S["body"]), p.get("bullet_color", "primary"))
        return tb

    GLUE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Q[1-4]|FY|H[12]|No\.|Step|Phase|Wave|Cycle|Region)\.? (\d[\d,]*)\b|\b\d{1,2}(?::\d\d)? (?:a\.m\.|p\.m\.|am\b|pm\b|AM\b|PM\b)")

    def glue(self, p):
        """Keep dates, quarters, times and numbered labels on one line with a no-break space ('Nov 17', 'Q1 2027', '6 a.m.')."""
        def f(t):
            t = self.GLUE.sub(lambda m: m.group(0).replace(" ", "\u00a0"), t)
            for st in STATUS_MULTI:  # statuses stay whole; the only break is after "\u00b7" ("FIXED \u00b7 / AWAITING RETEST")
                t = t.replace(st, st.replace(" \u00b7 ", "\u00a0\u00b7\u2009").replace(" ", "\u00a0").replace("\u2009", " "))
            return t
        if p.get("runs"):
            return dict(p, runs=[(f(t), c) for t, c in p["runs"]])
        return dict(p, t=f(p["t"])) if "t" in p else p

    ORPHAN_NAMES = ("title", "subtitle", "diagram:label", "takeaway:text")  # the texts lint LAST_LINE_ORPHAN reads

    def no_orphan(self, paras, w, h, floor, name="title"):
        """Step one paragraph down (to its floor) until its last line carries at least two words, measured in the
        deck's own font, so a wider or narrower font never strands one word on the last line."""
        p = paras[0]
        txt = "".join(t for t, _c in p["runs"]) if p.get("runs") else p.get("t", "")
        font, bold = p.get("font", F["body"]), p.get("bold", False)
        title = name == "title"
        for size in range(int(p["size"]), int(floor) - 1, -1):
            wl = FIT.render_wrap(txt, size, font, bold, w)  # D-25: the wrap a viewer sees, as lint ORPHAN reads it
            bad = widow(FIT, wl, size, font, bold, w, False) or (title and widow(FIT, wl, size, font, bold, w, True))
            if not bad:
                if len(wl) * size * LH(font, bold) / 72 <= h + 0.04:
                    return [dict(p, size=size)]
        return paras

    @staticmethod
    def autofit(paras, w, h, floor):
        base = paras[0].get("size", S["body"])
        trial = paras
        for size in range(int(base), int(floor) - 1, -1):
            k = size / float(base)
            trial = [dict(p, size=max(int(floor) if i == 0 else 9, int(round(p.get("size", S["body"]) * k)))) for i, p in enumerate(paras)]
            spec = [(" ".join(t for t, _c in (p.get("runs") or [(p["t"], None)])), p["size"], p.get("font", F["body"]), p.get("bold", False),
                     p.get("after") or 0, bool(p.get("bullet"))) for p in trial]
            if FIT.fits(None, spec, w, h, False):
                return trial
        return trial

    @staticmethod
    def _bullet(par, size, color):
        pPr = par._p.get_or_add_pPr()
        ind = int(Pt(size) * 1.15)
        pPr.set("marL", str(ind)); pPr.set("indent", str(-ind))
        clr = pPr.makeelement(qn("a:buClr"), {})
        clr.append(clr.makeelement(qn("a:srgbClr"), {"val": C.get(color, color)}))
        pPr.append(clr)
        pPr.append(pPr.makeelement(qn("a:buSzPct"), {"val": "100000"}))
        pPr.append(pPr.makeelement(qn("a:buFont"), {"typeface": F["body"]}))  # the bullet glyph in the deck's own font
        pPr.append(pPr.makeelement(qn("a:buChar"), {"char": "\u2022"}))

    ACCENT_T = 0.08

    def accent_card(self, box, x, y, w, h, side, accent, fill="white", line=None, line_w=0.75, radius=None, shadow=False, name="card"):
        """Layered accent: a rounded shape in the accent color sits behind the card with the same corner radius, showing
        only on the accent side (top or left); the outer bounds stay x, y, w, h. meta.accent_style "line" keeps the old
        flat strip for teams that need it."""
        t = self.ACCENT_T
        if self.meta.get("accent_style") == "line":
            card = self.shape(box, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, line=line, line_w=line_w, name=name, radius=radius, shadow=shadow)
            if side == "top":
                self.shape(box, MSO_SHAPE.RECTANGLE, x + 0.02, y + 0.02, w - 0.04, 0.08, fill=accent, name="accent:line")
            else:
                self.shape(box, MSO_SHAPE.RECTANGLE, x, y + 0.08, 0.06, h - 0.16, fill=accent, name="accent:line")
            return card
        self.shape(box, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=accent, name="accent:back", radius=radius)
        if side == "top":
            return self.shape(box, MSO_SHAPE.ROUNDED_RECTANGLE, x, y + t, w, h - t, fill=fill, line=line, line_w=line_w, name=name, radius=radius, shadow=shadow)
        return self.shape(box, MSO_SHAPE.ROUNDED_RECTANGLE, x + t, y, w - t, h, fill=fill, line=line, line_w=line_w, name=name, radius=radius, shadow=shadow)

    def shape(self, box, kind, x, y, w, h, fill=None, line=None, name="shape", line_w=1.0, radius=None, shadow=False, alpha=None):
        sh = box.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.name = name
        sh.shadow.inherit = False
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
            if alpha is not None:
                clr = sh._element.spPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
                clr.append(clr.makeelement(qn("a:alpha"), {"val": str(int(alpha * 100000))}))
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(line_w)
        else:
            sh.line.fill.background()
        if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = min(0.5, radius / min(w, h))
        if shadow:
            self.soft_shadow(sh)
        return sh

    @staticmethod
    def soft_shadow(sh):
        spPr = sh._element.spPr
        for e in spPr.findall(qn("a:effectLst")):
            spPr.remove(e)
        eff = spPr.makeelement(qn("a:effectLst"), {})
        sd = eff.makeelement(qn("a:outerShdw"), {"blurRad": "190500", "dist": "38100", "dir": "5400000", "algn": "t", "rotWithShape": "0"})
        clr = sd.makeelement(qn("a:srgbClr"), {"val": C["black"]})
        clr.append(clr.makeelement(qn("a:alpha"), {"val": "13000"}))
        sd.append(clr); eff.append(sd)
        ln = spPr.find(qn("a:ln"))
        if ln is not None:
            ln.addnext(eff)
        else:
            spPr.append(eff)

    CONTACT_ICONS = {"email": "mail", "mail": "mail", "channel": "messages", "chat": "messages", "teams": "messages", "phone": "phone",
                     "office hours": "clock", "hours": "clock", "web": "link", "link": "link", "site": "world", "ticket": "lifebuoy", "help desk": "headset"}
    KIND_ICONS = {"example": "book", "tip": "bulb", "note": "info-circle", "warning": "alert-triangle"}

    def icon(self, box, name, x, y, size, color, tag=None):
        """Place a Tabler outline icon as a native, recolorable vector shape (no fill, round 2px-on-24 stroke)."""
        from pptx.oxml import parse_xml
        sh = box.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(size), Inches(size))
        sh.name = tag or ("icon:" + name)
        spPr = sh._element.spPr
        for child in list(spPr):
            if child.tag.endswith("}prstGeom") or child.tag.endswith("}solidFill") or child.tag.endswith("}ln") or child.tag.endswith("}noFill"):
                spPr.remove(child)
        geom, line, _w = iconlib.drawingml(name, T["colors"][color], size)
        xfrm = spPr.find(qn("a:xfrm"))
        spPr.insert(list(spPr).index(xfrm) + 1, parse_xml(geom))
        spPr.append(parse_xml('<a:noFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'))
        spPr.append(parse_xml(line))
        st = sh._element.find(qn("p:style"))
        if st is not None:
            sh._element.remove(st)
        sh.text_frame.text = ""
        return sh

    def numbered_text(self, box, x, slot_top, w, slot_h, num, paras, name, fit, d, fill, fg, mname, msize, gap=0.3, bold=False, valign="center"):
        """A number marker and its text: the text block is fitted, then centered in its slot (or top-aligned), and the
        marker is centered on the text's FIRST line, so numbers line up with their text however it wraps."""
        tx, tw = x + d + gap, w - d - gap
        paras = self.autofit(paras, tw - 2 * INSET, slot_h - 2 * INSET, MIN[fit])
        fs = paras[0]["size"]
        txt = " ".join(p.get("t", "") for p in paras)
        th = min(slot_h, FIT.lines(txt, fs, paras[0].get("font", F["body"]), bold or paras[0].get("bold", False), tw - 2 * INSET) * fs * LH() / 72 + 2 * INSET + 0.02)
        ty = slot_top + ((slot_h - th) / 2 if valign == "center" else 0)
        self.text(box, tx, ty, tw, th, paras, name)
        cy = first_line_center(ty, fs)
        self.circle_num(box, x, cy - d / 2, d, num, fill, fg, name=mname, size=msize)
        return ty, th

    def circle_num(self, box, x, y, d, num, fill, fg, line=None, name="marker", size=None):
        c = self.shape(box, MSO_SHAPE.OVAL, x, y, d, d, fill=fill, line=line, name=name, line_w=1.5)
        tf = c.text_frame
        for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, side, 0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        if str(num) == "":
            return c
        r = p.add_run(); r.text = str(num)
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = F["body"], Pt(size or S["label"]), True, rgb(fg)
        return c

    @staticmethod
    def alt(shape, text):
        el = shape._element
        for tag in ("p:nvGraphicFramePr", "p:nvPicPr", "p:nvGrpSpPr", "p:nvSpPr"):
            nv = el.find(qn(tag))
            if nv is not None:
                nv.find(qn("p:cNvPr")).set("descr", text)
                return

    def notes(self, s, txt):
        if txt:
            s.notes_slide.notes_text_frame.text = txt

    def title(self, s, t, color="dark"):
        self.text(s.shapes, LX, TT, CW, 1.2, [{"t": proper(t), "size": S["title"], "color": color}], "title", fit="title")

    def source(self, s, src, color="muted"):
        if src:
            self.text(s.shapes, LX, 6.47, CW, 0.28, [{"t": "Source: " + src, "size": S["source"], "color": color}], "source")

    def callout(self, s, x, y, w, h, txt, name="takeaway"):
        g = s.shapes.add_group_shape(); g.name = name
        self.accent_card(g.shapes, x, y, w, h, "left", "primary", fill="callout", radius=R["callout"], name="callout:box")
        self.text(g.shapes, x + 0.3, y + 0.08, w - 0.5, h - 0.16, [{"t": txt, "size": S["body"], "color": "dark"}], "takeaway:text", anchor=MSO_ANCHOR.MIDDLE, fit="body")
        return g

    def two_tone(self, t, accent, base, hi):
        i = t.lower().find(accent.lower()) if accent else -1
        if i >= 0:
            a, mid, b = t[:i], t[i:i + len(accent)], t[i + len(accent):]
            return [x for x in ((a, base), (mid, hi), (b, base)) if x[0]]
        return [(t, base)]

    # ---------------- layouts ----------------
    def cover(self):
        m = self.meta
        style = m.get("cover", "white")
        key = "content" if m.get("logo") == "none" else {"white": "cover_white", "primary": "cover_primary", "dark": "cover_dark"}[style]
        s = self.new(key)
        dark = key in DARK
        base, hi = ("white", "card" if key == "cover_primary" else "context") if dark else ("dark", "primary")
        if self.draft:
            self.text(s.shapes, RX - 3.0, 0.18, 3.0, 0.4, [{"t": "Draft: Screenshots Pending" if (self.shots or self.ui_slides or self.missing_images()) else "Draft",
                      "size": S["label"], "bold": True, "color": "white" if dark else "primary", "align": PP_ALIGN.RIGHT}], "draft:mark", align=PP_ALIGN.RIGHT)
        if m.get("cover_align") == "center":
            self.cover_centered(s, m, dark, base, hi)
            return
        self.text(s.shapes, LX, 0.7, 11.6, 2.7, [{"runs": self.two_tone(proper(m.get("title", "")), m.get("title_accent"), base, hi),
                                               "size": S["cover_title"], "font": F["display"], "bold": True}], "title", anchor=MSO_ANCHOR.BOTTOM, fit="cover_title")
        if m.get("subtitle"):
            self.text(s.shapes, LX, 3.5, 11.0, 1.2, [{"t": proper(m["subtitle"]), "size": S["cover_sub"], "color": "white" if dark else "primary"}], "subtitle", fit="cover_sub")
        lines = [x for x in (m.get("presenter"), m.get("date")) if x]
        if lines:
            self.text(s.shapes, 8.2, 5.7, RX - 8.2, 0.75, [{"t": l, "size": S["cover_meta"], "color": "white" if dark else "text", "align": PP_ALIGN.RIGHT} for l in lines], "meta")
        self.notes(s, m.get("notes"))

    def cover_centered(self, s, m, dark, base, hi):
        """Centered cover: title, subtitle, a short accent rule and the presenter/date, all on the slide's center line,
        kept clear of the logo in the bottom-left corner."""
        self.text(s.shapes, LX, 0.9, CW, 2.0, [{"runs": self.two_tone(proper(m.get("title", "")), m.get("title_accent"), base, hi),
                                              "size": S["cover_title"], "font": F["display"], "bold": True}], "title", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="cover_title")
        if m.get("subtitle"):
            self.text(s.shapes, LX, 3.0, CW, 0.6, [{"t": proper(m["subtitle"]), "size": S["cover_sub"], "color": "white" if dark else "primary"}], "subtitle", align=PP_ALIGN.CENTER, fit="cover_sub")
        self.shape(s.shapes, MSO_SHAPE.RECTANGLE, W / 2 - 0.5, 3.85, 1.0, 0.05, fill="secondary" if dark else "primary", name="accent")
        lines = [x for x in (m.get("presenter"), m.get("date")) if x]
        if lines:
            self.text(s.shapes, LX, 4.15, CW, 0.75, [{"t": l, "size": S["cover_meta"], "color": "white" if dark else "text", "align": PP_ALIGN.CENTER} for l in lines], "meta")
        self.notes(s, m.get("notes"))

    def summary(self, d):
        s = self.new("cover_dark")
        px = 4.75
        self.shape(s.shapes, MSO_SHAPE.RECTANGLE, px, 0, W - px, H, fill="white", name="bg:panel")
        self.text(s.shapes, LX, 0.75, px - LX - 0.4, 0.35, [{"t": "Summary", "size": S["label"], "bold": True, "color": "white"}], "label")
        self.text(s.shapes, LX, 1.15, px - LX - 0.4, 2.3, [{"t": proper(d["title"]), "size": S["panel_title"], "color": "white"}], "title", fit="panel_title")
        if self.meta.get("decision"):
            self.text(s.shapes, LX, 3.55, px - LX - 0.4, 0.35, [{"t": "Decision Needed", "size": S["label"], "bold": True, "color": "context"}], "label:decision")
            self.text(s.shapes, LX, 3.95, px - LX - 0.4, 1.4, [{"t": self.meta["decision"], "size": S["body2"], "color": "white"}], "decision", fit="body2")
        pts = d["points"]
        x0, top, bottom = px + 0.65, 1.0, 6.3
        step = (bottom - top) / len(pts)
        tw = RX - x0 - 0.85
        for i, p in enumerate(pts):
            g = s.shapes.add_group_shape(); g.name = "point"
            self.numbered_text(g.shapes, x0, top + i * step, RX - x0, step, i + 1, [{"t": p, "size": S["body"], "color": "dark"}], "body", "body",
                               0.55, "card", "primary", "point:num", S["body2"], gap=0.3)
        self.notes(s, d.get("notes"))

    def section(self, d):
        s = self.new("section")
        self.shape(s.shapes, MSO_SHAPE.RECTANGLE, W / 2 - 0.5, 2.75, 1.0, 0.05, fill="secondary", name="accent")
        self.text(s.shapes, 1.2, 2.95, W - 2.4, 1.6, [{"runs": self.two_tone(proper(d["title"]), d.get("accent"), "white", "card"),
                                                      "size": S["section_title"], "font": F["display"], "bold": True}], "title", align=PP_ALIGN.CENTER, fit="section_title")
        if d.get("subtitle"):
            self.text(s.shapes, 1.2, 4.65, W - 2.4, 0.8, [{"t": proper(d["subtitle"]), "size": S["section_sub"], "color": "white"}], "subtitle", align=PP_ALIGN.CENTER, fit="section_sub")
        self.notes(s, d.get("notes"))

    def band(self, s, top=None, bottom=6.35):
        """Light-tint background band behind the body (a tone change that keeps the white title and footer)."""
        top = BT - 0.15 if top is None else top
        self.shape(s.shapes, MSO_SHAPE.RECTANGLE, 0, top, W, bottom - top, fill="card", name="bg:band")

    def bullets(self, d):
        s = self.new("content")
        if d.get("tint"):
            self.band(s)
        self.title(s, d["title"])
        short = sum(len(p.split()) for p in d["points"]) <= 24
        self.text(s.shapes, LX, BT + 0.15, 8.6, BB - BT - 0.3, [{"t": p, "size": S["subhead"] if short else S["body"], "bullet": True, "after": 26 if short else 18, "color": "text"} for p in d["points"]], "body", fit="body")
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def statement(self, d):
        if d.get("attribution"):
            s = self.new("quote")
            self.text(s.shapes, 1.6, 2.1, 7.7, 2.6, [{"t": d["text"], "size": S["statement"], "font": F["display"], "bold": True, "color": "dark"}], "body", anchor=MSO_ANCHOR.MIDDLE, fit="statement")
            self.text(s.shapes, 1.6, 5.25, 6.1, 0.5, [{"t": d["attribution"], "size": S["body2"], "color": "muted"}], "attribution")
        else:
            s = self.new("content")
            if d.get("tint"):
                self.band(s, 1.25)
            self.text(s.shapes, 1.4, 1.6, W - 2.8, 4.2, [{"t": d["text"], "size": S["statement"], "font": F["display"], "bold": True, "color": "dark"}], "body", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, fit="statement")
        self.notes(s, d.get("notes"))

    def kpi_minimal(self, d):
        """Borderless KPIs: big numbers on white separated by hairline dividers."""
        s = self.new("content")
        self.title(s, d["title"])
        k = d["kpis"]
        gap, h = 0.6, 2.6
        y = 2.35 if (d.get("context") or d.get("takeaway")) else BT + (BB - BT - h) * 0.42
        w = (CW - gap * (len(k) - 1)) / len(k)
        for i, item in enumerate(k):
            x = LX + i * (w + gap)
            alert = item.get("status") == "missed"
            g = s.shapes.add_group_shape(); g.name = "kpi:alert" if alert else "kpi"
            self.text(g.shapes, x, y, w, 1.25, [{"t": item["value"], "size": S["shift"], "font": F["display"], "bold": True, "color": "alert" if alert else "primary"}],
                      "kpi:value", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="kpi")
            self.text(g.shapes, x, y + 1.35, w, 0.6, [{"t": proper(item["label"]), "size": S["body2"], "bold": True, "color": "dark"}], "kpi:label", align=PP_ALIGN.CENTER, fit="body2")
            if item.get("delta"):
                self.text(g.shapes, x, y + 1.95, w, 0.55, [{"t": item["delta"], "size": S["detail"], "color": "text"}], "kpi:delta", align=PP_ALIGN.CENTER, fit="detail")
            if i:
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x - gap / 2), Inches(y + 0.2), Inches(x - gap / 2), Inches(y + h - 0.1))
                ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(0.75); ln.name = "divider"
        if d.get("context"):
            self.text(s.shapes, LX, 5.5, CW, 0.7, [{"t": d["context"], "size": S["body2"], "color": "text"}], "body", fit="body2")
        if d.get("takeaway"):
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, d["takeaway"])
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def shift(self, d):
        """From -> to: one metric before and after, same type scale, a thin arrow and an optional change pill."""
        s = self.new("content")
        self.title(s, d["title"])
        f, t = d["from"], d["to"]
        take = d.get("takeaway")
        cy = 3.55 if take else 3.85
        bw = 4.4
        lx, rx = LX + 0.3, RX - 0.3 - bw
        alert = t.get("status") == "missed"
        if d.get("metric"):
            self.text(s.shapes, LX, max(BT, cy - 1.65), CW, 0.42, [{"t": proper(d["metric"]), "size": S["body2"], "bold": True, "color": "muted"}], "label", align=PP_ALIGN.CENTER, fit="body2")
        for side, item, x in (("from", f, lx), ("to", t, rx)):
            g = s.shapes.add_group_shape(); g.name = "shift:%s%s" % (side, ":alert" if side == "to" and alert else "")
            col = "muted" if side == "from" else ("alert" if alert else "primary")
            self.text(g.shapes, x, cy - 1.15, bw, 1.4, [{"t": item["value"], "size": S["shift"], "font": F["display"], "bold": True, "color": col}],
                      "kpi:value", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="shift")
            self.text(g.shapes, x, cy + 0.35, bw, 0.5, [{"t": proper(item["label"]), "size": S["body2"], "bold": side == "to", "color": "dark" if side == "to" else "muted"}],
                      "kpi:label", align=PP_ALIGN.CENTER, fit="body2")
        ax0, ax1 = lx + bw + 0.35, rx - 0.35
        ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(ax0), Inches(cy - 0.45), Inches(ax1), Inches(cy - 0.45))
        ln.line.color.rgb = rgb("dark"); ln.line.width = Pt(1.5); ln.name = "shift:arrow"
        lnx = ln.line._get_or_add_ln(); lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        if d.get("change"):
            pw = min(ax1 - ax0 - 0.2, 0.32 + 0.16 * len(d["change"]))
            g = s.shapes.add_group_shape(); g.name = "shift:change"
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, (ax0 + ax1) / 2 - pw / 2, cy - 1.15, pw, 0.46, fill="card", name="pill", radius=0.23)
            self.text(g.shapes, (ax0 + ax1) / 2 - pw / 2, cy - 1.15, pw, 0.46, [{"t": d["change"], "size": S["label"], "bold": True, "color": "primary"}], "kpi:delta", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
        if take:
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, take)
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def steps(self, d):
        """Editorial numbered list: numeral | label | detail on full-width rows divided by hairlines."""
        s = self.new("content")
        if d.get("tint"):
            self.band(s)
        self.title(s, d["title"])
        rows = d["steps"]
        top, bottom = BT + 0.1, BB - 0.05
        rh = min(1.45, (bottom - top) / len(rows))
        nw, lw = 0.95, 3.7
        hl = d.get("highlight")
        for i, r in enumerate(rows):
            y = top + i * rh
            key = hl == i
            if i:
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(LX), Inches(y), Inches(RX), Inches(y))
                ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(0.75); ln.name = "step:rule"
            g = s.shapes.add_group_shape(); g.name = "step"
            self.text(g.shapes, LX, y + 0.12, nw, rh - 0.24, [{"t": "%02d" % (i + 1), "size": S["step_num"], "font": F["display"], "bold": True, "color": "primary" if key or hl is None else "muted"}],
                      "step:num", anchor=MSO_ANCHOR.MIDDLE, fit="step_num")
            self.text(g.shapes, LX + nw, y + 0.12, lw, rh - 0.24, [{"t": proper(r["label"]), "size": S["body"], "bold": True, "color": "primary" if key else "dark"}],
                      "diagram:label", anchor=MSO_ANCHOR.MIDDLE, fit="body")
            if r.get("detail"):
                self.text(g.shapes, LX + nw + lw + 0.3, y + 0.12, RX - (LX + nw + lw + 0.3), rh - 0.24, [{"t": r["detail"], "size": S["body2"], "color": "text"}],
                          "diagram:text", anchor=MSO_ANCHOR.MIDDLE, fit="detail")
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    STATUS = {"done": ("Done", "primary", None, "primary"), "in_progress": ("In Progress", "white", "primary", "primary"),
              "open": ("Open", "white", "muted", "muted_text"), "at_risk": ("At Risk", "alert", None, "alert_text")}

    def checklist(self, d):
        """Readiness or status list: a status dot centered on each item's first line, the status in words, owner and date."""
        s = self.new("content")
        self.title(s, d["title"])
        items = d["items"]
        rh = min(0.82, (BB - BT - 0.2) / len(items))
        top = BT + max(0.1, (BB - BT - rh * len(items)) * 0.42)
        dot, mw = 0.32, 4.1
        for i, it in enumerate(items):
            y = top + i * rh
            if i:
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(LX), Inches(y), Inches(RX), Inches(y))
                ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(0.75); ln.name = "check:rule"
            word, fill, ring, col = self.STATUS[it["status"]]
            alert = it["status"] == "at_risk"
            g = s.shapes.add_group_shape(); g.name = "check:alert" if alert else "check"
            ty, th = self.numbered_text(g.shapes, LX + INSET, y, RX - mw - 0.3 - LX, rh, "", [{"t": it["text"], "size": S["body2"], "color": "dark"}], "check:text", "body2",
                                        dot, fill, "white", "check:num", None, gap=0.3)
            m = g.shapes[-1]
            if ring:
                m.line.color.rgb = rgb(ring); m.line.width = Pt(2)
            meta = "  \u00b7  ".join(x for x in (it.get("owner"), it.get("date")) if x)
            self.text(g.shapes, RX - mw, ty, 1.35, th, [{"t": word, "size": S["detail"], "bold": True, "color": col}], "check:status", anchor=MSO_ANCHOR.MIDDLE)
            if meta:
                self.text(g.shapes, RX - mw + 1.4, ty, mw - 1.4, th, [{"t": meta, "size": S["detail"], "color": "text"}], "ask:meta", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT, fit="detail")
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def qa(self, d):
        """Anticipated questions: a short blue rule, the question, then the answer, in an aligned one- or two-column grid."""
        s = self.new("content")
        self.title(s, d["title"])
        pairs = d["pairs"]
        cols = 1 if len(pairs) == 1 else 2
        gap = 0.6
        cw = (CW - gap * (cols - 1)) / cols
        hq = lambda q: FIT.lines(q, S["body2"], F["body"], True, cw - 2 * INSET) * S["body2"] * LH() / 72 + 2 * INSET + 0.02
        ha = lambda a: FIT.lines(a, S["body3"], F["body"], False, cw - 2 * INSET) * S["body3"] * LH() / 72 + 2 * INSET + 0.02
        rows = [pairs[i:i + cols] for i in range(0, len(pairs), cols)]
        rhs = [max(0.18 + hq(p["q"]) + 0.08 + ha(p["a"]) for p in r) for r in rows]
        total = sum(rhs) + 0.45 * (len(rows) - 1)
        y = BT + max(0.15, (BB - BT - total) * 0.42)
        for r, rh in zip(rows, rhs):
            for j, p in enumerate(r):
                x = LX + j * (cw + gap)
                g = s.shapes.add_group_shape(); g.name = "qa"
                self.shape(g.shapes, MSO_SHAPE.RECTANGLE, x + INSET, y, 0.6, 0.05, fill="primary", name="qa:rule")
                self.text(g.shapes, x, y + 0.16, cw, hq(p["q"]), [{"t": p["q"], "size": S["body2"], "bold": True, "color": "dark"}], "qa:q")
                self.text(g.shapes, x, y + 0.16 + hq(p["q"]) + 0.08, cw, ha(p["a"]), [{"t": p["a"], "size": S["body3"], "color": "text"}], "qa:a")
            y += rh + 0.45
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    @staticmethod
    def sibling_size(texts, size, floor_key, width, font, bold):
        """One size for parallel headings, measured in the font the deck uses: the largest from `size` down to its
        floor at which every text fits on one line; failing that, the largest at which none leaves one word alone
        on its last line; failing that, `size` (auto-fit and the lint then take over). A wider font steps down a
        point or two instead of wrapping one card's title."""
        floor = MIN.get(floor_key, size)
        sizes = [s for s in range(int(size), int(floor) - 1, -1)]
        for s in sizes:
            if all(FIT.lines(t, s, font, bold, width) <= 1 for t in texts if t):
                return s
        for s in sizes:
            if all(not (len(w) >= 2 and len(FIT.words_of(w[-1])) == 1) for w in (FIT.wrap(t, s, font, bold, width) for t in texts if t)):
                return s
        return size

    def harmonize(self, slide):
        """Siblings share one type size: each group of same-named text shapes shrinks to its smallest fitted size."""
        groups = {}
        def walk(shapes):
            for sh in shapes:
                if sh.shape_type == 6:
                    walk(sh.shapes)
                elif sh.name in T["sib_names"] and sh.has_text_frame:
                    groups.setdefault(sh.name, []).append(sh)
        walk(slide.shapes)
        for name, shs in groups.items():
            if len(shs) < 2:
                continue
            sizes = [r.font.size for sh in shs for p in sh.text_frame.paragraphs for r in p.runs if r.font.size]
            if not sizes:
                continue
            m = min(sizes)
            for sh in shs:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = m

    def kpi(self, d):
        if d.get("style") == "minimal":
            return self.kpi_minimal(d)
        dark = bool(d.get("dark"))
        s = self.new("dark" if dark else "content")
        self.title(s, d["title"], "white" if dark else "dark")
        k = d["kpis"]
        gap, h = 0.35, 2.95
        y = 2.15 if (d.get("context") or d.get("takeaway")) else BT + (BB - BT - h) * 0.42
        w = (CW - gap * (len(k) - 1)) / len(k)
        for i, item in enumerate(k):
            x = LX + i * (w + gap)
            alert = item.get("status") == "missed"
            g = s.shapes.add_group_shape(); g.name = "kpi:alert" if alert else "kpi"
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill="white" if dark else "card", name="card",
                       radius=R["card"], shadow=dark)
            self.text(g.shapes, x + 0.2, y + 0.35, w - 0.4, 1.0, [{"t": item["value"], "size": S["kpi"], "font": F["display"], "bold": True,
                                                                 "color": "alert" if alert else "primary"}], "kpi:value", align=PP_ALIGN.CENTER, fit="kpi")
            self.text(g.shapes, x + 0.2, y + 1.4, w - 0.4, 0.6, [{"t": proper(item["label"]), "size": S["body2"], "bold": True, "color": "dark"}], "kpi:label", align=PP_ALIGN.CENTER, fit="body2")
            if item.get("delta"):
                self.text(g.shapes, x + 0.25, y + 1.95, w - 0.5, h - 2.1, [{"t": item["delta"], "size": S["detail"], "color": "text"}], "kpi:delta", align=PP_ALIGN.CENTER, fit="detail")
        if d.get("context"):
            self.text(s.shapes, LX, 5.5, CW, 0.7, [{"t": d["context"], "size": S["body2"], "color": "white" if dark else "text"}], "body", fit="body2")
        if d.get("takeaway"):
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, d["takeaway"])
        self.source(s, d.get("source"), "white" if dark else "muted")
        self.notes(s, d.get("notes"))

    def chart(self, d):
        s = self.new("content")
        self.title(s, d["title"])
        c = d["chart"]
        take = d.get("takeaway")
        bottom = 5.2 if take else BB - 0.1
        if c["type"] == "bar" and len(c["series"]) == 1 and len(c["categories"]) <= 8 and not c.get("native"):
            self.pill_bars(s, d, BT + 0.1, bottom)
        else:
            self.native_chart(s, d, BT, bottom - BT)
        if take:
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, take)
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def pill_bars(self, s, d, top, bottom):
        c = d["chart"]
        cats, vals = c["categories"], c["series"][0]["values"]
        hl, al = c.get("highlight", {}), c.get("alert", {})
        g = s.shapes.add_group_shape()
        g.name = "visual:chart:alert" if al else "visual:chart"
        n = len(cats)
        row = min(0.8, (bottom - top) / n)
        th = row * 0.6
        lw = 2.4
        tx, tw = LX + lw + 0.25, CW - lw - 0.25
        vmax = max(vals) or 1
        for i, (cat, v) in enumerate(zip(cats, vals)):
            y = top + i * row + (row - th) / 2
            self.text(g.shapes, LX, y - 0.05, lw, th + 0.1, [{"t": cat, "size": S["body2"], "bold": True, "color": "dark"}], "bar:label", fit="body2",
                      anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, tx, y, tw, th, fill="track", name="bar:track", radius=th / 2)
            col = "alert" if al.get("category") == cat else ("primary" if hl.get("category") == cat or (not hl and i == 0) else "context")
            bw = max(th, tw * v / vmax)
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, tx, y, bw, th, fill=col, name="bar:alert" if col == "alert" else "bar", radius=th / 2)
            label = fmt(v, c.get("number_format"))
            need = 0.11 * len(label) + 0.35
            if bw >= need:
                self.text(g.shapes, tx, y, bw - 0.15, th, [{"t": label, "size": S["label"], "bold": True, "color": "dark" if col == "context" else "white"}],
                          "bar:value", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
            else:
                self.text(g.shapes, tx + bw + 0.08, y, need + 0.2, th, [{"t": label, "size": S["label"], "bold": True, "color": "dark"}], "bar:value", anchor=MSO_ANCHOR.MIDDLE)
        self.alt(g, d.get("alt", ""))

    def native_chart(self, s, d, top, height):
        c = d["chart"]
        kind = c["type"]
        data = CategoryChartData()
        data.categories = c["categories"]
        for ser in c["series"]:
            data.add_series(ser["name"], ser["values"])
        gf = s.shapes.add_chart(CHARTS[kind], Inches(LX), Inches(top), Inches(CW), Inches(height), data)
        gf.name = "visual:chart:alert" if c.get("alert") else "visual:chart"
        self.alt(gf, d.get("alt", ""))
        ch = gf.chart
        ch.has_legend, ch.has_title = False, False
        ch.font.name, ch.font.size = F["body"], Pt(S["label"])
        ch.font.color.rgb = rgb("text")
        va, ca = ch.value_axis, ch.category_axis
        va.has_major_gridlines, va.visible = False, False
        ca.major_tick_mark = XL_TICK_MARK.NONE
        ca.format.line.color.rgb = rgb("card_line")
        ca.tick_labels.font.size = Pt(S["label"])
        if kind in ("bar", "stacked_bar"):
            ca.reverse_order = True
        plot = ch.plots[0]
        f = c.get("number_format", "General")
        hl, al = c.get("highlight", {}), c.get("alert", {})
        if kind == "line":
            vals = [v for ser in c["series"] for v in ser["values"]]
            lo, hi = min(vals), max(vals)
            if lo >= 0 and hi > lo:
                va.minimum_scale = max(0, lo - (hi - lo) * 0.4)
                va.maximum_scale = hi + (hi - lo) * 0.2
            last = len(c["categories"]) - 1
            for ser in plot.series:
                key = ser.name == hl.get("series") or (not hl and ser.index == 0)
                ser.smooth = False
                ser.format.line.color.rgb = rgb("primary" if key else "secondary")
                ser.format.line.width = Pt(2.75 if key else 1.75)
                if key:
                    ser.marker.style = XL_MARKER_STYLE.CIRCLE
                    ser.marker.size = 8
                    ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = rgb("white")
                    ser.marker.format.line.color.rgb = rgb("primary")
                else:
                    ser.marker.style = XL_MARKER_STYLE.NONE
                    ser.format.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                dl = ser.points[last].data_label
                dl.position = XL_LABEL_POSITION.RIGHT
                dl.text_frame.text = "%s %s" % (ser.name, fmt(c["series"][ser.index]["values"][last], f))
                dl.font.size, dl.font.bold = Pt(S["label"]), key
                dl.font.color.rgb = rgb("primary" if key else "muted")
            return
        stacked = kind.startswith("stacked")
        plot.gap_width = 70
        if stacked:
            plot.overlap = 100
        plot.has_data_labels = True
        dls = plot.data_labels
        dls.number_format, dls.number_format_is_linked = f, False
        dls.font.size, dls.font.bold = Pt(S["label"]), True
        dls.font.color.rgb = rgb("white" if stacked else "dark")
        dls.position = XL_LABEL_POSITION.CENTER if stacked else XL_LABEL_POSITION.OUTSIDE_END
        shades = ["dark", "primary", "secondary"]
        for ser in plot.series:
            if stacked:
                base = ("primary" if ser.name == hl["series"] else "context") if hl.get("series") else shades[ser.index % 3]
            else:
                base = "primary" if (ser.name == hl.get("series") or (not hl.get("series") and not hl.get("category") and ser.index == 0)) else "context"
            ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(base)
            for i, cat in enumerate(c["categories"]):
                col = None
                if hl.get("category") == cat and not stacked:
                    col = "primary"
                if al.get("category") == cat and (not al.get("series") or al["series"] == ser.name):
                    col = "alert"
                if col:
                    pt = ser.points[i]
                    pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(col)

    def screenshot(self, d):
        s = self.new("content")
        self.title(s, d["title"])
        calls = d.get("callouts", [])
        take = d.get("takeaway")
        bw, bh = (7.9 if calls else CW), ((TAKE_TOP - 0.2) if take else BB) - BT
        step, kh = (1.05, 1.0) if take else (1.35, 1.2)
        right = d.get("_side") == "right"
        kx = LX if right else LX + bw + 0.45
        kw = (RX - bw - 0.45 - (LX + 0.55)) if right else RX - (LX + bw + 1.0)
        path = os.path.join(self.base, d["image"]) if d.get("image") else ""
        if path and os.path.isfile(path):
            from PIL import Image
            iw, ih = Image.open(path).size
            sc = min(bw / iw, bh / ih)
            w, h = iw * sc, ih * sc
            x, y = (RX - w) if (calls and right) else LX, BT + (bh - h) / 2
            pic = s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
            pic.name = "visual:screenshot"
            pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
            geom = pic._element.spPr.find(qn("a:prstGeom"))
            av = geom.find(qn("a:avLst"))
            if av is None:
                av = geom.makeelement(qn("a:avLst"), {}); geom.append(av)
            av.append(av.makeelement(qn("a:gd"), {"name": "adj", "fmla": "val %d" % int(100000 * R["image"] / min(w, h))}))
            pic.line.color.rgb = rgb("card_line"); pic.line.width = Pt(0.75)
            self.soft_shadow(pic)
            self.alt(pic, d.get("alt", ""))
        else:
            if not self.draft:
                raise SystemExit("ERROR slide %d: screenshot not found: %s (attach it, or build with --draft)" % (self.n, d.get("image")))
            x, y, w, h = (RX - bw) if (calls and right) else LX, BT, bw, bh
            ph = self.shape(s.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill="callout", line="context", name="visual:placeholder", radius=R["card"])
            ph.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            tf = ph.text_frame; tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = "Screenshot needed: " + d.get("alt", d.get("image", ""))
            r.font.name, r.font.size, r.font.color.rgb = F["body"], Pt(S["body2"]), rgb("muted")
            self.alt(ph, "Placeholder for screenshot: " + d.get("alt", ""))
            self.shot(d.get("image", "(no file name)"), d.get("alt", ""))
        for i, co in enumerate(calls, 1):
            self.circle_num(s.shapes, x + co["x"] * w - 0.2, y + co["y"] * h - 0.2, 0.4, i, "primary", "white", line="white", name="callout:marker")
            ly = BT + 0.25 + (i - 1) * step
            g = s.shapes.add_group_shape(); g.name = "callout:key"
            self.numbered_text(g.shapes, kx, ly - 0.05, kw + 0.55, kh, i, [{"t": co["text"], "size": S["body2"], "color": "dark"}], "callout:text", "body2",
                               0.4, "card", "primary", "callout:num", None, gap=0.15, valign="top")
        if take:
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, take)
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def diagram(self, d):
        s = self.new("content")
        self.title(s, d["title"])
        g = d["diagram"]
        take = d.get("takeaway") if g["kind"] != "timeline" else None
        self.bottom = (TAKE_TOP - 0.2) if take else BB
        grp = s.shapes.add_group_shape(); grp.name = "visual:diagram"
        getattr(self, "_dg_" + g["kind"])(grp, g)
        self.alt(grp, d.get("alt", ""))
        if take:
            self.callout(s, LX, TAKE_TOP, CW, TAKE_H, take)
        self.bottom = BB
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    ICON_ROOM = 0.52

    def _card(self, grp, x, y, w, h, label, detail, key=False, fill="white", icon=None, room=False):
        self.shape(grp.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, line="primary" if key else "card_line",
                   line_w=1.5 if key else 0.75, name="diagram:card", radius=R["card"], shadow=fill == "white")
        dy = self.ICON_ROOM if room else 0
        if icon:
            self.icon(grp.shapes, icon, x + w / 2 - 0.19, y + 0.18, 0.38, "primary")
        self.text(grp.shapes, x + 0.15, y + 0.15 + dy, w - 0.3, 0.5, [{"t": proper(label), "size": S["body2"], "bold": True, "color": "primary" if key else "dark"}],
                  "diagram:label", align=PP_ALIGN.CENTER, fit="body2")
        if detail:
            self.text(grp.shapes, x + 0.18, y + 0.68 + dy, w - 0.36, h - 0.8 - dy, [{"t": detail, "size": S["detail"], "color": "text"}], "diagram:text", align=PP_ALIGN.CENTER, fit="detail")

    def _dg_process(self, grp, g, timeline=False):
        nodes, hl = g["nodes"], g.get("highlight")
        n = len(nodes)
        slot = CW / n
        bottom = getattr(self, "bottom", BB)
        lines0 = max(FIT.lines(nd.get("detail", ""), S["detail"], F["body"], False, min(3.0, slot - 0.3) - 0.44) for nd in nodes)
        ch0 = min(2.6, max(1.3, 0.85 + lines0 * S["detail"] * LH() / 72 + 0.2)) + (self.ICON_ROOM if any(nd.get("icon") for nd in nodes) else 0)
        # centered in the band between the title and the bottom margin (marker, gap, card), not at a fixed height
        cy = 4.1 if timeline else max(BT + 0.35, BT + (bottom - BT - (0.4 + ch0)) / 2)
        ln = grp.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(LX), Inches(cy), Inches(RX), Inches(cy))
        ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(2); ln.name = "diagram:line"
        cw = min(3.0, slot - 0.3)
        lines = max(FIT.lines(nd.get("detail", ""), S["detail"], F["body"], False, cw - 0.44) for nd in nodes)
        ic = any(nd.get("icon") for nd in nodes)
        ch = min(2.2 if timeline else 2.6, max(1.3, 0.85 + lines * S["detail"] * LH() / 72 + 0.2)) + (self.ICON_ROOM if ic else 0)
        if not timeline:
            ch = min(ch, bottom - cy - 0.4)
        for i, nd in enumerate(nodes):
            cx = LX + slot * i + slot / 2
            key = hl == i
            if g.get("numbered") and not timeline:
                self.circle_num(grp.shapes, cx - 0.21, cy - 0.21, 0.42, str(i + 1), "primary" if key else "dark", "white", name="diagram:node", size=13)
            elif timeline:
                self.shape(grp.shapes, MSO_SHAPE.OVAL, cx - 0.17, cy - 0.17, 0.34, 0.34, fill="primary" if key else "white", line="primary" if key else "dark",
                           line_w=2.25, name="diagram:node")
            else:  # hollow dot: the line already shows the order (numbers only with "numbered": true)
                self.shape(grp.shapes, MSO_SHAPE.OVAL, cx - 0.13, cy - 0.13, 0.26, 0.26, fill="white", line="primary" if key else "dark",
                           line_w=2.25, name="diagram:node")
            above = timeline and i % 2 == 1
            cyard = cy - 0.4 - ch if above else cy + 0.4
            self._card(grp, cx - cw / 2, cyard, cw, ch, nd["label"], nd.get("detail"), key, icon=nd.get("icon"), room=ic)
            if timeline and nd.get("when"):
                wy = cy + 0.28 if above else cy - 0.62
                self.text(grp.shapes, cx - cw / 2, wy, cw, 0.34, [{"t": proper(nd["when"]), "size": S["label"], "bold": True, "color": "primary"}],
                          "diagram:when", align=PP_ALIGN.CENTER)

    def _dg_funnel(self, grp, g):
        nodes, hl = g["nodes"], g.get("highlight")
        bottom = getattr(self, "bottom", BB)
        top = BT + 0.15
        n = len(nodes)
        row = min(0.95, (bottom - top) / n)
        bh = row * 0.8
        for i, nd in enumerate(nodes):
            w = CW * (0.94 - 0.5 * i / max(1, n - 1))
            x, y = W / 2 - w / 2, top + i * row
            key = hl == i
            self.shape(grp.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, bh, fill="primary" if key else "card", name="diagram:bar", radius=bh / 2)
            fg = "white" if key else "dark"
            self.text(grp.shapes, x + 0.3, y, w - 0.6, bh, [{"runs": [(str(nd["value"]) + "   ", "white" if key else "primary"), (proper(nd["label"]), fg)],
                      "size": S["body2"], "bold": True}], "diagram:label", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, fit="body2")

    def _dg_cycle(self, grp, g):
        import math
        nodes, hl = g["nodes"], g.get("highlight")
        bottom = getattr(self, "bottom", BB)
        n = len(nodes)
        ic = any(nd.get("icon") for nd in nodes)
        cw, ch = 2.9, 1.45 + (self.ICON_ROOM if ic else 0)
        cx, cy = W / 2, (BT + bottom) / 2
        rx, ry = 3.9, max(0.8, (bottom - BT) / 2 - ch / 2 - 0.05)
        cent = []
        for i in range(n):
            a = math.radians(-90 + 360.0 * i / n)
            cent.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        for i in range(n):
            (x0, y0), (x1, y1) = cent[i], cent[(i + 1) % n]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy) or 1
            ux, uy = dx / L, dy / L
            exit_ = min((cw / 2) / abs(ux) if ux else 99, (ch / 2) / abs(uy) if uy else 99)
            a0, a1 = exit_ + 0.12, L - exit_ - 0.14
            if a1 - a0 < 0.25:
                continue
            ln = grp.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x0 + ux * a0), Inches(y0 + uy * a0), Inches(x0 + ux * a1), Inches(y0 + uy * a1))
            ln.line.color.rgb = rgb("primary"); ln.line.width = Pt(2); ln.name = "diagram:arrow"
            lnx = ln.line._get_or_add_ln()
            lnx.append(lnx.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        top_bottom = cy - ry + ch / 2
        dia = min(1.5, 2 * (cy - top_bottom) - 0.25)
        if g.get("center") and dia >= 0.9:
            self.shape(grp.shapes, MSO_SHAPE.OVAL, cx - dia / 2, cy - dia / 2, dia, dia, fill="card", name="diagram:center")
            self.text(grp.shapes, cx - dia / 2 + 0.08, cy - dia / 2 + 0.08, dia - 0.16, dia - 0.16, [{"t": proper(g["center"]), "size": S["body2"], "bold": True, "color": "dark"}],
                      "diagram:label", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, fit="body2")
        for i, nd in enumerate(nodes):
            x, y = cent[i]
            self._card(grp, x - cw / 2, y - ch / 2, cw, ch, nd["label"], nd.get("detail"), hl == i, icon=nd.get("icon"), room=ic)

    def _dg_roadmap(self, grp, g):
        periods, lanes = g["periods"], g["lanes"]
        hl = g.get("highlight") or {}
        bottom = getattr(self, "bottom", BB)
        lw = 2.3
        gx = LX + lw
        colw = (RX - gx) / len(periods)
        hy = BT + 0.05
        for j, p in enumerate(periods):
            self.text(grp.shapes, gx + j * colw, hy, colw, 0.4, [{"t": proper(str(p)), "size": S["label"], "bold": True, "color": "muted"}], "diagram:axis", align=PP_ALIGN.CENTER)
        top = hy + 0.55
        rowh = min(1.25, (bottom - top) / len(lanes))
        for j in range(len(periods) + 1):
            x = gx + j * colw
            ln = grp.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(top - 0.05), Inches(x), Inches(top + rowh * len(lanes)))
            ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(0.75); ln.name = "diagram:grid"
        idx = {str(p): k for k, p in enumerate(periods)}
        pos = lambda v: v if isinstance(v, int) else idx[str(v)]
        for i, lane in enumerate(lanes):
            y = top + i * rowh
            self.text(grp.shapes, LX, y, lw - 0.2, rowh, [{"t": proper(lane["label"]), "size": S["body2"], "bold": True, "color": "dark"}], "diagram:label", anchor=MSO_ANCHOR.MIDDLE, fit="body2")
            bh = min(0.56, rowh * 0.62)
            for k, it in enumerate(lane["items"]):
                a, b = pos(it["start"]), pos(it["end"])
                key = hl.get("lane") == i and hl.get("item", 0) == k
                x0, x1 = gx + a * colw + 0.08, gx + (b + 1) * colw - 0.08
                by = y + (rowh - bh) / 2
                self.shape(grp.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x0, by, x1 - x0, bh, fill="primary" if key else "card", name="diagram:bar", radius=bh / 2)
                self.text(grp.shapes, x0 + 0.12, by, x1 - x0 - 0.24, bh, [{"t": it["label"], "size": S["body3"], "bold": True, "color": "white" if key else "dark"}],
                          "diagram:text", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, fit="detail")

    def _dg_layers(self, grp, g):
        nodes, hl = g["nodes"], g.get("highlight")
        bottom = getattr(self, "bottom", BB)
        n = len(nodes)
        rh = min(0.95, (bottom - BT - 0.1) / n)
        bh = rh - 0.14
        top = BT + max(0.05, (bottom - BT - rh * n) * 0.42)
        lw = 3.4
        for i, nd in enumerate(nodes):
            y = top + i * rh
            key = hl == i
            self.shape(grp.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, LX, y, CW, bh, fill="primary" if key else "card", name="diagram:bar", radius=R["card"])
            self.text(grp.shapes, LX + 0.35, y, lw - 0.35, bh, [{"t": proper(nd["label"]), "size": S["body2"], "bold": True, "color": "white" if key else "dark"}],
                      "diagram:label", anchor=MSO_ANCHOR.MIDDLE, fit="body2")
            if nd.get("detail"):
                self.text(grp.shapes, LX + lw + 0.2, y, CW - lw - 0.55, bh, [{"t": nd["detail"], "size": S["body3"], "color": "white" if key else "text"}],
                          "diagram:text", anchor=MSO_ANCHOR.MIDDLE, fit="detail")

    def _dg_timeline(self, grp, g):
        self._dg_process(grp, g, timeline=True)

    def _dg_matrix(self, grp, g):
        q, hl = g["nodes"], g.get("highlight")
        x0, y0 = LX, BT + 0.4
        gap = 0.2
        qw, qh = (CW - gap) / 2, (getattr(self, "bottom", BB) - y0 - 0.45 - gap) / 2
        for i, nd in enumerate(q):
            cx, cy = i % 2, i // 2
            x, y = x0 + cx * (qw + gap), y0 + cy * (qh + gap)
            key = hl == i
            self.shape(grp.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, qw, qh, fill="primary" if key else "card", name="diagram:quad", radius=R["card"])
            self.text(grp.shapes, x + 0.3, y + 0.25, qw - 0.6, 0.5, [{"t": proper(nd["label"]), "size": S["body"], "bold": True, "color": "white" if key else "dark"}], "diagram:label", fit="body")
            if nd.get("detail"):
                self.text(grp.shapes, x + 0.3, y + 0.8, qw - 0.6, qh - 1.0, [{"t": nd["detail"], "size": S["body3"], "color": "white" if key else "text"}], "diagram:text", fit="detail")
        ax = g.get("axes", {})
        if ax.get("y"):
            self.text(grp.shapes, x0, BT, 5.0, 0.32, [{"t": "\u2191  " + proper("higher " + ax["y"]), "size": S["label"], "bold": True, "color": "muted"}], "diagram:axis")
        if ax.get("x"):
            self.text(grp.shapes, RX - 5.0, y0 + 2 * qh + gap + 0.1, 5.0, 0.32, [{"t": proper("higher " + ax["x"]) + "  \u2192", "size": S["label"], "bold": True, "color": "muted"}],
                      "diagram:axis", align=PP_ALIGN.RIGHT)

    def _dg_comparison(self, grp, g):
        gap = 1.0
        cw = (CW - gap) / 2
        lines = max(sum(FIT.lines(p, S["body2"], F["body"], False, cw - 0.8 - S["body2"] * 1.1 / 72) for p in col["points"]) + 0.2 * (len(col["points"]) - 1)
                    for col in (g["left"], g["right"]))
        need = 1.05 + lines * S["body2"] * LH() / 72 + 0.55
        bot = getattr(self, "bottom", BB)
        h = min(bot - BT - 0.3, max(2.4, need))
        y = BT + 0.1 + max(0, (bot - BT - 0.3 - h) / 2 - 0.15)
        for i, col in enumerate((g["left"], g["right"])):
            x = LX + i * (cw + gap)
            key = i == 1
            self.accent_card(grp.shapes, x, y, cw, h, "top", "primary" if key else "dark", line="card_line", line_w=1.0, radius=R["card"], name="diagram:card")
            self.text(grp.shapes, x + 0.4, y + 0.4, cw - 0.8, 0.5, [{"t": proper(col["label"]), "size": S["subhead"], "bold": True, "color": "dark"}], "diagram:label", fit="body")
            self.text(grp.shapes, x + 0.4, y + 1.1, cw - 0.8, h - 1.35,
                      [{"t": p, "size": S["body2"], "color": "text", "bullet": True, "bullet_color": "primary", "after": 14}
                       for p in col["points"]], "diagram:text", fit="body3")
        self.circle_num(grp.shapes, LX + cw + gap / 2 - 0.3, y + h / 2 - 0.3, 0.6, "vs", "dark", "white", name="diagram:vs", size=14)

    def table(self, d):
        s = self.new("content")
        self.title(s, d["title"])
        t = d["table"]
        cols, rows = t["columns"], t["rows"]
        take = d.get("takeaway")
        rh = min(0.5, ((TAKE_TOP - 0.2) - BT) / (len(rows) + 1)) if take else 0.5
        gf = s.shapes.add_table(len(rows) + 1, len(cols), Inches(LX), Inches(BT), Inches(CW), Inches(rh * (len(rows) + 1)))
        gf.name = "visual:table"
        self.alt(gf, d.get("alt", "Table: " + ", ".join(cols)))
        tbl = gf.table
        sid = tbl._tbl.tblPr.find(qn("a:tableStyleId"))
        if sid is None:
            sid = tbl._tbl.tblPr.makeelement(qn("a:tableStyleId"), {}); tbl._tbl.tblPr.append(sid)
        sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
        hl = t.get("highlight_row")
        for r in range(len(rows) + 1):
            for ci in range(len(cols)):
                cell = tbl.cell(r, ci)
                cell.fill.solid(); cell.fill.fore_color.rgb = rgb("card" if r == 0 else "white")
                cell.margin_left = cell.margin_right = Inches(0.14)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                key = hl is not None and r - 1 == hl
                txt = proper(str(cols[ci])) if r == 0 else str(rows[r - 1][ci])
                tag = STATUS_AT_START.match(txt) if r > 0 and (t.get("tag_column") == ci or t.get("tag_column") is None) else None
                parts = [(tag.group(1), True)] + ([(txt[tag.end(1):], False)] if txt[tag.end(1):] else []) if tag else [(txt, None)]
                for ptxt, is_tag in parts:
                    run = cell.text_frame.paragraphs[0].add_run()
                    run.text = ptxt
                    run.font.name, run.font.size = F["body"], Pt(S["detail"])
                    run.font.bold = r == 0 or key or bool(is_tag)
                    run.font.color.rgb = rgb("dark" if r == 0 else ("primary" if key or is_tag else "text"))
                tcPr = cell._tc.get_or_add_tcPr()
                ln = tcPr.makeelement(qn("a:lnB"), {"w": str(Pt(0.75)), "cmpd": "sng"})
                sf = ln.makeelement(qn("a:solidFill"), {})
                sf.append(sf.makeelement(qn("a:srgbClr"), {"val": C["card_line"]}))
                ln.append(sf); tcPr.insert(0, ln)
        if take:
            self.callout(s, LX, min(TAKE_TOP, BT + rh * (len(rows) + 1) + 0.45), CW, TAKE_H, take)
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def cards(self, d):
        """2-4 parallel idea cards; optional numbers, one highlighted card, optional tint band."""
        s = self.new("content")
        tint = bool(d.get("tint"))
        cs, hl = d["cards"], d.get("highlight")
        gap = 0.35
        w = (CW - gap * (len(cs) - 1)) / len(cs)
        ls = self.sibling_size([proper(c["label"]) for c in cs], S["body"], "body", w - 0.68, F["body"], True)
        lh = max(FIT.lines(proper(c["label"]), ls, F["body"], True, w - 0.68) for c in cs) * ls * LH(F["body"], True) / 72 + 0.12
        dh = max(FIT.lines(c.get("detail", ""), S["body3"], F["body"], False, w - 0.68) for c in cs) * S["body3"] * LH() / 72 + 0.12
        lead = d.get("numbered") or any(c.get("icon") for c in cs)
        h = min(3.8, 0.35 + (0.8 if lead else 0) + lh + (0.15 + dh if any(c.get("detail") for c in cs) else 0) + 0.4)
        y = BT + max(0.35, (BB - BT - h) * 0.42)  # optical center: a touch above the middle of the body zone
        if tint:
            self.band(s, y - 0.45, y + h + 0.45)
        self.title(s, d["title"])
        for i, c in enumerate(cs):
            x = LX + i * (w + gap)
            key = hl == i
            fill = "primary" if key else ("white" if tint else "card")
            fg = "white" if key else "dark"
            g = s.shapes.add_group_shape(); g.name = "cards:card"
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill=fill, name="card", radius=R["card"], shadow=tint and not key)
            ty = y + 0.35
            if d.get("numbered"):
                self.circle_num(g.shapes, x + 0.3 + INSET, ty, 0.55, i + 1, "white" if key else "primary", "primary" if key else "white", name="card:num", size=S["body2"])
                ty += 0.8
            elif c.get("icon"):
                self.icon(g.shapes, c["icon"], x + 0.3 + INSET, ty, 0.5, "white" if key else "primary")
                ty += 0.8
            self.text(g.shapes, x + 0.3, ty, w - 0.6, lh, [{"t": proper(c["label"]), "size": ls, "bold": True, "color": fg}], "diagram:label", fit="body")
            if c.get("detail"):
                self.text(g.shapes, x + 0.3, ty + lh + 0.15, w - 0.6, max(dh, y + h - (ty + lh + 0.15) - 0.3), [{"t": c["detail"], "size": S["body3"], "color": "white" if key else "text"}], "diagram:text", fit="detail")
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def _picture(self, s, path, x, y, bw, bh, alt, align="left"):
        from PIL import Image
        iw, ih = Image.open(path).size
        sc = min(bw / iw, bh / ih)
        w, h = iw * sc, ih * sc
        px = x + (bw - w) if align == "right" else (x + (bw - w) / 2 if align == "center" else x)
        py = y + (bh - h) / 2
        pic = s.shapes.add_picture(path, Inches(px), Inches(py), Inches(w), Inches(h))
        pic.name = "visual:screenshot"
        pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
        geom = pic._element.spPr.find(qn("a:prstGeom"))
        av = geom.find(qn("a:avLst"))
        if av is None:
            av = geom.makeelement(qn("a:avLst"), {}); geom.append(av)
        av.append(av.makeelement(qn("a:gd"), {"name": "adj", "fmla": "val %d" % int(100000 * R["image"] / min(w, h))}))
        pic.line.color.rgb = rgb("card_line"); pic.line.width = Pt(0.75)
        self.soft_shadow(pic)
        self.alt(pic, alt)
        return pic

    def split(self, d):
        """A rounded tint or dark panel with the point beside one visual (a screenshot or one big number). Sides alternate."""
        s = self.new("content")
        self.title(s, d["title"])
        right = d.get("_side") == "right"
        dark = d.get("panel") == "dark"
        pw, gap = 4.9, 0.45
        vw = CW - pw - gap
        px = (RX - pw) if right else LX
        vx = LX if right else LX + pw + gap
        y, h = BT + 0.05, BB - BT - 0.15
        g = s.shapes.add_group_shape(); g.name = "split:panel"
        self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, px, y, pw, h, fill="dark" if dark else "card", name="panel", radius=R["card"])
        self.text(g.shapes, px + 0.45, y + 0.45, pw - 0.9, h - 0.9,
                  [{"t": p, "size": S["body"], "bullet": True, "bullet_color": "secondary" if dark else "primary", "after": 18, "color": "white" if dark else "dark"} for p in d["points"]],
                  "body", anchor=MSO_ANCHOR.MIDDLE, fit="body")
        v = d["visual"]
        if v["kind"] == "number":
            top = y + (h - (2.6 + (0.65 if v.get("delta") else 0))) / 2
            self.text(s.shapes, vx, top, vw, 1.9, [{"t": v["value"], "size": S["hero"], "font": F["display"], "bold": True, "color": "primary"}],
                      "hero:value", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="hero")
            self.text(s.shapes, vx, top + 2.0, vw, 0.6, [{"t": proper(v["label"]), "size": S["subhead"], "bold": True, "color": "dark"}], "label", align=PP_ALIGN.CENTER, fit="body")
            if v.get("delta"):
                self.text(s.shapes, vx, top + 2.65, vw, 0.5, [{"t": v["delta"], "size": S["body2"], "color": "text"}], "body", align=PP_ALIGN.CENTER, fit="body2")
        else:
            path = os.path.join(self.base, v["image"]) if v.get("image") else ""
            if path and os.path.isfile(path):
                self._picture(s, path, vx, y, vw, h, v.get("alt", ""), align="left" if right else "right")
            else:
                if not self.draft:
                    raise SystemExit("ERROR slide %d: screenshot not found: %s (attach it, or build with --draft)" % (self.n, v.get("image")))
                ph = self.shape(s.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, vx, y, vw, h, fill="callout", line="context", name="visual:placeholder", radius=R["card"])
                ph.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                self.alt(ph, "Placeholder for screenshot: " + v.get("alt", ""))
                self.shot(v.get("image", "(no file name)"), v.get("alt", ""))
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def hero(self, d):
        """Dark breather slide: one big number with its label, or one big statement, plus an optional supporting line."""
        s = self.new("hero")
        title = self.two_tone(proper(d["title"]), d.get("accent"), "white", "context")
        if d.get("value"):
            self.text(s.shapes, LX, 0.75, CW, 2.05, [{"t": d["value"], "size": S["hero"], "font": F["display"], "bold": True, "color": "white"}],
                      "hero:value", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="hero")
            self.text(s.shapes, LX, 2.85, CW, 0.55, [{"t": proper(d["label"]), "size": S["subhead"], "bold": True, "color": "white"}], "label", align=PP_ALIGN.CENTER, fit="body")
            self.shape(s.shapes, MSO_SHAPE.RECTANGLE, W / 2 - 0.5, 3.62, 1.0, 0.05, fill="secondary", name="accent")
            self.text(s.shapes, 1.2, 3.85, W - 2.4, 1.45, [{"runs": title, "size": S["hero_title"], "font": F["display"], "bold": True}],
                      "title", align=PP_ALIGN.CENTER, fit="hero_title")
            top = 5.4
        else:
            n_lines = min(3, FIT.lines(proper(d["title"]), S["statement"], F["display"], True, W - 2.4 - 0.08))
            th = n_lines * S["statement"] * LH(F["display"], True) / 72 + 0.1
            ty = 3.55 - th / 2 - (0.4 if d.get("text") else 0)
            if d.get("icon"):
                self.icon(s.shapes, d["icon"], W / 2 - 0.3, ty - 1.15, 0.6, "white")
            self.shape(s.shapes, MSO_SHAPE.RECTANGLE, W / 2 - 0.5, ty - 0.3, 1.0, 0.05, fill="secondary", name="accent")
            self.text(s.shapes, 1.2, ty, W - 2.4, th, [{"runs": title, "size": S["statement"], "font": F["display"], "bold": True}],
                      "title", align=PP_ALIGN.CENTER, fit="statement")
            top = ty + th + 0.3
        if d.get("text"):
            self.text(s.shapes, 1.6, top, W - 3.2, 0.9, [{"t": d["text"], "size": S["body2"], "color": "white"}], "body", align=PP_ALIGN.CENTER, fit="body2")
        self.source(s, d.get("source"), "white")
        self.notes(s, d.get("notes"))

    def contents(self, d):
        """Guide table of contents: numbered entries in one or two aligned columns with hairline rules."""
        s = self.new("content")
        self.title(s, d["title"])
        items = [i if isinstance(i, str) else i["label"] for i in d["items"]]
        cols = 1 if len(items) <= 4 else 2
        gap = 0.9
        colw = (CW - gap) / 2 if cols == 2 else 7.4
        per = -(-len(items) // cols)
        rh = 0.66
        top = BT + max(0.25, (BB - BT - rh * per) * 0.42)
        for i, label in enumerate(items):
            c, r = divmod(i, per)
            x, y = LX + c * (colw + gap), top + r * rh
            g = s.shapes.add_group_shape(); g.name = "contents:item"
            self.text(g.shapes, x, y, 0.75, rh - 0.12, [{"t": "%02d" % (i + 1), "size": S["body"], "bold": True, "color": "primary"}], "step:num", anchor=MSO_ANCHOR.MIDDLE)
            self.text(g.shapes, x + 0.75, y, colw - 0.75, rh - 0.12, [{"t": proper(label), "size": S["body"], "color": "dark"}], "diagram:label", anchor=MSO_ANCHOR.MIDDLE, fit="body")
            ln = g.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y + rh - 0.06), Inches(x + colw), Inches(y + rh - 0.06))
            ln.line.color.rgb = rgb("card_line"); ln.line.width = Pt(0.75); ln.name = "contents:rule"
        self.notes(s, d.get("notes"))

    def _shot(self, s, path_rel, alt, x, y, w, h, align="center"):
        """Place a screenshot (or a draft placeholder) in a box; return its actual (x, y, w, h)."""
        path = os.path.join(self.base, path_rel) if path_rel else ""
        if path and os.path.isfile(path):
            pic = self._picture(s, path, x, y, w, h, alt, align=align)
            return pic.left / 914400.0, pic.top / 914400.0, pic.width / 914400.0, pic.height / 914400.0
        if not self.draft:
            raise SystemExit("ERROR slide %d: screenshot not found: %s (attach it, or build with --draft)" % (self.n, path_rel))
        ph = self.shape(s.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill="callout", line="context", name="visual:placeholder", radius=R["card"])
        ph.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        self.alt(ph, "Placeholder for screenshot: " + (alt or ""))
        self.shot(path_rel or "(no file name)", alt or "")
        return x, y, w, h

    def anatomy(self, d):
        """Dashboard or screen anatomy: one centered screenshot with lettered zone cards on both sides, each joined to the image."""
        s = self.new("content")
        self.title(s, d["title"])
        top = BT + 0.1
        if d.get("intro"):
            self.text(s.shapes, LX, BT - 0.05, CW, 0.62, [{"t": d["intro"], "size": S["body3"], "color": "text"}], "body", fit="detail")
            top = BT + 0.7
        zones = d["zones"]
        nl = -(-len(zones) // 2)
        cols = [zones[:nl], zones[nl:]]
        iw = 5.5
        ix = (W - iw) / 2
        ih = BB - top - 0.05
        px, py, pw, ph = self._shot(s, d.get("image"), d.get("alt", ""), ix, top, iw, ih)
        cw = ix - 0.45 - LX
        letter = 0
        dw = cw - 0.83 - 0.08  # the detail box (x + 0.68 to x + cw - 0.15) less its insets: measure what is drawn

        def zone_h(z):
            dl = FIT.lines(z.get("detail", ""), S["detail"], F["body"], False, dw) if z.get("detail") else 0
            return min(1.6, 0.22 + 0.36 + (0.06 + dl * S["detail"] * LH() / 72 + 2 * INSET if dl else 0) + 0.22)
        col_h = [[zone_h(z) for z in col] for col in cols]
        for i in range(max(len(c) for c in col_h)):  # mirrored zones share a height, so the two columns' rows line up
            row = [c[i] for c in col_h if i < len(c)]
            for c in col_h:
                if i < len(c):
                    c[i] = max(row)
        for side, col in enumerate(cols):
            if not col:
                continue
            gap = 0.25
            heights = col_h[side]
            block = sum(heights) + gap * (len(col) - 1)
            y = py + (ph - block) / 2
            x = LX if side == 0 else RX - cw
            for z, h in zip(col, heights):
                g = s.shapes.add_group_shape(); g.name = "anatomy:zone"
                self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, cw, h, fill="card", name="card", radius=R["card"])
                ch = chr(ord("A") + letter)
                ty, th = self.numbered_text(g.shapes, x + 0.18, y + 0.2, cw - 0.33, 0.4, ch, [{"t": proper(z["label"]), "size": S["body2"], "bold": True, "color": "dark"}],
                                            "diagram:label", "body2", 0.36, "primary", "white", "anatomy:num", None, gap=0.14, bold=True, valign="top")
                if z.get("detail"):
                    dx = x + 0.18 + 0.36 + 0.14
                    self.text(g.shapes, dx, ty + th + 0.04, x + cw - 0.15 - dx, y + h - (ty + th + 0.04) - 0.12, [{"t": z["detail"], "size": S["detail"], "color": "text"}], "diagram:text", fit="detail")
                cy = y + h / 2
                x0, x1 = (x + cw, px) if side == 0 else (px + pw, x)
                ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(min(x0, x1) + 0.02), Inches(cy), Inches(max(x0, x1) - 0.02), Inches(cy))
                ln.line.color.rgb = rgb("primary"); ln.line.width = Pt(1.25); ln.name = "anatomy:link"
                if z.get("x") is not None and z.get("y") is not None:
                    self.circle_num(s.shapes, px + z["x"] * pw - 0.18, py + z["y"] * ph - 0.18, 0.36, ch, "primary", "white", line="white", name="callout:marker")
                y += h + gap
                letter += 1
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def annotated(self, d):
        """A screenshot beside a heading and 2-4 annotated notes (bold lead-in, then the explanation). Sides alternate.
        Type steps down one size (all siblings together) when the notes would not fit the column."""
        s = self.new("content")
        self.title(s, d["title"])
        right = d.get("_side") == "right"
        iw, gap = 5.9, 0.55
        nw = CW - iw - gap
        ix = RX - iw if right else LX
        nx = LX if right else LX + iw + gap
        top, ih = BT + 0.05, BB - BT - 0.1
        self._shot(s, d.get("image"), d.get("alt", ""), ix, top, iw, ih, align="center")
        mark, mg = 0.12, 0.22
        tw = nw - mark - mg
        hgt = lambda t, size, bold, w: FIT.lines(t, size, F["body"], bold, w - 2 * INSET) * size * LH() / 72 + 2 * INSET + 0.02
        for hs, ls, ts, gp in ((S["body"], S["body2"], S["body3"], 0.3), (S["body2"], S["body3"], S["detail"], 0.22)):
            hh = hgt(proper(d["heading"]), hs, True, nw) if d.get("heading") else 0
            ih2 = hgt(d.get("intro", ""), ts, False, nw) if d.get("intro") else 0
            rows = [(hgt(proper(a["lead"]), ls, True, tw), hgt(a["text"], ts, False, tw)) for a in d["annotations"]]
            block = hh + (0.12 if hh else 0) + ih2 + (0.25 if ih2 else 0) + sum(l + 0.04 + t for l, t in rows) + gp * (len(rows) - 1)
            if block <= ih:
                break
        y = top + max(0, (ih - block) * 0.42)
        if hh:
            self.text(s.shapes, nx, y, nw, hh, [{"t": proper(d["heading"]), "size": hs, "bold": True, "color": "primary"}], "diagram:label"); y += hh + 0.12
        if ih2:
            self.text(s.shapes, nx, y, nw, ih2, [{"t": d["intro"], "size": ts, "color": "text"}], "body"); y += ih2 + 0.25
        for a, (lh, th) in zip(d["annotations"], rows):
            g = s.shapes.add_group_shape(); g.name = "note"
            self.text(g.shapes, nx + mark + mg, y, tw, lh, [{"t": proper(a["lead"]), "size": ls, "bold": True, "color": "dark"}], "qa:q")
            self.text(g.shapes, nx + mark + mg, y + lh + 0.04, tw, th, [{"t": a["text"], "size": ts, "color": "text"}], "qa:a")
            cy = first_line_center(y, ls)
            if a.get("icon"):
                self.icon(g.shapes, a["icon"], nx + INSET - 0.06, cy - 0.12, 0.24, "primary", tag="icon:%s:num" % a["icon"])
            else:
                self.shape(g.shapes, MSO_SHAPE.RECTANGLE, nx + INSET, cy - mark / 2, mark, mark, fill="primary", name="note:num")
            y += lh + 0.04 + th + gp
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    KINDS = {"example": ("Example", "primary"), "tip": ("Tip", "secondary"), "note": ("Note", "dark"), "warning": ("Warning", "alert")}

    def callouts(self, d):
        """2-3 typed guidance cards (example, tip, note, warning): white cards, a colored top bar, the type in words."""
        s = self.new("content")
        self.title(s, d["title"])
        cs = d["cards"]
        gap = 0.4
        w = (CW - gap * (len(cs) - 1)) / len(cs)
        iw = w - 0.7 - 2 * INSET
        th = max(FIT.lines(proper(c["title"]), S["body"], F["body"], True, iw) for c in cs) * S["body"] * LH() / 72 + 2 * INSET + 0.02
        bh = max(FIT.lines(c["text"], S["body3"], F["body"], False, iw) for c in cs) * S["body3"] * LH() / 72 + 2 * INSET + 0.02
        kh = S["label"] * LH() / 72 + 2 * INSET + 0.02
        h = 0.08 + 0.35 + kh + 0.08 + th + 0.1 + bh + 0.4
        y = BT + max(0.3, (BB - BT - h) * 0.42)
        for i, c in enumerate(cs):
            x = LX + i * (w + gap)
            word, col = self.KINDS[c["kind"]]
            g = s.shapes.add_group_shape(); g.name = "callout:alert" if c["kind"] == "warning" else "callout:card"
            self.accent_card(g.shapes, x, y, w, h, "top", col, line="card_line", radius=R["card"], shadow=True)
            ty = y + 0.08 + 0.35
            icn = c.get("icon", self.KIND_ICONS[c["kind"]])
            kx = x + 0.35
            if icn:
                isz = 0.3
                self.icon(g.shapes, icn, x + 0.35 + INSET, first_line_center(ty, S["label"]) - isz / 2, isz, "alert" if c["kind"] == "warning" else ("dark" if c["kind"] == "note" else "primary"))
                kx = x + 0.35 + isz + 0.14
            self.text(g.shapes, kx, ty, x + w - 0.35 - kx, kh, [{"t": c.get("label") or word.upper(), "size": S["label"], "bold": True, "color": "primary" if c["kind"] != "note" else "dark"}], "callout:kind")
            ty += kh + 0.08
            self.text(g.shapes, x + 0.35, ty, w - 0.7, th, [{"t": proper(c["title"]), "size": S["body"], "bold": True, "color": "dark"}], "diagram:label")
            ty += th + 0.1
            self.text(g.shapes, x + 0.35, ty, w - 0.7, bh, [{"t": c["text"], "size": S["body3"], "color": "text"}], "diagram:text")
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def article(self, d):
        """Reading slide for guides: an article card (heading and 1-3 paragraphs) beside a light key-takeaways card."""
        s = self.new("content")
        self.title(s, d["title"])
        aw, gap = 7.8, 0.4
        sw = CW - aw - gap
        tw = aw - 0.8
        hh = FIT.lines(proper(d["heading"]), S["body"], F["body"], True, tw - 2 * INSET) * S["body"] * LH() / 72 + 2 * INSET + 0.02
        paras = d["paragraphs"]
        pl = sum(FIT.lines(p, S["body3"], F["body"], False, tw - 2 * INSET) for p in paras)
        ph = pl * S["body3"] * LH() / 72 + 2 * INSET + 0.06 + len(paras) * 10 / 72.0
        items = d.get("takeaways", [])
        stw = sw - 0.75
        sth = S["body2"] * LH() / 72 + 2 * INSET + 0.02
        ihs = [FIT.lines(t, S["detail"], F["body"], False, stw - 2 * INSET) * S["detail"] * LH() / 72 + 2 * INSET + 0.02 for t in items]
        h = min(BB - BT - 0.1, max(0.4 + hh + 0.15 + ph + 0.4, 0.4 + sth + 0.25 + sum(ihs) + 0.22 * max(0, len(ihs) - 1) + 0.4))
        y = BT + max(0.05, (BB - BT - h) * 0.42)
        g = s.shapes.add_group_shape(); g.name = "article"
        self.accent_card(g.shapes, LX, y, aw, h, "top", "dark", line="card_line", radius=R["card"], shadow=True)
        self.text(g.shapes, LX + 0.4, y + 0.4, tw, hh, [{"t": proper(d["heading"]), "size": S["body"], "bold": True, "color": "primary"}], "diagram:label")
        self.text(g.shapes, LX + 0.4, y + 0.4 + hh + 0.15, tw, ph, [{"t": p, "size": S["body3"], "color": "text", "after": 10} for p in paras], "body")
        if items:
            sx = LX + aw + gap
            g2 = s.shapes.add_group_shape(); g2.name = "aside"
            self.shape(g2.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, sx, y, sw, h, fill="card", name="card", radius=R["card"])
            self.text(g2.shapes, sx + 0.35, y + 0.4, sw - 0.7, sth, [{"t": proper(d.get("aside_title", "Key Takeaways")), "size": S["body2"], "bold": True, "color": "dark"}], "label")
            ty = y + 0.4 + sth + 0.25
            for t, ih in zip(items, ihs):
                self.shape(g2.shapes, MSO_SHAPE.RECTANGLE, sx + 0.35, ty + 0.04, 0.05, ih - 0.08, fill="primary", name="aside:bar")
                self.text(g2.shapes, sx + 0.5, ty, stw, ih, [{"t": t, "size": S["detail"], "color": "dark"}], "aside:text")
                ty += ih + 0.22
        self.source(s, d.get("source"))
        self.notes(s, d.get("notes"))

    def contact(self, d):
        """Guide closing on dark: a centered question, one supporting line and 1-3 contact rows (label and value, no icons)."""
        s = self.new("hero")
        title = self.two_tone(proper(d["title"]), d.get("accent"), "white", "context")
        rows = d.get("contacts", [])
        block = 1.1 + (0.75 if d.get("text") else 0) + 0.35 + len(rows) * 0.8
        y = max(1.0, (H - block) / 2 - 0.3)
        self.text(s.shapes, 1.2, y, W - 2.4, 1.1, [{"runs": title, "size": S["closing_title"], "font": F["display"], "bold": True}], "title", anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER, fit="closing_title")
        y += 1.2
        if d.get("text"):
            self.text(s.shapes, 1.6, y, W - 3.2, 0.6, [{"t": d["text"], "size": S["body"], "color": "white"}], "body", align=PP_ALIGN.CENTER, fit="body2")
            y += 0.75
        y += 0.35
        rw = 6.8
        for r in rows:
            g = s.shapes.add_group_shape(); g.name = "contact"
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, (W - rw) / 2, y, rw, 0.64, fill="white", alpha=0.12, name="contact:row", radius=R["callout"])
            icn = r.get("icon", self.CONTACT_ICONS.get(r["label"].strip().lower()))
            lx = (W - rw) / 2 + 0.3
            if icn:
                self.icon(g.shapes, icn, lx, y + 0.32 - 0.14, 0.28, "white")
                lx += 0.42
            self.text(g.shapes, lx, y, (W - rw) / 2 + 2.0 - lx, 0.64, [{"t": proper(r["label"]), "size": S["body2"], "bold": True, "color": "white"}], "contact:label", anchor=MSO_ANCHOR.MIDDLE)
            self.text(g.shapes, (W - rw) / 2 + 2.0, y, rw - 2.3, 0.64, [{"t": r["value"], "size": S["body2"], "color": "white"}], "contact:value", anchor=MSO_ANCHOR.MIDDLE, fit="body2")
            y += 0.8
        self.notes(s, d.get("notes"))

    def _dg_milestones(self, grp, g):
        """Milestones on one horizontal line; cards alternate above and below, each tied to its dot by a short stem."""
        import math
        nodes, hl = g["nodes"], g.get("highlight")
        bottom = getattr(self, "bottom", BB)
        n = len(nodes)
        cy = (BT + bottom) / 2 + 0.05
        sp = CW / n
        cw = min(2.9, 2 * sp - 0.35)
        lines = max(FIT.lines(nd.get("detail", ""), S["detail"], F["body"], False, cw - 0.36 - 0.08) for nd in nodes)
        ic = any(nd.get("icon") for nd in nodes)
        ch = min(cy - BT - 0.45, max(1.2, 0.85 + lines * S["detail"] * LH() / 72 + 0.2) + (self.ICON_ROOM if ic else 0))
        ln = grp.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(LX), Inches(cy), Inches(RX), Inches(cy))
        ln.line.color.rgb = rgb("primary"); ln.line.width = Pt(1.5); ln.name = "diagram:line"
        for i, nd in enumerate(nodes):
            x = LX + sp * (i + 0.5)
            up = i % 2 == 1
            key = hl == i
            stem = grp.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(cy - 0.3 if up else cy + 0.13), Inches(x), Inches(cy - 0.13 if up else cy + 0.3))
            stem.line.color.rgb = rgb("primary"); stem.line.width = Pt(1.25); stem.name = "diagram:stem"
            dot = self.shape(grp.shapes, MSO_SHAPE.OVAL, x - 0.13, cy - 0.13, 0.26, 0.26, fill="primary" if key else "white", line="primary", line_w=2.25, name="diagram:node")
            y = cy - 0.3 - ch if up else cy + 0.3
            self._card(grp, x - cw / 2, y, cw, ch, nd["label"], nd.get("detail"), key, fill="card", icon=nd.get("icon"), room=ic)
            if nd.get("when"):
                wy = cy + 0.2 if up else cy - 0.2 - 0.34
                self.text(grp.shapes, x - 1.0, wy, 2.0, 0.34, [{"t": proper(nd["when"]), "size": S["label"], "bold": True, "color": "primary"}], "diagram:when", align=PP_ALIGN.CENTER)

    def closing(self, d):
        s = self.new("content" if self.meta.get("logo") == "none" else "cover_primary")
        dark = self.meta.get("logo") != "none"
        fg = "white" if dark else "dark"
        self.text(s.shapes, LX, 0.85, CW, 1.4, [{"t": proper(d["title"]), "size": S["closing_title"], "font": F["display"], "bold": True, "color": fg}],
                  "title", anchor=MSO_ANCHOR.BOTTOM, fit="closing_title")
        for i, a in enumerate(d.get("asks", [])):
            y = 2.65 + i * 0.95
            g = s.shapes.add_group_shape(); g.name = "ask"
            self.shape(g.shapes, MSO_SHAPE.ROUNDED_RECTANGLE, LX, y, CW, 0.78, fill="white", alpha=0.12 if dark else None, name="ask:row", radius=R["callout"])
            if not dark:
                g.shapes[-1].fill.fore_color.rgb = rgb("card")
            self.numbered_text(g.shapes, LX + 0.18, y, RX - 3.4 - (LX + 0.18), 0.78, i + 1, [{"t": a["action"], "size": S["body2"], "bold": True, "color": fg}], "body", "body2",
                               0.44, "white" if dark else "primary", "primary" if dark else "white", "ask:num", None, gap=0.18, bold=True)
            tail = "  \u00b7  ".join(x for x in (a.get("owner"), a.get("date")) if x)
            if tail:
                self.text(g.shapes, RX - 3.3, y + 0.1, 3.05, 0.58, [{"t": tail, "size": S["detail"], "color": fg}], "ask:meta", anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT, fit="detail")
        self.notes(s, d.get("notes"))

    def build(self, out):
        iconlib.load_overlay(os.path.join(self.base, "icons.local.json"))
        self.cover()
        dispatch = {"summary": self.summary, "bullets": self.bullets, "section": self.section, "statement": self.statement,
                    "kpi": self.kpi, "chart": self.chart, "screenshot": self.screenshot, "diagram": self.diagram,
                    "table": self.table, "closing": self.closing, "hero": self.hero, "cards": self.cards, "split": self.split,
                    "shift": self.shift, "steps": self.steps, "checklist": self.checklist, "qa": self.qa,
                    "contents": self.contents, "anatomy": self.anatomy, "annotated": self.annotated, "callouts": self.callouts,
                    "article": self.article, "contact": self.contact}
        last_split, last_annot, prev = None, None, None
        for d in self.deck["slides"]:
            if d["layout"] == "split":
                side = d.get("side") or ("right" if last_split == "left" else "left")
                last_split = side
                d = dict(d, _side=side)
            elif d["layout"] == "annotated":
                side = d.get("side") or ("right" if last_annot == "left" else "left")
                last_annot = side
                d = dict(d, _side=side)
            elif d["layout"] == "screenshot":
                walk = prev is not None and prev["layout"] == "screenshot" and d.get("series") and d.get("series") == prev.get("series")
                side = d.get("side") or (("right" if prev.get("_side", "left") == "left" else "left") if walk else "left")
                d = dict(d, _side=side)
            self.cur = d
            self.by_n[self.n + 1] = d
            dispatch[d["layout"]](d)
            prev = d
        if self.deck.get("appendix"):
            self.section({"title": "Appendix"})
            for d in self.deck["appendix"]:
                dispatch[d["layout"]](d)
        for sl in self.prs.slides:
            self.harmonize(sl)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        cp = self.prs.core_properties  # file details come from the deck and brand, never a template's leftovers
        cp.title, cp.subject = str(self.meta.get("title", ""))[:255], str(self.meta.get("subtitle", ""))[:255]
        cp.author = cp.last_modified_by = str(self.meta.get("presenter") or self.brand.org or self.brand.display_name or "")[:255]
        cp.keywords, cp.comments, cp.category = "", "Built by slide-deck", ""  # brand.py never reads its own builds as a theme
        self.prs.save(out)
        note = ""
        if self.draft and (self.shots or self.ui_slides):
            sl = os.path.join(self.base, re.sub(r"(\.deck)?\.json$", "", os.path.basename(self.deck_path or "deck.json")) + ".shotlist.md")
            k = self.write_shotlist(sl)
            note = ", %d screenshot placeholders, shot list: %s (%d captures%s)" % (len(self.shots), sl, k, ", existing list kept" if self.shotlist_kept else "")
        print("BUILT %s: %d slides%s" % (out, self.n, note))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck"); ap.add_argument("--out", required=True); ap.add_argument("--draft", action="store_true")
    ap.add_argument("--brand", help="brand profile (default: meta.brand, then brand.json in the project, then detected)")
    a = ap.parse_args()
    deck = normalize(json.load(open(a.deck, encoding="utf-8")))
    from lint_deck import Lint, use_brand
    brand = use_brand(BR.load(source=a.deck, brand=a.brand))
    print(brand.lines()[0] + "; logo: %s" % ("yes" if brand.logo_png("light") else "none"))
    gate = Lint(a.draft)
    gate.deck_path = os.path.abspath(a.deck)
    gate.brand = brand
    gate.deck(deck, os.path.dirname(os.path.abspath(a.deck)))
    if gate.fails:
        print("NOT BUILT: deck.json failed the design gate; fix these and rebuild.")
        sys.exit(gate.report())
    b = Builder(deck, os.path.dirname(os.path.abspath(a.deck)), a.draft, brand)
    b.deck_path = os.path.abspath(a.deck)
    by_n = {}
    k = 1
    for d in deck.get("slides", []):
        k += 1; by_n[k] = d
    b.ui_slides = [(n, by_n[n].get("title", "")) for n in gate.ui_slides if n in by_n]
    b.build(a.out)


if __name__ == "__main__":
    main()
