#!/usr/bin/env python3
"""Self-test for training-material-designer. Run after any change to lint_training.py or the examples.

  python3 scripts/test_training.py
Every example must lint clean; each known-bad mutation must fail with its expected code.
Prints `SELF-TEST: <passed>/<total> passed`; exits 1 on any failure.
"""
import json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
EXD = os.path.join(os.path.dirname(HERE), "assets", "examples")
sys.path.insert(0, HERE)
# Hermetic brand: lint runs resolve the brand of an empty project unless a case gives the file its own brand.json.
os.environ["BRAND_PROJECT"] = tempfile.mkdtemp(prefix="training_brand_empty_")
import lint_training as L


ONLY = None  # --only filter: None runs every case


def only_codes(valid):
    """--only list prints every check code, sorted; --only A,B keeps cases tagged A or B; unknown codes exit 2."""
    global ONLY
    a = sys.argv[1:]
    arg = next((x[7:] for x in a if x.startswith("--only=")), None)
    if "--only" in a:
        i = a.index("--only"); arg = a[i + 1] if i + 1 < len(a) else ""
    if arg is None:
        return
    if arg == "list":
        print("\n".join(sorted(valid))); sys.exit(0)
    req = {c.strip() for c in arg.split(",") if c.strip()}
    if not req or req - set(valid):
        sys.stderr.write("unknown --only code(s): %s. Valid codes: %s\n" % (", ".join(sorted(req - set(valid))) or "(none)", ", ".join(sorted(valid)))); sys.exit(2)
    ONLY = req


def selected(*codes):
    return ONLY is None or bool(ONLY & set(codes))

results = []
def check(name, ok, detail=""):
    results.append(ok); print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + detail[:300]))

def ex(fmt):
    return open(os.path.join(EXD, fmt + ".example.md"), encoding="utf-8").read()

def codes(txt):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(txt)
    r = L.lint_file(f.name); os.unlink(f.name)
    return {x[1] for x in r if x[0] == "FAIL"}

