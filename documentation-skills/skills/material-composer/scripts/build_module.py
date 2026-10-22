#!/usr/bin/env python3
"""E-learning (request row D-14; SCORM 1.2 package D-28): module.json -> one self-contained HTML module + storyboard .md, behind one gate.

  python3 build_module.py module.json --check                       run the gate (includes a trial render for ELEARN_OFFLINE)
  python3 build_module.py module.json --out Name [--draft] [--embed-font]
        writes Name.html (inline CSS/JS, images as data URIs, no network) and Name.storyboard.md; refuses on FAIL unless --draft.
        The brand fonts the project ships (or the bundled fallback) are copied to fonts/ next to the HTML and loaded with
        @font-face; --embed-font inlines them instead (one self-contained file). Installed system fonts are never copied.
  python3 build_module.py module.json --out Name --scorm
        also writes Name_SCORM12.zip (imsmanifest.xml + index.html at the root, plus fonts/ when the brand has font files) and gates it (SCORM_PACKAGE);
        the package resumes on the learner's last screen with their answers (D-52). Pilot every package in your LMS's test area first.
  --brand brand.json   use this brand profile; otherwise the brand comes from the module's project (scripts/brand.py)

Codes: ELEARN_INTERACTION, ELEARN_OBJECTIVE, ELEARN_OFFLINE, ELEARN_STRUCTURE, PLACEHOLDER, SCORM_PACKAGE, SOURCES_MISSING, TITLE_CASE.
Data lists live in references/elearning_rules.json. Schema and limits: references/forms-and-elearning.md.
"""
import argparse, base64, hashlib, html, json, os, re, shutil, sys, zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from text_rules import proper  # shared copy, read-only
import brand as BR  # shared copy, read-only
import style_tokens as ST

TOKENS = ST.shipped()  # sizes; colors, fonts, logo and footer come from the project brand (set_brand)
RULES = json.load(open(os.path.join(SKILL, "references", "elearning_rules.json"), encoding="utf-8"))
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CUR = {}


def set_brand(source=None, brand=None, project=None):
    """Resolve the project brand for this build (explicit profile > profile beside the source > detected > neutral)."""
    _CUR["t"] = ST.tokens(source, brand, project)
    return _CUR["t"]


def cur():
    return _CUR.get("t") or set_brand()


class Gate:
    def __init__(self, name):
        self.name, self.n, self.msgs = name, 0, []

    def check(self, bad, level, code, msg):
        self.n += 1
        if bad:
            self.msgs.append((level, code, msg))
        return not bad

    @property
    def failed(self):
        return sum(1 for m in self.msgs if m[0] == "FAIL")

    def codes(self, level="FAIL"):
        return [c for lv, c, _ in self.msgs if lv == level]

    def report(self, out=print):
        for lv, code, msg in self.msgs:
            out("%s [%s] %s" % (lv, code, msg))
        out("%s GATE: %d checks, %d failed" % (self.name, self.n, self.failed))


def term_rx(terms):
    parts = []
    for t in sorted(terms, key=len, reverse=True):
        e = re.escape(t).replace("\\ ", r"\s+")
        parts.append(r"\b%s\b" % e if re.match(r"^\w.*\w$|^\w$", t) else e)
    return re.compile("(?i)(" + "|".join(parts) + ")")


PLACEHOLDER_RX = term_rx(RULES["placeholders"])
OFFLINE_RX = re.compile(r"""(?i)(?:\b(?:src|href|action|poster|srcset|data)\s*=\s*["']?\s*(?:https?:)?//)|(?:url\(\s*["']?\s*(?:https?:)?//)|(?:@import\s+["'](?:https?:)?//)""")
URL_TEXT_RX = re.compile(r"(?i)https?://")


def options_of(s):
    """(kind, block, options) for an interactive screen, else (None, None, [])."""
    q = s.get("question") or None
    if q and q.get("options"):
        return "question", q, q["options"]
    if s.get("choices"):
        return "choices", None, s["choices"]
    return None, None, []


def screens_of(mod):
    """Screens as delivered: a summary screen is added when the module has none."""
    sc = [dict(s) for s in mod.get("screens") or []]
    if sc and not any(s.get("type") == "summary" for s in sc):
        sc.append({"id": "SUMMARY", "type": "summary", "title": "Summary", "body": "Here is what you can do now.", "_added": True})
    return sc


def module_texts(mod):
    m = mod.get("meta") or {}
    out = [("title", m.get("title")), ("audience", m.get("audience"))]
    out += [("objective", o) for o in m.get("objectives") or []] + [("source", s) for s in m.get("sources") or []]
    for s in mod.get("screens") or []:
        sid = s.get("id") or "?"
        out += [(sid, s.get("title")), (sid, s.get("body")), (sid + " alt", s.get("alt"))] + [(sid, b) for b in s.get("bullets") or []]
        q = s.get("question") or {}
        out.append((sid + " stem", q.get("stem")))
        for o in (q.get("options") or []) + (s.get("choices") or []):
            out += [(sid + " option", o.get("text")), (sid + " feedback", o.get("feedback"))]
    return [(w, str(t)) for w, t in out if t]


def objective_verb(obj):
    t = re.sub(r"\s+", " ", str(obj).strip().lower())
    for p in sorted(RULES["objective_prefixes"], key=len, reverse=True):
        if t.startswith(p + " "):
            t = t[len(p) + 1:]
            break
    for bad in sorted(RULES["non_observable_verbs"], key=len, reverse=True):
        if re.match(r"%s\b" % re.escape(bad), t):
            return bad, False
    first = (re.findall(r"[a-z]+", t) or [""])[0]
    return first, first in RULES["observable_verbs"]


