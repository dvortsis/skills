#!/usr/bin/env python3
"""Plan any material: resolve the requested format to a family, renderer, anatomy, limits and gates, and write
<name>.plan.json. Unlisted formats borrow the nearest catalog entry (derived_from). Per-request changes never touch the
catalog; use catalog_tool.py for lasting format changes.

  plan_material.py "badge card for UAT testers" --audience "UAT testers" --subject "Expense tool rollout" [--out x.plan.json]
      [--family F] [--output pdf|md|docx|pptx|html|xlsx] [--set words=300] [--add-section "Title"[@after]]
      [--drop-section "Title"] [--rename-section "Old=New"] [--overlay overlay.json] [--ask]
      [--audience-profile business|leaders|technical|clinical-partners|physicians|frontline]
      [--translation-ready [--source <Name>.doc.json|.md]]
  plan_material.py --retarget old.plan.json --as "quick reference card" [--out new.plan.json]
      change a material's format: prints which sections carry over, which are new and which are dropped
Every plan prints MATCH (exact, alias, derived high, derived family, low). A low match plans a neutral outline
(Purpose | Key Points | What to Do | Get Help); with --ask it prints one QUESTION instead and writes no plan.
Codes: FORMAT_RESOLVE (FAIL when nothing can be resolved), MATCH_CONFIDENCE (WARN, low match), AUDIENCE_PROFILE
(FAIL, unknown profile), PLAN_GATES (FAIL, renderer without gates), DOC_TYPE (WARN, doc_type the document builder
does not list), TRANSLATION_READY (75 percent word budget, text-only Word export, written translation process)."""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catlib

RULES = catlib.rules()

OUT_BY_RENDERER = {"doc-sheet": ["pdf", "docx"], "doc-long": ["pdf", "docx"], "deck": ["pptx"], "page": ["confluence"],
                   "training-md": ["md"], "md": ["md"], "form": ["pdf", "xlsx"], "module": ["html", "md"],
                   "xlsx": ["xlsx"]}
UNIVERSAL = ["plain language (JARGON_UNDEFINED, TELEGRAPHIC)", "Proper Case titles and the hyphen rule", "no PHI, placeholders or filler",
             "sources listed", "one name per set (RENAMED_TERM)", "visual review for anything rendered"]


# check: FORMAT_RESOLVE FAIL
# check: MATCH_CONFIDENCE WARN
# check: AUDIENCE_PROFILE FAIL
# check: PLAN_GATES FAIL
# check: DOC_TYPE WARN
# check: TRANSLATION_READY INFO
def apply_profile(plan, name):
    pid, p = catlib.profile(name)
    if not pid:
        print("FAIL [AUDIENCE_PROFILE] unknown profile '%s' (use %s)" % (name, ", ".join(p))); return False
    fl = p.get("format_limits", {}).get(plan["format"], {})
    if plan["words"] and p.get("words_multiplier", 1.0) != 1.0:
        plan["words"] = int(plan["words"] * p["words_multiplier"])
    plan["words"] = fl.get("words", plan["words"]); plan["title_words"] = fl.get("title_words")
    plan.update(audience_profile=pid, profile_tone=p.get("tone"), jargon=p.get("jargon"), terminology_sets=p.get("terminology_sets", ["internal"]),
                limits_source=p.get("source") if fl else None)
    return True


def apply_overrides(plan, a):
    an = plan["anatomy"]; done = []
    for kv in a.set or []:
        k, v = kv.split("=", 1); plan[k] = int(v) if v.isdigit() else v; done.append("set " + kv)
    for t in a.drop_section or []:
        n = len(an); an[:] = [s for s in an if catlib.key(s["title"]) != catlib.key(t)]
        done.append(("dropped " if len(an) < n else "no section to drop: ") + t)
    for kv in a.rename_section or []:
        old, new = kv.split("=", 1)
        for s in an:
            if catlib.key(s["title"]) == catlib.key(old):
                s["title"] = new; done.append("renamed %s -> %s" % (old, new))
    for t in a.add_section or []:
        title, _, after = t.partition("@")
        idx = next((i + 1 for i, s in enumerate(an) if after and catlib.key(s["title"]) == catlib.key(after)), len(an))
        an.insert(idx, {"title": title, "required": True}); done.append("added " + title)
    return done


