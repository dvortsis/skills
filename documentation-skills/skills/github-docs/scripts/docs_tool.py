#!/usr/bin/env python3
"""Scaffold and maintain a textbook-style guide in GitHub Markdown (references/structure.md).

  python3 scripts/docs_tool.py new docs --title "Beacon setup guide" --app Beacon \
      --chapters "Before you start;Install Beacon;Set up Beacon;Keep Beacon safe;Everyday use;Troubleshooting" [--project DIR]
  python3 scripts/docs_tool.py sync docs [--check]
  python3 scripts/docs_tool.py figure docs/images/unraid-template-illustration.svg --title "Beacon container template" \
      --source "unraid/beacon.xml:11-17" --field "Web UI port=8484|Host port (TCP)" [--action "Apply"] [--project DIR]

new writes the home page, one page per chapter, Appendix A (answers), Appendix B (settings reference), glossary,
revisions, index and images/SHOTLIST.md from assets/templates, with the project logo on the home page when the brand
has one (scripts/brand.py). It refuses to overwrite existing files. Every page it writes holds WRITE: markers that the
lint fails (PLACEHOLDER) until they are replaced with real content.

sync rewrites only the generated parts: chapter and appendix numbers in headings (Chapter N: / N.M / Appendix X:)
and figure captions (*Figure N.M: ...*) from the file order, every link to a renumbered heading, the contents on the
home page, the navigation footer on every page and index.md from <!-- index: term; term --> markers. --check changes
nothing and exits 1 when sync would change a file (NAV, NUMBERING, INDEX are then stale).

figure writes a source-gated, stamped SVG screen illustration (*-illustration.svg) from discovered project labels
(--source and --field "Label=Value|Note"), styled in the project's brand colors and stamped
"Illustration, not a live screenshot" so readers never mistake it for a live capture while screenshots are pending.
"""
import argparse, datetime, html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mdlib as M  # noqa: E402

TEMPLATES = os.path.join(HERE, "..", "assets", "templates")
NAV = re.compile(r"<!-- nav:start -->.*?<!-- nav:end -->", re.S)
CONTENTS = re.compile(r"<!-- contents:start -->.*?<!-- contents:end -->", re.S)
INDEX_BLOCK = re.compile(r"<!-- index:start -->.*?<!-- index:end -->", re.S)
MARKER = re.compile(r"<!--\s*index:\s*(?!start\s*-->|end\s*-->)(.+?)\s*-->")
FIG_CAP = re.compile(r"^(\s*\*Figure)(?:\s+[A-Z0-9]+(?:\.\d+)?)?:\s*(.+?\*\s*)$")


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return re.sub(r"-+", "-", s)[:40].strip("-") or "chapter"


def template(name, **kw):
    t = M.read_file(os.path.join(TEMPLATES, name))
    for k, v in kw.items():
        t = t.replace("{{%s}}" % k, v)
    return t


def cmd_new(a):
    docs = os.path.abspath(a.docs)
    os.makedirs(os.path.join(docs, "images"), exist_ok=True)
    chapters = [c.strip() for c in a.chapters.split(";") if c.strip()]
    if len(chapters) < 2:
        sys.exit("STOPPED: give at least two chapters (--chapters \"A;B\")")
    files = {}
    logo = ""
    try:
        import brand as BR
        b = BR.load(project=a.project or os.path.dirname(docs))
        if b.logo:
            relp = os.path.relpath(b.logo, docs).replace(os.sep, "/")
            logo = '<p align="center"><img src="%s" alt="%s" width="160"></p>\n\n' % (relp, b.logo_alt())
    except Exception:
        pass
    today = datetime.date.today().isoformat()
    rows = "\n".join("| WRITE: a task from %s | [Chapter %d](%02d-%s.md) |" % (c.lower(), n, n, slugify(c)) for n, c in enumerate(chapters, 1))
    files["README.md"] = template("home.md", TITLE=a.title, APP=a.app, LOGO=logo, TASKS=rows, DATE=today)
    for n, c in enumerate(chapters, 1):
        name = "%02d-%s.md" % (n, slugify(c))
        trouble = c.lower().startswith("troubleshoot")
        files[name] = template("troubleshooting.md" if trouble else "chapter.md", N=str(n), TITLE=c, APP=a.app)
    files["appendix-a-answers.md"] = template("answers.md", APP=a.app)
    files["appendix-b-settings-reference.md"] = template("settings-reference.md", APP=a.app)
    files["glossary.md"] = template("glossary.md", APP=a.app)
    files["revisions.md"] = template("revisions.md", APP=a.app, DATE=today)
    files["index.md"] = template("index.md", APP=a.app)
    shot = os.path.join("images", "SHOTLIST.md")
    clash = [f for f in list(files) + [shot] if os.path.exists(os.path.join(docs, f))]
    if clash:
        sys.exit("STOPPED: these files already exist and new never overwrites: %s" % ", ".join(clash))
    for f, body in files.items():
        M.write_file(os.path.join(docs, f), body)
    M.write_file(os.path.join(docs, shot), template("shotlist.md", APP=a.app))
    print("NEW: %d pages in %s (%d chapters) + images/SHOTLIST.md. Replace every WRITE: marker, then run sync and lint." % (len(files), docs, len(chapters)))
    sync(docs, check=False)
    return 0


