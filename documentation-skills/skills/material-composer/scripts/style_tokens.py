#!/usr/bin/env python3
"""Style tokens for every composed material: the project brand (scripts/brand.py) over the shipped non-color tokens.

  python3 style_tokens.py show [--source F] [--brand P]            print the colors, fonts, logo and footer a build of F uses
  python3 style_tokens.py check [--doc-theme P] [--deck-theme P]   STYLE_DRIFT: FAIL when the shipped fallback colors
                                                                    differ from brand.py's neutral defaults or from a
                                                                    sibling theme's fallback values (by role)
  python3 style_tokens.py build                                    rewrite the fallback colors in
                                                                    assets/style_tokens.json from brand.py's neutral defaults
Fonts are never named here: they come from the project, else brand.py's bundled fallback (brand.FALLBACK_FONTS).
Builds call tokens(source=..., brand=...): colors, fonts, logo and footer come from the project brand; sizes come from
assets/style_tokens.json. Sibling themes are looked up next to this skill only (../document-builder/assets/doc_theme.json,
../slide-deck/assets/theme.json); a sibling that is not installed prints UNVERIFIED for that sibling, never FAIL."""
import argparse, copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import brand as BR  # shared copy, read-only

OUT = os.path.join(SKILL, "assets", "style_tokens.json")
SIBLINGS = {"document": ("document-builder", "assets", "doc_theme.json"), "deck": ("slide-deck", "assets", "theme.json")}


def shipped(path=OUT):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def neutral():
    """brand.py's neutral defaults, resolved without looking at any project (what a build uses when nothing is found)."""
    return BR.Brand({}, SKILL, "neutral defaults")


def tokens(source=None, brand=None, project=None, b=None):
    """Shipped sizes plus the project brand: colors (roles and legacy aliases), font families, the Brand itself (logo,
    footer, font files and metrics: b.measure_path(), b.metrics())."""
    t = copy.deepcopy(shipped())
    b = b or BR.load(source=source, brand=brand, project=project)
    t["colors"] = dict(b.colors)
    t["fonts"] = dict(b.fonts)
    t["brand"] = b
    return t


def sibling(kind):
    p = os.path.join(os.path.dirname(SKILL), *SIBLINGS[kind])
    return p if os.path.isfile(p) else None


def role_colors(theme):
    """A theme's colors keyed by role (legacy keys such as navy or blue map to their role)."""
    out = {}
    for k, v in (theme.get("colors") or {}).items():
        role = BR.LEGACY.get(k, k)
        h = BR.hex6(v)
        if role in BR.ROLES and h and (k == role or role not in out):
            out[role] = h
    return out


# check: STYLE_DRIFT FAIL
def drift(tok, themes):
    """FAIL lines: shipped fallback vs brand.py neutral defaults, then vs each sibling theme on the roles it defines."""
    bad = []
    fc = {k: str(v).upper() for k, v in (tok.get("fallback_colors") or {}).items()}
    n = neutral()
    for role in BR.ROLES:
        if fc.get(role) != n.colors[role]:
            bad.append("fallback %s: tokens %s, brand.py neutral %s (run style_tokens.py build)" % (role, fc.get(role), n.colors[role]))
    for kind, theme in themes:
        tc = role_colors(theme)
        for role in sorted(set(tc) & set(fc)):
            if tc[role] != fc[role]:
                bad.append("%s: %s %s, fallback %s" % (role, kind, tc[role], fc[role]))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "check", "show"])
    ap.add_argument("--doc-theme"); ap.add_argument("--deck-theme"); ap.add_argument("--out", default=OUT)
    ap.add_argument("--source"); ap.add_argument("--brand"); ap.add_argument("--project")
    a = ap.parse_args()
    if a.cmd == "show":
        t = tokens(a.source, a.brand, a.project)
        print("\n".join(t["brand"].lines()))
        return 1 if t["brand"].failures() else 0
    tok = shipped(a.out if os.path.isfile(a.out) else OUT)
    if a.cmd == "build":
        n = neutral()
        tok["fallback_colors"] = {k: n.colors[k] for k in BR.ROLES}
        tok.pop("fallback_fonts", None)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(tok, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("wrote " + a.out)
        return 0
    themes = []
    for kind, given in (("document", a.doc_theme), ("deck", a.deck_theme)):
        p = given or sibling(kind)
        if not p:
            print("UNVERIFIED STYLE_DRIFT: %s theme not found (%s not installed next to this skill)" % (kind, SIBLINGS[kind][0]))
            continue
        with open(p, encoding="utf-8") as f:
            themes.append((kind, json.load(f)))
    bad = drift(tok, themes)
    for b in bad:
        print("FAIL [STYLE_DRIFT] " + b)
    print("STYLE_DRIFT: %d failed (fallback vs brand.py neutral defaults%s)" % (len(bad), "".join(", %s theme" % k for k, _ in themes)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