def gate(mod, base_dir="."):
    g = Gate("MODULE")
    m = mod.get("meta") or {}
    title = (m.get("title") or "").strip()
    g.check(not title, "FAIL", "ELEARN_STRUCTURE", "meta.title is empty")
    if title:
        g.check(proper(m["title"]) != m["title"], "FAIL", "TITLE_CASE", "title is not Proper Case; use \"%s\"" % proper(m["title"]))
    g.check(not [s for s in m.get("sources") or [] if str(s).strip()], "FAIL", "SOURCES_MISSING", "meta.sources is empty; list the sources behind the content")
    g.check(not m.get("duration_min"), "WARN", "ELEARN_STRUCTURE", "meta.duration_min is missing")
    objs = [o for o in m.get("objectives") or [] if str(o).strip()]
    g.check(not objs, "FAIL", "ELEARN_OBJECTIVE", "meta.objectives is empty; list 1-5 things the learner can do after the module")
    for k, o in enumerate(objs, 1):
        verb, ok = objective_verb(o)
        banned = verb in RULES["non_observable_verbs"]
        g.check(banned, "FAIL", "ELEARN_OBJECTIVE", "objective %d starts with \"%s\"; start with an observable verb (identify, complete, explain...)" % (k, verb))
        if not banned:
            g.check(not ok, "WARN", "ELEARN_OBJECTIVE", "objective %d starts with \"%s\", not in the observable verb list; check a learner can show it" % (k, verb))
    for where, text in module_texts(mod):
        hit = PLACEHOLDER_RX.search(text)
        g.check(bool(hit), "FAIL", "PLACEHOLDER", "%s: placeholder text '%s'" % (where, hit.group(0) if hit else ""))
        if where.split(" ")[0] not in ("source",):
            g.check(bool(URL_TEXT_RX.search(text)) and "](" not in text, "WARN", "ELEARN_OFFLINE", "%s: URL in screen text; learners may be offline, name the page instead" % where)

    raw = mod.get("screens") or []
    g.check(not raw, "FAIL", "ELEARN_STRUCTURE", "module has no screens")
    if raw and not any(s.get("type") == "summary" for s in raw):
        g.check(True, "WARN", "ELEARN_STRUCTURE", "no summary screen; a Summary screen listing the objectives was added")
    seen = set()
    for s in raw:
        sid = str(s.get("id") or "")
        g.check(not sid, "FAIL", "ELEARN_STRUCTURE", "a screen has no id")
        g.check(bool(sid) and sid in seen, "FAIL", "ELEARN_STRUCTURE", "duplicate screen id %s" % sid)
        seen.add(sid)
        g.check(s.get("type") not in RULES["screen_types"], "FAIL", "ELEARN_STRUCTURE", "%s: unknown type %r (use %s)" % (sid, s.get("type"), ", ".join(RULES["screen_types"])))
        g.check(not (s.get("title") or "").strip(), "FAIL", "ELEARN_STRUCTURE", "%s: screen has no title" % sid)
        if (s.get("title") or "").strip():
            g.check(proper(s["title"]) != s["title"], "WARN", "TITLE_CASE", "%s: title \"%s\" is not Proper Case; use \"%s\"" % (sid, s["title"], proper(s["title"])))
        if s.get("image"):
            img = str(s["image"])
            g.check(not (s.get("alt") or "").strip() and not s.get("decorative"), "FAIL", "ELEARN_STRUCTURE", "%s: image needs alt text (or \"decorative\": true)" % sid)
            if not re.match(r"(?i)^(https?:)?//|^data:", img):
                g.check(not os.path.isfile(os.path.join(base_dir, img)), "FAIL", "ELEARN_STRUCTURE", "%s: image file not found: %s" % (sid, img))
        kind, q, opts = options_of(s)
        if s.get("type") in ("question", "practice"):
            g.check(kind is None, "FAIL", "ELEARN_INTERACTION", "%s: %s screen has no question with options" % (sid, s.get("type")))
        if s.get("question") is not None and not (s.get("question") or {}).get("options"):
            g.check(True, "FAIL", "ELEARN_INTERACTION", "%s: question has no options" % sid)
        if kind:
            g.check(len(opts) < 2, "FAIL", "ELEARN_INTERACTION", "%s: needs at least 2 options (has %d)" % (sid, len(opts)))
            if kind == "question":
                g.check(not (q.get("stem") or "").strip(), "FAIL", "ELEARN_INTERACTION", "%s: question has no stem" % sid)
            nofb = [LETTERS[i] for i, o in enumerate(opts) if not str(o.get("feedback") or "").strip()]
            g.check(bool(nofb), "FAIL", "ELEARN_INTERACTION", "%s: %s %s %s no feedback" % (
                sid, "options" if len(nofb) > 1 else "option", ", ".join(nofb), "have" if len(nofb) > 1 else "has"))
            notext = [LETTERS[i] for i, o in enumerate(opts) if not str(o.get("text") or "").strip()]
            g.check(bool(notext), "FAIL", "ELEARN_INTERACTION", "%s: option %s has no text" % (sid, ", ".join(notext)))
            if kind == "question":
                ncor = sum(1 for o in opts if o.get("correct"))
                g.check(ncor == 0, "FAIL", "ELEARN_INTERACTION", "%s: question has no correct option" % sid)
                g.check(ncor > 1 and not q.get("multi"), "FAIL", "ELEARN_INTERACTION", "%s: %d options are correct but multi is false" % (sid, ncor))
    mx = RULES["max_screens_without_interaction"]
    run = []
    for s in screens_of(mod) + [{"_end": True}]:
        if not s.get("_end") and options_of(s)[0] is None:
            run.append(str(s.get("id")))
            continue
        if len(run) > mx:
            g.check(True, "FAIL", "ELEARN_INTERACTION", "screens %s-%s have no interaction (maximum %d in a row)" % (run[0], run[-1], mx))
        else:
            g.check(False, "FAIL", "ELEARN_INTERACTION", "")
        run = []
    return g


def offline_check(doc, g):
    hits = sorted(set(m.group(0).strip() for m in OFFLINE_RX.finditer(doc)))
    g.check(bool(hits), "FAIL", "ELEARN_OFFLINE", "built HTML loads external URLs (%s); inline the file or remove the link" % ", ".join(hits[:3]))
    return g


# ---------------------------------------------------------------- HTML
def esc(s):
    return html.escape(str(s or ""), quote=True)


def inline(text):
    """Escaped text with **bold** and [label](target) only."""
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t


def paras(text):
    return "".join("<p>%s</p>" % inline(p.strip()).replace("\n", "<br>") for p in re.split(r"\n\s*\n", str(text or "")) if p.strip())


