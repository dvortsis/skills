# deck.json schema

```json
{
  "meta": {"title": "≤12 words", "subtitle": "optional", "presenter": "", "date": "", "year": 2026,
           "audience": "required", "decision": "required", "big_idea": "required, ≤30 words",
           "cover": "white (default) | primary | dark", "title_accent": "optional, 1-3 words of the title to recolor",
           "logo": "omit (the project logo from the brand) or \"none\"", "brand": "optional path to a brand profile; omit (or \"auto\") for automatic",
           "accent_style": "tab (default) | line"},
  "slides": [ { "layout": "...", "title": "4-15 word takeaway", "notes": "8+ words", ... } ],
  "appendix": [ ...same slide objects; an Appendix divider is added automatically... ]
}
```
The cover is generated from `meta`. Paths are relative to the deck.json folder.

**Brand.** `meta.brand` names a brand profile (`brand.json` format, `references/brand.md`); omit it, or set `"auto"`, to use a profile found in the project or the brand detected from its files. `build_deck.py` and `lint_deck.py` both take `--brand brand.json`, which overrides `meta.brand`; then `$BRAND_PROFILE` applies. The build prints the BRAND line it used. `meta.cover` and split `panel` take role names; the older `blue`/`navy` (cover) and `navy` (panel) are still read as `primary`/`dark`. `meta.logo: "none"` puts the cover and closing on the plain Content layout, without the corner logo (LOGO_OPTION fails any other value; set a different logo in the brand profile).

| layout | Required fields | Optional |
|---|---|---|
| `summary` | title, points[1–4], notes (uses `meta.decision` in the dark panel) | |
| `section` | title | subtitle, accent (1–3 title words, drawn in the `card` tint on primary), notes |
| `bullets` | title, points[1–3], notes | source |
| `statement` | text (≤20 words), notes | attribution |
| `kpi` | title, kpis[1–4]{value, label}, source, notes | dark (dark slide, white cards), kpis[].delta, kpis[].status "missed" + reason, context or takeaway (not both) |
| `contents` | title, items[3–8] (≤6 words each), notes | opens a deck of 6+ slides that people navigate (any deck type) |
| `anatomy` | title, image, alt, zones[2–6]{label (≤4 words), detail (≤16 words)}, notes | zones[].x and .y (0–1) pin a lettered marker on the screenshot; intro (≤25 words); source |
| `annotated` | title, image, alt, annotations[2–4]{lead (≤4 words), text (≤22 words)}, notes | heading (≤6 words), intro (≤25 words), side (left/right; omit to alternate), source |
| `callouts` | title, cards[2–3]{kind example/tip/note/warning, title (≤5 words), text (≤30 words)}, notes | cards[].label (≤3 words, replaces the kind word); at most one warning |
| `article` | title, heading (≤8 words), paragraphs[1–3], notes | takeaways[≤4] (≤12 words each), aside_title; ≤110 words in inform decks, ≤60 in decision decks |
| `contact` | title (≤8 words), contacts[1–3]{label (≤2 words), value (≤44 chars)}, notes | text (≤18 words), accent; closes an inform deck |
| `checklist` | title, items[3–6]{text (≤12 words), status done/in_progress/open/at_risk}, notes | items[].owner, items[].date, items[].reason (required for at_risk), source |
| `qa` | title, pairs[1–4]{q (ends with ?, ≤14 words), a (≤25 words)}, notes | source |
| `shift` | title, from{value, label}, to{value, label}, source, notes | metric (≤6 words), change (≤10 chars pill), to.status "missed" + reason, takeaway |
| `steps` | title, steps[3–5]{label (≤5 words), detail (≤14 words)}, notes | highlight (index), tint, source |
| `cards` | title, cards[2–4]{label (≤4 words), detail (≤14 words)}, notes | numbered, highlight (index), tint, source |
| `split` | title, points[1–3], visual{kind "screenshot", image, alt} or visual{kind "number", value, label}, notes | panel ("tint" default or "dark"), side ("left"/"right"; omit to alternate), visual.delta, source (required for a number) |
| `hero` | title (≤12 words), notes | value (≤7 chars) + label (≤6 words) + source for a big number; text (≤20 words); accent (1–3 title words, drawn in the `context` tint on dark) |
| `chart` | title, chart{type, categories, series[{name, values}], highlight{category or series}}, source, alt, notes | chart.number_format, chart.alert{category, series?, reason}, chart.native (force a native chart instead of pill bars), takeaway (≤22 words, shown as a callout under the chart) |
| `screenshot` | title, image, alt, notes | callouts[≤3]{x, y, text}, source |
| `diagram` | title, diagram{kind, …}, alt, notes | diagram.highlight (index) |
| `table` | title, table{columns, rows}, notes | table.highlight_row, table.tag_column (column index; default: any column), source, alt |
| `closing` | title ("Decision needed: …"), asks[1–3]{action, owner, date} | notes |

