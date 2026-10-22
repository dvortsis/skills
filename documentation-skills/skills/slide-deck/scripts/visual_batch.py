#!/usr/bin/env python3
"""Visual review by contact sheet (VISUAL_BATCH). Shared file: identical copies in slide-deck and document-builder.

  python3 visual_batch.py render SRC [--per-sheet 4] [--width 800] [--out DIR]   SRC: .pdf, .pptx/.docx or a PNG folder
  python3 visual_batch.py viewed RENDER_DIR --sheet N [N ...]                    record sheets you looked at
  python3 visual_batch.py full RENDER_DIR --page P --reason "text"               record a full-size view
  python3 visual_batch.py finding RENDER_DIR --page P --text "what is wrong"     record a finding (unfixed)
  python3 visual_batch.py fixed RENDER_DIR --page P [--note "how"]               mark that page's findings fixed
  python3 visual_batch.py check RENDER_DIR [--log <file_key>.visual_qa.md]       FAIL VISUAL_BATCH; writes the log table
Every render goes to a new folder <name>_render_<timestamp> (viewers can show an older image when a name is reused).
Rule: view every sheet; open a page full size when its sheet shows a possible problem and for every page with small
text (figures, dense tables). check fails when a page is on no viewed sheet, a full-size view skipped its sheet, or a
finding is unfixed. Reply line: "visual review: N pages on S sheets, F viewed full size, M findings fixed".
"""
import argparse, datetime, glob, json, math, os, shutil, subprocess, sys, tempfile

FINDINGS = []
LOG = "visual_log.json"


def add(sev, code, msg):
    FINDINGS.append((sev, code, msg))


def new_dir(out, name):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    d = os.path.join(out, "%s_render_%s" % (name, stamp))
    n = 1
    while os.path.exists(d):
        d = os.path.join(out, "%s_render_%s_%d" % (name, stamp, n)); n += 1
    os.makedirs(os.path.join(d, "pages"))
    return d


def find_soffice():
    """LibreOffice on PATH or in its usual install folders (Windows, macOS, Linux)."""
    hit = shutil.which("soffice") or shutil.which("libreoffice")
    if hit:
        return hit
    roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")] + ["C:\\Program Files", "C:\\Program Files (x86)"]
    cands = [os.path.join(r, "LibreOffice", "program", "soffice.exe") for r in roots if r]
    cands += ["/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/lib/libreoffice/program/soffice", "/opt/libreoffice/program/soffice"]
    return next((c for c in cands if os.path.isfile(c)), None)


_OFFICE_PS = {  # read-only export through the installed Office app; nothing is saved over the source
    ".pptx": "$a = New-Object -ComObject PowerPoint.Application; try { $p = $a.Presentations.Open($env:VB_SRC, -1, 0, 0); "
             "$p.SaveAs($env:VB_PDF, 32); $p.Close() } finally { $a.Quit() }",
    ".docx": "$a = New-Object -ComObject Word.Application; $a.Visible = $false; try { $d = $a.Documents.Open($env:VB_SRC, $false, $true); "
             "$d.ExportAsFixedFormat($env:VB_PDF, 17); $d.Close($false) } finally { $a.Quit() }",
}


def office_pdf(src, pdf):
    """Windows fallback: convert with PowerPoint or Word when they are installed. True when the PDF was written."""
    ext = os.path.splitext(src)[1].lower()
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if os.name != "nt" or ext not in _OFFICE_PS or not ps:
        return False
    env = dict(os.environ, VB_SRC=os.path.abspath(src), VB_PDF=os.path.abspath(pdf))
    try:
        subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", _OFFICE_PS[ext]], capture_output=True, timeout=300, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return os.path.isfile(pdf)


def convert(src, tmp):
    """PDF path for a .pptx/.docx, or (None, reason). LibreOffice first, then the installed Office app on Windows."""
    pdf = os.path.join(tmp, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    soffice = find_soffice()
    if soffice:
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, src], capture_output=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if os.path.isfile(pdf):
            return pdf, None
    if office_pdf(src, pdf):
        return pdf, None
    return None, ("conversion to PDF failed for %s" % os.path.basename(src)) if soffice else \
        "LibreOffice (or, on Windows, PowerPoint/Word) not available to convert %s" % os.path.basename(src)


