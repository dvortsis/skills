#!/usr/bin/env python3
"""One gate for composed materials. Markdown pieces are checked against their plan (or the catalog entry named in front
matter `format:`); kits, instructor-led pairs and the style tokens have their own modes.

  lint_material.py FILE.md [--plan P.plan.json] [--overlay O.json] [--source DRAFT --facts FACTS]
  lint_material.py DOC.json --plan P.plan.json            each top-level section of a sheet or document vs the plan
  lint_material.py --kit kit.json                       KIT_COVERAGE across every piece, then each piece
  lint_material.py --ilt GUIDE.md --deck DECK.json      ILT_PAIR
  lint_material.py --style                              STYLE_DRIFT (style_tokens.py check)
  --brand brand.json                                    use this brand profile instead of each file's project brand
Codes: ANATOMY_MATCH, FRONT_MATTER, SOURCES_MISSING, PLACEHOLDER, FILLER, SLOP_OPENER, PHI_PATTERN, TITLE_CASE,
SUBJECT_LENGTH, WORD_LIMIT, DERIVED_NOTE, RENAMED_TERM, JARGON_UNDEFINED (warn), TERM_BRAND (warn: the shared AP rules
plus the house terms named by the project's brand profile; audience sets load only when that file defines them), COMMS_CHECK (communication formats also run executive-communications check_comms;
WARN when that skill is not installed, $MATERIAL_SKILLS_DIR overrides the skills folder), KIT_COVERAGE, KIT_ADOPTION
(adoption-measures piece in every kit), ILT_PAIR, STYLE_DRIFT.
Format rules by catalog format (data: material_rules.json format_rules; .md, doc.json and check-off forms): RACI_ONE_A,
AGENDA_TIME, METRIC_FIELDS, DICT_FIELDS, RELEASE_ACTION, PROPOSAL_ASK, PROCESS_TEXT, CHECKOFF_VERBS; warn only:
CHARTER_GOAL, PLAN_COVERAGE, DASH_DEFS.
Last line: "LINT_MATERIAL: n file(s), k failed"."""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import catlib, text_rules
try:
    import plain_language
except Exception:
    plain_language = None

RULES = json.load(open(os.path.join(catlib.SKILL, "references", "material_rules.json"), encoding="utf-8"))
F = []
OPTS = {}


def use_brand(path, brand=None):
    """The project's brand for this file: its house terms (TERM_BRAND, jargon, acronyms) and names kept capitalized."""
    try:
        import brand as BR
        b = BR.load(source=path, brand=brand)
    except (ImportError, SystemExit, OSError, ValueError) as e:
        print("BRAND: not loaded (%s)" % e); return None
    if b.terminology and plain_language and hasattr(plain_language, "use_project_terms"):
        plain_language.use_project_terms(b.terminology)
    text_rules.add_proper_nouns([w for n in (b.name, b.org) for w in str(n or "").split()])
    return b


def add(level, code, msg):
    F.append((level, code, msg)); print("%s [%s] %s" % (level, code, msg))


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    meta, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^\s+- ", line) and key:
            meta.setdefault(key, []).append(line.strip()[2:].strip())
        elif ":" in line and not line.startswith(" "):
            key, v = line.split(":", 1); key = key.strip(); v = v.strip()
            meta[key] = v if v else []
    return meta, text[m.end():]


def sections(body):
    out, cur = [], None
    for line in body.splitlines():
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if h and not line.startswith("###"):
            cur = {"title": h.group(1), "lines": []}; out.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    return out


def words(s):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", s))


def count(sec, kind):
    L = sec["lines"]
    if kind == "steps":
        return sum(1 for x in L if re.match(r"^\s*\d+[.)]\s", x))
    if kind == "items":
        return sum(1 for x in L if re.match(r"^\s*([-*•]|\d+[.)]|\[ \])\s", x))
    if kind == "questions":
        return sum(1 for x in L if re.match(r"^###\s", x) or re.match(r"^\s*\*\*.+\?\*\*\s*$", x))
    return 0


def plan_for(meta, plan_path, overlay):
    if plan_path:
        return json.load(open(plan_path, encoding="utf-8"))
    cat = catlib.load(overlay)
    r = catlib.resolve(cat, meta.get("format", ""))
    if not r or not r.get("entry"):
        return None
    e = r["entry"]
    return {"format": r["id"], "label": e["label"], "family": e["family"], "anatomy": e.get("anatomy", []), "words": e.get("words"),
            "how": r["how"], "derived_from": r["derived_from"], "subject_max": e.get("subject_max"), "renamed_terms": sorted(cat.get("renamed", {}))}