CASES = [
    ("FRONT_MATTER", "quick-start", lambda t: t.replace("audience: New billing specialists\n", "")),
    ("FORMAT", "quick-start", lambda t: t.replace("format: quick-start", "format: poster")),
    ("SOURCES_MISSING", "job-aid", lambda t: re.sub(r"sources:\n(  - .*\n)+", "sources:\n", t)),
    ("OBJECTIVE_VAGUE", "quick-start", lambda t: t.replace("objective: Pick", "objective: Understand how to pick")),
    ("SECTION_MISSING", "quick-start", lambda t: t.replace("## Common Mistakes", "## Pitfalls")),
    ("EMPTY_SECTION", "job-aid", lambda t: t.replace("The headline numbers match the totals on the report home page.", "")),
    ("SCRIPT_TABLE", "video-script", lambda t: t.replace("| Time | On Screen | Narration |", "| Time | Narration | Visual |")),
    ("TIMECODE", "video-script", lambda t: t.replace("| 0:50-1:20 |", "| 0:55-1:20 |")),
    ("DURATION", "video-script", lambda t: t.replace("duration_min: 3", "duration_min: 8")),
    ("CHECK_ANSWER", "video-script", lambda t: t.replace("Answer: the one with more denied dollars.", "Think it over.")),
    ("CHECK_CADENCE", "video-script", lambda t: t.replace("Check: two reasons", "Two reasons").replace("Check: you clicked", "You clicked")),
    ("NARRATION_PACE", "video-script", lambda t: t.replace("Save your filters as a custom view so the report opens ready tomorrow.", " ".join(["Save your filters as a custom view so the report opens ready tomorrow."] * 12))),
    ("LENGTH", "job-aid", lambda t: t.replace("## Get Help", "## Notes\n" + "This line adds extra words to the job aid. " * 40 + "\n\n## Get Help")),
    ("STEPS_MAX", "quick-start", lambda t: t.replace("5. Save your filters as a custom view.", "\n".join("%d. Do step %d." % (i, i) for i in range(5, 11)))),
    ("MODULE_CHECK", "facilitator-guide", lambda t: t.replace("Check: what changes", "Ask: what changes").replace("Answer: every number", "Expect: every number")),
    ("AGENDA_TABLE", "facilitator-guide", lambda t: re.sub(r"## Agenda\n.*?\n## Modules", "## Agenda\nIntro, modules, wrap-up.\n\n## Modules", t, flags=re.S)),
    ("QUESTION_COUNT", "knowledge-check", lambda t: re.sub(r"### Q3.*?## Scoring", "## Scoring", t, flags=re.S)),
    ("ANSWER_MISSING", "knowledge-check", lambda t: t.replace("Answer: A\n", "")),
    ("WHY_MISSING", "knowledge-check", lambda t: re.sub(r"Why: The region filter applies to the whole report\.\n(Why not .*\n)*", "", t)),
    ("PLACEHOLDER", "quick-start", lambda t: t.replace("contact the report developer", "contact TBD")),
    ("SLOP_WORD", "quick-start", lambda t: t.replace("See denied claims", "Leverage denied claims")),
    ("PHI", "job-aid", lambda t: t.replace("with no patient details", "of MRN 1234567")),
]
# Codes of the cases outside CASES; examples linting clean are EXAMPLES, the plain_language parity check is BUILD.
EXTRA_CODES = {"EXAMPLES", "BUILD", "SCREENSHOTS_PENDING", "SCREENSHOTS_MISSING", "TELEGRAPHIC", "JARGON_UNDEFINED", "QS_PDF_LIMITS", "QS_SOURCE_MATCH", "MD_TO_SHEET",
               "CAPTION_FILE", "WHY_PER_OPTION", "FOLLOWUP_PLAN", "TERM_BRAND"}


# --- D-05: output: pdf (SYNTHETIC inputs from the bundled examples; no real names or PHI) ---
DIAGRAM = ("diagram: [{label: Open the Report, icon: file-analytics}, {label: Set Filters, icon: filter}, "
           "{label: Click a Bar, icon: click}, {label: Pick a Reason, icon: list-check}, {label: Save the View, icon: device-floppy}]\n")


def pdf_md(fmt, diagram=True):
    extra = "output: pdf\nrole: Billing Specialist\nowner: Sample Report Team (synthetic)\n" + (DIAGRAM if diagram and fmt == "quick-start" else "")
    return re.sub(r"(?m)^(path: .*\n)", lambda m: m.group(1) + extra, ex(fmt), count=1)


def sim_build(doc, pdf):
    """SIMULATED build (document-builder has no sheet layout yet): writes the doc.json's reader text into a PDF
    with PyMuPDF, one page per top-level section, as the sheet would print it (title band, headings, blocks, footer)."""
    import fitz
    strip = lambda t: re.sub(r"\*\*|`", "", str(t))
    out = fitz.open()
    for sec in doc["sections"]:
        lines = [doc["meta"]["title"], sec["title"], "Version %s · %s" % (doc["meta"]["version"], doc["meta"]["date"])]
        for sub in sec["sections"]:
            lines.append(sub["title"])
            for b in sub["blocks"]:
                if b["type"] == "step_diagram":
                    lines.append("   ".join(s["label"] for s in b["steps"]))
                lines += [strip(b["text"])] if b.get("text") else []
                lines += [("%d. " % (i + 1) if b["type"] == "numbered" else "• ") + strip(x) for i, x in enumerate(b.get("items") or [])]
        lines.append("©2026 Northwind Traders Ltd. · %s v%s" % (doc["meta"]["title"], doc["meta"]["version"]))  # synthetic brand footer
        pg = out.new_page()
        pg.insert_textbox(fitz.Rect(54, 54, pg.rect.width - 54, pg.rect.height - 54), "\n".join(lines), fontsize=9)
    out.save(pdf)