def data_uri(path, base_dir):
    if re.match(r"(?i)^(https?:)?//|^data:", path):
        return path
    p = os.path.join(base_dir, path)
    if not os.path.isfile(p):
        return ""
    if path.lower().endswith(".b64"):   # packaged images ship as base64 text (CONVENTIONS: Binaries)
        ext = path[:-4].rsplit(".", 1)[-1].lower()
        data = re.sub(r"\s+", "", open(p, encoding="ascii").read())
    else:
        ext = path.rsplit(".", 1)[-1].lower()
        data = base64.b64encode(open(p, "rb").read()).decode()
    return "data:%s;base64,%s" % (RULES["image_types"].get(ext, "application/octet-stream"), data)


def logo_uri(width=360):
    """The project logo as a PNG data URI for the white chip in the title bar, or None (no logo: no chip)."""
    raw = cur()["brand"].logo_png("light", width)
    return "data:image/png;base64," + base64.b64encode(raw).decode() if raw else None


def css_family(name):
    return '"%s"' % str(name).replace('"', "").replace("\\", "")


def font_assets():
    """[(family, weight, path)] for the brand's body (regular, bold) and heading (bold) font files that may travel with
    the module: files the project ships and the bundled fallback (SIL OFL). Installed system fonts are not copied (their
    licenses rarely allow it); the CSS still names them, so a learner who has them installed sees them."""
    b = cur()["brand"]
    shareable = [d for d in b.font_dirs()] + [x for x in (BR.bundled_dir(),) if x]
    out = []
    for role, weight in (("body", 400), ("body", 700), ("heading", 700)):
        fam = b.fonts.get(role) or b.fonts["body"]
        path = b.font_path(role, bold=weight == 700)
        if path and any(os.path.abspath(path).startswith(os.path.abspath(d)) for d in shareable) \
                and (fam, weight) not in [(f, w) for f, w, _ in out]:
            out.append((fam, weight, path))
    return out


def font_url(path):
    return "fonts/" + os.path.basename(path)


def font_face(embed):
    """@font-face rules for the brand fonts: local() first, then the font file (fonts/ next to the HTML and in the SCORM
    package, or inlined as a data URI with --embed-font)."""
    out = []
    for fam, w, path in font_assets():
        ext = os.path.splitext(path)[1].lower()
        fmt, mime = ("opentype", "font/otf") if ext == ".otf" else ("truetype", "font/ttf")
        src = 'local(%s)' % css_family(fam + (" Bold" if w == 700 else ""))
        if embed:
            with open(path, "rb") as fh:
                src += ', url(data:%s;base64,%s) format("%s")' % (mime, base64.b64encode(fh.read()).decode(), fmt)
        else:
            src += ', url("%s") format("%s")' % (font_url(path), fmt)
        out.append('@font-face{font-family:%s;font-weight:%d;font-style:normal;font-display:swap;src:%s}' % (css_family(fam), w, src))
    return "\n".join(out)


CSS = """
:root{--dark:#%(dark)s;--primary:#%(primary)s;--secondary:#%(secondary)s;--alert:#%(alert)s;--text:#%(text)s;--muted-text:#%(muted_text)s;
--line:#%(card_line)s;--card:#%(card)s;--track:#%(track)s;--white:#%(white)s;--tint:#%(tint)s;--alert-tint:#%(alert_tint)s}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:%(family)s,system-ui,sans-serif;font-size:%(body)dpx;line-height:%(lh_body)s;color:var(--text);background:#F7F7F7}
.skip{position:absolute;left:-999px;top:0;background:var(--white);color:var(--dark);padding:8px 12px;z-index:10}
.skip:focus{left:8px;top:8px}
.titlebar{background:var(--dark);color:var(--white);display:flex;align-items:center;gap:16px;padding:12px 24px}
.titlebar .chip{background:var(--white);border-radius:6px;padding:6px 10px;display:flex}
.titlebar img{height:32px;width:auto;display:block}
h1,h2,h3,legend{font-family:%(hfamily)s,system-ui,sans-serif}
.titlebar h1{font-size:%(h2)dpx;margin:0;line-height:%(lh_head)s}
.titlebar .eyebrow{margin:0;font-size:%(small)dpx;color:var(--card)}
.progress-wrap{max-width:860px;margin:16px auto 0;padding:0 24px;display:flex;align-items:center;gap:16px}
.progress{flex:1;height:10px;background:var(--track);border-radius:5px;overflow:hidden}
.progress .bar{height:100%%;width:0;background:var(--primary);transition:width .2s}
#counter{margin:0;font-size:%(small)dpx;color:var(--text);white-space:nowrap;font-weight:700}
main{max-width:860px;margin:12px auto;padding:0 24px}
.screen{background:var(--white);border:1px solid var(--line);border-radius:8px;padding:24px 28px;margin-bottom:16px}
.js .screen{display:none}
.js .screen.current{display:block}
.screen h2{color:var(--primary);font-size:%(h1)dpx;line-height:%(lh_head)s;margin:0 0 12px}
.screen .type{display:inline-block;font-size:%(small)dpx;color:var(--dark);background:var(--card);border-radius:4px;padding:1px 8px;margin-bottom:8px;text-transform:capitalize}
.screen ul{padding-left:1.3em}
.screen figure{margin:16px 0}
.screen figure img{max-width:100%%;height:auto;border:1px solid var(--line);border-radius:4px}
fieldset.q,.choices{border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:16px 0}
fieldset.q legend{font-weight:700;padding:0 6px;color:var(--dark)}
.opt{display:flex;align-items:flex-start;gap:10px;padding:8px;border-radius:6px}
.opt:hover{background:var(--tint)}
.opt input{width:20px;height:20px;margin:2px 0 0;accent-color:var(--primary);flex:none}
.opt label{cursor:pointer;flex:1}
.letter{font-weight:700;color:var(--dark);margin-right:6px}
.choices p{margin:0 0 8px;font-weight:700;color:var(--dark)}
button{font:inherit;font-weight:700;border-radius:6px;padding:10px 20px;cursor:pointer;border:2px solid var(--primary);background:var(--white);color:var(--primary)}
button.primary,#next{background:var(--primary);color:var(--white)}
button:disabled{opacity:.45;cursor:not-allowed}
button.choice{display:block;width:100%%;text-align:left;margin:8px 0;font-weight:400;color:var(--text);border-color:var(--line)}
button.choice[aria-pressed="true"]{border-color:var(--primary);background:var(--tint)}
:focus-visible{outline:3px solid var(--secondary);outline-offset:2px}
button:focus-visible,.opt input:focus-visible{outline:3px solid var(--dark);outline-offset:3px}
h2:focus{outline:none}
h2:focus-visible{outline:3px solid var(--secondary)}
.feedback{margin-top:12px;min-height:1px}
.feedback:not(:empty){padding:10px 14px;border-left:6px solid var(--primary);background:var(--tint);border-radius:4px}
.feedback.incorrect:not(:empty){border-left-color:var(--alert);background:var(--alert-tint)}
.feedback ul{margin:6px 0 0}
.objectives{background:var(--tint);border-radius:8px;padding:12px 16px 12px 36px}
.nav{max-width:860px;margin:0 auto 32px;padding:0 24px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.nav .hint{font-size:%(small)dpx;color:var(--muted-text)}
.complete h2::before{content:"\\2713  ";color:var(--primary)}
@media (prefers-reduced-motion:reduce){.progress .bar{transition:none}}
@media print{.nav,.progress-wrap{display:none}.js .screen{display:block}}
"""