def lint_md(path, plan_path=None, overlay=None, meta_word="front matter", words_cap=True, fmt_rules=True):
    text = open(path, encoding="utf-8").read()
    meta, body = front(text)
    name = os.path.basename(path)
    for k in ("format", "title", "audience"):
        if not meta.get(k):
            add("FAIL", "FRONT_MATTER", "%s: front matter needs %s" % (name, k))
    if not meta.get("sources"):
        add("FAIL", "SOURCES_MISSING", "%s: list sources in front matter" % name)
    plan = plan_for(meta, plan_path, overlay)
    if not plan:
        add("FAIL", "ANATOMY_MATCH", "%s: format '%s' not resolvable; run plan_material.py" % (name, meta.get("format", "")))
        return
    secs = sections(body)
    have = [catlib.key(s["title"]) for s in secs]
    want = plan.get("anatomy", [])
    pos = []
    for w in want:
        k = catlib.key(w["title"])
        if k not in have:
            if w.get("required", True):
                add("FAIL", "ANATOMY_MATCH", '%s: missing section "%s"' % (name, w["title"]))
            continue
        pos.append(have.index(k))
        sec = secs[have.index(k)]
        for lk, (lo, hi) in (w.get("limits") or {}).items():
            n = count(sec, lk)
            if not lo <= n <= hi:
                add("FAIL", "ANATOMY_MATCH", '%s: "%s" has %d %s (allowed %d-%d)' % (name, w["title"], n, lk, lo, hi))
    if pos != sorted(pos):
        add("FAIL", "ANATOMY_MATCH", "%s: sections out of order (expected %s)" % (name, " | ".join(w["title"] for w in want if catlib.key(w["title"]) in have)))
    if want:
        extra = [s["title"] for s in secs if catlib.key(s["title"]) not in {catlib.key(w["title"]) for w in want}]
        if extra:
            add("WARN", "ANATOMY_MATCH", "%s: sections not in the %s anatomy: %s" % (name, plan["label"], ", ".join(extra)))
    if plan.get("how") == "derived" and catlib.key(meta.get("derived_from", "")) != catlib.key(plan.get("derived_from") or ""):
        add("FAIL", "DERIVED_NOTE", "%s: add derived_from: %s to %s so readers and reviewers see what was borrowed" % (name, plan.get("derived_from"), "meta (doc.json)" if meta_word == "meta" else "front matter"))
    wl = plan.get("words")
    bw = words(re.sub(r"^#.*$", "", body, flags=re.M))
    if words_cap and wl and bw > wl:
        add("FAIL", "WORD_LIMIT", "%s: %d words (maximum %d for %s)" % (name, bw, wl, plan["label"]))
    tw = plan.get("title_words")
    if tw and words(meta.get("title", "")) > tw:
        add("FAIL", "WORD_LIMIT", "%s: title is %d words (maximum %d for the %s profile)" % (name, words(meta.get("title", "")), tw, plan.get("audience_profile")))
    sm = plan.get("subject_max")
    if sm:
        subj = meta.get("subject", "")
        if not subj:
            add("FAIL", "SUBJECT_LENGTH", "%s: front matter needs subject" % name)
        elif len(subj) > sm:
            add("FAIL", "SUBJECT_LENGTH", "%s: subject is %d characters (maximum %d)" % (name, len(subj), sm))
    low = body.lower()
    pn = meta.get("proper_names") or []
    for n in (pn if isinstance(pn, list) else pn.split(";")):
        if n.strip():
            low = low.replace(n.strip().lower(), " ")  # PROPER_NAMES: declared names (a dashboard called "... Deep Dive") skip the filler list
    for p in RULES["placeholders"]:
        if re.search(p, body, re.I):
            add("FAIL", "PLACEHOLDER", "%s: placeholder text matches '%s'" % (name, p))
    for w in RULES["filler"]:
        if re.search(r"\b%s\b" % re.escape(w), low):
            add("FAIL", "FILLER", "%s: filler word '%s'" % (name, w))
    first = next((l for l in body.splitlines() if l.strip() and not l.startswith("#")), "")
    for o in RULES["slop_openers"]:
        if o in low:
            add("FAIL", "SLOP_OPENER", "%s: generic opener '%s'; open with the change or the ask" % (name, o))
    for label, pat in RULES["phi_patterns"].items():
        if re.search(pat, body, re.I):
            add("FAIL", "PHI_PATTERN", "%s: looks like %s; remove it" % (name, label))
    for h in [meta.get("title", "")] + [s["title"] for s in secs]:
        if h and text_rules.proper(h) != h:
            add("FAIL", "TITLE_CASE", '%s: "%s" should be "%s"' % (name, h, text_rules.proper(h)))
    for old in plan.get("renamed_terms") or []:
        if re.search(r"\b%s\b" % re.escape(old), body, re.I):
            add("FAIL", "RENAMED_TERM", "%s: '%s' was renamed in the catalog; use the new name" % (name, old))
    if plain_language and not plain_language.is_developer(meta.get("audience", "")):
        for term, _where, _hint in plain_language.jargon_hits([(name, body)])[:5]:
            add("WARN", "JARGON_UNDEFINED", "%s: define or replace '%s' at first use" % (name, term))
    term_brand(name, body, meta, plan)
    if fmt_rules:
        format_rules(name, fr_format(plan), secs, meta)
    fid = plan.get("format") if plan.get("format") in RULES["comms_kinds"] else plan.get("derived_from")
    if fid in RULES["comms_kinds"]:
        comms_check(path, name, RULES["comms_kinds"][fid])
    _ = first


def term_brand(name, body, meta, plan):
    if plain_language and plain_language.is_developer(meta.get("audience", "")):
        return
    sets = plan.get("terminology_sets")
    if not sets:
        pid, p = catlib.profile(meta.get("audience_profile"))
        sets = p.get("terminology_sets", ["internal"]) if pid else ["internal"]
    hits = plain_language.term_hits([(name, body)], sets=tuple(sets)) if plain_language and hasattr(plain_language, "term_hits") else None
    if hits is None:
        print("TERM_BRAND: not run (terminology.json missing)"); return
    for found, where, pref, _why in hits:
        add("WARN", "TERM_BRAND", '%s: "%s -> %s"' % (where, found, pref))


