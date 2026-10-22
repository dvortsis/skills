#!/usr/bin/env python3
"""Plain-language rules shared by the documentation skills (v1.1.0).

Byte-identical copies ship in document-builder, slide-deck, material-composer and training-material-designer so
every skill judges text the same way (edit one, then copy it to the others; the self-tests check they match).
term_hits() reads the shared references/terminology.json plus the project's own house terms when the brand profile
names a terminology file (use_project_terms). Each check takes ordered (where, text) pairs and returns findings; the
calling gate decides FAIL or WARN.
  python3 plain_language.py "Rate ease; Submit the test ID"   -> prints the findings for one line of text
"""
import re, sys

# term -> plain alternative (seed list; a project adds its own under "jargon" in its terminology file)
JARGON = {
    "grain": "time period or level of detail",
    "drill path": "click through to detail",
    "material": "would change a decision",
    "triage": "first review",
    "acceptance rule": "agreed rule",
    "evidence": "numbers and notes",
    "BAN": "headline number",
    "payload": "(internal, remove)",
    "disposition": "decision",
    "mock data": "sample data",
    "scope lock": "approval freezes the design",
    "override": "sign off past a warning",
}
_MAT_SKIP = "(?<!training )(?<!reference )(?<!learning )(?<!course )(?<!support )(?<!source )(?<!raw )(?<!printed )(?<!marketing )"
JARGON_RX = {
    "grain": re.compile(r"(?i)\bgrains?\b"),
    "drill path": re.compile(r"(?i)\bdrill[- ]paths?\b"),
    "material": re.compile(r"(?i)" + _MAT_SKIP + r"\bmaterial(?:ly)?\b(?!s)"),
    "triage": re.compile(r"(?i)\btriag(?:e|ed|es|ing)\b"),
    "acceptance rule": re.compile(r"(?i)\bacceptance rules?\b"),
    "evidence": re.compile(r"(?i)\bevidence\b"),
    "BAN": re.compile(r"\bBANs?\b"),
    "payload": re.compile(r"(?i)\bpayloads?\b"),
    "disposition": re.compile(r"(?i)\bdispositions?\b"),
    "mock data": re.compile(r"(?i)\bmock[- ]data\b"),
    "scope lock": re.compile(r"(?i)\bscope[- ]lock(?:ed)?\b"),
    "override": re.compile(r"(?i)\boverrid(?:e|es|den|ing)\b"),
}
DEFINES_AFTER = re.compile(r"^\s*(\(|\u2014|\u2013| - |:|,? (?:means|meaning|is the|is a|is an|are the|refers to|stands for|which means)\b)", re.I)
DEFINES_BEFORE = re.compile(r"(?i)\b(called|known as|we call|term|define[sd]?)\s+[\"'\u201c*]*$")

ACRONYMS = {"UAT": "user acceptance testing", "UX": "user experience", "SME": "subject matter expert",
            "BAN": "headline number"}  # a project adds its own under "acronyms" in its terminology file

SKILLS = ("document-builder", "slide-deck", "material-composer", "training-material-designer", "confluence-page-builder",
          "executive-communications")
INTERNAL_RX = [
    (re.compile(r"(?i)\b(%s)\b" % "|".join(re.escape(s) for s in SKILLS)), "skill name"),
    (re.compile(r"(?i)\b[\w-]+\.(py|js|json|pptx\.b64|b64)\b"), "script or file name"),
    (re.compile(r"(?i)\b(engine|skill set|skill|template|builder|prompt)\s+v?\d+\.\d+(\.\d+)?\b"), "engine or skill version"),
]
INTERNAL_WORDS = re.compile(r"(?i)\b(builders?|lint(?:s|ed|ing)?|gates?|mocked-up|specs?|JSON|payloads?|macros?|console)\b")
DEVELOPER = re.compile(r"(?i)\b(developers?|engineers?|maintainers?|agent (?:builders?|owners?)|technical staff|analytics engineers?|data developers?)\b")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
SEQUENCE_KINDS = {"process", "timeline", "cycle", "milestones", "layers"}
URL = re.compile(r"\[([^\]]*)\]\([^)]*\)|https?://\S+")

