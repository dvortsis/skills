#!/usr/bin/env python3
"""Gate for a textbook-style GitHub Markdown guide (references/structure.md, references/voice.md).

  python3 scripts/lint_docs.py docs [--strict]

Prints `LINT: <n> checks, <f> failed, <w> warnings`, then one FAIL/WARN line per finding as
`FAIL [CODE] file:line: message`. Exit 1 on any FAIL. --strict also fails on warnings (use before a release).
"""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mdlib as M  # noqa: E402

SHELL = {"bash", "sh", "shell", "console", "zsh", "powershell", "ps1", "pwsh", "cmd", "bat", "batch", "fish"}
WHERE = re.compile(r"(?i)\b(terminal|console|powershell|command prompt|shell|ssh|cmd|>_|on the server|on your server|"
                   r"in the [\w ]{0,30}(window|tab|app|folder|panel)|run (this|these|it) (in|on|from)|paste (it |this )?(in|into))\b|>_")
PAD_FAIL = re.compile(r"(?i)\b(don'?t worry|no need to worry|rest assured|needless to say|simply|obviously|of course|feel free to|"
                      r"please note|it(?:'s| is) important to note|it(?:'s| is) worth noting|nothing can go wrong|don'?t panic)\b")
PAD_WARN = re.compile(r"(?i)\b(just|easy|easily|basically|in order to|very|really|actually|quickly and easily)\b")
NEGATIVE = re.compile(r"(?i)\b(don'?t|do not|never|avoid|unsafe|not recommended|isn'?t safe)\b")
ALTERNATIVE = re.compile(r"(?i)\b(instead|use|keep|choose|set|turn on|turn off|leave|safe|recommended|only|change|add|select)\b")
SECRET = re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd|access[_-]?key)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-+/=.]{12,})")  # also BEACON_API_KEY=...
TOKEN_SHAPES = re.compile(r"\b(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bap]-[A-Za-z0-9-]{20,})\b")
PLACEHOLDER = re.compile(r"WRITE:|\bTODO\b|\bTBD\b|(?i:lorem ipsum)|\bFIXME\b")
BAD_OBJECTIVE = re.compile(r"(?i)^(understand|know|learn about|be aware|appreciate|grasp|get familiar)\b")
CHOICE_HEAD = {"option", "choice", "value", "mode"}


