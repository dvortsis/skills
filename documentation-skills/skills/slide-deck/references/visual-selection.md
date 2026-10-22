# Choosing the visual (one per slide, never decoration)

Pick the visual from the **message**, not from the data you happen to have. If nothing on this list fits, the slide is a `statement` or it belongs in the notes.

## Choose by message (story first; the library is a menu, not a checklist)
Write the storyline first: each slide's takeaway title plus its `message`. Only then choose the layout that tells that message, using `scripts/plan_deck.py` for options that keep the deck varied. No layout belongs to a subject or deck type: a `callouts` slide can hold tips in a training deck or risks in a decision deck; `anatomy` can explain a dashboard, an org structure or a workflow screen. A good deck uses the 5–8 layouts its story needs; never add one just to use it. MESSAGE_FIT fails when the layout can't tell the message.

| message | Use when the slide says… | Layouts that can tell it (first is usually best) |
|---|---|---|
| `point` | A decision, principle or turning point, stated plainly | `hero:statement`, `statement`, `split:number`, `split:screenshot` |
| `number` | One number that matters | `hero:number`, `split:number`, `kpi`, `kpi:minimal`, `kpi:dark` |
| `numbers` | Two to four headline numbers | `kpi`, `kpi:minimal`, `kpi:dark` |
| `change` | One metric before and after | `shift`, `chart`, `kpi`, `kpi:minimal` |
| `comparison` | A comparison, ranking, trend or mix across categories or time | `chart`, `table`, `diagram:comparison` |
| `flow` | Loss or conversion through stages | `diagram:funnel`, `chart` |
| `loop` | A repeating cycle | `diagram:cycle` |
| `sequence` | Ordered steps or a process | `diagram:process`, `diagram:milestones`, `diagram:timeline`, `steps` |
| `plan` | Work or milestones by period | `diagram:roadmap`, `diagram:milestones`, `diagram:timeline`, `table` |
| `structure` | The parts of a whole: tiers, an architecture, the anatomy of a screen or system | `diagram:layers`, `anatomy`, `cards` |
| `tradeoff` | Options against two criteria | `diagram:matrix` |
| `options` | A choice between two or more options | `diagram:comparison`, `cards`, `table` |
| `status` | Readiness, progress or open items | `checklist`, `table`, `kpi`, `kpi:minimal` |
| `questions` | Questions the audience will ask, with answers | `qa` |
| `ideas` | Two to four parallel ideas, changes or principles | `cards`, `bullets`, `steps` |
| `walkthrough` | How to read or use a screen, object or document | `annotated`, `screenshot`, `anatomy`, `split:screenshot` |
| `guidance` | Examples, tips and warnings | `callouts`, `cards` |
| `context` | Background the audience needs before the rest | `article`, `bullets`, `statement`, `split:screenshot` |

Keys: `diagram:<kind>` is a `diagram` slide of that kind; `hero:number` is a hero with a `value`; `split:<kind>` is a split with that visual; `kpi:minimal` and `kpi:dark` are KPI styles.
`lint_deck.py` prints LAYOUT_FIT advice when content looks like it belongs in another layout (for example, bullets that are all numbers).

