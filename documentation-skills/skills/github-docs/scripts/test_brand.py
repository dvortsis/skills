#!/usr/bin/env python3
"""Self-test for brand.py (the project brand resolver). Builds synthetic projects in a temp folder; no network.

  python3 scripts/test_brand.py
Prints one ok/FAIL line per check and BRAND SELF-TEST: n/m passed; exits 1 on any failure."""
import glob, hashlib, io, json, os, shutil, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brand  # noqa: E402

RESULTS = []


def ok(cond, name):
    RESULTS.append(bool(cond))
    print(("ok   " if cond else "FAIL ") + name)


def project(files):
    root = tempfile.mkdtemp(prefix="brandtest_")
    for rel, body in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb" if isinstance(body, bytes) else "w", **({} if isinstance(body, bytes) else {"encoding": "utf-8"})) as fh:
            fh.write(body)
    return root


def png(color=(20, 110, 60, 255), size=(240, 80), transparent=True):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    im = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    ImageDraw.Draw(im).rectangle([20, 20, size[0] - 20, size[1] - 20], fill=color)
    out = io.BytesIO(); im.save(out, "PNG")
    return out.getvalue()


SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100" viewBox="0 0 300 100"><rect x="10" y="10" width="280" height="80" rx="12" fill="#7B2CBF"/></svg>'


def all_pairs_pass(b):
    return not b.failures()


