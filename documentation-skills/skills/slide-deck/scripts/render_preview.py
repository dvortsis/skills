#!/usr/bin/env python3
"""Render a .pptx to slide PNGs and contact sheets of 4 for the visual review (VISUAL_BATCH).

  python3 scripts/render_preview.py out/Deck.pptx [--outdir out/preview] [--per-sheet 4]

Each run renders into a new folder (<deck>_preview_<timestamp>) so an image viewer never shows an older render; an
explicit --outdir is cleared of earlier slide PNGs first. The slides then go through the shared scripts/visual_batch.py
render, which writes sheet_NN.png (4 slides each, labelled by page) and visual_log.json to a new
<deck>_render_<timestamp> folder inside the preview folder; the script prints that folder and the next commands
(viewed, full, finding, fixed, check). contact_sheet.png (every slide, 3 across) is still written as an overview.

Needs PyMuPDF and a converter: LibreOffice (soffice), or on Windows an installed PowerPoint (read-only export). If
either is missing it prints NOT RUN with the reason and exits 0, so the
caller records the visual check as not run (never as passed). Brand fonts missing here are substituted
in the preview only; the .pptx keeps the brand fonts.
"""
import argparse, glob, os, re, shlex, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
VB = os.path.join(HERE, "visual_batch.py")


def sheets(pdf, outdir, per_sheet):
    """Contact sheets via the shared visual_batch module. Returns (render folder, log) or (None, reason)."""
    sys.path.insert(0, HERE)
    import visual_batch
    try:
        rd = visual_batch.render(pdf, per_sheet=per_sheet, width=1152, out=outdir)
    except SystemExit as e:
        return None, str(e.code)
    return rd, visual_batch.load(rd)


def next_steps(rd, log, pptx):
    vb = os.path.relpath(VB)
    vb = ("python " if os.name == "nt" else "python3 ") + shlex.quote(VB if vb.startswith("..") else vb)
    q = shlex.quote(rd)
    key = re.sub(r"_v\d+$", "", os.path.splitext(os.path.basename(pptx))[0])
    qa = shlex.quote(os.path.join(os.path.dirname(pptx), key + ".visual_qa.md"))
    print("NEXT: view every contact sheet (sheet_01.png to sheet_%02d.png in %s), then:" % (len(log["sheets"]), rd))
    print("  %s viewed %s --sheet %s" % (vb, q, " ".join(str(s["sheet"]) for s in log["sheets"])))
    print('  %s full %s --page P --reason "possible problem on its sheet" (also every page with small text)' % (vb, q))
    print('  %s finding %s --page P --text "what is wrong"' % (vb, q))
    print('  fix deck.json, rebuild and re-lint, then: %s fixed %s --page P --note "how"' % (vb, q))
    print("  %s check %s --log %s   (<file_key>.visual_qa.md)" % (vb, q, qa))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx"); ap.add_argument("--outdir")
    ap.add_argument("--per-sheet", type=int, default=4, help="slides per contact sheet (default 4)")
    a = ap.parse_args()
    try:
        import fitz
        from PIL import Image
    except ImportError as e:
        print("NOT RUN: preview needs PyMuPDF and Pillow (%s)" % e); return
    sys.path.insert(0, HERE)
    import visual_batch
    outdir = a.outdir or os.path.splitext(a.pptx)[0] + time.strftime("_preview_%Y%m%d-%H%M%S")
    os.makedirs(outdir, exist_ok=True)
    for old in glob.glob(os.path.join(outdir, "slide_*.png")) + glob.glob(os.path.join(outdir, "contact_sheet.png")):
        os.remove(old)
    tmp = tempfile.mkdtemp()
    pdf, why = visual_batch.convert(a.pptx, tmp)
    if not pdf:
        print("NOT RUN: " + why); return
    doc = fitz.open(pdf)
    paths = []
    for i, page in enumerate(doc, 1):
        p = os.path.join(outdir, "slide_%02d.png" % i)
        page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(p)
        paths.append(p)
    rd, log = sheets(pdf, outdir, a.per_sheet)
    ims = [Image.open(p) for p in paths]
    tw, th = 640, int(640 * ims[0].height / ims[0].width)
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 16, rows * th + (rows + 1) * 16), "#DFDFDF")
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th)), (16 + (i % cols) * (tw + 16), 16 + (i // cols) * (th + 16)))
    sp = os.path.join(outdir, "contact_sheet.png")
    sheet.save(sp)
    print("RENDERED %d slides -> %s (contact sheet: %s)" % (len(paths), outdir, sp))
    if rd is None:
        print("NOT RUN: contact sheets for the visual review: %s" % log); return
    print("SHEETS: %d pages on %d contact sheets of %d -> %s" % (len(log["pages"]), len(log["sheets"]), a.per_sheet, rd))
    next_steps(rd, log, a.pptx)


if __name__ == "__main__":
    main()