JS = r"""
(function(){
  document.documentElement.classList.add('js');
  var screens=[].slice.call(document.querySelectorAll('.screen[data-screen]'));
  var done=document.getElementById('complete'), back=document.getElementById('back'), next=document.getElementById('next');
  var counter=document.getElementById('counter'), bar=document.querySelector('.progress .bar'), prog=document.querySelector('.progress');
  var N=screens.length, i=0, finished=false;
  /* scorm12-adapter:start (D-28) */
  var lms=(function(){
    var api=null, live=false, ended=false, kept=false, fin=false, first={}, ans={}, at=0, back={screen:-1, q:{}};
    var qs=[].slice.call(document.querySelectorAll('fieldset.q')), mainEl=document.getElementById('main');
    var LIMIT=parseInt(mainEl?mainEl.getAttribute('data-suspend-limit'):'',10)||4096;
    function findAPI(win){var tries=0; while(win && win.API==null && win.parent!=null && win.parent!==win){if(++tries>7){return null;} win=win.parent;} return (win && win.API)||null;}
    try{api=findAPI(window); if(!api && window.opener){api=findAPI(window.opener);}}catch(e){api=null;}
    function set(k,v){try{api.LMSSetValue(k,String(v));}catch(e){}}
    function end(){if(!live||ended){return;} if(!fin){set('cmi.core.exit','suspend');} ended=true; try{api.LMSCommit(''); api.LMSFinish('');}catch(e){}}
    if(api){
      try{live=String(api.LMSInitialize(''))==='true';}catch(e){live=false;}
      if(live){var was=''; try{was=String(api.LMSGetValue('cmi.core.lesson_status')||'');}catch(e){}
        kept=(was==='passed'||was==='completed'); if(!kept){set('cmi.core.lesson_status','incomplete');}
        /* resume (D-52): cmi.core.lesson_location = screen number (1-based, as in the counter); cmi.suspend_data = {"q":{"<question #>":[first try right 1/0,"<chosen option indexes, base 36>"]}}, whole answers dropped from the end past the limit; cmi.core.exit 'suspend' on unload before Finish */
        var loc=get('cmi.core.lesson_location'); if(/^\d+$/.test(loc) && +loc>=1 && +loc<=N){back.screen=+loc-1;}
        var sd=null; try{sd=JSON.parse(get('cmi.suspend_data')||'{}');}catch(e){sd=null;}
        if(sd && sd.q && typeof sd.q==='object'){Object.keys(sd.q).forEach(function(j){var v=sd.q[j], fs=qs[+j];
          if(!/^\d+$/.test(j) || !fs || !v || typeof v.length!=='number' || typeof v[1]!=='string'){return;}
          ans[j]=[v[0]?1:0, v[1]]; back.q[j]=v[1];
          if(fs.getAttribute('data-scored')==='true'){first[fs.getAttribute('data-fb')]=!!v[0];}});}}
    }
    function get(k){try{return String(api.LMSGetValue(k)||'');}catch(e){return '';}}
    function save(){
      if(!live||ended){return;}
      set('cmi.core.lesson_location',at+1);
      var o={}, ks=Object.keys(ans); ks.forEach(function(k){o[k]=ans[k];}); var s=JSON.stringify({q:o});
      while(s.length>LIMIT && ks.length){delete o[ks.pop()]; s=JSON.stringify({q:o});} set('cmi.suspend_data',s);
      try{api.LMSCommit('');}catch(e){}
    }
    function place(n,quiet){at=n; if(!quiet){save();}}
    function answer(fs,ok,chosen,quiet){var k=fs.getAttribute('data-fb'); if(fs.getAttribute('data-scored')==='true' && !(k in first)){first[k]=ok;}
      var j=qs.indexOf(fs); if(j>=0 && chosen!==undefined){ans[j]=[ans[j]?ans[j][0]:(ok?1:0), chosen];} if(!quiet){save();}}
    function complete(){
      if(!live||ended){return;}
      fin=true; set('cmi.core.exit','');
      var scored=[].slice.call(document.querySelectorAll('fieldset.q[data-scored]'));
      var main=document.getElementById('main'), pass=parseFloat(main?main.getAttribute('data-pass-percent'):'')||80;
      var status='completed';
      if(scored.length){
        var right=scored.filter(function(f){return first[f.getAttribute('data-fb')]===true;}).length, pct=Math.round(right/scored.length*100);
        set('cmi.core.score.min',0); set('cmi.core.score.max',100); set('cmi.core.score.raw',pct);
        status=pct>=pass?'passed':'failed';
      }
      if(!(kept && status==='failed')){set('cmi.core.lesson_status',status);}
      end();
    }
    if(live && window.addEventListener){['beforeunload','pagehide','unload'].forEach(function(t){window.addEventListener(t,end);});}
    return {answer:answer, complete:complete, end:end, place:place, resume:back};
  })();
  /* scorm12-adapter:end */
  function heading(el){var h=el.querySelector('h2'); if(h){h.focus();}}
  function show(n,focus,boot){
    i=Math.max(0,Math.min(N-1,n)); finished=false; lms.place(i,boot);
    screens.forEach(function(s,k){var on=k===i; s.classList.toggle('current',on); s.hidden=!on;});
    done.classList.remove('current'); done.hidden=true;
    counter.textContent='Screen '+(i+1)+' of '+N;
    bar.style.width=((i+1)/N*100)+'%';
    prog.setAttribute('aria-valuenow',i+1); prog.setAttribute('aria-valuetext',counter.textContent);
    back.disabled=i===0; next.disabled=false; next.textContent=(i===N-1)?'Finish':'Next';
    if(focus){heading(screens[i]); window.scrollTo(0,0);}
  }
  function finish(){
    finished=true;
    screens.forEach(function(s){s.classList.remove('current'); s.hidden=true;});
    done.hidden=false; done.classList.add('current');
    counter.textContent='Module complete'; bar.style.width='100%';
    prog.setAttribute('aria-valuenow',N); prog.setAttribute('aria-valuetext','Module complete');
    back.disabled=false; next.disabled=true; heading(done); window.scrollTo(0,0);
    lms.complete();
  }
  back.addEventListener('click',function(){ if(finished){show(N-1,true);} else {show(i-1,true);} });
  next.addEventListener('click',function(){ if(i===N-1){finish();} else {show(i+1,true);} });
  document.getElementById('restart').addEventListener('click',function(){show(0,true);});
  document.addEventListener('keydown',function(e){
    if(e.altKey||e.ctrlKey||e.metaKey||e.shiftKey) return;
    var t=e.target; if(t && t.matches && t.matches('input,textarea,select,[contenteditable]')) return;
    if(e.key==='ArrowRight' && !next.disabled){e.preventDefault(); next.click();}
    else if(e.key==='ArrowLeft' && !back.disabled){e.preventDefault(); back.click();}
  });
  function say(fb,ok,lines,head){
    fb.className='feedback '+(ok?'correct':'incorrect'); fb.textContent='';
    var p=document.createElement('p'); p.style.margin='0';
    var b=document.createElement('strong'); b.textContent=head; p.appendChild(b);
    if(lines.length===1){p.appendChild(document.createTextNode(' '+lines[0])); fb.appendChild(p); return;}
    fb.appendChild(p); var ul=document.createElement('ul');
    lines.forEach(function(l){var li=document.createElement('li'); li.textContent=l; ul.appendChild(li);}); fb.appendChild(ul);
  }
  function picked(inputs){return inputs.map(function(x,n){return x.checked?n.toString(36):'';}).join('');}
  [].forEach.call(document.querySelectorAll('fieldset.q'),function(fs,j){
    var fb=document.getElementById(fs.getAttribute('data-fb'));
    var inputs=[].slice.call(fs.querySelectorAll('input')), grade;
    if(fs.getAttribute('data-multi')==='true'){
      grade=function(quiet){
        var chosen=inputs.filter(function(x){return x.checked;});
        if(!chosen.length){say(fb,false,['Choose at least one option, then select Check Answer.'],'No option chosen.'); return;}
        var ok=inputs.every(function(x){return x.checked===(x.getAttribute('data-correct')==='true');});
        lms.answer(fs,ok,picked(inputs),quiet);
        say(fb,ok,chosen.map(function(x){return x.getAttribute('data-letter')+': '+x.getAttribute('data-feedback');}),ok?'Correct.':'Not quite.');
      };
      fs.querySelector('button.check').addEventListener('click',function(){grade(false);});
    } else {
      grade=function(quiet){
        var x=inputs.filter(function(y){return y.checked;})[0]; if(!x){return;}
        var ok=x.getAttribute('data-correct')==='true';
        lms.answer(fs,ok,picked(inputs),quiet);
        say(fb,ok,[x.getAttribute('data-feedback')],ok?'Correct.':'Not quite.');
      };
      inputs.forEach(function(x){x.addEventListener('change',function(){grade(false);});});
    }
    var was=lms.resume.q[j];
    if(was){inputs.forEach(function(x,n){x.checked=was.indexOf(n.toString(36))>=0;}); grade(true);}
  });
  [].forEach.call(document.querySelectorAll('.choices'),function(g){
    var fb=document.getElementById(g.getAttribute('data-fb'));
    var btns=[].slice.call(g.querySelectorAll('button.choice'));
    btns.forEach(function(b){b.addEventListener('click',function(){
      btns.forEach(function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
      var ok=b.getAttribute('data-correct')==='true';
      say(fb,ok,[b.getAttribute('data-feedback')],ok?'Best choice.':'Think again.');
    });});
  });
  show(lms.resume.screen>=0?lms.resume.screen:0,false,true);
})();
"""


