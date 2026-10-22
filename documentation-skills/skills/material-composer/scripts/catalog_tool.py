#!/usr/bin/env python3
"""Developer commands: change, add, retire or rename format types without editing code or the base catalog.
Every change goes to the overlay (assets/catalog/overlay.json, or --overlay / $MATERIAL_OVERLAY so a separate install can keep
different house formats), is validated before it is saved, and is logged with the command line.

  catalog_tool.py list [--family F]                 catalog_tool.py show ID
  catalog_tool.py add ID --family F --label "L" [--like ID] [--alias "x" ...] [--set key=value ...]
  catalog_tool.py set ID key=value [key=value ...]  (label, family, renderer, words, pages, doc_type, deck_type, kind,
                                                     subject_max, pair, exemplar; value "null" removes the key)
  catalog_tool.py section ID add "Title" [--after "T"] [--optional] [--half] [--limit steps=3-5]
  catalog_tool.py section ID remove|require|optional|half|full "Title"
  catalog_tool.py section ID rename "Old" "New"     catalog_tool.py section ID move "Title" --after "T"|--first
  catalog_tool.py section ID limit "Title" steps=3-5
  catalog_tool.py alias ID add|remove "text"
  catalog_tool.py rename ID --label "New Label"     (old label becomes a retired name the gate flags: RENAMED_TERM)
  catalog_tool.py retire ID [--replaced-by ID]      catalog_tool.py restore ID
  catalog_tool.py family ID set key=value ...       catalog_tool.py family ID add --label "L" --renderer R --keywords "a,b"
  catalog_tool.py reset ID                          (drop overlay changes for one format)
  catalog_tool.py validate | diff | export [--out file]
  catalog_tool.py drift                             (OVERLAY_DRIFT: working overlay vs the installed shared copy)
  catalog_tool.py card --out card.doc.json [--title T] [--audience A] [--extra extra.json]
                                                    (a one-page "What I Can Make" quick reference card from the
                                                     live catalog; --extra adds an agent's own tasks and help line)
Output codes: CATALOG_SCHEMA (FAIL, change refused), CATALOG_CHANGE (the saved change), OVERLAY_DRIFT (FAIL)."""
import argparse, copy, datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catlib

NUM = {"words", "pages", "subject_max"}
# check: CATALOG_SCHEMA FAIL
# check: CATALOG_CHANGE INFO


def parse_val(k, v):
    if v == "null":
        return None
    if k in NUM:
        return int(v)
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def parse_limit(s):
    k, v = s.split("=", 1); lo, hi = v.split("-") if "-" in v else (v, v)
    return k, [int(lo), int(hi)]


class Tool:
    def __init__(self, path):
        self.path = catlib.overlay_path(path)
        self.ov = catlib.load_overlay(self.path)
        self.base = json.load(open(catlib.BASE, encoding="utf-8"))

    def cat(self):
        return catlib.merge(self.base, self.ov)

    def fmt(self, fid, create=False):
        cat = self.cat()
        if fid not in cat["formats"] and not create:
            sys.exit("FAIL [CATALOG_SCHEMA] unknown format %s (catalog_tool.py list)" % fid)
        o = self.ov["formats"].setdefault(fid, {})
        if fid in cat["formats"] and "anatomy" not in o:
            o["anatomy"] = copy.deepcopy(cat["formats"][fid].get("anatomy", []))
        return o

    def save(self, what):
        errs = catlib.validate(self.cat())
        if errs:
            for e in errs:
                print("FAIL [CATALOG_SCHEMA] " + e)
            print("Change refused; overlay unchanged."); return 1
        self.ov.setdefault("log", []).append({"date": datetime.date.today().isoformat(), "change": what, "command": " ".join(sys.argv[1:])})
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        json.dump(self.ov, open(self.path, "w", encoding="utf-8"), indent=1)
        print("CATALOG_CHANGE saved: %s (%s)" % (what, os.path.relpath(self.path, catlib.SKILL) if self.path.startswith(catlib.SKILL) else self.path))
        return 0


def find_sec(an, title):
    for i, s in enumerate(an):
        if catlib.key(s["title"]) == catlib.key(title):
            return i
    sys.exit("FAIL [CATALOG_SCHEMA] no section '%s' (have: %s)" % (title, ", ".join(s["title"] for s in an)))