def build_plan(cat, req, a):
    r = catlib.resolve(cat, req, a.family)
    if not r or not r.get("entry"):
        print("FAIL [FORMAT_RESOLVE] no format named; say what you need (for example 'job aid' or 'survey')"); return None
    if r["match"] == "low" and getattr(a, "ask", False):
        print("MATCH: low (%s)" % r["score"]); print("QUESTION: " + RULES["match"]["question"]); return "asked"
    e = r["entry"]; fam = cat["families"][e["family"]]
    rid, rend = catlib.renderer_of(cat, e)
    gates = RULES.get("renderer_gates", {}).get(rid)
    if gates is None:
        print("FAIL [PLAN_GATES] renderer %s has no gates in references/material_rules.json renderer_gates" % rid); return None
    outputs = OUT_BY_RENDERER.get(rid, ["md"])
    xo = {k: v for k, v in (RULES.get("extra_outputs", {}).get(r["id"]) or RULES.get("extra_outputs", {}).get(r["derived_from"] or "") or {}).items()
          if k not in outputs}  # D-53: e.g. data-dictionary and raci also plan xlsx
    if a.output and a.output not in xo:
        outputs = [a.output] + [o for o in outputs if o != a.output]
    also = [dict(cat["renderers"][rr], id=rr, output=o) for o, rr in xo.items()]
    gates = list(gates) + [x for o in also for x in RULES["renderer_gates"].get(o["id"], [])]
    outputs = outputs + [o["output"] for o in also]
    plan = {"request": req, "format": r["id"], "label": e["label"], "family": e["family"], "how": r["how"],
            "derived_from": r["derived_from"], "match": r["match"], "match_score": r["score"], "nearest": r.get("nearest"), "renderer": dict(rend, id=rid), "outputs": outputs, "also": also,
            "audience": a.audience, "subject": a.subject, "anatomy": e.get("anatomy", []),
            "words": e.get("words", fam.get("words")), "pages": e.get("pages", fam.get("pages")),
            "tone": fam.get("tone"), "purpose": fam.get("purpose"), "visuals": fam.get("visuals"),
            "doc_type": e.get("doc_type") or (r["id"] if rid == "doc-sheet" else None), "deck_type": e.get("deck_type"),
            "kind": e.get("kind"), "subject_max": e.get("subject_max"), "pair": e.get("pair"), "limits": e.get("limits", {}),
            "exemplar": e.get("exemplar"), "profile": e.get("profile"),
            "gates": list(gates) + UNIVERSAL, "house": "references/house-conventions.md",
            "style_tokens": "assets/style_tokens.json", "renamed_terms": sorted(cat.get("renamed", {}))}
    fr = RULES.get("format_rules", {}).get("formats", {})
    fg = (fr.get(r["id"]) or fr.get(r["derived_from"] or "") or {}).get("gate")
    if fg:
        plan["gates"].append(fg)
    if rid == "training-md" and "pdf" in outputs and e["family"] == "reference-sheet":
        plan["renderer"]["build"] = "training-material-designer scripts/md_to_sheet.py <file>.md, then document-builder build_doc.py (layout sheet)"
    if r["id"] == "quick-start" and outputs[0] == "pdf":
        plan["words"] = 250
    if r["match"] == "low":
        print("WARN [MATCH_CONFIDENCE] '%s' matched no catalog format well (nearest %s, %s); planned a neutral outline. "
              "Use --ask for one question, --family, or a catalog format name." % (req, r.get("nearest"), r["score"]))
    if rid == "doc-long":
        types = catlib.builder_doc_types()
        if types is None:
            print("WARN [DOC_TYPE] doc_type %s not checked: document-builder assets/doc_theme.json not found" % plan["doc_type"])
        elif plan["doc_type"] not in types:
            print("WARN [DOC_TYPE] doc_type %s is not a document builder type (%s); set meta.doc_type to one of them" % (plan["doc_type"], ", ".join(sorted(types))))
    if not apply_profile(plan, getattr(a, "audience_profile", None)):
        return None
    if getattr(a, "translation_ready", False):
        t = RULES["translation"]
        if plan["words"]:
            plan["words"] = int(plan["words"] * t["budget"])
        plan["translation"] = t; plan["gates"] = plan["gates"] + ["translation-ready: " + "; ".join(t["rules"])]
    plan["overrides"] = apply_overrides(plan, a)
    return plan