def comms_check(path, name, kind):
    base = os.environ.get("MATERIAL_SKILLS_DIR") or os.path.dirname(catlib.SKILL)
    tool = os.path.join(base, "executive-communications", "scripts", "check_comms.py")
    if not os.path.isfile(tool):
        add("WARN", "COMMS_CHECK", "%s: not run (executive-communications not installed)" % name); return
    cmd = [sys.executable, tool, path, "--kind", kind]
    for k in ("source", "facts"):
        if OPTS.get(k):
            cmd += ["--" + k, OPTS[k]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300); out, rc = r.stdout + r.stderr, r.returncode
    except (OSError, subprocess.SubprocessError) as ex:
        out, rc = str(ex), -1
    n = re.findall(r"(\d+) failed", out)
    if not n:
        add("FAIL", "COMMS_CHECK", "%s: check_comms %s did not report a result (exit %s)" % (name, kind, rc)); return
    print("COMMS_CHECK: check_comms %s, %s failed" % (kind, n[-1]))
    for line in out.splitlines():
        if line.startswith("FAIL"):
            print("  " + line)
    if int(n[-1]):
        add("FAIL", "COMMS_CHECK", "%s: check_comms %s reported %s failed" % (name, kind, n[-1]))


def _block_lines(b):
    k = b.get("type"); out = []
    if k == "paragraph":
        out.append(b.get("text", ""))
    elif k == "bullets":
        out += ["- " + x for x in b.get("items", [])]
    elif k == "numbered":
        out += ["%d. %s" % (i, x) for i, x in enumerate(b.get("items", []), 1)]
    elif k == "procedure":
        out += ["%d. %s" % (i, s.get("text", "")) for i, s in enumerate(b.get("steps", []), 1)]
    elif k in ("card", "callout"):
        if b.get("text"):
            out.append(b["text"])
        out += ["- " + x for x in b.get("items", [])]
    elif k == "table":
        out += ["- " + " | ".join(str(c) for c in r) for r in b.get("rows", [])]
    elif k == "faq":
        for q in b.get("items", []):
            out += ["### " + q.get("q", ""), q.get("a", "")]
    return out