def sync(docs, check=False):
    order, pages, stale, stats = plan(docs)
    if check:
        print("SYNC CHECK: %s" % ("up to date" if not stale else "stale: " + ", ".join(stale)))
        return 1 if stale else 0
    for n in stale:
        M.write_file(pages[n].path, pages[n].text)
    print("SYNC: %d pages, %d updated, %d headings renumbered, %d links fixed, %d index entries" % ((len(order), len(stale)) + stats))
    return 0


def plan(docs):
    """What sync would write: (page order, {name: Page}, names of pages that would change, (renumbered, links, index))."""
    order, chapters, appx = M.guide_pages(docs)
    pages = {n: M.Page(os.path.join(docs, n)) for n in order}
    texts = {n: p.text for n, p in pages.items()}
    remap = {}   # file -> {old anchor: new anchor}
    changed_headings = 0
    # 1. numbers in headings
    for n in order:
        p = pages[n]
        lines = p.lines[:]
        num = None
        if n in chapters:
            num = str(chapters.index(n) + 1)
        letter = re.match(r"appendix-([a-z])-", n)
        sub = 0
        old_anchors = dict(p.anchors)
        for i, lvl, t in p.headings:
            bare = M.NUM_PREFIX.sub("", t).strip()
            new = t
            if lvl == 1 and num:
                new = "Chapter %s: %s" % (num, bare)
            elif lvl == 1 and letter:
                new = "Appendix %s: %s" % (letter.group(1).upper(), bare)
            elif lvl == 2 and num:
                sub += 1; new = "%s.%d %s" % (num, sub, bare)
            if new != t:
                lines[i] = "#" * lvl + " " + new; changed_headings += 1
        fig_prefix = num or (letter.group(1).upper() if letter else None)
        if fig_prefix:
            fig_idx = 0
            for i, l in enumerate(lines):
                if i in p.code or p.in_details(i):
                    continue
                m = FIG_CAP.match(l)
                if m:
                    fig_idx += 1
                    new_cap = "%s %s.%d: %s" % (m.group(1), fig_prefix, fig_idx, m.group(2))
                    if new_cap != l:
                        lines[i] = new_cap; changed_headings += 1
        newp = M.Page(p.path, "\n".join(lines))
        # map old anchors to new by heading position
        pos_old = {v: k for k, v in old_anchors.items()}
        pos_new = {v: k for k, v in newp.anchors.items()}
        remap[n] = {pos_old[i]: pos_new[i] for i in pos_old if i in pos_new and pos_old[i] != pos_new[i]}
        pages[n] = newp
    # 2. links to renumbered headings
    links_fixed = 0
    for n in order:
        p = pages[n]

        def fix(m):
            nonlocal links_fixed
            text, target = m.group(1), m.group(2)
            parts = M.split_link(target)
            if not parts:
                return m.group(0)
            f, anc = parts
            dest = os.path.basename(f) if f else n
            new = remap.get(dest, {}).get(anc)
            if anc and new:
                links_fixed += 1
                return "[%s](%s#%s)" % (text, f, new)
            return m.group(0)
        body = "\n".join(M.LINK.sub(fix, l) if i not in p.code else l for i, l in enumerate(p.lines))
        pages[n] = M.Page(p.path, body)
    # 3. contents on the home page
    if "README.md" in pages:
        items = []
        for n in order[1:]:
            p = pages[n]
            h1 = next((h for h in p.headings if h[1] == 1), None)
            items.append("- [%s](%s)" % (M.plain(h1[2]) if h1 else n, n))
            if n in chapters:
                for i, lvl, t in p.headings:
                    if lvl == 2:
                        items.append("  - [%s](%s#%s)" % (M.plain(t), n, next(k for k, v in p.anchors.items() if v == i)))
        block = "<!-- contents:start -->\n" + "\n".join(items) + "\n<!-- contents:end -->"
        home = pages["README.md"].text
        home = CONTENTS.sub(lambda _: block, home) if CONTENTS.search(home) else home
        pages["README.md"] = M.Page(pages["README.md"].path, home)
    # 4. index
    entries = []
    for n in order:
        if n == "index.md":
            continue
        p = pages[n]
        for i, l in p.text_lines():
            for m in MARKER.finditer(l):
                h = p.section_of(i)
                if not h:
                    continue
                anc = next(k for k, v in p.anchors.items() if v == h[0])
                for term in [t.strip() for t in m.group(1).split(";") if t.strip()]:
                    entries.append((term, n, anc, M.plain(h[2])))
    if "index.md" in pages:
        out, letter = [], None
        for term, n, anc, where in sorted(set(entries), key=lambda e: (e[0].lower(), e[1], e[2])):
            first = term[0].upper() if term[0].isalpha() else "#"
            if first != letter:
                out += ["", "## %s" % first, ""]; letter = first
            out.append("- [%s](%s#%s) (%s)" % (term, n, anc, where))
        block = "<!-- index:start -->" + "\n".join(out) + "\n\n<!-- index:end -->"
        idx = pages["index.md"].text
        idx = INDEX_BLOCK.sub(lambda _: block, idx) if INDEX_BLOCK.search(idx) else idx.rstrip("\n") + "\n\n" + block + "\n"
        pages["index.md"] = M.Page(pages["index.md"].path, idx)
    # 5. navigation footer
    for k, n in enumerate(order):
        p = pages[n]
        parts = []
        if k > 0:
            parts.append("[← %s](%s)" % (M.plain(title_or(pages[order[k - 1]], order[k - 1])), order[k - 1]))
        if n != "README.md":
            parts.append("[Contents](README.md#contents)")
        if k + 1 < len(order):
            parts.append("[%s →](%s)" % (M.plain(title_or(pages[order[k + 1]], order[k + 1])), order[k + 1]))
        block = "<!-- nav:start -->\n---\n\n" + " · ".join(parts) + "\n<!-- nav:end -->"
        t = p.text
        t = NAV.sub(lambda _: block, t) if NAV.search(t) else t.rstrip("\n") + "\n\n" + block + "\n"
        pages[n] = M.Page(p.path, t)
    stale = [n for n in order if pages[n].text != texts[n]]
    return order, pages, stale, (changed_headings, links_fixed, len(entries))