Any body slide may carry `series` (a short name) to mark a deliberate walkthrough of up to 3 consecutive slides with the same layout. `takeaway` (≤22 words, an insight box under the visual) works on `chart`, `kpi`, `screenshot`, `table` and non-timeline `diagram` slides. Pacing rules: `references/pacing.md`.

Diagram kinds:
- `process`: nodes[3–6]{label, detail}; hollow dots mark the steps, `numbered: true` draws numbered circles instead (MARKER_BUSY warns on numbers plus icons without it); a node label that names a concept rather than an on-screen control sets `"label_kind": "concept"`
- `timeline`: nodes[3–6]{when, label, detail}
- `matrix`: nodes[4]{label, detail} in order TL, TR, BL, BR, plus axes{x, y}
- `comparison`: left{label, points[1–3]}, right{label, points[1–3]}; the right column is the highlighted one (primary tab, the other dark); headings must fit one line at the same size (MATCHED_HEADINGS); a dark "vs" marker sits between them, never an arrow (COMPARISON_CONNECTOR)
- `funnel`: nodes[3–5]{label, value} narrowing top to bottom, plus a source; highlight (index)
- `milestones`: nodes[3–6]{label, detail (≤14 words), when (≤3 words)} on one line, cards alternating above and below; highlight (index)
- `layers`: nodes[3–5]{label, detail (≤14 words)} stacked top to bottom; highlight (index)
- `roadmap`: periods[3–6], lanes[1–4]{label, items[1–3]{label (≤4 words), start, end}} (start/end are period names or 0-based indexes; items in a lane can't overlap); highlight{lane, item}
- `cycle`: nodes[3–5]{label, detail}, center (≤3 words, optional); highlight (index). A 5-step cycle can't take a takeaway

Every body slide carries `message` (one of the 18 types in `visual-selection.md`), written before the layout is chosen. `meta.type`: `decision` (default; opens with `summary`, ends with `closing` and its ask) or `inform` (explains, trains, documents or updates; opens with `summary` or `contents`, ends with `closing` or `contact`; `guide` and `training` are aliases). A `statement` with `"role": "retrieval"` is a quick check: text starts "Quick check:", ends with "?", and the answer is never on that slide (RETRIEVAL_FORM). The next slide gives the answer on the slide itself and sets `"role": "answer"` (RETRIEVAL_ANSWER); the pair is exempt from the pacing checks and counts as one interactive unit, not as text slides, in VISUAL_RATIO, HERO_MAX and LAYOUT_OVERUSE. A table cell that starts with a status in capitals (PASS, ACCEPTED, FIXED · AWAITING RETEST) renders the status as a bold tag in the primary color (STATUS_TAG); keep statuses whole, with breaks only after "·" (LABEL_BREAK). The cover's file title and subject come from `meta.title` and `meta.subtitle` (CORE_PROPS); `--draft` adds a draft mark to the cover (DRAFT_MARK). A `highlight` must share a key word with the title or takeaway (HIGHLIGHT_REASON). Optional `meta.shotlist`: path to the shot list while screenshots are pending. Speaker notes use plain cues, never design tags such as "Path: Foundation" or "Retrieval:" (NOTES_TAGS). Optional `icon` (a Tabler name) on items of `cards`, `callouts`, `contact`, `annotated`, process/timeline/cycle/milestones nodes, and on a `hero` statement. `meta.cover_align`: `left` (default) or `center`. Inform decks need title, audience and big_idea (no decision) and allow 70 body words per slide (decision decks 40). `kpi` accepts `style: "minimal"` (borderless numbers with hairline dividers; not with `dark`). `bullets`, `cards`, `steps` and attribution-free `statement` slides accept `tint: true`. `screenshot` accepts `side` ("left"/"right"; walkthrough series alternate automatically).

`chart.type`: `bar` | `column` | `line` | `stacked_bar` | `stacked_column`. A single-series `bar` with 8 or fewer categories is drawn as pill bars; everything else is a native, editable chart. `number_format` examples: `0%`, `0.0%`, `#,##0`, `$#,##0.0,,"M"`, `$#,##0,"K"`. `alert.reason`: `missed_goal` | `unfavorable_change` | `failed_save`.
A full working example is in `assets/example.deck.json`.
