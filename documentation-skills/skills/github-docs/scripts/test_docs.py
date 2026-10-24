#!/usr/bin/env python3
"""Self-test for the github-docs skill: the example guide passes the strict gate and is in sync, each known-bad change
fails with its code, sync renumbers and fixes links, new scaffolds without overwriting, and discover reads the
example project. Run after any change to the scripts, templates or example.

  python3 scripts/test_docs.py
Prints one ok/FAIL line per case and `SELF-TEST: <passed>/<total> passed`; exits 1 on any failure."""
import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLE = os.path.join(ROOT, "assets", "example", "project")
PY = sys.executable
R = []


def ok(cond, label, detail=""):
    R.append(bool(cond))
    print(("ok   " if cond else "FAIL ") + label + ("" if cond or not detail else "\n     " + detail[-600:].replace("\n", "\n     ")))


def run(*args, env=None):
    r = subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8", env=env)
    return r.returncode, r.stdout + r.stderr


def codes(out, level="FAIL"):
    return set(re.findall(r"^%s \[([A-Z0-9_]+)\]" % level, out, re.M))


def lint(docs, *extra):
    return run(os.path.join(HERE, "lint_docs.py"), docs, *extra)


def copy_example(tmp, name):
    dst = os.path.join(tmp, name)
    shutil.copytree(EXAMPLE, dst)
    return dst, os.path.join(dst, "docs")


def edit(docs, page, old, new, count=1):
    p = os.path.join(docs, page)
    s = open(p, encoding="utf-8").read()
    if old not in s:
        raise AssertionError("mutation target missing in %s: %r" % (page, old))
    open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, count))