def lint_doc_json(path, plan_path=None, overlay=None):
    """Sheets and documents: each top-level section is checked against the plan anatomy (level-2 titles)."""
    import tempfile
    d = json.load(open(path, encoding="utf-8")); m = d.get("meta", {})
    if "screens" in d or ("sections" in d and any("items" in s for s in d.get("sections", []))):
        tool = "build_module.py" if "screens" in d else "build_form.py"
        r = subprocess.run([sys.executable, os.path.join(HERE, tool), path, "--check"] + (["--brand", OPTS["brand"]] if OPTS.get("brand") else []),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in (r.stdout + r.stderr).splitlines():
            mm = re.match(r"^(FAIL|WARN) \[([A-Z_]+)\] (.*)$", line)
            if mm:
                add(mm.group(1), mm.group(2), mm.group(3))
        print("%s --check: exit %d" % (tool, r.returncode))
        if r.returncode and not any(x[0] == "FAIL" for x in F):
            add("FAIL", "ANATOMY_MATCH", "%s: %s --check exited %d" % (os.path.basename(path), tool, r.returncode))
        R = FR.get("formats", {}).get("skills-check-off")
        if R and "sections" in d and fr_doc_format(m, json.load(open(plan_path, encoding="utf-8")) if plan_path else {}, overlay) == "skills-check-off":
            fr_checkoff_items(os.path.basename(path), R, [it.get("label") or it.get("text") for s in d["sections"] for it in s.get("items", [])
                                                          if it.get("type") not in R["skip_types"]])
        return
    plan = json.load(open(plan_path, encoding="utf-8")) if plan_path else {}
    format_rules(os.path.basename(path), fr_doc_format(m, plan, overlay), fr_doc_model(d), m)
    long_form = plan.get("family") == "long-form" or (not plan and m.get("layout") != "sheet")
    fm = ["---", "format: %s" % (m.get("format") or m.get("doc_type", "")), "title: %s" % m.get("title", ""), "audience: %s" % m.get("audience", "")]
    if m.get("derived_from"):
        fm.append("derived_from: %s" % m["derived_from"])
    if m.get("proper_names"):
        fm += ["proper_names:"] + ["  - %s" % n for n in m["proper_names"]]
    fm += ["sources:"] + ["  - %s" % s for s in m.get("sources", [])] + ["---", ""]
    tmp = tempfile.mkdtemp(prefix="lintdoc_")
    stem = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(path))[0])
    if long_form:
        lines = list(fm)
        for s in d.get("sections", []):
            lines += ["", "## " + s.get("title", "")]
            for b in s.get("blocks", []):
                lines += _block_lines(b)
            for sub in s.get("sections", []):
                for b in sub.get("blocks", []):
                    lines += _block_lines(b)
        fp = os.path.join(tmp, stem + ".doc.json.md"); open(fp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        lint_md(fp, plan_path, overlay, meta_word="meta", words_cap=False, fmt_rules=False)
        return
    for i, s in enumerate(d.get("sections", []), 1):
        lines = list(fm)
        for b in s.get("blocks", []):
            lines += _block_lines(b)
        for sub in s.get("sections", []):
            lines += ["", "## " + sub["title"]]
            for b in sub.get("blocks", []):
                lines += _block_lines(b)
        nm = re.sub(r"[^A-Za-z0-9]+", "_", "%s_%d_%s" % (os.path.splitext(os.path.basename(path))[0], i, s.get("title", "")))[:80] + ".md"
        fp = os.path.join(tmp, nm); open(fp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        lint_md(fp, plan_path, overlay, meta_word="meta", fmt_rules=False)


def has_any(text, keys):
    t = catlib.key(text)
    return any(catlib.key(k) in t for k in keys)


def lint_kit(path, overlay=None):
    kit = json.load(open(path, encoding="utf-8")); base = os.path.dirname(os.path.abspath(path))
    for k in ("title", "change", "audience", "pieces"):
        if not kit.get(k):
            add("FAIL", "KIT_COVERAGE", "kit needs %s" % k)
    stages = set()
    variants = {v.lower(): c for c, vs in (kit.get("names") or {}).items() for v in vs}
    for p in kit.get("pieces", []):
        nm = p.get("label") or p.get("file")
        for k in ("file", "piece", "audience", "channel", "adkar", "send_date", "owner"):
            if not p.get(k):
                add("FAIL", "KIT_COVERAGE", "%s: missing %s" % (nm, k))
        if p.get("adkar") and p["adkar"] not in RULES["adkar"]:
            add("FAIL", "KIT_COVERAGE", "%s: ADKAR stage '%s' (use %s)" % (nm, p["adkar"], ", ".join(RULES["adkar"])))
        stages.add(p.get("adkar"))
        fp = os.path.join(base, p.get("file", ""))
        if not os.path.isfile(fp):
            add("FAIL", "KIT_COVERAGE", "%s: file %s not found" % (nm, p.get("file"))); continue
        txt = open(fp, encoding="utf-8", errors="ignore").read() if fp.endswith((".md", ".json")) else ""
        if fp.endswith(".pdf"):
            try:
                import fitz
                txt = "\n".join(pg.get_text() for pg in fitz.open(fp))
            except Exception:
                txt = ""
        if p.get("piece") in RULES["kit_message_pieces"]:
            for need, keys in RULES["kit_must_say"].items():
                if not has_any(txt, keys):
                    add("FAIL", "KIT_COVERAGE", '%s: no "%s"' % (nm, keys[0]))
        for v, c in variants.items():
            if re.search(r"\b%s\b" % re.escape(v), txt, re.I):
                add("FAIL", "KIT_COVERAGE", "%s: says '%s'; the kit name is '%s'" % (nm, v, c))
        if fp.endswith(".md"):
            lint_md(fp, overlay=overlay)
    kit_adoption(kit, base)
    miss = [s for s in RULES["adkar"] if s not in stages]
    if miss:
        add("WARN", "KIT_COVERAGE", "no piece for ADKAR stage(s): %s" % ", ".join(miss))


def kit_adoption(kit, base):
    """D-47: every kit has an adoption-measures piece in the reinforcement stage; each measure names what is measured,
    where it comes from and a review date; a target only with its source (kit_adoption in material_rules.json)."""
    R = RULES["kit_adoption"]
    ps = [p for p in kit.get("pieces", []) if p.get("piece") == R["piece"]]
    if not ps:
        add("FAIL", "KIT_ADOPTION", R["missing"]); return
    for p in ps:
        nm = p.get("label") or p.get("file")
        if p.get("adkar") != R["stage"]:
            add("FAIL", "KIT_ADOPTION", "%s: ADKAR stage '%s' (adoption measures belong in %s)" % (nm, p.get("adkar"), R["stage"]))
        fp = os.path.join(base, p.get("file", ""))
        if not os.path.isfile(fp):
            continue
        if fp.endswith(".json"):
            ms = json.load(open(fp, encoding="utf-8")).get("measures") or []
            if not ms:
                add("FAIL", "KIT_ADOPTION", "%s: no measures listed" % nm)
            for i, m in enumerate(ms, 1):
                lack = [k for k in R["fields"] if not m.get(k)]
                if lack:
                    add("FAIL", "KIT_ADOPTION", "%s: measure %d missing %s" % (nm, i, ", ".join(lack)))
                if m.get("target") and not m.get("target_source"):
                    add("FAIL", "KIT_ADOPTION", "%s: measure %d has a target with no target_source" % (nm, i))
        else:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
            for k, keys in R["fields_md"].items():
                if not has_any(txt, keys):
                    add("FAIL", "KIT_ADOPTION", '%s: no "%s"' % (nm, keys[0]))
            if re.search(r"(?mi)^\W*(%s)\b(?!\s+source)" % "|".join(map(re.escape, R["target_md"])), txt) and not has_any(txt, R["target_source_md"]):
                add("FAIL", "KIT_ADOPTION", '%s: a target with no "%s"' % (nm, R["target_source_md"][0]))


def lint_ilt(guide, deck):
    meta, body = front(open(guide, encoding="utf-8").read())
    dur = int(re.sub(r"\D", "", str(meta.get("duration_min", "0"))) or 0)
    agenda = next((s for s in sections(body) if catlib.key(s["title"]) == "agenda"), None)
    mins = 0
    if agenda:
        rows = [l for l in agenda["lines"] if l.startswith("|") and not re.match(r"^\|\s*-", l)]
        hdr = [c.strip().lower() for c in rows[0].strip("|").split("|")] if rows else []
        ci = next((i for i, h in enumerate(hdr) if "min" in h), None)
        for r in rows[1:]:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if ci is not None and ci < len(cells):
                m = re.search(r"\d+", cells[ci]); mins += int(m.group()) if m else 0
    if not agenda or mins != dur:
        add("FAIL", "ILT_PAIR", "agenda sums to %d of %d min" % (mins, dur))
    checks = len(re.findall(r"(?m)^\s*(\*\*)?Check:", body))
    d = json.load(open(deck, encoding="utf-8"))
    rs = [i + 1 for i, s in enumerate(d.get("slides", [])) if s.get("role") == "retrieval"]
    for n, sl in enumerate(rs, 1):
        if n > checks:
            add("FAIL", "ILT_PAIR", "retrieval slide %d has no guide Check" % sl)
    if checks > len(rs):
        add("WARN", "ILT_PAIR", "guide has %d Checks, deck has %d retrieval slides" % (checks, len(rs)))


# ---- Format rules (D-54..D-60): data in material_rules.json format_rules; see its "about" for how sections and tables are read.
FR = RULES.get("format_rules", {})


def fr_blank(c):
    return re.sub(r"[*_`]", "", str(c)).strip().lower() in FR.get("blank_cells", [""])


def fr_has_date(t):
    return any(re.search(p, t, re.I) for p in FR.get("date_patterns", []))


def fr_word(t, terms):
    return next((w for w in terms if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(w), t, re.I)), None)


def fr_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def fr_tables(lines):
    """Pipe tables in a section: [{"header": [...], "rows": [[...], ...]}]; the |---| line is skipped."""
    out, cur = [], None
    for l in lines:
        if not l.strip().startswith("|"):
            cur = None; continue
        cells = fr_cells(l)
        if cur is not None and not cur["rows"] and all(re.match(r"^:?-{3,}:?$", c) for c in cells):
            continue
        if cur is None:
            cur = {"header": cells, "rows": []}; out.append(cur)
        else:
            cur["rows"].append(cells)
    return out


def fr_doc_lines(b):
    k = b.get("type"); out = []
    if b.get("title") and k != "table":
        out.append("**%s**" % b["title"])
    if k == "table":
        cols = [str(c) for c in b.get("columns", [])]
        if cols:
            out += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in b.get("rows", [])]
    else:
        out += _block_lines(b)
    return out


