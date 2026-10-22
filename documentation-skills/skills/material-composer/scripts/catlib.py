"""Format catalog: base (references/format-catalog.json) + developer overlay (assets/catalog/overlay.json or
$MATERIAL_OVERLAY). Resolves any requested format name to a catalog entry, or derives one from the nearest entry."""
import copy, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BASE = os.path.join(SKILL, "references", "format-catalog.json")
OVERLAY = os.path.join(SKILL, "assets", "catalog", "overlay.json")
RULES = os.path.join(SKILL, "references", "material_rules.json")
PROFILES = os.path.join(SKILL, "references", "audience_profiles.json")
DOC_THEME = os.path.join(os.path.dirname(SKILL), "document-builder", "assets", "doc_theme.json")
STOP = {"a", "an", "the", "for", "of", "to", "and", "on", "in", "with", "my", "our", "new", "one", "please", "make", "create"}


def rules():
    return json.load(open(RULES, encoding="utf-8"))


def builder_doc_types():
    """Doc types the document builder accepts, read at run time ($MATERIAL_DOC_THEME overrides); None if not installed."""
    try:
        return set(json.load(open(os.environ.get("MATERIAL_DOC_THEME") or DOC_THEME, encoding="utf-8")).get("doc_types", {}))
    except (OSError, ValueError):
        return None


def profile(name=None):
    """-> (id, profile dict) for an audience profile name or alias (default when empty), or (None, names) when unknown."""
    data = json.load(open(PROFILES, encoding="utf-8"))
    k = key(name or data["default"])
    for pid, p in data["profiles"].items():
        if k == key(pid) or k in [key(x) for x in p.get("aliases", [])]:
            return pid, p
    return None, sorted(data["profiles"])


def overlay_path(p=None):
    return p or os.environ.get("MATERIAL_OVERLAY") or OVERLAY


def load_overlay(p=None):
    p = overlay_path(p)
    if os.path.isfile(p):
        return json.load(open(p, encoding="utf-8"))
    return {"format": "catalog-overlay", "families": {}, "formats": {}, "retired": {}, "renamed": {}, "log": []}


def merge(base, ov):
    cat = copy.deepcopy(base)
    for k, v in ov.get("families", {}).items():
        cat["families"].setdefault(k, {}).update(v)
    for k, v in ov.get("formats", {}).items():
        if k in cat["formats"] and not v.get("_replace"):
            cat["formats"][k].update(v)
        else:
            cat["formats"][k] = {x: y for x, y in v.items() if x != "_replace"}
    for k in ov.get("retired", {}):
        cat["formats"].pop(k, None)
    cat["retired"] = ov.get("retired", {})
    cat["renamed"] = ov.get("renamed", {})
    return cat


def load(overlay=None):
    return merge(json.load(open(BASE, encoding="utf-8")), load_overlay(overlay))


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", str(s).lower().replace("-", " ")).split()


def key(s):
    return " ".join(norm(s))


def tokens(s):
    return {t.rstrip("s") for t in norm(s) if t not in STOP}


def lookup(cat, name):
    """Exact id, label or alias (after normalizing). Returns (id, how) or (None, None)."""
    k = key(name)
    for fid, f in cat["formats"].items():
        if k == key(fid) or k == key(f.get("label", "")):
            return fid, "exact"
    for fid, f in cat["formats"].items():
        if any(k == key(a) for a in f.get("aliases", [])):
            return fid, "alias"
    for old, info in cat.get("retired", {}).items():
        if k == key(old) and info.get("replaced_by") in cat["formats"]:
            return info["replaced_by"], "retired->" + old
    return None, None


def family_scores(cat, name):
    t = tokens(name); low = " " + key(name) + " "
    out = {}
    for fam, f in cat["families"].items():
        s = 0.0
        for kw in f.get("keywords", []):
            kt = tokens(kw)
            if kt and kt <= t:
                s += 2.0 if " " + key(kw) + " " in low else 1.5
        out[fam] = s
    return out