VERBS = set("""
is are was were be been being has have had do does did can could will would should must may might shall
add adds open opens select selects click clicks choose chooses enter enters type types press presses go goes
check checks review reviews rate rates submit submits save saves copy copies paste pastes run runs find finds
read reads write writes record records mark marks set sets use uses show shows see sees start starts stop stops
filter filters sort sorts drag drags drop drops move moves edit edits update updates create creates delete deletes
ask asks answer answers explain explains describe describes compare compares confirm confirms test tests repeat
note notes keep keeps send sends share shares sign signs approve approves reject rejects reopen reopens resolve
resolves reply replies post posts publish publishes attach attaches upload uploads download downloads export exports
print prints scroll scrolls expand expands collapse collapses hover hovers tap taps follow follows return returns
log logs track tracks list lists name names tell tells give gives get gets make makes take takes need needs
want wants help helps let lets look looks pick picks finish finishes continue continues wait waits fix fixes
report reports flag flags assign assigns close closes switch switches turn turns change changes clear clears
reset resets apply applies leave leaves stay stays appear appears happen happens work works cover covers
include includes contain contains hold holds mean means define defines decide decides support supports
explore explores learn learns practice practices watch watches try tries capture captures measure measures
rerun reruns retest retests ship ships launch launches book books call calls arrive arrives route routes finish finishes
join joins sends lands land opens closes moves owns own drops rises falls grows cut cuts halve halves miss misses
""".split())


def is_developer(audience):
    return bool(DEVELOPER.search(audience or ""))


def _plain(text):
    return URL.sub(lambda m: m.group(1) or "", str(text or ""))


def jargon_hits(texts, glossary=()):
    """First use of each jargon term that is neither in the glossary nor defined where it first appears."""
    gl = {g.strip().lower() for g in glossary if g}
    seen, out = set(), []
    for where, text in texts:
        t = _plain(text)
        for term, rx in JARGON_RX.items():
            if term in seen:
                continue
            m = rx.search(t)
            if not m:
                continue
            seen.add(term)
            if term.lower() in gl or any(term.lower() in g or m.group(0).lower() in g for g in gl):
                continue
            spelled = t[max(0, m.start() - 1):m.start()] == "(" and t[m.end():m.end() + 1] == ")"
            if spelled or DEFINES_AFTER.search(t[m.end():]) or DEFINES_BEFORE.search(t[:m.start()]):
                continue
            out.append((term, where, JARGON[term]))
    return out


def internal_hits(texts):
    """Internal tool, skill, script, engine or version names and build words (UI labels in **bold** are exempt from
    the word list, never from skill or script names)."""
    out = []
    for where, text in texts:
        t = _plain(text)
        for rx, what in INTERNAL_RX:
            m = rx.search(t)
            if m:
                out.append((m.group(0), where, what))
        m = INTERNAL_WORDS.search(BOLD.sub("", t))
        if m:
            out.append((m.group(0), where, "build-process word"))
    return out


def acronym_hits(texts):
    """Acronyms whose first appearance is not spelled out ("user acceptance testing (UAT)" or "UAT (user acceptance testing)")."""
    seen, out = set(), []
    for where, text in texts:
        t = _plain(text)
        for ac, full in ACRONYMS.items():
            if ac in seen:
                continue
            m = re.search(r"\b%ss?\b" % ac, t)
            if not m:
                continue
            seen.add(ac)
            after, before = t[m.end():m.end() + 4], t[:m.start()]
            if re.match(r"s?\s*\(", after) or re.search(r"\(\s*$", before) and re.search(r"[A-Za-z]{3,}\s*\(\s*$", before):
                continue
            if full.lower().split()[0] in before[-60:].lower():
                continue
            out.append((ac, where, full))
    return out


_PROJECT_TERMS = []


def use_project_terms(path):
    """Add a project's house-style terms (same format as references/terminology.json: sets, plus optional jargon and
    acronyms) to every later check. Called by the gates with the brand profile's `terminology` file."""
    import json
    if not path or path in _PROJECT_TERMS:
        return
    with open(path, encoding="utf-8") as f:
        extra = json.load(f)
    _PROJECT_TERMS.append(path)
    for term, plain in (extra.get("jargon") or {}).items():
        JARGON[term] = plain
        JARGON_RX[term] = re.compile(r"(?i)\b%ss?\b" % re.escape(term))
    ACRONYMS.update(extra.get("acronyms") or {})


