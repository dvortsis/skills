#!/usr/bin/env python3
"""Self-test for material-composer core (catalog, developer commands, plan, gate, kits, ILT pairs, style tokens).
Form, survey and e-learning builders have their own test_builders.py.

  python3 scripts/test_composer.py [--only CODE[,CODE]] [--only list]
Prints `SELF-TEST: <passed>/<total> passed`; exits 1 on any failure. Inputs are synthetic except the
request fixtures in assets/fixtures (D-37, D-39, D-41, D-43, D-45)."""
import copy, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
PY = sys.executable
CODES = ["OVERLAY_DRIFT", "FORMAT_RESOLVE", "CATALOG_SCHEMA", "CATALOG_CHANGE", "ANATOMY_MATCH", "DERIVED_NOTE", "RENAMED_TERM", "SLOP_OPENER",
         "SUBJECT_LENGTH", "WORD_LIMIT", "PLACEHOLDER", "FILLER", "PHI_PATTERN", "TITLE_CASE", "SOURCES_MISSING", "FRONT_MATTER",
         "KIT_COVERAGE", "ILT_PAIR", "STYLE_DRIFT", "EXEMPLARS", "MATCH_CONFIDENCE", "AUDIENCE_PROFILE", "TERM_BRAND",
         "COMMS_CHECK", "PLAN_GATES", "DOC_TYPE", "TRANSLATION_READY", "SECTION_DRIFT", "KIT_ADOPTION",
         "RACI_ONE_A", "AGENDA_TIME", "METRIC_FIELDS", "DICT_FIELDS", "RELEASE_ACTION", "PROPOSAL_ASK", "PROCESS_TEXT", "CHECKOFF_VERBS",
         "CHARTER_GOAL", "PLAN_COVERAGE", "DASH_DEFS", "WHATS_NEW"]
ONLY = None
a = sys.argv[1:]
if "--only" in a:
    arg = a[a.index("--only") + 1] if a.index("--only") + 1 < len(a) else ""
    if arg == "list":
        print("\n".join(sorted(CODES))); sys.exit(0)
    ONLY = {c.strip() for c in arg.split(",") if c.strip()}
    if not ONLY or ONLY - set(CODES):
        sys.stderr.write("unknown --only code(s): %s\n" % ", ".join(sorted(ONLY - set(CODES)))); sys.exit(2)
results = []
TMP = tempfile.mkdtemp(prefix="composer_test_")
# Hermetic brand: every CLI run resolves the brand of an empty project unless a case points it at its own project.
os.environ["BRAND_PROJECT"] = tempfile.mkdtemp(prefix="composer_brand_empty_")
OV = os.path.join(TMP, "overlay.json")
ENV = dict(os.environ, MATERIAL_OVERLAY=OV)


def sel(*c):
    return ONLY is None or bool(ONLY & set(c))


def check(name, ok, detail=""):
    results.append(ok); print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + detail[-400:]))


def run(*args, cwd=TMP):
    r = subprocess.run([PY] + list(args), capture_output=True, text=True, cwd=cwd, env=ENV)
    return r.returncode, r.stdout + r.stderr


def S(n):
    return os.path.join(HERE, n)


def write(name, text):
    p = os.path.join(TMP, name); open(p, "w", encoding="utf-8").write(text); return p


JOB_AID = """---
format: job-aid
title: Record a Test Result
audience: UAT testers
sources:
  - Synthetic test content
---
# Record a Test Result

## When to Use
Use this when a test step is ready for your result.

## Steps
1. Open the test from your queue.
2. Follow the step exactly as written.
3. Record Pass or Fail for the step.

## Check Your Work
Every step shows a result before you submit.

## Questions?
Ask your review lead in the test channel.
"""
EMAIL = """---
format: announcement-email
title: New Review Page Opens Monday
audience: Report reviewers
subject: The new review page opens Monday
sources:
  - Synthetic kit content
---
## Why This Is Changing
Reviewers asked for one place to record results.

## What Changes for You
You record results on the review page instead of email.

## What to Do
Open the review page on Monday and record one result.

## Get Help
Reply to this email with the step name.
"""
TALK = """---
format: manager-talking-points
title: Review Page Talking Points
audience: Team leads
sources:
  - Synthetic kit content
---
## Key Message
Results move to one review page on Monday.

## Why This Is Changing
Reviewers asked for one place to record results.

## What Changes for Your Team
Your team records results on the review page instead of email.

## Anticipated Questions
### Do old emails still count?
Yes, until Monday.
### Who answers questions?
The review lead.

## What to Ask Your Team to Do
Record one result on the page by Wednesday.
"""

if sel("FORMAT_RESOLVE"):
    rc, out = run(S("plan_material.py"), "badge card for UAT testers", "--out", "b.plan.json")
    p = json.load(open(os.path.join(TMP, "b.plan.json"))) if rc == 0 else {}
    check("D-09 FORMAT_RESOLVE unlisted 'badge card' borrows quick-reference-card (synthetic)", p.get("derived_from") == "quick-reference-card" and p.get("family") == "reference-sheet" and p.get("renderer", {}).get("id") == "doc-sheet", out)
    rc, out = run(S("plan_material.py"), "")
    check("D-09 FORMAT_RESOLVE empty format fails", rc == 1 and "FAIL [FORMAT_RESOLVE]" in out, out)
    rc, out = run(S("plan_material.py"), "QRG", "--out", "q.plan.json")
    check("D-09 FORMAT_RESOLVE alias 'QRG' is exact catalog entry", rc == 0 and json.load(open(os.path.join(TMP, "q.plan.json")))["format"] == "quick-reference-card", out)
    rc, out = run(S("plan_material.py"), "--retarget", "b.plan.json", "--as", "job aid", "--out", "j.plan.json")
    check("D-17 FORMAT_RESOLVE retarget to job aid lists carry-over and new sections", rc == 0 and "carry over: Get Help" in out and "write new: When to Use" in out, out)
    rc, out = run(S("plan_material.py"), "job aid", "--add-section", "Safety Note@When to Use", "--drop-section", "Check Your Work", "--set", "words=200", "--out", "o.plan.json")
    p = json.load(open(os.path.join(TMP, "o.plan.json")))
    check("D-17 FORMAT_RESOLVE per-request overrides change only this plan", [s["title"] for s in p["anatomy"]] == ["When to Use", "Safety Note", "Steps", "Get Help"] and p["words"] == 200 and "THIS REQUEST ONLY" in out, out)

if sel("CATALOG_SCHEMA", "CATALOG_CHANGE"):
    rc, out = run(S("catalog_tool.py"), "add", "huddle-card", "--family", "reference-sheet", "--label", "Huddle Card", "--like", "quick-reference-card", "--alias", "shift huddle card")
    check("D-17 CATALOG_CHANGE developer adds a format from an existing one", rc == 0 and "CATALOG_CHANGE saved" in out, out)
    rc, out = run(S("catalog_tool.py"), "section", "huddle-card", "add", "Talk Track", "--after", "At a Glance", "--limit", "items=2-4")
    rc2, out2 = run(S("catalog_tool.py"), "set", "job-aid", "pages=2", "words=500")
    rc3, out3 = run(S("plan_material.py"), "huddle card", "--out", "h.plan.json")
    p = json.load(open(os.path.join(TMP, "h.plan.json")))
    check("D-17 CATALOG_CHANGE section and limits change the next plan", rc == 0 and rc2 == 0 and p["format"] == "huddle-card" and [s["title"] for s in p["anatomy"]][1] == "Talk Track", out + out2 + out3)
    rc, out = run(S("catalog_tool.py"), "add", "bad-one", "--family", "no-such-family", "--label", "Bad One")
    check("D-17 CATALOG_SCHEMA unknown family is refused and overlay unchanged", rc == 1 and "FAIL [CATALOG_SCHEMA]" in out and "bad-one" not in open(OV).read(), out)
    rc, out = run(S("catalog_tool.py"), "alias", "job-aid", "add", "Quick Reference Card")
    check("D-17 CATALOG_SCHEMA duplicate name across formats is refused", rc == 1 and "FAIL [CATALOG_SCHEMA]" in out, out)
    rc, out = run(S("catalog_tool.py"), "retire", "faq-sheet", "--replaced-by", "one-pager")
    rc2, out2 = run(S("plan_material.py"), "faq-sheet", "--out", "f.plan.json")
    check("D-17 CATALOG_CHANGE retired format routes to its replacement", rc == 0 and json.load(open(os.path.join(TMP, "f.plan.json")))["format"] == "one-pager", out + out2)
    rc, out = run(S("catalog_tool.py"), "validate")
    check("D-17 CATALOG_SCHEMA merged catalog validates after developer changes", rc == 0 and "0 failed" in out, out)
    os.remove(OV)

if sel("ANATOMY_MATCH"):
    p = write("Record_Result_Job_Aid.md", JOB_AID)
    rc, out = run(S("plan_material.py"), "job aid", "--rename-section", "Get Help=Questions?", "--out", "ja.plan.json")
    rc, out = run(S("lint_material.py"), p, "--plan", "ja.plan.json")
    check("D-10 ANATOMY_MATCH complete job aid passes", rc == 0 and "0 failed" in out, out)
    write("Bad_Job_Aid.md", JOB_AID.replace("## Questions?\nAsk your review lead in the test channel.\n", ""))
    rc, out = run(S("lint_material.py"), "Bad_Job_Aid.md", "--plan", "ja.plan.json")
    check("D-10 ANATOMY_MATCH missing Questions? fails", rc == 1 and 'FAIL [ANATOMY_MATCH] Bad_Job_Aid.md: missing section "Questions?"' in out, out)
    write("Long_Steps.md", JOB_AID.replace("3. Record Pass or Fail for the step.", "\n".join("%d. Do step %d now." % (i, i) for i in range(3, 11))))
    rc, out = run(S("lint_material.py"), "Long_Steps.md", "--plan", "ja.plan.json")
    check("D-10 ANATOMY_MATCH step limit enforced", rc == 1 and "has 10 steps (allowed 2-8)" in out, out)

