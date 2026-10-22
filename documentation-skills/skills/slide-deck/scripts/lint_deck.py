#!/usr/bin/env python3
"""Design and storytelling gate for decks. Checks deck.json (story, density, visual fit) and, when given, the
built .pptx (bounds, overlap, text fit, fonts, colors, alert-color use, alt text, notes).

  python3 scripts/lint_deck.py deck.json [--pptx out/Deck.pptx] [--draft] [--story] [--brand brand.json]

Colors and fonts are checked against the project brand the build used (scripts/brand.py; same lookup order).
Prints `LINT: <n> checks, <f> failed, <w> warnings`, then FAIL/WARN lines with a code and slide number.
--story also prints the title-only read-through (the ghost deck). Exit 1 on any FAIL. --draft turns a missing
screenshot into a warning; a deck built or linted with --draft is never final.
"""
import argparse, json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling modules (iconlib) even under python -P / safe_path
import plain_language as PL  # noqa: E402  (shared with the document, composer and training skills)
import brand as BR  # noqa: E402  (project brand)

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "..", "assets", "theme.json"), encoding="utf-8"))
G = T["slide"]
C = T["colors"]
LEGACY_VALUES = {"blue": "primary", "navy": "dark"}


def normalize(deck):
    """Accept the older color names in deck.json (meta.cover blue/navy, split panel navy) as the role names."""
    m = deck.get("meta") or {}
    if m.get("cover") in LEGACY_VALUES:
        m["cover"] = LEGACY_VALUES[m["cover"]]
    for d in (deck.get("slides") or []) + (deck.get("appendix") or []):
        if isinstance(d, dict) and d.get("panel") in LEGACY_VALUES:
            d["panel"] = LEGACY_VALUES[d["panel"]]
    return deck
W_IN = G.get("width_in", 13.333)
GENERIC = {"agenda", "overview", "background", "summary", "executive summary", "next steps", "q&a", "questions", "thank you",
           "key takeaways", "introduction", "results", "data", "update", "status", "findings", "recommendations", "appendix",
           "conclusion", "discussion", "timeline", "metrics", "dashboard"}
BANNED = re.compile(r"(?i)\b(leverage|synerg\w*|unlock\w*|game[- ]chang\w*|revolutioni[sz]\w*|seamless\w*|cutting[- ]edge|robust|delve|empower\w*|world[- ]class|best[- ]in[- ]class)\b")
VISUAL = {"chart", "kpi", "screenshot", "diagram", "anatomy", "annotated"}
CONTENT = {"bullets", "chart", "kpi", "screenshot", "diagram", "table", "statement", "hero", "cards", "split", "shift", "steps", "checklist", "qa",
           "anatomy", "annotated", "callouts", "article"}
ICON_FIELDS = {"cards": "cards", "callouts": "cards", "contact": "contacts", "annotated": "annotations"}
ICON_DIAGRAMS = {"process", "timeline", "cycle", "milestones"}
FIG_LAYOUTS = {"screenshot", "annotated", "anatomy"}
ONE_LINE_TITLES = {"table", "steps", "diagram:matrix", "diagram:comparison"}
NO_SPACE_CHECK = {"hero", "section", "statement", "closing", "contact", "contents", "summary"}
UI_VERB = re.compile(r"(?i)\b(click|select|open|choose|enter|press|tap|drag|expand|scroll|type|sign in)\b")
NOTES_TAG = re.compile(r"(?im)\bpath\s*:\s*(foundation|standard|advanced)\b|^\s*\[?(retrieval|transfer|foundation|bloom|recall)\]?\s*[:.]?\s*$|\[(retrieval|transfer|recall)\]|\b(retrieval|transfer)\s*:")
STOP = {"this", "that", "with", "from", "your", "their", "what", "when", "where", "which", "into", "than", "then", "them", "they", "have", "will",
        "each", "every", "only", "more", "most", "less", "over", "under", "about", "after", "before", "slide", "shows", "show", "page"}


def keyset(*texts):
    out = set()
    for t in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z']+", str(t or "")):
            w = w.lower().strip("'")
            if len(w) >= 4 and w not in STOP:
                for suf in ("ing", "ed", "es", "s", "e"):
                    if len(w) > 4 and w.endswith(suf):
                        w = w[: -len(suf)]; break
                out.add(w)
    return out
MESSAGES = {
    "point": ("A decision, principle or turning point, stated plainly", ["hero:statement", "statement", "split:number", "split:screenshot"]),
    "number": ("One number that matters", ["hero:number", "split:number", "kpi", "kpi:minimal", "kpi:dark"]),
    "numbers": ("Two to four headline numbers", ["kpi", "kpi:minimal", "kpi:dark"]),
    "change": ("One metric before and after", ["shift", "chart", "kpi", "kpi:minimal"]),
    "comparison": ("A comparison, ranking, trend or mix across categories or time", ["chart", "table", "diagram:comparison"]),
    "flow": ("Loss or conversion through stages", ["diagram:funnel", "chart"]),
    "loop": ("A repeating cycle", ["diagram:cycle"]),
    "sequence": ("Ordered steps or a process", ["diagram:process", "diagram:milestones", "diagram:timeline", "steps"]),
    "plan": ("Work or milestones by period", ["diagram:roadmap", "diagram:milestones", "diagram:timeline", "table"]),
    "structure": ("The parts of a whole: tiers, an architecture, the anatomy of a screen or system", ["diagram:layers", "anatomy", "cards"]),
    "tradeoff": ("Options against two criteria", ["diagram:matrix"]),
    "options": ("A choice between two or more options", ["diagram:comparison", "cards", "table"]),
    "status": ("Readiness, progress or open items", ["checklist", "table", "kpi", "kpi:minimal"]),
    "questions": ("Questions the audience will ask, with answers", ["qa"]),
    "ideas": ("Two to four parallel ideas, changes or principles", ["cards", "bullets", "steps"]),
    "walkthrough": ("How to read or use a screen, object or document", ["annotated", "screenshot", "anatomy", "split:screenshot"]),
    "guidance": ("Examples, tips and warnings", ["callouts", "cards"]),
    "context": ("Background the audience needs before the rest", ["article", "bullets", "statement", "split:screenshot"]),
}


def shotlist_path(meta, base, deck_path=None):
    """meta.shotlist, or <deck stem>.shotlist.md beside deck.json, if it exists."""
    cands = [meta.get("shotlist")] if meta.get("shotlist") else []
    if deck_path:
        b = os.path.basename(deck_path)
        cands.append(re.sub(r"(\.deck)?\.json$", "", b) + ".shotlist.md")
    for c in cands:
        p = c if os.path.isabs(c) else os.path.join(base, c)
        if os.path.isfile(p):
            return p
    return None


def lkey(d):
    """The layout as the message map sees it: diagram kinds, hero and split forms, and KPI styles are distinct."""
    lay = d.get("layout")
    if lay == "diagram":
        return "diagram:" + str((d.get("diagram") or {}).get("kind"))
    if lay == "hero":
        return "hero:number" if d.get("value") else "hero:statement"
    if lay == "split":
        return "split:" + str((d.get("visual") or {}).get("kind"))
    if lay == "kpi":
        return "kpi:dark" if d.get("dark") else ("kpi:minimal" if d.get("style") == "minimal" else "kpi")
    return lay


FRAME_CODE = {"summary": "S", "contents": "S", "closing": "C", "contact": "C"}
DIAGRAM_KINDS = ("process", "timeline", "matrix", "comparison", "funnel", "cycle", "roadmap", "layers", "milestones")
CALLOUT_KINDS = ("example", "tip", "note", "warning")
CHECK_STATUS = ("done", "in_progress", "open", "at_risk")
CENTERED_LAYOUTS = {"kpi", "cards", "hero", "shift", "section", "anatomy", "callouts", "contact"}
CENTERED_DIAGRAMS = {"funnel", "cycle", "comparison", "matrix", "process", "layers", "milestones"}
TONE_CODE = {"white": "W", "tint": "L", "dark": "N", "primary": "B"}
FRAME = {"summary", "closing", "contents", "contact"}
TAKEAWAY_OK = {"chart", "screenshot", "diagram", "table", "kpi", "shift"}
RHYTHM_CODE = {"hero": "H", "data": "D", "visual": "V", "text": "T"}


def archetype(d):
    """Layout archetype for pacing: hero (dark or big-type breather), data, visual or text. Frame slides return None."""
    lay = d.get("layout")
    if lay in FRAME:
        return None
    if lay in ("hero", "section", "statement") or (lay == "kpi" and d.get("dark")):
        return "hero"
    if lay in ("kpi", "chart", "table", "shift"):
        return "data"
    if lay == "split":
        return "data" if (d.get("visual") or {}).get("kind") == "number" else "visual"
    if lay in ("screenshot", "diagram", "anatomy", "annotated"):
        return "visual"
    return "text"


def tone(d):
    """Dominant background tone: dark (hero, dark KPI, dark split panel), primary (section), tint (tint band or tint split panel), white."""
    lay = d.get("layout")
    if lay == "hero" or (lay == "kpi" and d.get("dark")) or (lay == "split" and d.get("panel") == "dark"):
        return "dark"
    if lay == "section":
        return "primary"
    if d.get("tint") or lay == "split":
        return "tint"
    return "white"


def variant(d):
    """What counts as 'the same layout' for LAYOUT_REPEAT: dark and light KPI slides, and diagrams of different kinds, differ."""
    lay = d.get("layout")
    if lay == "kpi":
        return "kpi:dark" if d.get("dark") else ("kpi:minimal" if d.get("style") == "minimal" else "kpi")
    if lay == "diagram":
        return "diagram:" + str((d.get("diagram") or {}).get("kind"))
    if lay == "hero":
        return "hero:number" if d.get("value") else "hero:statement"
    return lay


def quick_check_pairs(main):
    """D-25: slide numbers of each quick check ("role": "retrieval") and the answer slide right after it ("role": "answer").
    The ratio rules (VISUAL_RATIO, HERO_MAX, LAYOUT_OVERUSE) count such a pair as one interactive unit, not as text slides."""
    out = set()
    for (n0, d0), (n1, d1) in zip(main, main[1:]):
        if d0.get("role") == "retrieval" and d1.get("role") == "answer":
            out |= {n0, n1}
    return out


def rhythm(slides):
    return " ".join(RHYTHM_CODE.get(archetype(d), FRAME_CODE.get(d.get("layout"), "?")) for d in slides)


def tones(slides):
    return " ".join(TONE_CODE[tone(d)] if archetype(d) else FRAME_CODE.get(d.get("layout"), "?") for d in slides)
CHART_TYPES = {"bar", "column", "line", "stacked_bar", "stacked_column"}


STATUSES = ("FIXED \u00b7 AWAITING RETEST", "FIX PENDING RELEASE", "NO ACTION REQUIRED", "DECLINED \u2013 BEST PRACTICE", "DECLINED - BEST PRACTICE",
            "DEFERRED TO PHASE 2", "AWAITING TRIAGE", "NOT A DEFECT", "FIX REQUIRED", "NOT STARTED", "IN PROGRESS", "IN TESTING", "NOT RUN",
            "ACCEPTED", "RE-OPENED", "VERIFIED", "RESOLVED", "BLOCKED", "PASS", "FAIL", "OPEN", "DONE", "LIVE")
STATUS_AT_START = re.compile(r"^(%s)(?=$|[\s,.;:\u2013-])" % "|".join(re.escape(x) for x in STATUSES))
SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "if", "as", "at", "by", "in", "of", "off", "on", "per", "to", "up", "via", "vs", "vs."}


from text_rules import proper, add_proper_nouns  # noqa: E402  one Proper Case and hyphen rule for decks, documents and pages (text_rules.py)


BRAND = BR.Brand({}, HERE, "fallback")  # replaced by use_brand(); fonts and metrics are read from it at call time


def role_of(font):
    """The brand role a run's font name plays: display, mono or body (unknown names measure as body)."""
    f = BRAND.fonts
    if font and font == f.get("display") and font != f.get("body"):
        return "display"
    if font and font == f.get("mono") and font != f.get("body"):
        return "mono"
    return "body"


def LH(font=None, bold=False):
    """Single line spacing of a font as a fraction of its size, from the font file (what PowerPoint lays out)."""
    return BRAND.metrics(role_of(font), bold)["line"]


def FL(font=None, bold=False):
    """Optical center of a first line below the top of its text (fraction of the size): ascent minus half the cap height."""
    return BRAND.metrics(role_of(font), bold)["first"]


def widow(fit, lines, size, font, bold, avail, title):
    """The one orphan rule build and lint share. Titles (ORPHAN): the last of two or more lines is under a quarter
    of the width, or two words or fewer under half of it. Other texts (LAST_LINE_ORPHAN): the last line is one word,
    a lone separator or a parenthesis on its own."""
    if len(lines) < 2:
        return False
    last = lines[-1].strip()
    if title:
        lw = fit.width(last, size, font, bold)
        return lw < 0.25 * avail or (len(fit.words_of(last)) <= 2 and lw < 0.5 * avail)
    return len(fit.words_of(last)) == 1 or last in ("·", "-", "–") or bool(re.fullmatch(r"\(.*\)", last))


def use_brand(b):
    """Make build and lint judge one brand: its palette and fonts, its font files and metrics, its house terms and
    its proper nouns."""
    global BRAND
    BRAND = b
    b.apply(T)
    if b.terminology:
        PL.use_project_terms(b.terminology)
    add_proper_nouns((b.display_name + " " + b.org).split())
    return b


def words(s):
    """Word count; a contraction such as "Doesn't" counts as one word."""
    return len(re.findall(r"[\w%$.,/&+'\u2019-]+", s or ""))


