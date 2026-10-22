#!/usr/bin/env python3
"""Lint gate for training-material-designer Markdown deliverables.

  python3 scripts/lint_training.py <file.md> [more.md ...] [--pdf <file.pdf>] [--brand brand.json]
TERM_BRAND uses the shared AP rules (references/terminology.json) plus the house terms named by the project's brand
profile ("terminology" in brand.json; --brand, or found beside the file or at its project root by scripts/brand.py from
this skill or a sibling skill: material-composer, document-builder or slide-deck).
Formats (front matter `format:`): video-script, quick-start, job-aid, facilitator-guide, knowledge-check.
Front matter `output: pdf` (quick-start, job-aid) applies the one-page limits (QS_PDF_LIMITS, references/sheet-output.json).
--pdf: every sentence of each .md body must appear in the built PDF's text (QS_SOURCE_MATCH; PyMuPDF).
Video scripts: every narration cell must fit its time slot at the caption rate in references/training-rules.json
(CAPTION_FILE); scripts/md_to_captions.py then writes the .srt captions and the transcript.
Prints FAIL/WARN lines and `LINT: n file(s), x failed, y warnings`; exits 1 on any FAIL.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plain_language as PL  # noqa: E402  (shared with material-composer, confluence-page-builder, slide-deck)

REQ = {
    "video-script": ["Objective", "Script", "Wrap-up and Next Steps"],  # one hyphen rule (v4.22.0)
    "quick-start": ["Who It's For", "What You Can Do", "Steps", "Worked Example", "Common Mistakes", "Get Help"],
    "job-aid": ["When to Use", "Steps", "Check Your Work", "Get Help"],
    "facilitator-guide": ["Session Overview", "Learning Objectives", "Agenda", "Modules", "Practice Scenario", "Transfer Scenario", "Materials", "Follow-up"],
    "knowledge-check": ["Instructions", "Questions", "Scoring"],
}
FM_REQ = ["format", "title", "audience", "objective", "path", "sources"]
PATHS = {"foundation", "standard", "advanced", "all"}
VAGUE = re.compile(r"(?i)^\s*(understand|know|learn( about)?|be aware|appreciate|become familiar|gain (an )?understanding)\b")
SLOP = ["leverage", "unlock", "seamless", "robust", "synergy", "empower", "game-changing", "cutting-edge", "world-class", "best-in-class", "deep dive"]
PLACEHOLDER = re.compile(r"(?i)\b(TBD|TODO|lorem ipsum|xxx+|first last)\b|\[insert|\{\{|<placeholder>")
PHI = [(re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN-like number"), (re.compile(r"(?i)\bMRN[:#\s]*\d{5,}"), "MRN"),
       (re.compile(r"(?i)\b(DOB|date of birth)[:\s]+\d"), "date of birth")]
UI_VERB = re.compile(r"(?i)\b(click|select|open|choose|enter|press|tap|drag|expand|scroll|type|sign in)\b")
TIME = re.compile(r"^(\d{1,2}):([0-5]\d)\s*[-–]\s*(\d{1,2}):([0-5]\d)$")
SHEET = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "sheet-output.json"), encoding="utf-8"))
RULES = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "training-rules.json"), encoding="utf-8"))
OPTION = re.compile(r"(?:^|\s)([A-H])[.)]\s+\S")
WHY_FOR = re.compile(r"(?mi)^\s*\**why(?: not)? ([A-H])\b\**\s*:")
NORM = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2011": "-", "\u2212": "-", "\u00a0": " ", "\u00ad": ""}


def front_matter(txt):
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return None, txt
    fm, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^\s+-\s+", line) and key:
            fm.setdefault(key, []).append(line.split("-", 1)[1].strip())
        elif ":" in line:
            key, v = line.split(":", 1); key = key.strip(); v = v.strip()
            fm[key] = v if v else []
    return fm, txt[m.end():]


def sections(body):
    parts = re.split(r"(?m)^## +(.+?)\s*$", body)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def table_rows(s):
    rows = [r.strip() for r in s.splitlines() if r.strip().startswith("|")]
    out = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    return [r for r in out if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]


def secs(m1, s1):
    return int(m1) * 60 + int(s1)


def norm(s):
    """QS_SOURCE_MATCH normalization: quotes, dashes and whitespace (a hyphen at a line end joins its word)."""
    for a, b in NORM.items():
        s = s.replace(a, b)
    return re.sub(r"-\s+", "-", re.sub(r"\s+", " ", s)).strip()


def md_plain(s):
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\*\*|__|`|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)", "", s).strip()


def source_units(body):
    """(section, step number or None, sentence) for every sentence of the .md body, in order (headings excluded)."""
    out = []
    for sec, txt in sections(body).items():
        step, cur = 0, []
        def emit(text, n):
            for s in re.split(r"(?<=[.!?])\s+", md_plain(text)):
                if s.strip():
                    out.append((sec, n, s.strip()))
        for raw in txt.splitlines() + [""]:
            line = raw.strip()
            num = re.match(r"^\d+[.)]\s+(.*)$", line)
            item = num or re.match(r"^[*+-]\s+(.*)$", line)
            if cur and (not line or item or line.startswith("|") or not raw[:1].isspace() and cur[0] == "item"):
                emit(" ".join(cur[2]), cur[1]); cur = []
            if not line or re.fullmatch(r"!\[[^\]]*\]\([^)]*\)", line):
                continue
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    for c in cells:
                        emit(c, None)
                continue
            if item:
                step += 1 if num else 0
                cur = ["item", step if num and sec == SHEET["steps_section"] else None, [item.group(1)]]
            elif cur:
                cur[2].append(line)
            else:
                cur = ["para", None, [re.sub(r"^#{3,6}\s+|^>\s*", "", line)]]
    return out


def pdf_streams(doc):
    """Normalized PDF text as reading streams: the default order, plus left and right column streams (half-width pairs
    print side by side and their lines interleave in the default order)."""
    default, cols = [], {"L": [], "R": []}
    for pg in doc:
        default.append(pg.get_text())
        mid = pg.rect.width / 2.0
        lines = [(ln["bbox"][1], ln["bbox"][0], "".join(s["text"] for s in ln["spans"])) for b in pg.get_text("dict")["blocks"] for ln in b.get("lines", [])]
        for y, x, t in sorted(lines):
            cols["R" if x >= mid - 6 else "L"].append(t)
    return [norm(" ".join(default)), norm(" ".join(cols["L"])), norm(" ".join(cols["R"]))]


PASSES = []  # pass and note lines (QS_SOURCE_MATCH pass, TERM_BRAND not run), printed before the LINT summary


def caption_overruns(rows):
    """CAPTION_FILE: rows of (number, time, start s, end s, narration); a message per row whose narration is longer
    than its slot holds at the caption rate (references/training-rules.json)."""
    wpm, out = RULES["caption"]["words_per_minute"], []
    for i, t, a, b, narr in rows:
        n, cap = len(narr.split()), int((b - a) * wpm / 60)
        if n > cap:
            out.append("row %d (%s): narration is %d words; a %d-second slot holds %d at %d words per minute, so the captions can't keep up; cut the words or lengthen the slot" % (i, t, n, b - a, cap, wpm))
    return out


def option_feedback(q):
    """WHY_PER_OPTION: the wrong options of one question that have no feedback line. 'Why:' covers the answer;
    'Why <L>:' or 'Why not <L>:' covers option L. Options sit inline (A. ...  B. ...) or one per line."""
    letters = []
    for line in q.splitlines():
        if re.match(r"^\s*[A-H][.)]\s", line):
            letters += [x for x in OPTION.findall(line) if x not in letters]
    ans = re.search(r"(?mi)^\s*\**answer:\**\s*([A-H])\b", q)
    covered = set(WHY_FOR.findall(q.upper().replace("WHY NOT", "WHY")))
    return [x for x in letters if x not in covered and not (ans and x == ans.group(1).upper())]


def followup_plan(txt):
    """FOLLOWUP_PLAN: the facilitator guide's Follow-up names the follow-up evaluation and when it is sent."""
    fu = RULES["follow_up_evaluation"]; lo, hi = fu["send_after_days"]
    when = "%d to %d days after training" % (lo, hi)
    if not re.search(fu["pattern"], txt, re.I):
        return "Follow-up has no follow-up evaluation; say when it is sent (%s) and build it with the %s" % (when, fu["format"])
    days = [int(d) for d in re.findall(r"(\d+)(?=(?:\s*(?:-|\u2013|to)\s*\d+)?\s*days?\b)", txt)]
    days += [int(d) for d in re.findall(r"\d+\s*(?:-|\u2013|to)\s*(\d+)\s*days?\b", txt)]
    if not days:
        return "Follow-up names the follow-up evaluation but not when it is sent; send it %s" % when
    if any(d < lo or d > hi for d in days):
        return "Follow-up sends the follow-up evaluation %s days after training; send it %s" % ("-".join(str(d) for d in sorted(set(days))), when)


