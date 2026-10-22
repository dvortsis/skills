# Rhythm and pacing (enforced by `lint_deck.py`)

A deck feels interesting when the eye gets a change every slide or two while the brand stays constant. Vary the **layout archetype**, not the colors, fonts or shapes.

## Archetypes
| Archetype | Code | Layouts |
|---|---|---|
| Data | D | `kpi` (cards or minimal), `chart`, `table`, `shift`, `split` with a number |
| Visual | V | `screenshot`, `diagram` (all nine kinds), `split` with a screenshot, `anatomy`, `annotated` |
| Text | T | `bullets`, `cards`, `steps`, `checklist`, `qa`, `callouts`, `article` |
| Hero (breather) | H | `hero`, `section`, `statement`, `kpi` with `dark: true` |
| Frame | S / C | `summary` or `contents`, and `closing` or `contact` (not counted) |
`lint_deck.py deck.json --story` prints the rhythm strip, for example `S D V H D V V T H V D C`, and a tone strip, for example `S L W L N W W N L W W C`.

## Tone (the second rhythm)
| Tone | Code | Comes from |
|---|---|---|
| White | W | Most slides |
| Light tint | L | `tint: true` on `bullets`, `cards` or a `statement` without attribution (a `card` tint band behind the body), or a `split` with `panel: tint` |
| Dark | N | `hero`, `kpi` with `dark: true`, `split` with `panel: dark` |
| Primary | B | `section` |
The letters N and B are the codes the tone strip prints for dark and primary. Rules: TONE_RUN (decks with 8+ body slides: never five white slides in a row), TINT_ADJACENT (never two tint slides in a row), TINT_LAYOUT (tint only on bullets, cards and plain statements).

## Layout spread
LAYOUT_OVERUSE: decks with 6+ body slides put no layout on more than 40% of them. LAYOUT_DISTINCT: decks with 8+ body slides use at least 5 distinct layouts (a diagram kind or a dark KPI counts as distinct). MIRROR: split slides alternate the panel side, and walkthrough screenshots alternate the image side; omit `side` and the builder alternates for you.

## Alternation rules
| Code | Rule | Level |
|---|---|---|
| LAYOUT_REPEAT | No two consecutive slides with the same layout (a dark and a light KPI slide differ; diagrams of different kinds differ). A deliberate walkthrough may repeat: give each slide the same `"series"` value | FAIL |
| SERIES_MAX / SERIES_SPLIT | A series holds 3 slides at most, and they must be consecutive | FAIL |
| ARCHETYPE_RUN | No three body slides of the same archetype in a row (except one series) | FAIL |
| LAYOUT_VARIETY | Decks with 6+ body slides use at least three archetypes | FAIL |
| HERO_ADJACENT | Never two hero or divider slides back to back | FAIL |
| HERO_MAX | About one hero per four body slides at most (one allowed in any deck) | FAIL |
| PACING | Decks with 8+ body slides: no more than five content slides without a breather; aim for one every 3–5 | FAIL |
| DENSE_RUN | Follow a dense slide (a table or 30+ words) with a lighter one | WARN |
| TEXT_RUN, VISUAL_RATIO | Existing rules: never two text-only slides in a row; at least half the content slides carry a visual (a hero number counts) | FAIL |

## Hero slides (`layout: hero`)
A dark, full-bleed breather on the master's Dark layout: white display type, an optional accent of 1–3 title words in the `context` tint, a short `secondary` rule. Two forms:
- **Number:** `value` (≤7 characters), `label` (≤6 words), `title` (the so-what, ≤12 words), optional `text`, and a `source` (required).
- **Statement:** `title` (≤12 words) and optional `text` (≤20 words); use it to restate the decision or mark a turn in the story.
Place a hero after a run of evidence (the number that matters most) or just before the ask. Never open or close on one; the summary and closing frame the deck.

## Insight boxes (`takeaway`)
A `callout`-tint box with a primary left bar under the visual, carrying the so-what in 22 words or fewer. Allowed on `chart`, `kpi` (instead of `context`), `screenshot`, `table` and `process`, `matrix` or `comparison` diagrams; not on timelines, text or hero slides. Rules: it must add impact, an action or an implication, not repeat the title (TAKEAWAY_ECHO); use it on the 1–3 slides that most need it (TAKEAWAY_NONE warns when there are none, TAKEAWAY_OVERUSE when more than two thirds of visuals have one).

## New ways to add variety
- `cards`: 2–4 parallel ideas as rounded cards (label ≤4 words, detail ≤14), optionally numbered with one highlighted. Use instead of bullets when items are parallel.
- `split`: a rounded tint or dark panel with 1–3 points beside a screenshot or one big number. Good for "here is the point, here is the proof".
- `diagram` `funnel`: 3–5 narrowing stages with values (loss through a pipeline). `diagram` `cycle`: 3–5 steps in a loop with an optional center label (Plan-Do-Study-Act, continuous improvement).
- `kpi` with `style: minimal`: borderless big numbers divided by hairlines (a cleaner variant of KPI cards; counts as a different layout).
- `shift`: one metric from → to with a thin arrow and a change pill; both numbers on the same scale.
- `steps`: an editorial numbered list (numeral, label, detail) on full-width rows divided by hairlines; highlight one step.
- `diagram` `roadmap`: 3–6 periods, 1–4 lanes, pill bars per item; highlight one item.
- `tint: true`: a light band that changes the tone of a text slide without a new color.

## A good default arc for 8–12 slides
`summary` → data (KPI with an insight box) → visual (process) → **hero number** → data (chart) → visual walkthrough (`series`, 2 slides) → text → **hero statement** → visual (comparison) → data (table with an insight box) → `closing`. See `assets/rhythm.example.deck.json`. A minimal arc: `summary` → minimal KPIs → steps → shift → hero statement → roadmap → cards (tint) → chart → split (dark) → matrix → hero number → `closing`; see `assets/minimal.example.deck.json`. A higher-variety arc: `summary` → split number (tint) → funnel → cards (tint) → hero → chart → cycle → split screenshot (dark) → tinted statement → mirrored walkthrough → `closing`; see `assets/variety.example.deck.json`.
