#!/usr/bin/env python3
"""Storyline first, layouts second. Propose layouts for a storyline from each slide's message and the deck's variety.

  python3 scripts/plan_deck.py storyline.json
storyline.json: {"meta": {...same as deck.json...}, "slides": [{"title": "...", "message": "number", "has": ["screenshot"]}, ...]}
  message: one of the 18 message types (python3 scripts/plan_deck.py --messages lists them)
  has (optional): what the content actually provides: numbers, series (a chart's values), dates, screenshot, steps, options
Prints, per slide, a first and second choice that tells the message, avoids repeating the previous layout or slide type,
and keeps tone and layout spread varied. It never decides for you: pick what fits the content, then write deck.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_deck import MESSAGES  # noqa: E402

ARCH = {"hero": "H", "statement": "H", "kpi:dark": "H", "kpi": "D", "kpi:minimal": "D", "chart": "D", "table": "D", "shift": "D", "split:number": "D",
        "screenshot": "V", "anatomy": "V", "annotated": "V", "split:screenshot": "V"}
NEEDS = {"chart": {"series"}, "shift": {"numbers"}, "kpi": {"numbers"}, "kpi:minimal": {"numbers"}, "kpi:dark": {"numbers"}, "hero:number": {"numbers"},
         "split:number": {"numbers"}, "screenshot": {"screenshot"}, "anatomy": {"screenshot"}, "annotated": {"screenshot"}, "split:screenshot": {"screenshot"},
         "diagram:roadmap": {"dates"}, "diagram:timeline": {"dates"}, "diagram:funnel": {"numbers"}}
TINT = {"split:number", "split:screenshot", "cards", "steps", "bullets"}
DARK = {"hero:statement", "hero:number", "kpi:dark"}


def arch(k):
    if k.startswith("hero"):
        return "H"
    if k.startswith("diagram:"):
        return "V"
    return ARCH.get(k, "T")


def plan(slides):
    out, prev, run, used, white = [], None, [], {}, 0
    for i, s in enumerate(slides):
        opts = list(MESSAGES.get(s.get("message"), ("", []))[1])
        if not opts:
            out.append((s, None, None, "unknown message %r" % s.get("message"))); continue
        has = set(s.get("has", []))
        def score(k):
            sc = 0
            if has and NEEDS.get(k) and not (NEEDS[k] & has):
                sc += 100
            if k == prev:
                sc += 50
            if len(run) >= 2 and run[-1] == run[-2] == arch(k):
                sc += 40
            if arch(k) == "H" and run and run[-1] == "H":
                sc += 40
            sc += 8 * used.get(k, 0)
            if white >= 3 and not (k in TINT or k in DARK):
                sc += 6
            sc += opts.index(k)
            return sc
        ranked = sorted(opts, key=score)
        first = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        out.append((s, first, second, ""))
        prev = first; run.append(arch(first)); used[first] = used.get(first, 0) + 1
        white = 0 if (first in TINT or first in DARK) else white + 1
    return out


def main(argv):
    if argv and argv[0] == "--messages":
        for k, (desc, lays) in MESSAGES.items():
            print("%-12s %-70s -> %s" % (k, desc, ", ".join(lays)))
        return 0
    if not argv:
        print(__doc__); return 2
    sl = json.load(open(argv[0], encoding="utf-8"))
    rows = plan(sl.get("slides", []))
    print("Plan for %d slides (first choice | second choice). Write the storyline first; then pick per slide:" % len(rows))
    for i, (s, a, b, err) in enumerate(rows, 1):
        print("%2d. [%s] %s\n      -> %s%s%s" % (i, s.get("message"), s.get("title", "")[:70], a or "-", ("  |  " + b) if b else "", ("  (" + err + ")") if err else ""))
    print("Keys: diagram:<kind> means layout diagram with that kind; hero:number means a hero with value; split:<kind> is split with that visual; kpi:minimal is style minimal.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