def source_match(add, path, fm, body, pdf):
    """QS_SOURCE_MATCH: every sentence of the .md body appears in the PDF text; reports the first mismatch."""
    title = fm.get("title") or os.path.basename(path)
    if not os.path.isfile(pdf):
        add("FAIL", "QS_SOURCE_MATCH", "%s: PDF %s not found; build it first" % (title, pdf)); return
    try:
        import fitz
    except ImportError:
        add("WARN", "QS_SOURCE_MATCH", "not run: PyMuPDF is not installed"); return
    streams = pdf_streams(fitz.open(pdf))
    for sec, n, s in source_units(body):
        if not any(norm(s) in t for t in streams):
            where = "%s step %d" % (sec, n) if n else sec
            add("FAIL", "QS_SOURCE_MATCH", "%s: PDF text differs from the source (%s)" % (title, where)); return
    return True


def pdf_limits(add, fm, fmt, S, words):
    """QS_PDF_LIMITS: output: pdf (one-page sheet) limits for quick-start and job-aid (references/sheet-output.json)."""
    out = str(fm.get("output", "")).strip().lower()
    if out not in SHEET["output_values"]:
        return
    lim = SHEET["limits"].get(fmt)
    if not lim:
        add("FAIL", "QS_PDF_LIMITS", "output: pdf is for %s only (this is %s)" % (" and ".join(SHEET["limits"]), fmt)); return
    if words > lim["words"]:
        add("FAIL", "QS_PDF_LIMITS", "%s with output: pdf: %d words (maximum %d for a one-page PDF)" % (fmt, words, lim["words"]))
    n = len(re.findall(r"(?m)^\s*\d+\.\s+\S", S.get(SHEET["steps_section"], "")))
    if n > lim["steps_max"]:
        add("FAIL", "QS_PDF_LIMITS", "%s with output: pdf: %d steps (maximum %d)" % (fmt, n, lim["steps_max"]))
    elif n < lim.get("steps_min", 1):
        add("FAIL", "QS_PDF_LIMITS", "%s with output: pdf: %d steps (minimum %d)" % (fmt, n, lim["steps_min"]))
    if "mistakes_max" in lim:
        k = len(re.findall(r"(?m)^\s*(?:[*+-]|\d+\.)\s+\S", S.get(SHEET["mistakes_section"], "")))
        if k > lim["mistakes_max"]:
            add("FAIL", "QS_PDF_LIMITS", "%s with output: pdf: %d common mistakes (maximum %d)" % (fmt, k, lim["mistakes_max"]))