def to_pdf(src, tmp):
    pdf, why = convert(src, tmp)
    if not pdf:
        sys.exit("visual review: not run (%s)" % why)
    return pdf


def pdf_pages(pdf, width, dest):
    try:
        import fitz
    except ImportError:
        sys.exit("visual review: not run (PyMuPDF not available)")
    out = []
    for i, pg in enumerate(fitz.open(pdf), 1):
        zoom = max(width / pg.rect.width, 1.0)
        p = os.path.join(dest, "page_%03d.png" % i)
        pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(p); out.append(p)
    return out


def render(src, per_sheet=4, width=800, out=None):
    from PIL import Image, ImageDraw
    src = src.rstrip("/")
    name = os.path.splitext(os.path.basename(src))[0]
    d = new_dir(out or os.path.dirname(os.path.abspath(src)), name)
    pages_dir = os.path.join(d, "pages")
    if os.path.isdir(src):
        pages = []
        for i, f in enumerate(sorted(f for f in glob.glob(os.path.join(src, "*")) if f.lower().endswith((".png", ".jpg", ".jpeg"))), 1):
            im = Image.open(f).convert("RGB")
            if im.width < width:
                im = im.resize((width, int(im.height * width / im.width)))
            p = os.path.join(pages_dir, "page_%03d.png" % i); im.save(p); pages.append(p)
    else:
        pdf = src if src.lower().endswith(".pdf") else to_pdf(src, tempfile.mkdtemp(prefix="vb_"))
        pages = pdf_pages(pdf, width, pages_dir)
    if not pages:
        sys.exit("visual review: not run (no pages rendered from %s)" % os.path.basename(src))
    cols = 2 if per_sheet > 1 else 1
    log = {"source": os.path.basename(src), "created": datetime.datetime.now().isoformat(timespec="seconds"),
           "per_sheet": per_sheet, "pages": [], "sheets": [], "full_views": [], "findings": []}
    for s in range(math.ceil(len(pages) / per_sheet)):
        chunk = pages[s * per_sheet:(s + 1) * per_sheet]
        ims = [Image.open(p).convert("RGB") for p in chunk]
        cw, ch = max(max(im.width for im in ims), width), max(im.height for im in ims) + 28
        rows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (cols * cw + (cols + 1) * 12, rows * ch + (rows + 1) * 12), "white")
        dr = ImageDraw.Draw(sheet)
        for k, im in enumerate(ims):
            x, y = 12 + (k % cols) * (cw + 12), 12 + (k // cols) * (ch + 12)
            pno = s * per_sheet + k + 1
            dr.text((x, y), "Page %d" % pno, fill="black")
            sheet.paste(im, (x, y + 22))
            dr.rectangle([x - 1, y + 21, x + im.width, y + 22 + im.height], outline="#888888")
            log["pages"].append({"page": pno, "sheet": s + 1, "file": os.path.relpath(chunk[k], d)})
        sp = os.path.join(d, "sheet_%02d.png" % (s + 1))
        sheet.save(sp)
        log["sheets"].append({"sheet": s + 1, "file": os.path.basename(sp), "pages": [p["page"] for p in log["pages"] if p["sheet"] == s + 1], "viewed": False})
    save(d, log)
    print("render: %s | %d pages on %d sheets" % (d, len(pages), len(log["sheets"])))
    return d


def load(d):
    return json.load(open(os.path.join(d, LOG), encoding="utf-8"))


def save(d, log):
    json.dump(log, open(os.path.join(d, LOG), "w", encoding="utf-8"), indent=1)


def page_sheet(log, page):
    pg = [p for p in log["pages"] if p["page"] == page]
    if not pg:
        sys.exit("ERROR no page %d in this render" % page)
    return pg[0]["sheet"]


def check(d, log_md=None):
    """Return (findings, report line). Writes the markdown log table when log_md is given."""
    FINDINGS[:] = []
    log = load(d)
    viewed = {s["sheet"] for s in log["sheets"] if s["viewed"]}
    unseen = [p["page"] for p in log["pages"] if p["sheet"] not in viewed]
    if unseen:
        add("FAIL", "VISUAL_BATCH", "pages on no viewed sheet: %s" % unseen)
    skipped = sorted({f["page"] for f in log["full_views"] if f["sheet"] not in viewed})
    if skipped:
        add("FAIL", "VISUAL_BATCH", "full-size views without viewing their sheet first: pages %s" % skipped)
    open_f = [f for f in log["findings"] if not f.get("fixed")]
    if open_f:
        add("FAIL", "VISUAL_BATCH", "unfixed findings: %s" % "; ".join("page %d: %s" % (f["page"], f["text"]) for f in open_f))
    full = {f["page"] for f in log["full_views"]}
    fixed = sum(1 for f in log["findings"] if f.get("fixed"))
    line = "visual review: %d pages on %d sheets, %d viewed full size, %d findings fixed" % (len(log["pages"]), len(log["sheets"]), len(full), fixed)
    if log_md:
        rows = ["| Page | Sheet | Full Size | Findings | Fixed |", "|---|---|---|---|---|"]
        for p in log["pages"]:
            fs = [f for f in log["findings"] if f["page"] == p["page"]]
            rows.append("| %d | %d | %s | %s | %s |" % (p["page"], p["sheet"], "yes" if p["page"] in full else "no",
                        "; ".join(f["text"] for f in fs) or "none", ("yes" if all(f.get("fixed") for f in fs) else "no") if fs else "n/a"))
        open(log_md, "w", encoding="utf-8").write("# Visual Review: %s\n\nRender folder: %s\n\n%s\n\n%s\n" % (log["source"], os.path.basename(d.rstrip("/")), "\n".join(rows), line))
    return list(FINDINGS), line


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render"); p.add_argument("src"); p.add_argument("--per-sheet", type=int, default=4); p.add_argument("--width", type=int, default=800); p.add_argument("--out")
    p = sub.add_parser("viewed"); p.add_argument("dir"); p.add_argument("--sheet", type=int, nargs="+", required=True)
    p = sub.add_parser("full"); p.add_argument("dir"); p.add_argument("--page", type=int, required=True); p.add_argument("--reason", required=True)
    p = sub.add_parser("finding"); p.add_argument("dir"); p.add_argument("--page", type=int, required=True); p.add_argument("--text", required=True)
    p = sub.add_parser("fixed"); p.add_argument("dir"); p.add_argument("--page", type=int, required=True); p.add_argument("--note", default="")
    p = sub.add_parser("check"); p.add_argument("dir"); p.add_argument("--log")
    a = ap.parse_args()
    if a.cmd == "render":
        render(a.src, a.per_sheet, a.width, a.out); return 0
    log = load(a.dir)
    if a.cmd == "viewed":
        for s in log["sheets"]:
            if s["sheet"] in a.sheet:
                s["viewed"] = True
        save(a.dir, log); print("viewed sheets %s" % a.sheet); return 0
    if a.cmd == "full":
        log["full_views"].append({"page": a.page, "sheet": page_sheet(log, a.page), "reason": a.reason})
        save(a.dir, log); print("full-size view recorded: page %d" % a.page); return 0
    if a.cmd == "finding":
        log["findings"].append({"page": a.page, "sheet": page_sheet(log, a.page), "text": a.text, "fixed": False})
        save(a.dir, log); print("finding recorded: page %d" % a.page); return 0
    if a.cmd == "fixed":
        n = 0
        for f in log["findings"]:
            if f["page"] == a.page and not f.get("fixed"):
                f["fixed"], f["note"] = True, a.note; n += 1
        save(a.dir, log); print("marked %d finding(s) fixed on page %d" % (n, a.page)); return 0
    found, line = check(a.dir, a.log)
    for f in found:
        print("%s %s: %s" % f)
    print(line if not found else "visual review: FAIL x%d (%s)" % (len(found), line))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
