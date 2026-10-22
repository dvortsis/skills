# Forms, Surveys and E-learning

Rows D-13, D-46, D-48 to D-51 (`scripts/build_form.py`) and D-14 (`scripts/build_module.py`). Data lists: `survey_rules.json`, `elearning_rules.json` (add terms there, never in code). Synthetic exemplars: `assets/examples/`.

## Commands

```
python3 build_form.py form.json --check                 # gate + trial build (FORM_FIELDS_MATCH)
python3 build_form.py form.json --out Name [--draft]    # Name.pdf (fillable, tagged) + Name.xlsx + Name.msforms.csv
python3 build_module.py module.json --check
python3 build_module.py module.json --out Name [--draft] [--embed-font]   # Name.html + Name.storyboard.md
python3 build_sheet.py sheet.json --out Name           # Name.xlsx (tracker, data dictionary, RACI)
python3 build_sheet.py Name.xlsx --check               # reopen and gate (XLSX_TABLE)
python3 test_builders.py [--only CODE[,CODE]]           # self-tests; --only list prints codes
```
(`python` instead of `python3` on Windows.) Every builder takes `--brand brand.json`; without it the brand comes from the source's project (`scripts/brand.py show --source <source>` prints it): colors, fonts (the project's own font files, else the bundled fallback brand.py names), logo and footer owner. No logo found: none is drawn. No owner found: no copyright line.

Both builders run the gate first and refuse to write on any FAIL unless `--draft` (draft output is marked DRAFT). Lines read `FAIL [CODE] ...` / `WARN [CODE] ...`, then `FORM GATE: n checks, k failed` or `MODULE GATE: n checks, k failed`.

## form.json

```json
{"meta": {"title": "Proper Case Title", "kind": "survey|form", "audience": "", "purpose": "one line",
  "owner": "team, not a person", "version": "1.0", "date": "2026-10-11", "sources": ["..."],
  "anonymous": true, "phi_approved": false, "est_minutes": 5,
  "format": "follow-up-evaluation", "send_after_days": 45},
 "sections": [{"title": "", "intro": "optional",
  "items": [{"id": "Q1", "type": "single|multi|scale|text|longtext|date|checkbox|dropdown|signature",
    "label": "", "required": true, "options": ["..."], "help": "optional",
    "scale": {"min": 1, "max": 5, "low": "Strongly disagree", "high": "Strongly agree", "labels": ["..."]},
    "opt_out": "Not applicable", "show_if": {"Q2": "Yes"}, "rows": 4, "compound_ok": false}]}]}
```

`rows` (longtext height), `compound_ok`, `format`/`send_after_days` (follow-up evaluations only), `scale.labels` (one per point; overrides the standard sets in `scale_point_labels`), `opt_out` (scale and single items; always the last choice) and `show_if` (one earlier item id and one answer or a list of answers) are optional. The id becomes the PDF field name: start with a letter, then letters, digits, `_` or `-`.

### What the PDF contains
Letter, 0.75 in margins. Page 1: logo row (the project logo left, when the brand has one; format label right), a title band in the brand dark color (title; "Version X · Date") with a secondary-color rule, purpose, audience, minutes and anonymity note (surveys) or owner (forms), "* Required" legend. Section headings in the brand primary; items never split across pages ("(continued)" on carry-over). Footer: the brand footer (when the project names an owner) + " · Title vX · Page X of Y".

| Type | Widget |
|---|---|
| text / longtext | text field / multiline text field |
| date | text field, Acrobat date format, "MM/DD/YYYY" printed beside it |
| single | radio group (one field per item, export value = option text) |
| scale | radio group, numbers above the points and a label under every point; only the end labels when no label set fits (SCALE_LABELS) |
| multi | checkboxes under one parent field (`Q5.1`, `Q5.2`...) |
| checkbox | one checkbox beside its label |
| dropdown | combo box starting at "Select one" |
| signature | text field; a date item right after it in the same section is placed beside it |

