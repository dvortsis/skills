# Developer tools

Run from the package root (the folder that holds `skills/` and `tools/`). Python 3.8+, no extra modules. Works on Windows and Linux.

| Tool | What it does |
|---|---|
| `tools/gen_preflight.py` | Regenerates each skill's `scripts/preflight.py`: the list of every packaged file with its size and sha256[:12], plus the skill's runtime needs (the `SETTINGS` table at the top of the tool). Name and version come from `SKILL.md` frontmatter. |
| `tools/package.py` | Regenerates the preflights, runs each one (stops on NOT READY or CHANGED), then writes `<skill>.zip` per skill and `documentation-skills.zip` (`skills/<skill>/...` plus these tools), extracts each skill zip, reruns its preflight and prints a summary. |
| `tools/gen_checks.py` | Regenerates a skill's `CHECKS.md` from the `# check: CODE LEVEL` markers in its scripts: `python tools/gen_checks.py skills/slide-deck slide-deck skills/slide-deck/CHECKS.md`. Run it after editing a gate script, then rerun gen_preflight. (github-docs keeps a hand-written CHECKS.md.) |

## Shared files
These ship as identical copies; edit one, copy it to the others, and the self-tests check they match:
`scripts/brand.py` and `scripts/test_brand.py` (all five skills), `scripts/plain_language.py` and
`references/terminology.json` (all but github-docs), `scripts/iconlib.py` and `scripts/visual_batch.py` (slide-deck,
document-builder), `scripts/text_rules.py` (slide-deck, material-composer).

```
python tools/gen_preflight.py                     # all skills
python tools/gen_preflight.py slide-deck          # one skill
python tools/gen_preflight.py --check             # exit 1 if any preflight is out of date
python tools/package.py --check                   # same check; use before committing
python tools/package.py --out dist                # build all zips into dist/
```

Every edit to any file in a skill (including `SKILL.md`) changes its hash, so **rerun `python tools/gen_preflight.py` after every edit**, or the installed skill reports `CHANGED`. Never edit `preflight.py` by hand. To change a skill's required or optional Python modules, LibreOffice or Node needs, edit `SETTINGS` in `gen_preflight.py` and regenerate.

Not packaged or hashed: `scripts/preflight.py` itself, `__pycache__`, `*.pyc`, `.DS_Store`, and render output folders (`render`, `renders`, `*_render`, ...). Each skill's `SKILL.md` `name` must equal its folder name, because the preflight tells users to attach `<name>.zip`; `package.py` refuses to build otherwise.

Both tools take `--root DIR` to work on a copy of the package instead of the folder above `tools/`.