if sel("DERIVED_NOTE"):
    run(S("plan_material.py"), "badge card for UAT testers", "--out", "b.plan.json")
    body = "---\nformat: badge card\ntitle: UAT Badge Card\naudience: UAT testers\n%ssources:\n  - Synthetic\n---\n## At a Glance\nTest one step at a time.\n\n## Common Tasks\n- Record a result.\n- Add a note.\n\n## Get Help\nAsk your review lead.\n"
    write("Badge.md", body % ""); rc, out = run(S("lint_material.py"), "Badge.md", "--plan", "b.plan.json")
    check("D-09 DERIVED_NOTE derived format without derived_from fails", rc == 1 and "FAIL [DERIVED_NOTE]" in out, out)
    write("Badge2.md", body % "derived_from: quick-reference-card\n"); rc, out = run(S("lint_material.py"), "Badge2.md", "--plan", "b.plan.json")
    check("D-09 DERIVED_NOTE derived format with derived_from passes", rc == 0, out)

if sel("RENAMED_TERM"):
    run(S("catalog_tool.py"), "rename", "quick-start", "--label", "Starter Sheet")
    write("Ren.md", JOB_AID.replace("Use this when", "See the Quick Start. Use this when"))
    rc, out = run(S("lint_material.py"), "Ren.md")
    check("D-17 RENAMED_TERM old label after a developer rename fails", rc == 1 and "FAIL [RENAMED_TERM]" in out, out)
    os.remove(OV); rc, out = run(S("lint_material.py"), "Ren.md")
    check("D-17 RENAMED_TERM without a rename passes", "RENAMED_TERM" not in out, out)

SHARED = [("SLOP_OPENER", "Exciting news! "), ("PLACEHOLDER", "Owner: TBD. "), ("FILLER", "This will unlock speed. "),
          ("PHI_PATTERN", "MRN: 1234567 "), ]
for code, ins in SHARED:
    if sel(code):
        write("S_%s.md" % code, EMAIL.replace("Reviewers asked", ins + "Reviewers asked"))
        rc, out = run(S("lint_material.py"), "S_%s.md" % code)
        check("D-10 %s planted text fails" % code, rc == 1 and "FAIL [%s]" % code in out, out)
        rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL))
        check("D-10 %s clean email passes" % code, rc == 0 and code not in out, out)
if sel("FILLER"):
    pn = EMAIL.replace("Reviewers asked", "The Bottleneck Deep Dive dashboard is ready. Reviewers asked")
    write("Pn_bad.md", pn)
    rc, out = run(S("lint_material.py"), "Pn_bad.md")
    check("D-91 FILLER inside an undeclared name still fails", rc == 1 and "FAIL [FILLER]" in out, out)
    write("Pn_ok.md", pn.replace("---\n", "---\nproper_names:\n  - Bottleneck Deep Dive\n", 1))
    rc, out = run(S("lint_material.py"), "Pn_ok.md")
    check("D-91 FILLER skips a declared proper name (front matter proper_names)", rc == 0 and "FILLER" not in out, out)
    write("Pn_mixed.md", pn.replace("---\n", "---\nproper_names:\n  - Bottleneck Deep Dive\n", 1).replace("Reviewers asked", "Let us deep dive. Reviewers asked"))
    rc, out = run(S("lint_material.py"), "Pn_mixed.md")
    check("D-91 FILLER outside the declared name still fails", rc == 1 and "FAIL [FILLER]" in out, out)
if sel("SUBJECT_LENGTH"):
    write("Subj.md", EMAIL.replace("The new review page opens Monday", "The new review page opens Monday and here is everything about it"))
    rc, out = run(S("lint_material.py"), "Subj.md")
    check("D-12 SUBJECT_LENGTH long subject fails", rc == 1 and "FAIL [SUBJECT_LENGTH]" in out, out)
    rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL)); check("D-12 SUBJECT_LENGTH short subject passes", rc == 0, out)
if sel("WORD_LIMIT"):
    write("Wl.md", EMAIL.replace("Reviewers asked for one place to record results.", "Reviewers asked for one place to record results. " * 40))
    rc, out = run(S("lint_material.py"), "Wl.md"); check("D-10 WORD_LIMIT over 250 words fails", rc == 1 and "FAIL [WORD_LIMIT]" in out, out)
    rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL)); check("D-10 WORD_LIMIT short email passes", rc == 0, out)
if sel("TITLE_CASE"):
    write("Tc.md", EMAIL.replace("## What to Do", "## what to do"))
    rc, out = run(S("lint_material.py"), "Tc.md"); check("D-10 TITLE_CASE lower-case heading fails", rc == 1 and "FAIL [TITLE_CASE]" in out, out)
    rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL)); check("D-10 TITLE_CASE Proper Case passes", rc == 0, out)
if sel("SOURCES_MISSING", "FRONT_MATTER"):
    write("Nos.md", EMAIL.replace("sources:\n  - Synthetic kit content\n", "").replace("audience: Report reviewers\n", ""))
    rc, out = run(S("lint_material.py"), "Nos.md")
    check("D-10 SOURCES_MISSING and FRONT_MATTER fail without sources and audience", rc == 1 and "FAIL [SOURCES_MISSING]" in out and "FAIL [FRONT_MATTER]" in out, out)
    rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL)); check("D-10 SOURCES_MISSING complete front matter passes", rc == 0, out)

ADOPT_PIECE = {"label": "Adoption Measures", "file": "adopt.json", "piece": "adoption-measures", "audience": "Team leads", "channel": "review meeting", "adkar": "reinforcement", "send_date": "2026-11-02", "owner": "Change lead"}
ADOPT = {"measures": [{"measure": "Reviewers who recorded a result on the review page", "source": "Review page result counts (synthetic)", "review_date": "2026-11-02",
                       "target": "Every reviewer", "target_source": "Synthetic launch plan"},
                      {"measure": "Results still sent by email", "source": "Shared inbox count (synthetic)", "review_date": "2026-11-02"}]}
if sel("KIT_COVERAGE", "KIT_ADOPTION"):
    json.dump(ADOPT, open(os.path.join(TMP, "adopt.json"), "w"))
if sel("KIT_COVERAGE"):
    write("email.md", EMAIL); write("talk.md", TALK)
    kit = {"title": "Review Page Launch Kit", "change": "Results move to one review page", "audience": "Report reviewers",
           "names": {"review page": ["review portal", "results site"]},
           "pieces": [{"label": "Announcement Email", "file": "email.md", "piece": "announcement-email", "audience": "Reviewers", "channel": "email", "adkar": "awareness", "send_date": "2026-10-19", "owner": "Change lead"},
                      {"label": "Manager Talking Points", "file": "talk.md", "piece": "manager-talking-points", "audience": "Team leads", "channel": "huddle", "adkar": "desire", "send_date": "2026-10-16", "owner": "Change lead"},
                      ADOPT_PIECE]}  # D-47: a complete kit carries an adoption-measures piece
    json.dump(kit, open(os.path.join(TMP, "kit.json"), "w"))
    rc, out = run(S("lint_material.py"), "--kit", "kit.json")
    check("D-12 KIT_COVERAGE complete kit passes (ADKAR gaps warn only)", rc == 0 and "WARN [KIT_COVERAGE] no piece for ADKAR" in out, out)
    write("email.md", EMAIL.replace("## What Changes for You\nYou record results on the review page instead of email.\n", "").replace("review page on Monday", "review portal on Monday"))
    rc, out = run(S("lint_material.py"), "--kit", "kit.json")
    check("D-12 KIT_COVERAGE email without reader impact and with a variant name fails", rc == 1 and 'Announcement Email: no "What Changes for You"' in out and "says 'review portal'" in out, out)

