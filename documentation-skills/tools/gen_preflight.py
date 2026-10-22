#!/usr/bin/env python3
"""Regenerate each skill's scripts/preflight.py from the files in its folder.

Usage:
    python tools/gen_preflight.py [--root DIR] [--check] [skill ...]

With no skill names, every folder under skills/ that has a SKILL.md is regenerated. --root is the package
root that holds skills/ (default: the parent of this tools/ folder). --check writes
nothing and exits 1 if any preflight.py would change.

Rerun this after every edit to a skill: the preflight lists every packaged file
with its size and sha256[:12], so any edit makes the skill report CHANGED.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Runtime requirements per skill (folder name). Edit here, then rerun the generator.
# Skills not listed here keep the settings found in their current preflight.py.
SETTINGS = {
    "document-builder": {
        "NEEDS_NODE": False,
        "REQUIRES": {"docx": "python-docx"},
        "OPTIONAL": {"PIL": "Pillow", "fitz": "PyMuPDF", "matplotlib": "matplotlib", "numpy": "numpy"},
        "NEEDS_OFFICE": True,
    },
    "slide-deck": {
        "NEEDS_NODE": False,
        "REQUIRES": {"pptx": "python-pptx"},
        "OPTIONAL": {"PIL": "Pillow", "fitz": "PyMuPDF"},
        "NEEDS_OFFICE": True,
    },
    "material-composer": {
        "NEEDS_NODE": False,
        "REQUIRES": {},
        "OPTIONAL": {"PIL": "Pillow", "docx": "python-docx", "fitz": "PyMuPDF", "openpyxl": "openpyxl"},
        "NEEDS_OFFICE": False,
    },
    "training-material-designer": {
        "NEEDS_NODE": False,
        "REQUIRES": {},
        "OPTIONAL": {"fitz": "PyMuPDF", "yaml": "PyYAML"},
        "NEEDS_OFFICE": False,
    },
    "github-docs": {
        "NEEDS_NODE": False,
        "REQUIRES": {},
        "OPTIONAL": {"PIL": "Pillow", "fitz": "PyMuPDF", "yaml": "PyYAML"},
        "NEEDS_OFFICE": False,
    },
}
SETTING_KEYS = ("NEEDS_NODE", "REQUIRES", "OPTIONAL", "NEEDS_OFFICE")

# Never packaged: caches, OS litter and render output folders.
EXCLUDE_DIRS = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git",
                "render", "renders", "_render*", "*_render", "*-render", "*_renders", "*-renders")
EXCLUDE_FILES = ("*.pyc", "*.pyo", ".DS_Store", "Thumbs.db", "desktop.ini")
PREFLIGHT = "scripts/preflight.py"


def excluded_dir(name):
    return any(fnmatch.fnmatch(name.lower(), p.lower()) for p in EXCLUDE_DIRS)


def excluded_file(name):
    return any(fnmatch.fnmatch(name.lower(), p.lower()) for p in EXCLUDE_FILES)


def skill_files(skill_dir, include_preflight=False):
    """Sorted forward-slash paths of every packaged file in skill_dir."""
    out = []
    for dp, dns, fns in os.walk(skill_dir):
        dns[:] = sorted(d for d in dns if not excluded_dir(d))
        for f in fns:
            if excluded_file(f):
                continue
            rel = os.path.relpath(os.path.join(dp, f), skill_dir).replace(os.sep, "/")
            if rel == PREFLIGHT and not include_preflight:
                continue
            out.append(rel)
    return sorted(out)


def frontmatter(skill_dir):
    """name and version from the SKILL.md YAML frontmatter (simple key: value lines)."""
    path = os.path.join(skill_dir, "SKILL.md")
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0].strip() != "---":
        raise SystemExit("ERROR %s: no frontmatter" % path)
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("'\"")
    for k in ("name", "version"):
        if not meta.get(k):
            raise SystemExit("ERROR %s: frontmatter has no %s" % (path, k))
    return meta["name"], meta["version"]


def settings_from_preflight(path):
    """Read NEEDS_NODE/REQUIRES/OPTIONAL/NEEDS_OFFICE literals from an existing preflight.py."""
    import ast
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return None
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in SETTING_KEYS:
                try:
                    found[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
    return found if all(k in found for k in SETTING_KEYS) else None


def settings_for(skill, skill_dir):
    if skill in SETTINGS:
        return SETTINGS[skill]
    s = settings_from_preflight(os.path.join(skill_dir, PREFLIGHT))
    if s is None:
        raise SystemExit("ERROR %s: not in SETTINGS and no readable settings in %s; add it to SETTINGS in %s"
                         % (skill, PREFLIGHT, os.path.basename(__file__)))
    return s


def lit(value):
    """ASCII-only Python literal (json is valid Python for str/int/dict-of-str)."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