MUTATIONS = [  # (code, page, old, new)
    ("PLACEHOLDER", "03-set-up-beacon.md", "Open **Settings** > **Network**.", "WRITE: the network page. Open **Settings** > **Network**."),
    ("VOICE_PADDING", "01-before-you-start.md", "All three methods run the same Beacon.", "Don't worry, all three methods run the same Beacon."),
    ("COMMAND_WHERE", "05-troubleshooting.md", "   In the Unraid terminal, paste:\n", "   Then:\n"),
    ("CODE_LANG", "05-troubleshooting.md", "```bash", "```"),
    ("CHOICE_RECOMMENDED", "01-before-you-start.md", "**Unraid app catalog (recommended)**", "**Unraid app catalog**"),
    ("SETTING_RECOMMENDED", "02-install-beacon.md", "**Recommended:** `6990`, protocol UDP.\n", ""),
    ("UNSAFE_ALTERNATIVE", "02-install-beacon.md", "> Don't check **Public networks**. Anyone on a café or airport network could reach Beacon. Keep it on **Private networks** only.",
     "> Don't check **Public networks**. Anyone on a café or airport network could reach Beacon."),
    ("OBJECTIVES", "03-set-up-beacon.md", "> [!NOTE]\n> **What you will learn**", "> [!NOTE]\n> **Before this chapter**"),
    ("OBJECTIVE_VERB", "01-before-you-start.md", "> - Choose the install method that fits the device you have.", "> - Understand the install methods."),
    ("TAKEAWAYS", "04-keep-beacon-safe.md", "> **Key takeaways**", "> **Summary**"),
    ("ANSWERS", "appendix-a-answers.md", "2. Off. Add a port forward by hand only when Chapter 5 says you need one.\n", ""),
    ("LINK_BROKEN", "03-set-up-beacon.md", "Unraid shows it at the top left", "[Unraid](02-install-beacon.md#no-such-heading) shows it at the top left"),
    ("SECRET_LITERAL", "05-troubleshooting.md", "docker logs beacon --tail 50", "BEACON_API_KEY=9f8e7d6c5b4a39281706f5e4 docker logs beacon --tail 50"),
    ("SECURITY_CHAPTER", "04-keep-beacon-safe.md", "# Chapter 4: Keep Beacon safe", "# Chapter 4: Remote access"),
    ("TROUBLESHOOTING", "05-troubleshooting.md", "| Problem | Likely cause | Fix |", "| Problem | Cause | Fix |"),
    ("ALERT_KIND", "02-install-beacon.md", "> [!CAUTION]", "> [!DANGER]"),
    ("PROCEDURE_RESULT", "04-keep-beacon-safe.md", "   **Result:** The old key stops working right away.", "   The old key stops working right away."),
    ("NUMBERING", "02-install-beacon.md", "## 2.1 Install on Unraid", "## 2.7 Install on Unraid"),
    ("SYNC_STALE", "revisions.md", "[← Glossary](glossary.md)", "[Back](glossary.md)"),
    ("TASK_FINDER", "README.md", "| If you want to | Go to |", "| Task | Where |"),
    ("IMG_MISSING", "01-before-you-start.md", "Beacon uses two folders:", "![Beacon shows its two folders here](images/missing.png)\n\nBeacon uses two folders:"),
    ("IMG_ALT", "01-before-you-start.md", "Beacon uses two folders:", "![Folders](images/missing.png)\n\nBeacon uses two folders:"),
    ("FIGURE_CAPTION", "02-install-beacon.md", "*Figure 2.1: Unraid template with the ports and mapped folders filled in. Illustration, not a live screenshot.*\n", ""),
    ("FIGURE_SOURCE", "02-install-beacon.md", "images/unraid-template-illustration.svg", "images/stock-template.svg"),
    ("ILLUSTRATION_LABEL", "02-install-beacon.md", "*Figure 2.1: Unraid template with the ports and mapped folders filled in. Illustration, not a live screenshot.*",
     "*Figure 2.1: Unraid template with the ports and mapped folders filled in.*"),
    ("GLOSSARY_ORDER", "glossary.md", "## Container", "## Zone"),
    ("H1_ONE", "revisions.md", "| Version | Date | Change |", "# Second title\n\n| Version | Date | Change |"),
]
WARN_MUTATIONS = [
    ("BACKGROUND_LONG", "01-before-you-start.md", "All three methods run the same Beacon.",
     "All three methods run the same Beacon. " + " ".join(["Each method installs the same program with the same settings page."] * 8)),
    ("SENTENCE_LONG", "01-before-you-start.md", "All three methods run the same Beacon.",
     "All three methods run the same Beacon on every device you can think of, from the smallest home server up to the largest office machine in the building."),
    ("GLOSSARY_LINK", "02-install-beacon.md", "the [container](glossary.md#container) side stays", "the container side stays"),
    ("READING_PATHS", "README.md", "**Reading paths.** First-time installers read Chapters 1 to 4 in order. Returning readers use the table above to jump to a setting, backup or fix.\n", ""),
]


