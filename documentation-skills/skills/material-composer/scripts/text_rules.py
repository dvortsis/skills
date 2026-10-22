#!/usr/bin/env python3
"""Text rules for every deliverable (v4.23.0): short descriptive titles, Proper Case, common formatting.

proper() is the one Proper Case rule: slide-deck and material-composer import it from their own copies of this file,
so decks, review pages and documents follow one rule (AP style).
  python3 text_rules.py "some title"      -> prints the Proper Case form
"""
import re, sys

SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "if", "as", "at", "by", "in", "of", "off", "on", "per", "to", "up", "via", "vs", "vs."}
# One hyphen rule for every deliverable: the word after a hyphen stays lowercase ("Sign-off", "Drop-off") unless it is
# an acronym, mixed case ("Non-SaaS") or a proper noun from this list. add_proper_nouns() adds the project's own names.
PROPER_AFTER_HYPHEN = {w.lower(): w for w in (
    "Tableau", "Confluence", "Excel", "PowerPoint", "Word", "Atlantic", "American",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April",
    "May", "June", "July", "August", "September", "October", "November", "December",
    "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec", "Do", "Study", "Act")}


def add_proper_nouns(words):
    """Keep project names capitalized after a hyphen (the brand and product names from the brand profile)."""
    for w in words or ():
        if w and w[0].isupper() and w.isalpha() and len(w) > 2:
            PROPER_AFTER_HYPHEN[w.lower()] = w


def after_hyphen(w):
    if not w or w[0].isdigit() or not any(c.isalpha() for c in w) or any(c.isupper() for c in w[1:]):
        return w
    return PROPER_AFTER_HYPHEN.get(w.lower(), w.lower())


FILLER = re.compile(r"(?i)^(chart|graph|dashboard|visual|view|table) of\b|\b(overview of|breakdown of)\b")


def proper(text):
    """Proper Case for headings (AP style): capitalize principal words and
    words of 4+ letters; lowercase articles, conjunctions and prepositions of 3 letters or fewer unless first, last
    or after a colon or dash. Acronyms, mixed-case words and tokens starting with a digit are left alone. Idempotent."""
    parts = re.split(r"(\s+)", text or "")
    idx = [i for i, p in enumerate(parts) if p.strip()]
    out, start = list(parts), True
    for n, i in enumerate(idx):
        tok = parts[i]
        m = re.match(r"^([^\w$]*)(.*?)([^\w%]*)$", tok)
        lead, core, trail = m.group(1), m.group(2), m.group(3)
        last = n == len(idx) - 1
        def cap(w, edge):
            if not w or w[0].isdigit() or w[0] == "$" or any(c.isupper() for c in w[1:]) or not any(c.isalpha() for c in w):
                return w
            if w.lower() in SMALL and not edge:
                return w.lower()
            return w[0].upper() + w[1:]
        if "-" in core:
            segs = core.split("-")
            core = "-".join(cap(sg, True) if k == 0 else after_hyphen(sg) for k, sg in enumerate(segs))
        else:
            core = cap(core, start or last)
        out[i] = lead + core + trail
        start = bool(re.search(r"[:\u2014\u2013?!]$", tok)) or tok in ("\u2014", "\u2013", "-")
    return "".join(out)


def title_problems(text, max_words=6, max_chars=48, question_ok=False):
    """Problems with one title or subtitle; empty list = OK."""
    t = text or ""
    p = []
    if t != t.strip() or "  " in t:
        p.append("extra spaces")
    if not question_ok and t.strip().endswith("?"):
        p.append("a question (use a short descriptive title)")
    if re.search(r"[.;:,]$", t.strip()):
        p.append("ends with punctuation")
    pt = re.sub(r"\bV(\d)", r"v\1", proper(t))
    if t != pt and re.sub(r"\bv(\d)", r"V\1", t) != proper(t):
        p.append("not Proper Case (%r)" % pt)
    n = len(re.findall(r"[^\s\u00b7\u00d7|/+\u2013\u2014-]+", t.replace(" & ", " ")))
    if n > max_words or len(t) > max_chars:
        p.append("too long (%d words, %d characters; max %d / %d)" % (n, len(t), max_words, max_chars))
    if FILLER.search(t):
        p.append("filler words (say what it shows)")
    return p


if __name__ == "__main__":
    print(proper(" ".join(sys.argv[1:])))