| The title says… | Use | Layout and settings |
|---|---|---|
| A headline number or 2–4 numbers vs goal | KPI cards | `kpi`, 1–4 rounded cards (`dark: true` for a dark feature slide); the alert color only with `status: missed` and a reason |
| Ranking or comparison across categories | Pill bars, sorted | `chart` `bar` (single series, ≤8 categories, drawn as rounded bars on a track); highlight the one that matters |
| Change over time (3+ ordered points) | Line | `chart` `line`, at most 4 series, one highlighted, direct end labels |
| Few periods or discrete counts over time | Column | `chart` `column` |
| Composition (parts of a whole) | Stacked bar or column (at most 3 parts) | `chart` `stacked_*`; never pie, donut or 3-D |
| Something in the product: a feature, flow or UI change | Screenshot | `screenshot`, cropped to the area that matters, at most 3 numbered callouts |
| A sequence, workflow or plan | Process or timeline | `diagram` `process` or `timeline`, 3–6 steps |
| Prioritization or a trade-off | 2×2 matrix | `diagram` `matrix`, one quadrant highlighted |
| Before and after, or option A vs B | Comparison | `diagram` `comparison`, at most 3 points per side |
| Loss or conversion through stages | Funnel | `diagram` `funnel`, 3–5 narrowing stages with values, one highlighted |
| A repeating improvement loop (Plan-Do-Study-Act) | Cycle | `diagram` `cycle`, 3–5 steps, optional center label |
| 2–4 parallel ideas, changes or principles | Cards | `cards`, optionally numbered, one highlighted, `tint` for a tone change |
| Go-live readiness, open items or status by owner | Checklist | `checklist`, 3–6 items with status words (done, in progress, open, at risk) |
| The questions leaders will ask, with answers | Q&A | `qa`, 1–4 question/answer pairs |
| Tiers, layers or a technology stack | Layers | `diagram` `layers`, 3–5 stacked bands, one highlighted |
| One metric before and after | Shift | `shift`, from → to on one scale, optional change pill |
| An ordered set of actions or fixes | Steps | `steps`, 3–5 numbered rows, one highlighted |
| A sequence where the line already shows the order | Process | `diagram` process with hollow dots; `numbered: true` only when the order itself is the point |
| A plan across months or quarters | Roadmap | `diagram` `roadmap`, 3–6 periods, 1–4 lanes |
| Headline numbers, quieter than cards | Minimal KPIs | `kpi` with `style: minimal` |
| One point plus its proof (a screenshot or one number) | Split | `split`, tint or dark panel; sides alternate |
| Exact values people must look up | Table | `table`: main deck at most 6×5, otherwise appendix |
| A principle, quote or turning point | Statement | `statement`, 20 words or fewer |

## Density limits (enforced by `lint_deck.py`)
- One visual per slide. Body text of 40 words or fewer (70 in inform decks), not counting the title. Bullets: 3 or fewer at 12 words or fewer (the summary allows 4 at 16 words). Step, card and diagram-node details take up to 14 words so each can be a full instruction.
- Never shorten text into a code. If a sentence doesn't fit, split the slide or move the detail to a screenshot callout. "Rate ease; Submit the test ID" fails as shorthand (TELEGRAPHIC); write "Rate how easy the task was, then select Submit."
- Every label makes sense without the speaker notes. A highlight points at what the title or takeaway says.
- At least half of the content slides carry a chart, KPI, screenshot or diagram. Never two text-only slides in a row.
- Alternate layouts and archetypes and add hero breathers in long decks; see `references/pacing.md` (LAYOUT_REPEAT, ARCHETYPE_RUN, PACING, HERO_*, TAKEAWAY_*).
- Charts: at most 2 series (bar/column), 4 (line) or 3 (stacked); at most 12 categories (aim for 8 or fewer, with the tail grouped as "Other").

## Chart rules
- Primary is the focus and gray is context. Highlight exactly what the title talks about. Use direct labels: no legend, no gridlines, no value axis when values are labelled.
- The alert color (the brand's `alert` role) is only for a missed goal, an unfavorable change or a failed save. It always needs `alert.reason`.
- Round values and set `number_format` (`0%`, `0.0%`, `#,##0`, `$#,##0.0,,"M"`). Add a source line to every chart.
- Build charts natively from data (editable in PowerPoint). Never paste a chart picture when you have the numbers.

## Screenshot rules
- Only real captures supplied by the user (dashboards, reports, applications, Confluence pages). The agent never fakes, mocks up or "recreates" a screenshot. The one exception is an approved, stamped illustration the matching guide already uses: keep the stamp and say "Illustration, not a live screenshot" in the source line (ILLUSTRATION_LABEL).
- **No PHI or PII**: use test or masked data. If a capture shows patient names, MRNs, DOBs or employee IDs, stop and ask for a masked one.
- Crop to the region the title talks about. Callouts are numbered markers placed at 0–1 x/y fractions of the image, with at most 8 words each in the side key.
- If a screenshot is missing, build with `--draft` and send the generated `<deck>.shotlist.md`. A draft is never final. A deck that teaches a screen on 5+ slides shows it on 3+ (SCREENSHOT_SLIDES).

## Diagram rules
- Native shapes only (editable). Labels have 4 words or fewer and details 12 or fewer. At most one highlighted node.
- Icons: Tabler outline icons only, used to help people scan (see `brand.md`). No clip-art, emoji, stock photos or decorative imagery. White space is the design.
