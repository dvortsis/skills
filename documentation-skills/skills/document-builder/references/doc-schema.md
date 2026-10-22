# doc.json schema

```
meta: title, subtitle?, doc_type, audience, purpose, owner, version, date, classification? (default "Internal use only"),
      sources [..] (required), doc_label? (cover label), page_break_level? (1 default: each top-level section starts a page; 0: sections run on,
      for guides with many short sections; replaces h1_new_page, still read), toc_levels? (1-3, default 2; the contents runs to as many pages
      as it needs), design? ("standard" default, or "branded": dark cover band, no page header, secondary-color rule under chapter titles),
      brand? (path to a brand profile, relative to doc.json; default: brand.json beside doc.json or at the project root,
      then the project's own theme files; see the Brand section below), shotlist? (path to the shot list while screenshots are pending), appendix_icons? (true: Glossary, Revision History, Sources
      and Index get icons too), first_release? (true: a first release; no What's New section),
      origination_date? (required for policy, META_MISSING; printed on the cover as Origination Date),
      profile? ("lean" or "textbook"; guide profiles below),
      owner_role?, last_reviewed?, next_review? (REVIEW_DATE warns when next_review is missing; shown as an Owner Role | Last Reviewed |
      Next Review table above the revisions, and in every sheet footer), latest_url? (https://; sheets print "Printed copies may be out
      of date. Latest version: <latest_url>"; without it the footer keeps "Printed copies may be out of date.")
sections: [{title, icon?, orientation?, objectives?: [..], blocks?: [...], sections?: [... up to 3 levels], takeaways?: [..]}]   icon = bundled Tabler name, shown before the heading
          orientation: "landscape" (top level only) prints that section on landscape pages, 9.0 in text width, for wide figures and tables; the next section returns to portrait. Figure width_in may not exceed the section's text width (FIG_WIDTH)
          objectives -> "What You Will Learn" note box (target icon) after the opener paragraph (first block when there is none); takeaways -> "Key Takeaways" tip box (bulb icon)
          after the subsections, so it is the chapter's last block. Fixed titles, kinds and icons; 2-6 items each (OBJECTIVES, TAKEAWAYS)
appendices?: [{title, icon?, blocks}]    -> Appendix A, B, ... before the automatic ones (not Glossary, Revision History, Sources or Index)
glossary?: [{term, definition}]          -> Appendix: Glossary (sorted)
revisions: [{version, date, author, change}]  -> Appendix: Revision History (required for user-guide, technical-reference, sop, manual, policy)
index?: [{term, section}]                -> Appendix: Index (last; A-Z, each entry a link with its page). section = number ("3.2") or a unique title
```
## Sheet layout (meta.layout "sheet")
```
meta: as above plus layout: "sheet"; doc_type = any kebab-case format id (quick-start, job-aid, quick-reference-card, checklist,
      one-pager, status-report, faq-sheet, ...; it labels the band); owner as provided; sheet?: {pages_per_section 1,
      min_body_pt 9, min_table_pt 8, min_figure_pt 8, text_scale 1.0 (0.8-1.5; one scale for every page; floors never lowered)}
sections: [{title (role or topic), blocks?, sections?: [{title, width?: "half" | "full", blocks}]}]   no appendices, glossary, index, revisions pages
```
No cover, contents or TOC field, no automatic appendices. Each top-level section starts a page: the brand logo (when there is one) and format label, then a
band in the brand's dark color with meta.title, the section title and "Version X · Date", closed by a secondary-color rule. Level-2 titles are
primary-color 11 pt bold; two consecutive `"width": "half"` subsections sit side by side (borderless two-column table). Footer on every
page: "<brand footer> <classification> · <title> v<version> · Revised <date>" (brand footer: "©<year> <org>" or the profile's own `footer`, left out when the project names no owner; classification: meta.classification, default "Proprietary and confidential. For internal use only.", left out when the brand footer already says it), then
"Printed copies may be out of date." (+ " Latest version: <meta.latest_url>" as a link, + " · Owner Role: … · Last Reviewed: … · Next Review: …" when set; D-65), then
"Sources: ..." with the linked sources only (http/https or [title](url)) if they fit; unlinked or unfitted sources stay in meta and the doc properties and "Page X of Y". One PDF bookmark per top-level section.
D-26: `meta.subtitle?` prints in the band under the section title (11 pt in the brand's context tint, 4.5:1 on the dark band, above "Version X · Date"); nothing when absent; SHEET_SUBTITLE fails when the subtitle is not on page 1 of the PDF.
D-27: footer sources `[title](https://...)` show the title and bare https URLs show themselves, both as real hyperlinks (footer relationship, PDF link annotation); SOURCE_LINK fails when a linked source's URL has no link annotation on a page.
Formats, labels, limits and the Quick Start anatomy are data in `assets/sheet_formats.json`; example: `assets/quick-start.example.doc.json`.

| doc_type | Lint |
|---|---|
| quick-start | QS_STRUCTURE: level-2 titles in order Who It's For, What You Can Do, Steps (numbered/procedure, 3-5 steps), Worked Example, Common Mistakes (≤2 items), Get Help; ≤250 words per role. QS_PAGE_COUNT: each role ≤ pages_per_section ("QS_PAGE_COUNT pass: <n> roles, <n> pages" / "FAIL [QS_PAGE_COUNT] role <n>: <k> pages") |
| decision-guide, participant-handout, release-notes, meeting-agenda, raci, process-map | 1 page per section; each top-level section needs the catalog's level-2 sections (SECTION_REQUIRED), e.g. release-notes: Summary, What Changed, Who Is Affected, Action Needed, Get Help |
| dashboard-guide, metric-definitions, data-dictionary, project-charter, training-plan; faq-sheet | 2 pages per section (also the default pages_per_section); same level-2 rule (dashboard-guide: Purpose, Access, How It Is Organized, Definitions, How to Use It, Data Sources and Refresh, Known Limitations, Get Help); faq-sheet has no sections list |
| any other sheet | SHEET_PAGE_FIT: each section ≤ pages_per_section, and pages_per_section ≤ the format's `pages`; `required` top-level titles if the format lists them. SHEET_FORMAT_KNOWN fails when a catalog sheet type (`catalog_sheet_types`) has no entry; other kebab-case ids use the default rules |

The build never shrinks text to make a page fit: an over-long section still builds and lint fails QS_PAGE_COUNT / SHEET_PAGE_FIT (cut words or raise pages_per_section). FIG_TEXT_SIZE is a FAIL under min_figure_pt (8 pt) on sheets.

Order of appendices: yours, Glossary, Revision History, Sources, Index. Headings are numbered automatically (1, 1.1, 1.1.1); don't number titles yourself.

## Required top-level sections
| doc_type | Required (any order, other sections allowed) |
|---|---|
| user-guide | Introduction · Getting Started · Troubleshooting · Support (one "Troubleshooting and Support" chapter meets both) |
| technical-reference | Overview · Definitions · Support |
| sop | Purpose · Scope · Roles and Responsibilities · Procedure · Exceptions · References |
| manual | Introduction · Support ("Troubleshooting and Support" meets it) |
| report | Executive Summary · Findings · Recommendations |
| policy | Purpose · Scope · Policy Statement · Roles and Responsibilities · Definitions · Exceptions · Related Documents; plus revisions and meta.origination_date (example: `assets/policy.example.doc.json`) |

Accessibility (DOC_A11Y, WCAG 2.1 AA and PDF/UA basics): Word styles carry w:lang en-US; every data table repeats its header row; every picture has alt text; text colors come only from `doc_theme.json` a11y.text_pairs, each 4.5:1 or more on its background (gray text in muted_text, warning text in alert_text; the brand alert color stays on icons and bars); the brand resolver darkens or lightens any project color that misses a pair, and reports it; the PDF gets /Lang en-US and /Title = meta.title. TERM_BRAND (warn) flags off-style terms from the shared `references/terminology.json` (AP dates, more than), the project's house terms (the brand profile's `terminology` file, same format, e.g. a `case` rule for a product name) and the capitalization of the brand name and org from a brand profile; without the shared file it says "not run" and the BRAND casing rule on the brand name fails instead.

## Guide profiles (meta.profile, GUIDE_PROFILE)
Lint only; the build never reads it. `lean` (example: `assets/user-guide.example.doc.json`): numbered task topics (a section with a `procedure` for each task), a top-level `Reference` chapter, contents and a glossary; no `objectives` or `takeaways` boxes, no index, and no heading or callout titled What You Will Learn, Key Takeaways or Index (say "What This Guide Covers"). `textbook` (example: `assets/textbook.example.doc.json`): chapter openers, both boxes and an index. When meta.profile is unset: textbook if the doc uses objectives, takeaways or an index; else lean when doc_type is user-guide and meta.audience is not a developer audience; else not checked (developer manuals stay textbook). Lists live in `doc_theme.json` profiles.

## Blocks
| type | Fields | Rules |
|---|---|---|
| paragraph | text | Inline `**bold**` for UI labels, `` `code` ``, `[text](https://…)`; ≤120 words (warn) |
| bullets / numbered | items | 2–9 items |
| procedure | title? ("To export a report:"), steps [{text, result?, image?, caption?, alt?, width_in?}] | 2–12 steps; one action per step, starts with the verb, ≤40 words |
| table | columns, rows, caption, widths_in? | 1–6 columns; every row the same length; caption above; header repeats on each page |
| figure | image, caption, alt, width_in?, crop? | User-supplied screenshot, or a source-gated, stamped illustration from an overlay skill (caption says illustration); caption ≥3 words below; alt text ≥4 words; a short paragraph (≤40 words) right after it stays on the same page; text under 7 pt at print size warns (FIG_TEXT_SIZE; FAIL under 8 pt on sheets); `crop` [x0, y0, x1, y1] fractions 0-1 prints only that part (FIGURE_CROP) |
| callout | kind (note, tip, example, important, warning), text and/or items, title?, icon? | ≤60 words and ≤6 items; default Tabler icon per kind; the alert color only for warning |
| code | code, title? | Monospace block, lines ≤90 characters; optional bold title above |
| step_diagram | steps [{label, icon}], emphasize_sequence? | 3–6 steps (STEP_COUNT); labels ≤4 words (STEP_LABEL), never broken mid-word; Tabler icons above hollow dots on one line (U+25CB in the brand body font when its file has the glyph, else a ring picture), equal spacing; the dot rows and the ring's lift come from the font's own metrics; numerals only with emphasize_sequence |
| card | text and/or items, title?, accent? (primary default, dark, secondary, alert) | One-cell box, 4.5 pt left bar in the accent on the card tint; title and bullets in dark (alert cards: alert_text) for 4.5:1; never splits; title optional |
| page_break | – | Rarely needed; top-level sections already start on a new page (unless page_break_level is 0) |

## What the build guarantees
Letter page, 1 in margins, the brand fonts throughout (body and headings, mono for code; see Fonts below); cover with the project logo (none when the project has no logo; LOGO_NONE warns), type label, title, subtitle and a metadata table; contents as a real Word TOC field whose page numbers are set from the PDF layout (Word users can press F9 to refresh), every entry a working link in Word and the PDF, over as many pages as it needs; index entries link to their sections and are set in two columns; table columns are never narrower than their longest word, measured with the body font's own file at the table size plus cell padding (`widths_in` sets widths, but a column too narrow for its longest word is widened); each callout is one row that can't split across pages, so its title stays with its body; no page header; footer with the brand footer (when the project names an owner), classification, version and "Page X of Y"; tagged PDF with bookmarks and embedded fonts.

## Brand (scripts/brand.py)
Build and lint resolve one brand per doc.json: `--brand PATH`, else `meta.brand`, else `brand.json` (or `.brand.json`, `.brand/brand.json`, `brand/brand.json`) beside doc.json or at the project root, else what the project's files define, else neutral defaults (no logo, no copyright line). A profile is JSON: `name`, `org`, `footer` ("©{year} {org}. Internal use only."; `{year}` comes from meta.date), `classification`, `logo` and `logo_on_dark` (PNG, SVG or JPG, relative to the profile), `terminology` (house terms), `colors` by role (primary, dark, secondary, alert, alert_text, text, muted, muted_text, context, card, callout, card_line, track) and `fonts` (body, heading, display, mono); `"detect": true` merges it over what detection finds. `python3 scripts/brand.py detect --out brand.json` writes one to edit; `brand.py check brand.json` validates it. Colors the profile leaves out are derived from the primary; any text pair under 4.5:1 is adjusted (hue kept) and reported. `assets/doc_theme.json` holds the layout and the neutral fallback colors. LOGO (FAIL) checks the logo is on the cover (sheets: every title band) when the brand has one; LOGO_NONE (WARN) says the project has none.
## Fonts
No font is hard-coded. The brand names the body, heading, display and mono fonts: a brand.json `fonts` entry, the project's theme files (CSS font-family, Tailwind fontFamily, design tokens, Office themes) or font files the project ships (`.ttf`/`.otf`, or listed in brand.json `font_files`). When the project names none, the bundled fallback applies: Inter for body and headings, JetBrains Mono for code (SIL OFL, `assets/fonts/`). The build measures text with the real font file (table column widths, step-diagram labels) and sizes font-dependent layout from the font's metrics (line height, ascent, cap height). Every font file it can find, and whose license allows embedding, is embedded in the .docx (obfuscated font parts, ECMA-376 §17.8.1), so Word, LibreOffice and recipients draw the brand font even when it isn't installed. The Office theme of the .docx is set to the brand fonts and colors. FONTS fails on any other family; FONT_EMBED fails when an available body font was not embedded; FONT_MISSING warns when the named body font isn't on this machine (it can't be measured exactly or embedded); PDF_FONT fails when the PDF isn't drawn in the body font.