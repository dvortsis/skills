#!/usr/bin/env python3
"""Find the setup facts a guide needs in a project, each with its source (file:line). Standard library only
(PyYAML is used for compose files when installed).

  python3 scripts/discover.py [--project DIR] [--out setup.facts.md] [--json facts.json]

Reads: Unraid Community Applications templates (*.xml with <Container>), docker-compose / compose files, Dockerfiles,
.env.example files, Windows installer scripts (Inno Setup .iss, WiX .wxs, NSIS .nsi), web manifests, and lists the
files most likely to define the in-app settings screen so you read them yourself. Prints a summary, the CONCEPTS
line (entries of references/concepts.md the project involves) and the OPEN line (facts the guide needs that no file
answered: ask the user once). Never guesses a value: a fact without a source is an open question.
"""
import argparse, json, os, re, sys

SKIP = {"node_modules", ".git", "vendor", "dist", "build", "out", ".next", ".venv", "venv", "env", "__pycache__",
        "coverage", "target", "bin", "obj", ".idea", ".vscode", "site-packages", ".cache", ".pytest_cache"}
SECRET = re.compile(r"(?i)(pass(word)?|secret|token|api[_-]?key|private[_-]?key|credential)")
MAX_FILES = 8000


def walk(root):
    n = 0
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for f in sorted(files):
            n += 1
            if n > MAX_FILES:
                return
            yield os.path.join(d, f)


def rel(root, p):
    return os.path.relpath(p, root).replace(os.sep, "/")


def read(p):
    try:
        if os.path.getsize(p) > 2_000_000:
            return ""
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def line_of(text, needle, start=0):
    i = text.find(needle, start)
    return text.count("\n", 0, i) + 1 if i >= 0 else 0


class Facts:
    def __init__(self, root):
        self.root, self.rows, self.concepts, self.settings_sources = root, [], set(), []

    def add(self, kind, name, value, src, line, note="", concepts=()):
        self.rows.append({"kind": kind, "name": name, "value": value, "source": "%s:%d" % (src, line) if line else src, "note": note})
        self.concepts.update(concepts)


# ---------------------------------------------------------------- Unraid templates
def unraid(F, p, text):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return
    if root.tag != "Container":
        return
    r = rel(F.root, p)
    for tag in ("Name", "Repository", "Network", "WebUI", "Support", "Project", "Privileged"):
        el = root.find(tag)
        if el is not None and (el.text or "").strip():
            F.add("unraid", tag, el.text.strip(), r, line_of(text, "<%s>" % tag),
                  concepts={"Network": ["network-modes"], "Privileged": ["network-modes"]}.get(tag, []))
    for cfg in root.findall("Config"):
        a = cfg.attrib
        typ, target = a.get("Type", ""), a.get("Target", "")
        value = (cfg.text or "").strip() or a.get("Default", "")
        name = a.get("Name", target)
        note = "; ".join(x for x in (a.get("Description", "").strip(), "required" if a.get("Required") == "true" else "",
                                     "masked (secret)" if a.get("Mask") == "true" else "", "advanced" if a.get("Display") == "advanced" else "") if x)
        line = line_of(text, 'Name="%s"' % name) or line_of(text, 'Target="%s"' % target)
        if typ == "Port":
            F.add("port", name, "host %s -> container %s/%s" % (value, target, a.get("Mode", "tcp")), r, line, note, ["port-mappings", "tcp-udp"])
        elif typ == "Path":
            F.add("path", name, "host %s -> container %s (%s)" % (value, target, a.get("Mode", "rw")), r, line, note,
                  ["container-rebuilt", "path-mappings", "appdata", "mnt-user-cache"])
        elif typ == "Variable":
            secret = a.get("Mask") == "true" or SECRET.search(target or name)
            F.add("secret" if secret else "variable", name, "%s=%s" % (target, "<masked>" if secret else value), r, line, note,
                  ["api-keys"] if secret else (["puid-pgid"] if target in ("PUID", "PGID") else []))
        elif typ == "Device":
            F.add("device", name, value or target, r, line, note)


# ---------------------------------------------------------------- compose
def yaml_load(text):
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        return mini_yaml(text)
    except Exception:
        return None


def mini_yaml(text):
    """Enough YAML for compose files: nested maps, lists of scalars and of maps, quoted and plain scalars."""
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))

    def scalar(s):
        s = re.sub(r"\s+#.*$", "", s).strip()
        return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'" else s

    def block(i, ind):
        if i < len(lines) and lines[i][1].startswith("- "):
            out = []
            while i < len(lines) and lines[i][0] == ind and lines[i][1].startswith("- "):
                item = lines[i][1][2:]
                if re.match(r"^[\w.-]+\s*:(\s|$)", item) and not item.startswith(("'", '"')):
                    sub = [(ind + 2, item)]
                    j = i + 1
                    while j < len(lines) and lines[j][0] > ind:
                        sub.append(lines[j]); j += 1
                    val, _ = block_from(sub, 0, ind + 2)
                    out.append(val); i = j
                else:
                    out.append(scalar(item)); i += 1
            return out, i
        out = {}
        while i < len(lines) and lines[i][0] == ind:
            m = re.match(r"^([^:]+?)\s*:\s*(.*)$", lines[i][1])
            if not m:
                i += 1; continue
            k, v = scalar(m.group(1)), m.group(2)
            if v and v not in ("|", ">"):
                out[k] = scalar(v); i += 1
            elif i + 1 < len(lines) and lines[i + 1][0] > ind:
                out[k], i = block(i + 1, lines[i + 1][0])
            else:
                out[k] = None; i += 1
        return out, i

    def block_from(sub, i, ind):
        nonlocal lines
        keep = lines
        lines = sub
        try:
            return block(i, ind)
        finally:
            lines = keep
    if not lines:
        return None
    val, _ = block(0, lines[0][0])
    return val