if sel("KIT_ADOPTION"):
    rc, out = run(S("lint_material.py"), "--kit", os.path.join(SKILL, "assets", "exemplars", "change-kit.kit.json"))
    check("D-47 KIT_ADOPTION change-kit exemplar with its adoption-measures piece: 0 failed", rc == 0 and "KIT_ADOPTION" not in out and "6 file(s), 0 failed" in out, out)
    write("email.md", EMAIL); write("talk.md", TALK)
    base = {"title": "Review Page Launch Kit", "change": "Results move to one review page", "audience": "Report reviewers",
            "pieces": [{"label": "Announcement Email", "file": "email.md", "piece": "announcement-email", "audience": "Reviewers", "channel": "email", "adkar": "awareness", "send_date": "2026-10-19", "owner": "Change lead"}]}
    json.dump(base, open(os.path.join(TMP, "k0.json"), "w"))
    rc, out = run(S("lint_material.py"), "--kit", "k0.json")
    check("D-47 KIT_ADOPTION synthetic kit with no adoption-measures piece fails", rc == 1 and "FAIL [KIT_ADOPTION] kit has no adoption-measures piece (reinforcement stage)" in out, out)
    bad = {"measures": [{"measure": "Reviewers who recorded a result", "source": "Review page counts (synthetic)", "target": "Every reviewer"}]}
    json.dump(bad, open(os.path.join(TMP, "adopt_bad.json"), "w"))
    json.dump(dict(base, pieces=base["pieces"] + [dict(ADOPT_PIECE, file="adopt_bad.json", adkar="knowledge")]), open(os.path.join(TMP, "k1.json"), "w"))
    rc, out = run(S("lint_material.py"), "--kit", "k1.json")
    check("D-47 KIT_ADOPTION synthetic piece in the wrong stage, with no review date and an unsourced target fails", rc == 1 and "ADKAR stage 'knowledge' (adoption measures belong in reinforcement)" in out
          and "measure 1 missing review_date" in out and "measure 1 has a target with no target_source" in out, out)
    md = "# Adoption Measures\n\n## What We Measure\nReviewers who recorded a result.\n\n## Where It Comes From\nReview page counts (synthetic).\n\n## Review Date\n2026-11-02\n\n## Target\nEvery reviewer.\n%s"
    write("adopt_bad.md", md % ""); write("adopt_ok.md", md % "\n## Target Source\nSynthetic launch plan.\n")
    res = []
    for fn in ("adopt_bad.md", "adopt_ok.md"):
        json.dump(dict(base, pieces=base["pieces"] + [dict(ADOPT_PIECE, file=fn)]), open(os.path.join(TMP, "k2.json"), "w"))
        res.append(run(S("lint_material.py"), "--kit", "k2.json"))
    check("D-47 KIT_ADOPTION synthetic Markdown piece with a Target but no Target Source fails; with one, no KIT_ADOPTION failure", 'a target with no "Target Source"' in res[0][1]
          and "FAIL [KIT_ADOPTION]" not in res[1][1], res[0][1] + res[1][1])

if sel("ILT_PAIR"):
    guide = "---\nformat: facilitator-guide\ntitle: Review Page Session\naudience: Team leads\nduration_min: 60\nsources:\n  - Synthetic\n---\n## Agenda\n| Module | Minutes |\n|---|---|\n| Welcome | 10 |\n| Walkthrough | %d |\n| Practice | 20 |\n\n## Modules\n### Walkthrough\nCheck: Where do you record a result?\nAnswer: On the review page.\n%s"
    deck = {"slides": [{"role": "retrieval"}, {"role": "answer"}, {"role": "retrieval"}, {"role": "answer"}]}
    json.dump(deck, open(os.path.join(TMP, "deck.json"), "w"))
    write("g_ok.md", guide % (30, "Check: What do you add when a step fails?\nAnswer: A note.\n"))
    rc, out = run(S("lint_material.py"), "--ilt", "g_ok.md", "--deck", "deck.json")
    check("D-15 ILT_PAIR matched guide and deck pass", rc == 0, out)
    deck["slides"].append({"role": "retrieval"}); json.dump(deck, open(os.path.join(TMP, "deck.json"), "w"))
    write("g_bad.md", guide % (45, "Check: What do you add when a step fails?\nAnswer: A note.\n"))
    rc, out = run(S("lint_material.py"), "--ilt", "g_bad.md", "--deck", "deck.json")
    check("D-15 ILT_PAIR 75 of 60 minutes and an unmatched retrieval slide fail", rc == 1 and "agenda sums to 75 of 60 min" in out and "retrieval slide 5 has no guide Check" in out, out)

if sel("STYLE_DRIFT"):
    rc, out = run(S("style_tokens.py"), "check")
    check("D-11 STYLE_DRIFT shipped themes match", rc == 0 and "0 failed" in out, out)
    fb = json.load(open(os.path.join(SKILL, "assets", "style_tokens.json"), encoding="utf-8"))["fallback_colors"]
    dk, dc = os.path.join(TMP, "theme.json"), os.path.join(TMP, "doc_theme.json")
    json.dump({"colors": dict(fb, alert="D9480E")}, open(dk, "w"))  # synthetic sibling themes
    json.dump({"colors": dict(fb)}, open(dc, "w"))
    rc, out = run(S("style_tokens.py"), "check", "--deck-theme", dk, "--doc-theme", dc)
    check("D-11 STYLE_DRIFT changed deck alert color fails (synthetic themes)", rc == 1 and "FAIL [STYLE_DRIFT] alert: deck D9480E, fallback %s" % fb["alert"] in out
          and "1 failed" in out, out)
    json.dump({"colors": dict(fb, navy=fb["dark"])}, open(dk, "w"))
    rc, out = run(S("style_tokens.py"), "check", "--deck-theme", dk, "--doc-theme", dc)
    check("D-11 STYLE_DRIFT matching synthetic themes pass (legacy keys map to roles)", rc == 0 and "STYLE_DRIFT: 0 failed" in out, out)
    bad = dict(json.load(open(os.path.join(SKILL, "assets", "style_tokens.json"), encoding="utf-8"))); bad["fallback_colors"] = dict(fb, primary="0069B2")
    bt = os.path.join(TMP, "tokens_bad.json"); json.dump(bad, open(bt, "w"))
    rc, out = run(S("style_tokens.py"), "check", "--out", bt, "--deck-theme", dc, "--doc-theme", dc)
    check("D-11 STYLE_DRIFT shipped fallback that differs from brand.py's neutral defaults fails", rc == 1 and "fallback primary: tokens 0069B2, brand.py neutral %s" % fb["primary"] in out, out)

if sel("ANATOMY_MATCH"):
    rep = {"meta": {"title": "Example Readout", "doc_type": "report", "audience": "Leaders", "sources": ["Synthetic"]},
           "sections": [{"title": t, "blocks": [{"type": "paragraph", "text": "Synthetic text for %s." % t}]} for t in ["Executive Summary", "Background", "Findings", "Recommendations", "Next Steps"]]}
    json.dump(rep, open(os.path.join(TMP, "rep.doc.json"), "w"))
    run(S("plan_material.py"), "post-implementation review", "--out", "pir.plan.json")
    rc, out = run(S("lint_material.py"), "rep.doc.json", "--plan", "pir.plan.json")
    check("D-19 ANATOMY_MATCH long-form report checks top-level sections (portfolio defect regression)", rc == 0, out)
    rep["sections"].pop(); json.dump(rep, open(os.path.join(TMP, "rep.doc.json"), "w"))
    rc, out = run(S("lint_material.py"), "rep.doc.json", "--plan", "pir.plan.json")
    check("D-19 ANATOMY_MATCH long-form report missing Next Steps fails", rc == 1 and 'missing section "Next Steps"' in out, out)
    form = {"meta": {"title": "Example Sign-off Form", "kind": "form", "audience": "Partners", "purpose": "Record sign-off.", "owner": "BI team", "version": "1.0", "date": "2026-10-11", "sources": ["Synthetic"]},
            "sections": [{"title": "Sign-off", "items": [{"id": "Q1", "type": "text", "label": "Dashboard name", "required": True}]}]}
    json.dump(form, open(os.path.join(TMP, "f.form.json"), "w"))
    rc, out = run(S("lint_material.py"), "f.form.json")
    check("D-19 ANATOMY_MATCH form.json routes to build_form --check, not the document rules (portfolio defect regression)", "build_form.py --check" in out and "missing section" not in out, out)

if sel("EXEMPLARS"):
    cat = json.load(open(os.path.join(SKILL, "references", "format-catalog.json")))
    miss = []
    for fid, f in cat["formats"].items():
        ex = f.get("exemplar")
        if ex and ex.startswith("assets/") and not os.path.exists(os.path.join(SKILL, ex)):
            miss.append(fid + ": " + ex)
    check("D-09 EXEMPLARS every composer exemplar named in the catalog ships", not miss, "; ".join(miss))
    md = [os.path.join(SKILL, "assets", "exemplars", x) for x in sorted(os.listdir(os.path.join(SKILL, "assets", "exemplars"))) if x.endswith(".md")]
    rc, out = run(S("lint_material.py"), *md) if md else (1, "no exemplars")
    check("D-09 EXEMPLARS Markdown exemplars pass the gate", rc == 0, out)

INST = dict(os.environ, MATERIAL_OVERLAY=os.path.join(SKILL, "assets", "catalog", "overlay.json"))
FIX = os.path.join(SKILL, "assets", "fixtures")
LINT_DOC = os.path.join(os.path.dirname(SKILL), "document-builder", "scripts", "lint_doc.py")


def run_env(env, *args):
    r = subprocess.run([PY] + list(args), capture_output=True, text=True, cwd=TMP, env=env)
    return r.returncode, r.stdout + r.stderr


if sel("MATCH_CONFIDENCE"):
    for fmt in ("poster", "certificate", "infographic"):
        rc, out = run_env(INST, S("plan_material.py"), fmt, "--audience", "non-technical business users", "--subject", "denials dashboard", "--out", "m.plan.json")
        check("D-36 MATCH_CONFIDENCE '%s' is a low match with the neutral outline" % fmt, rc == 0 and "MATCH: low (" in out and "WARN [MATCH_CONFIDENCE]" in out
              and "SECTIONS: Purpose | Key Points | What to Do | Get Help" in out and "Who It's For" not in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "certificate", "--ask")
    check("D-36 MATCH_CONFIDENCE --ask prints one question and no plan", rc == 0 and "QUESTION: Is this closer to a one-pager, a reference table or a long document?" in out and "PLAN:" not in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "job aid", "--out", "m2.plan.json")
    rc2, out2 = run_env(INST, S("plan_material.py"), "playbook", "--out", "m3.plan.json")  # D-44: policy is its own format now
    check("D-36 MATCH_CONFIDENCE exact and family-default matches do not warn", "MATCH: exact (1.0)" in out and "MATCH_CONFIDENCE" not in out + out2
          and "MATCH: derived family (long-form default sop)" in out2, out + out2)