def main():
    roots = []
    try:
        # 1. Tailwind project with an SVG logo
        r = project({"package.json": json.dumps({"name": "@acme/web-portal", "author": "Acme Labs <hi@acme.test>"}),
                     "tailwind.config.js": "module.exports = { theme: { extend: { colors: { primary: { DEFAULT: '#7B2CBF', 100: '#f3e8ff', 900: '#2A0A4A' }, "
                                           "secondary: '#2EC4B6', warning: '#F59F00' }, fontFamily: { sans: ['Inter', 'sans-serif'], heading: ['\"Poppins\"', 'system-ui'] } } } }",
                     "public/logo.svg": SVG, "public/favicon.png": png() or b"", "LICENSE": "MIT License\n\nCopyright (c) 2025 Acme Labs Inc.\n"})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.colors["primary"] == "7B2CBF", "Tailwind: primary from colors.primary.DEFAULT (%s)" % b.colors["primary"])
        ok(b.colors["dark"] == "2A0A4A", "Tailwind: dark from primary.900 (%s)" % b.colors["dark"])
        ok(b.colors["secondary"] == "2EC4B6", "Tailwind: secondary")
        ok(b.sources.get("alert", "").endswith("warning") and abs(brand.hue(b.colors["alert"]) - brand.hue("F59F00")) < 4
           and brand.contrast(b.colors["alert"], "FFFFFF") >= 3.0, "Tailwind: alert from warning, darkened to 3:1 for big numbers (%s)" % b.colors["alert"])
        ok(b.fonts["body"] == "Inter" and b.fonts["display"] == "Poppins", "Tailwind: fonts body Inter, display Poppins (%s, %s)" % (b.fonts["body"], b.fonts["display"]))
        ok(b.logo and b.logo.endswith("logo.svg"), "logo: public/logo.svg picked over the favicon")
        ok(b.org == "Acme Labs Inc." and b.footer(2026) == "©2026 Acme Labs Inc.", "footer from LICENSE copyright (%r)" % b.footer(2026))
        ok(b.name == "Web Portal", "name from package.json, scope dropped (%r)" % b.name)
        have_svg = brand.raster(os.path.join(r, "public", "logo.svg")) is not None
        if have_svg:
            ok(b.logo_png("light") and b.logo_png("dark"), "SVG logo rasterizes; dark slides get a white knockout")
        else:
            print("skip SVG rasterizing (PyMuPDF not installed): builds report the logo as unreadable and draw none")
        ok(all_pairs_pass(b), "Tailwind brand: every text pair passes")

        # 2. shadcn-style CSS variables with a dark mode that must be ignored
        r = project({"package.json": "{}", "src/app/globals.css":
                     "@layer base { :root { --primary: 161 94% 30%; --primary-foreground: 0 0% 100%; --foreground: 222 47% 11%; "
                     "--accent: 210 40% 96%; --destructive: 0 84% 60%; --font-sans: 'Source Sans 3', sans-serif; } "
                     ".dark { --primary: 0 0% 98%; --foreground: 0 0% 98%; } }"})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.sources.get("primary", "").endswith("--primary") and abs(brand.hue(b.colors["primary"]) - 161) < 4,
           "CSS: --primary from :root (hue kept), .dark ignored (%s)" % b.colors["primary"])
        ok(b.colors["text"] == brand.parse_color("222 47% 11%"), "CSS: text from --foreground")
        ok(b.sources.get("secondary", "").startswith("derived"), "CSS: a near-white --accent is not taken as secondary")
        ok(b.fonts["body"] == "Source Sans 3", "CSS: body font from --font-sans")
        ok(all_pairs_pass(b), "CSS brand: every text pair passes")

        # 3. design tokens (Style Dictionary)
        r = project({"tokens/brand.tokens.json": json.dumps({"color": {"brand": {"primary": {"value": "{color.base.red.600}"}},
                                                                       "base": {"red": {"600": {"value": "#C1121F"}}}}})})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.colors["primary"] == "C1121F", "tokens: aliased {color.base.red.600} resolves (%s)" % b.colors["primary"])
        ok(b.colors["alert"] != "D9480F" or abs(brand.hue("D9480F") - brand.hue("C1121F")) > 25, "tokens: alert stays distinct from a red brand")

        # 4. pastel primary that fails contrast
        r = project({"styles/vars.scss": "$primary: #FFD54F;\n$text: #333;"})
        roots.append(r)
        b = brand.load(project=r)
        ok(all_pairs_pass(b), "pastel: every text pair passes after adjustment")
        ok(any("adjusted primary" in n for n in b.notes), "pastel: the primary change is reported")
        ok(b.colors["secondary"] == "FFD54F", "pastel: the original color is kept as secondary")
        ok(brand.hue(b.colors["primary"]) - brand.hue("FFD54F") < 6, "pastel: hue kept when darkening")

        # 5. empty project: neutral defaults, nothing invented
        r = project({"notes.txt": "nothing here"})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.origin.startswith("neutral defaults"), "empty: neutral defaults")
        ok(b.logo is None and b.logo_png() is None and b.footer() == "", "empty: no logo and no footer")
        ok(all_pairs_pass(b), "defaults: every text pair passes")

        # 6. explicit profile wins and resolves relative paths; detect:true merges
        logo = png((200, 30, 30, 255)) or SVG.encode()
        r = project({"tailwind.config.js": "module.exports={theme:{colors:{primary:'#123456'}}}",
                     "brand/brand.json": json.dumps({"name": "Northwind", "org": "Northwind Traders", "footer": "©{year} {org}. Internal use only.",
                                                     "logo": "mark.png", "colors": {"primary": "#0B7A75"}, "fonts": {"body": "Calibri"}}),
                     "brand/mark.png": logo})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.colors["primary"] == "0B7A75" and b.name == "Northwind", "profile: brand/brand.json overrides detection")
        ok(b.logo and os.path.basename(b.logo) == "mark.png", "profile: logo path relative to the profile")
        ok(b.footer(2027) == "©2027 Northwind Traders. Internal use only.", "profile: footer template")
        ok(b.fonts["display"] == "Calibri", "profile: display follows body when not given")
        merged = project({"tailwind.config.js": "module.exports={theme:{colors:{primary:'#123456', secondary: '#E07A5F'}}}",
                          "brand.json": json.dumps({"detect": True, "name": "Merged"})})
        roots.append(merged)
        b = brand.load(project=merged)
        ok(b.colors["primary"] == "123456" and b.name == "Merged", "profile: detect:true keeps detected colors")

        # 7. deck meta.brand points at a profile; legacy color names accepted
        r = project({"deck.json": json.dumps({"meta": {"brand": "kit/b.json"}}), "kit/b.json": json.dumps({"colors": {"blue": "#005A9C", "navy": "#0F1E3D"}})})
        roots.append(r)
        b = brand.load(source=os.path.join(r, "deck.json"))
        ok(b.colors["primary"] == "005A9C" and b.colors["dark"] == "0F1E3D" and b.colors["blue"] == "005A9C", "meta.brand profile; legacy names map to roles")

        # 8. vendored CSS and test fixtures are ignored; light-on-dark logo variant found
        r = project({"package.json": "{}", "node_modules/bootstrap/dist/css/bootstrap.css": ":root{--bs-primary:#0d6efd}",
                     "tests/fixtures/theme.css": ":root{--primary:#ff00ff}", "assets/brand/logo.png": png((10, 60, 120, 255)) or b"",
                     "assets/brand/logo-white.png": png((255, 255, 255, 255)) or b""})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.sources.get("primary") in (None, "logo's main color"), "vendored and fixture CSS ignored (%s)" % b.sources.get("primary"))
        if png():
            ok(b.logo and b.logo.endswith("logo.png") and b.logo_on_dark and b.logo_on_dark.endswith("logo-white.png"), "logo-white.png is the on-dark variant")
            ok(b.colors["primary"] != brand.DEFAULT_COLORS["primary"], "logo color used as primary when no tokens exist")

        # 9. MUI theme and Office template
        r = project({"src/theme.ts": "export default createTheme({ palette: { primary: { main: '#00695C', dark: '#003D33', contrastText: '#fff' }, "
                                     "text: { primary: '#212121' }, warning: { main: '#ED6C02' } }, typography: { fontFamily: '\"Roboto\", sans-serif' } })"})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.colors["primary"] == "00695C" and b.colors["dark"] == "003D33" and b.colors["text"] == "212121", "MUI: palette.primary.main/dark, text.primary")
        ok(b.fonts["body"] == "Roboto", "MUI: typography.fontFamily")

        # 10. an Office template is read; our own builds and installed skills are not
        def office(core, accent):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("docProps/core.xml", '<cp:coreProperties xmlns:cp="x"><cp:comments>%s</cp:comments></cp:coreProperties>' % core)
                z.writestr("ppt/theme/theme1.xml", '<a:theme><a:accent1><a:srgbClr val="%s"/></a:accent1><a:majorFont><a:latin typeface="Georgia"/></a:majorFont></a:theme>' % accent)
            return buf.getvalue()
        r = project({"package.json": "{}", "brand/Company-Template.potx": office("", "8E244D"),
                     "out2/Brand_Review.pptx": office("Built by slide-deck", "1F497D"),
                     "tools/skills/slide-deck/SKILL.md": "---\nname: x\n---", "tools/skills/slide-deck/assets/theme.json": json.dumps({"colors": {"primary": "#00FF00"}})})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.colors["primary"] == "8E244D" and b.fonts["display"] == "Georgia", "Office template: accent1 and major font read (%s)" % b.colors["primary"])
        r = project({"package.json": "{}", "Brand_Review.pptx": office("Built by slide-deck", "1F497D"),
                     "skills/deck/SKILL.md": "x", "skills/deck/assets/theme.json": json.dumps({"colors": {"primary": "#00AA00"}})})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.origin.startswith("neutral"), "own builds ('Built by') and installed skill folders are never read as the brand (%s)" % b.origin)
        b = brand.Brand({"org": "Northwind Ltd.", "footer": "©{year} {org}."}, r, "x")
        ok(b.footer(2027) == "©2027 Northwind Ltd.", "footer template doesn't double the period after 'Ltd.' (%r)" % b.footer(2027))

        # 11. fonts: the project's own first, the bundled fallback only when it names none
        b = brand.Brand({}, r, "x")
        ok(b.fonts["body"] == brand.FALLBACK_FONTS["body"] and b.sources["font_body"].startswith("fallback"),
           "fonts: a project that names none gets the fallback set, marked as fallback (%s)" % b.fonts)
        if brand.bundled_dir():
            ok(b.font_status() == {"body": "bundled", "display": "bundled", "mono": "bundled"} and b.font_path("body", bold=True).endswith("-Bold.ttf"),
               "fonts: the bundled fallback decodes and resolves by style (%s)" % b.font_status())
            m = b.metrics("body")
            ok(1.0 < m["line"] < 1.5 and 0.4 < m["first"] < 0.8 and m["source"].endswith(".ttf"), "fonts: line height and first-line center come from the font file (%s)" % m)
        else:
            print("skip bundled fonts (this skill ships none; it doesn't render)")
        r = project({"package.json": json.dumps({"name": "x", "dependencies": {"@fontsource/source-sans-3": "5.0.0", "@fontsource/fira-code": "5.0.0", "@mui/material": "6.0.0"}})})
        roots.append(r)
        b = brand.load(project=r)
        ok(b.fonts["body"] == "Source Sans 3" and b.fonts["mono"] == "Fira Code", "fonts: @fontsource packages name the project's fonts (%s, %s)" % (b.fonts["body"], b.fonts["mono"]))
        r = project({"package.json": json.dumps({"name": "x", "dependencies": {"@mui/material": "6.0.0"}})})
        roots.append(r)
        ok(brand.load(project=r).fonts["body"] == "Roboto", "fonts: the UI framework's default (Material UI: Roboto) when nothing else names one")
        src = brand.find_font("Inter") if brand.bundled_dir() else None
        if src:
            with open(src, "rb") as fh:
                data = fh.read()
            r = project({"package.json": "{}", "assets/fonts/Inter-Regular.ttf": data})
            roots.append(r)
            b = brand.load(project=r)
            ok(b.fonts["body"] == "Inter" and b.sources["font_body"].startswith("font file") and b.font_status()["body"] == "project file",
               "fonts: a font file the project ships names its font and is the file used (%s, %s)" % (b.sources.get("font_body"), b.font_status()))
        ok(brand.font_metrics("no-such-file.ttf")["source"] == "typical", "fonts: an unreadable file gives typical metrics, never a crash")

        # 12. copies match
        here = os.path.dirname(HERE)
        copies = sorted(glob.glob(os.path.join(os.path.dirname(here), "*", "scripts", "brand.py")))
        digests = set()
        for p in copies:
            with open(p, "rb") as fh:
                digests.add(hashlib.sha256(fh.read()).hexdigest())
        ok(len(digests) == 1, "brand.py copies in sibling skills are identical (%d found)" % len(copies))
        ok(brand.check_profile(os.path.join(roots[5], "brand", "brand.json")) == [], "check: a valid profile passes BRAND_SCHEMA")
        bad = project({"brand.json": json.dumps({"colors": {"purple": "#fff", "primary": "nope"}, "logo": "missing.png", "colour": 1})})
        roots.append(bad)
        ok(len(brand.check_profile(os.path.join(bad, "brand.json"))) == 4, "check: unknown role, bad value, missing logo and unknown key fail")
    finally:
        for r in roots:
            shutil.rmtree(r, ignore_errors=True)
    n = sum(RESULTS)
    print("BRAND SELF-TEST: %d/%d passed" % (n, len(RESULTS)))
    return 0 if n == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