def lint_codes(path, pdf=None, level="FAIL"):
    return [x for x in L.lint_file(path, pdf) if x[0] == level]


def d05_cases(tmp):
    import md_to_sheet as M
    if selected("MD_TO_SHEET"):
        p = os.path.join(tmp, "Synthetic_Quick_Start.md"); open(p, "w", encoding="utf-8").write(pdf_md("quick-start"))
        (dp, d, _), = M.convert([p])
        subs = d["sections"][0]["sections"]
        titles = [s["title"] for s in subs]
        blk = {s["title"]: [b["type"] for b in s["blocks"]] for s in subs}
        shape = (d["meta"]["layout"] == "sheet" and d["meta"]["doc_type"] == "quick-start" and len(d["sections"]) == 1
                 and d["sections"][0]["title"] == "Billing Specialist" and titles == L.REQ["quick-start"]
                 and [s.get("width") for s in subs] == ["half", "half", None, None, "half", "half"]
                 and blk["Steps"] == ["step_diagram", "numbered"] and len(subs[2]["blocks"][1]["items"]) == 5
                 and len(subs[2]["blocks"][0]["steps"]) == 5 and blk["Worked Example"] == ["card"] and os.path.isfile(dp))
        check("D-05 md_to_sheet: quick-start -> sheet doc.json (layout sheet, role section, half pairs, step_diagram, numbered, card)", shape, json.dumps(d)[:300])
        q = os.path.join(tmp, "Synthetic_Job_Aid.md"); open(q, "w", encoding="utf-8").write(pdf_md("job-aid"))
        (_, j, _), = M.convert([q])
        check("D-05 md_to_sheet: job-aid -> doc_type job-aid, numbered steps, no diagram without front matter diagram",
              j["meta"]["doc_type"] == "job-aid" and not any(b["type"] == "step_diagram" for s in j["sections"][0]["sections"] for b in s["blocks"]))
        p2 = os.path.join(tmp, "Synthetic_Quick_Start_2.md"); open(p2, "w", encoding="utf-8").write(pdf_md("quick-start", False).replace("role: Billing Specialist", "role: Team Lead"))
        (cp, c, _), = M.convert([p, p2], combine=True, out=os.path.join(tmp, "set.doc.json"))
        check("D-05 md_to_sheet --combine: two .md files -> one doc.json with one page (top-level section) each",
              [s["title"] for s in c["sections"]] == ["Billing Specialist", "Team Lead"] and c["meta"]["layout"] == "sheet")
        # D-08 fixture regression: a real delivered Quick Start (no role: line, one library figure, no output: pdf)
        fx = os.path.join(os.path.dirname(HERE), "assets", "fixtures", "D-08.Portal_Leader_Quick_Start.md")
        if not os.path.isfile(fx):
            print("NOT RUN D-08 fixture (fixture not shipped)")
        else:
            src = open(fx, encoding="utf-8").read()
            q = os.path.join(tmp, "Portal_Leader_Quick_Start.md")
            open(q, "w", encoding="utf-8").write(src.replace("---\n", "---\noutput: pdf\n", 1))
            (_, d8, _), = M.convert([q])
            sec = d8["sections"][0]; figs = [b for s in sec["sections"] for b in s["blocks"] if b.get("type") == "figure"]
            check("D-08 fixture regression: page title is the role from the title ('Leader'), not the audience sentence", sec["title"] == "Leader", sec["title"])
            check("D-08 fixture regression: the library figure is kept by default", len(figs) == 1, str(len(figs)))
            open(q, "w", encoding="utf-8").write(src.replace("---\n", "---\noutput: pdf\npdf_figures: false\n", 1))
            (_, d8, _), = M.convert([q])
            figs = [b for s in d8["sections"][0]["sections"] for b in s["blocks"] if b.get("type") == "figure"]
            check("D-08 fixture regression: pdf_figures: false leaves the figure out of the sheet", not figs, str(len(figs)))
        r = subprocess.run([sys.executable, os.path.join(HERE, "md_to_sheet.py"), p], capture_output=True, text=True)
        check("D-05 md_to_sheet prints the doc.json path and the exact build command",
              r.returncode == 0 and "DOC " + os.path.splitext(p)[0] + ".doc.json" in r.stdout and "build_doc.py %s --out" % dp in r.stdout and "--pdf" in r.stdout, r.stdout + r.stderr)
    if selected("QS_PDF_LIMITS"):
        p = os.path.join(tmp, "Limits_Quick_Start.md")
        def lim(txt, fmt="quick-start"):
            open(p, "w", encoding="utf-8").write(txt)
            return [x[3] for x in lint_codes(p) if x[1] == "QS_PDF_LIMITS"]
        check("D-05 QS_PDF_LIMITS: the example quick start and job aid with output: pdf pass", not lim(pdf_md("quick-start")) and not lim(pdf_md("job-aid")))
        six = pdf_md("quick-start").replace("5. Save your filters as a custom view.", "5. Save your filters as a custom view.\n6. Share the view with your lead.")
        check("D-05 negative QS_PDF_LIMITS: 6 steps (maximum 5)", any("6 steps (maximum 5)" in m for m in lim(six)))
        two = re.sub(r"3\. Click.*?\n5\. Save your filters as a custom view\.\n", "", pdf_md("quick-start"), flags=re.S)
        check("D-05 negative QS_PDF_LIMITS: 2 steps (minimum 3)", any("2 steps (minimum 3)" in m for m in lim(two)))
        three = pdf_md("quick-start").replace("## Get Help", "* Forgetting to save the view. Save it before you leave.\n\n## Get Help")
        check("D-05 negative QS_PDF_LIMITS: 3 common mistakes (maximum 2)", any("3 common mistakes (maximum 2)" in m for m in lim(three)))
        long_ = pdf_md("quick-start").replace("## Get Help", "Read the totals line before you pick a reason each week. " * 9 + "\n\n## Get Help")
        check("D-05 negative QS_PDF_LIMITS: over 250 words for a one-page PDF (the Markdown quick start allows 450)",
              any("(maximum 250 for a one-page PDF)" in m for m in lim(long_)) and "LENGTH" not in {x[1] for x in lint_codes(p)})
        nine = pdf_md("job-aid").replace("## Check Your Work", "".join("%d. Check item %d on the report page.\n" % (i, i) for i in range(5, 10)) + "\n## Check Your Work")
        check("D-05 negative QS_PDF_LIMITS: job aid with 9 steps (maximum 8)", any("9 steps (maximum 8)" in m for m in lim(nine)), str(lim(nine)))
        kc = ex("knowledge-check").replace("format: knowledge-check\n", "format: knowledge-check\noutput: pdf\n")
        check("D-05 negative QS_PDF_LIMITS: output: pdf on a knowledge check fails", any("output: pdf is for" in m for m in lim(kc)))
    if selected("QS_SOURCE_MATCH"):
        try:
            import fitz  # noqa: F401
        except ImportError:
            check("D-05 QS_SOURCE_MATCH (PyMuPDF missing: not run)", False); return
        p = os.path.join(tmp, "UAT_Tester_Quick_Start.md"); open(p, "w", encoding="utf-8").write(pdf_md("quick-start"))
        pdf = os.path.join(tmp, "UAT_Tester_Quick_Start.pdf")
        sim_build(M.convert([p])[0][1], pdf)
        check("D-05 QS_SOURCE_MATCH: PDF built from the .md (simulated build) passes, 0 failed", not lint_codes(p, pdf), str(lint_codes(p, pdf)))
        open(p, "w", encoding="utf-8").write(pdf_md("quick-start").replace("3. Click the longest payer bar", "3. Click the tallest payer bar"))
        got = [x[3] for x in lint_codes(p, pdf) if x[1] == "QS_SOURCE_MATCH"]
        check("D-05 negative QS_SOURCE_MATCH: step 3 edited without rebuilding fails (Steps step 3)",
              got == ["Denials Report Quick Start: PDF text differs from the source (Steps step 3)"], str(got))
        sim_build(M.convert([p])[0][1], pdf)
        check("D-05 QS_SOURCE_MATCH: after the rebuild, 0 failed", not lint_codes(p, pdf), str(lint_codes(p, pdf)))
        check("D-05 negative QS_SOURCE_MATCH: a missing PDF fails", any(x[1] == "QS_SOURCE_MATCH" for x in lint_codes(p, pdf + ".missing")))
        cli = lambda: subprocess.run([sys.executable, os.path.join(HERE, "lint_training.py"), p, "--pdf", pdf], capture_output=True, text=True).stdout
        out = cli()
        check("D-19 portfolio clash: QS_SOURCE_MATCH positive (synthetic): a matching PDF prints 'QS_SOURCE_MATCH pass: <title>' before the LINT summary",
              "QS_SOURCE_MATCH pass: Denials Report Quick Start\nLINT: 1 file(s), 0 failed" in out, out[-300:])
        open(p, "w", encoding="utf-8").write(pdf_md("quick-start"))  # the PDF was rebuilt from the edited step 3
        out = cli()
        check("D-19 portfolio clash: QS_SOURCE_MATCH negative (synthetic): a PDF that differs prints the FAIL and no pass line",
              "FAIL QS_SOURCE_MATCH " in out and "QS_SOURCE_MATCH pass" not in out, out[-300:])