class Lint:
    def __init__(self, draft):
        self.draft, self.checks, self.fails, self.warns = draft, 0, [], []

    def check(self, ok, code, n, msg, warn=False):
        self.checks += 1
        if not ok:
            (self.warns if warn else self.fails).append("%s [%s] slide %s: %s" % ("WARN" if warn else "FAIL", code, n, msg))
        return ok

    # ---------------- deck.json ----------------
    def deck(self, deck, base):
        import iconlib
        added, rejected = iconlib.load_overlay(os.path.join(base, "icons.local.json"))
        self.check(not rejected, "ICON_OVERLAY", "-", "icons.local.json has icons that aren't Tabler outline icons: %s" % ", ".join(rejected[:5]))  # check: ICON_OVERLAY FAIL
        m = deck.get("meta", {})
        self.guide = m.get("type", "decision") in ("inform", "guide", "training")
        self.check(m.get("type", "decision") in ("decision", "inform", "guide", "training"), "META_TYPE", 1, "meta.type must be decision (the deck asks for a decision) or inform (it explains, trains, documents or updates; guide and training are aliases)")  # check: META_TYPE FAIL
        self.base = base
        self.check(m.get("cover_align", "left") in ("left", "center"), "META_TYPE", 1, "meta.cover_align must be left (default) or center")  # check: META_TYPE FAIL
        for k in ("title", "audience", "big_idea") + (() if self.guide else ("decision",)):
            self.check(bool(m.get(k)), "META_MISSING", 1, "meta.%s is required (who is it for, %s, the one-sentence story)" % (k, "what it helps them do" if self.guide else "what should they decide"))  # check: META_MISSING FAIL
        self.check(words(m.get("big_idea")) <= 30, "BIG_IDEA_LENGTH", 1, "big_idea should be one sentence of 30 words or fewer")  # check: BIG_IDEA_LENGTH FAIL
        self.check(words(m.get("title")) <= 12, "COVER_TITLE", 1, "cover title over 12 words; the template allows three lines at most")  # check: COVER_TITLE FAIL
        self.check(m.get("logo") in (None, "none"), "LOGO_OPTION", 1, "meta.logo can only be omitted (the project logo from the brand) or \"none\"; to use another logo, set it in the brand profile (references/brand.md)")  # check: LOGO_OPTION FAIL
        self.check(m.get("cover", "white") in ("white", "primary", "dark"), "COVER_STYLE", 1, "meta.cover must be white, primary or dark")  # check: COVER_STYLE FAIL
        self.accent(1, m.get("title", ""), m.get("title_accent"))
        self.meta = m
        main, appx = deck.get("slides", []), deck.get("appendix", [])
        n, numbered = 1, []
        for d in main:
            n += 1; numbered.append((n, d, False))
        if appx:
            n += 1
            for d in appx:
                n += 1; numbered.append((n, d, True))
        titles = {}
        for n, d, in_appx in numbered:
            self.slide(n, d, base, in_appx)
            t = (d.get("title") or "").strip().lower()
            if t:
                self.check(t not in titles, "DUP_TITLE", n, "same title as slide %s" % titles.get(t))  # check: DUP_TITLE FAIL
                titles.setdefault(t, n)
        content = [(n, d) for n, d, a in numbered if not a and d.get("layout") in CONTENT]
        if self.guide:
            if len(main) >= 6:
                self.check(main[0].get("layout") in ("summary", "contents"), "OPENER_FIRST", 2, "an inform deck of 6+ slides opens with a summary (the one thing to remember) or contents (where to find each part)")  # check: OPENER_FIRST FAIL
            self.check(bool(main) and main[-1].get("layout") in ("contact", "closing"), "CLOSING_LAST", n, "an inform deck ends on a closing slide (next steps) or a contact slide (where to get help)")  # check: CLOSING_LAST FAIL
        else:
            if len(main) >= 5:
                self.check(main[0].get("layout") == "summary", "SUMMARY_FIRST", 2, "decks of 5+ slides open with a summary slide that states the answer")  # check: SUMMARY_FIRST FAIL
            self.check(bool(main) and main[-1].get("layout") == "closing", "CLOSING_LAST", n, "a decision deck ends on a closing slide with the ask")  # check: CLOSING_LAST FAIL
        for k, d, a in numbered:
            if a:
                continue
            lay = d.get("layout")
            if lay in ("summary", "contents"):
                self.check(main and d is main[0], "FRAME_POSITION", k, "%s slides open the deck; they can't sit in the middle" % lay)  # check: FRAME_POSITION FAIL
            if lay in ("closing", "contact"):
                self.check(main and d is main[-1], "FRAME_POSITION", k, "%s slides close the deck; they can't sit in the middle" % lay)  # check: FRAME_POSITION FAIL
            if lay in CONTENT:
                msg = d.get("message")
                if self.check(bool(msg), "MESSAGE_MISSING", k, "say what this slide's message is (message: one of %s) before choosing its layout" % ", ".join(MESSAGES)):  # check: MESSAGE_MISSING FAIL
                    if self.check(msg in MESSAGES, "MESSAGE_UNKNOWN", k, "message %r is not one of %s" % (msg, ", ".join(MESSAGES))):  # check: MESSAGE_UNKNOWN FAIL
                        self.check(lkey(d) in MESSAGES[msg][1], "MESSAGE_FIT", k, "a %s slide can't tell a %r message; use one of %s" % (lkey(d), msg, ", ".join(MESSAGES[msg][1])))  # check: MESSAGE_FIT FAIL
        if sum(1 for d in main if d.get("layout") == "contents") and len(main) < 6:
            self.check(False, "LAYOUT_FIT", 2, "a deck of %d slides doesn't need a contents slide; open with a summary" % len(main), warn=True)  # check: LAYOUT_FIT WARN
        pairs = quick_check_pairs([(k, d) for k, d, a in numbered if not a])
        ratio = [(k, d) for k, d in content if k not in pairs]  # D-25: a quick check and its answer are one interactive unit, neither text nor visual
        if len(ratio) >= 3:
            vis = sum(1 for _, d in ratio if d.get("layout") in VISUAL | {"split"} or (d.get("layout") == "hero" and d.get("value")))
            self.check(vis / len(ratio) >= 0.5, "VISUAL_RATIO", "-", "%d of %d content slides carry a visual; at least half should (chart, KPI, screenshot or diagram)" % (vis, len(ratio)))  # check: VISUAL_RATIO FAIL
        prev, prev_d = None, {}
        for n, d in content:
            txt = d.get("layout") in ("bullets", "statement")
            pair = d.get("role") == "answer" and prev_d.get("role") == "retrieval"  # a quick check and its answer belong together
            self.check(not (txt and prev) or pair, "TEXT_RUN", n, "two text-only slides in a row; turn one into a visual or merge them")  # check: TEXT_RUN FAIL
            prev, prev_d = txt, d
        self.pacing([(k, d) for k, d, a in numbered if not a])
        self.screenshots(deck, numbered, base)
        self.sequence(deck, numbered)
        self.terms(deck)
        self.rhythm = rhythm(main)
        self.msgs = ["%d. [%s] %s: %s" % (k, d.get("message", "-"), lkey(d), (d.get("title") or d.get("text") or "")[:60]) for k, d, a in numbered if not a and d.get("layout") in CONTENT]
        self.tones = tones(main)
        self.check(len(main) <= 20, "DECK_LENGTH", "-", "main deck has %d slides; move detail to the appendix" % len(main))  # check: DECK_LENGTH FAIL
        self.check(len(main) <= 12, "DECK_LENGTH", "-", "main deck has %d slides; aim for 12 or fewer" % len(main), warn=True)  # check: DECK_LENGTH WARN
        return numbered

    TERM_FAMILIES = [("approve", r"\bapprov(?:e|es|ed|al|ing)\b"), ("sign-off", r"\bsign(?:ed)?[- ]?off\b|\bsignoff\b")]
    TERM_GROUPS = [["approve", "sign-off"]]

    def sequence(self, deck, numbered):
        """RETRIEVAL_ANSWER: every quick check is followed by its answer on a slide; TERM_CONSISTENT: one name per step."""
        main = [(k, d) for k, d, a in numbered]
        for i, (k, d) in enumerate(main):
            if d.get("role") == "retrieval":
                nxt = main[i + 1][1] if i + 1 < len(main) else {}
                ok = nxt.get("role") == "answer" or str(nxt.get("title") or nxt.get("text") or "").strip().lower().startswith("answer")
                self.check(ok, "RETRIEVAL_ANSWER", k, "a quick check needs the next slide to give the answer on the slide itself (\"role\": \"answer\")")  # check: RETRIEVAL_ANSWER FAIL
        def names(d):  # step names: titles and the labels of steps, cards, nodes and callouts, not ordinary prose
            g = d.get("diagram") or {}
            items = (d.get("steps") or []) + (d.get("cards") or []) + (g.get("nodes") or []) + [g.get("left") or {}, g.get("right") or {}]
            return [str(d.get("title") or "")] + [str(it.get("label") or it.get("title") or "") for it in items if isinstance(it, dict)]
        blob = " | ".join(x for _, d in main for x in names(d))
        for grp in self.TERM_GROUPS:
            used = [name for name, rx in self.TERM_FAMILIES if name in grp and re.search("(?i)" + rx, blob)]
            self.check(len(used) <= 1, "TERM_CONSISTENT", "-", "one step, two names: %s; pick one and use it on every slide" % " and ".join("'%s'" % u for u in used))  # check: TERM_CONSISTENT FAIL

    def terms(self, deck):
        """TERM_BRAND (D-39): off-style terms in slide text and notes, from the shared terminology.json plus the project's
        own house terms (brand profile `terminology`); WARN only, skipped for developer audiences like the jargon checks."""
        m = deck.get("meta", {})
        if PL.is_developer(m.get("audience", "")):
            return
        skip = {"image", "alt", "layout", "message", "icon", "role", "style", "kind", "highlight", "series", "source"}
        def strings(x):
            if isinstance(x, str):
                yield x
            elif isinstance(x, list):
                for v in x:
                    yield from strings(v)
            elif isinstance(x, dict):
                for k, v in x.items():
                    if k not in skip:
                        yield from strings(v)
        texts = [("-", str(m.get(k) or "")) for k in ("title", "subtitle", "big_idea")]
        for n, d in enumerate(list(deck.get("slides") or []) + list(deck.get("appendix") or []), 1):
            texts += [(str(n), s) for s in strings(d)]
        hits = PL.term_hits(texts)
        if hits is None:
            self.warns.append("WARN [TERM_BRAND] slide -: TERM_BRAND: not run (terminology.json missing)"); return
        self.checks += 1
        for found, where, pref, why in hits[:12]:
            self.check(False, "TERM_BRAND", where, '"%s -> %s" (%s)' % (found, pref, why), warn=True)  # check: TERM_BRAND WARN

    def screenshots(self, deck, numbered, base):
        """SCREENSHOT_SLIDES: an inform or training deck that walks through a screen on 5+ slides shows it on 3+."""
        m = deck.get("meta", {})
        vis = lambda d: json.dumps({k: v for k, v in d.items() if k not in ("notes", "image", "alt", "layout", "message", "icon", "series", "role")})
        ui = [k for k, d, a in numbered if d.get("layout") in FIG_LAYOUTS or UI_VERB.search(vis(d))]
        figs = [k for k, d, a in numbered if d.get("layout") in FIG_LAYOUTS or (d.get("layout") == "split" and d.get("image"))]
        self.ui_slides = []
        if not self.guide or len(ui) < 5 or len(figs) >= 3:
            self.checks += 1; return
        self.ui_slides = [k for k in ui if k not in figs]
        sl = shotlist_path(m, base, getattr(self, "deck_path", None))
        if sl:
            msg = "shot list pending (%s): %d slides walk through a screen, %d show it; add the screenshots, then rebuild" % (os.path.basename(sl), len(ui), len(figs))
        elif self.draft:
            msg = "shot list pending: %d slides walk through a screen, %d show it; the --draft build writes <deck>.shotlist.md" % (len(ui), len(figs))
        else:
            msg = "%d slides walk through a screen but only %d show it; add screenshot, annotated or anatomy slides (3+), or build with --draft for a shot list" % (len(ui), len(figs))
        self.check(False, "SCREENSHOT_SLIDES", "-", msg, warn=True)  # check: SCREENSHOT_SLIDES WARN

    def pacing(self, main):
        """Layout archetype alternation and rhythmic pacing for the main deck (the appendix is exempt)."""
        body = [(n, d, archetype(d)) for n, d in main if archetype(d)]
        for (n0, d0), (n1, d1) in zip(main, main[1:]):
            if variant(d0) != variant(d1):
                continue
            series = (d0.get("series") and d0.get("series") == d1.get("series")) or (d0.get("role") == "retrieval" and d1.get("role") == "answer")
            self.check(bool(series), "LAYOUT_REPEAT", n1, "same layout as slide %s (%s); alternate layouts, or mark a deliberate walkthrough with the same \"series\" value" % (n0, variant(d1)))  # check: LAYOUT_REPEAT FAIL
        runs = {}
        for n, d in main:
            if d.get("series"):
                runs.setdefault(d["series"], []).append(n)
        for name, ns in runs.items():
            self.check(len(ns) <= 3, "SERIES_MAX", ns[-1], "series %r has %d slides; a walkthrough holds 3 or fewer before the audience needs a change of pace" % (name, len(ns)))  # check: SERIES_MAX FAIL
            self.check(ns == list(range(ns[0], ns[0] + len(ns))), "SERIES_SPLIT", ns[-1], "series %r slides must be consecutive" % name)  # check: SERIES_SPLIT FAIL
        for i in range(2, len(body)):
            a, b, c = body[i - 2], body[i - 1], body[i]
            same = a[2] == b[2] == c[2] and c[0] - a[0] == 2
            walk = a[1].get("series") and a[1].get("series") == b[1].get("series") == c[1].get("series")
            self.check(not same or bool(walk), "ARCHETYPE_RUN", c[0], "three %s slides in a row (%s-%s); alternate data, visual, text and hero slides" % (c[2], a[0], c[0]))  # check: ARCHETYPE_RUN FAIL
        for (n0, d0, a0), (n1, d1, a1) in zip(body, body[1:]):
            if a0 == a1 == "hero" and n1 - n0 == 1 and not (d0.get("role") == "retrieval" and d1.get("role") == "answer"):
                self.check(False, "HERO_ADJACENT", n1, "two hero or divider slides back to back (%s, %s); a breather works because it is rare" % (n0, n1))  # check: HERO_ADJACENT FAIL
        pairs = quick_check_pairs(main)  # D-25: each quick check + answer pair is one interactive unit for the ratio rules
        units = [(n, d, a) for n, d, a in body if n not in pairs]
        nunits = len(units) + sum(1 for n, d, a in body if n in pairs and d.get("role") == "retrieval")
        heroes = [n for n, d, a in units if a == "hero"]
        if len(body) >= 8:
            gap, last = 0, None
            for n, d, a in body:
                gap = 0 if a == "hero" else gap + 1
                if gap == 6:
                    self.check(False, "PACING", n, "six content slides without a breather; add a hero, section or statement slide every 3-5 slides in long decks")  # check: PACING FAIL
        if body:
            self.check(len(heroes) <= max(1, nunits // 3), "HERO_MAX", heroes[-1] if heroes else "-", "%d hero or divider slides in %d; keep them to about one in four so they stay special" % (len(heroes), nunits))  # check: HERO_MAX FAIL
        if len(body) >= 6:
            kinds = {a for _n, _d, a in body}
            self.check(len(kinds) >= 3, "LAYOUT_VARIETY", "-", "only %s slides; use at least three of data, visual, text and hero" % "/".join(sorted(kinds)))  # check: LAYOUT_VARIETY FAIL
        if nunits >= 6 and units:
            counts = {}
            for n, d, a in units:
                counts[d.get("layout")] = counts.get(d.get("layout"), 0) + 1
            lay, c = max(counts.items(), key=lambda kv: kv[1])
            self.check(c <= max(2, int(nunits * 0.4)), "LAYOUT_OVERUSE", "-", "%d of %d body slides use %s; no layout should carry more than 40%% of the deck" % (c, nunits, lay))  # check: LAYOUT_OVERUSE FAIL
        if len(body) >= 8:
            distinct = {variant(d) for n, d, a in body}
            self.check(len(distinct) >= 5, "LAYOUT_DISTINCT", "-", "only %d distinct layouts in %d body slides; use at least 5 (cards, split, funnel or cycle add variety)" % (len(distinct), len(body)))  # check: LAYOUT_DISTINCT FAIL
            run = 0
            for n, d, a in body:
                run = run + 1 if tone(d) == "white" else 0
                if run == 5:
                    self.check(False, "TONE_RUN", n, "five white slides in a row; break the run with a tint band, a split panel or a hero slide")  # check: TONE_RUN FAIL
        for (n0, d0, a0), (n1, d1, a1) in zip(body, body[1:]):
            if n1 - n0 == 1 and tone(d0) == tone(d1) == "tint":
                self.check(False, "TINT_ADJACENT", n1, "two light-tint slides in a row (%s, %s); tint is an accent, alternate it with white" % (n0, n1))  # check: TINT_ADJACENT FAIL
        last_side, prev = {}, None
        for n, d in main:
            lay = d.get("layout")
            if lay in ("split", "annotated") and d.get("side"):
                self.check(d["side"] != last_side.get(lay), "MIRROR", n, "%s slides alternate sides; this one repeats side %r (omit side to alternate automatically)" % (lay, d["side"]))  # check: MIRROR FAIL
            if lay in ("split", "annotated"):
                last_side[lay] = d.get("side") or ("right" if last_side.get(lay) == "left" else "left")
            if lay == "screenshot" and prev is not None and prev.get("layout") == "screenshot" and d.get("series") and d.get("series") == prev.get("series") and d.get("side") and d.get("side") == prev.get("side"):
                self.check(False, "MIRROR", n, "walkthrough screenshots alternate sides; omit side to mirror automatically")  # check: MIRROR FAIL
            prev = d
        dense = 0
        for n, d, a in body:
            heavy = d.get("layout") == "table" or self.body_words(d) >= 30
            dense = dense + 1 if heavy else 0
            self.check(dense < 3, "DENSE_RUN", n, "three dense slides in a row; follow a dense slide with a lighter one", warn=True)  # check: DENSE_RUN WARN
        elig = [(n, d) for n, d, a in body if d.get("layout") in TAKEAWAY_OK and not (d.get("layout") == "diagram" and (d.get("diagram") or {}).get("kind") == "timeline")]
        with_take = sum(1 for _n, d in elig if d.get("takeaway"))
        if len(elig) >= 3:
            self.check(with_take >= 1, "TAKEAWAY_NONE", "-", "no insight boxes; add a takeaway to the 1-3 slides where the visual needs a 'so what'", warn=True)  # check: TAKEAWAY_NONE WARN
            self.check(with_take <= max(1, (2 * len(elig)) // 3), "TAKEAWAY_OVERUSE", "-", "%d of %d visuals have insight boxes; they lose impact when every slide has one" % (with_take, len(elig)), warn=True)  # check: TAKEAWAY_OVERUSE WARN

    @staticmethod
    def body_words(d):
        parts = list(d.get("points", [])) + [d.get("takeaway", ""), d.get("context", ""), d.get("text", ""), d.get("label", "")]
        parts += [c.get("text", "") for c in d.get("callouts", [])] + [k.get("label", "") + " " + k.get("delta", "") for k in d.get("kpis", [])]
        g = d.get("diagram") or {}
        parts += [nd.get("label", "") + " " + nd.get("detail", "") for nd in g.get("nodes", [])]
        parts += [p for side in ("left", "right") for p in (g.get(side) or {}).get("points", [])]
        return sum(words(p) for p in parts)

    def slide(self, n, d, base, in_appx):
        lay = d.get("layout")
        known = CONTENT | {"summary", "section", "closing", "contents", "contact"}
        if not self.check(lay in known, "LAYOUT", n, "unknown layout %r" % lay):  # check: LAYOUT FAIL
            return
        title = d.get("title") or d.get("text") or ""
        body = []
        if lay in CONTENT | {"summary"} and lay != "statement":
            t = d.get("title", "")
            self.check(t.strip().lower().rstrip(".") not in GENERIC, "TITLE_GENERIC", n, "%r is a topic label; write the takeaway as a sentence" % t)  # check: TITLE_GENERIC FAIL
            lo = 3 if getattr(self, "guide", False) else 4
            self.check(lo <= words(t) <= 15, "TITLE_LENGTH", n, "title has %d words; use a %d-15 word %s" % (words(t), lo, "title that says what the reader will learn or do" if lo == 3 else "takeaway sentence"))  # check: TITLE_LENGTH FAIL
            self.check(len(t) <= 90, "TITLE_LENGTH", n, "title over 90 characters will wrap past two lines")  # check: TITLE_LENGTH FAIL
            self.check(t == proper(t), "PROPER_CASE", n, "write headings in Proper Case: %r (the builder converts it)" % proper(t), warn=True)  # check: PROPER_CASE WARN
            self.check(len((d.get("notes") or "").split()) >= 8, "NOTES_MISSING", n, "speaker notes (8+ words) carry the detail so the slide can stay sparse")  # check: NOTES_MISSING FAIL
        if lay == "section":
            self.accent(n, d.get("title", ""), d.get("accent"))
        if lay in ("section", "closing"):
            self.check(bool(d.get("title")), "TITLE_MISSING", n, "title is required")  # check: TITLE_MISSING FAIL
        self.check(not BANNED.search(json.dumps(d)), "SLOP_WORD", n, "filler word %r; say what happens instead" % (BANNED.search(json.dumps(d)) or [""])[0])  # check: SLOP_WORD FAIL
        if lay in ("bullets", "summary"):
            pts = d.get("points", [])
            cap, wcap = (4, 16) if lay == "summary" else (3, 12)
            self.check(1 <= len(pts) <= cap, "BULLETS_MAX", n, "%d points; %s allows %d" % (len(pts), lay, cap))  # check: BULLETS_MAX FAIL
            for p in pts:
                self.check(words(p) <= wcap, "BULLET_WORDS", n, "point over %d words: %r" % (wcap, p[:60]))  # check: BULLET_WORDS FAIL
            body += pts
        if lay == "statement":
            self.check(words(d.get("text")) <= 20, "STATEMENT_WORDS", n, "statement over 20 words")  # check: STATEMENT_WORDS FAIL
        if lay == "kpi":
            k = d.get("kpis", [])
            self.check(1 <= len(k) <= 4, "KPI_MAX", n, "%d KPIs; show 1-4 cards" % len(k))  # check: KPI_MAX FAIL
            for i in k:
                self.check(len(str(i.get("value", ""))) <= 7, "KPI_VALUE", n, "KPI value %r is too long; round it (e.g. $4.2M)" % i.get("value"))  # check: KPI_VALUE FAIL
                self.check(words(i.get("label")) <= 5, "KPI_LABEL", n, "KPI label over 5 words")  # check: KPI_LABEL FAIL
                if i.get("status") == "missed":
                    self.check(i.get("reason") in T["alert_reasons"], "ALERT_REASON", n, "orange KPI needs reason: " + "/".join(T["alert_reasons"]))  # check: ALERT_REASON FAIL
                body += [i.get("label", ""), i.get("delta", "")]
            body.append(d.get("context", ""))
            self.check(bool(d.get("source")), "SOURCE_MISSING", n, "numbers need a source line")  # check: SOURCE_MISSING FAIL
        if lay == "chart":
            self.chart(n, d)
        if d.get("takeaway"):
            tk = d["takeaway"]
            ok_lay = lay in TAKEAWAY_OK and not (lay == "diagram" and (d.get("diagram") or {}).get("kind") == "timeline")
            self.check(ok_lay, "TAKEAWAY_LAYOUT", n, "insight boxes go on chart, KPI, screenshot, table or process/matrix/comparison diagram slides; on a %s slide put it in the title or notes" % (lay if lay != "diagram" else "timeline"))  # check: TAKEAWAY_LAYOUT FAIL
            self.check(words(tk) <= 22, "TAKEAWAY_WORDS", n, "takeaway over 22 words")  # check: TAKEAWAY_WORDS FAIL
            tw = set(re.findall(r"[a-z0-9%$]+", (d.get("title") or "").lower())); kw = set(re.findall(r"[a-z0-9%$]+", tk.lower()))
            self.check(not kw or len(kw & tw) / len(kw) < 0.7, "TAKEAWAY_ECHO", n, "the takeaway repeats the title; say the so-what (impact, action or implication) instead")  # check: TAKEAWAY_ECHO FAIL
            self.check(not (lay == "kpi" and d.get("context")), "TAKEAWAY_CONTEXT", n, "use either context or takeaway on a KPI slide, not both")  # check: TAKEAWAY_CONTEXT FAIL
            body.append(tk)
        if lay == "hero":
            self.accent(n, d.get("title", ""), d.get("accent"))
            self.check(words(d.get("title")) <= 12, "HERO_TEXT", n, "hero title over 12 words; a breather slide says one short thing")  # check: HERO_TEXT FAIL
            if d.get("value"):
                self.check(len(str(d["value"])) <= 7, "KPI_VALUE", n, "hero value %r is too long; round it (e.g. $4.2M)" % d["value"])  # check: KPI_VALUE FAIL
                self.check(bool(d.get("label")) and words(d.get("label")) <= 6, "HERO_LABEL", n, "a hero number needs a label of 6 words or fewer saying what it counts")  # check: HERO_LABEL FAIL
                self.check(bool(d.get("source")), "SOURCE_MISSING", n, "a hero number needs a source line")  # check: SOURCE_MISSING FAIL
            else:
                self.check(not d.get("label"), "HERO_LABEL", n, "label is only for a hero number; use text for a supporting line")  # check: HERO_LABEL FAIL
            self.check(words(d.get("text")) <= 20, "HERO_TEXT", n, "hero supporting text over 20 words")  # check: HERO_TEXT FAIL
            body += [d.get("label", ""), d.get("text", "")]
        if lay == "screenshot":
            img = d.get("image")
            exists = bool(img) and os.path.isfile(os.path.join(base, img))
            self.check(exists, "IMAGE_MISSING", n, "screenshot %r not found; attach it (or add it to the shot list)" % img, warn=self.draft)  # check: IMAGE_MISSING FAIL # check: IMAGE_MISSING WARN
            cs = d.get("callouts", [])
            self.check(len(cs) <= 3, "CALLOUTS_MAX", n, "%d callouts; use 3 or fewer, or crop to the area that matters" % len(cs))  # check: CALLOUTS_MAX FAIL
            for c in cs:
                self.check(0 <= c.get("x", -1) <= 1 and 0 <= c.get("y", -1) <= 1, "CALLOUT_POS", n, "callout x/y must be 0-1 fractions of the image")  # check: CALLOUT_POS FAIL
                self.check(words(c.get("text")) <= 8, "CALLOUT_WORDS", n, "callout over 8 words")  # check: CALLOUT_WORDS FAIL
                body.append(c.get("text", ""))
        if lay == "diagram":
            g = d.get("diagram", {})
            kind = g.get("kind")
            if self.check(kind in DIAGRAM_KINDS, "DIAGRAM_KIND", n, "kind must be one of " + ", ".join(DIAGRAM_KINDS)):  # check: DIAGRAM_KIND FAIL
                if kind == "milestones":
                    nodes = g.get("nodes", [])
                    self.check(3 <= len(nodes) <= 6, "DIAGRAM_NODES", n, "%d milestones; use 3-6" % len(nodes))  # check: DIAGRAM_NODES FAIL
                    for nd in nodes:
                        self.check(words(nd.get("detail")) <= 14, "DIAGRAM_DETAIL", n, "milestone detail over 14 words")  # check: DIAGRAM_DETAIL FAIL
                        self.check(words(nd.get("when")) <= 3, "DIAGRAM_LABEL", n, "milestone when over 3 words")  # check: DIAGRAM_LABEL FAIL
                    body += [nd.get("detail", "") for nd in nodes]
                    nodes = [dict(nd, detail="") for nd in nodes]
                elif kind == "layers":
                    nodes = g.get("nodes", [])
                    self.check(3 <= len(nodes) <= 5, "DIAGRAM_NODES", n, "%d layers; use 3-5" % len(nodes))  # check: DIAGRAM_NODES FAIL
                    for nd in nodes:
                        self.check(words(nd.get("detail")) <= 14, "DIAGRAM_DETAIL", n, "layer detail over 14 words")  # check: DIAGRAM_DETAIL FAIL
                    nodes = [dict(nd, detail="") for nd in nodes]
                    body += [nd.get("detail", "") for nd in g.get("nodes", [])]
                elif kind == "roadmap":
                    nodes = []
                    per, lanes = g.get("periods", []), g.get("lanes", [])
                    self.check(3 <= len(per) <= 6, "ROADMAP_SHAPE", n, "%d periods; use 3-6" % len(per))  # check: ROADMAP_SHAPE FAIL
                    self.check(1 <= len(lanes) <= 4, "ROADMAP_SHAPE", n, "%d lanes; use 1-4" % len(lanes))  # check: ROADMAP_SHAPE FAIL
                    idx = {str(p): k for k, p in enumerate(per)}
                    for ln in lanes:
                        self.check(words(ln.get("label")) <= 4 and bool(ln.get("label")), "DIAGRAM_LABEL", n, "lane label needs 1-4 words")  # check: DIAGRAM_LABEL FAIL
                        its = ln.get("items", [])
                        self.check(1 <= len(its) <= 3, "ROADMAP_SHAPE", n, "lane %r has %d items; use 1-3" % (ln.get("label"), len(its)))  # check: ROADMAP_SHAPE FAIL
                        spans = []
                        for it in its:
                            a = it.get("start"); b = it.get("end")
                            a = a if isinstance(a, int) else idx.get(str(a)); b = b if isinstance(b, int) else idx.get(str(b))
                            ok = a is not None and b is not None and 0 <= a <= b < len(per)
                            self.check(ok, "ROADMAP_SHAPE", n, "item %r needs start <= end inside the periods" % it.get("label"))  # check: ROADMAP_SHAPE FAIL
                            self.check(words(it.get("label")) <= 4, "DIAGRAM_LABEL", n, "roadmap item label over 4 words: %r" % it.get("label"))  # check: DIAGRAM_LABEL FAIL
                            body.append(it.get("label", ""))
                            if ok:
                                spans.append((a, b))
                        spans.sort()
                        self.check(all(s2[0] > s1[1] for s1, s2 in zip(spans, spans[1:])), "ROADMAP_OVERLAP", n, "items in lane %r overlap; give each its own lane or periods" % ln.get("label"))  # check: ROADMAP_OVERLAP FAIL
                        body.append(ln.get("label", ""))
                elif kind == "funnel":
                    nodes = g.get("nodes", [])
                    self.check(3 <= len(nodes) <= 5, "DIAGRAM_NODES", n, "%d funnel stages; use 3-5" % len(nodes))  # check: DIAGRAM_NODES FAIL
                    nums = []
                    for nd in nodes:
                        self.check(bool(nd.get("value")) and len(str(nd.get("value"))) <= 8, "FUNNEL_VALUE", n, "each funnel stage needs a short value (8 characters or fewer)")  # check: FUNNEL_VALUE FAIL
                        m = re.search(r"[\d.,]+", str(nd.get("value", "")).replace(",", ""))
                        nums.append(float(m.group(0)) if m and m.group(0).replace(".", "", 1).isdigit() else None)
                    if all(v is not None for v in nums):
                        self.check(all(a >= b for a, b in zip(nums, nums[1:])), "FUNNEL_ORDER", n, "funnel values must narrow from top to bottom; use a bar chart for values that rise")  # check: FUNNEL_ORDER FAIL
                    self.check(bool(d.get("source")), "SOURCE_MISSING", n, "funnel values need a source line")  # check: SOURCE_MISSING FAIL
                elif kind == "cycle":
                    nodes = g.get("nodes", [])
                    self.check(3 <= len(nodes) <= 5, "DIAGRAM_NODES", n, "%d cycle steps; use 3-5" % len(nodes))  # check: DIAGRAM_NODES FAIL
                    self.check(words(g.get("center")) <= 3, "DIAGRAM_LABEL", n, "cycle center label over 3 words")  # check: DIAGRAM_LABEL FAIL
                    self.check(not (d.get("takeaway") and len(nodes) > 4), "CYCLE_TAKEAWAY", n, "a 5-step cycle has no room for an insight box; use 3-4 steps or move the takeaway to the notes")  # check: CYCLE_TAKEAWAY FAIL
                    body.append(g.get("center", ""))
                elif kind in ("process", "timeline"):
                    nodes = g.get("nodes", [])
                    self.check(3 <= len(nodes) <= 6, "DIAGRAM_NODES", n, "%d steps; use 3-6" % len(nodes))  # check: DIAGRAM_NODES FAIL
                elif kind == "matrix":
                    nodes = g.get("nodes", [])
                    self.check(len(nodes) == 4, "DIAGRAM_NODES", n, "a 2x2 needs exactly 4 quadrants")  # check: DIAGRAM_NODES FAIL
                else:
                    nodes = []
                    for side in ("left", "right"):
                        col = g.get(side, {})
                        self.check(bool(col.get("label")) and 1 <= len(col.get("points", [])) <= 3, "DIAGRAM_NODES", n, "comparison %s needs a label and 1-3 points" % side)  # check: DIAGRAM_NODES FAIL
                        for p in col.get("points", []):
                            self.check(words(p) <= 10, "DIAGRAM_DETAIL", n, "comparison point over 10 words")  # check: DIAGRAM_DETAIL FAIL
                            body.append(p)
                for nd in nodes:
                    self.check(words(nd.get("label")) <= 4, "DIAGRAM_LABEL", n, "node label over 4 words: %r" % nd.get("label"))  # check: DIAGRAM_LABEL FAIL
                    self.check(words(nd.get("detail")) <= 14, "DIAGRAM_DETAIL", n, "node detail over 14 words")  # check: DIAGRAM_DETAIL FAIL
                    body += [nd.get("label", ""), nd.get("detail", "")]
        if lay == "kpi":
            self.check(d.get("style", "cards") in ("cards", "minimal"), "KPI_STYLE", n, "kpi style must be cards (default) or minimal")  # check: KPI_STYLE FAIL
            self.check(not (d.get("style") == "minimal" and d.get("dark")), "KPI_STYLE", n, "minimal KPIs are for white slides; use dark cards or a hero for a dark slide")  # check: KPI_STYLE FAIL
        if lay == "shift":
            f, t = d.get("from") or {}, d.get("to") or {}
            for side, it in (("from", f), ("to", t)):
                self.check(bool(it.get("value")) and len(str(it.get("value"))) <= 7, "KPI_VALUE", n, "shift %s needs a value of 7 characters or fewer" % side)  # check: KPI_VALUE FAIL
                self.check(bool(it.get("label")) and words(it.get("label")) <= 4, "SHIFT_LABEL", n, "shift %s needs a label of 1-4 words (when or what)" % side)  # check: SHIFT_LABEL FAIL
                body.append(it.get("label", ""))
            self.check(len(str(d.get("change", ""))) <= 10, "SHIFT_CHANGE", n, "change pill over 10 characters; round it (e.g. -34%)")  # check: SHIFT_CHANGE FAIL
            self.check(words(d.get("metric")) <= 6, "SHIFT_LABEL", n, "metric label over 6 words")  # check: SHIFT_LABEL FAIL
            if t.get("status") == "missed":
                self.check(t.get("reason") in T["alert_reasons"], "ALERT_REASON", n, "orange needs reason: " + "/".join(T["alert_reasons"]))  # check: ALERT_REASON FAIL
            self.check(bool(d.get("source")), "SOURCE_MISSING", n, "numbers need a source line")  # check: SOURCE_MISSING FAIL
            body.append(d.get("metric", ""))
        if lay == "checklist":
            its = d.get("items", [])
            self.check(3 <= len(its) <= 6, "CHECKLIST_MAX", n, "%d items; use 3-6 (split longer lists or move them to the appendix)" % len(its))  # check: CHECKLIST_MAX FAIL
            for it in its:
                self.check(it.get("status") in CHECK_STATUS, "CHECK_STATUS", n, "status must be one of " + ", ".join(CHECK_STATUS))  # check: CHECK_STATUS FAIL
                self.check(bool(it.get("text")) and words(it.get("text")) <= 12, "CHECK_WORDS", n, "item needs 1-12 words: %r" % (it.get("text") or "")[:50])  # check: CHECK_WORDS FAIL
                if it.get("status") == "at_risk":
                    self.check(it.get("reason") in T["alert_reasons"], "ALERT_REASON", n, "an at-risk item is orange and needs reason: " + "/".join(T["alert_reasons"]))  # check: ALERT_REASON FAIL
                body.append(it.get("text", ""))
        if lay == "qa":
            ps = d.get("pairs", [])
            self.check(1 <= len(ps) <= 4, "QA_MAX", n, "%d questions; use 1-4 per slide" % len(ps))  # check: QA_MAX FAIL
            for p in ps:
                self.check(str(p.get("q", "")).strip().endswith("?") and words(p.get("q")) <= 14, "QA_WORDS", n, "each question ends with ? and has 14 words or fewer")  # check: QA_WORDS FAIL
                self.check(bool(p.get("a")) and words(p.get("a")) <= 25, "QA_WORDS", n, "each answer needs 1-25 words")  # check: QA_WORDS FAIL
            self.check(sum(words(p.get("q")) + words(p.get("a")) for p in ps) <= 100, "QA_WORDS", n, "Q&A slide over 100 words; split it or move detail to notes")  # check: QA_WORDS FAIL
        if lay == "steps":
            st = d.get("steps", [])
            self.check(3 <= len(st) <= 5, "STEPS_MAX", n, "%d steps; use 3-5" % len(st))  # check: STEPS_MAX FAIL
            for r in st:
                self.check(bool(r.get("label")) and words(r.get("label")) <= 5, "STEP_WORDS", n, "step label needs 1-5 words: %r" % r.get("label"))  # check: STEP_WORDS FAIL
                self.check(words(r.get("detail")) <= 14, "STEP_WORDS", n, "step detail over 14 words")  # check: STEP_WORDS FAIL
                body += [r.get("label", ""), r.get("detail", "")]
            hl = d.get("highlight")
            self.check(hl is None or (isinstance(hl, int) and 0 <= hl < len(st)), "STEPS_HIGHLIGHT", n, "highlight must be the index of one step")  # check: STEPS_HIGHLIGHT FAIL
        if lay == "cards":
            cs = d.get("cards", [])
            self.check(2 <= len(cs) <= 4, "CARDS_MAX", n, "%d cards; use 2-4 parallel ideas" % len(cs))  # check: CARDS_MAX FAIL
            for c in cs:
                self.check(bool(c.get("label")) and words(c.get("label")) <= 4, "CARD_WORDS", n, "card label needs 1-4 words: %r" % c.get("label"))  # check: CARD_WORDS FAIL
                self.check(words(c.get("detail")) <= 14, "CARD_WORDS", n, "card detail over 14 words")  # check: CARD_WORDS FAIL
                body += [c.get("label", ""), c.get("detail", "")]
            hl = d.get("highlight")
            self.check(hl is None or (isinstance(hl, int) and 0 <= hl < len(cs)), "CARDS_HIGHLIGHT", n, "highlight must be the index of one card")  # check: CARDS_HIGHLIGHT FAIL
        if lay == "split":
            v = d.get("visual") or {}
            self.check(d.get("panel", "tint") in ("tint", "dark"), "SPLIT_PANEL", n, "panel must be tint or dark")  # check: SPLIT_PANEL FAIL
            self.check(d.get("side") in (None, "left", "right"), "SPLIT_SIDE", n, "side must be left or right (or omitted to alternate)")  # check: SPLIT_SIDE FAIL
            pts = d.get("points", [])
            self.check(1 <= len(pts) <= 3, "BULLETS_MAX", n, "split panel holds 1-3 points")  # check: BULLETS_MAX FAIL
            for p in pts:
                self.check(words(p) <= 12, "BULLET_WORDS", n, "point over 12 words: %r" % p[:60])  # check: BULLET_WORDS FAIL
            body += pts
            if self.check(v.get("kind") in ("screenshot", "number"), "SPLIT_VISUAL", n, "split visual.kind must be screenshot or number"):  # check: SPLIT_VISUAL FAIL
                if v["kind"] == "number":
                    self.check(len(str(v.get("value", ""))) <= 7 and bool(v.get("value")), "KPI_VALUE", n, "split number needs a value of 7 characters or fewer")  # check: KPI_VALUE FAIL
                    self.check(bool(v.get("label")) and words(v.get("label")) <= 6, "HERO_LABEL", n, "split number needs a label of 6 words or fewer")  # check: HERO_LABEL FAIL
                    self.check(bool(d.get("source")), "SOURCE_MISSING", n, "a number needs a source line")  # check: SOURCE_MISSING FAIL
                    body.append(v.get("label", ""))
                else:
                    img = v.get("image")
                    self.check(bool(img) and os.path.isfile(os.path.join(base, img)), "IMAGE_MISSING", n, "screenshot %r not found" % img, warn=self.draft)  # check: IMAGE_MISSING FAIL # check: IMAGE_MISSING WARN
                    self.check(words(v.get("alt")) >= 5, "ALT_MISSING", n, "alt text (5+ words) describing what the screenshot shows")  # check: ALT_MISSING FAIL
        if (lay in ("bullets", "cards", "steps") or (lay == "statement" and not d.get("attribution"))) or not d.get("tint"):
            pass
        else:
            self.check(False, "TINT_LAYOUT", n, "tint bands are for bullets, cards and statement slides")  # check: TINT_LAYOUT FAIL
        if lay in ("chart", "screenshot", "diagram"):
            self.check(words(d.get("alt")) >= 5, "ALT_MISSING", n, "alt text (5+ words) describing what the visual shows")  # check: ALT_MISSING FAIL
        if lay == "table":
            t = d.get("table", {})
            cols, rows = t.get("columns", []), t.get("rows", [])
            big = len(rows) > 6 or len(cols) > 5
            self.check(not big or in_appx, "TABLE_SIZE", n, "%dx%d table; main-deck tables max 6 rows x 5 columns, move it to the appendix or chart it" % (len(rows), len(cols)))  # check: TABLE_SIZE FAIL
            self.check(all(len(r) == len(cols) for r in rows), "TABLE_SHAPE", n, "every row needs one value per column")  # check: TABLE_SHAPE FAIL
            self.check(len(rows) <= 12, "TABLE_SIZE", n, "over 12 rows will not fit; split or summarize")  # check: TABLE_SIZE FAIL
            self.check(bool(d.get("source")), "SOURCE_MISSING", n, "tables of numbers need a source line", warn=True)  # check: SOURCE_MISSING WARN
        if lay == "closing":
            a = d.get("asks", [])
            self.check(1 <= len(a) <= 3, "ASKS", n, "closing needs 1-3 asks (action, owner, date)")  # check: ASKS FAIL
            for x in a:
                self.check(bool(x.get("owner")) and bool(x.get("date")), "ASK_OWNER", n, "each ask needs an owner and a date", warn=True)  # check: ASK_OWNER WARN
                self.check(words(x.get("action")) <= 12, "ASK_WORDS", n, "ask over 12 words; state the action plainly", warn=True)  # check: ASK_WORDS WARN
        self.newlayouts(n, d, lay, base, body)
        self.icons(n, d, lay)
        self.fit(n, d, lay)
        self.plain(n, d, lay)
        cap = 70 if getattr(self, "guide", False) else 40
        if lay in CONTENT and lay not in ("statement", "table", "qa", "article"):
            bw = sum(words(b) for b in body)
            self.check(bw <= cap, "BODY_WORDS", n, "%d words on the slide body; keep it to %d and move the rest to notes" % (bw, cap))  # check: BODY_WORDS FAIL

    def plain(self, n, d, lay):
        """Plain words: no shorthand details, highlights tied to the message, retrieval slides that ask, no design tags in notes."""
        g = d.get("diagram") or {}
        items = [("step", x) for x in d.get("steps") or []] + [("card", x) for x in d.get("cards") or []]
        items += [("node", x) for x in (g.get("nodes") or [] if g.get("kind") in PL.SEQUENCE_KINDS else [])]
        for what, it in items:
            if not isinstance(it, dict):
                continue
            for key, detail in (("label", False), ("detail", True)):
                why = PL.telegraphic(it.get(key, ""), detail) if it.get(key) else None
                self.check(not why, "TELEGRAPHIC", n, "%s %s %r reads as shorthand (%s); write a full instruction, or split the slide" % (what, key, str(it.get(key))[:50], why), warn=True)  # check: TELEGRAPHIC WARN
        hi = None
        if lay in ("steps", "cards") and isinstance(d.get("highlight"), int):
            arr = d.get("steps" if lay == "steps" else "cards") or []
            hi = arr[d["highlight"]] if 0 <= d["highlight"] < len(arr) else None
        elif lay == "diagram" and isinstance(g.get("highlight"), int) and g.get("nodes"):
            hi = g["nodes"][g["highlight"]] if 0 <= g["highlight"] < len(g["nodes"]) else None
        elif lay == "table" and isinstance((d.get("table") or {}).get("highlight_row"), int):
            rows = d["table"].get("rows") or []
            hr = d["table"]["highlight_row"]
            hi = {"label": " ".join(map(str, rows[hr]))} if 0 <= hr < len(rows) else None
        if hi is not None:
            ok = bool(keyset(hi.get("label"), hi.get("detail"), hi.get("value")) & keyset(d.get("title"), d.get("takeaway")))
            self.check(ok, "HIGHLIGHT_REASON", n, "the highlighted item %r shares no key word with the title or takeaway, so the highlight looks arbitrary; tie it to the message or drop it" % str(hi.get("label"))[:40], warn=True)  # check: HIGHLIGHT_REASON WARN
        if d.get("role") == "retrieval":
            t = str(d.get("text") or d.get("title") or "").strip()
            ok = lay == "statement" and t.startswith("Quick check:") and t.endswith("?") and len((d.get("notes") or "").split()) >= 5
            self.check(ok, "RETRIEVAL_FORM", n, "a retrieval slide is a statement that starts 'Quick check:', ends with '?', and keeps its answer only in the speaker notes")  # check: RETRIEVAL_FORM FAIL
        imgtxt = " ".join(str(d.get(x, "")) for x in ("image", "alt"))
        if re.search(r"(?i)illustration", imgtxt):
            ok = re.search(r"(?i)illustration,? not a live screenshot", str(d.get("source", "")))
            self.check(bool(ok), "ILLUSTRATION_LABEL", n, "an illustration needs the source line \"Illustration, not a live screenshot\" (and keeps its stamp)")  # check: ILLUSTRATION_LABEL FAIL
        cols = []
        if lay == "diagram" and g.get("kind") == "comparison":
            cols = [g.get("left", {}).get("points") or [], g.get("right", {}).get("points") or []]
        elif lay == "bullets":
            cols = [d.get("points") or []]
        for pts in cols:
            starts = [PL.has_verb(str(p).split()[0]) for p in pts if str(p).split()]
            self.check(len(set(starts)) <= 1, "PARALLEL_POINTS", n, "points start with different forms (verb next to noun): %s" % [str(p)[:25] for p in pts], warn=True)  # check: PARALLEL_POINTS WARN
        tag = NOTES_TAG.search(d.get("notes") or "")
        self.check(not tag, "NOTES_TAGS", n, "speaker notes carry the design tag %r; presenters won't know it. Write a plain cue (\"Ask the group…\", \"Pause for answers\")" % (tag.group(0).strip() if tag else ""), warn=True)  # check: NOTES_TAGS WARN

    def icons(self, n, d, lay):
        """Tabler outline icons: known names, all-or-none within a set, never instead of a number, only where supported."""
        import iconlib
        def known(name, where):
            ok = iconlib.exists(name)
            self.check(ok, "ICON_UNKNOWN", n, "icon %r (%s) is not in the Tabler set shipped with the skill; pick one from assets/icons/tabler.json, or fetch it from https://api.iconify.design/tabler.json?icons=%s and save the response next to deck.json as icons.local.json" % (name, where, name))  # check: ICON_UNKNOWN FAIL
        items = []
        if lay in ICON_FIELDS:
            items = d.get(ICON_FIELDS[lay]) or []
        elif lay == "diagram":
            g = d.get("diagram") or {}
            if g.get("kind") in ICON_DIAGRAMS:
                items = g.get("nodes") or []
            elif any(isinstance(nd, dict) and nd.get("icon") for nd in g.get("nodes", [])):
                self.check(False, "ICON_PLACEMENT", n, "%s diagrams don't take icons; use them on process, timeline, cycle or milestones" % g.get("kind"))  # check: ICON_PLACEMENT FAIL
        with_icon = [it for it in items if isinstance(it, dict) and it.get("icon")]
        for it in with_icon:
            known(it["icon"], lay)
        if lay not in ("callouts", "contact") and with_icon:
            self.check(len(with_icon) == len(items), "ICON_PARTIAL", n, "%d of %d items have icons; use icons on all items in a set or on none" % (len(with_icon), len(items)))  # check: ICON_PARTIAL FAIL
        if lay == "cards" and with_icon:
            self.check(not d.get("numbered"), "ICON_CONFLICT", n, "numbered cards don't take icons; choose numbers (order matters) or icons (categories)")  # check: ICON_CONFLICT FAIL
        if d.get("icon"):
            self.check(lay == "hero" and not d.get("value"), "ICON_PLACEMENT", n, "a slide-level icon only goes on a hero statement slide")  # check: ICON_PLACEMENT FAIL
            known(d["icon"], lay)
        for k in ("points", "items", "kpis", "steps", "pairs", "zones"):
            for it in d.get(k) or []:
                if isinstance(it, dict) and it.get("icon"):
                    self.check(False, "ICON_PLACEMENT", n, "%s on a %s slide don't take icons" % (k, lay))  # check: ICON_PLACEMENT FAIL
                    break

    def newlayouts(self, n, d, lay, base, body):
        """Validation for contents, anatomy, annotated, callouts, article and contact slides."""
        guide = getattr(self, "guide", False)
        def img(path, alt):
            self.check(bool(path) and os.path.isfile(os.path.join(base, path)), "IMAGE_MISSING", n, "screenshot %r not found" % path, warn=self.draft)  # check: IMAGE_MISSING FAIL # check: IMAGE_MISSING WARN
            self.check(words(alt) >= 5, "ALT_MISSING", n, "alt text (5+ words) describing what the screenshot shows")  # check: ALT_MISSING FAIL
        if lay == "contents":
            its = [i if isinstance(i, str) else (i or {}).get("label", "") for i in d.get("items", [])]
            self.check(3 <= len(its) <= 8, "CONTENTS_MAX", n, "%d entries; use 3-8" % len(its))  # check: CONTENTS_MAX FAIL
            for i in its:
                self.check(1 <= words(i) <= 6, "CONTENTS_WORDS", n, "contents entry needs 1-6 words: %r" % i[:40])  # check: CONTENTS_WORDS FAIL
            self.check(bool(d.get("title")), "TITLE_MISSING", n, "contents slide needs a title, for example 'What This Guide Covers'")  # check: TITLE_MISSING FAIL
        if lay == "anatomy":
            zs = d.get("zones", [])
            self.check(2 <= len(zs) <= 6, "ANATOMY_ZONES", n, "%d zones; use 2-6" % len(zs))  # check: ANATOMY_ZONES FAIL
            for z in zs:
                self.check(bool(z.get("label")) and words(z.get("label")) <= 4, "ANATOMY_WORDS", n, "zone label needs 1-4 words: %r" % z.get("label"))  # check: ANATOMY_WORDS FAIL
                self.check(words(z.get("detail")) <= 16, "ANATOMY_WORDS", n, "zone detail over 16 words")  # check: ANATOMY_WORDS FAIL
                if z.get("x") is not None or z.get("y") is not None:
                    ok = all(isinstance(z.get(k), (int, float)) and 0 <= z.get(k) <= 1 for k in ("x", "y"))
                    self.check(ok, "ANATOMY_PIN", n, "zone %r pin needs x and y between 0 and 1" % z.get("label"))  # check: ANATOMY_PIN FAIL
                body += [z.get("label", ""), z.get("detail", "")]
            self.check(words(d.get("intro")) <= 25, "ANATOMY_WORDS", n, "intro over 25 words")  # check: ANATOMY_WORDS FAIL
            body.append(d.get("intro", ""))
            img(d.get("image"), d.get("alt"))
        if lay == "annotated":
            an = d.get("annotations", [])
            self.check(2 <= len(an) <= 4, "ANNOTATIONS_MAX", n, "%d annotations; use 2-4" % len(an))  # check: ANNOTATIONS_MAX FAIL
            for a in an:
                self.check(bool(a.get("lead")) and words(a.get("lead")) <= 4, "ANNOTATION_WORDS", n, "annotation lead needs 1-4 words: %r" % a.get("lead"))  # check: ANNOTATION_WORDS FAIL
                self.check(bool(a.get("text")) and words(a.get("text")) <= 22, "ANNOTATION_WORDS", n, "annotation text needs 1-22 words")  # check: ANNOTATION_WORDS FAIL
                body += [a.get("lead", ""), a.get("text", "")]
            self.check(words(d.get("heading")) <= 6, "ANNOTATION_WORDS", n, "heading over 6 words")  # check: ANNOTATION_WORDS FAIL
            self.check(words(d.get("intro")) <= 25, "ANNOTATION_WORDS", n, "intro over 25 words")  # check: ANNOTATION_WORDS FAIL
            self.check(d.get("side") in (None, "left", "right"), "SPLIT_SIDE", n, "side must be left or right (or omitted to alternate)")  # check: SPLIT_SIDE FAIL
            body += [d.get("heading", ""), d.get("intro", "")]
            img(d.get("image"), d.get("alt"))
        if lay == "callouts":
            cs = d.get("cards", [])
            self.check(2 <= len(cs) <= 3, "CALLOUTS_MAX", n, "%d callout cards; use 2-3" % len(cs))  # check: CALLOUTS_MAX FAIL
            for c in cs:
                self.check(c.get("kind") in CALLOUT_KINDS, "CALLOUT_KIND", n, "kind must be one of " + ", ".join(CALLOUT_KINDS))  # check: CALLOUT_KIND FAIL
                self.check(bool(c.get("title")) and words(c.get("title")) <= 5, "CALLOUT_WORDS", n, "callout title needs 1-5 words: %r" % c.get("title"))  # check: CALLOUT_WORDS FAIL
                self.check(bool(c.get("text")) and words(c.get("text")) <= 30, "CALLOUT_WORDS", n, "callout text needs 1-30 words")  # check: CALLOUT_WORDS FAIL
                self.check(words(c.get("label")) <= 3, "CALLOUT_WORDS", n, "callout label over 3 words")  # check: CALLOUT_WORDS FAIL
                body += [c.get("title", ""), c.get("text", "")]
            self.check(sum(1 for c in cs if c.get("kind") == "warning") <= 1, "CALLOUT_KIND", n, "one warning per slide; orange marks the single risk to notice")  # check: CALLOUT_KIND FAIL
        if lay == "article":
            ps = d.get("paragraphs", [])
            self.check(1 <= len(ps) <= 3, "ARTICLE_SHAPE", n, "%d paragraphs; use 1-3" % len(ps))  # check: ARTICLE_SHAPE FAIL
            self.check(bool(d.get("heading")) and words(d.get("heading")) <= 8, "ARTICLE_SHAPE", n, "article heading needs 1-8 words")  # check: ARTICLE_SHAPE FAIL
            tk = d.get("takeaways", [])
            self.check(len(tk) <= 4, "ARTICLE_SHAPE", n, "%d takeaways; use 4 or fewer" % len(tk))  # check: ARTICLE_SHAPE FAIL
            for t in tk:
                self.check(words(t) <= 12, "ARTICLE_SHAPE", n, "takeaway over 12 words: %r" % t[:40])  # check: ARTICLE_SHAPE FAIL
            cap = 110 if guide else 60
            aw = sum(words(p) for p in ps) + sum(words(t) for t in tk) + words(d.get("heading"))
            self.check(aw <= cap, "ARTICLE_WORDS", n, "%d words; an article slide holds %d at most (move the rest to notes or a Confluence page)" % (aw, cap))  # check: ARTICLE_WORDS FAIL
        if lay == "contact":
            rows = d.get("contacts", [])
            self.check(1 <= len(rows) <= 3, "CONTACT_MAX", n, "%d contacts; use 1-3" % len(rows))  # check: CONTACT_MAX FAIL
            for r in rows:
                self.check(bool(r.get("label")) and words(r.get("label")) <= 2, "CONTACT_WORDS", n, "contact label needs 1-2 words (Email, Channel, Office hours)")  # check: CONTACT_WORDS FAIL
                self.check(bool(r.get("value")) and len(str(r.get("value"))) <= 44, "CONTACT_WORDS", n, "contact value needs 1-44 characters")  # check: CONTACT_WORDS FAIL
            self.check(words(d.get("text")) <= 18, "CONTACT_WORDS", n, "supporting line over 18 words")  # check: CONTACT_WORDS FAIL
            self.check(bool(d.get("title")) and words(d.get("title")) <= 8, "CONTACT_WORDS", n, "contact title needs 1-8 words")  # check: CONTACT_WORDS FAIL
            self.accent(n, d.get("title", ""), d.get("accent"))

    def fit(self, n, d, lay):
        """Advice (warnings) when the content would tell its story better in another layout."""
        W_ = lambda cond, msg: self.check(not cond, "LAYOUT_FIT", n, msg, warn=True)  # check: LAYOUT_FIT WARN
        pts = d.get("points", [])
        if lay == "bullets":
            W_(len(pts) >= 2 and all(re.match(r"^\s*[$\d]", p) for p in pts), "every point leads with a number; a kpi (or shift) slide shows numbers better")
            W_(len(pts) >= 2 and all(re.match(r"^[^:]{2,30}:\s", p) for p in pts), "points are label: detail pairs; cards or steps show parallel ideas better")
            W_(len(pts) >= 2 and all(re.match(r"(?i)^(step\s*\d|first|then|next|finally)\b", p) for p in pts[:2]), "points are a sequence; use steps or a process diagram")
        if lay == "chart":
            c = d.get("chart", {})
            cats, ser = c.get("categories", []), c.get("series", [])
            W_(len(cats) == 2 and len(ser) == 1, "two values on a chart; a shift slide (from -> to) tells a before/after better")
            W_(len(cats) == 1, "one value on a chart; use a kpi or hero number")
        if lay == "kpi":
            W_(len(d.get("kpis", [])) == 1 and not d.get("context") and not d.get("takeaway"), "a single KPI with nothing else; a hero number or split number gives it room")
        if lay == "table":
            t = d.get("table", {})
            W_(len(t.get("rows", [])) <= 2 and len(t.get("columns", [])) <= 3, "a tiny table; kpi, cards or a sentence in the title reads faster")
            cols = [str(c).lower() for c in t.get("columns", [])]
            W_(any(c in ("status", "state") for c in cols) and len(t.get("rows", [])) <= 6, "a status table; a checklist slide shows readiness with status words and owners")
        if lay == "diagram" and (d.get("diagram") or {}).get("kind") == "process":
            W_(len((d.get("diagram") or {}).get("nodes", [])) == 3 and not any(nd.get("detail") for nd in d["diagram"]["nodes"]), "three bare steps; a steps slide or a sentence may say it with less ink")

    def chart(self, n, d):
        c = d.get("chart", {})
        kind = c.get("type")
        if not self.check(kind in CHART_TYPES, "CHART_TYPE", n, "chart type %r not allowed; use bar, column, line, stacked_bar or stacked_column (no pie, donut, 3-D, radar)" % kind):  # check: CHART_TYPE FAIL
            return
        cats, ser = c.get("categories", []), c.get("series", [])
        self.check(bool(ser) and all(len(s.get("values", [])) == len(cats) for s in ser), "CHART_DATA", n, "each series needs one value per category")  # check: CHART_DATA FAIL
        cap = 3 if kind.startswith("stacked") else (4 if kind == "line" else 2)
        self.check(len(ser) <= cap, "CHART_SERIES_MAX", n, "%d series on a %s chart; max %d. Split the chart or gray out context" % (len(ser), kind, cap))  # check: CHART_SERIES_MAX FAIL
        self.check(len(cats) <= 12, "CHART_CATEGORIES", n, "%d categories; group the tail into Other or use a table in the appendix" % len(cats))  # check: CHART_CATEGORIES FAIL
        self.check(len(cats) <= 8 or kind == "line", "CHART_CATEGORIES", n, "%d bars; sort them and consider showing the top 7 + Other" % len(cats), warn=True)  # check: CHART_CATEGORIES WARN
        if kind == "line":
            self.check(len(cats) >= 3, "LINE_POINTS", n, "a line needs 3+ ordered points; use bars for fewer")  # check: LINE_POINTS FAIL
        hl = c.get("highlight", {})
        need = len(ser) > 1 or (len(cats) > 1 and kind in ("bar", "column"))
        if need and not kind.startswith("stacked"):
            self.check(bool(hl.get("category") or hl.get("series")), "CHART_HIGHLIGHT", n, "say what to look at: highlight one category or series (blue); the rest stay gray")  # check: CHART_HIGHLIGHT FAIL
        if hl.get("category"):
            self.check(hl["category"] in cats, "CHART_HIGHLIGHT", n, "highlight category %r is not in categories" % hl["category"])  # check: CHART_HIGHLIGHT FAIL
        if hl.get("series"):
            self.check(hl["series"] in [s.get("name") for s in ser], "CHART_HIGHLIGHT", n, "highlight series %r is not a series name" % hl["series"])  # check: CHART_HIGHLIGHT FAIL
        al = c.get("alert")
        if al:
            self.check(al.get("reason") in T["alert_reasons"], "ALERT_REASON", n, "orange is only for: " + ", ".join(T["alert_reasons"]))  # check: ALERT_REASON FAIL
            self.check(al.get("category") in cats, "ALERT_REASON", n, "alert category %r is not in categories" % al.get("category"))  # check: ALERT_REASON FAIL
        self.check(bool(d.get("source")), "SOURCE_MISSING", n, "charts need a source line")  # check: SOURCE_MISSING FAIL

    def accent(self, n, title, acc):
        if acc:
            self.check(acc.lower() in (title or "").lower() and words(acc) <= 3, "ACCENT", n, "accent %r must be 1-3 words taken from the title" % acc)  # check: ACCENT FAIL

    # ---------------- built .pptx ----------------
    def pptx(self, path, numbered):
        from pptx import Presentation
        from pptx.util import Emu
        prs = Presentation(path)
        W, H = prs.slide_width / 914400, prs.slide_height / 914400
        fit = Fit()
        self.need_notes = {k for k, d, _a in numbered if d.get("layout") in CONTENT | {"summary"}}
        self.by_n = {k: d for k, d, _a in numbered}
        self.appx = {k for k, d, a in numbered if a}
        self.title_bottom = {}
        allowed_colors = set(v.upper() for v in T["colors"].values())
        fonts = {T["fonts"]["display"], T["fonts"]["body"]}
        for n, s in enumerate(prs.slides, 1):
            shapes = list(s.shapes)
            boxes = []
            for sh in shapes:
                x, y, w, h = [v / 914400 for v in (sh.left, sh.top, sh.width, sh.height)]
                if abs(sh.rotation) in (90, 270):
                    cx, cy = x + w / 2, y + h / 2
                    x, y, w, h = cx - h / 2, cy - w / 2, h, w
                self.check(x >= -0.01 and y >= -0.01 and x + w <= W + 0.01 and y + h <= H + 0.01, "OUT_OF_BOUNDS", n, "%s runs off the slide" % sh.name)  # check: OUT_OF_BOUNDS FAIL
                boxes.append((sh.name, x, y, w, h))
                for t in self._texts(sh):
                    self.check(fit.fits(*t), "TEXT_OVERFLOW", n, "text in %s does not fit its box: %r" % (sh.name, t[0][0][0][:50]))  # check: TEXT_OVERFLOW FAIL
                if sh.name.startswith("visual:") and not sh.name.startswith("visual:placeholder"):
                    descr = sh._element.xpath("./*[1]/p:cNvPr/@descr")
                    self.check(bool(descr and descr[0].strip()), "PPTX_ALT", n, "%s has no alt text" % sh.name)  # check: PPTX_ALT FAIL
                xml = sh._element.xml
                for typeface in re.findall(r'<a:latin typeface="([^"]+)"', xml):
                    self.check(typeface in fonts, "FONT", n, "font %r in %s; use %s" % (typeface, sh.name, " or ".join(sorted(fonts))))  # check: FONT FAIL
                for sz in re.findall(r'<a:rPr[^>]*\ssz="(\d+)"', xml):
                    self.check(int(sz) >= 900, "FONT_SIZE", n, "%spt text in %s; minimum is 9pt (footer) and 14pt for content" % (int(sz) / 100, sh.name))  # check: FONT_SIZE FAIL
                    if sh.name in ("body", "takeaway", "callout:text", "kpi:label"):
                        self.check(int(sz) >= 1400, "FONT_SIZE", n, "%spt content text in %s; minimum 14pt" % (int(sz) / 100, sh.name))  # check: FONT_SIZE FAIL
                cols = set(c.upper() for c in re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', xml))
                if sh.has_chart:
                    cols |= set(c.upper() for c in re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', sh.chart._chartSpace.xml))
                for col in cols:
                    self.check(col in allowed_colors, "COLOR", n, "off-palette color #%s in %s" % (col, sh.name))  # check: COLOR FAIL
                if T["colors"]["alert"].upper() in cols:
                    self.check("alert" in sh.name, "ORANGE", n, "the alert color in %s without an alert reason" % sh.name)  # check: ORANGE FAIL
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    a, b = boxes[i], boxes[j]
                    if self._exempt(a[0], b[0]):
                        continue
                    ix = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                    iy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
                    self.check(not (ix > 0.02 and iy > 0.02), "OVERLAP", n, "%s overlaps %s" % (a[0], b[0]))  # check: OVERLAP FAIL
            logos = [[v / 914400 for v in (sh.left, sh.top, sh.width, sh.height)] for sh in s.slide_layout.shapes if sh.name == "Logo"]
            corner = [b for b in logos if b[1] < G["footer_zone_in"]]  # the cover logo; footer-band logos are covered by FOOTER_ZONE
            if n == 1 and getattr(self, "meta", {}).get("logo") != "none":
                has_logo = bool(getattr(self, "brand", None) and self.brand.logo_png("light"))
                self.check(bool(logos) or not has_logo, "LOGO_MISSING", n, "cover is not on a cover layout with the project logo (use meta.cover, not a content layout)")  # check: LOGO_MISSING FAIL
                self.check(has_logo or not getattr(self, "brand", None), "LOGO_NONE", n, "no project logo found, so the cover has none; add one to the brand profile (references/brand.md) if the project has a logo", warn=True)  # check: LOGO_NONE WARN
            for name, x, y, w, h in boxes:
                if name.startswith("bg:"):
                    continue
                self.check(y + h <= G["footer_zone_in"] + 0.01, "FOOTER_ZONE", n, "%s reaches into the footer band (logo, footer line, slide number)" % name)  # check: FOOTER_ZONE FAIL
                for lx, ly, lw, lh in corner:
                    m = 0.25
                    clear = x >= lx + lw + m or x + w <= lx - m or y >= ly + lh + m or y + h <= ly - m
                    self.check(clear, "LOGO_ZONE", n, "%s crowds the logo; keep the logo corner clear" % name)  # check: LOGO_ZONE FAIL
            for sh, txt in self._headings(shapes):
                self.check(txt == proper(txt), "PROPER_CASE", n, "heading %s is not in Proper Case: %r" % (sh, txt[:60]))  # check: PROPER_CASE FAIL
            for sh in shapes:
                if sh.name == "title" and sh.has_text_frame and len(sh.text_frame.paragraphs) == 1:
                    runs = sh.text_frame.paragraphs[0].runs
                    if runs and runs[0].font.size:
                        ptxt = sh.text_frame.paragraphs[0].text
                        fs, fn, fb = runs[0].font.size.pt, runs[0].font.name or T["fonts"]["body"], bool(runs[0].font.bold)
                        avail = sh.width / 914400 - 0.08
                        if "\v" in ptxt:
                            wl = [l.strip() for l in ptxt.split("\v")]
                            for l in wl:
                                self.check(fit.width(l, fs, fn, fb) <= avail + 0.01, "TITLE_BREAK", n, "title line %r is wider than its box; rebuild instead of editing breaks" % l[:40])  # check: TITLE_BREAK FAIL
                        else:
                            wl = fit.wrap(ptxt, fs, fn, fb, avail)
                        seen = [x for l in wl for x in fit.render_wrap(l, fs, fn, fb, avail)]  # D-25: the lines a viewer sees
                        last = seen[-1] if seen else ""
                        self.check(not widow(fit, seen, fs, fn, fb, avail, True), "ORPHAN", n, "title leaves %r alone on its last line (two words or fewer, or under a quarter of the width); shorten or reword it" % last)  # check: ORPHAN FAIL
                        dd = self.by_n.get(n) or {}
                        lk = dd.get("layout", "") + (":" + (dd.get("diagram") or {}).get("kind", "") if dd.get("layout") == "diagram" else "")
                        if lk in ONE_LINE_TITLES or dd.get("layout") in ONE_LINE_TITLES:
                            self.check(len(wl) <= 1, "TITLE_LINES", n, "a %s slide's title must fit one line (it wraps to %d); a second line pushes the content against it" % (lk, len(wl)))  # check: TITLE_LINES FAIL
                        self.title_bottom[n] = sh.top / 914400 + 0.05 + len(wl) * fs * LH(fn, fb) / 72
            self.space(n, s, shapes, fit)
            self.design(n, s, shapes, fit, W, H)
            self.crisp(n, s, shapes, W)
            if n in self.need_notes:
                notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
                self.check(len(notes.split()) >= 8, "PPTX_NOTES", n, "content slide without speaker notes")  # check: PPTX_NOTES FAIL
        self.deck_design(prs, numbered)
        self.check(len(prs.slides) == (numbered[-1][0] if numbered else 1), "SLIDE_COUNT", "-", "built deck has %d slides, deck.json implies %d" % (len(prs.slides), numbered[-1][0] if numbered else 1))  # check: SLIDE_COUNT FAIL

    def space(self, n, s, shapes, fit):
        """TITLE_GAP, EMPTY_SPACE and CARD_FILL: what the built slide looks like, not what deck.json says."""
        d = self.by_n.get(n)
        tb = self.title_bottom.get(n)
        if not d or tb is None:
            return
        skip = lambda nm: nm in ("title", "subtitle", "source", "accent", "meta", "label") or nm.startswith("bg:")
        ttl = next((sh for sh in shapes if sh.name == "title"), None)
        tx0, tx1 = (ttl.left / 914400, (ttl.left + ttl.width) / 914400) if ttl is not None else (0, W_IN)
        body = [(sh.name, sh.top / 914400, (sh.top + sh.height) / 914400) for sh in shapes if not skip(sh.name) and sh.top / 914400 >= tb - 0.3]
        under = [b for b, sh in zip(body, [sh for sh in shapes if not skip(sh.name) and sh.top / 914400 >= tb - 0.3])
                 if min(tx1, (sh.left + sh.width) / 914400) - max(tx0, sh.left / 914400) > 0.2]
        if not body:
            return
        if under and d.get("layout") not in NO_SPACE_CHECK:
            top = min(b[1] for b in under)
            self.check(top - tb >= 0.25, "TITLE_GAP", n, "only %.2f in between the title and %s; keep at least 0.25 in (shorten the title to one line)" % (max(0, top - tb), min(under, key=lambda b: b[1])[0]), warn=True)  # check: TITLE_GAP WARN
        if d.get("layout") not in NO_SPACE_CHECK:
            bottom = max(b[2] for b in body)
            used = (bottom - tb) / max(0.1, G["footer_zone_in"] - 0.35 - tb)
            appx = n in self.appx
            self.check(used >= 0.6, "EMPTY_SPACE", n, "content ends at %d%% of the space under the title; %s" % (round(100 * used),
                       "appendix slides under half full fail; merge or enlarge" if appx and used < 0.5 else "fill it (larger visual, takeaway) or merge the slide"), warn=not (appx and used < 0.5))  # check: EMPTY_SPACE FAIL # check: EMPTY_SPACE WARN
        for sh in shapes:
            if sh.shape_type != 6 or sh.name not in ("kpi", "kpi:alert", "cards:card"):
                continue
            kids = list(sh.shapes)
            card = next((k for k in kids if k.name == "card"), None)
            if card is None:
                continue
            ct, ch = card.top / 914400, card.height / 914400
            bots = []
            for k in kids:
                if k is card or not getattr(k, "has_text_frame", False) or not k.text_frame.text.strip():
                    continue
                kt, kh, kw = k.top / 914400, k.height / 914400, k.width / 914400
                th = 0.0
                for p in k.text_frame.paragraphs:
                    size = next((r.font.size.pt for r in p.runs if r.font.size), 14)
                    th += fit.lines(p.text, size, (p.runs[0].font.name if p.runs else None) or T["fonts"]["body"], bool(p.runs and p.runs[0].font.bold), kw - 0.1) * size * LH(p.runs[0].font.name if p.runs else None) / 72
                ctr = k.text_frame._bodyPr.get("anchor") == "ctr"
                bots.append(kt + (kh + th) / 2 if ctr else kt + 0.05 + th)
            if bots:
                empty = (ct + ch - max(bots)) / ch
                self.check(empty <= 0.35, "CARD_FILL", n, "%s: the bottom %d%% of the card is empty; center the text or let the card shrink to it" % (sh.name, round(100 * empty)), warn=True)  # check: CARD_FILL WARN

    HEADINGS = ("title", "subtitle", "label", "label:decision", "kpi:label", "diagram:label", "diagram:axis", "diagram:when")

    def crisp(self, n, s, shapes, W):
        """Modern-minimal finish on the built slide: one size per sibling group, clean margins, no near-miss alignment, hairline weights."""
        sizes = {}
        def walk(shs):
            for sh in shs:
                if sh.shape_type == 6:
                    walk(list(sh.shapes))
                elif sh.name in T.get("sib_names", []) and sh.has_text_frame:
                    for p in sh.text_frame.paragraphs:
                        for r in p.runs:
                            if r.font.size:
                                sizes.setdefault(sh.name, set()).add(r.font.size.pt)
        walk(shapes)
        for name, v in sizes.items():
            self.check(len(v) == 1, "SIBLING_SIZE", n, "%s text uses %d sizes (%s); siblings share one size" % (name, len(v), ", ".join("%g" % x for x in sorted(v))))  # check: SIBLING_SIZE FAIL
        def marker_groups(shs):
            for sh in shs:
                if sh.shape_type == 6:
                    kids = list(sh.shapes)
                    marks = [k for k in kids if k.name.endswith(":num")]
                    texts = [k for k in kids if k.shape_type != 6 and getattr(k, "has_text_frame", False) and k.has_text_frame and k.text_frame.text.strip() and not k.name.endswith(":num")]
                    if marks and texts:
                        yield marks[0], texts
                    yield from marker_groups(kids)
        E = 914400.0
        for m, texts in marker_groups(shapes):
            mx, my, mw, mh = m.left / E, m.top / E, m.width / E, m.height / E
            right = [t for t in texts if t.left / E >= mx + mw - 0.01 and abs(t.top / E - my) < 1.0]
            below = [t for t in texts if t.top / E >= my + mh - 0.01 and abs(t.left / E - mx) < 0.6]
            if right:
                t = min(right, key=lambda t: t.left)
                runs = [r for p in t.text_frame.paragraphs for r in p.runs]
                fs = runs[0].font.size.pt if runs and runs[0].font.size else 18
                anchor = t.text_frame.vertical_anchor
                if anchor in (None, 1):
                    line_c = t.top / E + 0.04 + FL(runs[0].font.name if runs else None) * fs / 72.0
                    self.check(abs(line_c - (my + mh / 2)) <= 0.035, "MARKER_ALIGN", n, "number %s is %.2f in off the center of its text's first line" % (m.name, (my + mh / 2) - line_c))  # check: MARKER_ALIGN FAIL
                else:
                    self.check(abs((t.top / E + t.height / E / 2) - (my + mh / 2)) <= 0.035 or len(t.text_frame.text) < 60, "MARKER_ALIGN", n, "number %s is not centered on its text" % m.name)  # check: MARKER_ALIGN FAIL
            elif below:
                t = min(below, key=lambda t: t.top)
                self.check(abs((t.left / E + 0.04) - mx) <= 0.02, "MARKER_ALIGN", n, "number %s is not flush with the left edge of its text (%.2f in)" % (m.name, mx - (t.left / E + 0.04)))  # check: MARKER_ALIGN FAIL
        d = getattr(self, "by_n", {}).get(n) or {}
        lay, kind = d.get("layout"), (d.get("diagram") or {}).get("kind")
        if lay in CENTERED_LAYOUTS or (lay == "diagram" and kind in CENTERED_DIAGRAMS):
            body = [sh for sh in shapes if not sh.name.startswith("bg:") and sh.name not in ("title", "source", "takeaway")
                    and sh.top / E >= 1.8 and sh.top / E < 6.45]
            if body:
                l = min(sh.left for sh in body) / E; r = max(sh.left + sh.width for sh in body) / E
                self.check(abs((l + r) / 2 - W / 2) <= 0.03, "CENTERED", n, "the %s block is %.2f in off the slide's center line" % (lay if lay != "diagram" else kind, (l + r) / 2 - W / 2))  # check: CENTERED FAIL
        lefts = []
        for sh in shapes:
            if sh.name.startswith("bg:"):
                continue
            x, w = sh.left / 914400, sh.width / 914400
            self.check(x >= 0.55 and x + w <= W - 0.55, "EDGE_MARGIN", n, "%s sits within 0.55 in of the slide edge; keep the margins clean" % sh.name)  # check: EDGE_MARGIN FAIL
            lefts.append(round(x, 3))
        u = sorted(set(lefts))
        for a, b in zip(u, u[1:]):
            self.check(not (0.045 < b - a < 0.12), "NEAR_MISS", n, "left edges at %.2f and %.2f in almost line up; align them exactly or separate them clearly" % (a, b))  # check: NEAR_MISS FAIL
        for sh in shapes:
            if getattr(sh, "has_chart", False) and sh.has_chart:
                continue
            xml = re.sub(r'<p:sp>(?:(?!</p:sp>).)*?name="icon:[^"]*"(?:(?!</p:sp>).)*?</p:sp>', "", sh._element.xml, flags=re.S) if sh.shape_type == 6 else ("" if sh.name.startswith("icon:") else sh._element.xml)
            for wv in re.findall(r'<a:ln w="(\d+)"', xml):
                self.check(int(wv) <= 28575, "LINE_WEIGHT", n, "%gpt line in %s; keep rules and outlines at 2.25pt or lighter" % (int(wv) / 12700, sh.name))  # check: LINE_WEIGHT FAIL
        def all_shapes(shs):
            for sh in shs:
                if sh.shape_type == 6:
                    yield from all_shapes(list(sh.shapes))
                else:
                    yield sh
        for sh in all_shapes(shapes):
            if sh.name.startswith("icon:"):
                sz = sh.width / 914400.0
                self.check(0.2 <= sz <= 0.8 and abs(sh.width - sh.height) < 9144, "ICON_SIZE", n, "icon %s is %.2f in; keep icons square and 0.2-0.8 in" % (sh.name, sz))  # check: ICON_SIZE FAIL

    def _headings(self, shapes):
        for sh in shapes:
            if sh.shape_type == 6:
                yield from self._headings(list(sh.shapes))
            elif sh.name in self.HEADINGS and sh.has_text_frame:
                yield sh.name, sh.text_frame.text.replace("\u2191", "").replace("\u2192", "").strip()
            elif sh.has_table:
                for c in sh.table.rows[0].cells:
                    yield "table header", c.text_frame.text

    @staticmethod
    def _exempt(a, b):
        if a.startswith("bg:") or b.startswith("bg:"):
            return True
        if any(x.startswith("callout:marker") for x in (a, b)) and any(x.startswith("visual:") for x in (a, b)):
            return True
        return False

    def _texts(self, sh):
        out = []
        if sh.shape_type == 6:  # group
            for c in sh.shapes:
                out += self._texts(c)
            return out
        if not getattr(sh, "has_text_frame", False) or not sh.has_text_frame or abs(sh.rotation) in (90, 270):
            return out
        tf = sh.text_frame
        paras = []
        for p in tf.paragraphs:
            runs = [(r.text, (r.font.size.pt if r.font.size else 18), r.font.name or T["fonts"]["body"], bool(r.font.bold)) for r in p.runs]
            if runs:
                after = p.space_after.pt if p.space_after is not None else 0
                bullet = p._p.pPr is not None and p._p.pPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar") is not None
                paras.append((" ".join(r[0] for r in runs), runs[0][1], runs[0][2], runs[0][3], after, bullet))
        if not paras:
            return out
        ins = lambda v: (v or 0) / 914400
        w = sh.width / 914400 - ins(tf.margin_left) - ins(tf.margin_right)
        h = sh.height / 914400 - ins(tf.margin_top) - ins(tf.margin_bottom)
        out.append(([(p[0],) for p in paras], paras, w, h, sh.shape_type == 1))
        return out

    def report(self, story_lines=None):
        print("LINT: %d checks, %d failed, %d warnings" % (self.checks, len(self.fails), len(self.warns)))
        for l in self.fails + self.warns:
            print(l)
        if story_lines:
            print("Title read-through (does it tell the story on its own?):")
            for l in story_lines:
                print("  " + l)
            if getattr(self, "rhythm", None):
                print("Rhythm (S summary or contents, D data, V visual, T text, H hero, C closing or contact): " + self.rhythm)
                if getattr(self, "msgs", None):
                    print("Message -> layout:")
                    for line in self.msgs:
                        print("  " + line)
                print("Tone (W white, L light tint, N dark, B primary): " + self.tones)
        return 1 if self.fails else 0


    # ---------------- 2.9: what the reader sees on the built slide (Training Deck Design Standard) ----------------
    ACCENT_T = 0.08
    CARD_NAMES = ("card", "diagram:card", "callout:box")
    HEAD_NAMES = ("diagram:label",)
    RULE_NAMES = ("accent", "step:rule", "qa:rule", "check:rule", "contents:rule", "diagram:line", "diagram:stem", "accent:line", "split:panel")
    MINOR = SMALL | {"with", "from", "into", "then", "than", "that", "this", "your", "our"}

    @staticmethod
    def _flat(shapes):
        for sh in shapes:
            if sh.shape_type == 6:
                yield from Lint._flat(sh.shapes)
            else:
                yield sh

    @staticmethod
    def _box(sh):
        return sh.left / 914400, sh.top / 914400, sh.width / 914400, sh.height / 914400

    @staticmethod
    def _fill_hex(sh):
        try:
            if sh.fill.type == 1:
                return str(sh.fill.fore_color.rgb).upper()
        except Exception:
            return None
        return None

    @staticmethod
    def _contrast(a, b):
        def lum(h):
            c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        la, lb = lum(a), lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def _para_lines(self, fit, p, avail):
        size = next((r.font.size.pt for r in p.runs if r.font.size), 14)
        font = next((r.font.name for r in p.runs if r.font.name), None) or T["fonts"]["body"]
        bold = bool(p.runs and p.runs[0].font.bold)
        lines = []
        for part in p.text.split("\v"):  # a typed line break starts a new line
            lines += fit.wrap(part, size, font, bold, avail) or [""]
        return lines, size, font, bold

    def design(self, n, s, shapes, fit, W, H):
        from pptx.oxml.ns import qn
        d = self.by_n.get(n) or {}
        lay = d.get("layout", "cover" if n == 1 else "")
        kind = (d.get("diagram") or {}).get("kind")
        flat = list(self._flat(shapes))
        layout_name = s.slide_layout.name
        tone = {name: T["layout_bg"][key] for key, (_mi, name) in T["layouts"].items()}.get(layout_name, "white")
        slide_bg = C[tone]
        # ACCENT_STYLE / ACCENT_RADIUS
        cards = [sh for sh in flat if sh.name in self.CARD_NAMES]
        if self.meta.get("accent_style") != "line":
            for sh in flat:
                try:
                    flat_rect = sh.shape_type == 1 and sh.auto_shape_type == 1
                except Exception:
                    flat_rect = False
                if not flat_rect or sh.name in self.RULE_NAMES or sh.name.startswith(("bg:", "bar", "visual:")):
                    continue
                x, y, w, h = self._box(sh)
                if min(w, h) >= 0.12 or max(w, h) < 0.4:
                    continue
                for c in cards:
                    cx, cy, cw, ch = self._box(c)
                    inside = x >= cx - 0.04 and y >= cy - 0.04 and x + w <= cx + cw + 0.04 and y + h <= cy + ch + 0.04
                    edge = min(abs(y - cy), abs(x - cx), abs(cy + ch - y - h), abs(cx + cw - x - w)) <= 0.12
                    if inside and edge:
                        self.check(False, "ACCENT_STYLE", n, "flat accent strip %r on the edge of %s; use the rounded accent tab (accent_card)" % (sh.name, c.name))  # check: ACCENT_STYLE FAIL
                        break
        for grp in [sh for sh in shapes if sh.shape_type == 6] + [s]:
            kids = list(grp.shapes)
            for a in [k for k in kids if k.name == "accent:back"]:
                ax, ay, aw, ah = self._box(a)
                mate = next((k for k in kids if k.name in self.CARD_NAMES and abs(k.left / 914400 - ax) < 0.1 + self.ACCENT_T and abs(k.top / 914400 - ay) < 0.1 + self.ACCENT_T), None)
                if mate is not None:
                    ra = a.adjustments[0] * min(aw, ah) if len(a.adjustments) else 0
                    mx, my, mw, mh = self._box(mate)
                    rm = mate.adjustments[0] * min(mw, mh) if len(mate.adjustments) else 0
                    self.check(abs(ra - rm) <= 0.015, "ACCENT_RADIUS", n, "accent corner radius %.2f in vs card %.2f in; use the same radius in inches" % (ra, rm))  # check: ACCENT_RADIUS FAIL
        # paired cards: PAIRED_ALIGNMENT, CARD_FILL_BALANCE
        # A card's outer box is its accent tab's when it has one (accent_card keeps x, y, w, h on the tab); its kind is
        # the group it sits in. Rows are cards whose outer tops lie within 0.15 in of each other.
        outer, kind = {}, {}
        for g in [sh for sh in shapes if sh.shape_type == 6]:
            kids = list(g.shapes)
            back = next((k for k in kids if k.name == "accent:back"), None)
            for k in kids:
                if k.name in self.CARD_NAMES:
                    kind[k.shape_id] = g.name
                    if back is not None:
                        outer[k.shape_id] = back
        rows, last = {}, None
        for c in sorted([c for c in cards if c.name != "callout:box"], key=lambda c: outer.get(c.shape_id, c).top):
            t = outer.get(c.shape_id, c).top / 914400
            if last is None or t - last > 0.15:
                key = t
            rows.setdefault(key, []).append(c)
            last = t
        texts = [sh for sh in flat if getattr(sh, "has_text_frame", False) and sh.text_frame.text.strip()]
        def inside(t, c):
            tx, ty, tw, th = self._box(t); cx, cy, cw, ch = self._box(c)
            return cx - 0.05 <= tx + tw / 2 <= cx + cw + 0.05 and cy - 0.05 <= ty + th / 2 <= cy + ch + 0.05
        def text_h(t):
            tw = t.width / 914400 - 0.1
            def para_h(p):
                lines, size, font, bold = self._para_lines(fit, p, tw)
                return len(lines) * size * LH(font, bold) / 72
            return sum(para_h(p) for p in t.text_frame.paragraphs if p.text.strip())
        for top, row in rows.items():
            if len(row) < 2:
                continue
            ob = [outer.get(c.shape_id, c) for c in row]
            same_kind = len({kind.get(c.shape_id) for c in row}) == 1
            ws = [o.width / 914400 for o in ob] if same_kind else [row[0].width / 914400] * len(row)  # a main card and its aside may differ in width
            hs = [o.height / 914400 for o in ob]
            firsts = []
            fills = []
            for c in row:
                ins = [t for t in texts if inside(t, c)]
                firsts.append(min((t.top / 914400 for t in ins), default=None))
                fills.append(sum(text_h(t) for t in ins) / max(0.1, c.height / 914400))
            ft = [f for f in firsts if f is not None]
            ok = max(ws) - min(ws) <= 0.03 and max(hs) - min(hs) <= 0.03 and (not ft or max(ft) - min(ft) <= 0.06)
            self.check(ok, "PAIRED_ALIGNMENT", n, "side-by-side cards differ in width, height or first text line (widths %s, heights %s)" % ([round(x, 2) for x in ws], [round(x, 2) for x in hs]))  # check: PAIRED_ALIGNMENT FAIL
            if fills:
                self.check(max(fills) - min(fills) <= 0.35, "CARD_FILL_BALANCE", n, "paired cards look unbalanced: text fills %s of each card (bullet counts may differ; even out the text)" % ["%d%%" % round(100 * f) for f in fills], warn=True)  # check: CARD_FILL_BALANCE WARN
        # MATCHED_HEADINGS
        heads = [t for t in texts if t.name in self.HEAD_NAMES]
        sets = {}
        for t in heads:
            sets.setdefault(round(t.top / 914400 * 4) / 4, []).append(t)
        for top, hs in sets.items():
            if len(hs) < 2 or len({round(h.left / 914400, 1) for h in hs}) < 2:
                continue
            props = []
            for h in hs:
                p = h.text_frame.paragraphs[0]
                wl, size, font, bold = self._para_lines(fit, p, h.width / 914400 - 0.1)
                col = next((str(r.font.color.rgb) for r in p.runs if r.font.color and r.font.color.type is not None), "")
                props.append((len(wl), size, bold, col))
            same_color = lay == "diagram" and kind == "comparison" or lay == "callouts"
            keyset = {(a, b, c) for a, b, c, _ in props}
            colors = {p[3] for p in props}
            ok = len(keyset) == 1 and (not same_color or len(colors) == 1)
            self.check(ok, "MATCHED_HEADINGS", n, "headings in side-by-side cards differ (lines, size, bold, color): %s; make them one line in one style" % props)  # check: MATCHED_HEADINGS FAIL
        # COMPARISON_CONNECTOR
        if lay == "diagram" and kind == "comparison":
            arrow = [sh for sh in flat if sh.name == "diagram:arrow" or (getattr(sh, "has_text_frame", False) and sh.text_frame.text.strip() in ("\u2192", "\u2190", "->"))]
            self.check(not arrow, "COMPARISON_CONNECTOR", n, "a comparison uses an arrow, which implies one side leads to the other; use the neutral 'vs' marker")  # check: COMPARISON_CONNECTOR FAIL
        # TEXT_COLLISION (rendered text areas overlap)
        areas = []
        for t in texts:
            if t.name.startswith(("visual:", "bg:")) or t.has_text_frame is False:
                continue
            x, y, w, h = self._box(t)
            th = min(h, text_h(t))
            anc = t.text_frame.vertical_anchor
            ty = y + (h - th) / 2 if anc == 3 else y + h - th if anc == 4 else y
            areas.append((t.name, x, ty, w, th))
        for i in range(len(areas)):
            for j in range(i + 1, len(areas)):
                a, b = areas[i], areas[j]
                ix = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]); iy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
                self.check(not (ix > 0.05 and iy > 0.05), "TEXT_COLLISION", n, "text in %s runs into %s" % (a[0], b[0]))  # check: TEXT_COLLISION FAIL
        # LAST_LINE_ORPHAN, LABEL_BREAK, HIGHLIGHT_SPLIT
        for t in texts:
            avail = t.width / 914400 - 0.08
            for p in t.text_frame.paragraphs:
                if not p.text.strip():
                    continue
                wl, size, font, bold = self._para_lines(fit, p, avail)
                for wd in fit.words_of(p.text.replace("\v", " ")):
                    if fit.width(wd, size, font, bold) > avail + 0.02:
                        self.check(False, "LABEL_BREAK", n, "%r is wider than %s and will break inside the word" % (wd[:30], t.name))  # check: LABEL_BREAK FAIL
                if t.name in ("title", "subtitle", "diagram:label", "takeaway:text") and len(wl) >= 2:
                    last = wl[-1].strip()
                    self.check(not widow(fit, wl, size, font, bold, avail, False), "LAST_LINE_ORPHAN", n, "%r sits alone on the last line of %s; reword or shorten" % (last, t.name))  # check: LAST_LINE_ORPHAN FAIL
                cols = [str(r.font.color.rgb) if r.font.color and r.font.color.type is not None else "" for r in p.runs]
                if t.name == "title" and len(set(cols)) >= 2:
                    base = cols[0]
                    pos, spans = 0, []
                    for el in p._p:  # walk runs and line breaks in order, so offsets match p.text
                        if el.tag == qn("a:br"):
                            pos += 1
                        elif el.tag == qn("a:r"):
                            rt = "".join(x.text or "" for x in el.iter(qn("a:t")))
                            clr = el.find(".//" + qn("a:srgbClr"))
                            if clr is not None and clr.get("val", "").upper() != base.upper():
                                spans.append((pos, pos + len(rt), rt))
                            pos += len(rt)
                    breaks, acc = [], 0
                    for line in wl[:-1]:
                        acc += len(line) + 1; breaks.append(acc)
                    for a0, a1, txt in spans:
                        split = any(a0 < b < a1 for b in breaks)
                        minor = all(w.lower().strip(",.") in self.MINOR for w in txt.split())
                        self.check(not split and not minor, "HIGHLIGHT_SPLIT", n, "highlight %r %s; highlight a whole phrase that fits on one line" % (txt.strip(), "breaks across lines" if split else "covers only minor words"))  # check: HIGHLIGHT_SPLIT FAIL
        # table cells: LAST_LINE_ORPHAN, LABEL_BREAK, STATUS_TAG
        for gf in [sh for sh in flat if getattr(sh, "has_table", False) and sh.has_table]:
            tbl = gf.table
            widths = [c.width / 914400 for c in tbl.columns]
            for ri, row in enumerate(tbl.rows):
                for ci, cell in enumerate(row.cells):
                    avail = widths[ci] - 0.3
                    for p in cell.text_frame.paragraphs:
                        if not p.text.strip():
                            continue
                        wl, size, font, bold = self._para_lines(fit, p, avail)
                        for wd in fit.words_of(p.text):
                            if fit.width(wd, size, font, bold) > avail + 0.02:
                                self.check(False, "LABEL_BREAK", n, "%r is wider than its table column and will break inside the word" % wd[:30])  # check: LABEL_BREAK FAIL
                        if len(wl) >= 2:
                            last = wl[-1].strip()
                            self.check(not (len(fit.words_of(last)) == 1 or re.fullmatch(r"\(.*\)", last)), "LAST_LINE_ORPHAN", n, "%r sits alone on the last line of a table cell" % last)  # check: LAST_LINE_ORPHAN FAIL
                        if ri > 0:
                            m = STATUS_AT_START.match(p.text)
                            if m:
                                r0 = p.runs[0] if p.runs else None
                                tagged = r0 is not None and r0.text.startswith(m.group(1)) and bool(r0.font.bold) and r0.font.color and r0.font.color.type is not None and str(r0.font.color.rgb).upper() == C["primary"].upper()
                                self.check(tagged, "STATUS_TAG", n, "status %r in a table cell isn't styled as a tag (bold, in the primary color)" % m.group(1))  # check: STATUS_TAG FAIL
        # ACCENT_CONTRAST
        fills = [(sh, self._box(sh), self._fill_hex(sh)) for sh in flat if self._fill_hex(sh) and not getattr(sh, "has_text_frame", False) or (self._fill_hex(sh) and sh.name in self.CARD_NAMES + ("accent:back", "bg:panel", "bg:band"))]
        order = {id(sh): i for i, sh in enumerate(flat)}
        for t in texts:
            if t.name.startswith("visual:"):
                continue
            x, y, w, h = self._box(t)
            cx, cy = x + w / 2, y + min(h, 0.6) / 2
            under = [f for f in fills if order.get(id(f[0]), 0) < order.get(id(t), 0) and f[1][0] <= cx <= f[1][0] + f[1][2] and f[1][1] <= cy <= f[1][1] + f[1][3]]
            bg = (under[-1][2] if under else (self._fill_hex(t) or slide_bg))
            for p in t.text_frame.paragraphs:
                pcols = {str(r.font.color.rgb).upper() for r in p.runs if r.text.strip() and r.font.color and r.font.color.type is not None}
                base = next((str(r.font.color.rgb).upper() for r in p.runs if r.text.strip() and r.font.color and r.font.color.type is not None), None)
                for r in p.runs:
                    if not r.text.strip() or not (r.font.color and r.font.color.type is not None):
                        continue
                    fg = str(r.font.color.rgb).upper()
                    size = r.font.size.pt if r.font.size else 14
                    need = 3.0 if size >= 24 else 4.5
                    accent = (len(pcols) >= 2 and fg != base) or t.name == "label:decision"
                    if accent:
                        cr = self._contrast(fg, bg)
                        self.check(cr >= need, "ACCENT_CONTRAST", n, "%r in %s is %.1f:1 on #%s; needs %.1f:1 (accent words use 'context' on dark and 'card' on primary)" % (r.text[:30], t.name, cr, bg, need))  # check: ACCENT_CONTRAST FAIL
        # MARKER_BUSY
        if lay == "diagram" and kind == "process":
            numerals = [sh for sh in flat if sh.name == "diagram:node" and getattr(sh, "has_text_frame", False) and sh.text_frame.text.strip().isdigit()]
            icons = [sh for sh in flat if sh.name.startswith("icon")]
            self.check(not (numerals and icons and not (d.get("diagram") or {}).get("numbered")), "MARKER_BUSY", n, "numbered markers plus icons make the step diagram busy; use hollow dots or set numbered: true", warn=True)  # check: MARKER_BUSY WARN
        # EMPTY_BAND, TOP_GAP
        tb = self.title_bottom.get(n)
        body = [self._box(sh) for sh in shapes if sh.name not in ("title", "subtitle", "source", "accent", "meta", "label", "draft:mark") and not sh.name.startswith("bg:")]
        if lay and lay not in NO_SPACE_CHECK | {"cover"} and body:
            top = min(b[1] for b in body)
            self.check(top <= 0.40 * H, "EMPTY_BAND", n, "content starts %d%% down the slide, leaving an empty band under the title" % round(100 * top / H), warn=True)  # check: EMPTY_BAND WARN
            if tb is not None:
                self.check(top - tb <= 1.2, "TOP_GAP", n, "content starts %.1f in below the title (over 1.2 in); center it in the band" % (top - tb), warn=True)  # check: TOP_GAP WARN

    def deck_design(self, prs, numbered):
        feet = []
        for n, s in enumerate(prs.slides, 1):
            ft = next((sh.text_frame.text for sh in s.slide_layout.shapes if sh.name.startswith("Footer") and sh.has_text_frame), None)
            if ft:
                feet.append((n, ft))
        if feet:
            base = feet[0][1]
            odd = [n for n, f in feet if f != base]
            self.check(not odd, "FOOTER_CONSISTENT", "-", "footer text differs on slides %s (%r)" % (odd, next((f for n, f in feet if f != base), "")[:70]))  # check: FOOTER_CONSISTENT FAIL
        cp = prs.core_properties
        self.check(bool((cp.title or "").strip()) and (cp.subject or "").strip() != "Standardization", "CORE_PROPS", "-", "file details: title %r, subject %r; set them from meta.title and meta.subtitle" % (cp.title, cp.subject))  # check: CORE_PROPS FAIL
        if self.draft:
            cover = list(self._flat(prs.slides[0].shapes)) if len(prs.slides) else []
            mark = any(sh.name == "draft:mark" or (getattr(sh, "has_text_frame", False) and sh.text_frame.text.strip().lower().startswith("draft")) for sh in cover)
            self.check(mark, "DRAFT_MARK", 1, "built with --draft but the cover shows no draft mark")  # check: DRAFT_MARK FAIL


class Fit:
    """Greedy word-wrap measured with the font files themselves: the project's fonts (its own files, or installed),
    else the bundled fallback (brand.py measure_path). Display text is measured in the display font at its weight.
    Without Pillow, an average-width estimate is used and the check says less."""
    def __init__(self):
        self.cache = {}
        try:
            from PIL import ImageFont
            self.IF = ImageFont
        except ImportError:
            self.IF = None

    def face(self, font, bold, px):
        role = role_of(font)
        path = BRAND.measure_path(role, bool(bold or role == "display"))
        if not (self.IF and path):
            return None
        key = (path, px)
        if key not in self.cache:
            self.cache[key] = self.IF.truetype(path, px)
        return self.cache[key]

    def width(self, text, size, font, bold):
        f = self.face(font, bold, int(size * 4))
        if f is None:
            return len(text) * size * 0.52 / 72
        return f.getlength(text) / 4 / 72

    @staticmethod
    def words_of(text):
        """Break opportunities are ordinary spaces only; a no-break space (U+00A0) keeps pairs like 'Nov 17' together."""
        return [w for w in re.split(r"[ \t\n]+", text or "") if w]

    def wrap(self, text, size, font, bold, avail):
        out, cur = [], ""
        for word in self.words_of(text):
            trial = (cur + " " + word).strip()
            if self.width(trial, size, font, bold) <= avail or not cur:
                cur = trial
            else:
                out.append(cur); cur = word
        if cur:
            out.append(cur)
        return out

    def lines(self, text, size, font, bold, avail):
        return len(self.wrap(text, size, font, bold, avail)) if text else 0

    def render_wrap(self, text, size, font, bold, avail):
        """D-25: the wrap a viewer sees. When the brand font has no file on this machine, a renderer substitutes another
        face (fc-match; LibreOffice may draw it as Noto Sans Bold, a few percent wider), so a line breaks where either
        the measured font or that substitute runs out of room. With the font available, or no fc-match, this equals wrap()."""
        faces = self.__dict__.setdefault("faces", {})
        role = role_of(font)
        key = (font, bool(bold or role == "display"))
        if BRAND.font_path(role, key[1]):
            return self.wrap(text, size, font, bold, avail)
        if key not in faces:
            faces[key] = None
            if self.IF and shutil.which("fc-match"):
                r = subprocess.run(["fc-match", "-f", "%{family}\t%{file}", font + (":bold" if key[1] else "")], capture_output=True, text=True,
                                   env=BR.fontconfig_env(BRAND.font_dirs())).stdout.strip()
                fam, _, path = r.partition("\t")
                if path and font.lower() not in fam.lower():
                    try:
                        faces[key] = self.IF.truetype(path, 200)
                    except OSError:
                        faces[key] = None
        face = faces[key]
        if face is None:
            return self.wrap(text, size, font, bold, avail)
        wide = lambda t: max(self.width(t, size, font, bold), face.getlength(t) * size / 200.0 / 72)
        out, cur = [], ""
        for word in self.words_of(text):
            trial = (cur + " " + word).strip()
            if wide(trial) <= avail or not cur:
                cur = trial
            else:
                out.append(cur); cur = word
        if cur:
            out.append(cur)
        return out

    def fits(self, _labels, paras, w, h, is_autoshape):
        total = 0.0
        for text, size, font, bold, after, bullet in paras:
            avail = w - (size * 1.1 / 72 if bullet else 0)
            lines, cur = 1, ""
            for word in self.words_of(text):
                trial = (cur + " " + word).strip()
                if self.width(trial, size, font, bold) <= avail:
                    cur = trial
                else:
                    if not cur:
                        return False
                    lines, cur = lines + 1, word
            total += lines * size * LH(font, bold) / 72 + after / 72
        return total <= h + 0.04


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck"); ap.add_argument("--pptx"); ap.add_argument("--draft", action="store_true"); ap.add_argument("--story", action="store_true")
    ap.add_argument("--brand", help="brand profile (default: the one the build uses)")
    a = ap.parse_args()
    deck = normalize(json.load(open(a.deck, encoding="utf-8")))
    L = Lint(a.draft)
    L.brand = use_brand(BR.load(source=a.deck, brand=a.brand))
    L.deck_path = os.path.abspath(a.deck)
    numbered = L.deck(deck, os.path.dirname(os.path.abspath(a.deck)))
    if a.pptx:
        if not os.path.isfile(a.pptx):
            print("NOT RUN: %s does not exist (the build was refused or the path is wrong); fix deck.json and rebuild first" % a.pptx)
            sys.exit(1)
        L.pptx(a.pptx, numbered)
    story = None
    if a.story:
        story = ["1 " + deck.get("meta", {}).get("title", "")] + ["%s %s" % (n, d.get("title") or d.get("text", "")) for n, d, ap_ in numbered if not ap_]
    sys.exit(L.report(story))


if __name__ == "__main__":
    main()