_BRAND_MOD = []


def _brand_module():
    """scripts/brand.py from this skill, else from a sibling skill installed next to it; None when none is installed.
    Loaded once per run, so brand.load()'s cache holds across files."""
    if _BRAND_MOD:
        return _BRAND_MOD[0]
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    skills = os.path.dirname(os.path.dirname(here))
    mod = None
    for d in [here] + [os.path.join(skills, s, "scripts") for s in ("material-composer", "document-builder", "slide-deck")]:
        f = os.path.join(d, "brand.py")
        if os.path.isfile(f):
            spec = importlib.util.spec_from_file_location("brand", f)
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            break
    _BRAND_MOD.append(mod)
    return mod


BRAND = {"profile": None}


def use_project_terms(path):
    """Load the project's house terms (brand profile "terminology") for this file; returns the terminology path or None."""
    explicit = BRAND["profile"]
    near = [os.path.join(os.path.dirname(os.path.abspath(path)), n) for n in ("brand.json", ".brand.json")]
    br = _brand_module()
    if br is None:
        if explicit or any(os.path.isfile(n) for n in near):
            note = "TERM_BRAND: project house terms not loaded (brand.py not found; install material-composer beside this skill)"
            if note not in PASSES: PASSES.append(note)
        return None
    try:
        b = br.load(source=path, brand=explicit)
    except (SystemExit, OSError, ValueError) as e:
        note = "TERM_BRAND: project house terms not loaded (%s)" % e
        if note not in PASSES: PASSES.append(note)
        return None
    if b.terminology and hasattr(PL, "use_project_terms"):
        PL.use_project_terms(b.terminology)
    return b.terminology