# --- Round 6: D-71 CAPTION_FILE, D-72 WHY_PER_OPTION, D-73 FOLLOWUP_PLAN, D-39 TERM_BRAND ---
def cli_lint(path, cwd=None, script=None):
    return subprocess.run([sys.executable, script or os.path.join(HERE, "lint_training.py"), path], capture_output=True, text=True, cwd=cwd,
                          encoding="utf-8", errors="replace").stdout


def round6_cases(tmp):
    import md_to_captions as C
    if selected("CAPTION_FILE"):
        vs = os.path.join(tmp, "Denials_Video_Script.md"); open(vs, "w", encoding="utf-8").write(ex("video-script"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "md_to_captions.py"), vs], capture_output=True, text=True)
        srt = os.path.join(tmp, "Denials_Video_Script.srt"); trp = os.path.join(tmp, "Denials_Video_Script.transcript.md")
        rows = [rw for rw in L.table_rows(L.sections(L.front_matter(ex("video-script"))[1])["Script"])[1:]]
        cues = open(srt, encoding="utf-8").read().strip().split("\n\n") if os.path.isfile(srt) else []
        ok = (r.returncode == 0 and len(cues) == len(rows) == 7 and cues[0].split("\n")[1] == "00:00:00,000 --> 00:00:20,000"
              and cues[-1].split("\n")[1] == "00:02:40,000 --> 00:03:00,000"
              and all(" ".join(c.split("\n")[2:]) == rw[2] for c, rw in zip(cues, rows)))
        check("D-71 CAPTION_FILE positive (scenario: shipped example): md_to_captions writes <file>.srt, one cue per row, start/end from Time (HH:MM:SS,mmm), text = narration", ok, r.stdout + r.stderr + str(cues[:2]))
        tr = open(trp, encoding="utf-8").read() if os.path.isfile(trp) else ""
        check("D-71 CAPTION_FILE positive: <file>.transcript.md has the title and every narration cell with its time",
              tr.startswith("# Find Your Top Denial Reasons in Three Clicks") and all("**%s.**" % rw[0] in tr and rw[2] in tr for rw in rows), tr[:300])
        check("D-71 CAPTION_FILE positive: the shipped example has no CAPTION_FILE finding", not [x for x in L.lint_file(vs) if x[1] == "CAPTION_FILE"])
        check("D-71 CAPTION_FILE positive (synthetic): 80 words in a 30-second slot fits at 160 words per minute",
              not L.caption_overruns([(1, "0:00-0:30", 0, 30, " ".join(["word"] * 80))]) and bool(L.caption_overruns([(1, "0:00-0:30", 0, 30, " ".join(["word"] * 81))])))
        long_ = " ".join(["Look at the payer chart and find the longest bar."] * 8) + " Stop."  # synthetic: 81 words
        bad = os.path.join(tmp, "Long_Video_Script.md")
        open(bad, "w", encoding="utf-8").write(ex("video-script").replace("Next, look at the payer chart. The longest bar is the payer with the most denied dollars this month.", long_))
        got = [x[3] for x in L.lint_file(bad) if x[1] == "CAPTION_FILE" and x[0] == "FAIL"]
        check("D-71 negative CAPTION_FILE (synthetic over-long row): FAIL names the row (row 3, 0:50-1:20)",
              len(got) == 1 and got[0].startswith("row 3 (0:50-1:20): narration is 81 words; a 30-second slot holds 80 at 160 words per minute"), str(got))
        r = subprocess.run([sys.executable, os.path.join(HERE, "md_to_captions.py"), bad], capture_output=True, text=True)
        check("D-71 negative CAPTION_FILE: md_to_captions prints the FAIL, writes nothing and exits 1",
              r.returncode == 1 and r.stdout.startswith("FAIL CAPTION_FILE [") and not os.path.exists(os.path.join(tmp, "Long_Video_Script.srt"))
              and not os.path.exists(os.path.join(tmp, "Long_Video_Script.transcript.md")), r.stdout)
    if selected("WHY_PER_OPTION"):
        q4 = ("### Q4\nWhich chart shows the denial reasons?\nA. Payer chart  B. Reasons chart  C. Trend line  D. Headline numbers\n"
              "Answer: B\nWhy: The reasons chart lists each denial reason.\n\n## Scoring")  # synthetic question
        kc = ex("knowledge-check").replace("## Scoring", q4, 1)
        got = [x[3] for x in lint_text(kc) if x[1] == "WHY_PER_OPTION"]
        check("D-72 negative WHY_PER_OPTION (synthetic: options A-D, only 'Why:' for the answer): FAIL names A, C, D",
              got == ["Q4: options A, C, D have no feedback; add 'Why not <letter>:' for each wrong option (the answer keeps 'Why:')"], str(got))
        check("D-72 WHY_PER_OPTION positive: the shipped knowledge check gives feedback for every option", not [x for x in lint_text(ex("knowledge-check")) if x[1] == "WHY_PER_OPTION"])
        q4b = ("### Q4\nWhich chart shows the denial reasons?\nA. Payer chart\nB. Reasons chart\nC. Trend line\nD. Headline numbers\n"
               "Answer: B\nWhy: The reasons chart lists each denial reason.\nWhy not A: The payer chart groups by payer.\n"
               "Why not C: The trend line shows change over time.\nWhy not D: The headline numbers are totals.\n\n## Scoring")  # synthetic
        check("D-72 WHY_PER_OPTION positive (synthetic): options one per line, each wrong option with 'Why not <letter>:'",
              not codes(ex("knowledge-check").replace("## Scoring", q4b, 1)))
    if selected("FOLLOWUP_PLAN"):
        fu = lambda t: [x for x in lint_text(t) if x[1] == "FOLLOWUP_PLAN"]
        check("D-73 FOLLOWUP_PLAN positive: the shipped facilitator guide names the follow-up evaluation and when it is sent", not fu(ex("facilitator-guide")))
        no_eval = re.sub(r"(?m)^Send the follow-up evaluation.*\n?", "", ex("facilitator-guide"))  # synthetic
        got = fu(no_eval)
        check("D-73 negative FOLLOWUP_PLAN (synthetic: Follow-up without a follow-up evaluation): WARN, 0 failed",
              [x[0] for x in got] == ["WARN"] and not codes(no_eval) and "follow-up-evaluation format" in got[0][3], str(got))
        got = fu(ex("facilitator-guide").replace("45 days after the session", "7 days after the session"))  # synthetic
        check("D-73 negative FOLLOWUP_PLAN (synthetic): evaluation sent 7 days after training warns (30 to 60 days)",
              len(got) == 1 and got[0][0] == "WARN" and "7 days" in got[0][3] and "30 to 60 days" in got[0][3], str(got))
    if selected("TERM_BRAND"):
        fx = os.path.join(os.path.dirname(HERE), "assets", "fixtures", "D-39.input.md")
        kept = open(fx, encoding="utf-8").read().split("## Why This Is Changing\n", 1)[1].strip()
        fg = os.path.join(tmp, "Brand_Facilitator_Guide.md")
        wrap = lambda txt: ex("facilitator-guide").replace("## Learning Objectives", "### Why This Is Changing\n" + txt + "\n\n## Learning Objectives", 1)
        open(fg, "w", encoding="utf-8").write(wrap(kept))
        out = cli_lint(fg)
        tb = [l for l in out.splitlines() if l.startswith("WARN TERM_BRAND ")]
        base = ['"Over 40 -> More than 40"', '"Jan 17th -> Jan. 17"']
        check("D-39 TERM_BRAND negative, no project brand (fixture D-39 kept section in a synthetic facilitator guide): the 2 shared AP rules warn, LINT 0 failed",
              len(tb) == 2 and all(any(w in l for l in tb) for w in base) and "LINT: 1 file(s), 0 failed, 2 warnings" in out, out[-600:])
        proj = os.path.join(tmp, "house_project"); os.makedirs(proj, exist_ok=True)
        house = os.path.join(proj, "house.json")
        json.dump({"name": "NorthStar", "terminology": "house.json"}, open(os.path.join(proj, "brand.json"), "w"))
        json.dump({"format": "terminology", "sets": {"internal": [
            {"id": "product", "kind": "case", "word": "NorthStar", "why": "product name"},
            {"id": "roles", "kind": "midsentence", "pattern": "\\bAnalysts\\b", "why": "job titles lowercase mid-sentence"},
            {"id": "email", "kind": "regex", "pattern": "\\be-mail\\b", "suggest": "email", "why": "house style"}]}}, open(house, "w"))
        pg = os.path.join(proj, "Brand_Facilitator_Guide.md"); open(pg, "w", encoding="utf-8").write(wrap(kept))
        out = cli_lint(pg)
        tb = [l for l in out.splitlines() if l.startswith("WARN TERM_BRAND ")]
        want = base + ['"Northstar -> NorthStar"', '"Analysts -> analysts"', '"e-mail -> email"']
        check("D-39 TERM_BRAND negative with the project's house terms (brand.json terminology beside the file): 5 WARN lines, LINT 0 failed, 5 warnings",
              len(tb) == 5 and all(any(w in l for l in tb) for w in want) and "LINT: 1 file(s), 0 failed, 5 warnings" in out, out[-600:])
        L.PL.use_project_terms(house)  # the house terms apply to the in-process checks below as well
        fixed = ("The NorthStar denials view moves on Jan. 17 so analysts see the same numbers. More than 40 saved views move with you, "
                 "and billing teams keep their filters; send questions by email.")  # synthetic corrected text
        clean = not [x for x in lint_text(wrap(fixed)) if x[1] == "TERM_BRAND"] and not any(x[1] == "TERM_BRAND" for f in L.REQ for x in lint_text(ex(f)))
        check("D-39 TERM_BRAND positive (synthetic): the corrected text and every shipped example give no TERM_BRAND", clean)
        dev = wrap(kept).replace("audience: Billing specialists and team leads", "audience: Report developers")
        check("D-39 TERM_BRAND skipped for developer audiences (like JARGON_UNDEFINED)", "audience: Report developers" in dev and not [x for x in lint_text(dev) if x[1] == "TERM_BRAND"])
        cp = os.path.join(tmp, "noterms")
        shutil.copytree(os.path.dirname(HERE), cp, ignore=shutil.ignore_patterns("__pycache__", "assets"))
        os.remove(os.path.join(cp, "references", "terminology.json"))
        out = cli_lint(fg, script=os.path.join(cp, "scripts", "lint_training.py"))
        check("D-39 TERM_BRAND: a missing terminology.json reports 'not run', never a pass",
              "TERM_BRAND: not run (terminology.json missing)\nLINT: 1 file(s), 0 failed, 0 warnings" in out and "WARN TERM_BRAND" not in out and "TERM_BRAND pass" not in out, out[-300:])


