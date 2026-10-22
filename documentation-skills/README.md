# Documentation Skills

Canonical repository/root folder: `documentation-skills`.

Five Agent Skills that write documentation, decks, training and communication materials **in the brand of whatever project they run in**. Each skill writes a source file (`deck.json`, `doc.json`, Markdown), builds the output with its own scripts, and refuses to deliver until a lint gate passes.

## Skills

| Skill | Builds | Gate |
|---|---|---|
| `slide-deck` | PowerPoint decks (.pptx): one story, the right visual per slide (native charts, screenshots with callouts, diagrams, big numbers), varied pacing | `lint_deck.py`: story, density, layout, contrast, fonts, colors, orphans |
| `document-builder` | Word and PDF documents: user guides (lean or textbook), technical references, SOPs, manuals, reports, policies, one-page sheets | `lint_doc.py`: structure, contents, bookmarks, embedded fonts, accessibility |
| `material-composer` | Entry point for any material: plans the format and routes it to a renderer; builds fillable PDF forms, HTML e-learning (SCORM 1.2) and Excel trackers itself | `lint_material.py` plus the renderer's gate |
| `training-material-designer` | Training: video scripts with captions, quick starts, job aids, facilitator guides, knowledge checks; designs training decks and pages | `lint_training.py` |
| `github-docs` | Textbook-style setup and user guides as GitHub Markdown in `docs/` for moderately technical users (task finder, chapters with objectives, procedures with results, safe-by-default choices, settings reference, glossary, index) | `lint_docs.py`: format, voice, safe choices, commands, secrets, links |

## Branding comes from the project

No skill carries a brand of its own. `scripts/brand.py` (an identical copy in every skill) resolves the project's brand, and every build and lint uses the same result:

1. An explicit profile: `--brand brand.json`, the source's `meta.brand`, or `$BRAND_PROFILE`.
2. A `brand.json` beside the source or at the project root (`python scripts/brand.py detect --out brand.json` writes one to edit).
3. Detected from the project: design tokens, Tailwind / MUI / Chakra themes, CSS / SCSS / LESS variables, Office templates (.potx, .dotx, .thmx), Android `colors.xml`, the web manifest, logo files (SVG preferred; light-on-dark variants found or knocked out), the LICENSE copyright holder for footers.
4. Neutral defaults: a neutral palette, no logo, no footer.

Missing color roles are derived from the brand's primary color, and any color that fails a WCAG AA text-contrast pair is darkened or lightened (hue kept), with every change reported. `python scripts/brand.py show --source <file>` prints what a build will use.

## Fonts

The skills never set a font of their own. Fonts come from the project (profile, CSS/Tailwind/tokens, Office templates, `@fontsource` packages, font files the project ships, or its UI framework's default). Only when a project names none do the skills fall back to **Inter** (text) and **JetBrains Mono** (code), both SIL Open Font License, bundled in the rendering skills' `assets/fonts/` so text is measured with the real font on any machine.

Layouts are measured from the font files: widths for wrapping and auto-fit, and line spacing and first-line centers from each font's own metrics, so card heights, title bands and marker alignment adapt to the font. Word documents and PDF forms embed the fonts; e-learning packages ship them.

## Requirements

- Python 3.8+ (`python3`, or `python` on Windows).
- `python-pptx` (slide-deck), `python-docx` (document-builder); Pillow and PyMuPDF recommended (logos, font measurement, rendering); `openpyxl` for Excel output.
- For PDFs and visual review: LibreOffice, or on Windows an installed Word / PowerPoint (used read-only through COM).

Each skill starts with `scripts/preflight.py`, which checks its files (size and checksum) and runtimes and prints `READY` or what is missing.

## Install

Copy a skill folder from `skills/` into your agent's skills folder (for Claude Code, `~/.claude/skills/<skill>` or `.claude/skills/<skill>` in a project), or upload a skill's zip where your agent takes skills. Keep the source files (deck.json, doc.json, docs/) inside the project you're documenting, so the brand lookup finds the project.

## Maintaining

`tools/` holds the maintainer tools: `gen_preflight.py` (regenerate every preflight after any edit), `gen_checks.py` (regenerate a skill's `CHECKS.md` index) and `package.py` (build and verify the zips). See `tools/README.md`. Each skill has a self-test in `scripts/test_*.py`.

## Licenses of bundled assets

- Inter and JetBrains Mono: SIL Open Font License 1.1 (license files in `assets/fonts/`).
- Tabler icons: MIT (`assets/icons/LICENSE-tabler.txt`).
