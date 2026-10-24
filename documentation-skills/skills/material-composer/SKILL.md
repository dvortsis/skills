---
name: material-composer
description: Entry point for any document, training or communication material in any format, including formats with no template. Fits the request to one of eight families, borrows the nearest catalog format's sections and the project's own brand (logo, colors, fonts and footer detected from the project it runs in), picks the renderer (document, deck, page, training, or its own form and e-learning builders) and runs one gate. Use for quick reference cards, job aids, quick starts, checklists, one-pagers, status reports, change and communication kits, announcement emails, talking points, FAQs, instructor-led decks with facilitator guides, e-learning, video scripts, surveys, follow-up evaluations, intake and sign-off forms, policies, release notes, RACI charts, agendas, metric definitions, data dictionaries, Excel trackers and similar ("make a ... for ..."). Also use when a developer asks to add, change, rename or retire a format type or move a material to another format.
version: 2.0.0
---

# Material Composer

You plan, borrow, write the source, build with the named renderer and gate. Never hand-build Word, PDF, HTML or PowerPoint. Commands below use `python3`; use `python` where that is the interpreter's name (Windows).

## 0. Preflight (first, before any other work)
Run `scripts/preflight.py` from this skill's folder (the folder containing this SKILL.md). On `READY`, continue. If it fails or is missing, stop and say once: "The material-composer skill loaded without its supporting files. Please attach `material-composer.zip` to this chat, or ask the agent owner to re-upload it as a .zip." When the zip is attached, extract it, run preflight there, and run every command from that folder. Never hand-write, approximate or skip a script. Then run `scripts/catalog_tool.py drift`; on `FAIL [OVERLAY_DRIFT]` say once: "The installed format catalog and your saved catalog changes differ (both versions are named above). Please ask the agent owner to repackage material-composer." and continue with the installed catalog.

## 0b. Brand
`python3 scripts/brand.py show --source <source>` (before the source exists, `--project <project folder>`). It prints the BRAND line, the colors, fonts, logo and footer every build of that source will use: an explicit `--brand brand.json` or the source's `meta.brand`, else a `brand.json` beside the source or at the project root, else what it detects in the project (design tokens, Tailwind/CSS themes, Office templates, logo files, LICENSE owner), else neutral defaults. Put the BRAND line in your reply. When it says `neutral defaults`, ask once whether the user has a logo, brand colors or a brand.json (`scripts/brand.py detect --out brand.json` writes one to edit), then continue either way; never invent a logo or footer. Every builder and gate takes `--brand` to override the project brand.