def main():
    only_codes(EXTRA_CODES | {c for c, _, _ in CASES})
    for fmt in L.REQ if selected("EXAMPLES") else ():
        got = codes(ex(fmt))
        check("example %s lints clean" % fmt, not got, str(got))
    for code, fmt, fn in (c for c in CASES if selected(c[0])):
        got = codes(fn(ex(fmt)))
        check("negative " + code, code in got, "got %s" % sorted(got))
    warns = lambda txt: {x[1] for x in lint_text(txt) if x[0] == "WARN"}
    if selected("SCREENSHOTS_PENDING"):
        check("pending screenshots warn (SCREENSHOTS_PENDING), never pass silently", "SCREENSHOTS_PENDING" in warns(ex("quick-start")))
    if selected("SCREENSHOTS_MISSING"):
        bad = re.sub(r"screenshots: pending\nrequired_screenshots:\n(  - .*\n)+", "", ex("quick-start"))
        check("negative SCREENSHOTS_MISSING (steps teach a screen, no screenshots, nothing pending)", "SCREENSHOTS_MISSING" in codes(bad))
        check("embedded screenshot clears the screenshot check", not ({"SCREENSHOTS_MISSING"} & codes(bad.replace("## Worked Example", "![Report with filters set](filters.png)\n\n## Worked Example"))))
    if selected("TELEGRAPHIC"):
        tele = ex("job-aid").replace("4. Reopen your saved custom view if you use one.", "4. Rate ease; Submit the test ID")
        check("warn TELEGRAPHIC ('Rate ease; Submit the test ID')", "TELEGRAPHIC" in warns(tele))
    if selected("JARGON_UNDEFINED"):
        jar = ex("job-aid").replace("Use this when the numbers look wrong", "Use this when the grain looks wrong")
        check("warn JARGON_UNDEFINED ('grain' with no definition)", "JARGON_UNDEFINED" in warns(jar))
    tmp = tempfile.mkdtemp()
    d05_cases(tmp)
    round6_cases(tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    if selected("BUILD"):
        mine = open(os.path.join(HERE, "plain_language.py"), encoding="utf-8").read()
        for sib in ("material-composer", "slide-deck", "confluence-page-builder"):
            other = os.path.join(os.path.dirname(os.path.dirname(HERE)), sib, "scripts", "plain_language.py")
            if os.path.isfile(other):
                check("plain_language.py matches %s's copy" % sib, open(other, encoding="utf-8").read() == mine)
            else:
                print("UNVERIFIED plain_language.py parity with %s (not installed next to this skill)" % sib)
    print("SELF-TEST: %d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


def lint_text(txt):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(txt)
    r = L.lint_file(f.name); os.unlink(f.name)
    return r

if __name__ == "__main__":
    main()