def compose(F, p, text):
    data = yaml_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
        return
    r = rel(F.root, p)
    for svc, s in data["services"].items():
        if not isinstance(s, dict):
            continue
        ln = line_of(text, "%s:" % svc)
        if s.get("image"):
            F.add("compose", "%s image" % svc, str(s["image"]), r, line_of(text, str(s["image"])))
        for port in s.get("ports") or []:
            port = port.get("published", "") if isinstance(port, dict) else str(port)
            bind = "local only" if str(port).startswith("127.0.0.1") else ""
            F.add("port", "%s port" % svc, str(port), r, line_of(text, str(port), 0) or ln, bind, ["port-mappings", "tcp-udp"] + (["zero-address"] if "0.0.0.0" in str(port) else []))
        for vol in s.get("volumes") or []:
            vol = "%s:%s" % (vol.get("source", ""), vol.get("target", "")) if isinstance(vol, dict) else str(vol)
            F.add("path", "%s volume" % svc, vol, r, line_of(text, vol.split(":")[0]) or ln, "", ["container-rebuilt", "path-mappings", "appdata"])
        env = s.get("environment") or {}
        items = env.items() if isinstance(env, dict) else [(e.split("=", 1) + [""])[:2] for e in env if isinstance(e, str)]
        for k, v in items:
            secret = bool(SECRET.search(str(k)))
            F.add("secret" if secret else "variable", "%s %s" % (svc, k), "<masked>" if secret else str(v), r, line_of(text, str(k)) or ln, "",
                  ["api-keys"] if secret else (["puid-pgid"] if k in ("PUID", "PGID") else []))
        if s.get("network_mode"):
            F.add("network", "%s network_mode" % svc, str(s["network_mode"]), r, line_of(text, "network_mode"), "", ["network-modes"])
        if s.get("restart"):
            F.add("compose", "%s restart" % svc, str(s["restart"]), r, line_of(text, "restart"))


def dockerfile(F, p, text):
    r = rel(F.root, p)
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"(?i)^\s*(EXPOSE|VOLUME|ENV|HEALTHCHECK)\s+(.+)$", line)
        if not m:
            continue
        kw, val = m.group(1).upper(), m.group(2).strip()
        if kw == "EXPOSE":
            F.add("port", "image exposes", val, r, i, "", ["port-mappings", "tcp-udp"])
        elif kw == "VOLUME":
            F.add("path", "image volume", val, r, i, "data written here must be mapped", ["container-rebuilt", "path-mappings"])
        elif kw == "ENV":
            k = re.split(r"[=\s]", val, 1)[0]
            F.add("secret" if SECRET.search(k) else "variable", "image env " + k, "<masked>" if SECRET.search(k) else val, r, i)
        else:
            F.add("health", "healthcheck", val[:80], r, i)


def env_example(F, p, text):
    r = rel(F.root, p)
    comment = ""
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("#"):
            comment = s.lstrip("# ").strip(); continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.*)$", s)
        if m:
            secret = bool(SECRET.search(m.group(1)))
            F.add("secret" if secret else "variable", m.group(1), "<masked>" if secret else m.group(2), r, i, comment,
                  ["api-keys"] if secret else (["zero-address"] if "0.0.0.0" in m.group(2) else []))
        comment = ""


