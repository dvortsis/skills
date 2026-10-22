#!/usr/bin/env python3
"""Captions and transcript from a video script's Script table (CAPTION_FILE).

  python3 scripts/md_to_captions.py <file>.md [--out DIR]
Writes <file>.srt (one cue per table row; start and end from the Time column) and <file>.transcript.md
(title, then each row's time, on-screen note and narration). A narration cell longer than its time slot allows
at the words-per-minute rate in references/training-rules.json prints `FAIL CAPTION_FILE ...`, writes nothing
and exits 1.
"""
import os, sys, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint_training as L  # noqa: E402


def stamp(sec):
    return "%02d:%02d:%02d,000" % (sec // 3600, sec % 3600 // 60, sec % 60)


def script_rows(path):
    """(title, [(time, start, end, on_screen, narration)]) from the Script table; columns found by header."""
    fm, body = L.front_matter(open(path, encoding="utf-8").read())
    rows = L.table_rows(L.sections(body).get("Script", ""))
    if not rows:
        raise ValueError("no Script table")
    head = [c.lower() for c in rows[0]]
    if "time" not in head or "narration" not in head:
        raise ValueError("the Script table needs Time and Narration columns")
    ti, ni = head.index("time"), head.index("narration")
    oi = head.index("on screen") if "on screen" in head else None
    out = []
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        m = L.TIME.match(r[ti])
        if not m:
            raise ValueError("time '%s' must look like 0:00-0:20" % r[ti])
        a, b = L.secs(m.group(1), m.group(2)), L.secs(m.group(3), m.group(4))
        out.append((r[ti], a, b, r[oi] if oi is not None else "", r[ni]))
    return (fm or {}).get("title") or os.path.splitext(os.path.basename(path))[0], out


def convert(path, out_dir=None):
    """Returns (srt_path, transcript_path), or raises CaptionError with the CAPTION_FILE messages."""
    title, rows = script_rows(path)
    bad = L.caption_overruns([(i + 1, t, a, b, n) for i, (t, a, b, _, n) in enumerate(rows)])
    if bad:
        raise CaptionError(bad)
    width = L.RULES["caption"]["line_chars"]
    srt = []
    for i, (t, a, b, _, n) in enumerate(rows, 1):
        srt.append("%d\n%s --> %s\n%s\n" % (i, stamp(a), stamp(b), "\n".join(textwrap.wrap(n, width))))
    tr = ["# %s" % title, "", "Transcript of the video script.", ""]
    for t, a, b, scr, n in rows:
        tr.append("**%s.** %s%s" % (t, "*(On screen: %s)* " % scr if scr else "", n))
        tr.append("")
    stem = os.path.splitext(os.path.basename(path))[0]
    d = out_dir or os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    sp, tp = os.path.join(d, stem + ".srt"), os.path.join(d, stem + ".transcript.md")
    open(sp, "w", encoding="utf-8").write("\n".join(srt))
    open(tp, "w", encoding="utf-8").write("\n".join(tr))
    return sp, tp


class CaptionError(Exception):
    pass


def main(argv):
    out = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print("ERROR --out needs a folder"); return 2
        out = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    if len(argv) != 1:
        print(__doc__); return 2
    try:
        sp, tp = convert(argv[0], out)
    except CaptionError as e:
        for msg in e.args[0]:
            print("FAIL CAPTION_FILE [%s] %s" % (argv[0], msg))
        return 1
    except (ValueError, OSError) as e:
        print("ERROR %s: %s" % (argv[0], e)); return 2
    print("SRT %s\nTRANSCRIPT %s" % (sp, tp))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