def _terminology():
    import json, os
    here = os.path.dirname(os.path.abspath(__file__))
    data = None
    for p in (os.path.join(here, "..", "references", "terminology.json"), os.path.join(here, "terminology.json")):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            break
    if data is None:
        return None
    for p in _PROJECT_TERMS:
        with open(p, encoding="utf-8") as f:
            extra = json.load(f)
        for name, rules in (extra.get("sets") or {}).items():
            data["sets"].setdefault(name, []).extend(rules)
        data.setdefault("months_ap", {}).update(extra.get("months_ap") or {})
    return data


_DATE_RX = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
                      r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)(\.?)\s+(\d{1,2})(st|nd|rd|th)?\b")
_SKIP_HOST = re.compile(r"(?i)[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|io|co|gov|edu)(?:/[\w/.%-]*[\w/])?")


def term_hits(texts, sets=("internal",)):
    """Off-style terms: returns (found, where, preferred, why) per hit, or None when the shared terminology.json is
    missing (the caller reports the check as not run). sets: 'internal' (default) plus any audience set the project's
    terminology file defines (loaded only with that audience profile). Email addresses and domains are skipped."""
    data = _terminology()
    if data is None:
        return None
    rules = [r for s in sets for r in data["sets"].get(s, [])]
    months = data.get("months_ap", {})
    out = []
    for where, text in texts:
        t = _SKIP_HOST.sub(lambda m: " " * len(m.group(0)), _plain(text))
        for r in rules:
            k = r["kind"]
            if k == "case":
                for m in re.finditer(r"(?<![\w@./-])%s(?![\w@-])" % re.escape(r["word"]), t, re.I):
                    if m.group(0) != r["word"]:
                        out.append((m.group(0), where, r["word"], r["why"]))
            elif k == "apdate":
                for m in _DATE_RX.finditer(t):
                    ap = "%s %s" % (months.get(m.group(1).lower(), m.group(1)), m.group(3))
                    if m.group(0) != ap:
                        out.append((m.group(0), where, ap, r["why"]))
            elif k == "midsentence":
                for m in re.finditer(r["pattern"], t):
                    before = t[:m.start()].rstrip(" *_\"'(")
                    if before and before[-1] not in ".!?:#\n|-" and not before.endswith("\n"):
                        out.append((m.group(0), where, m.group(0).lower(), r["why"]))
            else:
                for m in re.finditer(r["pattern"], t):
                    if "suggest_template" in r:
                        more = "More" if m.group(1).isupper() else "more"
                        sug = r["suggest_template"].replace("{More}", more).replace("{2}", m.group(2))
                        found = m.group(0)
                        nm = re.match(r"\d[\d,.]*", t[m.end() - 1:])
                        if nm:
                            found, sug = found[:-1] + nm.group(0), sug[:-1] + nm.group(0)
                        out.append((found, where, sug, r["why"]))
                    else:
                        out.append((m.group(0), where, r["suggest"], r["why"]))
    return out


def _words(s):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", s)


FOLLOW = {"the", "a", "an", "to", "from", "with", "by", "in", "on", "for", "until", "each", "every", "all", "your", "their",
          "its", "this", "that", "it", "them", "up", "out", "into", "over", "back", "one", "two", "three"}


def has_verb(s):
    ws = _words(s)
    for i, w in enumerate(ws):
        lw = w.lower()
        if lw in VERBS or (len(lw) > 4 and (lw.endswith("ed") or lw.endswith("ing"))):
            return True
        nxt = ws[i + 1].lower() if i + 1 < len(ws) else ""
        if i > 0 and len(lw) >= 4 and lw.endswith("s") and not lw.endswith(("ss", "us", "is")) and nxt in FOLLOW:
            return True
    return False


def telegraphic(text, detail=True):
    """Shorthand: two or more short clauses joined by semicolons (each 4 words or fewer), or (details only) a phrase
    of 4+ words with no verb. Returns the reason or None."""
    t = BOLD.sub(lambda m: m.group(1), _plain(text)).strip()
    if not t:
        return None
    parts = [p for p in re.split(r"\s*;\s*", t) if p.strip()]
    if len(parts) >= 2 and all(len(_words(p)) <= 4 for p in parts):
        return "short clauses joined by semicolons"
    if detail and len(_words(t)) >= 4 and not has_verb(t):
        return "no verb"
    return None


if __name__ == "__main__":
    line = " ".join(sys.argv[1:])
    print({"telegraphic": telegraphic(line), "jargon": jargon_hits([("arg", line)]), "internal": internal_hits([("arg", line)]),
           "acronyms": acronym_hits([("arg", line)])})