def render_screen(s, k, n, meta, base_dir):
    sid = esc(s.get("id"))
    out = ['<section class="screen" data-screen="%d" id="screen-%s" data-id="%s" data-type="%s" aria-labelledby="h-%s">' % (k, sid, sid, esc(s.get("type")), sid),
           '<span class="type">%s</span>' % esc(s.get("type")),
           '<h2 id="h-%s" tabindex="-1">%s</h2>' % (sid, esc(s.get("title"))), paras(s.get("body"))]
    if s.get("bullets"):
        out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(b) for b in s["bullets"]))
    if s.get("image"):
        alt = "" if s.get("decorative") else s.get("alt")
        out.append('<figure><img src="%s" alt="%s"></figure>' % (esc(data_uri(str(s["image"]), base_dir)), esc(alt)))
    kind, q, opts = options_of(s)
    fb = "fb-%s" % sid
    if kind == "question":
        multi = bool(q.get("multi"))
        out.append('<fieldset class="q" data-multi="%s" data-fb="%s"%s><legend>%s%s</legend>' % ("true" if multi else "false", fb, ' data-scored="true"' if s.get("type") == "question" else "", esc(q.get("stem")), " (Choose all that apply.)" if multi else ""))
        for i, o in enumerate(opts):
            oid = "%s-%s" % (sid, LETTERS[i])
            out.append('<div class="opt"><input type="%s" name="q-%s" id="%s" value="%s" data-letter="%s" data-correct="%s" data-feedback="%s">'
                       '<label for="%s"><span class="letter">%s.</span>%s</label></div>' % (
                           "checkbox" if multi else "radio", sid, oid, LETTERS[i], LETTERS[i], "true" if o.get("correct") else "false", esc(o.get("feedback")), oid, LETTERS[i], inline(o.get("text"))))
        if multi:
            out.append('<button type="button" class="check primary">Check Answer</button>')
        out.append("</fieldset>")
    elif kind == "choices":
        out.append('<div class="choices" role="group" aria-labelledby="cl-%s" data-fb="%s"><p id="cl-%s">What would you do?</p>' % (sid, fb, sid))
        for i, o in enumerate(opts):
            out.append('<button type="button" class="choice" aria-pressed="false" data-letter="%s" data-correct="%s" data-feedback="%s"><span class="letter">%s.</span>%s</button>' % (
                LETTERS[i], "true" if o.get("correct") else "false", esc(o.get("feedback")), LETTERS[i], inline(o.get("text"))))
        out.append("</div>")
    if kind:
        out.append('<div class="feedback" id="%s" role="status" aria-live="polite"></div>' % fb)
    if s.get("type") == "summary":
        out.append('<h3>You can now:</h3><ul class="objectives">%s</ul>' % "".join("<li>%s</li>" % inline(o) for o in meta.get("objectives") or []))
    out.append("</section>")
    return "\n".join(x for x in out if x)