def title_or(page, name):
    h1 = next((h for h in page.headings if h[1] == 1), None)
    return h1[2] if h1 else name


def cmd_figure(a):
    """Build a source-gated, stamped SVG screen illustration (*-illustration.svg) from discovered project labels."""
    out_path = os.path.abspath(a.out)
    if not out_path.lower().endswith("-illustration.svg"):
        sys.exit("STOPPED: figure output file must end with '-illustration.svg' (got %s)" % os.path.basename(out_path))
    if not a.source.strip():
        sys.exit("STOPPED: --source <file:line> is required so every illustration traces to a project file")
    fields = []
    for raw in a.field or []:
        if "=" not in raw:
            sys.exit("STOPPED: --field takes 'Label=Value' or 'Label=Value|Note' (got %r)" % raw)
        lbl, rest = raw.split("=", 1)
        val, _, note = rest.partition("|")
        fields.append((lbl.strip(), val.strip(), note.strip()))
    if not fields:
        sys.exit("STOPPED: give at least one --field 'Label=Value|Note'")
    pal = {"dark": "1B365D", "primary": "0B7A75", "text": "1F2937", "muted_text": "4B5563", "card": "F8FAFC", "card_line": "CBD5E1"}
    fnt = {"body": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", "mono": "'JetBrains Mono', Consolas, monospace"}
    try:
        import brand as BR
        proj = a.project or os.path.dirname(os.path.dirname(os.path.dirname(out_path)))
        b = BR.load(project=proj)
        for k in pal:
            if b.colors.get(k):
                pal[k] = b.colors[k]
        if b.fonts.get("body"):
            fnt["body"] = "'%s', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" % b.fonts["body"]
        if b.fonts.get("mono"):
            fnt["mono"] = "'%s', Consolas, monospace" % b.fonts["mono"]
    except Exception:
        pass
    w = 720
    row_h = 54
    foot_h = 52 if a.action else 36
    h = 56 + len(fields) * row_h + foot_h
    esc = lambda s: html.escape(str(s), quote=True)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s — Illustration, not a live screenshot">' % (w, h, w, h, esc(a.title)),
        '  <title>%s (Illustration, not a live screenshot)</title>' % esc(a.title),
        '  <rect x="1" y="1" width="%d" height="%d" rx="8" fill="#FFFFFF" stroke="#%s" stroke-width="1.5"/>' % (w - 2, h - 2, pal["card_line"]),
        '  <path d="M1 9 Q1 1 9 1 L%d 1 Q%d 1 %d 9 L%d 46 L1 46 Z" fill="#%s"/>' % (w - 9, w - 1, w - 1, w - 1, pal["dark"]),
        '  <text x="18" y="29" fill="#FFFFFF" font-family="%s" font-size="14" font-weight="700">%s</text>' % (esc(fnt["body"]), esc(a.title)),
        '  <rect x="%d" y="11" width="214" height="24" rx="12" fill="#FFFFFF" fill-opacity="0.16" stroke="#FFFFFF" stroke-opacity="0.45"/>' % (w - 228),
        '  <text x="%d" y="27" text-anchor="middle" fill="#FFFFFF" font-family="%s" font-size="11" font-weight="600">Illustration, not a live screenshot</text>' % (w - 121, esc(fnt["body"])),
    ]
    for idx, (lbl, val, note) in enumerate(fields):
        y = 46 + idx * row_h
        if idx > 0:
            svg.append('  <line x1="16" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1"/>' % (y, w - 16, y, pal["card_line"]))
        ly = y + (23 if note else 31)
        svg.append('  <text x="20" y="%d" fill="#%s" font-family="%s" font-size="13" font-weight="600">%s</text>' % (ly, pal["text"], esc(fnt["body"]), esc(lbl)))
        if note:
            svg.append('  <text x="20" y="%d" fill="#%s" font-family="%s" font-size="11">%s</text>' % (y + 41, pal["muted_text"], esc(fnt["body"]), esc(note)))
        bx, by, bw, bh = 310, y + 11, w - 328, 32
        svg.append('  <rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="#%s" stroke="#%s" stroke-width="1"/>' % (bx, by, bw, bh, pal["card"], pal["card_line"]))
        if val.startswith(("[x]", "[X]", "[ ]")):
            checked = val[:3].lower() == "[x]"
            label_txt = val[3:].strip()
            cb_fill = "#%s" % pal["primary"] if checked else "#FFFFFF"
            cb_stroke = "#%s" % pal["primary"] if checked else "#%s" % pal["muted_text"]
            svg.append('  <rect x="%d" y="%d" width="16" height="16" rx="3" fill="%s" stroke="%s" stroke-width="1.5"/>' % (bx + 10, by + 8, cb_fill, cb_stroke))
            if checked:
                svg.append('  <path d="M%d %d L%d %d L%d %d" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
                           % (bx + 13, by + 16, bx + 17, by + 20, bx + 23, by + 12))
            svg.append('  <text x="%d" y="%d" fill="#%s" font-family="%s" font-size="12" font-weight="600">%s</text>'
                       % (bx + 34, by + 21, pal["text"], esc(fnt["body"]), esc(label_txt)))
        else:
            svg.append('  <text x="%d" y="%d" fill="#%s" font-family="%s" font-size="12">%s</text>' % (bx + 12, by + 21, pal["text"], esc(fnt["mono"]), esc(val)))
    fy = 46 + len(fields) * row_h
    svg.append('  <path d="M1 %d L%d %d L%d %d Q%d %d %d %d L9 %d Q1 %d 1 %d Z" fill="#%s"/>'
               % (fy, w - 1, fy, w - 1, h - 9, w - 1, h - 1, w - 9, h - 1, h - 1, h - 1, h - 9, pal["card"]))
    svg.append('  <line x1="1" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="1"/>' % (fy, w - 1, fy, pal["card_line"]))
    sy = fy + (31 if a.action else 23)
    svg.append('  <text x="18" y="%d" fill="#%s" font-family="%s" font-size="11">Illustration, not a live screenshot · Source: %s</text>'
               % (sy, pal["muted_text"], esc(fnt["body"]), esc(a.source)))
    if a.action:
        abw = max(88, len(a.action) * 8 + 28)
        abx, aby = w - abw - 18, fy + 12
        svg.append('  <rect x="%d" y="%d" width="%d" height="28" rx="5" fill="#%s"/>' % (abx, aby, abw, pal["primary"]))
        svg.append('  <text x="%d" y="%d" text-anchor="middle" fill="#FFFFFF" font-family="%s" font-size="12" font-weight="600">%s</text>'
                   % (abx + abw // 2, aby + 19, esc(fnt["body"]), esc(a.action)))
    svg.append('</svg>\n')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    M.write_file(out_path, "\n".join(svg))
    print("FIGURE: wrote %s (%d fields, source %s)" % (out_path, len(fields), a.source))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("docs"); n.add_argument("--title", required=True); n.add_argument("--app", required=True)
    n.add_argument("--chapters", required=True); n.add_argument("--project")
    s = sub.add_parser("sync"); s.add_argument("docs"); s.add_argument("--check", action="store_true")
    f = sub.add_parser("figure"); f.add_argument("out"); f.add_argument("--title", required=True); f.add_argument("--source", required=True)
    f.add_argument("--field", action="append", required=True); f.add_argument("--action", default=""); f.add_argument("--project")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        return cmd_new(a)
    if a.cmd == "figure":
        return cmd_figure(a)
    return sync(os.path.abspath(a.docs), a.check)


if __name__ == "__main__":
    sys.exit(main())