def lint_file(path, pdf=None):
    R = []
    add = lambda lv, code, msg: R.append((lv, code, path, msg))
    txt = open(path, encoding="utf-8").read()
    fm, body = front_matter(txt)
    if fm is None:
        add("FAIL", "FRONT_MATTER", "file must start with --- front matter ---"); return R
    for k in FM_REQ:
        if not fm.get(k): add("FAIL", "FRONT_MATTER", "front matter needs '%s'" % k)
    fmt = fm.get("format", "")
    if fmt not in REQ:
        add("FAIL", "FORMAT", "format must be one of " + ", ".join(REQ)); return R
    if fm.get("path") and str(fm["path"]).lower() not in PATHS: add("FAIL", "FRONT_MATTER", "path must be foundation, standard, advanced or all")
    if not isinstance(fm.get("sources"), list) or not fm.get("sources"): add("FAIL", "SOURCES_MISSING", "list the sources behind the facts under sources:")
    if fm.get("objective") and VAGUE.search(str(fm["objective"])): add("FAIL", "OBJECTIVE_VAGUE", "objective must start with an observable action verb (find, decide, submit, explain), not 'understand' or 'know'")
    S = sections(body)
    for req in REQ[fmt]:
        if req not in S: add("FAIL", "SECTION_MISSING", "%s needs an H2 '%s'" % (fmt, req))
        elif not S[req].strip(): add("FAIL", "EMPTY_SECTION", "section '%s' is empty" % req)
    words = len(re.findall(r"\b\w[\w'’-]*\b", body))
    if fmt == "video-script" and "Script" in S:
        rows = table_rows(S["Script"])
        if not rows or [c.lower() for c in rows[0]] != ["time", "on screen", "narration"]:
            add("FAIL", "SCRIPT_TABLE", "Script must be a table with columns Time | On Screen | Narration")
        else:
            prev_end, total_words, checks, end, slots = 0, 0, 0, 0, []
            for i, r in enumerate(rows[1:], 1):
                if len(r) != 3: add("FAIL", "SCRIPT_TABLE", "row needs 3 cells: %s" % " | ".join(r)); continue
                m = TIME.match(r[0])
                if not m: add("FAIL", "TIMECODE", "time '%s' must look like 0:00-0:20" % r[0]); continue
                a, b = secs(m.group(1), m.group(2)), secs(m.group(3), m.group(4))
                if a != prev_end or b <= a: add("FAIL", "TIMECODE", "time '%s' must start where the last row ended (%d:%02d) and move forward" % (r[0], prev_end // 60, prev_end % 60))
                prev_end = b; end = b; slots.append((i, r[0], a, b, r[2]))
                n = len(r[2].split()); total_words += n
                pace = n / ((b - a) / 60.0) if b > a else 0
                if pace > 220: add("FAIL", "NARRATION_PACE", "row %s: %d words can't be said in %d seconds" % (r[0], n, b - a))
                elif pace > 190: add("WARN", "NARRATION_PACE", "row %s: %d words is fast to say" % (r[0], n))
                if "check:" in (r[1] + r[2]).lower():
                    checks += 1
                    if "answer:" not in r[2].lower(): add("FAIL", "CHECK_ANSWER", "check at %s needs 'Answer:' in the narration after a pause" % r[0])
            for msg in caption_overruns(slots): add("FAIL", "CAPTION_FILE", msg)
            mins = end / 60.0
            target = fm.get("duration_min")
            lo, hi = (2.0, 6.0)
            if target:
                try: t = float(target); lo, hi = t * 0.75, t * 1.25
                except ValueError: add("FAIL", "FRONT_MATTER", "duration_min must be a number")
            if not (lo <= mins <= hi): add("FAIL", "DURATION", "script runs %.1f min; target %.1f-%.1f min" % (mins, lo, hi))
            if mins and total_words / mins > 160: add("FAIL", "NARRATION_PACE", "narration averages %d words per minute; keep it at or under 160" % (total_words / mins))
            if checks < max(1, int(mins // 2)): add("FAIL", "CHECK_CADENCE", "%d check(s) in %.1f min; add one at least every 2 minutes" % (checks, mins))
    if fmt in ("quick-start", "job-aid"):
        cap, steps_cap = (450, 7) if fmt == "quick-start" else (300, 10)
        if words > cap: add("FAIL", "LENGTH", "%s is %d words; keep it to %d (one page)" % (fmt, words, cap))
        steps = re.findall(r"(?m)^\s*\d+\.\s+\S", S.get("Steps", ""))
        if not steps: add("FAIL", "STEPS_MAX", "Steps must be a numbered list")
        elif len(steps) > steps_cap: add("FAIL", "STEPS_MAX", "%d steps; keep it to %d or split the task" % (len(steps), steps_cap))
    pdf_limits(add, fm, fmt, S, words)
    if fmt == "facilitator-guide":
        if not fm.get("duration_min"): add("FAIL", "FRONT_MATTER", "facilitator-guide needs duration_min")
        mods = re.split(r"(?m)^### +", S.get("Modules", ""))[1:]
        if not mods: add("FAIL", "MODULE_CHECK", "Modules needs one H3 per module")
        for mtxt in mods:
            name = mtxt.splitlines()[0].strip()
            if "check:" not in mtxt.lower() or "answer:" not in mtxt.lower(): add("FAIL", "MODULE_CHECK", "module '%s' needs a 'Check:' with an 'Answer:'" % name)
        if not table_rows(S.get("Agenda", "")): add("FAIL", "AGENDA_TABLE", "Agenda must be a table (Time | Activity | Path)")
        if S.get("Follow-up", "").strip():
            msg = followup_plan(S["Follow-up"])
            if msg: add("WARN", "FOLLOWUP_PLAN", msg)
    if fmt == "knowledge-check":
        qs = re.split(r"(?m)^### +", S.get("Questions", ""))[1:]
        if not 3 <= len(qs) <= 10: add("FAIL", "QUESTION_COUNT", "%d questions; use 3-10" % len(qs))
        for q in qs:
            name = q.splitlines()[0].strip()
            if not re.search(r"(?mi)^\s*\**answer:", q): add("FAIL", "ANSWER_MISSING", "%s needs 'Answer:'" % name)
            ans = re.search(r"(?mi)^\s*\**answer:\**\s*([A-H])\b", q)
            if not re.search(r"(?mi)^\s*\**why:", q) and not (ans and ans.group(1).upper() in WHY_FOR.findall(q)):
                add("FAIL", "WHY_MISSING", "%s needs 'Why:' explaining the answer" % name)
            miss = option_feedback(q)
            if miss: add("FAIL", "WHY_PER_OPTION", "%s: option%s %s %s no feedback; add 'Why not <letter>:' for each wrong option (the answer keeps 'Why:')" % (name, "s" if len(miss) > 1 else "", ", ".join(miss), "have" if len(miss) > 1 else "has"))
    if fmt in ("quick-start", "job-aid"):
        ui = [l for l in re.findall(r"(?m)^\s*\d+\.\s+(.+)$", S.get("Steps", "")) if PL.BOLD.search(l) or UI_VERB.search(l)]
        if ui and not re.search(r"!\[[^\]]*\]\([^)]+\)", body):
            req = fm.get("required_screenshots")
            if str(fm.get("screenshots", "")).lower() == "pending" and isinstance(req, list) and req:
                add("WARN", "SCREENSHOTS_PENDING", "%d screenshot(s) listed as pending; add them before calling this complete" % len(req))
            else:
                add("FAIL", "SCREENSHOTS_MISSING", "the steps teach a screen but show none; embed the user's screenshots, or add 'screenshots: pending' and a 'required_screenshots:' list")
    items = [(m, True) for m in re.findall(r"(?m)^\s*(?:\d+\.|[*-])\s+(.+)$", body)]
    for it, _ in items:
        why = PL.telegraphic(it, True)
        if why: add("WARN", "TELEGRAPHIC", "%r reads as shorthand (%s); write a full instruction" % (it[:60], why))
    if not PL.is_developer(fm.get("audience")):
        lines = [(path, l) for l in re.sub(r"(?s)```.*?```", "", body).splitlines() if l.strip() and not l.lstrip().startswith("#")]
        for term, _, alt in PL.jargon_hits(lines, re.findall(r"(?m)^\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|", body)):
            add("WARN", "JARGON_UNDEFINED", "define or replace '%s' at first use (plain: %s)" % (term, alt))
        use_project_terms(path)
        hits = PL.term_hits(lines)
        if hits is None:
            if "TERM_BRAND: not run (terminology.json missing)" not in PASSES: PASSES.append("TERM_BRAND: not run (terminology.json missing)")
        for found, _, pref, why in hits or ():
            add("WARN", "TERM_BRAND", '"%s -> %s" (%s)' % (found, pref, why))
    if PLACEHOLDER.search(body): add("FAIL", "PLACEHOLDER", "placeholder text '%s'; ask, or list it under Open Questions in chat" % PLACEHOLDER.search(body).group(0))
    for w in SLOP:
        if re.search(r"(?i)\b%s\b" % re.escape(w), body): add("FAIL", "SLOP_WORD", "filler word '%s'" % w)
    for rx, what in PHI:
        if rx.search(body): add("FAIL", "PHI", "possible %s; remove it" % what)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"(?m)^[|#>*\-\d].*$", "", body)) if len(s.split()) > 3]
    if sents and sum(len(s.split()) for s in sents) / len(sents) > 20: add("WARN", "LONG_SENTENCES", "average sentence over 20 words; shorten for readability")
    if pdf:
        if source_match(add, path, fm, body, pdf):
            PASSES.append("QS_SOURCE_MATCH pass: %s" % (fm.get("title") or os.path.basename(path)))
    return R


def main(argv):
    if not argv:
        print(__doc__); return 2
    R, pdf = [], None
    PASSES.clear()
    if "--pdf" in argv:
        i = argv.index("--pdf")
        if i + 1 >= len(argv):
            print("ERROR --pdf needs a PDF file"); return 2
        pdf = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    if "--brand" in argv:
        i = argv.index("--brand")
        if i + 1 >= len(argv):
            print("ERROR --brand needs a brand.json file"); return 2
        BRAND["profile"] = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    for p in argv: R.extend(lint_file(p, pdf))
    for r in R: print("%s %s [%s] %s" % r)
    for line in PASSES: print(line)
    f = sum(1 for r in R if r[0] == "FAIL")
    print("LINT: %d file(s), %d failed, %d warnings" % (len(argv), f, len(R) - f))
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