## Workflow
1. **Frame.** Audience, subject, format and output (PDF, Word, slides, HTML, email, chat). Infer what you can; ask once, in one line, for the rest. Asked what you can make: `python3 scripts/catalog_tool.py card --out card.doc.json [--extra agent.json]`, then build it as a doc-sheet.
2. **Plan.** `python3 scripts/plan_material.py "<format as asked>" --audience "..." --subject "..." [--output pdf] --out <name>.plan.json`. It prints FORMAT, BUILD, SECTIONS, LIMITS, TONE and GATES. When FORMAT says "borrowed from X", tell the user in one line and put `derived_from: X` in the source (DERIVED_NOTE). Every plan prints MATCH; on `MATCH: low` it plans a neutral outline (Purpose, Key Points, What to Do, Get Help): say so, or rerun with `--ask` and ask its one QUESTION. `--audience-profile` sets tone, limits and terms (business default; leaders, technical, clinical-partners, physicians, frontline; an audience term set such as clinical-partners applies only when the project's terminology file defines it). Add `--translation-ready` only when translation is requested: 75 percent word budget; after writing the source run `scripts/translation_export.py <source>` and name the written translation process the plan prints (never machine translation).
3. **Facts.** Only the request, attachments and sources found with connected search tools (if any) or the sources the user names. Unknown numbers, dates, names or screens become open questions, never placeholders. Examples use roles, never real people; no PHI.
4. **Borrow.** Read `references/house-conventions.md` once and only your family's section of `references/families.md`. Copy the plan's `exemplar` (if any) or the renderer's example, then replace every value. Keep the plan's section titles, order and limits.
5. **Build** with the plan's BUILD line:

| Renderer | Source you write | Build |
|---|---|---|
| doc-sheet | doc.json, `meta.layout: "sheet"`, `meta.doc_type` = plan doc_type | document-builder `build_doc.py` |
| doc-long | doc.json | document-builder (textbook profile for guides and manuals) |
| deck | deck.json | slide-deck |
| training-md | training .md (`output: pdf` → `md_to_sheet.py`, then build_doc) | training-material-designer |
| md | .md with front matter (format, title, audience, sources, subject for emails) | none; send as .email or .message when asked |
| github-docs | `docs/*.md` pages in the project repository (textbook setup or user guide on GitHub, with screenshots or stamped illustrations) | github-docs skill (`docs_tool.py`, `lint_docs.py`); hand over when the request is a docs folder or GitHub guide |
| form | form.json | `scripts/build_form.py` (tagged fillable PDF + .xlsx + .msforms.csv; say to paste it into a new Microsoft Form, never that it imports) |
| module | module.json | `scripts/build_module.py` (HTML + storyboard; `--scorm` adds a SCORM 1.2 zip for your LMS, which resumes on the learner's last screen with their answers; pilot every package in the LMS's test area first) |
| xlsx | sheet.json (Tracker; the data-dictionary and raci plans add it on an ALSO line) | `scripts/build_sheet.py` (one named table, Status dropdown from the Lists tab, Definitions tab; `--check` reopens it) |

6. **Gate** until 0 failed: `python3 scripts/lint_material.py <file.md|doc.json> --plan <plan>`, plus the renderer's own gate. Kits: `--kit kit.json` (needs an adoption-measures piece in the reinforcement stage: KIT_ADOPTION). Instructor-led pairs: `--ilt guide.md --deck deck.json`. Forms and modules gate before they build. Communication formats also run executive-communications check_comms when that optional skill is installed (COMMS_CHECK; pass `--source` and `--facts` when the draft has them; not installed: a not-run warning, never a FAIL). When a documentation overlay skill is attached, also run its gate and set check.
7. **Look.** Render every page or screen into a new folder; view contact sheets, full size only where flagged; fix and rebuild. Report "visual review: N pages, M fixed", or "not run (reason)" when preflight printed `WARN render: not available` or you can't view images.
8. **Deliver.** Link each file with one line on where it goes, then the BRAND line, `CHECKS: lint_material 0 failed; <renderer gate> 0 failed; visual review ...`, any borrowed format, and at most three open questions.

## Changing Formats
* **This request only** (anyone): `plan_material.py` flags `--add-section "Title@After"`, `--drop-section`, `--rename-section "Old=New"`, `--set words=300`, `--output`, `--family`.
* **Change a material's format** ("turn this job aid into a quick reference card"): `plan_material.py --retarget old.plan.json --as "<new format>"`; reuse the carry-over sections, write the new ones, drop the rest.
* **Lasting changes to format types** (the developer or agent owner only): `scripts/catalog_tool.py` (`references/developer-commands.md`) writes the overlay, validates it (CATALOG_SCHEMA) and logs it. Skill files are read-only after install, so deliver the updated `assets/catalog/overlay.json` and say: "Repackage the skill with this file (or attach it to a chat) to keep the change." Different agents may keep different overlays (`--overlay` or `$MATERIAL_OVERLAY`).

## Never
Invented facts, dates or numbers; placeholders; generic openers ("Exciting news!", "This document will"); filler words; text shrunk below 9 pt body or 8 pt figure text to fit a page; e-learning with more than 4 screens in a row without interaction; trivia quizzes; double-barreled or leading survey items and mixed scales; forms that collect PHI; one kit using two names for the same thing; a borrowed format delivered without saying what it borrowed; colors outside the project brand palette, or the alert color except for warnings and misses; an invented logo or copyright line; delivering with a FAIL.
