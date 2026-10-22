"""Brand-neutral slide master, generated at build time from the project brand (scripts/brand.py). No template file ships.

Seven layouts, named in assets/theme.json "layouts" and colored by "layout_bg": light, primary and dark covers, content,
section, quote and dark. Theme colors and fonts come from the brand, so anyone editing the deck in PowerPoint picks from
the project palette. The project logo sits in the cover corner (on light, or its light-on-dark version on primary and
dark covers) and small in the footer band of content and dark slides; with no logo, nothing is drawn. The footer line
and slide number sit in the footer band below footer_zone_in, which content never enters (FOOTER_ZONE).
"""
import io, re, struct
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

THEME_SLOT = {"white": MSO_THEME_COLOR.BACKGROUND_1, "primary": MSO_THEME_COLOR.ACCENT_1, "dark": MSO_THEME_COLOR.TEXT_2}
COVER_LOGO = (0.68, 5.6, 2.4, 0.9)      # x, y, max w, max h (inches): bottom-left cover corner
SMALL_LOGO = (12.65, 6.9, 1.1, 0.34)    # right edge, top, max w, max h: footer band, right-aligned
FOOTER = (1.1, 7.0, 7.4, 0.22)
NUMBER = (0.68, 7.0, 0.36, 0.22)


def _theme_xml(xml, B):
    c = B.colors
    slots = {"dk1": "000000", "lt1": "FFFFFF", "dk2": c["dark"], "lt2": c["card"], "accent1": c["primary"],
             "accent2": c["secondary"], "accent3": c["alert"], "accent4": c["context"], "accent5": c["muted"],
             "accent6": c["text"], "hlink": c["primary"], "folHlink": c["dark"]}
    for slot, val in slots.items():
        xml = re.sub(r"<a:%s>.*?</a:%s>" % (slot, slot), '<a:%s><a:srgbClr val="%s"/></a:%s>' % (slot, val, slot), xml, flags=re.S)
    name = re.sub(r"[<>&\"]", "", B.display_name or "Project")[:60]
    xml = re.sub(r'<a:clrScheme name="[^"]*"', '<a:clrScheme name="%s"' % name, xml)
    xml = re.sub(r'<a:theme ([^>]*)name="[^"]*"', r'<a:theme \1name="%s"' % name, xml, count=1)
    for tag, font in (("majorFont", B.fonts["display"]), ("minorFont", B.fonts["body"])):
        xml = re.sub(r"(<a:%s>\s*<a:latin typeface=\")[^\"]*(\")" % tag, r"\g<1>%s\g<2>" % font.replace("\\", ""), xml)
    return xml


def _clear(layout):
    tree = layout.shapes._spTree
    for sh in list(layout.shapes):
        tree.remove(sh._element)


def _next_id(layout):
    return max([int(v) for v in layout.shapes._spTree.xpath(".//p:cNvPr/@id")] + [1]) + 1


def _text(layout, x, y, w, h, text, size, color, name, align=PP_ALIGN.LEFT, font=None, field=None):
    """A text box on a layout (python-pptx only adds shapes to slides, so the element is built directly)."""
    from pptx.oxml.shapes.autoshape import CT_Shape
    from pptx.shapes.autoshape import Shape
    sp = CT_Shape.new_textbox_sp(_next_id(layout), name, Inches(x), Inches(y), Inches(w), Inches(h))
    layout.shapes._spTree.insert_element_before(sp, "p:extLst")
    tb = Shape(sp, layout.shapes)
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    if field:
        fld = p._p.makeelement(qn("a:fld"), {"id": "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", "type": field})
        rpr = fld.makeelement(qn("a:rPr"), {"lang": "en-US", "sz": str(int(size * 100))})
        fill = rpr.makeelement(qn("a:solidFill"), {}); clr = fill.makeelement(qn("a:srgbClr"), {"val": color}); fill.append(clr); rpr.append(fill)
        if font:
            rpr.append(rpr.makeelement(qn("a:latin"), {"typeface": font}))
        t = fld.makeelement(qn("a:t"), {}); t.text = "‹#›"
        fld.append(rpr); fld.append(t); p._p.append(fld)
    else:
        r = p.add_run(); r.text = text
        r.font.size = Pt(size); r.font.color.rgb = RGBColor.from_string(color)
        if font:
            r.font.name = font
    return tb


def _png_size(png):
    return struct.unpack(">II", png[16:24])


def _logo(layout, png, box, alt, right=False):
    """Place a logo inside a box, keeping its aspect ratio; left-aligned (or right-aligned to box x) and bottom-aligned."""
    from pptx.oxml.shapes.picture import CT_Picture
    w, h = _png_size(png)
    bx, by, bw, bh = box
    scale = min(bw / w, bh / h)
    lw, lh = w * scale, h * scale
    x = bx - lw if right else bx
    _part, rid = layout.part.get_or_add_image_part(io.BytesIO(png))
    pic = CT_Picture.new_pic(_next_id(layout), "Logo", alt, rid, Inches(x), Inches(by + bh - lh), Inches(lw), Inches(lh))
    layout.shapes._spTree.insert_element_before(pic, "p:extLst")


def build(T, B, logo=True):
    """A Presentation whose layouts match T['layouts'], branded with B. Returns (prs, {key: layout}).
    logo=False (deck meta.logo "none", e.g. a co-branded deck) draws no logo on any layout."""
    prs = Presentation()
    G = T["slide"]
    prs.slide_width, prs.slide_height = Inches(G["width_in"]), Inches(G["height_in"])
    master = prs.slide_masters[0]
    theme = master.part.part_related_by(RT.THEME)
    theme._blob = _theme_xml(theme.blob.decode("utf-8"), B).encode("utf-8")
    sx = G["width_in"] / 10.0
    for sh in master.shapes:  # the default master is 4:3; stretch its placeholders to the wide slide
        sh.left, sh.width = int(sh.left * sx), int(sh.width * sx)
    names, bg = {}, T["layout_bg"]
    for key, (_mi, name) in T["layouts"].items():
        names.setdefault(name, bg[key])
    layouts = list(master.slide_layouts)
    for extra in layouts[len(names):]:
        master.slide_layouts.remove(extra)
    footer = B.footer()
    fonts = B.fonts["body"]
    try:
        light, dark = (B.logo_png("light"), B.logo_png("dark")) if logo else (None, None)
    except Exception:
        light = dark = None
    out = {}
    for layout, (name, tone) in zip(master.slide_layouts, names.items()):
        _clear(layout)
        layout.name = name
        layout._element.cSld.set("name", name)
        fill = layout.background.fill
        fill.solid(); fill.fore_color.theme_color = THEME_SLOT[tone]
        on_dark = tone != "white"
        ink = "FFFFFF" if on_dark else B.colors["muted_text"]
        cover = name.startswith("Cover")
        if footer:
            fx = NUMBER[0] if cover else FOOTER[0]
            _text(layout, fx, FOOTER[1], FOOTER[2], FOOTER[3], footer, 9, ink, "Footer", font=fonts)
        if not cover:
            _text(layout, *NUMBER, "", 9, ink, "Slide Number", font=fonts, field="slidenum")
        png = dark if on_dark else light
        if png:
            if cover:
                _logo(layout, png, COVER_LOGO, B.logo_alt())
            elif name != "Section":
                _logo(layout, png, SMALL_LOGO, B.logo_alt(), right=True)
        out[name] = layout
    return prs, {key: out[name] for key, (_mi, name) in T["layouts"].items()}