if sel("WHATS_NEW"):
    rc, out = run(S("catalog_tool.py"), "card", "--out", os.path.join(TMP, "card.doc.json"))
    d = json.load(open(os.path.join(TMP, "card.doc.json")))
    rows = d["sections"][0]["sections"][0]["blocks"][1]["rows"]
    n = sum(len(r[1].split(", ")) for r in rows)
    check("D-98 WHATS_NEW card lists every live format by family", rc == 0 and "card: %d formats" % n in out and d["meta"]["doc_type"] == "quick-reference-card", out)
    plan = os.path.join(TMP, "qrc.plan.json"); run(S("plan_material.py"), "quick reference card", "--audience", "Everyone", "--subject", "formats", "--out", plan)
    rc, out = run(S("lint_material.py"), os.path.join(TMP, "card.doc.json"), "--plan", plan)
    check("D-98 WHATS_NEW card passes the composer gate", rc == 0 and "0 failed" in out, out)
if sel("CATALOG_SCHEMA"):
    rc, out = run_env(INST, S("catalog_tool.py"), "validate")
    check("D-37 CATALOG_SCHEMA installed overlay validates (48 + Policy since D-44 + Tracker since D-53)", rc == 0 and "CATALOG: 50 formats, 8 families, 0 failed" in out, out)
    same, low, bad = 0, 0, []
    after_d44 = {"policy": "FORMAT: Policy (long-form) BUILD: document-builder -> pdf, docx"}  # intended: D-44 Policy format
    for line in open(os.path.join(FIX, "D-37.routing_after.txt"), encoding="utf-8"):
        req, exp = line.rstrip("\n").split(" => ", 1)
        exp = after_d44.get(req, exp)
        rc, out = run_env(INST, S("plan_material.py"), req, "--out", "r.plan.json")
        got = " ".join(x for x in out.splitlines() if x.startswith(("FORMAT:", "BUILD:")))
        if got.strip() == exp.strip():
            same += 1
        elif "MATCH: low (" in out:
            low += 1
        else:
            bad.append(req)
    check("D-37 CATALOG_SCHEMA routing matches routing_after.txt (24 same, 5 low after D-36; policy own format after D-44)", same == 24 and low == 5 and not bad, "same %d low %d other %s" % (same, low, bad))
    ov = json.load(open(INST["MATERIAL_OVERLAY"])); ov["formats"]["memo"]["family"] = "no-such-family"
    json.dump(ov, open(os.path.join(TMP, "bad_overlay.json"), "w"))
    rc, out = run_env(dict(os.environ, MATERIAL_OVERLAY=os.path.join(TMP, "bad_overlay.json")), S("catalog_tool.py"), "validate")
    check("D-37 CATALOG_SCHEMA overlay with an unknown family fails (synthetic)", rc == 1 and "FAIL [CATALOG_SCHEMA] memo: unknown family no-such-family" in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "policy", "--subject", "report access", "--out", "d44.plan.json")
    dt = json.load(open(os.path.join(TMP, "d44.plan.json"))).get("doc_type") if rc == 0 else None
    check("D-44 CATALOG_SCHEMA policy is its own long-form format on doc type policy", rc == 0 and "FORMAT: Policy (long-form)\n" in out and "borrowed from" not in out
          and "MATCH: exact" in out and "SECTIONS: Purpose | Scope | Policy Statement | Roles and Responsibilities | Definitions | Exceptions | Related Documents" in out and dt == "policy", out)
    cp = os.path.join(TMP, "skill_nopolicy"); shutil.copytree(SKILL, cp, ignore=shutil.ignore_patterns("__pycache__"))
    cj = os.path.join(cp, "references", "format-catalog.json"); c = json.load(open(cj)); c["formats"].pop("policy"); json.dump(c, open(cj, "w"))
    th = os.path.join(os.path.dirname(SKILL), "document-builder", "assets", "doc_theme.json")
    rc, out = run_env(dict(INST, MATERIAL_DOC_THEME=th), os.path.join(cp, "scripts", "plan_material.py"), "policy", "--out", "d44b.plan.json")
    check("D-44 CATALOG_SCHEMA synthetic catalog without the Policy format borrows from sop again", rc == 0 and "borrowed from sop" in out and "MATCH: derived family" in out, out)

if sel("AUDIENCE_PROFILE"):
    rc, out = run_env(INST, S("plan_material.py"), "chat post", "--audience-profile", "physicians", "--out", "cp.plan.json")
    check("D-38 AUDIENCE_PROFILE physicians chat post limits", rc == 0 and "LIMITS: title <= 10 words, body <= 100 words (common physician communication practice)" in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "chat post", "--audience-profile", "business", "--out", "cb.plan.json")
    check("D-38 AUDIENCE_PROFILE business chat post 120 words, terms defined, no system or tool names", rc == 0 and "LIMITS: words 120" in out
          and "define every term at first use; no system or tool names" in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "chat post", "--audience-profile", "nurses")
    check("D-38 AUDIENCE_PROFILE unknown profile fails", rc == 1 and "FAIL [AUDIENCE_PROFILE] unknown profile 'nurses'" in out, out)
    post = "---\nformat: chat-post\ntitle: %s\naudience: Physicians\nsources:\n  - Synthetic\n---\n## What Changed\nThe denials view now opens on the summary.\n\n## What to Do\nOpen the view and pick your center.\n\n## Get Help\nReply in this channel.\n"
    p = json.load(open(os.path.join(TMP, "cp.plan.json"))); p["anatomy"] = [{"title": t} for t in ("What Changed", "What to Do", "Get Help")]
    json.dump(p, open(os.path.join(TMP, "cp2.plan.json"), "w"))
    write("Cp_long.md", post % "The Denials View Now Opens on the Summary Page for Every Center Today")
    rc, out = run_env(INST, S("lint_material.py"), "Cp_long.md", "--plan", "cp2.plan.json")
    write("Cp_ok.md", post % "Denials View Opens on the Summary")
    rc2, out2 = run_env(INST, S("lint_material.py"), "Cp_ok.md", "--plan", "cp2.plan.json")
    check("D-38 AUDIENCE_PROFILE physicians title over 10 words fails, short title passes (synthetic)", rc == 1 and "title is 13 words (maximum 10 for the physicians profile)" in out and rc2 == 0, out + out2)

if sel("TERM_BRAND"):
    rc, out = run_env(INST, S("plan_material.py"), "announcement email", "--drop-section", "What Changes for You", "--drop-section", "What to Do", "--drop-section", "Get Help", "--out", "d39.plan.json")
    rc, out = run_env(INST, S("lint_material.py"), os.path.join(FIX, "D-39.input.md"), "--plan", "d39.plan.json")
    base = ['"Jan 17th -> Jan. 17"', '"Over 40 -> More than 40"']
    check("D-39 TERM_BRAND fixture, no project brand: the 2 shared AP rules warn, gate still 0 failed", rc == 0 and out.count("WARN [TERM_BRAND]") == 2
          and all(w in out for w in base) and "1 file(s), 0 failed" in out, out)
    hp = os.path.join(TMP, "house_project"); os.makedirs(hp, exist_ok=True)
    shutil.copy(os.path.join(FIX, "D-39.input.md"), hp)
    json.dump({"name": "NorthStar", "terminology": "house.json"}, open(os.path.join(hp, "brand.json"), "w"))
    json.dump({"format": "terminology", "sets": {"internal": [
        {"id": "product", "kind": "case", "word": "NorthStar", "why": "product name"},
        {"id": "roles", "kind": "midsentence", "pattern": "\\bAnalysts\\b", "why": "job titles lowercase mid-sentence"},
        {"id": "email", "kind": "regex", "pattern": "\\be-mail\\b", "suggest": "email", "why": "house style"}]}}, open(os.path.join(hp, "house.json"), "w"))
    rc, out = run_env(INST, S("lint_material.py"), os.path.join(hp, "D-39.input.md"), "--plan", "d39.plan.json")
    want = base + ['"Northstar -> NorthStar"', '"Analysts -> analysts"', '"e-mail -> email"']
    check("D-39 TERM_BRAND fixture with the project's house terms (brand.json terminology): 5 off-style terms warn, gate still 0 failed",
          rc == 0 and out.count("WARN [TERM_BRAND]") == 5 and all(w in out for w in want) and "1 file(s), 0 failed" in out, out)
    rc, out = run(S("lint_material.py"), write("S_ok.md", EMAIL))
    check("D-39 TERM_BRAND on-brand email has no TERM_BRAND warning", rc == 0 and "TERM_BRAND" not in out, out)