def fr_doc_model(d):
    """doc.json -> [{"title", "lines"}] for every section and subsection at any depth (subsection titles become ### lines)."""
    out = []

    def walk(s):
        e = {"title": s.get("title", ""), "lines": []}; out.append(e)
        for b in s.get("blocks", []):
            e["lines"] += fr_doc_lines(b)
        for sub in s.get("sections", []):
            e["lines"] += ["", "### " + sub.get("title", "")] + walk(sub)
        return e["lines"]
    for s in d.get("sections", []):
        walk(s)
    return out


def fr_sec(model, title):
    k = catlib.key(title)
    return next((s for s in model if catlib.key(s["title"]) == k), None)


def fr_table(sec):
    t = fr_tables(sec["lines"]) if sec else []
    return t[0] if t else None


def fr_col(hdr, keys, skip=()):
    return next((i for i, h in enumerate(hdr) if i and i not in skip and any(k in h.lower() for k in keys)), None)


def fr_cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def fr_name(row):
    return re.sub(r"[*_`]", "", row[0]).strip() if row else ""


def fr_format(plan):
    fs = FR.get("formats", {})
    for f in (plan.get("format"), plan.get("derived_from")):
        if f in fs:
            return f
    return None


def fr_doc_format(m, plan, overlay=None):
    if plan:
        return fr_format(plan)
    req = m.get("format") or m.get("doc_type") or ""
    r = catlib.resolve(catlib.load(overlay), req) if req else None
    if not r or not r.get("entry") or r.get("match") == "low":
        return None
    return fr_format({"format": r["id"], "derived_from": r.get("derived_from")})


def fr_letters(cell, R):
    """RACI letters in one cell: 'A', 'R/A', 'A, R', 'AR' or full words (raci.letters)."""
    m = {w: L for L, ws in R["letters"].items() for w in ws}
    out = set()
    for tok in re.split(r"[\s/,;&+()]+", re.sub(r"[*_`]", "", str(cell)).lower()):
        if not tok or tok == "and":
            continue
        if tok in m:
            out.add(m[tok])
        elif len(tok) <= 4 and all(ch in m for ch in tok):
            out.update(m[ch] for ch in tok)
    return out


def fr_raci(name, R, model, meta):
    """D-54: exactly one Accountable and at least one Responsible role per activity row."""
    # check: RACI_ONE_A FAIL
    C = "RACI_ONE_A"
    sec = fr_sec(model, R["section"])
    if not sec:
        return
    t = fr_table(sec)
    if not t:
        add("FAIL", C, "%s: %s has no table (one row per activity, one column per role)" % (name, R["section"])); return
    for row in t["rows"]:
        nm = fr_name(row)
        if not nm:
            continue
        sets = [fr_letters(c, R) for c in row[1:]]
        na = sum(1 for s in sets if "A" in s)
        if na > 1:
            add("FAIL", C, '%s: "%s" has %d Accountable roles (needs exactly one)' % (name, nm, na))
        elif not na:
            add("FAIL", C, '%s: "%s" has no Accountable role (needs exactly one)' % (name, nm))
        if not any("R" in s for s in sets):
            add("FAIL", C, '%s: "%s" has no Responsible role' % (name, nm))


def fr_minutes(v):
    d = re.sub(r"\D", "", str(v or ""))
    return int(d) if d else None