def overlay_version(ov):
    """(log entries, last log date, sha256[:12] of the canonical JSON) for OVERLAY_DRIFT messages."""
    import hashlib
    log = ov.get("log") or []
    sha = hashlib.sha256(json.dumps(ov, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return len(log), (log[-1].get("date") if log else "-"), sha


def drift(working=None):
    """OVERLAY_DRIFT (D-74, OPS-01): the installed overlay (assets/catalog/overlay.json, the one versioned shared copy,
    mastered in the suite bundle and shipped in this skill's zip to every agent) against a working overlay
    (--overlay or $MATERIAL_OVERLAY) that lasting developer changes were written to. FAIL names both versions."""
    shipped_p = catlib.OVERLAY
    working = working or os.environ.get("MATERIAL_OVERLAY")
    shipped = json.load(open(shipped_p, encoding="utf-8"))
    vs = overlay_version(shipped)
    tag = lambda v: "%d log entries, last %s, sha %s" % v
    if not working or os.path.abspath(working) == os.path.abspath(shipped_p) or not os.path.isfile(working):
        print("OVERLAY_DRIFT pass: no working overlay; the installed overlay is the shared copy (%s)" % tag(vs)); return 0
    wo = json.load(open(working, encoding="utf-8"))
    vw = overlay_version(wo)
    if vw[2] == vs[2]:
        print("OVERLAY_DRIFT pass: working overlay matches the installed shared copy (%s)" % tag(vs)); return 0
    lw, ls = wo.get("log") or [], shipped.get("log") or []
    if len(lw) < len(ls) and ls[:len(lw)] == lw:
        why = "is older than the installed shared copy; delete it or rebuild it from the installed copy"
    elif len(lw) > len(ls) and lw[:len(ls)] == ls:
        why = "has %d lasting change(s) that are not in the installed skill; ask the agent owner to repackage material-composer from the suite bundle master" % (len(lw) - len(ls))
    else:
        why = "and the installed shared copy have different histories; ask the agent owner to reconcile them in the suite bundle master and repackage"
    print("FAIL [OVERLAY_DRIFT] working overlay %s (%s) %s; installed shared copy: %s" % (working, tag(vw), why, tag(vs)))  # check: OVERLAY_DRIFT FAIL
    return 1


def card(cat, a):
    """WHATS_NEW: one-page quick reference card listing every live format by family (retired formats left out)."""
    # check: WHATS_NEW INFO
    extra = json.load(open(a.extra, encoding="utf-8")) if a.extra else {}
    fams = cat.get("families", {})
    by = {}
    for fid, f in cat["formats"].items():
        if fid in cat.get("retired", {}):
            continue
        by.setdefault(f["family"], []).append(f["label"])
    rows = [[fams.get(k, {}).get("label", k.replace("-", " ").title()), ", ".join(sorted(v))] for k, v in sorted(by.items(), key=lambda x: fams.get(x[0], {}).get("label", x[0]))]
    n = sum(len(v) for v in by.values())
    tasks = extra.get("tasks") or ["Ask for a format by name: \"Make a %s for %s about %s.\"" % ("job aid", "new billing specialists", "claim holds"),
                                   "Name the audience and the output you need (PDF, Word, slides, email or chat).",
                                   "Change one piece only: \"Turn this job aid into a quick reference card.\""]
    doc = {"meta": {"title": a.title, "doc_type": "quick-reference-card", "layout": "sheet", "audience": a.audience,
                    "purpose": "Use this to see every format you can ask for and how to ask",
                    "owner": extra.get("owner", "Agent owner"), "version": "1.0", "date": datetime.date.today().strftime("%B %Y"),
                    "classification": "Internal use only",
                    "sheet": {"pages_per_section": 1, "min_body_pt": 9, "min_table_pt": 8, "min_figure_pt": 8, "text_scale": 1.0},
                    "sources": ["Format catalog and overlay (%d formats in %d families)" % (n, len(by))] + extra.get("sources", [])},
           "sections": [{"title": extra.get("heading", "Every Format You Can Ask For"), "sections": [
               {"title": "At a Glance", "blocks": [
                   {"type": "paragraph", "text": extra.get("intro") or "Ask in plain words for any of these %d formats. If what you need isn't listed, ask anyway: the closest format is borrowed and named in the reply." % n},
                   {"type": "table", "caption": "Formats by Family", "columns": ["Family", "Formats"], "widths_in": [1.6, 4.9], "rows": rows}]},
               {"title": "Common Tasks", "blocks": [{"type": "bullets", "items": tasks[:8]}]},
               {"title": "Get Help", "width": "half", "blocks": [{"type": "paragraph", "text": extra.get("help") or "Ask the agent owner to add or change a format."}]}]}]}
    json.dump(doc, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("card: %d formats in %d families -> %s" % (n, len(by), a.out))
    return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--overlay")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("list"); p.add_argument("--family")
    p = sp.add_parser("show"); p.add_argument("id")
    p = sp.add_parser("add"); p.add_argument("id"); p.add_argument("--family", required=True); p.add_argument("--label", required=True)
    p.add_argument("--like"); p.add_argument("--alias", action="append", default=[]); p.add_argument("--set", action="append", default=[])
    p = sp.add_parser("set"); p.add_argument("id"); p.add_argument("pairs", nargs="+")
    p = sp.add_parser("section"); p.add_argument("id"); p.add_argument("action", choices=["add", "remove", "require", "optional", "half", "full", "rename", "move", "limit"])
    p.add_argument("title"); p.add_argument("extra", nargs="?"); p.add_argument("--after"); p.add_argument("--first", action="store_true")
    p.add_argument("--optional", action="store_true"); p.add_argument("--half", action="store_true"); p.add_argument("--limit", action="append", default=[])
    p = sp.add_parser("alias"); p.add_argument("id"); p.add_argument("action", choices=["add", "remove"]); p.add_argument("text")
    p = sp.add_parser("rename"); p.add_argument("id"); p.add_argument("--label", required=True)
    p = sp.add_parser("retire"); p.add_argument("id"); p.add_argument("--replaced-by")
    p = sp.add_parser("restore"); p.add_argument("id")
    p = sp.add_parser("family"); p.add_argument("id"); p.add_argument("action", choices=["set", "add"]); p.add_argument("pairs", nargs="*")
    p.add_argument("--label"); p.add_argument("--renderer"); p.add_argument("--keywords", default="")
    p = sp.add_parser("reset"); p.add_argument("id")
    sp.add_parser("validate"); sp.add_parser("diff"); sp.add_parser("drift")
    p = sp.add_parser("export"); p.add_argument("--out")
    p = sp.add_parser("card"); p.add_argument("--out", required=True); p.add_argument("--title", default="What I Can Make")
    p.add_argument("--audience", default="Everyone who asks this agent for documents, training or communications")
    p.add_argument("--extra")
    a = ap.parse_args()
    if a.cmd == "drift":
        return drift(a.overlay)
    t = Tool(a.overlay); c = a.cmd

    if c == "card":
        return card(t.cat(), a)
    if c == "list":
        cat = t.cat()
        for fid, f in sorted(cat["formats"].items(), key=lambda x: (x[1]["family"], x[0])):
            if not a.family or f["family"] == a.family:
                print("%-28s %-16s %s%s" % (fid, f["family"], f["label"], "  [overlay]" if fid in t.ov["formats"] else ""))
        for k, v in cat.get("retired", {}).items():
            print("%-28s retired%s" % (k, " -> " + v["replaced_by"] if v.get("replaced_by") else ""))
        return 0
    if c == "show":
        cat = t.cat(); f = cat["formats"].get(a.id) or sys.exit("FAIL [CATALOG_SCHEMA] unknown format %s" % a.id)
        r, _ = catlib.renderer_of(cat, f)
        print(json.dumps(dict(f, renderer=r), indent=1)); return 0
    if c == "add":
        cat = t.cat()
        if a.id in cat["formats"]:
            sys.exit("FAIL [CATALOG_SCHEMA] %s exists; use set or section" % a.id)
        e = copy.deepcopy(cat["formats"][a.like]) if a.like else {"anatomy": []}
        if a.like and a.like not in cat["formats"]:
            sys.exit("FAIL [CATALOG_SCHEMA] --like %s unknown" % a.like)
        e.update(family=a.family, label=a.label, aliases=a.alias, _replace=True)
        if a.like:
            e["derived_from"] = a.like
            if e.get("doc_type"):
                e["doc_type"] = a.id
        for kv in a.set:
            k, v = kv.split("=", 1); e[k] = parse_val(k, v)
        t.ov["formats"][a.id] = e; return t.save("added %s (%s)" % (a.id, a.label))
    if c == "set":
        o = t.fmt(a.id)
        for kv in a.pairs:
            k, v = kv.split("=", 1); o[k] = parse_val(k, v)
        return t.save("%s: %s" % (a.id, ", ".join(a.pairs)))
    if c == "section":
        o = t.fmt(a.id); an = o["anatomy"]
        if a.action == "add":
            s = {"title": a.title, "required": not a.optional}
            if a.half:
                s["width"] = "half"
            if a.limit:
                s["limits"] = dict(parse_limit(x) for x in a.limit)
            pos = 0 if a.first else (find_sec(an, a.after) + 1 if a.after else len(an))
            an.insert(pos, s)
        elif a.action == "remove":
            an.pop(find_sec(an, a.title))
        elif a.action in ("require", "optional"):
            an[find_sec(an, a.title)]["required"] = a.action == "require"
        elif a.action in ("half", "full"):
            s = an[find_sec(an, a.title)]
            s.pop("width", None)
            if a.action == "half":
                s["width"] = "half"
        elif a.action == "rename":
            an[find_sec(an, a.title)]["title"] = a.extra or sys.exit("FAIL [CATALOG_SCHEMA] rename needs the new title")
        elif a.action == "move":
            s = an.pop(find_sec(an, a.title))
            an.insert(0 if a.first else find_sec(an, a.after) + 1, s)
        elif a.action == "limit":
            k, v = parse_limit(a.extra); an[find_sec(an, a.title)].setdefault("limits", {})[k] = v
        return t.save("%s: section %s '%s'%s" % (a.id, a.action, a.title, " -> " + a.extra if a.extra else ""))
    if c == "alias":
        o = t.fmt(a.id); al = o.setdefault("aliases", list(t.cat()["formats"][a.id].get("aliases", [])))
        (al.append(a.text) if a.action == "add" else al.remove(a.text))
        return t.save("%s: alias %s '%s'" % (a.id, a.action, a.text))
    if c == "rename":
        old = t.cat()["formats"][a.id]["label"] if a.id in t.cat()["formats"] else sys.exit("FAIL [CATALOG_SCHEMA] unknown %s" % a.id)
        o = t.fmt(a.id); o["label"] = a.label
        t.ov.setdefault("renamed", {})[old] = {"format": a.id, "now": a.label}
        return t.save("%s: label '%s' -> '%s' (old label now flagged)" % (a.id, old, a.label))
    if c == "retire":
        if a.id not in t.cat()["formats"]:
            sys.exit("FAIL [CATALOG_SCHEMA] unknown %s" % a.id)
        t.ov.setdefault("retired", {})[a.id] = {"replaced_by": a.replaced_by, "date": datetime.date.today().isoformat()}
        return t.save("retired %s%s" % (a.id, " (replaced by %s)" % a.replaced_by if a.replaced_by else ""))
    if c == "restore":
        t.ov.get("retired", {}).pop(a.id, None); return t.save("restored %s" % a.id)
    if c == "family":
        if a.action == "add":
            t.ov["families"][a.id] = {"label": a.label, "renderer": a.renderer, "keywords": [k.strip() for k in a.keywords.split(",") if k.strip()], "purpose": "", "pages": None, "words": None, "tone": "", "visuals": ""}
        for kv in a.pairs:
            k, v = kv.split("=", 1)
            t.ov["families"].setdefault(a.id, {})[k] = [x.strip() for x in v.split(",")] if k == "keywords" else parse_val(k, v)
        return t.save("family %s: %s %s" % (a.id, a.action, " ".join(a.pairs)))
    if c == "reset":
        t.ov["formats"].pop(a.id, None); return t.save("reset %s to the base catalog" % a.id)
    if c == "validate":
        errs = catlib.validate(t.cat())
        for e in errs:
            print("FAIL [CATALOG_SCHEMA] " + e)
        print("CATALOG: %d formats, %d families, %d failed" % (len(t.cat()["formats"]), len(t.cat()["families"]), len(errs)))
        return 1 if errs else 0
    if c == "diff":
        for fid in t.ov["formats"]:
            print("format %s: %s" % (fid, "new" if fid not in t.base["formats"] else "changed"))
        for k, v in t.ov.get("retired", {}).items():
            print("retired %s" % k)
        for k, v in t.ov.get("renamed", {}).items():
            print("renamed '%s' -> '%s'" % (k, v["now"]))
        for e in t.ov.get("log", [])[-10:]:
            print("log %s %s" % (e["date"], e["change"]))
        return 0
    if c == "export":
        s = json.dumps(t.cat(), indent=1)
        (open(a.out, "w").write(s) if a.out else print(s)); return 0


if __name__ == "__main__":
    sys.exit(main())