TEMPLATE = '''#!/usr/bin/env python3
"""Preflight for the @NAME@ skill (v@VERSION@). Generated by tools/gen_preflight.py; do not edit by hand.
Checks every packaged file and required runtimes before any work starts. Prints READY, or NOT READY and exits 1."""
import glob, hashlib, importlib.util, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = @NAME_LIT@
VERSION = @VERSION_LIT@
FILES = {
@FILES@
}
NEEDS_NODE = @NEEDS_NODE@
REQUIRES = @REQUIRES@
OPTIONAL = @OPTIONAL@
NEEDS_OFFICE = @NEEDS_OFFICE@
def absent(mods):
    out = []
    for m, pip in sorted(mods.items()):
        try:
            found = importlib.util.find_spec(m) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            out.append(pip if pip == m else "%s (import %s)" % (pip, m))
    return out
def find_office():
    for exe in ("soffice", "libreoffice"):
        p = shutil.which(exe)
        if p:
            return p
    cands = []
    if os.name == "nt":
        bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
        for base in [b for b in bases if b] + ["C:\\\\Program Files", "C:\\\\Program Files (x86)"]:
            cands.append(os.path.join(base, "LibreOffice", "program", "soffice.exe"))
    elif sys.platform == "darwin":
        cands.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    else:
        cands += ["/usr/bin/soffice", "/usr/local/bin/soffice", "/snap/bin/libreoffice"]
        cands += sorted(glob.glob("/opt/libreoffice*/program/soffice"))
    for p in cands:
        if os.path.isfile(p):
            return p
    return None
def windows_office():
    """Installed Office apps (PowerPoint, Word) that scripts/visual_batch.py can use to export PDFs on Windows."""
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []
    found = []
    for app in ("PowerPoint", "Word"):
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, app + ".Application"))
            found.append(app)
        except OSError:
            pass
    return found
def node_version(node):
    try:
        return subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
def main():
    missing, changed = [], []
    for rel, (size, sha) in sorted(FILES.items()):
        p = os.path.join(ROOT, *rel.split("/"))
        if not os.path.isfile(p):
            missing.append(rel)
            continue
        with open(p, "rb") as fh:
            data = fh.read()
        if len(data) != size or hashlib.sha256(data).hexdigest()[:12] != sha:
            changed.append(rel)
    node = shutil.which("node")
    nv = node_version(node) if node else ""
    print("skill: " + SKILL + " v" + VERSION + " | folder: " + ROOT)
    print("python: " + sys.version.split()[0])
    if missing: print("MISSING " + str(len(missing)) + " of " + str(len(FILES)) + " files: " + ", ".join(missing))
    if changed: print("CHANGED (differs from the packaged v" + VERSION + " file): " + ", ".join(changed))
    if NEEDS_NODE and not node: print("MISSING Node.js: this skill's scripts need `node` in the sandbox")
    req, opt = absent(REQUIRES), absent(OPTIONAL)
    office = find_office() if NEEDS_OFFICE else None
    ms = windows_office() if NEEDS_OFFICE and not office else []
    if req: print("MISSING Python modules (pip install): " + ", ".join(req))  # check: PREFLIGHT_RUNTIME FAIL
    if opt: print("WARN optional Python modules not installed (the features that use them will not run): " + ", ".join(opt))  # check: PREFLIGHT_RUNTIME WARN
    if NEEDS_OFFICE and not office and ms: print("LibreOffice not found; PDF export and previews use " + " and ".join(ms) + " (Windows)")
    elif NEEDS_OFFICE and not office: print("WARN LibreOffice not found: PDF output will not run; .docx and .pptx still build")  # check: PREFLIGHT_RUNTIME WARN
    if NEEDS_OFFICE:
        conv = "LibreOffice" if office else " and ".join(ms)
        gone = ([] if conv else ["LibreOffice"]) + absent({"fitz": "PyMuPDF"})
        if gone: print("WARN render: not available (missing " + ", ".join(gone) + "): report visual review: not run (no renderer)")  # check: RENDER_PROBE WARN
        else: print("render: available (" + conv + ", PyMuPDF); visual review also needs an image viewer in this session")
    if missing or (NEEDS_NODE and not node) or req:
        print("NOT READY: ask for " + SKILL + ".zip to be attached to this chat (or re-uploaded to the agent as a .zip), extract it, and run preflight from that folder.")
        sys.exit(1)
    rt = len(REQUIRES) + len(OPTIONAL)
    print("READY: " + str(len(FILES)) + " files" + (", node " + nv if NEEDS_NODE and node else "") + (", python modules %d of %d" % (rt - len(opt), rt) if rt else "") + (", LibreOffice" if NEEDS_OFFICE and office else (", " + " and ".join(ms) if ms else "")) +(" (warning: changed files above)" if changed else ""))
if __name__ == "__main__":
    main()
'''