def resolve(cat, name, family=None):
    """-> dict(id, entry, how, derived_from, score) or None when name is empty."""
    if not str(name or "").strip():
        return None
    fid, how = lookup(cat, name)
    if fid:
        return {"id": fid, "entry": copy.deepcopy(cat["formats"][fid]), "how": how, "derived_from": None, "score": 1.0, "match": how.split("->")[0]}
    t = tokens(name)
    fs = family_scores(cat, name)
    fam = family or max(fs, key=lambda k: (fs[k], k == "reference-sheet"))
    if not family and fs[fam] == 0:
        fam = "reference-sheet"
    best, bscore = None, -1.0
    for cid, f in cat["formats"].items():
        if f["family"] != fam:
            continue
        lab = tokens(f.get("label", "")) | tokens(cid)
        ali = {w for a in f.get("aliases", []) for w in tokens(a)} - lab
        s = len(t & lab) + 0.6 * len(t & ali)
        if s > bscore:
            best, bscore = cid, s
    if best is None:
        return {"id": None, "entry": None, "how": "unresolved", "derived_from": None, "score": 0, "match": "none"}
    m = rules().get("match", {}); level = "derived high"
    if bscore < m.get("low_below", 1.0):
        dflt = m.get("family_default", {}).get(fam)
        if (family or fs.get(fam)) and dflt in cat["formats"] and cat["formats"][dflt]["family"] == fam:
            best, level = dflt, "derived family"
        else:
            level = "low"
    e = copy.deepcopy(cat["formats"][best])
    name = re.split(r"\s+(?:for|about|on|to)\s+", str(name).strip(), maxsplit=1, flags=re.I)[0] or name
    kid = re.sub(r"[^a-z0-9]+", "-", key(name)).strip("-")
    if e.get("doc_type"):
        if renderer_of(cat, e)[0] != "doc-long":
            e["doc_type"] = kid
        elif kid in (builder_doc_types() or ()):
            e["doc_type"] = kid
    e["label"] = " ".join(w if (w.isupper() and len(w) > 1) else (w.capitalize() if w.lower() not in STOP else w.lower()) for w in str(name).strip().split())
    e["aliases"] = []
    if level == "low":
        e["anatomy"] = copy.deepcopy(m.get("neutral_anatomy", []))
        for k in ("exemplar", "limits"):
            e.pop(k, None)
        return {"id": kid, "entry": e, "how": "unresolved-low", "derived_from": None, "nearest": best, "score": round(bscore, 2), "match": "low"}
    return {"id": kid, "entry": e, "how": "derived", "derived_from": best, "score": round(bscore, 2), "match": level}


SCHEMA_KEYS = {"family", "label", "aliases", "anatomy"}


def validate(cat):
    errs = []
    fams = set(cat["families"]); rends = set(cat["renderers"])
    for k, f in cat["families"].items():
        if f.get("renderer") not in rends:
            errs.append("family %s: unknown renderer %s" % (k, f.get("renderer")))
    seen = {}
    for fid, f in cat["formats"].items():
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", fid):
            errs.append("%s: id must be kebab-case" % fid)
        miss = SCHEMA_KEYS - set(f)
        if miss:
            errs.append("%s: missing %s" % (fid, ", ".join(sorted(miss))))
        if f.get("family") not in fams:
            errs.append("%s: unknown family %s" % (fid, f.get("family")))
        if f.get("renderer") and f["renderer"] not in rends:
            errs.append("%s: unknown renderer %s" % (fid, f["renderer"]))
        titles = [s.get("title") for s in f.get("anatomy", [])]
        if len(titles) != len(set(titles)):
            errs.append("%s: duplicate section titles" % fid)
        for s in f.get("anatomy", []):
            for lk, lv in (s.get("limits") or {}).items():
                if not (isinstance(lv, list) and len(lv) == 2 and lv[0] <= lv[1]):
                    errs.append("%s/%s: limit %s must be [min, max]" % (fid, s.get("title"), lk))
        for n in [f.get("label", "")] + f.get("aliases", []):
            k = key(n)
            if k in seen and seen[k] != fid:
                errs.append("name '%s' used by %s and %s" % (n, seen[k], fid))
            seen[k] = fid
        if f.get("pair") and f["pair"] not in cat["formats"]:
            errs.append("%s: pair %s not in catalog" % (fid, f["pair"]))
    return errs


def renderer_of(cat, entry):
    r = entry.get("renderer") or cat["families"][entry["family"]]["renderer"]
    return r, cat["renderers"][r]