Tooltips are labels (options read "Label: option"); required items get the PDF Required flag. An item with `show_if` gets a line in the brand primary above it: "Answer Q3 only if you answered Yes to Q2" (displayed numbers; forms name the question by its label). No submit button or backend. Basic screen-reader tags (not full PDF/UA): structure tree (Document; one P per page, one Form per field), /Lang en-US, /MarkInfo, shown title, /Tabs /S. The PDF always embeds (and subsets) a real font file: the project's own font (files it ships, or an installed copy), else the bundled fallback (`PDF font: <font> (embedded)`, or `... (embedded; the brand font <font> is not available here)`). Text widths, line spacing, baselines, field heights and box positions come from that file's metrics (brand.py `measure_path`, `metrics`), so the layout adapts to the font. Text typed into fields uses the PDF viewer's standard form font (PDF form fields can only rely on the base-14 fonts).

The .xlsx has "Questions" (ID, Section, Question, Type, Required, Options/Scale) and "About" (meta) sheets with frozen header rows in the brand dark color, white text and the brand body font; column widths are measured with that font.

`Name.msforms.csv` (UTF-8): Question, Type, Options, Required, Help, Branching; one row per item in PDF order with the same wording (numbers left off; Forms numbers questions). Types come from `msforms_types`. Tell the user to create a new Microsoft Form and paste each row; never claim it imports automatically.

### Form gate

| Code | Level | Rule |
|---|---|---|
| SURVEY_ITEM | FAIL | single/multi/scale label joins two things with "and"/"or" ("Q3 asks two things"), unless `compound_ok`. Fixed phrases such as "pros and cons" are allowed (`compound_phrases_ok`) |
| SURVEY_ITEM | FAIL | leading wording (`leading_phrases`) |
| SURVEY_ITEM | FAIL | scales with different ranges: `mixed scales (1-5, 1-7)` |
| SURVEY_ITEM | FAIL | single/multi/dropdown with fewer than 2 options or duplicate options; scale missing an end label, min ≥ max, or more than 11 points |
| FORM_FIELD | FAIL | empty label, missing, invalid or duplicate id, unknown type, bad `kind`, no items; PHI terms (`phi_terms`) unless `meta.phi_approved` |
| FORM_FIELD | WARN | signature with no date item in its section; identity question in an anonymous survey; survey with no `est_minutes` |
| FORM_FIELDS_MATCH | FAIL | after the build, distinct top-level field names in the PDF ≠ number of items (radio groups and checkbox sets count once) |
| PLACEHOLDER | FAIL | TBD, TODO, First Last, lorem, XXX, `[insert`, `{{` anywhere in the text |
| SOURCES_MISSING | FAIL | `meta.sources` empty |
| FOLLOWUP_ITEMS | WARN | `meta.format` follow-up-evaluation: `missing: frequency of use, barriers, result` (keywords in `followup_topics`); `send_after_days` unset or outside 30-60; kind not survey |
| SCALE_LABELS | WARN | a scale (for example 7-point) with no `scale.labels` and no standard set; wrong `scale.labels` count is SURVEY_ITEM FAIL; `opt_out` on other types is FORM_FIELD FAIL |
| FORM_TAGS | FAIL | the built PDF lacks /StructTreeRoot, /Lang, /MarkInfo, /Title, DisplayDocTitle, /Tabs /S on a page, or a field tooltip |
| FORM_BRANCH | FAIL | `show_if` names an unknown or later item, an answer that item lacks, or an item with no fixed answers |
| TITLE_CASE | FAIL / WARN | title is not `text_rules.proper()` (the message gives the corrected title); section titles WARN |

## module.json