def render_html(mod, base_dir=".", embed_font=False, draft=False):
    m = mod.get("meta") or {}
    sc = screens_of(mod)
    n = len(sc)
    T = cur()
    C, b = T["colors"], T["brand"]
    css = font_face(embed_font) + CSS % dict(C, **{"body": TOKENS["screen_px"]["body"], "small": TOKENS["screen_px"]["small"],
                                                   "h1": TOKENS["screen_px"]["h1"], "h2": TOKENS["screen_px"]["h2"],
                                                   "tint": BR.mix(C["primary"], "FFFFFF", 0.06), "alert_tint": BR.mix(C["alert"], "FFFFFF", 0.06),
                                                   "family": css_family(T["fonts"]["body"]), "hfamily": css_family(T["fonts"].get("heading") or T["fonts"]["body"]),
                                                   # line heights from the fonts' own metrics (body: 1.25 x single spacing; headings: single spacing)
                                                   "lh_body": "%.2f" % (b.metrics("body")["line"] * 1.25), "lh_head": "%.2f" % b.metrics("heading", bold=True)["line"]})
    eyebrow = "E-learning \u00b7 Version %s \u00b7 %s \u00b7 About %s minutes%s" % (m.get("version", ""), m.get("date", ""), m.get("duration_min", "?"), " \u00b7 DRAFT" if draft else "")
    body = "\n".join(render_screen(s, k, n, m, base_dir) for k, s in enumerate(sc))
    year = (re.match(r"(\d{4})", str(m.get("date", ""))) or [None, None])[1]
    owner = b.footer(year)  # "" when the project names no owner: no copyright line
    footer = " \u00b7 ".join(x for x in (esc(owner), "%s v%s" % (esc(m.get("title")), esc(m.get("version", "")))) if x)
    logo = logo_uri()
    chip = '<span class="chip"><img src="%s" alt="%s"></span>' % (logo, esc(b.logo_alt())) if logo else ""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="material-composer build_module.py">
<title>%(title)s</title>
<style>
%(css)s
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="titlebar">%(chip)s<div><p class="eyebrow">%(eyebrow)s</p><h1>%(title)s</h1></div></header>
<div class="progress-wrap"><div class="progress" role="progressbar" aria-label="Module progress" aria-valuemin="1" aria-valuemax="%(n)d" aria-valuenow="1"><div class="bar"></div></div><p id="counter" aria-live="polite">Screen 1 of %(n)d</p></div>
<main id="main" data-pass-percent="%(pass)s" data-suspend-limit="%(limit)d">
%(body)s
<section class="screen complete" id="complete" hidden aria-labelledby="h-complete"><h2 id="h-complete" tabindex="-1">Module complete</h2><p>You finished all %(n)d screens of %(title)s. You can close this window, or start again to review.</p><button type="button" id="restart">Start Again</button></section>
</main>
<nav class="nav" aria-label="Screen navigation"><button type="button" id="back">Back</button><span class="hint">Tip: use the Left and Right arrow keys to move between screens.</span><button type="button" id="next">Next</button></nav>
<noscript><p style="max-width:860px;margin:0 auto;padding:0 24px">JavaScript is off: all screens are shown in order, and answer feedback is not available.</p></noscript>
<footer style="max-width:860px;margin:0 auto 24px;padding:0 24px;font-size:12px;color:#%(gray)s">%(footer)s</footer>
<script>
%(js)s
</script>
</body>
</html>
""" % {"title": esc(m.get("title")), "css": css, "chip": chip, "eyebrow": esc(eyebrow), "n": n, "body": body, "js": JS,
       "footer": footer, "gray": C["muted_text"], "pass": "%g" % pass_mark(m),
       "limit": RULES["scorm_suspend_limit"]}


# ---------------------------------------------------------------- SCORM 1.2 (D-28)
ADLCP = "http://www.adlnet.org/xsd/adlcp_rootv1p2"
SCORM_NEEDS = ("LMSInitialize", "cmi.core.lesson_status", "cmi.core.score.raw")


def pass_mark(m):
    try:
        p = float(m.get("pass_percent", 80))
    except (TypeError, ValueError):
        return 80.0
    return p if 0 < p <= 100 else 80.0


def scored_questions(mod):
    return sum(1 for s in screens_of(mod) if s.get("type") == "question" and options_of(s)[0] == "question")


def scorm_manifest(mod, files):
    m = mod.get("meta") or {}
    title = esc(m.get("title") or "Module")
    ident = "MOD-" + hashlib.sha256((str(m.get("title")) + str(m.get("version"))).encode("utf-8")).hexdigest()[:12]
    mastery = "\n        <adlcp:masteryscore>%g</adlcp:masteryscore>" % pass_mark(m) if scored_questions(mod) else ""
    listed = "\n".join('        <file href="%s"/>' % esc(f) for f in files)
    return """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="%(id)s" version="%(ver)s" xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" xmlns:adlcp="%(adlcp)s">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>%(title)s</title>
      <item identifier="ITEM-1" identifierref="RES-1" isvisible="true">
        <title>%(title)s</title>%(mastery)s
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" adlcp:scormtype="sco" href="index.html">
%(files)s
    </resource>
  </resources>