if sel("COMMS_CHECK"):
    sk = os.path.join(TMP, "skills"); os.makedirs(os.path.join(sk, "executive-communications", "scripts"), exist_ok=True)
    stub = os.path.join(sk, "executive-communications", "scripts", "check_comms.py")
    write("C_email.md", EMAIL)
    rc, out = run_env(dict(ENV, MATERIAL_SKILLS_DIR=os.path.join(TMP, "none")), S("lint_material.py"), "C_email.md")
    check("D-40 COMMS_CHECK not installed warns not run (no FAIL)", rc == 0 and "WARN [COMMS_CHECK] C_email.md: not run (executive-communications not installed)" in out, out)
    open(stub, "w").write("import sys\nopen(%r, 'w').write(' '.join(sys.argv[1:]))\nprint('CHECK_COMMS: 1 file(s), 0 failed')\n" % os.path.join(TMP, "args.txt"))
    write("src.md", "Synthetic source draft."); write("facts.json", "{}")
    rc, out = run_env(dict(ENV, MATERIAL_SKILLS_DIR=sk), S("lint_material.py"), "C_email.md", "--source", "src.md", "--facts", "facts.json")
    args = open(os.path.join(TMP, "args.txt")).read() if os.path.isfile(os.path.join(TMP, "args.txt")) else ""
    check("D-40 COMMS_CHECK installed stub runs with --kind email, --source and --facts (synthetic stub)", rc == 0 and "COMMS_CHECK: check_comms email, 0 failed" in out
          and "--kind email --source src.md --facts facts.json" in args, out + args)
    open(stub, "w").write("import sys\nsys.exit(3)\n")
    rc, out = run_env(dict(ENV, MATERIAL_SKILLS_DIR=sk), S("lint_material.py"), "C_email.md")
    check("D-40 COMMS_CHECK installed but no result fails (synthetic stub)", rc == 1 and "FAIL [COMMS_CHECK] C_email.md: check_comms email did not report a result (exit 3)" in out, out)

if sel("PLAN_GATES"):
    _b = open(os.path.join(FIX, "D-41.input.md"), encoding="utf-8").read()
    fmt = next(l.split(":", 1)[1].strip() for l in _b.splitlines() if l.startswith("format:"))
    rc, out = run_env(INST, S("plan_material.py"), fmt, "--out", "vs.plan.json")
    gates = next((l for l in out.splitlines() if l.startswith("GATES:")), "")
    check("D-41 PLAN_GATES video script fixture lists the training gate, no e-learning gates", rc == 0 and "BUILD: training-material-designer -> md" in out
          and "lint_training" in gates and not any(g in gates for g in ("ELEARN_INTERACTION", "ELEARN_OBJECTIVE", "ELEARN_OFFLINE")), out)
    rc, out = run_env(INST, S("plan_material.py"), "e-learning module", "--out", "el.plan.json")
    check("D-41 PLAN_GATES e-learning module (module renderer) keeps the e-learning gates", rc == 0 and "ELEARN_INTERACTION" in out and "lint_training" not in out, out)

if sel("DOC_TYPE"):
    th = json.load(open(os.path.join(os.path.dirname(SKILL), "document-builder", "assets", "doc_theme.json"))) if os.path.isfile(LINT_DOC) else {"doc_types": {"sop": {}}}
    th["doc_types"].setdefault("playbook", {"required": []}); json.dump(th, open(os.path.join(TMP, "th_pol.json"), "w"))
    th["doc_types"].pop("playbook"); json.dump(th, open(os.path.join(TMP, "th_nopol.json"), "w"))
    for tag, tf, want in (("lists playbook (synthetic theme)", "th_pol.json", "playbook"), ("has no playbook", "th_nopol.json", "sop")):  # D-44 moved from policy
        rc, out = run_env(dict(INST, MATERIAL_DOC_THEME=os.path.join(TMP, tf)), S("plan_material.py"), "playbook", "--out", "pol.plan.json")
        dt = json.load(open(os.path.join(TMP, "pol.plan.json")))["doc_type"] if rc == 0 else None
        d = json.load(open(os.path.join(FIX, "D-43.input.json"))); d["meta"]["doc_type"] = dt
        json.dump(d, open(os.path.join(TMP, "d43.doc.json"), "w"))
        if os.path.isfile(LINT_DOC) and dt in json.load(open(os.path.join(os.path.dirname(SKILL), "document-builder", "assets", "doc_theme.json")))["doc_types"]:
            rc2, out2 = run_env(INST, LINT_DOC, "d43.doc.json", "--draft")
        else:
            rc2, out2 = 0, "lint_doc not run: builder type %s not installed (UNVERIFIED)" % dt; print("skip " + out2)
        check("D-43 DOC_TYPE builder %s -> plan doc_type %s; fixture lint_doc has no DOC_TYPE failure" % (tag, want), dt == want and "borrowed from sop" in out and "[DOC_TYPE]" not in out + out2, out + out2)
    json.dump({"doc_types": {"user-guide": {}}}, open(os.path.join(TMP, "th_min.json"), "w"))
    rc, out = run_env(dict(INST, MATERIAL_DOC_THEME=os.path.join(TMP, "th_min.json")), S("plan_material.py"), "playbook", "--out", "pol2.plan.json")
    rc2, out2 = run_env(INST, S("plan_material.py"), "glossary card", "--out", "gc.plan.json")
    check("D-43 DOC_TYPE unbuildable doc_type warns (synthetic theme); derived sheet keeps its kebab id", "WARN [DOC_TYPE] doc_type sop is not a document builder type" in out
          and json.load(open(os.path.join(TMP, "gc.plan.json")))["doc_type"] == "glossary-card", out + out2)

if sel("TRANSLATION_READY"):
    rc, out = run_env(INST, S("plan_material.py"), "job aid", "--out", "t0.plan.json")
    rc2, out2 = run_env(INST, S("plan_material.py"), "job aid", "--translation-ready", "--out", "t1.plan.json")
    check("D-61 TRANSLATION_READY job aid budget drops to 75 percent and the plan names the written translation process", "LIMITS: words 250" in out and "TRANSLATION" not in out
          and "LIMITS: words 187" in out2 and "never machine translation" in out2 and "approved translation vendor" in out2 and "purchase order" in out2, out + out2)
    src = {"meta": {"title": "Record a Result", "doc_type": "job-aid", "layout": "sheet", "audience": "UAT testers", "sources": ["Synthetic"]},
           "sections": [{"title": "Steps", "blocks": [{"type": "procedure", "steps": [{"text": "Open the test.", "image": "x.png"}, {"text": "Record the result."}]},
                                                      {"type": "figure", "image": "y.png", "caption": "Synthetic results screen", "alt": "Synthetic results screen image"},
                                                      {"type": "faq", "items": [{"q": "Who checks it?", "a": "The review lead."}]}]}]}
    json.dump(src, open(os.path.join(TMP, "Record.doc.json"), "w"))
    rc, out = run_env(INST, S("plan_material.py"), "job aid", "--translation-ready", "--source", "Record.doc.json", "--out", "t2.plan.json")
    fp = os.path.join(TMP, "Record_for_translation.docx"); txt, shapes = "", -1
    if os.path.isfile(fp):
        import docx
        dd = docx.Document(fp); txt = " ".join(p.text for p in dd.paragraphs); shapes = len(dd.inline_shapes)
    check("D-61 TRANSLATION_READY writes a text-only <Name>_for_translation.docx (synthetic source)", rc == 0 and "TRANSLATION EXPORT:" in out and shapes == 0
          and "Record the result." in txt and "The review lead." in txt and "2 images left out" in out, out)

if sel("ANATOMY_MATCH"):
    run_env(INST, S("plan_material.py"), "status report", "--out", "sr.plan.json")
    rc, out = run_env(INST, S("lint_material.py"), os.path.join(FIX, "D-45.input.json"), "--plan", "sr.plan.json")
    miss = ['missing section "%s"' % t for t in ("Overall Status", "Milestones", "Risks, Issues and Asks")]
    check("D-45 ANATOMY_MATCH fixture (old status-report exemplar) with the overlay plan: 3 FAIL", rc == 1 and out.count("FAIL [ANATOMY_MATCH]") == 3
          and all(m in out for m in miss) and "1 file(s), 3 failed" in out, out)
    srx = os.path.join(SKILL, "assets", "exemplars", "status-report.doc.json")
    rc, out = run_env(INST, S("lint_material.py"), srx, "--plan", "sr.plan.json")
    check("D-45 ANATOMY_MATCH new status-report exemplar LINT_MATERIAL 0 failed", rc == 0 and "1 file(s), 0 failed" in out, out)
    if os.path.isfile(LINT_DOC):
        rc, out = run_env(INST, LINT_DOC, srx)
        check("D-45 ANATOMY_MATCH new status-report exemplar lint_doc 0 failed", rc == 0 and ", 0 failed" in out, out)
    else:
        print("skip D-45 ANATOMY_MATCH lint_doc: document-builder not installed (UNVERIFIED)")

def fmd(fmt, title, secs, extra=""):
    """Synthetic Markdown piece for the D-54..D-60 format rules."""
    return ("---\nformat: %s\ntitle: %s\naudience: Billing specialists\n%ssources:\n  - Synthetic test content\n---\n# %s\n\n" % (fmt, title, extra, title)
            + "\n".join("## %s\n%s\n" % (t, b) for t, b in secs))


def flint(fname, text, *extra):
    p = write(fname, text) if not isinstance(text, dict) else (json.dump(text, open(os.path.join(TMP, fname), "w")) or os.path.join(TMP, fname))
    return run_env(dict(INST, MATERIAL_SKILLS_DIR=os.path.join(TMP, "none")), S("lint_material.py"), p, *extra)


def tbl(hdr, rows):
    return "\n".join("| " + " | ".join(r) + " |" for r in [hdr, ["---"] * len(hdr)] + rows)