```json
{"meta": {"title": "", "audience": "", "objectives": ["Identify ..."], "duration_min": 12,
  "version": "1.0", "date": "2026-10-11", "sources": ["..."], "pass_percent": 80},
 "screens": [{"id": "S1", "type": "intro|content|scenario|question|practice|summary",
   "title": "", "body": "blank line = new paragraph; **bold** and [label](#anchor) allowed",
   "bullets": ["..."], "image": "file.png", "alt": "", "decorative": false,
   "question": {"stem": "", "multi": false, "options": [{"text": "", "correct": true, "feedback": ""}]},
   "choices": [{"text": "", "correct": false, "feedback": ""}]}]}
```

A screen counts as interactive when it has a `question` with options, or `choices` (branching feedback on a scenario). Image paths are relative to module.json and are inlined as data URIs.

### What the HTML contains
One file, inline CSS/JS, no network; works from disk. Title bar in the brand dark color with the project logo on a white chip (alt text "<brand name> logo"; no logo: no chip), progress bar and "Screen n of N", Back/Next plus Left/Right arrows (ignored inside inputs), focus moved to each heading, focus-visible outlines. Radio inputs (single), checkboxes + Check Answer (multi), `aria-pressed` buttons (scenario choices); the chosen option's feedback appears in an `aria-live` region ("Correct."/"Not quite."; alert-color edge only for incorrect). The summary screen lists the objectives; Finish shows "Module complete". Text uses the brand fonts with generic fallbacks only (`system-ui, sans-serif`); line heights come from the font's metrics. The font files the project ships (or the bundled fallback) go to `fonts/` next to the HTML and load with `@font-face` (`--embed-font` inlines them instead, one self-contained file); installed system fonts are named but never copied. Colors are CSS variables from the brand roles (`--primary`, `--dark`, `--secondary`, `--alert`); the footer is the brand footer plus title and version. Without JavaScript all screens show in order.

Storyboard: front matter (title, audience, objectives, duration_min, version, date, sources) and the table Screen | Type | On Screen | Interaction | Feedback.

### SCORM 1.2 package for your LMS (D-28)
`python3 scripts/build_module.py module.json --out Name --scorm` also writes `Name_SCORM12.zip` with `imsmanifest.xml` (metadata schema "ADL SCORM", schemaversion 1.2, one organization, one item, one resource `adlcp:scormtype="sco"` `href="index.html"` listing every file; `adlcp:masteryscore` = pass mark when the module has question screens) and `index.html` (the same module) at the root, plus `fonts/<file>` for each brand font file the HTML loads, nothing else. The zip is a build output: deliver it next to the HTML, never store it in a skill.

The module's script looks for the LMS `API` object in its parent frames (up to 7 levels) and the opener. If found: `LMSInitialize("")`, `cmi.core.lesson_status` "incomplete" (kept if already passed or completed). On Finish: `cmi.core.score.min` 0, `max` 100, `raw` = percent of `question` screens answered correctly on the first try; `lesson_status` "passed" or "failed" against `meta.pass_percent` (default 80; a prior pass is never downgraded), or "completed" when there are no question screens; then `LMSCommit("")` and `LMSFinish("")`. Closing the window early commits and finishes as "incomplete". Resume (D-52): every screen change and answer sets `cmi.core.lesson_location` (screen number as in the counter) and `cmi.suspend_data` (compact JSON `{"q":{"<question #>":[first try right 1/0,"<chosen options>"]}}`, at most 4096 characters; past that, whole answers drop from the end), then `LMSCommit("")`; closing before Finish sets `cmi.core.exit` "suspend" (Finish sets ""); on start `LMSGetValue` reopens that screen with the answers and first-try scores restored (bad values start on screen 1). Practice screens and scenario choices are not scored. With no LMS the module runs exactly as the offline HTML, and it never calls a network URL.

Upload (people only; the agent cannot upload to an LMS):
1. Build with `--scorm` until both gates show 0 failed.
2. Upload the zip to the LMS's test or pilot area first, following your LMS team's upload instructions. Launch it, finish once passing and once failing, and check the transcript shows the status and score.
3. Only then ask the LMS administrator to load it in production. If the pilot rejects the package, report its message; never hand-edit the zip.