def fr_agenda(name, R, model, meta):
    """D-55: topic minutes add up to the meeting length; each topic has an owner role."""
    # check: AGENDA_TIME FAIL
    # check: AGENDA_TIME WARN
    C = "AGENDA_TIME"
    sec = fr_sec(model, R["section"])
    if not sec:
        return
    t = fr_table(sec)
    if not t:
        add("FAIL", C, "%s: %s has no table (one row per topic with minutes and owner role)" % (name, R["section"])); return
    mi, oi = fr_col(t["header"], R["minutes_headers"]), fr_col(t["header"], R["owner_headers"])
    if mi is None:
        add("FAIL", C, "%s: %s table has no minutes column" % (name, R["section"]))
    if oi is None:
        add("FAIL", C, "%s: %s table has no owner column" % (name, R["section"]))
    total, skip = 0, {catlib.key(x) for x in R["total_labels"]}
    for row in t["rows"]:
        nm = fr_name(row)
        if not nm or catlib.key(nm) in skip:
            continue
        mm = re.search(r"\d+", fr_cell(row, mi)) if mi is not None else None
        total += int(mm.group()) if mm else 0
        if oi is not None and fr_blank(fr_cell(row, oi)):
            add("FAIL", C, '%s: "%s" has no owner role' % (name, nm))
    length = fr_minutes(meta.get(R["length_meta"]))
    if length is None:
        for txt in [str(meta.get("title", ""))] + ["\n".join(s["lines"]) for s in model if catlib.key(s["title"]) in {catlib.key(x) for x in R["length_sections"]}]:
            mm = re.search(R["length_pattern"], txt, re.I)
            if mm:
                length = int(mm.group(1)); break
    if length is None:
        add("WARN", C, "%s: meeting length not found (add %s or 'NN-minute' to the title or Purpose); topics total %d minutes" % (name, R["length_meta"], total))
    elif mi is not None and total != length:
        add("FAIL", C, "%s: agenda topics total %d of %d minutes" % (name, total, length))


def fr_fields(name, R, model, C, what):
    """Shared by D-56 and D-57: each row of the section's table has every field in R["fields"]."""
    sec = fr_sec(model, R["section"])
    if not sec:
        return None
    t = fr_table(sec)
    if not t:
        add("FAIL", C, "%s: %s has no table (one row per %s)" % (name, R["section"], what)); return None
    cols = {f: fr_col(t["header"], ks) for f, ks in R["fields"].items()}
    for f, i in cols.items():
        if i is None:
            add("FAIL", C, "%s: %s table has no %s column" % (name, R["section"], f))
    for row in t["rows"]:
        nm = fr_name(row)
        for f, i in cols.items():
            if nm and i is not None and fr_blank(fr_cell(row, i)):
                add("FAIL", C, '%s: "%s" has a blank %s' % (name, nm, f))
    return t


def fr_metric(name, R, model, meta):
    """D-56: definition, formula, source, refresh and owner role for every metric."""
    # check: METRIC_FIELDS FAIL
    fr_fields(name, R, model, "METRIC_FIELDS", "metric")


def fr_dictionary(name, R, model, meta):
    """D-57: description, data type and source per field; PHI-classified fields carry the PHI flag; Example values that look
    like a phone number or email are PHI_PATTERN (body-wide PHI patterns already cover SSN, MRN and dates of birth)."""
    # check: DICT_FIELDS FAIL
    # check: PHI_PATTERN FAIL
    t = fr_fields(name, R, model, "DICT_FIELDS", "field")
    if not t:
        return
    h = t["header"]
    ci = fr_col(h, R["classification"])
    fi, ei = fr_col(h, R["phi_flag"], skip={ci}), fr_col(h, R["example"])
    for row in t["rows"]:
        nm = fr_name(row)
        if not nm:
            continue
        cls = fr_cell(row, ci)
        if ci is not None and fr_word(cls, R["phi_classes"]) and not fr_word(cls, R["not_phi"]):
            if re.sub(r"[*_`]", "", fr_cell(row, fi)).strip().lower() not in R["flag_yes"]:
                add("FAIL", "DICT_FIELDS", '%s: "%s" is classified PHI but its PHI flag is missing' % (name, nm))
        for label, pat in R["example_patterns"].items():
            if ei is not None and re.search(pat, fr_cell(row, ei)):
                add("FAIL", "PHI_PATTERN", '%s: example for "%s" looks like %s; use a synthetic value' % (name, nm, label))


def fr_labels(lines):
    """Group labels: ### headings and bold-only lines (doc.json subsection and block titles arrive as these)."""
    out = []
    for l in lines:
        m = re.match(r"^\s*#{3,}\s+(.+?)\s*$", l) or re.match(r"^\s*\*\*([^*]+?)\*\*\s*:?\s*$", l)
        if m:
            out.append(m.group(1).strip().rstrip(":").strip())
    return out


def fr_items(lines):
    return [re.sub(r"^\s*([-*\u2022]|\d+[.)])\s+(\[[ xX]\]\s*)?", "", l).strip() for l in lines if re.match(r"^\s*([-*\u2022]|\d+[.)])\s+\S", l)]


def fr_release(name, R, model, meta):
    """D-58: What Changed grouped as New, Changed, Fixed, Removed; Action Needed has a date when users are affected."""
    # check: RELEASE_ACTION FAIL
    C, allowed = "RELEASE_ACTION", {catlib.key(g) for g in R["groups"]}
    sec = fr_sec(model, R["section"])
    if sec:
        labels, vals = fr_labels(sec["lines"]), []
        t = fr_table(sec)
        gi = next((i for i, x in enumerate(t["header"]) if any(k in x.lower() for k in R["group_headers"])), None) if t else None
        if gi is not None:
            vals = [fr_cell(r, gi) for r in t["rows"] if not fr_blank(fr_cell(r, gi))]
        bad = [x for x in labels + vals if catlib.key(x) not in allowed]
        content = [l for l in sec["lines"] if l.strip() and not fr_labels([l])]
        if content and not (labels or vals):
            add("FAIL", C, "%s: %s is not grouped (use %s)" % (name, R["section"], ", ".join(R["groups"])))
        for x in dict.fromkeys(bad):
            add("FAIL", C, "%s: %s group '%s' is not one of %s" % (name, R["section"], re.sub(r"[*_`]", "", x).strip(), ", ".join(R["groups"])))
    aff, act = fr_sec(model, R["affected_section"]), fr_sec(model, R["action_section"])
    affected = not (aff and fr_word(" ".join(aff["lines"]), R["not_affected"]))
    if affected and act and not fr_has_date(" ".join(act["lines"])):
        add("FAIL", C, "%s: %s has no date (users are affected)" % (name, R["action_section"]))