if sel("RACI_ONE_A"):
    RH = ["Activity", "Billing Specialist", "Team Lead", "Finance Analyst"]
    def raci(rows):
        return fmd("raci", "Refund Approval Roles", [("Purpose", "Shows who does each step of a synthetic refund."), ("Roles", "Billing specialist, team lead, finance analyst."),
                                                     ("RACI Matrix", tbl(RH, rows)), ("How to Use This Chart", "Find the activity, then read across."), ("Get Help", "Ask your team lead.")])
    rc, out = flint("raci_bad.md", raci([["Review the request", "R", "A", "C"], ["Approve the refund", "R", "A", "A"], ["Send the notice", "I", "A", "C"]]))
    check("D-54 RACI_ONE_A synthetic two A's in one row and no R in another: 2 FAIL lines naming the rows", rc == 1 and out.count("FAIL [RACI_ONE_A]") == 2
          and 'FAIL [RACI_ONE_A] raci_bad.md: "Approve the refund" has 2 Accountable roles (needs exactly one)' in out
          and 'FAIL [RACI_ONE_A] raci_bad.md: "Send the notice" has no Responsible role' in out, out)
    rc, out = flint("raci_ok.md", raci([["Review the request", "R", "A", "C"], ["Approve the refund", "R/A", "Consulted", "I"], ["Send the notice", "Responsible", "A, C", "-"]]))
    check("D-54 RACI_ONE_A synthetic clean RACI ('R/A', 'A, C', full words) passes", rc == 0 and "RACI_ONE_A" not in out and "0 failed" in out, out)
    def raci_doc(rows):
        P = lambda t, x: {"title": t, "blocks": [{"type": "paragraph", "text": x}]}
        return {"meta": {"title": "Refund Approval Roles", "doc_type": "raci", "layout": "sheet", "audience": "Billing specialists", "sources": ["Synthetic test content"]},
                "sections": [{"title": "Refund Roles", "sections": [P("Purpose", "Shows who does each step of a synthetic refund."), P("Roles", "Billing specialist, team lead, finance analyst."),
                              {"title": "RACI Matrix", "blocks": [{"type": "table", "caption": "Synthetic roles", "columns": RH, "rows": rows}]},
                              P("How to Use This Chart", "Find the activity, then read across."), P("Get Help", "Ask your team lead.")]}]}
    rc, out = flint("raci_bad.doc.json", raci_doc([["Review the request", "R", "A", "C"], ["Approve the refund", "R", "A", "A"], ["Send the notice", "I", "Accountable", "C"]]))
    check("D-54 RACI_ONE_A synthetic doc.json sheet (no --plan, meta.doc_type raci): 2 FAIL lines naming the rows", rc == 1 and out.count("FAIL [RACI_ONE_A]") == 2
          and '"Approve the refund" has 2 Accountable roles' in out and '"Send the notice" has no Responsible role' in out, out)
    rc, out = flint("raci_ok.doc.json", raci_doc([["Review the request", "R", "A", "C"], ["Approve the refund", "AR", "C", ""], ["Send the notice", "Responsible", "A", "I"]]))
    check("D-54 RACI_ONE_A synthetic clean doc.json sheet ('AR', full words) passes", rc == 0 and "RACI_ONE_A" not in out, out)
    rc, out = run_env(INST, S("plan_material.py"), "raci", "--out", "raci.plan.json")
    check("D-54 RACI_ONE_A plan GATES name the RACI rule", rc == 0 and "RACI_ONE_A (exactly one A and at least one R per activity)" in out, out)

if sel("AGENDA_TIME"):
    def agenda(rows, purpose="A 60-minute huddle to review synthetic denial trends.", extra=""):
        return fmd("meeting-agenda", "Denials Huddle", [("Purpose", purpose), ("Desired Outcomes", "Agree on the top three fixes."),
                                                         ("Agenda", tbl(["Topic", "Owner", "Minutes"], rows))], extra)
    rc, out = flint("agenda_bad.md", agenda([["Trend review", "Analytics lead", "30"], ["Top fixes", "Team lead", "30"], ["Next steps", "", "15"], ["Total", "", "75"]]))
    check("D-55 AGENDA_TIME synthetic 60-minute agenda with 75 minutes of topics and a topic with no owner fails", rc == 1
          and "FAIL [AGENDA_TIME] agenda_bad.md: agenda topics total 75 of 60 minutes" in out and 'FAIL [AGENDA_TIME] agenda_bad.md: "Next steps" has no owner role' in out, out)
    ok_rows = [["Trend review", "Analytics lead", "30"], ["Top fixes", "Team lead", "20"], ["Next steps", "Team lead", "10"], ["Total", "", "60"]]
    rc, out = flint("agenda_ok.md", agenda(ok_rows))
    check("D-55 AGENDA_TIME synthetic clean 60-minute agenda (Total row skipped) passes", rc == 0 and "AGENDA_TIME" not in out, out)
    rc, out = flint("agenda_meta.md", agenda(ok_rows, extra="duration_min: 45\n"))
    rc2, out2 = flint("agenda_nolen.md", agenda(ok_rows, purpose="A huddle to review synthetic denial trends."))
    check("D-55 AGENDA_TIME synthetic duration_min wins over the Purpose; no length at all warns only", rc == 1 and "FAIL [AGENDA_TIME] agenda_meta.md: agenda topics total 60 of 45 minutes" in out
          and rc2 == 0 and "WARN [AGENDA_TIME] agenda_nolen.md: meeting length not found" in out2, out + out2)

if sel("METRIC_FIELDS"):
    MH = ["Metric", "Business Definition", "Formula", "Source", "Refresh", "Owner Role"]
    def metric(first):
        return fmd("metric-definitions", "Revenue Cycle Metric Definitions", [("Purpose", "Defines the synthetic metrics on the denials dashboard."),
                   ("Metric Definitions", tbl(MH, [first, ["Example Denial Rate", "Share of claims denied", "Denied claims / submitted claims", "Synthetic claims table", "Daily", "Revenue analytics lead"]])),
                   ("Change Log", "Synthetic first version."), ("Get Help", "Ask the analytics team.")])
    rc, out = flint("metric_bad.md", metric(["Example Clean Claim Rate", "Share of claims accepted on first submission", "", "-", "Daily", "Revenue analytics lead"]))
    check("D-56 METRIC_FIELDS synthetic blank formula and blank source: one FAIL per blank field naming the metric", rc == 1 and out.count("FAIL [METRIC_FIELDS]") == 2
          and 'FAIL [METRIC_FIELDS] metric_bad.md: "Example Clean Claim Rate" has a blank formula' in out
          and 'FAIL [METRIC_FIELDS] metric_bad.md: "Example Clean Claim Rate" has a blank source' in out, out)
    rc, out = flint("metric_ok.md", metric(["Example Clean Claim Rate", "Share of claims accepted on first submission", "Accepted claims / submitted claims", "Synthetic claims table", "Daily", "Revenue analytics lead"]))
    check("D-56 METRIC_FIELDS synthetic clean metric table passes", rc == 0 and "METRIC_FIELDS" not in out, out)

if sel("DICT_FIELDS", "PHI_PATTERN"):
    DH = ["Field", "Description", "Data Type", "Source", "Classification", "PHI Flag", "Example"]
    D_ROWS = [["Claim ID", "Synthetic claim key", "Text", "Claims table", "Internal", "No", "CLM-0001"]]
    def dictionary(row):
        return fmd("data-dictionary", "Denials Extract Data Dictionary", [("Purpose", "Describes the fields in the synthetic denials extract."), ("How to Read This Dictionary", "One row per field."),
                   ("Fields", tbl(DH, D_ROWS + [row])), ("Data Classification Notes", "PHI fields need the PHI flag."), ("Get Help", "Ask the data team.")])
    rc, out = flint("dict_bad.md", dictionary(["Contact Number", "Patient phone number", "Text", "Registration table", "PHI", "", "555-201-4477"]))
    check("D-57 DICT_FIELDS synthetic PHI-classified field missing its flag, phone-number example: DICT_FIELDS and PHI_PATTERN FAIL", rc == 1
          and 'FAIL [DICT_FIELDS] dict_bad.md: "Contact Number" is classified PHI but its PHI flag is missing' in out
          and 'FAIL [PHI_PATTERN] dict_bad.md: example for "Contact Number" looks like a phone number; use a synthetic value' in out, out)
    rc, out = flint("dict_ok.md", dictionary(["Contact Number", "Patient phone number", "Text", "Registration table", "PHI", "Yes", "(synthetic, not shown)"]))
    check("D-57 DICT_FIELDS synthetic clean dictionary (PHI flagged, no real-looking example) passes", rc == 0 and "DICT_FIELDS" not in out and "PHI_PATTERN" not in out, out)
    ddoc = {"meta": {"title": "Denials Extract Data Dictionary", "doc_type": "data-dictionary", "audience": "Billing specialists", "sources": ["Synthetic test content"]},
            "sections": [{"title": "Fields", "blocks": [{"type": "table", "columns": DH, "rows": D_ROWS + [["Patient Email", "", "Text", "", "PHI", "Yes", "pat.example@sample.org"]]}]}]}
    rc, out = flint("dict_bad.doc.json", ddoc)
    check("D-57 DICT_FIELDS synthetic doc.json (no --plan): blank description and source, email example", rc == 1
          and 'FAIL [DICT_FIELDS] dict_bad.doc.json: "Patient Email" has a blank description' in out and 'FAIL [DICT_FIELDS] dict_bad.doc.json: "Patient Email" has a blank source' in out
          and 'FAIL [PHI_PATTERN] dict_bad.doc.json: example for "Patient Email" looks like an email address' in out, out)