</manifest>
""" % {"id": ident, "ver": esc(m.get("version") or "1.0"), "adlcp": ADLCP, "title": title, "mastery": mastery, "files": listed}


def write_scorm(mod, doc, path, fonts=()):
    files = {"index.html": doc.encode("utf-8")}
    for _f, _w, fp in fonts:
        with open(fp, "rb") as fh:
            files[font_url(fp)] = fh.read()
    d = re.match(r"(\d{4})-(\d{2})-(\d{2})", str((mod.get("meta") or {}).get("date", "")))
    stamp = (int(d.group(1)), int(d.group(2)), int(d.group(3)), 0, 0, 0) if d and int(d.group(1)) >= 1980 else (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in [("imsmanifest.xml", scorm_manifest(mod, sorted(files)))] + sorted(files.items()):
            zi = zipfile.ZipInfo(name, date_time=stamp)
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(zi, text if isinstance(text, bytes) else text.encode("utf-8"))
    return sorted(["imsmanifest.xml"] + list(files))


def suspend_worst(page):
    """Longest cmi.suspend_data the page can write (D-52): every question answered with every option chosen."""
    qs = re.findall(r'<fieldset class="q".*?</fieldset>', page, re.S)
    b36 = "0123456789abcdefghijklmnopqrstuvwxyz"
    parts = ['"%d":[0,"%s"]' % (j, "".join(b36[n % 36] for n in range(len(re.findall(r"<input ", f))))) for j, f in enumerate(qs)]
    return len('{"q":{%s}}' % ",".join(parts))


def scorm_fail(g, bad, msg):
    return g.check(bad, "FAIL", "SCORM_PACKAGE", msg)  # check: SCORM_PACKAGE FAIL


def scorm_check(path, g=None):
    """Gate a built SCORM 1.2 zip: manifest at root parses, schemaversion 1.2, one SCO whose href exists,
    every file listed, adapter calls present in index.html, and index.html still offline."""
    g = g or Gate("SCORM_PACKAGE")
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        scorm_fail(g, True, "%s is not a readable zip (%s)" % (os.path.basename(path), e))
        return g
    with z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        scorm_fail(g, "imsmanifest.xml" not in names, "imsmanifest.xml is not at the root of the zip")
        nested = [n for n in names if n.lower().endswith((".zip", ".7z", ".rar", ".tar", ".gz"))]
        scorm_fail(g, bool(nested), "nested archive(s) in the package: %s" % ", ".join(nested))
        if "imsmanifest.xml" not in names:
            return g
        try:
            root = ET.fromstring(z.read("imsmanifest.xml"))
        except ET.ParseError as e:
            scorm_fail(g, True, "imsmanifest.xml does not parse as XML (%s)" % e)
            return g
        ln = lambda el: el.tag.rsplit("}", 1)[-1]
        els = list(root.iter())
        text_of = lambda tag: [(e.text or "").strip() for e in els if ln(e) == tag]
        scorm_fail(g, "1.2" not in text_of("schemaversion"), "manifest does not declare schemaversion 1.2 (found %s)" % (text_of("schemaversion") or "none"))
        scorm_fail(g, "ADL SCORM" not in text_of("schema"), "manifest metadata schema is not \"ADL SCORM\"")
        orgs = [e for e in els if ln(e) == "organization"]
        scorm_fail(g, len(orgs) != 1, "manifest needs exactly one organization (has %d)" % len(orgs))
        res = [e for e in els if ln(e) == "resource"]
        scos = [r for r in res if (r.get("{%s}scormtype" % ADLCP) or r.get("{%s}scormType" % ADLCP) or "").lower() == "sco"]
        scorm_fail(g, len(scos) != 1, "manifest needs exactly one SCO resource (has %d)" % len(scos))
        if len(scos) == 1:
            href = scos[0].get("href") or ""
            scorm_fail(g, href not in names, "SCO href \"%s\" is not in the zip" % href)
            refs = [e.get("identifierref") for e in els if ln(e) == "item"]
            scorm_fail(g, scos[0].get("identifier") not in refs, "no item points at the SCO resource %s" % scos[0].get("identifier"))
        listed = {f.get("href") for r in res for f in r if ln(f) == "file"}
        want = set(names) - {"imsmanifest.xml"}
        scorm_fail(g, want - listed, "file(s) in the zip but not listed in the manifest: %s" % ", ".join(sorted(want - listed)))
        scorm_fail(g, listed - want, "file(s) listed in the manifest but missing from the zip: %s" % ", ".join(sorted(listed - want)))
        if "index.html" not in names:
            scorm_fail(g, True, "index.html is not in the zip")
            return g
        page = z.read("index.html").decode("utf-8", "replace")
        miss = [k for k in SCORM_NEEDS if k not in page]
        scorm_fail(g, bool(miss), "index.html has no SCORM 1.2 adapter (missing %s)" % ", ".join(miss))
        gone = [k for k in RULES["scorm_resume_needs"] if k not in page]
        scorm_fail(g, bool(gone), "index.html does not save the learner's place (missing %s)" % ", ".join(gone))
        worst, lim = suspend_worst(page), RULES["scorm_suspend_limit"]
        scorm_fail(g, worst > lim, "cmi.suspend_data could reach %d characters; SCORM 1.2 allows %d (fewer questions or options)" % (worst, lim))
        offline_check(page, g)
    return g


# ---------------------------------------------------------------- storyboard
def cell(s):
    return str(s or "").replace("|", "\\|").replace("\r", "").replace("\n\n", "<br>").replace("\n", " ").strip()


def yaml_str(s):
    return json.dumps(str(s), ensure_ascii=False)


def storyboard(mod):
    m = mod.get("meta") or {}
    fm = ["---", "title: %s" % yaml_str(m.get("title", "")), "audience: %s" % yaml_str(m.get("audience", "")), "objectives:"]
    fm += ["  - %s" % yaml_str(o) for o in m.get("objectives") or []]
    fm += ["duration_min: %s" % (m.get("duration_min") or 0), "version: %s" % yaml_str(m.get("version", "")), "date: %s" % yaml_str(m.get("date", "")), "sources:"]
    fm += ["  - %s" % yaml_str(s) for s in m.get("sources") or []]
    fm += ["---", "", "# %s: Storyboard" % m.get("title", ""), "",
           "Built by material-composer `build_module.py`. Each row is one screen of the HTML module.", "",
           "| Screen | Type | On Screen | Interaction | Feedback |", "|---|---|---|---|---|"]
    for s in screens_of(mod):
        on = ["**%s**" % cell(s.get("title"))]
        if s.get("body"):
            on.append(cell(s.get("body")))
        on += ["\u2022 %s" % cell(b) for b in s.get("bullets") or []]
        if s.get("image"):
            on.append("Image: %s (alt: %s)" % (cell(os.path.basename(str(s["image"]))), cell(s.get("alt") or "decorative")))
        if s.get("type") == "summary":
            on.append("Objectives: " + "; ".join(cell(o) for o in m.get("objectives") or []))
        if s.get("_added"):
            on.append("(added by the builder)")
        kind, q, opts = options_of(s)
        if kind == "question":
            inter = ["%s: %s" % ("Multiple choice, choose all" if q.get("multi") else "Single choice", cell(q.get("stem")))]
        elif kind == "choices":
            inter = ["Branching choice: What would you do?"]
        else:
            inter = ["None"]
        inter += ["%s. %s%s" % (LETTERS[i], cell(o.get("text")), " (correct)" if o.get("correct") else "") for i, o in enumerate(opts)]
        fbk = ["%s: %s" % (LETTERS[i], cell(o.get("feedback")) or "**missing**") for i, o in enumerate(opts)] or ["n/a"]
        fm.append("| %s | %s | %s | %s | %s |" % (cell(s.get("id")), cell(s.get("type")), "<br>".join(on), "<br>".join(inter), "<br>".join(fbk)))
    fm += ["", "Sources: " + "; ".join(cell(s) for s in m.get("sources") or []), ""]
    return "\n".join(fm)


# ---------------------------------------------------------------- CLI
def run(mod, out=None, base_dir=".", draft=False, check=False, embed_font=False, say=print, scorm=False, source=None, brand=None):
    """source: the module.json path (its project supplies the brand); brand: an explicit brand.json."""
    set_brand(source, brand)
    g = gate(mod, base_dir)
    if not check and g.failed and not draft:
        g.report(say)
        say("refused: fix the FAIL lines or pass --draft")
        return g, None
    doc = render_html(mod, base_dir, embed_font, draft)
    offline_check(doc, g)
    if check or out is None:
        g.report(say)
        return g, None
    if g.failed and not draft:
        g.report(say)
        say("refused: fix the FAIL lines or pass --draft")
        return g, None
    with open(out + ".html", "w", encoding="utf-8") as fh:
        fh.write(doc)
    with open(out + ".storyboard.md", "w", encoding="utf-8") as fh:
        fh.write(storyboard(mod))
    fonts = [] if embed_font else font_assets()
    if fonts:  # the @font-face rules point at fonts/ next to the HTML
        fdir = os.path.join(os.path.dirname(os.path.abspath(out)), "fonts")
        os.makedirs(fdir, exist_ok=True)
        for _f, _w, fp in fonts:
            shutil.copyfile(fp, os.path.join(fdir, os.path.basename(fp)))
    zp = sg = None
    if scorm:
        zp = out + "_SCORM12.zip"
        entries = write_scorm(mod, doc, zp, fonts)
        sg = scorm_check(zp)
        g.n += sg.n
        g.msgs += sg.msgs
    g.report(say)
    say("wrote %s.html (%d screens, %d KB) and %s.storyboard.md%s%s" % (out, len(screens_of(mod)), len(doc) // 1024, out,
        "; fonts/ beside it: %s (keep the folder with the HTML)" % ", ".join(os.path.basename(p) for _f, _w, p in fonts) if fonts else "",
        " (DRAFT)" if draft else ""))
    if scorm:
        if sg.failed:
            os.remove(zp)
            say("SCORM_PACKAGE GATE: %d checks, %d failed; refused: %s removed" % (sg.n, sg.failed, os.path.basename(zp)))
            return g, None
        say("SCORM_PACKAGE GATE: %d checks, 0 failed; wrote %s (%s; %d KB)" % (sg.n, os.path.basename(zp), ", ".join(entries), os.path.getsize(zp) // 1024))
        return g, (out + ".html", out + ".storyboard.md", zp)
    return g, (out + ".html", out + ".storyboard.md")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module")
    ap.add_argument("--out")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--embed-font", action="store_true", help="inline the brand font files as data URIs instead of a fonts/ folder (one self-contained file; adds their size)")
    ap.add_argument("--scorm", action="store_true", help="also write Name_SCORM12.zip for your LMS (D-28)")
    ap.add_argument("--brand", help="brand profile (brand.json); default: the module's project brand")
    a = ap.parse_args()
    if not a.check and not a.out:
        ap.error("--out Name or --check is required")
    mod = json.load(open(a.module, encoding="utf-8"))
    if a.scorm and not a.out:
        ap.error("--scorm needs --out Name")
    g, files = run(mod, a.out, os.path.dirname(os.path.abspath(a.module)), a.draft, a.check, a.embed_font, scorm=a.scorm, source=a.module, brand=a.brand)
    print(cur()["brand"].lines()[0])
    if a.scorm and files is None:
        return 1
    return 1 if g.failed and not (a.draft and files) else 0


if __name__ == "__main__":
    sys.exit(main())