def installer(F, p, text):
    r = rel(F.root, p)
    ext = os.path.splitext(p)[1].lower()
    F.concepts.update(["smartscreen", "uac"])
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if re.search(r"(?i)advfirewall\s+firewall\s+add\s+rule|FirewallException|nsisFirewall|New-NetFirewallRule", s):
            port = re.search(r"(?i)(?:localport=|Port=\"?)(\d+)", s)
            proto = re.search(r"(?i)protocol=\"?(tcp|udp)", s)
            prof = re.search(r"(?i)profile=\"?(\w+)", s)
            F.add("firewall", "installer firewall rule", "port %s/%s profile %s" % (port.group(1) if port else "?", proto.group(1) if proto else "?",
                                                                                  prof.group(1) if prof else "not set (applies to all)"), r, i, "", ["firewall"])
        if re.search(r"(?i)\bsc(\.exe)?\b[^\n]*\bcreate\b|ServiceInstall|SimpleSC::InstallService|New-Service|nssm(\.exe)?\b[^\n]*\binstall\b", s):
            F.add("service", "installer installs a service", s[:120], r, i, "", ["services"])
        m = re.match(r"(?i)^(AppName|AppVersion|DefaultDirName|PrivilegesRequired|AppPublisher)\s*=\s*(.+)$", s)
        if m and ext == ".iss":
            F.add("installer", m.group(1), m.group(2), r, i)
        if re.search(r"(?i)ProgramData|%PROGRAMDATA%|\{commonappdata\}|CommonAppDataFolder", s):
            F.add("path", "installer data folder", s[:120], r, i, "candidate data folder for the Defender exclusion", ["realtime-scan"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=os.getcwd()); ap.add_argument("--out"); ap.add_argument("--json")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.project)
    F = Facts(root)
    text_mentions = {"dht": [], "upnp": [], "natpmp": [], "vpn": [], "0.0.0.0": []}
    for p in walk(root):
        b = os.path.basename(p).lower()
        ext = os.path.splitext(b)[1]
        if ext in (".png", ".jpg", ".gif", ".ico", ".zip", ".exe", ".dll", ".so", ".woff", ".woff2", ".ttf", ".pdf", ".lock"):
            continue
        text = read(p)
        if not text:
            continue
        if ext == ".xml" and "<Container" in text[:4000]:
            unraid(F, p, text)
        elif re.fullmatch(r"(docker-)?compose(\.[\w-]+)?\.ya?ml", b):
            compose(F, p, text)
        elif b == "dockerfile" or b.startswith("dockerfile.") or b.endswith(".dockerfile"):
            dockerfile(F, p, text)
        elif re.fullmatch(r"\.env\.(example|sample|template|dist)|env\.example|example\.env", b):
            env_example(F, p, text)
        elif ext in (".iss", ".wxs", ".nsi", ".nsh"):
            installer(F, p, text)
        if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".go", ".rs", ".cs", ".java", ".kt", ".json", ".yaml", ".yml", ".toml", ".ini"):
            r = rel(root, p)
            if re.search(r"(?i)setting|preference|config|options", r) and not re.search(r"(?i)test|spec|mock|fixture|\.d\.ts$|tsconfig|eslint|prettier|babel|webpack|vite\.config|jest|package(-lock)?\.json", r):
                F.settings_sources.append(r)
            low = text.lower()
            for k in text_mentions:
                if k in low and len(text_mentions[k]) < 3:
                    text_mentions[k].append("%s:%d" % (r, line_of(low, k)))
    concept_for = {"dht": "dht", "upnp": "upnp", "natpmp": "upnp", "vpn": "vpn", "0.0.0.0": "zero-address"}
    for k, where in text_mentions.items():
        if where:
            F.concepts.add(concept_for[k])
            F.add("mention", k, "mentioned in code", where[0], 0, ", ".join(where[1:]))
    if any(r["kind"] in ("port", "path") for r in F.rows):
        F.concepts.update(["web-ui-offline", "strong-passwords", "backups", "updates", "ip-localhost"])
    if any(r["kind"] == "secret" for r in F.rows):
        F.concepts.update(["api-keys", "sharing-logs"])
    open_q = []
    if not any(r["kind"] == "port" for r in F.rows):
        open_q.append("which port the web UI uses")
    if not any(r["kind"] == "path" for r in F.rows):
        open_q.append("where the app keeps its data (the folder to map and back up)")
    if not F.settings_sources:
        open_q.append("where the settings screen is defined (or screenshots of it)")
    lines = ["# Setup facts", "", "Generated by discover.py from %s. Every guide fact needs a row here or a cited source." % os.path.basename(root), "",
             "| Kind | Name | Value | Source | Note |", "|---|---|---|---|---|"]
    for row in F.rows:
        lines.append("| %s | %s | %s | %s | %s |" % tuple(str(row[k]).replace("|", "\\|") for k in ("kind", "name", "value", "source", "note")))
    lines += ["", "## Settings screen sources to read", ""] + (["- %s" % s for s in F.settings_sources[:40]] or ["- none found"])
    lines += ["", "## Concepts to explain (references/concepts.md)", "", ", ".join(sorted(F.concepts)) or "none", "",
              "## Open questions", ""] + (["- " + q for q in open_q] or ["- none"])
    md = "\n".join(lines) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"facts": F.rows, "settings_sources": F.settings_sources, "concepts": sorted(F.concepts), "open": open_q}, fh, indent=1)
    kinds = {}
    for row in F.rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    print("DISCOVER: %d facts (%s) in %s" % (len(F.rows), ", ".join("%s %d" % kv for kv in sorted(kinds.items())) or "none", root))
    print("SETTINGS SOURCES: %d file(s)%s" % (len(F.settings_sources), (": " + ", ".join(F.settings_sources[:6])) if F.settings_sources else ""))
    print("CONCEPTS: " + (", ".join(sorted(F.concepts)) or "none"))
    print("OPEN: " + ("; ".join(open_q) if open_q else "none"))
    if a.out:
        print("wrote " + a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