class Lint:
    def __init__(self, docs):
        self.docs, self.checks, self.fails, self.warns = docs, 0, [], []

    def check(self, ok, code, where, msg, warn=False):
        self.checks += 1
        if not ok:
            (self.warns if warn else self.fails).append("%s [%s] %s: %s" % ("WARN" if warn else "FAIL", code, where, msg))
        return ok

    def run(self):
        d = self.docs
        if not os.path.isdir(d):
            self.check(False, "STRUCTURE", d, "docs folder not found"); return
        order, chapters, appx = M.guide_pages(d)
        self.pages = {n: M.Page(os.path.join(d, n)) for n in order}
        self.order, self.chapters, self.appx = order, chapters, appx
        self.structure()
        for n in order:
            self.page(n, self.pages[n])
        for n in chapters:
            self.chapter(n, self.pages[n])
        self.answers()
        self.glossary()
        self.sync_state()

    # ---------------- guide-wide
    def structure(self):
        names = set(self.order)
        for need in ("README.md", "glossary.md", "revisions.md", "index.md"):
            self.check(need in names, "STRUCTURE", "docs", "%s is missing (references/structure.md)" % need)
        self.check(len(self.chapters) >= 2, "STRUCTURE", "docs", "a guide needs at least two chapters (01-*.md, 02-*.md)")
        nums = [int(c[:2]) for c in self.chapters]
        self.check(nums == list(range(1, len(nums) + 1)), "CHAPTER_FILES", "docs", "chapter files must be numbered 01, 02, ... without gaps (found %s)" % nums)
        titles = {n: self.h1(n) for n in self.chapters}
        self.check(any(re.search(r"(?i)\bsafe|secur", t) for t in titles.values()), "SECURITY_CHAPTER", "docs",
                   "no chapter about keeping the app safe (a chapter title with 'safe' or 'secure')")
        trouble = any(self.is_trouble_table(h) for p in self.pages.values() for _, h, _r in p.tables())
        self.check(trouble, "TROUBLESHOOTING", "docs", "no troubleshooting table (Problem | Likely cause | Fix)")
        self.check(any(re.search(r"(?i)setting", a) for a in self.appx), "SETTINGS_REFERENCE", "docs",
                   "no settings reference appendix (appendix-b-settings-reference.md) listing every field", warn=True)
        ex = any("**Worked example**" in "\n".join(b) for p in self.pages.values() for _, k, b, _ok in p.alerts())
        self.check(ex, "WORKED_EXAMPLE", "docs", "the guide has no worked example (a [!NOTE] alert starting **Worked example**)")
        self.check(any(self.questions(self.pages[c]) for c in self.chapters), "CHECKS", "docs",
                   "no chapter has Check your understanding questions", warn=True)
        if "README.md" in self.pages:
            self.home(self.pages["README.md"])
        if "revisions.md" in self.pages:
            t = [x for x in self.pages["revisions.md"].tables() if [c.lower() for c in x[1][:3]] == ["version", "date", "change"]]
            self.check(bool(t and t[0][2]), "REVISIONS", "revisions.md", "needs a Version | Date | Change table with at least one row")
        if "index.md" in self.pages:
            n = sum(1 for _, l in self.pages["index.md"].text_lines() if l.startswith("- ["))
            self.check(n >= 3, "INDEX", "index.md", "fewer than 3 index entries; add <!-- index: term --> markers under headings and run sync")

    def home(self, p):
        heads = [M.plain(t).lower() for _, lvl, t in p.headings if lvl == 2]
        for need in ("who this guide is for", "how to use this guide", "contents", "what you need", "about this guide"):
            self.check(need in heads, "HOME_SECTIONS", "README.md", "missing the '%s' section" % need.capitalize())
        self.check("<!-- contents:start -->" in p.text, "HOME_SECTIONS", "README.md", "Contents has no <!-- contents:start --> marker for sync")
        finder = [t for t in p.tables() if [c.lower() for c in t[1][:2]] == ["if you want to", "go to"]]
        linked = sum(1 for r in finder[0][2] if re.search(r"\]\(\d{2}-[\w-]+\.md", " ".join(r))) if finder else 0
        self.check(linked >= min(3, len(self.chapters)), "TASK_FINDER", "README.md",
                   "the 'Where to find each task' table (If you want to | Go to) needs rows linking at least %d chapters" % min(3, len(self.chapters)))

    def sync_state(self):
        try:
            import docs_tool
            _order, _pages, stale, _s = docs_tool.plan(self.docs)
        except Exception as e:  # a broken page is reported by the page checks
            self.check(False, "SYNC_STALE", "docs", "sync could not run: %s" % e); return
        self.check(not stale, "SYNC_STALE", "docs", "numbering, contents, navigation or index is out of date in %s; run docs_tool.py sync" % ", ".join(stale))

    def answers(self):
        asked = {self.bare(self.h1(c)): (c, len(self.questions(self.pages[c]))) for c in self.chapters if self.questions(self.pages[c])}
        if not asked:
            return
        a = self.pages.get("appendix-a-answers.md")
        if not self.check(a is not None, "ANSWERS", "docs", "chapters ask questions but appendix-a-answers.md is missing"):
            return
        given = {}
        for i, t, s, e in a.sections(2):
            given[self.bare(t)] = sum(1 for k in range(s, e) if re.match(r"^\d+\.\s", a.lines[k]))
        for title, (c, n) in asked.items():
            self.check(given.get(title) == n, "ANSWERS", "appendix-a-answers.md",
                       "%s asks %d question(s); Appendix A has %s under a heading named '%s'" % (c, n, given.get(title, "none"), title))

    def glossary(self):
        g = self.pages.get("glossary.md")
        if not g:
            return
        terms = [M.plain(t) for _, lvl, t in g.headings if lvl == 2]
        self.check(terms == sorted(terms, key=str.lower), "GLOSSARY_ORDER", "glossary.md", "terms are not in A to Z order")
        self.terms = {t: M.slug(t) for t in terms}
        for n in self.chapters:
            p = self.pages[n]
            nav = p.text.find("<!-- nav:start -->")
            nav_line = p.text.count("\n", 0, nav) if nav >= 0 else len(p.lines)
            body = [(i, l) for i, l in p.text_lines() if not l.lstrip().startswith("#") and i < nav_line]
            def visible(l):  # what a reader reads as prose: no comments, no UI labels in bold, no links elsewhere
                l = re.sub(r"<!--.*?-->", "", l)
                l = re.sub(r"\*\*[^*]+\*\*", "", l)
                return re.sub(r"\[[^\]]*\]\([^)]*\)", lambda m: m.group(0) if "glossary.md" in m.group(0) else "", l)
            for term, anc in self.terms.items():
                rx = re.compile(r"(?i)\b%s\b" % re.escape(term))
                first = next((i for i, l in body if rx.search(visible(l))), None)
                if first is None:
                    continue
                linked = any("glossary.md#%s" % anc in l for i, l in body if i <= first)
                self.check(linked, "GLOSSARY_LINK", "%s:%d" % (n, first + 1), "first use of '%s' isn't linked to glossary.md#%s" % (term, anc), warn=True)

    # ---------------- per page
    def page(self, n, p):
        h1s = [h for h in p.headings if h[1] == 1]
        self.check(len(h1s) == 1, "H1_ONE", n, "a page has exactly one # heading (found %d)" % len(h1s))
        prev = 1
        for i, lvl, t in p.headings:
            self.check(lvl <= prev + 1, "HEADING_LEVEL", "%s:%d" % (n, i + 1), "heading level jumps from %d to %d" % (prev, lvl))
            prev = lvl
            words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", M.NUM_PREFIX.sub("", M.plain(t)))[1:] if len(w) > 3 and not w.isupper()]
            self.check(not (len(words) >= 3 and all(w[0].isupper() for w in words)), "HEADING_CASE", "%s:%d" % (n, i + 1),
                       "heading looks like Title Case; GitHub docs use sentence case: %r" % t, warn=True)
        for i, l in enumerate(p.lines):
            if PLACEHOLDER.search(l):
                self.check(False, "PLACEHOLDER", "%s:%d" % (n, i + 1), "unfinished text: %r" % l.strip()[:70])
        self.links(n, p)
        self.images(n, p)
        self.alerts(n, p)
        self.code(n, p)
        self.prose(n, p)
        self.tables(n, p)
        self.procedures(n, p)
        self.settings(n, p)
        self.check("<!-- nav:start -->" in p.text, "NAV", n, "no navigation footer markers; run docs_tool.py sync")

    def links(self, n, p):
        for i, text, target in p.links():
            parts = M.split_link(target)
            if parts is None:
                continue
            f, anc = parts
            dest_path = os.path.normpath(os.path.join(self.docs, f)) if f else p.path
            where = "%s:%d" % (n, i + 1)
            if f and not self.check(os.path.exists(dest_path), "LINK_BROKEN", where, "link to %s: file not found" % f):
                continue
            if anc and dest_path.endswith(".md"):
                dest = self.pages.get(os.path.basename(dest_path)) if os.path.dirname(dest_path) == os.path.normpath(self.docs) else None
                dest = dest or M.Page(dest_path)
                self.check(anc in dest.anchors, "LINK_BROKEN", where, "anchor #%s not found in %s" % (anc, os.path.basename(dest_path)))

    def images(self, n, p):
        for i, alt, src in p.images():
            where = "%s:%d" % (n, i + 1)
            if not re.match(r"^[a-z]+:", src):
                self.check(os.path.exists(os.path.normpath(os.path.join(self.docs, src))), "IMG_MISSING", where, "image %s not found" % src)
            logo = "logo" in alt.lower()
            self.check(logo or len(alt.split()) >= 4, "IMG_ALT", where, "alt text needs at least four words describing the image: %r" % alt)

    def alerts(self, n, p):
        per = {}
        for i, kind, body, clean in p.alerts():
            where = "%s:%d" % (n, i + 1)
            self.check(kind in M.KINDS, "ALERT_KIND", where, "[!%s] isn't a GitHub alert; use NOTE, TIP, IMPORTANT, WARNING or CAUTION" % kind)
            self.check(clean, "ALERT_SYNTAX", where, "put [!%s] alone on the first line of the quote" % kind)
            text = " ".join(body)
            boxed = text.startswith("**What you will learn**") or text.startswith("**Key takeaways**")
            if not boxed:
                h = p.section_of(i)
                per[h[0] if h else -1] = per.get(h[0] if h else -1, 0) + 1
            if kind in ("WARNING", "CAUTION") and NEGATIVE.search(text):
                self.check(ALTERNATIVE.search(re.sub(NEGATIVE, "", text)), "UNSAFE_ALTERNATIVE", where,
                           "names something unsafe without the safe alternative (say what to do instead)")
        for h, k in per.items():
            self.check(k <= 2, "ALERT_DENSITY", "%s:%d" % (n, h + 1), "%d alerts in one section; keep two at most" % k, warn=True)

    def code(self, n, p):
        for s, e, lang in p.fences:
            where = "%s:%d" % (n, s + 1)
            self.check(bool(lang), "CODE_LANG", where, "code block without a language tag (```bash, ```powershell, ```yaml, ...)")
            if lang.lower() in SHELL:
                k, before = s - 1, ""
                while k >= 0 and k >= s - 4:
                    if p.lines[k].strip() and k not in p.code:
                        before = p.lines[k]; break
                    k -= 1
                self.check(bool(WHERE.search(before)), "COMMAND_WHERE", where,
                           "say exactly where to run this command in the sentence before it (for example 'In PowerShell, paste:')")
            for k in range(s, e + 1):
                self.secret(n, k, p.lines[k])

    def secret(self, n, k, line):
        m = SECRET.search(line)
        if m and not re.search(r"<[^>]+>|x{6,}|\*{4,}|(?i:example|your[_-]|changeme|redacted|placeholder)", m.group(2)):
            self.check(False, "SECRET_LITERAL", "%s:%d" % (n, k + 1), "looks like a real %s; use a <placeholder>" % m.group(1))
        if TOKEN_SHAPES.search(line):
            self.check(False, "SECRET_LITERAL", "%s:%d" % (n, k + 1), "looks like a real access token; use a <placeholder>")

    def prose(self, n, p):
        para, start = [], None
        def flush():
            if para:
                text = " ".join(x.strip() for x in para)
                words = len(text.split())
                if not p.in_details(start) and not text.startswith(("|", "<")):
                    self.check(words <= 70, "BACKGROUND_LONG", "%s:%d" % (n, start + 1),
                               "%d-word paragraph; keep the step short and put background in <details> or a linked page" % words, warn=True)
        for i, l in enumerate(p.lines):
            s = l.strip()
            if i in p.code or not s or s.startswith(("#", "|", "<!--", "- ", "* ")) or re.match(r"^\d+\.\s", s) or s.startswith(">"):
                flush(); para, start = [], None
            else:
                if start is None:
                    start = i
                para.append(l)
            if i in p.code or s.startswith(("<!--", "|")) or not s:
                continue
            clean = re.sub(r"`[^`]*`", "", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s))
            if s.startswith(("#", "!", "<")):
                continue
            self.secret(n, i, s)
            m = PAD_FAIL.search(clean)
            if m:
                self.check(False, "VOICE_PADDING", "%s:%d" % (n, i + 1), "cut %r: state the fact or the action instead (references/voice.md)" % m.group(0))
            m = PAD_WARN.search(clean)
            if m:
                self.check(False, "VOICE_PADDING", "%s:%d" % (n, i + 1), "%r usually pads or minimizes; cut it or say it plainly" % m.group(0), warn=True)
            for sent in re.split(r"(?<=[.!?])\s+", re.sub(r"^\s*(>|[-*]|\d+\.)\s*", "", clean)):
                w = len(sent.split())
                if w > 25:
                    self.check(False, "SENTENCE_LONG", "%s:%d" % (n, i + 1), "%d-word sentence; split it (25 at most)" % w, warn=True)
            if re.match(r"(?i)^\*\*unsafe:\*\*", s):
                self.check(ALTERNATIVE.search(re.sub(NEGATIVE, "", s[10:])), "UNSAFE_ALTERNATIVE", "%s:%d" % (n, i + 1),
                           "an **Unsafe:** line must give the safe alternative")
        flush()

    def tables(self, n, p):
        for i, head, rows in p.tables():
            where = "%s:%d" % (n, i + 1)
            if head and M.plain(head[0]).lower() in CHOICE_HEAD:
                rec = [r for r in rows if "(recommended)" in " ".join(r).lower()]
                self.check(len(rec) == 1, "CHOICE_RECOMMENDED", where, "a choice table needs exactly one row marked (recommended); found %d" % len(rec))
            if [M.plain(h).lower() for h in head[:1]] == ["setting"] and any("recommend" in h.lower() for h in head):
                col = next(k for k, h in enumerate(head) if "recommend" in h.lower())
                for r in rows:
                    self.check(len(r) > col and r[col].strip() not in ("", "-", "—"), "SETTING_RECOMMENDED", where,
                               "setting %r has no recommended value" % (r[0] if r else "?"))
            if self.is_trouble_table(head):
                for r in rows:
                    self.check(len(r) >= 3 and all(c.strip() for c in r[:3]), "TROUBLESHOOTING", where, "every row needs a problem, a likely cause and a fix")

    def procedures(self, n, p):
        i = 0
        L = p.lines
        while i < len(L):
            if i in p.code or not re.match(r"^To [^:]{3,}:\s*$", L[i].strip()):
                i += 1; continue
            start, j = i, i + 1
            while j < len(L) and not L[j].strip():
                j += 1
            steps, results, k = [], 0, j
            while k < len(L):
                s = L[k]
                if re.match(r"^\d+\.\s", s):
                    steps.append((k, s)); k += 1; continue
                if s.startswith((" ", "\t")) or (not s.strip() and k + 1 < len(L) and (re.match(r"^\d+\.\s", L[k + 1]) or L[k + 1].startswith(" "))):
                    if "**Result:**" in s:
                        results += 1
                    k += 1; continue
                break
            where = "%s:%d" % (n, start + 1)
            self.check(2 <= len(steps) <= 12, "PROCEDURE_STEPS", where, "a procedure has 2 to 12 numbered steps (found %d)" % len(steps))
            self.check(results >= 1, "PROCEDURE_RESULT", where, "say what the reader sees: add an indented **Result:** line, at least after the last step")
            for ln, s in steps:
                body = re.sub(r"^\d+\.\s+", "", s).strip()
                first = re.sub(r"[*_`]", "", body.split(" ")[0]) if body else ""
                self.check(first.lower() not in ("the", "a", "an", "this", "it", "you", "your", "there", "now", "then", "next"), "PROCEDURE_VERB",
                           "%s:%d" % (n, ln + 1), "start the step with the action (a verb): %r" % body[:50], warn=True)
                self.check(len(body.split()) <= 40, "PROCEDURE_STEPS", "%s:%d" % (n, ln + 1), "step over 40 words; one action per step", warn=True)
            i = k

    def settings(self, n, p):
        for i, t, s, e in p.sections(2):
            if not re.search(r"(?i)\b(settings?|fields?|options?)\b", M.plain(t)):
                continue
            h3 = [h for h in p.headings if s < h[0] < e and h[1] == 3]
            for k, (hi, _lvl, ht) in enumerate(h3):
                end = h3[k + 1][0] if k + 1 < len(h3) else e
                block = "\n".join(p.lines[hi:end])
                self.check("**Recommended:**" in block, "SETTING_RECOMMENDED", "%s:%d" % (n, hi + 1),
                           "setting '%s' needs a **Recommended:** line with the safe value" % M.plain(ht))

    # ---------------- chapters
    def chapter(self, n, p):
        h1 = self.h1(n)
        num = int(n[:2])
        self.check(re.match(r"^Chapter %d: \S" % num, h1 or ""), "NUMBERING", n, "the # heading must be 'Chapter %d: <title>'; run docs_tool.py sync" % num)
        for k, (i, t, s, e) in enumerate(p.sections(2), 1):
            self.check(t.startswith("%d.%d " % (num, k)), "NUMBERING", "%s:%d" % (n, i + 1), "expected '%d.%d ' before %r; run docs_tool.py sync" % (num, k, t))
        if re.search(r"(?i)troubleshoot", h1 or ""):
            return
        al = p.alerts()
        first_h2 = next((h[0] for h in p.headings if h[1] == 2), len(p.lines))
        obj = [a for a in al if "\n".join(a[2]).startswith("**What you will learn**")]
        if self.check(bool(obj) and obj[0][0] < first_h2 and obj[0][1] == "NOTE", "OBJECTIVES", n,
                      "add a [!NOTE] **What you will learn** box before the first section"):
            items = [re.sub(r"^[-*]\s+", "", b).strip() for b in obj[0][2] if re.match(r"^[-*]\s", b)]
            self.check(2 <= len(items) <= 6, "OBJECTIVES", "%s:%d" % (n, obj[0][0] + 1), "2 to 6 objectives (found %d)" % len(items))
            for it in items:
                self.check(not BAD_OBJECTIVE.search(it), "OBJECTIVE_VERB", "%s:%d" % (n, obj[0][0] + 1),
                           "objectives start with an observable verb, not %r" % it.split()[0])
        tk = [a for a in al if "\n".join(a[2]).startswith("**Key takeaways**")]
        last_h2 = max((h[0] for h in p.headings if h[1] == 2), default=0)
        if self.check(bool(tk) and tk[-1][0] > last_h2 and tk[-1][1] == "TIP", "TAKEAWAYS", n,
                      "end the chapter with a [!TIP] **Key takeaways** box after the last section"):
            items = [b for b in tk[-1][2] if re.match(r"^[-*]\s", b)]
            self.check(2 <= len(items) <= 6, "TAKEAWAYS", "%s:%d" % (n, tk[-1][0] + 1), "2 to 6 takeaways (found %d)" % len(items))

    # ---------------- helpers
    def h1(self, n):
        p = self.pages.get(n)
        h = next((h for h in p.headings if h[1] == 1), None) if p else None
        return M.plain(h[2]) if h else ""

    @staticmethod
    def bare(t):
        return M.NUM_PREFIX.sub("", M.plain(t)).strip().lower()

    @staticmethod
    def is_trouble_table(head):
        return [M.plain(h).lower() for h in head[:3]] == ["problem", "likely cause", "fix"]

    @staticmethod
    def questions(p):
        for i, t, s, e in p.sections(2):
            if re.search(r"(?i)check your understanding", t):
                return [p.lines[k] for k in range(s, e) if re.match(r"^\d+\.\s", p.lines[k])]
        return []

    def report(self, strict=False):
        print("LINT: %d checks, %d failed, %d warnings" % (self.checks, len(self.fails), len(self.warns)))
        for l in self.fails + self.warns:
            print(l)
        return 1 if self.fails or (strict and self.warns) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("docs"); ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    L = Lint(os.path.abspath(a.docs))
    L.run()
    return L.report(a.strict)


if __name__ == "__main__":
    sys.exit(main())