def card(p):
    how = "  borrowed from %s" % p["derived_from"] if p["derived_from"] else ("  neutral outline (nearest: %s)" % p["nearest"] if p["match"] == "low" else "")
    m = "derived family (%s default %s)" % (p["family"], p["derived_from"]) if p["match"] == "derived family" else "%s (%s)" % (p["match"], p["match_score"])
    lim = ("LIMITS: title <= %s words, body <= %s words%s" % (p["title_words"], p["words"], " (%s)" % p["limits_source"] if p.get("limits_source") else "")
           if p.get("title_words") else "LIMITS: words %s, pages %s%s" % (p["words"] or "-", p["pages"] or "-", "".join("; %s %s" % (s["title"], s["limits"]) for s in p["anatomy"] if s.get("limits"))))
    L = ["FORMAT: %s (%s)%s" % (p["label"], p["family"], how), "MATCH: " + m,
         "BUILD: %s -> %s" % (p["renderer"]["skill"], ", ".join(o for o in p["outputs"] if o not in [x["output"] for x in p.get("also", [])]))
         + ("; build %s" % p["renderer"]["build"] if p["renderer"].get("id") == "xlsx" else ""),
         "SECTIONS: " + (" | ".join(s["title"] + ("" if s.get("required", True) else " (optional)") + (" [half]" if s.get("width") == "half" else "") for s in p["anatomy"]) or "per the renderer's schema"),
         lim, "TONE: %s" % p["tone"],
         "PROFILE: %s - %s; %s; terminology: %s" % (p["audience_profile"], p["profile_tone"], p["jargon"], ", ".join(p["terminology_sets"])),
         "GATES: " + "; ".join(p["gates"])]
    for x in p.get("also", []):
        L.insert(3, "ALSO: %s -> %s; build %s; gate %s" % (x["skill"], x["output"], x["build"], x["gate"]))
    if p.get("translation"):
        L.append("TRANSLATION: %s: %s." % (p["translation"]["never"], p["translation"]["process"]))
    if p["overrides"]:
        L.append("THIS REQUEST ONLY: " + "; ".join(p["overrides"]))
    return "\n".join(L)


def retarget(cat, a):
    old = json.load(open(a.retarget, encoding="utf-8")); a.audience = a.audience or old.get("audience"); a.subject = a.subject or old.get("subject")
    new = build_plan(cat, a.as_, a)
    if not new or new == "asked":
        return new
    ot = {catlib.key(s["title"]): s["title"] for s in old.get("anatomy", [])}
    nt = {catlib.key(s["title"]): s["title"] for s in new["anatomy"]}
    new["retargeted_from"] = old["format"]
    new["carry_over"] = [nt[k] for k in nt if k in ot]
    new["write_new"] = [nt[k] for k in nt if k not in ot]
    new["drop"] = [ot[k] for k in ot if k not in nt]
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request", nargs="?", default=""); ap.add_argument("--audience"); ap.add_argument("--subject")
    ap.add_argument("--family"); ap.add_argument("--output"); ap.add_argument("--out"); ap.add_argument("--overlay")
    ap.add_argument("--set", action="append"); ap.add_argument("--add-section", action="append"); ap.add_argument("--drop-section", action="append")
    ap.add_argument("--rename-section", action="append"); ap.add_argument("--retarget"); ap.add_argument("--as", dest="as_")
    ap.add_argument("--ask", action="store_true"); ap.add_argument("--audience-profile"); ap.add_argument("--translation-ready", action="store_true")
    ap.add_argument("--source")
    a = ap.parse_args()
    cat = catlib.load(a.overlay)
    p = retarget(cat, a) if a.retarget else build_plan(cat, a.request, a)
    if not p:
        return 1
    if p == "asked":
        return 0
    print(card(p))
    if a.retarget:
        print("CHANGE FORMAT: %s -> %s | carry over: %s | write new: %s | drop: %s" % (p["retargeted_from"], p["format"], ", ".join(p["carry_over"]) or "-", ", ".join(p["write_new"]) or "-", ", ".join(p["drop"]) or "-"))
    out = a.out or "%s.plan.json" % p["format"]
    json.dump(p, open(out, "w"), indent=1); print("PLAN: " + out)
    if p.get("translation"):
        if a.source:
            import translation_export
            translation_export.export(a.source, os.path.dirname(os.path.abspath(out)))
        else:
            print("TRANSLATION EXPORT: after writing the source run scripts/translation_export.py <source> (writes <Name>_for_translation.docx)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
