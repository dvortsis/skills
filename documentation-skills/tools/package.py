#!/usr/bin/env python3
"""Build the skill zips.

Usage:
    python tools/package.py --out DIR [--root DIR]
    python tools/package.py --check [--root DIR]

Default mode regenerates every skill's scripts/preflight.py (tools/gen_preflight.py),
runs each preflight and stops if any prints NOT READY or CHANGED (or exits nonzero),
then writes DIR/<skill>.zip per skill (skill folder at the zip root) and
DIR/documentation-skills.zip (skills/<skill>/... for every skill). Each per-skill zip
is extracted to a temporary folder and its preflight rerun before the summary prints.

--check writes nothing: exit 1 if regenerating would change any preflight.py.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import gen_preflight as gp  # noqa: E402

BUNDLE = "documentation-skills.zip"
ZIP_DATE = (2026, 1, 1, 0, 0, 0)  # fixed timestamp: same inputs give byte-identical zips


def run_preflight(path):
    """Run a preflight from a neutral working directory. Returns (ok, output)."""
    r = subprocess.run([sys.executable, path], capture_output=True, text=True, cwd=tempfile.gettempdir())
    out = (r.stdout + r.stderr).strip()
    lines = out.splitlines()
    bad = r.returncode != 0 or any(l.startswith(("NOT READY", "CHANGED")) for l in lines) \
        or not any(l.startswith("READY") for l in lines)
    return not bad, out


def add(zf, arcname, src):
    with open(src, "rb") as fh:
        data = fh.read()
    zi = zipfile.ZipInfo(arcname, ZIP_DATE)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, data)
    return len(data)


def main():
    ap = argparse.ArgumentParser(description="Build the skill zips.")
    ap.add_argument("--out", help="output folder for the zips")
    ap.add_argument("--root", default=gp.DEFAULT_ROOT, help="package root holding skills/ (default: %(default)s)")
    ap.add_argument("--check", action="store_true", help="only verify every preflight.py is current; exit 1 if not")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    skills = gp.all_skills(root)

    if a.check:
        stale = gp.generate(root, skills, check=True)
        if stale:
            print("FAIL preflight out of date for: %s (run: python tools/gen_preflight.py)" % ", ".join(stale))
            sys.exit(1)
        print("OK all %d preflights are current" % len(skills))
        return
    if not a.out:
        ap.error("--out DIR is required (or use --check)")
    out = os.path.abspath(a.out)
    skills_dir = os.path.join(root, "skills")
    if os.path.commonpath([out, skills_dir]) == skills_dir:
        sys.exit("ERROR --out must not be inside %s" % skills_dir)

    # 1. Each SKILL.md name must equal its folder: the preflight asks for <name>.zip.
    bad = [(s, gp.frontmatter(os.path.join(skills_dir, s))[0]) for s in skills]
    bad = [(s, n) for s, n in bad if n != s]
    if bad:
        for s, n in bad:
            print("FAIL %s: SKILL.md name is %r; it must equal the folder name (the zip is %s.zip)" % (s, n, s))
        sys.exit(1)

    # 2. Regenerate, then run every preflight.
    gp.generate(root, skills)
    failed = []
    for s in skills:
        ok, text = run_preflight(os.path.join(skills_dir, s, "scripts", "preflight.py"))
        print("--- preflight %s\n%s" % (s, text))
        if not ok:
            failed.append(s)
    if failed:
        print("FAIL preflight not READY (or CHANGED) for: " + ", ".join(failed))
        sys.exit(1)

    # 3. Write the zips.
    os.makedirs(out, exist_ok=True)
    summary = []
    with zipfile.ZipFile(os.path.join(out, BUNDLE), "w") as bundle:
        btotal = bfiles = 0
        for s in skills:
            sdir = os.path.join(skills_dir, s)
            files = gp.skill_files(sdir, include_preflight=True)
            zpath = os.path.join(out, s + ".zip")
            total = 0
            with zipfile.ZipFile(zpath, "w") as zf:
                for rel in files:
                    src = os.path.join(sdir, *rel.split("/"))
                    total += add(zf, s + "/" + rel, src)
                    add(bundle, "skills/" + s + "/" + rel, src)
            btotal += total
            bfiles += len(files)
            summary.append((s + ".zip", len(files), total, os.path.getsize(zpath)))
        tools_dir = os.path.dirname(os.path.abspath(__file__))  # the maintainer tools ship in the bundle too
        for f in sorted(os.listdir(tools_dir)):
            if f.endswith((".py", ".md")):
                btotal += add(bundle, "tools/" + f, os.path.join(tools_dir, f))
                bfiles += 1
    summary.append((BUNDLE, bfiles, btotal, os.path.getsize(os.path.join(out, BUNDLE))))

    # 4. Verify: clean paths, and each extracted per-skill zip passes its own preflight.
    failed = []
    for s in skills:
        with zipfile.ZipFile(os.path.join(out, s + ".zip")) as zf:
            names = zf.namelist()
            if any("\\" in n or "__pycache__" in n or not n.startswith(s + "/") for n in names):
                failed.append(s + " (bad paths)")
                continue
            tmp = tempfile.mkdtemp(prefix="pkgcheck_")
            try:
                zf.extractall(tmp)
                ok, text = run_preflight(os.path.join(tmp, s, "scripts", "preflight.py"))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if not ok:
                print("--- extracted %s.zip preflight\n%s" % (s, text))
                failed.append(s)
    if failed:
        print("FAIL extracted zip check: " + ", ".join(failed))
        sys.exit(1)

    print("\nwrote %s" % out)
    print("%-32s %6s %12s %12s" % ("zip", "files", "bytes", "zip bytes"))
    for name, n, total, zsize in summary:
        print("%-32s %6d %12d %12d" % (name, n, total, zsize))
    print("OK every extracted per-skill zip prints READY")


if __name__ == "__main__":
    main()
