#!/usr/bin/env python3
"""Scaffold and maintain a textbook-style guide in GitHub Markdown (references/structure.md).

  python3 scripts/docs_tool.py new docs --title "Beacon setup guide" --app Beacon \
      --chapters "Before you start;Install Beacon;Set up Beacon;Keep Beacon safe;Everyday use;Troubleshooting" [--project DIR]
  python3 scripts/docs_tool.py sync docs [--check]

new writes the home page, one page per chapter, Appendix A (answers), Appendix B (settings reference), glossary,
revisions and index from assets/templates, with the project logo on the home page when the brand has one
(scripts/brand.py). It refuses to overwrite existing files. Every page it writes holds WRITE: markers that the lint
fails (PLACEHOLDER) until they are replaced with real content.

sync rewrites only the generated parts: chapter and appendix numbers in headings (Chapter N: / N.M / Appendix X:)
from the file order, every link to a renumbered heading, the contents on the home page, the navigation footer on every
page and index.md from <!-- index: term; term --> markers. --check changes nothing and exits 1 when sync would change
a file (NAV, NUMBERING, INDEX are then stale).
"""
import argparse, datetime, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mdlib as M  # noqa: E402

TEMPLATES = os.path.join(HERE, "..", "assets", "templates")
NAV = re.compile(r"<!-- nav:start -->.*?<!-- nav:end -->", re.S)
CONTENTS = re.compile(r"<!-- contents:start -->.*?<!-- contents:end -->", re.S)
INDEX_BLOCK = re.compile(r"<!-- index:start -->.*?<!-- index:end -->", re.S)
MARKER = re.compile(r"<!--\s*index:\s*(?!start\s*-->|end\s*-->)(.+?)\s*-->")


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
    clash = [f for f in files if os.path.exists(os.path.join(docs, f))]
    if clash:
        sys.exit("STOPPED: these files already exist and new never overwrites: %s" % ", ".join(clash))
    for f, body in files.items():
        M.write_file(os.path.join(docs, f), body)
    print("NEW: %d pages in %s (%d chapters). Replace every WRITE: marker, then run sync and lint." % (len(files), docs, len(chapters)))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("docs"); n.add_argument("--title", required=True); n.add_argument("--app", required=True)
    n.add_argument("--chapters", required=True); n.add_argument("--project")
    s = sub.add_parser("sync"); s.add_argument("docs"); s.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        return cmd_new(a)
    return sync(os.path.abspath(a.docs), a.check)


if __name__ == "__main__":
    sys.exit(main())