if sel("RELEASE_ACTION"):
    def release(changed, affected, action):
        return fmd("release-notes", "Denials Dashboard Release Notes", [("Summary", "The synthetic denials dashboard has a new filter."), ("What Changed", changed),
                   ("Who Is Affected", affected), ("Action Needed", action), ("Get Help", "Ask the analytics team.")])
    rc, out = flint("rel_bad.md", release("- Added a payer filter.\n- Fixed the totals row.", "Billing specialists who use the denials dashboard.", "Update your saved views."))
    check("D-58 RELEASE_ACTION synthetic ungrouped changes and no Action Needed date while users are affected", rc == 1
          and "FAIL [RELEASE_ACTION] rel_bad.md: Action Needed has no date (users are affected)" in out
          and "FAIL [RELEASE_ACTION] rel_bad.md: What Changed is not grouped (use New, Changed, Fixed, Removed)" in out, out)
    rc, out = flint("rel_ok.md", release("### New\n- Added a payer filter.\n\n### Fixed\n- Fixed the totals row.", "Billing specialists who use the denials dashboard.", "Update your saved views by Oct. 30, 2026."))
    rc2, out2 = flint("rel_noaff.md", release(tbl(["Type", "Change"], [["New", "Added a payer filter."], ["Removed", "Old export button."]]), "No one; this is a back-end change.", "Nothing to do."))
    check("D-58 RELEASE_ACTION synthetic clean notes (### groups and dated action; Type table and no one affected) pass", rc == 0 and rc2 == 0 and "RELEASE_ACTION" not in out + out2, out + out2)

if sel("PROPOSAL_ASK"):
    WHY = " ".join("Denials grew in the synthetic sample for team %d over the last two quarters, and most came from missing authorization numbers." % i for i in range(1, 8))
    def proposal(rec, options, decision):
        return fmd("proposal", "Add a Denials Review Step", [("Recommendation", rec), ("Why Now", WHY), ("Options Considered", options),
                   ("Impact", "Billing specialists spend about one hour a week on the review."), ("Plan and Timeline", "Start with one team, then expand."),
                   ("Risks", "Reviews may slip during month-end close."), ("Decision Needed", decision)])
    rc, out = flint("prop_bad.md", proposal("Add a weekly synthetic denials review step to the billing workflow.", "- Keep the current workflow.", "Please approve the review step by Oct. 30, 2026."))
    check("D-59 PROPOSAL_ASK synthetic ask and date only in the last section, one option", rc == 1
          and "FAIL [PROPOSAL_ASK] prop_bad.md: state the ask and the decision date in the first 150 words (missing: the ask, the decision date)" in out
          and "FAIL [PROPOSAL_ASK] prop_bad.md: Options Considered lists 1 option(s) (at least 2)" in out, out)
    rc, out = flint("prop_ok.md", proposal("Please approve a weekly synthetic denials review step by Oct. 30, 2026.", "- Keep the current workflow.\n- Add the weekly review step.", "Approve by Oct. 30, 2026."))
    check("D-59 PROPOSAL_ASK synthetic clean proposal (ask and date up front, two options) passes", rc == 0 and "PROPOSAL_ASK" not in out, out)

if sel("PROCESS_TEXT"):
    def pmap(steps):
        return fmd("process-map", "Denial Rework Process Map", [("Purpose", "Shows how a synthetic denial moves from the queue to rework."), ("Roles", "Billing specialist and team lead."),
                   ("Process Map", "![Synthetic denial rework swimlane](denial_rework_map.png)"), ("Steps in Order", steps),
                   ("Hand-offs", "The team lead hands complex denials back to the specialist."), ("Get Help", "Ask your team lead.")])
    rc, out = flint("proc_bad.md", pmap("See the map above."))
    check("D-59 PROCESS_TEXT synthetic map image with no numbered text steps fails", rc == 1
          and "FAIL [PROCESS_TEXT] proc_bad.md: add a numbered text version of the map in Steps in Order (screen readers and print)" in out, out)
    rc, out = flint("proc_ok.md", pmap("1. Open the denial from the queue.\n2. Check the denial reason.\n3. Send the claim to rework."))
    check("D-59 PROCESS_TEXT synthetic clean map with numbered steps passes", rc == 0 and "PROCESS_TEXT" not in out, out)

if sel("CHECKOFF_VERBS"):
    CK_MSG = "\"Understands the queue\" uses 'understands', which an observer cannot see; start with an observable verb (demonstrates, completes, enters)"
    def ck_md(first):
        return fmd("skills-check-off", "Denial Queue Checklist", [("Observed Skills", "- [ ] %s\n- [ ] Opens the next claim in the queue\n- [ ] The learner can enter the denial reason code" % first)])
    rc, out = flint("ck_bad.md", ck_md("Understands the queue"))
    check("D-59 CHECKOFF_VERBS synthetic check-off item 'understands the queue' fails naming 'understands'", rc == 1 and "FAIL [CHECKOFF_VERBS] ck_bad.md: " + CK_MSG in out
          and out.count("CHECKOFF_VERBS") == 1, out)
    rc, out = flint("ck_ok.md", ck_md("Demonstrates how to sort the queue"))
    check("D-59 CHECKOFF_VERBS synthetic clean check-off (observable verbs, 'The learner can' lead-in) passes", rc == 0 and "CHECKOFF_VERBS" not in out, out)
    def ck_form(first):
        return {"meta": {"title": "Synthetic Queue Skills Checklist", "kind": "form", "format": "skills-check-off", "audience": "Billing specialists", "purpose": "Observe a team member working the synthetic denial queue.",
                         "owner": "Synthetic training team", "version": "1.0", "date": "2026-10-13", "sources": ["Synthetic test content"], "anonymous": False, "phi_approved": False},
                "sections": [{"title": "Observed Skills", "items": [{"id": "C1", "type": "checkbox", "label": first, "options": ["Met"]},
                             {"id": "C2", "type": "checkbox", "label": "Enters the denial reason code", "options": ["Met"]},
                             {"id": "C3", "type": "signature", "label": "Observer signature"}, {"id": "C4", "type": "date", "label": "Date observed"}]}]}
    rc, out = flint("ck_bad.form.json", ck_form("Understands the queue"))
    rc2, out2 = flint("ck_ok.form.json", ck_form("Demonstrates how to sort the queue"))
    check("D-59 CHECKOFF_VERBS synthetic check-off form doc.json: 'understands' fails, observable verbs pass", rc == 1 and "FAIL [CHECKOFF_VERBS] ck_bad.form.json: " + CK_MSG in out
          and rc2 == 0 and "CHECKOFF_VERBS" not in out2, out + out2)

if sel("CHARTER_GOAL"):
    def charter(goal, out_items):
        return fmd("project-charter", "Denials Reduction Charter", [("Problem", "Synthetic denials take too long to rework."), ("Goals and Measures", goal),
                   ("Scope", "**In scope:** the synthetic denial queue.\n\n**Out of scope:**\n" + out_items), ("Milestones", "Kickoff, pilot, rollout."),
                   ("Risks", "Month-end close may delay the pilot."), ("Roles and Decision Rights", "The project sponsor approves scope changes."), ("Get Help", "Ask the project lead.")])
    rc, out = flint("charter_bad.md", charter("- Improve denials.", ""))
    check("D-60 CHARTER_GOAL synthetic goal 'improve denials' and empty out-of-scope list warn (exit 0)", rc == 0
          and "WARN [CHARTER_GOAL] charter_bad.md: Goals and Measures has no measurable goal (add a number, percent, date, quarter or count)" in out
          and "WARN [CHARTER_GOAL] charter_bad.md: Scope has no out-of-scope items" in out, out)
    rc, out = flint("charter_ok.md", charter("- Cut the synthetic denial rate from 12 percent to 9 percent by Q2.", "- Payer contract changes."))
    check("D-60 CHARTER_GOAL synthetic clean charter (measurable goal, out-of-scope item) has no warning", rc == 0 and "CHARTER_GOAL" not in out, out)

if sel("PLAN_COVERAGE"):
    def tplan(rows):
        return fmd("training-plan", "Denials Training Plan", [("Purpose", "Plans synthetic denials training."), ("Audiences", "- **Billing specialists**: work the denial queue.\n- **Leaders**: review denial trends."),
                   ("Curriculum Map", tbl(["Module", "Audience", "Format"], rows)), ("Schedule", "November pilot."), ("Prerequisites", "Queue access."),
                   ("How We Will Measure Success", "Fewer reworked claims."), ("Get Help", "Ask the training team.")])
    base = [["Work the Denial Queue", "Billing specialists", "E-learning"], ["Read the Denial Codes", "Billing specialists", "Job aid"]]
    rc, out = flint("plan_bad.md", tplan(base))
    check("D-60 PLAN_COVERAGE synthetic audience 'Leaders' with no module warns (exit 0)", rc == 0 and "WARN [PLAN_COVERAGE] plan_bad.md: audience 'Leaders' has no module in the Curriculum Map" in out
          and out.count("PLAN_COVERAGE") == 1, out)
    rc, out = flint("plan_ok.md", tplan(base + [["Review Denial Trends", "Leaders", "Huddle"]]))
    check("D-60 PLAN_COVERAGE synthetic clean plan (every audience has a module) has no warning", rc == 0 and "PLAN_COVERAGE" not in out, out)

