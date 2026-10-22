"""Markdown helpers shared by docs_tool.py and lint_docs.py: GitHub anchors, headings, links, alerts, tables, lists,
code blocks and <details> regions, all with line numbers and with fenced code ignored."""
import os, re

FENCE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})\s*([\w+#.-]*)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG = re.compile(r"<img\b[^>]*>", re.I)
ALERT = re.compile(r"^\s*>\s*\[!(\w+)\]\s*$")
ALERT_ANY = re.compile(r"^\s*>\s*\[!(\w*)\]")
KINDS = ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION")
NUM_PREFIX = re.compile(r"^(?:Chapter\s+\d+:\s*|Appendix\s+[A-Z]:\s*|\d+(?:\.\d+)*\.?\s+)")


def read_file(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write_file(path, text):
    """UTF-8 with LF line endings, so pages look the same in every editor and diff."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def plain(text):
    """Heading text as GitHub renders it: links to their text, code and emphasis markers removed, HTML tags dropped."""
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"(\*\*|__|\*|_|`|~~)", "", t)
    return t.strip()


def slug(text):
    """GitHub's heading anchor: lowercase, keep letters, digits, spaces, hyphens and underscores, spaces to hyphens."""
    t = plain(text).lower()
    t = re.sub(r"[^\w\- ]", "", t, flags=re.UNICODE)
    return t.replace(" ", "-")


class Page:
    def __init__(self, path, text=None):
        self.path = path
        self.name = os.path.basename(path)
        self.text = text if text is not None else read_file(path)
        self.lines = self.text.split("\n")
        self._scan()

    def _scan(self):
        self.code = set()          # line indexes inside fenced code (fence lines included)
        self.fences = []           # (start, end, lang)
        self.headings = []         # (line, level, text)
        open_f = None
        for i, line in enumerate(self.lines):
            m = FENCE.match(line)
            if open_f is not None:
                self.code.add(i)
                if m and m.group(2)[0] == open_f[1][0] and len(m.group(2)) >= len(open_f[1]) and not m.group(3):
                    self.fences.append((open_f[0], i, open_f[2])); open_f = None
                continue
            if m:
                open_f = (i, m.group(2), m.group(3)); self.code.add(i); continue
            h = HEADING.match(line)
            if h:
                self.headings.append((i, len(h.group(1)), h.group(2)))
        if open_f is not None:
            self.fences.append((open_f[0], len(self.lines) - 1, open_f[2]))
        self.anchors = {}
        seen = {}
        for i, lvl, t in self.headings:
            s = slug(t)
            if s in seen:
                seen[s] += 1; s = "%s-%d" % (s, seen[s])
            else:
                seen[s] = 0
            self.anchors[s] = i
        for i, line in enumerate(self.lines):  # explicit anchors: <a id="x"></a> / <a name="x">
            for m in re.finditer(r"<a\s+(?:id|name)=\"([^\"]+)\"", line):
                self.anchors.setdefault(m.group(1), i)
        self.details = []          # (start, end) line ranges of <details> blocks
        stack = []
        for i, line in enumerate(self.lines):
            if i in self.code:
                continue
            if re.search(r"<details\b", line, re.I):
                stack.append(i)
            if re.search(r"</details>", line, re.I) and stack:
                self.details.append((stack.pop(), i))

    def in_details(self, i):
        return any(a <= i <= b for a, b in self.details)

    def text_lines(self):
        """(index, line) for lines outside fenced code."""
        return [(i, l) for i, l in enumerate(self.lines) if i not in self.code]

    def links(self):
        out = []
        for i, l in self.text_lines():
            for m in LINK.finditer(re.sub(r"`[^`]*`", "", l)):
                out.append((i, m.group(1), m.group(2)))
        return out

    def images(self):
        out = []
        for i, l in self.text_lines():
            for m in IMAGE.finditer(l):
                out.append((i, m.group(1), m.group(2)))
            for m in HTML_IMG.finditer(l):
                src = re.search(r"src=\"([^\"]+)\"", m.group(0)); alt = re.search(r"alt=\"([^\"]*)\"", m.group(0))
                out.append((i, alt.group(1) if alt else "", src.group(1) if src else ""))
        return out

    def alerts(self):
        """(line, kind, body lines) for each blockquote that starts with [!KIND]."""
        out, i = [], 0
        while i < len(self.lines):
            if i not in self.code:
                m = ALERT_ANY.match(self.lines[i])
                if m:
                    body, j = [], i + 1
                    while j < len(self.lines) and self.lines[j].lstrip().startswith(">"):
                        body.append(re.sub(r"^\s*>\s?", "", self.lines[j])); j += 1
                    out.append((i, m.group(1), body, bool(ALERT.match(self.lines[i]))))
                    i = j; continue
            i += 1
        return out

    def tables(self):
        """(line, header cells, rows) for pipe tables outside code."""
        out, i = [], 0
        while i < len(self.lines) - 1:
            if i not in self.code and self.lines[i].strip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", self.lines[i + 1]):
                head = cells(self.lines[i]); rows, j = [], i + 2
                while j < len(self.lines) and self.lines[j].strip().startswith("|"):
                    rows.append(cells(self.lines[j])); j += 1
                out.append((i, head, rows)); i = j; continue
            i += 1
        return out

    def section_of(self, i):
        """The nearest heading at or above line i: (line, level, text) or None."""
        prev = None
        for h in self.headings:
            if h[0] <= i:
                prev = h
            else:
                break
        return prev

    def sections(self, level=2):
        """[(heading line, text, start, end)] for headings of this level; end is exclusive."""
        hs = [h for h in self.headings if h[1] <= level]
        out = []
        for k, (i, lvl, t) in enumerate(hs):
            if lvl != level:
                continue
            end = next((h[0] for h in hs[k + 1:] if h[1] <= level), len(self.lines))
            out.append((i, t, i, end))
        return out


def cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def split_link(target):
    """('file.md', 'anchor') from a link target; file '' means this page."""
    if re.match(r"^[a-z][\w+.-]*:", target):
        return None
    f, _, a = target.partition("#")
    return f, a


def guide_pages(docs):
    """Ordered guide pages: README, chapters, appendices, glossary, revisions, index (those that exist)."""
    names = sorted(os.listdir(docs))
    chapters = [n for n in names if re.fullmatch(r"\d{2}-[\w-]+\.md", n)]
    appx = sorted(n for n in names if re.fullmatch(r"appendix-[a-z]-[\w-]+\.md", n))
    tail = [n for n in ("glossary.md", "revisions.md", "index.md") if n in names]
    head = ["README.md"] if "README.md" in names else []
    return head + chapters + appx + tail, chapters, appx