### Module gate

| Code | Level | Rule |
|---|---|---|
| ELEARN_INTERACTION | FAIL | more than 4 screens in a row with no interaction: `screens S3-S8 have no interaction (maximum 4 in a row)` |
| ELEARN_INTERACTION | FAIL | options without feedback: `S5: options C, D have no feedback` (letters by position); no correct option; several correct with `multi: false`; fewer than 2 options; question or practice screen without a question |
| ELEARN_OBJECTIVE | FAIL | no objectives, or an objective starting with a non-observable verb (understand, know, learn, be aware, appreciate...) after prefixes like "Learners will be able to" are stripped; a verb not in `observable_verbs` WARNs |
| ELEARN_OFFLINE | FAIL | built HTML has `http(s)://` or `//` in src, href or url() (the file is not written); a URL in screen text WARNs |
| ELEARN_STRUCTURE | FAIL / WARN | no screens; missing or duplicate id; unknown type; no title; image without alt or file missing. WARN: no summary screen (one is added) or no duration_min |
| SCORM_PACKAGE | FAIL | with `--scorm`, after the build: imsmanifest.xml missing from the root or not XML; schema not "ADL SCORM" or schemaversion not 1.2; not exactly one organization or one SCO; SCO href not in the zip or no item points at it; a file in the zip not listed, or listed and missing; a nested archive; index.html without `LMSInitialize`, `cmi.core.lesson_status` and `cmi.core.score.raw`, or without the resume calls (`scorm_resume_needs`); longest suspend_data over 4096 characters; index.html loading external URLs (ELEARN_OFFLINE). A failing zip is removed |
| PLACEHOLDER, SOURCES_MISSING | FAIL | same rules as the form gate |
| TITLE_CASE | FAIL / WARN | module title FAIL; screen titles WARN |

## sheet.json and Excel tables (D-53)
`meta` (title, format tracker / data-dictionary / raci, version, date, owner_role, sources), `lists` (name -> [{value, definition}]), `columns` ([{name, definition, list?, type: date?}]), `rows` (objects by column name, or arrays). Example: `assets/examples/synthetic_tracker.json` (3 statuses, 5 rows). For data-dictionary and raci, copy the PDF's table (RACI: one `RACI` list on every role column). The workbook: first tab (Tracker, Data Dictionary or RACI) with one named table (`tblTracker`...), header row frozen, header in the brand dark color with white text (the brand footer on printed pages); a hidden Lists tab (one column per list, the only dropdown source); a Definitions tab (every column, list value and the About lines). Settings: `material_rules.json` "sheet".

| Code | Level | Rule |
|---|---|---|
| XLSX_TABLE | FAIL | merged cells on any tab; a Status column (or any column with a list on the Definitions tab) with no dropdown, a dropdown not from the Lists tab, or a value outside its list; no named table at A1; header not frozen; header not in the project brand colors (dark fill, white text); Lists or Definitions tab missing. The build refuses on FAIL |

## Limits

* Forms: no conditional logic, calculations, submit button or backend; no Microsoft Forms/Qualtrics export (CP1 decision 6) or .docx form yet.
* Signature is a typed-name text field, not a certificate digital signature.
* Double-barrel detection is a wording heuristic; use `compound_ok` for deliberate compounds.
* PDFs still need a visual review (D-06); widget look varies slightly by viewer.
* SCORM 1.2 only: no SCORM 2004 or xAPI, no per-question `cmi.interactions`; still pilot every package in your LMS's test area first.
* No headless browser: HTML is checked by parsing and by running its script against a minimal DOM shim in Node.
* The SCORM adapter is proven in Node against a fake LMS `API`, not a real LMS: every package is tested in the LMS's pilot or test area before production (see SCORM 1.2 package above).
