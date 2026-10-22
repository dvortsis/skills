# Changelog

## Project-branded release

- Removed all branding of the organization the package was first written for: logos, the PowerPoint master, palette, display font, house terminology, internal tool names and footers.
- Added `scripts/brand.py`: resolves logo, colors, fonts and footer from the project the skills run in, derives missing color roles and fixes text contrast to WCAG AA. Identical copy in every skill.
- Slide masters are generated at build time from the brand (`slide-deck/scripts/master.py`); no template file ships.
- Fonts come from the project; Inter and JetBrains Mono (SIL OFL) are bundled as the fallback. Layout spacing, auto-fit and alignment are measured from the font files' own metrics. Word documents embed their fonts; PDF forms and e-learning packages carry them.
- Color tokens renamed to roles (primary, dark, secondary, alert, ...); older names (blue, navy, ...) are still accepted.
- The builder now avoids one-word last lines in labels, subtitles and takeaways as well as titles, using the same rule as the lint; parallel card titles step down together to stay on one line.
- Skill folders renamed: `slide-deck`, `document-builder`, `material-composer` (training-material-designer unchanged).
- New skill: `github-docs`, textbook-style setup guides in GitHub Markdown for moderately technical users, with project fact discovery (`discover.py`), scaffolding and sync (`docs_tool.py`) and a format and voice gate (`lint_docs.py`).
- Rendering and PDF export also work through an installed PowerPoint or Word on Windows when LibreOffice is absent.
- Preflights no longer search the whole disk; maintainer tools (`tools/`) regenerate preflights and checks indexes and build the zips.
- Fixed: text extracted from PDF forms showed wrong characters for digits with some fonts; anatomy zone text was measured at the wrong width; paired-card alignment checks depended on rounding; unclosed files on Windows.