def main():
    tmp = tempfile.mkdtemp(prefix="ghdocs_")
    os.environ["BRAND_PROJECT"] = tmp
    try:
        # 1. the example
        rc, out = lint(os.path.join(EXAMPLE, "docs"), "--strict")
        ok(rc == 0 and "0 failed, 0 warnings" in out, "example guide passes the strict gate", out)
        rc, out = run(os.path.join(HERE, "docs_tool.py"), "sync", os.path.join(EXAMPLE, "docs"), "--check")
        ok(rc == 0 and "up to date" in out, "example guide is in sync (numbering, contents, navigation, index)", out)
        # 2. every known-bad change fails with its code
        for k, (code, page, old, new) in enumerate(MUTATIONS):
            _proj, docs = copy_example(tmp, "m%02d" % k)
            edit(docs, page, old, new)
            rc, out = lint(docs)
            ok(rc == 1 and code in codes(out), "%s fails (%s)" % (code, page), out)
        for k, (code, page, old, new) in enumerate(WARN_MUTATIONS):
            _proj, docs = copy_example(tmp, "w%02d" % k)
            edit(docs, page, old, new)
            rc, out = lint(docs)
            ok(code in codes(out, "WARN") and code not in codes(out), "%s warns, doesn't fail (%s)" % (code, page), out)
            rc, out = lint(docs, "--strict")
            ok(rc == 1, "%s fails under --strict" % code, out)
        # 3. sync renumbers and fixes links (and figure captions)
        _proj, docs = copy_example(tmp, "sync")
        edit(docs, "02-install-beacon.md", "## 2.1 Install on Unraid", "## Pick a method\n\nStart with the method from Chapter 1.\n\n## 2.1 Install on Unraid")
        edit(docs, "02-install-beacon.md", "*Figure 2.1: Unraid template", "*Figure 9.9: Unraid template")
        edit(docs, "03-set-up-beacon.md", "Unraid shows it at the top left", "See [the template fields](02-install-beacon.md#22-template-fields). Unraid shows it at the top left")
        rc, out = run(os.path.join(HERE, "docs_tool.py"), "sync", docs)
        ch3 = open(os.path.join(docs, "03-set-up-beacon.md"), encoding="utf-8").read()
        ch2 = open(os.path.join(docs, "02-install-beacon.md"), encoding="utf-8").read()
        ok("## 2.1 Pick a method" in ch2 and "## 2.3 Template fields" in ch2 and "02-install-beacon.md#23-template-fields" in ch3
           and "*Figure 2.1: Unraid template" in ch2,
           "sync renumbers sections, figure captions and links to the renumbered heading", out)
        rc, out = lint(docs)
        ok(rc == 0, "the renumbered guide passes the gate", out)
        home = open(os.path.join(docs, "README.md"), encoding="utf-8").read()
        ok("[2.1 Pick a method](02-install-beacon.md#21-pick-a-method)" in home, "sync rewrites the contents", home[:400])
        # 3b. FIGURE_NONE gate (warns when only SHOTLIST.md exists, fails when neither figures nor SHOTLIST.md exist)
        _proj, fdocs = copy_example(tmp, "fignone")
        for pg in ("02-install-beacon.md", "03-set-up-beacon.md"):
            p = os.path.join(fdocs, pg)
            body = re.sub(r"\n!\[[^\]]+\]\(images/[^)]+\)\n\*Figure [^\n]+\*\n", "\n", open(p, encoding="utf-8").read())
            open(p, "w", encoding="utf-8", newline="\n").write(body)
        rc, out = lint(fdocs)
        ok(rc == 0 and "FIGURE_NONE" in codes(out, "WARN"), "FIGURE_NONE warns when procedures quote UI labels and only SHOTLIST.md is present", out)
        rc_s, out_s = lint(fdocs, "--strict")
        ok(rc_s == 1 and "FIGURE_NONE" in codes(out_s, "WARN"), "FIGURE_NONE warning fails under --strict", out_s)
        os.remove(os.path.join(fdocs, "images", "SHOTLIST.md"))
        edit(fdocs, "README.md", " see [the shot list](images/SHOTLIST.md) for the live captures that replace them.", "")
        rc, out = lint(fdocs)
        ok(rc == 1 and "FIGURE_NONE" in codes(out), "FIGURE_NONE fails when procedures quote UI labels and neither figures nor SHOTLIST.md exist", out)
        # 4. new scaffolds, adds the logo and SHOTLIST.md, never overwrites; figure builds a stamped SVG illustration
        proj = os.path.join(tmp, "newproj"); os.makedirs(os.path.join(proj, "public"))
        open(os.path.join(proj, "package.json"), "w").write('{"name": "harbor-notes"}')
        open(os.path.join(proj, "public", "logo.svg"), "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><rect width="200" height="60" fill="#0B7A75"/></svg>')
        env = dict(os.environ, BRAND_PROJECT=proj)
        rc, out = run(os.path.join(HERE, "docs_tool.py"), "new", os.path.join(proj, "docs"), "--title", "Harbor Notes setup guide", "--app", "Harbor Notes",
                      "--chapters", "Before you start;Install Harbor Notes;Keep Harbor Notes safe;Troubleshooting", "--project", proj, env=env)
        names = sorted(os.listdir(os.path.join(proj, "docs"))) if os.path.isdir(os.path.join(proj, "docs")) else []
        want = ["01-before-you-start.md", "02-install-harbor-notes.md", "03-keep-harbor-notes-safe.md", "04-troubleshooting.md", "README.md",
                "appendix-a-answers.md", "appendix-b-settings-reference.md", "glossary.md", "images", "index.md", "revisions.md"]
        ok(rc == 0 and names == want, "new writes the home page, 4 chapters, appendices, glossary, revisions and index", out + str(names))
        home = open(os.path.join(proj, "docs", "README.md"), encoding="utf-8").read() if names else ""
        ok('<img src="../public/logo.svg" alt="Harbor Notes logo"' in home and os.path.isfile(os.path.join(proj, "docs", "images", "SHOTLIST.md")),
           "new puts the project logo on the home page and scaffolds images/SHOTLIST.md", home[:300])
        fig_out = os.path.join(proj, "docs", "images", "settings-illustration.svg")
        rc_f, out_f = run(os.path.join(HERE, "docs_tool.py"), "figure", fig_out, "--title", "Harbor Notes — Settings", "--source", "package.json:1",
                          "--field", "Port=8080|Recommended", "--action", "Save", "--project", proj, env=env)
        svg_body = open(fig_out, encoding="utf-8").read() if os.path.isfile(fig_out) else ""
        ok(rc_f == 0 and "Illustration, not a live screenshot" in svg_body and "Source: package.json:1" in svg_body,
           "docs_tool.py figure writes a stamped, source-gated SVG illustration", out_f)
        rc, out = lint(os.path.join(proj, "docs"))
        ok(rc == 1 and "PLACEHOLDER" in codes(out) and "Traceback" not in out, "a fresh scaffold fails PLACEHOLDER until written", out)
        rc, out = run(os.path.join(HERE, "docs_tool.py"), "new", os.path.join(proj, "docs"), "--title", "X", "--app", "X", "--chapters", "A;B", env=env)
        ok(rc != 0 and "never overwrites" in out, "new refuses to overwrite an existing guide", out)
        # 5. discover reads the example project
        jf = os.path.join(tmp, "facts.json")
        rc, out = run(os.path.join(HERE, "discover.py"), "--project", EXAMPLE, "--json", jf)
        facts = json.load(open(jf, encoding="utf-8")) if os.path.isfile(jf) else {"facts": [], "concepts": []}
        kinds = {}
        for f in facts["facts"]:
            kinds.setdefault(f["kind"], []).append(f)
        ok(len(kinds.get("port", [])) >= 4 and any("6990/udp" in f["value"] for f in kinds["port"]), "discover: Unraid and compose ports with protocol", out)
        ok(any(f["source"].startswith("unraid/beacon.xml:") for f in kinds.get("path", [])), "discover: template paths cite file:line", str(kinds.get("path")))
        ok(all(f["value"].endswith("<masked>") for f in kinds.get("secret", [])) and len(kinds.get("secret", [])) == 2, "discover: secrets are masked, never printed", str(kinds.get("secret")))
        ok(any("profile private" in f["value"] for f in kinds.get("firewall", [])) and kinds.get("service"), "discover: installer firewall rules and service", out)
        ids = set(re.findall(r"`([a-z0-9-]+)`$", open(os.path.join(ROOT, "references", "concepts.md"), encoding="utf-8").read(), re.M))
        src = open(os.path.join(HERE, "discover.py"), encoding="utf-8").read()
        used = set(re.findall(r"\"([a-z]+(?:-[a-z]+)*)\"", "\n".join(re.findall(r"(?:concepts=|concept_for = |F\.concepts\.update\(|\[)\[?([^\]\n]*)", src))))
        used &= {u for u in used if "-" in u or u in ("appdata", "dht", "upnp", "vpn", "firewall", "services", "smartscreen", "uac", "updates", "backups", "defender")}
        ok(set(facts["concepts"]) <= ids and used <= ids, "every concept id discover emits has an entry in references/concepts.md", str(sorted((set(facts["concepts"]) | used) - ids)))
        # 6. packaging hygiene
        bad = []
        for d, _dirs, files in os.walk(ROOT):
            if "__pycache__" in d:
                continue
            for f in files:
                try:
                    open(os.path.join(d, f), "rb").read().decode("utf-8")
                except UnicodeDecodeError:
                    bad.append(f)
        ok(not bad, "every packaged file is UTF-8 text", str(bad))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = sum(R)
    print("SELF-TEST: %d/%d passed" % (n, len(R)))
    return 0 if n == len(R) else 1


if __name__ == "__main__":
    sys.exit(main())