def fr_proposal(name, R, model, meta):
    """D-59: the ask and the decision date in the first 150 words; at least two options."""
    # check: PROPOSAL_ASK FAIL
    C = "PROPOSAL_ASK"
    text = " ".join(l for s in model for l in s["lines"] if l.strip() and not l.lstrip().startswith("#"))
    first = " ".join(re.findall(r"\S+", re.sub(r"[*_`|]", " ", text))[:R["first_words"]])
    miss = [w for w, ok in (("the ask", fr_word(first, R["ask_terms"])), ("the decision date", fr_has_date(first))) if not ok]
    if miss:
        add("FAIL", C, "%s: state the ask and the decision date in the first %d words (missing: %s)" % (name, R["first_words"], ", ".join(miss)))
    sec = fr_sec(model, R["options_section"])
    if sec:
        t = fr_table(sec)
        n = len(fr_labels(sec["lines"])) or len(fr_items(sec["lines"])) or (len([r for r in t["rows"] if fr_name(r)]) if t else 0)
        if n < R["min_options"]:
            add("FAIL", C, "%s: %s lists %d option(s) (at least %d)" % (name, R["options_section"], n, R["min_options"]))


def fr_process(name, R, model, meta):
    """D-59: a numbered text version of the map (screen readers and print)."""
    # check: PROCESS_TEXT FAIL
    sec = fr_sec(model, R["section"])
    t = fr_table(sec)
    n = sum(1 for l in sec["lines"] if re.match(r"^\s*\d+[.)]\s+\S", l)) if sec else 0
    n += sum(1 for r in t["rows"] if re.match(r"^\d+[.)]?$", fr_name(r))) if t else 0
    if n < R["min_steps"]:
        add("FAIL", "PROCESS_TEXT", "%s: add a numbered text version of the map in %s (screen readers and print)" % (name, R["section"]))


def fr_checkoff_items(name, R, items):
    """D-59: each check-off criterion starts with an observable verb (verb list: elearning_rules.json non_observable_verbs)."""
    # check: CHECKOFF_VERBS FAIL
    verbs = json.load(open(os.path.join(catlib.SKILL, "references", R["verbs_file"]), encoding="utf-8"))[R["verbs_key"]]
    pats = []
    for v in sorted(verbs, key=len, reverse=True):
        w = v.split()
        forms = ["be", "is", "are"] if w[0] == "be" else [w[0], w[0] + "s", w[0] + "es", w[0] + "d", w[0] + "ed"]
        pats.append(re.compile(r"^(?:%s)\b%s" % ("|".join(map(re.escape, forms)), "".join(r"\s+" + re.escape(x) + r"\b" for x in w[1:]))))
    leads = sorted(R["lead_ins"], key=len, reverse=True)
    for it in items:
        t = re.sub(r"[*_`]", "", str(it or "")).strip()
        low, changed = t.lower(), True
        while changed:
            changed = False
            for li in leads:
                if re.match(re.escape(li) + r"\b", low):
                    low, changed = low[len(li):].lstrip(), True; break
        m = next((p.match(low) for p in pats if p.match(low)), None)
        if m:
            add("FAIL", "CHECKOFF_VERBS", "%s: \"%s\" uses '%s', which an observer cannot see; start with an observable verb (%s)" % (name, t, m.group(0), R["examples"]))


def fr_checkoff(name, R, model, meta):
    items = []
    for s in model:
        items += fr_items(s["lines"])
        for t in fr_tables(s["lines"]):
            items += [fr_name(r) for r in t["rows"] if fr_name(r)]
    fr_checkoff_items(name, R, items)


def fr_out_scope(sec, R):
    t = fr_table(sec)
    oi = next((i for i, x in enumerate(t["header"]) if fr_word(x, R["out_labels"])), None) if t else None
    if oi is not None:
        return sum(1 for r in t["rows"] if not fr_blank(fr_cell(r, oi)))
    alt = "|".join(re.escape(x) for x in sorted(R["out_labels"], key=len, reverse=True))
    on, n = False, 0
    for l in sec["lines"]:
        s = l.strip()
        m = re.match(r"^(?:#+\s*|[-*]\s+)?\**\s*(?:%s)\s*\**\s*:?\s*\**\s*(.*)$" % alt, s, re.I)
        if m:
            on = True; rest = m.group(1).strip("* ")
            n += 1 if rest and not fr_blank(rest) else 0
            continue
        if on and (s.startswith("#") or re.match(r"^\*\*[^*]+\*\*", s) or re.match(r"^(in scope|in-scope)\b", s, re.I)):
            on = False
        elif on and s and not fr_blank(re.sub(r"^([-*\u2022]|\d+[.)])\s+", "", s)):
            n += 1
    return n


