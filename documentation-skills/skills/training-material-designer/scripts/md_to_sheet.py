#!/usr/bin/env python3
"""Training quick-start or job-aid Markdown (front matter `output: pdf`) -> sheet doc.json for document-builder.

  python3 scripts/md_to_sheet.py <file.md> [more.md ...] [--combine] [--out doc.json] [--title "..."] [--owner "..."]
One doc.json per .md (next to it, <stem>.doc.json), or with --combine one doc.json with one page (top-level section) per
.md. The .md stays the single source: edit it, convert again, rebuild, then `lint_training.py <file>.md --pdf <file>.pdf`.
Mapping (contract "doc.json for a sheet"): meta.layout "sheet", meta.doc_type = format; one top-level section titled
with the role (front matter `role:`, else `audience:`); each H2 is a level-2 subsection in order; Who It's For + What
You Can Do and Common Mistakes + Get Help are half-width pairs; numbered steps -> numbered block; Worked Example ->
card block; front matter `diagram: [{label, icon}]` -> step_diagram block at the top of Steps. Lists and pairs come
from references/sheet-output.json. Prints DOC <path> and BUILD <exact command>.
"""
import argparse, datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_training as L  # noqa: E402

CFG = L.SHEET
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def proper(t):
    words = str(t).split()
    return " ".join(w if (w[:1].isupper() or (i and w.lower() in SMALL)) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def parse(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        sys.exit("ERROR %s: no front matter" % path)
    try:
        import yaml
        fm = yaml.safe_load(m.group(1)) or {}
        if not isinstance(fm, dict):
            raise ValueError
    except Exception:  # noqa: BLE001  (no PyYAML or not YAML: the lint's parser; diagram then unsupported)
        fm = L.front_matter(txt)[0] or {}
    return fm, txt[m.end():]


def blocks(text, base):
    out, para, lst, table = [], [], None, []
    def flush():
        nonlocal para, lst, table
        if para:
            out.append({"type": "paragraph", "text": " ".join(para)}); para = []
        if lst:
            out.append({"type": lst[0], "items": lst[1]}); lst = None
        if table:
            rows = [r for r in L.table_rows("\n".join(table))]
            out.append({"type": "table", "columns": rows[0], "rows": rows[1:]}); table = []
    for raw in text.splitlines():
        line = raw.rstrip()
        img = re.fullmatch(r"\s*!\[([^\]]*)\]\(([^)\s]+)[^)]*\)\s*", line)
        num = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        bul = re.match(r"^\s*[*+-]\s+(.*)$", line)
        if not line.strip():
            if para or table:
                flush()
            continue
        if img and SKIP_FIGURES:
            flush(); continue
        if img:
            flush()
            src = img.group(2) if os.path.isabs(img.group(2)) else os.path.normpath(os.path.join(base, img.group(2)))
            out.append({"type": "figure", "image": src, "caption": img.group(1), "alt": img.group(1)})
        elif line.lstrip().startswith("|"):
            if para or lst:
                flush()
            table.append(line)
        elif num or bul:
            kind = "numbered" if num else "bullets"
            if para or table or (lst and lst[0] != kind):
                flush()
            lst = lst or (kind, [])
            lst[1].append((num or bul).group(1).strip())
        elif lst and raw[:1] in (" ", "\t"):
            lst[1][-1] += " " + line.strip()
        else:
            if lst or table:
                flush()
            para.append(re.sub(r"^#{3,6}\s+", "", line.strip()))
    flush()
    return out


def card(bl):
    """Worked Example: its text (paragraphs) or items (a list) in one card; figures stay as blocks after it."""
    paras = [b["text"] for b in bl if b["type"] == "paragraph"]
    items = [x for b in bl if b["type"] in ("bullets", "numbered") for x in b["items"]]
    c = {"type": "card", "accent": "primary"}
    if paras:
        c["text"] = " ".join(paras)
    if items:
        c["items"] = items
    return [c] + [b for b in bl if b["type"] not in ("paragraph", "bullets", "numbered")]


def diagram(fm, path):
    d = fm.get("diagram")
    if not d:
        return None
    if not isinstance(d, list) or not all(isinstance(x, dict) and x.get("label") for x in d):
        print("WARN %s: diagram must be a list of {label, icon}; skipped" % path); return None
    lo, hi = CFG["diagram_steps"]
    if not lo <= len(d) <= hi:
        print("WARN %s: diagram has %d steps; the builder needs %d-%d" % (path, len(d), lo, hi))
    for x in d:
        if len(str(x["label"]).split()) > CFG["diagram_label_words"]:
            print("WARN %s: diagram label %r is over %d words" % (path, x["label"], CFG["diagram_label_words"]))
    return {"type": "step_diagram", "steps": [{"label": str(x["label"]), "icon": str(x.get("icon", "circle"))} for x in d],
            "emphasize_sequence": bool(fm.get("diagram_numbers", False))}


SKIP_FIGURES = False


def section(path):
    global SKIP_FIGURES
    fm, body = parse(path)
    SKIP_FIGURES = str(fm.get("pdf_figures", "true")).strip().lower() in ("false", "no", "0")  # D-08: one-page PDFs may leave figures out
    fmt = str(fm.get("format", ""))
    if fmt not in CFG["limits"]:
        sys.exit("ERROR %s: format %r; output: pdf is for %s" % (path, fmt, " and ".join(CFG["limits"])))
    if str(fm.get("output", "")).strip().lower() not in CFG["output_values"]:
        print("WARN %s: front matter has no 'output: pdf'; converting anyway" % path)
    subs = []
    for h, txt in L.sections(body).items():
        bl = blocks(txt, os.path.dirname(os.path.abspath(path)))
        if h in CFG["card_sections"]:
            bl = card(bl)
        if h == CFG["steps_section"]:
            dg = diagram(fm, path)
            bl = ([dg] if dg else []) + bl
        subs.append({"title": h, "blocks": bl})
    titles = [s["title"] for s in subs]
    for a, b in CFG["half_pairs"]:
        if a in titles and b in titles:
            sb = subs.pop(titles.index(b)); titles.remove(b)
            subs.insert(titles.index(a) + 1, sb); titles.insert(titles.index(a) + 1, b)
            subs[titles.index(a)]["width"] = sb["width"] = "half"
    t = re.sub(r"(?i)\s+(quick start|job aid)$", "", str(fm.get("title") or "")).strip()
    role = fm.get("role") or (t if t and t != str(fm.get("title") or "") else None) or fm.get("audience") or fm.get("title")  # D-08: role from the title before the audience sentence
    return fm, {"title": proper(role), "sections": subs}


def meta_from(fm, title=None, owner=None):
    m = {"title": title or str(fm.get("title", "")), "doc_type": str(fm.get("format")), "layout": "sheet",
         "audience": str(fm.get("audience", "")), "purpose": str(fm.get("objective", "")),
         "version": str(fm.get("version", "1.0")), "date": str(fm.get("date") or datetime.date.today().isoformat()),
         "sources": [str(s) for s in (fm.get("sources") or [])], "sheet": {"pages_per_section": 1}}
    own = owner or fm.get("owner")
    if own:
        m["owner"] = str(own)
    else:
        print("WARN owner: add 'owner:' to the front matter or pass --owner (document-builder needs meta.owner)")
    if fm.get("classification"):
        m["classification"] = str(fm["classification"])
    return m


def convert(paths, combine=False, out=None, title=None, owner=None):
    """Returns [(doc_json_path, doc, source .md paths)]; writes each file."""
    docs = []
    if combine:
        parts = [section(p) for p in paths]
        fmts = {str(fm.get("format")) for fm, _ in parts}
        if len(fmts) > 1:
            sys.exit("ERROR --combine needs one format; got %s" % ", ".join(sorted(fmts)))
        doc = {"meta": meta_from(parts[0][0], title, owner), "sections": [s for _, s in parts]}
        docs.append((out or os.path.splitext(paths[0])[0] + "_combined.doc.json", doc, list(paths)))
    else:
        for p in paths:
            fm, s = section(p)
            docs.append((out if out and len(paths) == 1 else os.path.splitext(p)[0] + ".doc.json", {"meta": meta_from(fm, title, owner), "sections": [s]}, [p]))
    for p, d, _ in docs:
        json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return docs


def builder():
    near = os.path.join(os.path.dirname(os.path.dirname(HERE)), CFG["builder"])
    return near if os.path.isfile(near) else "<document-builder>/scripts/build_doc.py"


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument("md", nargs="+"); ap.add_argument("--combine", action="store_true"); ap.add_argument("--out")
    ap.add_argument("--title"); ap.add_argument("--owner")
    a = ap.parse_args()
    for p, d, mds in convert(a.md, a.combine, a.out, a.title, a.owner):
        stem = re.sub(r"\.doc$", "", os.path.splitext(p)[0])
        print("DOC %s (%d page%s, doc_type %s, layout sheet)" % (p, len(d["sections"]), "" if len(d["sections"]) == 1 else "s", d["meta"]["doc_type"]))
        py = "python" if os.name == "nt" else "python3"  # the command name on this system
        print("BUILD %s %s %s --out %s.docx --pdf" % (py, builder(), p, stem))
        print("CHECK %s %s %s --pdf %s.pdf" % (py, os.path.join(HERE, "lint_training.py"), " ".join(mds), stem))
    return 0


if __name__ == "__main__":
    sys.exit(main())