def render(skill_dir, skill):
    """Return the generated preflight.py source (str, LF line endings, ASCII only)."""
    name, version = frontmatter(skill_dir)
    st = settings_for(skill, skill_dir)
    rows = []
    for rel in skill_files(skill_dir):
        with open(os.path.join(skill_dir, *rel.split("/")), "rb") as fh:
            data = fh.read()
        rows.append("%s: (%d, %s)," % (lit(rel), len(data), lit(hashlib.sha256(data).hexdigest()[:12])))
    src = TEMPLATE
    for key, val in (("@NAME_LIT@", lit(name)), ("@VERSION_LIT@", lit(version)),
                     ("@NAME@", name), ("@VERSION@", version), ("@FILES@", "\n".join(rows)),
                     ("@NEEDS_NODE@", repr(bool(st["NEEDS_NODE"]))), ("@NEEDS_OFFICE@", repr(bool(st["NEEDS_OFFICE"]))),
                     ("@REQUIRES@", lit(st["REQUIRES"])), ("@OPTIONAL@", lit(st["OPTIONAL"]))):
        src = src.replace(key, val)
    src.encode("ascii")  # raises if the docstring name/version is not ASCII
    return src, name, version, len(rows)


def all_skills(root):
    base = os.path.join(root, "skills")
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "SKILL.md")))


def generate(root, skills=None, check=False, quiet=False):
    """Regenerate (or with check=True, only compare) preflights. Returns the list of skills that differ."""
    skills = skills or all_skills(root)
    stale = []
    for skill in skills:
        skill_dir = os.path.join(root, "skills", skill)
        if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
            raise SystemExit("ERROR no skill at %s" % skill_dir)
        src, name, version, nfiles = render(skill_dir, skill)
        if name != skill:
            print("WARN %s: SKILL.md name is %r but the folder is %r; the preflight will ask for %s.zip"
                  % (skill, name, skill, name), file=sys.stderr)
        target = os.path.join(skill_dir, *PREFLIGHT.split("/"))
        new = src.encode("ascii")
        try:
            with open(target, "rb") as fh:
                old = fh.read()
        except OSError:
            old = None
        if old != new:
            stale.append(skill)
        if check:
            if not quiet:
                print("%s %s v%s: %s" % ("STALE" if old != new else "ok", skill, version,
                                         "preflight.py would change" if old != new else "preflight.py is current"))
            continue
        if old != new:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as fh:  # bytes: LF line endings on every platform
                fh.write(new)
        if not quiet:
            print("%s %s v%s: %d files" % ("wrote" if old != new else "unchanged", skill, version, nfiles))
    return stale


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("skills", nargs="*", help="skill folder names (default: all)")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="package root holding skills/ (default: %(default)s)")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if any preflight.py would change")
    a = ap.parse_args()
    stale = generate(os.path.abspath(a.root), a.skills, check=a.check)
    if a.check and stale:
        print("FAIL preflight out of date for: %s (run: python tools/gen_preflight.py)" % ", ".join(stale))
        sys.exit(1)


if __name__ == "__main__":
    main()