def fr_charter(name, R, model, meta):
    """D-60: a measurable goal (number, percent, date, quarter, count) and a filled out-of-scope list."""
    # check: CHARTER_GOAL WARN
    g, sc = fr_sec(model, R["goal_section"]), fr_sec(model, R["scope_section"])
    if g:
        txt = "\n".join(re.sub(r"^\s*(\d+[.)]|[-*\u2022])\s+", "", l) for l in g["lines"] if l.strip() and not re.match(r"^\s*\|[\s:|-]+\|\s*$", l))
        if not (any(re.search(p, txt) for p in R["measurable"]) or fr_has_date(txt)):
            add("WARN", "CHARTER_GOAL", "%s: %s has no measurable goal (add a number, percent, date, quarter or count)" % (name, R["goal_section"]))
    if sc and not fr_out_scope(sc, R):
        add("WARN", "CHARTER_GOAL", "%s: %s has no out-of-scope items" % (name, R["scope_section"]))


def fr_norm(s):
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in catlib.norm(s))


def fr_plan(name, R, model, meta):
    """D-60: every audience in Audiences has at least one module row in the Curriculum Map."""
    # check: PLAN_COVERAGE WARN
    a, mp = fr_sec(model, R["audience_section"]), fr_sec(model, R["map_section"])
    if not a or not mp:
        return
    t = fr_table(a)
    auds = [fr_name(r) for r in t["rows"] if fr_name(r)] if t else [re.split(r"\s*[:\u2014\u2013]\s*|\s+-\s+", re.sub(r"[*_`]", "", x))[0].strip() for x in fr_items(a["lines"])] or fr_labels(a["lines"])
    mt = fr_table(mp)
    ai = next((i for i, x in enumerate(mt["header"]) if any(k in x.lower() for k in R["audience_headers"])), None) if mt else None
    cells = [fr_cell(r, ai) for r in mt["rows"]] if ai is not None else [" ".join(mp["lines"])]
    if any(fr_norm(c) in {fr_norm(w) for w in R["all_words"]} for c in cells):
        return
    cover = " %s " % " | ".join(fr_norm(c) for c in cells)
    for au in auds:
        if au and " %s " % fr_norm(au) not in cover:
            add("WARN", "PLAN_COVERAGE", "%s: audience '%s' has no module in the %s" % (name, au, R["map_section"]))


def fr_dash(name, R, model, meta):
    """D-60: every metric named in the guide (capitalised words ending in a metric word) is defined in Definitions."""
    # check: DASH_DEFS WARN
    d = fr_sec(model, R["definitions_section"])
    if not d:
        return
    dtxt = " %s " % fr_norm(" ".join(d["lines"]))
    pat = re.compile(r"\b((?:[A-Z][\w%%-]*\s+){0,%d}(?:%s))\b" % (R["max_words"] - 1, "|".join(map(re.escape, R["metric_suffixes"]))))
    seen = set()
    for s in model:
        if s is d:
            continue
        for l in s["lines"]:
            for m in pat.finditer(re.sub(r"[*_`]", "", l)):
                w = m.group(1).split()
                while w and w[0] in R["stop_words"]:
                    w.pop(0)
                nm = " ".join(w)
                if len(w) < 2 or nm in seen:
                    continue
                seen.add(nm)
                if not any(" %s " % fr_norm(" ".join(w[i:])) in dtxt for i in range(len(w) - 1)):
                    add("WARN", "DASH_DEFS", "%s: '%s' is named but not defined in %s" % (name, nm, R["definitions_section"]))


FR_RULES = {"raci": fr_raci, "meeting-agenda": fr_agenda, "metric-definitions": fr_metric, "data-dictionary": fr_dictionary,
            "release-notes": fr_release, "proposal": fr_proposal, "process-map": fr_process, "skills-check-off": fr_checkoff,
            "project-charter": fr_charter, "training-plan": fr_plan, "dashboard-guide": fr_dash}


def format_rules(name, fid, model, meta):
    """Run the format-specific rules for catalog format fid (material_rules.json format_rules.formats)."""
    if fid in FR_RULES and fid in FR.get("formats", {}):
        FR_RULES[fid](name, FR["formats"][fid], model, meta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*"); ap.add_argument("--plan"); ap.add_argument("--overlay")
    ap.add_argument("--kit"); ap.add_argument("--ilt"); ap.add_argument("--deck"); ap.add_argument("--style", action="store_true")
    ap.add_argument("--source"); ap.add_argument("--facts")
    ap.add_argument("--brand", help="brand profile (brand.json); default: the brand of each file's project")
    a = ap.parse_args(); n = 0
    OPTS.update(source=a.source, facts=a.facts, brand=a.brand)
    for f in a.files + [x for x in (a.kit, a.ilt) if x]:
        use_brand(f, a.brand)
    if a.style:
        r = subprocess.run([sys.executable, os.path.join(HERE, "style_tokens.py"), "check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        for line in r.stdout.splitlines():
            if line.startswith("FAIL"):
                F.append(("FAIL", "STYLE_DRIFT", line))
            print(line)
        n += 1
    if a.kit:
        lint_kit(a.kit, a.overlay); n += 1 + len(json.load(open(a.kit, encoding="utf-8")).get("pieces", []))
    if a.ilt:
        lint_ilt(a.ilt, a.deck); n += 1
    for f in a.files:
        (lint_doc_json if f.endswith(".json") else lint_md)(f, a.plan, a.overlay); n += 1
    k = sum(1 for x in F if x[0] == "FAIL")
    print("LINT_MATERIAL: %d file(s), %d failed" % (n, k))
    return 1 if k else 0


if __name__ == "__main__":
    sys.exit(main())