if sel("DASH_DEFS"):
    def dguide(defs):
        return fmd("dashboard-guide", "Denials Dashboard Guide", [("Purpose", "Explains the synthetic denials dashboard."), ("Access", "Request access from the analytics team."),
                   ("How It Is Organized", "The Summary tab shows Denial Rate and Clean Claim Rate by month."), ("Definitions", tbl(["Term", "Definition"], defs)),
                   ("How to Use It", "Filter by payer to compare the Denial Rate."), ("Data Sources and Refresh", "Synthetic claims table, refreshed daily."),
                   ("Known Limitations", "Shows the last 13 months only."), ("Get Help", "Ask the analytics team.")])
    d1 = [["Denial Rate", "Denied claims divided by submitted claims (synthetic)."]]
    rc, out = flint("dash_bad.md", dguide(d1))
    check("D-60 DASH_DEFS synthetic guide naming 'Clean Claim Rate' without a definition warns (exit 0)", rc == 0
          and "WARN [DASH_DEFS] dash_bad.md: 'Clean Claim Rate' is named but not defined in Definitions" in out and out.count("DASH_DEFS") == 1, out)
    rc, out = flint("dash_ok.md", dguide(d1 + [["Clean Claim Rate", "Claims accepted on first submission divided by submitted claims (synthetic)."]]))
    check("D-60 DASH_DEFS synthetic clean guide (every named metric defined) has no warning", rc == 0 and "DASH_DEFS" not in out, out)

DRIFT = os.path.join(SKILL, "references", "section_drift.json")


def section_drift(skills=None, mapping=None):
    """D-42: -> (drift lines, note) for catalog vs document builder doc types vs page types; note is NOT RUN when a sibling is missing."""
    import ast
    sys.path.insert(0, HERE); import catlib
    cfg = json.load(open(DRIFT, encoding="utf-8")); mp = mapping or cfg["mapping"]
    skills = skills or os.environ.get("MATERIAL_SKILLS_DIR") or os.path.dirname(SKILL)
    theme_p = os.path.join(skills, cfg["siblings"]["document"], "assets", "doc_theme.json")
    page_p = os.path.join(skills, cfg["siblings"]["page"], "scripts", "pagelib.py")
    for name, p in ((cfg["siblings"]["document"], theme_p), (cfg["siblings"]["page"], page_p)):
        if not os.path.isfile(p):
            return [], "SECTION_DRIFT: NOT RUN (sibling not installed: %s)" % name
    dts = json.load(open(theme_p, encoding="utf-8"))["doc_types"]
    lit = {}
    for n in ast.parse(open(page_p, encoding="utf-8").read()).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], "id", "") in ("PAGE_TYPES", "OPTIONAL_SECTIONS"):
            lit[n.targets[0].id] = ast.literal_eval(n.value)
    pts, popt = lit.get("PAGE_TYPES", {}), lit.get("OPTIONAL_SECTIONS", {})
    cat = catlib.load(os.path.join(SKILL, "assets", "catalog", "overlay.json"))
    lines = []
    for fmt, m in mp.items():
        if not m.get("catalog"):
            if not m.get("catalog_note"):
                lines.append("%s: no catalog format and no catalog_note" % fmt)
            continue
        e = cat["formats"].get(m["catalog"])
        if e is None:
            lines.append("%s: catalog format %s not found" % (fmt, m["catalog"])); continue
        req = [s["title"] for s in e.get("anatomy", []) if s.get("required", True)]
        opt = [s["title"] for s in e.get("anatomy", []) if not s.get("required", True)]
        dt = m.get("doc_type")
        if dt and dt not in dts:
            lines.append("%s: doc_type %s is not a document builder type" % (fmt, dt)); dt = None
        elif not dt and not m.get("doc_note"):
            lines.append("%s: no doc_type and no doc_note" % fmt)
        if dt:
            dreq = dts[dt].get("required", [])
            req = req or list(dreq)  # empty_anatomy
            parts = [w + ", ".join(x) for w, x in (("document adds ", [s for s in dreq if s not in req + opt]), ("catalog adds ", [s for s in req if s not in dreq])) if x]
            if parts:
                lines.append("%s: %s (vs document)" % (fmt, ", ".join(parts)))
        pt = m.get("page_type")
        if not pt:
            if not m.get("page_note"):
                lines.append("%s: no page_type and no page_note" % fmt)
            continue
        if pt not in pts:
            lines.append("%s: page type %s not in PAGE_TYPES" % (fmt, pt)); continue
        sat = {q["section"] for q in cfg["equivalences"] if q.get("side") == "page" and dt and dts[dt].get(q["doc_type_flag"])}
        preq, pop = pts[pt], popt.get(pt, [])
        parts = [w + ", ".join(x) for w, x in (("page adds ", [s for s in preq if s not in req + opt and s not in sat]),
                                               ("page requires ", [s for s in preq if s in opt]),
                                               ("catalog adds ", [s for s in req if s not in preq + pop])) if x]
        parts = [p + " (optional in catalog)" if p.startswith("page requires") else p for p in parts]
        if parts:
            lines.append("%s: %s" % (fmt, ", ".join(parts)))
    return lines, None


def drift_report(lines, note, mapping=None):
    if note:
        return note
    n = len(mapping or json.load(open(DRIFT, encoding="utf-8"))["mapping"])
    return "\n".join(["FAIL [SECTION_DRIFT] " + l for l in lines] + ["SECTION_DRIFT: %d format(s), %d drift line(s)" % (n, len(lines))])


if sel("SECTION_DRIFT"):
    def fake_skills(name, doc_types, page_sop, page_opt):
        root = os.path.join(TMP, name)
        os.makedirs(os.path.join(root, "document-builder", "assets"), exist_ok=True)
        os.makedirs(os.path.join(root, "confluence-page-builder", "scripts"), exist_ok=True)
        json.dump({"doc_types": doc_types}, open(os.path.join(root, "document-builder", "assets", "doc_theme.json"), "w"))
        open(os.path.join(root, "confluence-page-builder", "scripts", "pagelib.py"), "w").write(
            "PAGE_TYPES = %r\nOPTIONAL_SECTIONS = %r\n" % ({"sop": page_sop}, {"sop": page_opt} if page_opt else {}))
        return root
    SOP = ["Purpose", "Scope", "Roles and Responsibilities", "Procedure", "Exceptions"]
    MAP = json.load(open(DRIFT, encoding="utf-8"))["mapping"]; sop_only = {"sop": MAP["sop"]}
    ok_root = fake_skills("drift_ok", {"sop": {"required": SOP + ["References"], "revisions": True}, "user-guide": {"required": ["Introduction"]}}, SOP + ["Revision History"], ["References"])
    lines, note = section_drift(ok_root, sop_only)
    check("D-42 SECTION_DRIFT synthetic aligned sop passes (References optional on the page, Revision History from the revisions appendix)", not lines and not note, drift_report(lines, note, sop_only))
    lines, note = section_drift(fake_skills("drift_old", {"sop": {"required": SOP + ["References"]}}, SOP + ["Revision History"], None), sop_only)
    rep = drift_report(lines, note, sop_only)
    check("D-42 SECTION_DRIFT synthetic pre-D-68 sop fails: page adds Revision History, catalog adds References", "FAIL [SECTION_DRIFT] sop: page adds Revision History, catalog adds References" in rep, rep)
    nonote = {k: {x: y for x, y in MAP[k].items() if not x.endswith("_note")} for k in ("how-to", "user-guide")}
    lines, note = section_drift(ok_root, nonote); rep = drift_report(lines, note, nonote)
    check("D-42 SECTION_DRIFT synthetic mapping without catalog_note and page_note reports the skipped comparisons", "how-to: no catalog format and no catalog_note" in rep
          and "user-guide: no page_type and no page_note" in rep, rep)
    lines, note = section_drift(os.path.join(TMP, "none"))
    check("D-42 SECTION_DRIFT sibling missing prints NOT RUN (no pass, no FAIL)", not lines and note == "SECTION_DRIFT: NOT RUN (sibling not installed: document-builder)", str(note))
    lines, note = section_drift(); rep = drift_report(lines, note); print(rep)
    if note:
        print("skip D-42 SECTION_DRIFT installed skills: %s (UNVERIFIED)" % note)
    else:
        check("D-42 SECTION_DRIFT installed skills: sop, user-guide, release-notes, how-to sections match", not lines, rep)

if sel("OVERLAY_DRIFT"):
    shipped = json.load(open(os.path.join(SKILL, "assets", "catalog", "overlay.json"), encoding="utf-8"))
    def drift_with(ov):
        p = os.path.join(TMP, "drift_overlay.json")
        if ov is None:
            if os.path.exists(p): os.remove(p)
        else:
            json.dump(ov, open(p, "w"), ensure_ascii=False)
        r = subprocess.run([PY, S("catalog_tool.py"), "drift"], capture_output=True, text=True, cwd=TMP, env=dict(os.environ, MATERIAL_OVERLAY=p))
        return r.returncode, r.stdout + r.stderr
    older = copy.deepcopy(shipped); older["log"] = older["log"][:-2]; older["formats"].pop(next(iter(older["formats"])))
    rc, out = drift_with(older)
    check("D-74 OVERLAY_DRIFT synthetic: a working overlay whose log is older than the shared copy fails and names both versions", rc == 1 and "FAIL [OVERLAY_DRIFT]" in out and "is older than" in out and out.count("log entries") == 2, out)
    newer = copy.deepcopy(shipped); newer["log"].append({"date": "2026-10-13", "change": "synthetic lasting change", "command": "set job-aid words=300"})
    rc, out = drift_with(newer)
    check("D-74 OVERLAY_DRIFT synthetic: lasting changes not in the installed skill fail and ask the owner to repackage", rc == 1 and "repackage" in out, out)
    rc, out = drift_with(copy.deepcopy(shipped))
    check("D-74 OVERLAY_DRIFT: a working overlay equal to the shared copy passes", rc == 0 and "OVERLAY_DRIFT pass" in out, out)
    rc, out = drift_with(None)
    check("D-74 OVERLAY_DRIFT: no working overlay passes and reports the shared copy version", rc == 0 and "no working overlay" in out, out)

shutil.rmtree(TMP, ignore_errors=True)
print("SELF-TEST: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
