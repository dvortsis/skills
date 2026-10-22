# Brand and visual style (modern minimal)

The deck carries the project's own brand: its logo, palette and fonts. The style (rounded cards, pill bars, tinted callouts, white space) is the same for every brand; only the role colors, fonts, logo and footer change.

## Where the brand comes from
`scripts/brand.py` resolves the brand once per build, and `build_deck.py` and `lint_deck.py` use the same lookup, so the lint checks against the brand the build used. The first match wins:
1. **An explicit profile:** `--brand brand.json`, then `meta.brand` in deck.json (a path relative to deck.json; omit it or set `"auto"` for automatic), then `$BRAND_PROFILE`. A named profile that doesn't exist stops the build.
2. **A profile in the project:** `brand.json`, `.brand.json`, `.brand/brand.json` or `brand/brand.json` beside deck.json, then the same names at the project root. The project root is the nearest folder above deck.json (or the working folder) holding `.git`, `package.json`, `pyproject.toml` or another project marker; `$BRAND_PROJECT` overrides it.
3. **Detected from the project files** (below).
4. **Neutral defaults:** a neutral blue and gray palette (the fallback in `assets/theme.json`), the fallback fonts (below), no logo and no footer line.

### Fonts
The skill never sets a font of its own. The project's fonts come first, in this order: the profile's `fonts`; fonts the project names (design tokens, Tailwind `fontFamily`, CSS font variables and `font-family` on `body` and headings, Office template themes, Google Fonts links, `next/font` imports); `@fontsource` packages in package.json; `.ttf`/`.otf` files the project ships (their own family names, and they are the files used); the UI framework's default (Material UI and Vuetify: Roboto). Only when none of these names a font does the deck use the fallback set: **Inter** for titles and text and **JetBrains Mono** for code, both SIL Open Font License, shipped in `assets/fonts/` (see its README) so text is measured with the real font on every machine. Generic stacks such as `system-ui, sans-serif` don't count as naming a font.

`python scripts/brand.py show --source deck.json` prints the result (the BRAND line, role colors with where each came from, fonts, logo, footer, notes and `BRAND_CONTRAST: n pairs, f failed`) and exits 1 if a contrast pair still fails. `python scripts/brand.py detect [--project DIR] [--out brand.json]` prints what the project defines and, with `--out`, writes it as a profile to correct by hand. `python scripts/brand.py check brand.json` validates a hand-written profile (BRAND_SCHEMA findings, then `BRAND_CHECK: n failed`).

### What detection reads
- **Colors and fonts**, by token name (primary, brand, accent, dark, secondary, warning or danger, text or foreground): design-token and theme JSON files; Tailwind configs and MUI `createTheme`, Chakra `extendTheme` and other theme objects in JS/TS; CSS, SCSS and LESS custom properties and variables (root-level first), plus `font-family` on `body` and headings; HTML `theme-color` meta tags, Google Fonts links and `next/font` imports; Office themes in `.potx`, `.dotx` and `.thmx` files (and `.pptx`/`.docx` files whose names contain templ, brand, theme or master): accent 1 is primary, dark 2 is dark, accent 2 is secondary, the major and minor fonts are the display and body fonts; Android `colors.xml`; the web manifest `theme_color`. With no color tokens at all, the logo's most common strong color becomes the primary.
- **Logo:** image files named logo, logotype, wordmark, lockup or brand, or in a `logo`, `logos` or `brand` folder. SVG is preferred (rasterized with PyMuPDF), then PNG; icon, mark and favicon files rank lower. A version with light ink (or named white, inverse, reversed, knockout or on-dark) becomes the on-dark logo. App icons (`apple-touch-icon`, `icon-512`, `favicon`) are used only when no logo file exists, and the BRAND line says so.
- **Name and footer:** the name from the `package.json` displayName or productName, the web manifest name, the README title or the package name, in that order; the organization from the LICENSE copyright holder or the `package.json` author. With an organization the footer line is "©YEAR ORG"; without one, there is no footer line.

### What it never does
- Reach the network or change project files (`detect` writes only the `--out` file).
- Draw, guess or recreate a logo. No logo found means no logo drawn. An SVG logo needs PyMuPDF; without it, no logo is drawn and the BRAND line says so.
- Read dependencies, build output, tests, fixtures or examples (`node_modules`, `vendor`, `dist`, `build`, `test`, `examples` and similar), minified files, lock files or CSS dark-mode blocks.
- Take a partner, client, vendor or framework logo (React, GitHub, Docker and the like) as the project's logo.
- Change a color silently. A color that misses a contrast pair is darkened or lightened, keeping its hue, and every change is printed as a note (`adjusted primary #... -> #...`).

## The brand profile (`brand.json`)
| Key | Meaning |
|---|---|
| `name`, `org` | Product or project name (theme name, logo alt text) and the organization (footer, file author) |
| `footer` | Footer template; `{year}` and `{org}` are filled in. Omit for "©YEAR ORG" (plus `classification`), `""` for none |
| `classification` | Optional label added after the copyright, e.g. "Internal" |
| `logo`, `logo_on_dark` | Paths (relative to the profile) to the logo and its light-on-dark version |
| `terminology` | Path to a house-terms file in the format of `references/terminology.json`, added to the generic rules (TERM_BRAND) |
| `colors` | `{role: color}` for any roles below; hex, `rgb()`, `hsl()` or `oklch()`. Missing roles are derived |
| `fonts` | `{body, heading, display, mono}`; decks use `display` (titles of covers and dividers, statements, big numbers) and `body` (everything else) |
| `detect` | `true` merges the profile over what detection finds (the profile wins) |

```json
{
  "name": "Harbor Notes",
  "org": "Harbor Labs",
  "footer": "©{year} {org} · Internal",
  "logo": "assets/harbor-logo.svg",
  "logo_on_dark": "assets/harbor-logo-white.svg",
  "colors": {"primary": "#2B5FD9", "dark": "#14213D", "alert": "#C2410C"},
  "fonts": {"body": "Inter", "display": "Inter"}
}
```

The older color names `blue`, `navy`, `light_blue` and `orange` are accepted in profiles as aliases of primary, dark, secondary and alert. In deck.json, `meta.cover` `blue`/`navy` and split `panel: navy` are still read as `primary`/`dark`.

## Role colors
Only these roles and their tints are used (COLOR fails any other color in the built file). Missing roles are derived: `dark` is the primary darkened, `secondary` a lighter primary, `context` a 50% tint of the primary, `card` and `callout` a 25% tint of the secondary.

| Role | Used for | Contrast rule (WCAG AA) |
|---|---|---|
| `primary` | The focus: highlighted bar, card, node or quadrant, accent text, status tags, short rules on white; cover and closing background (Cover Primary), section dividers | 4.5:1 on white; white on primary 4.5:1; on `card` 3:1, bold 14pt and larger only |
| `dark` | Titles and labels, comparison headings, the "vs" marker, ring nodes, note bars; hero, dark KPI, contact and summary backgrounds | 4.5:1 on white, `card`, `context` and `callout`; white on dark 4.5:1 |
| `secondary` | Short rules on dark slides, tip bars, bullets on a dark panel, line-chart context series | Decorative only; never text |
| `alert` | A missed goal, an unfavorable change, a failed save or the one warning, always with a reason (ORANGE, ALERT_REASON) | Never white text on it |
| `alert_text` | Alert-colored text | 4.5:1 on white and `card` |
| `text` | Body text | 4.5:1 on white, `card` and light gray |
| `muted`, `muted_text` | Gray context: the "before" side, secondary labels and sources; `muted_text` for the footer line on white | `muted_text` 4.5:1 on white |
| `context` | 50% tint of primary: context bars and columns, accent words on dark slides, placeholder outlines | `dark` on it 4.5:1 |
| `card`, `callout` | 25% tint of secondary: card fill, tint band, tint split panel, insight box and callout fill; accent words on primary slides | `card` on primary 3:1, bold large text only |
| `card_line`, `track` | Card outlines, hairline dividers, pill-bar tracks | None (no text) |
| `white`, `black` | Slide and card backgrounds, text on dark; black only for the soft shadow | — |

Accent words (two-tone titles, "Decision Needed") use `context` on dark slides and `card` on primary slides. ACCENT_CONTRAST fails any accent run under 4.5:1 (3:1 at 24pt and larger), measured against the color behind it.

## Generated layouts
`scripts/master.py` builds the master at build time from the brand: the theme colors and fonts are the brand's (so anyone editing in PowerPoint picks from the project palette), and the footer line and slide number sit in the footer band below 6.8 in.

| Layout | Background | The master draws | Used for |
|---|---|---|---|
| Cover Light | white | Logo in the bottom-left corner, footer line | Cover (`meta.cover: white`, the default) |
| Cover Primary | primary | On-dark logo in the corner, footer line | Cover `primary`; closing ask |
| Cover Dark | dark | On-dark logo in the corner, footer line | Cover `dark`; summary (dark panel with the decision, white content area) |
| Content | white | Footer line, slide number, small logo at the right of the footer band | All content slides, including tint bands, split, funnel and cycle; contents, anatomy, annotated, callouts, article, milestones |
| Section | primary | Footer line, slide number (no logo) | Section dividers and the Appendix divider |
| Quote | white | Footer line, slide number, small logo | Statement with attribution |
| Dark | dark | Footer line, slide number, small on-dark logo | Dark KPI slide (`kpi.dark`), hero breather (white display type, accent words in `context`, a short `secondary` rule), contact (closing for inform decks: centered white title, translucent contact rows) |

`meta.cover_align: center` centers the cover title, subtitle, short accent rule and meta on the center line. `meta.logo: "none"` (for example, a co-branded external deck) puts the cover and closing slides on the Content layout, so they carry no corner logo; the small footer logo on other slides stays. For no logo anywhere, use a brand profile without one.

## Logo rules
- The logo comes only from the project files or the brand profile. Never draw, import from elsewhere (the web, another project, an icon set), recolor or stretch a logo. The one automatic change is a white knockout made from a transparent logo's shape, used on primary and dark slides when the project has no on-dark version; a logo without transparency gets no knockout, so those slides show none (add `logo_on_dark`).
- The master places it with its aspect ratio kept: on covers in the bottom-left corner (at most 2.4 × 0.9 in), on content, quote and dark slides small at the right of the footer band (at most 1.1 × 0.34 in).
- Keep the corner clear: LOGO_ZONE fails content within 0.25 in of the cover logo, and FOOTER_ZONE fails content in the footer band. LOGO_MISSING fails a cover that isn't on a cover layout while the brand has a logo; LOGO_NONE warns when no project logo was found; LOGO_OPTION fails any `meta.logo` value other than omitted or `"none"` (set another logo in the brand profile).

## Shape language
- **Rounded, light, airy.** Cards are rounded rectangles (0.14 in radius): `card` tint with no line on white slides, white with a `card_line` hairline for the muted "before" side of a comparison, or white with a soft shadow on dark. Callouts use a 0.08 in radius with a 0.06 in primary left bar. Screenshots get 0.12 in rounded corners, a hairline border and a soft shadow.
- **Soft shadow only**: black at 13% opacity, 15pt blur, 3pt offset straight down. Never a hard or diagonal shadow.
- **Pill bars**: single-series horizontal bars of 8 or fewer are drawn as rounded bars on a light track, with the value inside the bar (or just outside when the bar is short).
- **Ring nodes** (white circles with a dark ring; filled primary for the focus step) on a light connector line for process and timeline diagrams. Timeline cards alternate above and below the line.
- **White space is the design.** Keep 0.68 in side margins, titles at the top-left and nothing in the footer band (below 6.8 in) or the logo corner.

## Modern minimal principles (the build and lint enforce the starred ones)
- **White space is the design.** One idea per slide, generous margins, nothing within 0.55 in of the slide edge* (EDGE_MARGIN).
- **Crisp alignment.** Elements share exact left edges; nothing "almost" lines up* (NEAR_MISS).
- **One type scale.** Sibling elements (KPI values, labels, card titles, diagram labels, callouts, bar labels) share one size; the builder harmonizes them after auto-fit* (SIBLING_SIZE).
- **Hairlines, not borders.** Rules and outlines at 2.25 pt or lighter* (LINE_WEIGHT); dividers at 0.75 pt in `card_line`. Prefer space or a hairline over a box.
- **Quiet color.** Primary marks the one thing to look at, gray is context, dark is for breathers. No gradients, heavy shadows or decoration.
- **Exact alignment.** Every number marker is centered on its text's first line and sits flush with the text's left edge* (MARKER_ALIGN). Symmetric layouts (KPIs, cards, hero, shift, funnel, cycle, comparison, matrix, process, layers) sit on the slide's center line within 0.03 in* (CENTERED). Rows and panels span the full content width.
- **Callout cards.** White cards with a hairline border and a colored top bar: primary for an example, secondary for a tip, dark for a note, the alert color for a warning (it marks the one risk on the slide, reason `risk_warning`). The type is written as a word (EXAMPLE, TIP) with its default icon (book, bulb, info-circle, alert-triangle); meaning never rests on an icon or color alone. Colors outside the brand roles (for example a green from another template) are never used; use primary instead. Every accented box (insight box, callout, article and comparison cards) gets a rounded accent tab: the accent shape sits behind the card with the same corner radius and shows only on the accent side (ACCENT_STYLE, ACCENT_RADIUS).
- **Status tags.** A table cell that starts with a status in capitals (PASS, ACCEPTED) is drawn as a bold tag in the primary color* (STATUS_TAG).
- **Typographic polish.** Titles never leave one word alone on the last line* (ORPHAN); the builder steps a title down a point at a time and locks line breaks so PowerPoint wraps it the same way. Dates, quarters and numbered labels stay on one line ("Nov 17", "Q1 2027"). Blocks sit at the optical center, slightly above the middle of the body zone.
- **Content-sized containers.** Cards, comparison columns, steps and roadmap rows size to their content; no half-empty boxes.
- **Variety from layout, not ornament.** Change the layout, tone or side; never add new colors or fonts.

## Icons
Tabler outline only (https://icon-sets.iconify.design/tabler/, MIT; 210 ship in `assets/icons/tabler.json`; any other Tabler outline icon can be fetched from `https://api.iconify.design/tabler.json?icons=<names>` and saved next to deck.json as `icons.local.json`). The builder draws them as native, recolorable vector shapes with the 2 px Tabler stroke. Rules the lint enforces: known names only (ICON_UNKNOWN); on every item of a set or none (ICON_PARTIAL); never instead of numbers on numbered cards (ICON_CONFLICT); only on cards, callouts, contact rows, annotations, process/timeline/cycle/milestones nodes and hero statements (ICON_PLACEMENT); square, 0.2–0.8 in (ICON_SIZE); role colors only (primary on white, white on dark, the alert color only on a warning). An icon always sits beside a word; it never carries meaning alone. Pick the literal icon (calendar for dates, filter for filters, shield-check for compliance); if none fits, use no icon.

## Type (theme sizes are the defaults)
| Element | Font | Default | Auto-fit floor |
|---|---|---|---|
| Cover title (max two lines) | Display font, bold | 60pt | 40pt |
| Cover subtitle | Body font | 32pt | 24pt |
| Cover presenter and date | Body font | 14pt | — |
| Slide headline | Body font, regular | 32pt | 24pt |
| Subhead (comparison headings) | Body font, bold | 24pt | 16pt |
| Section title / closing title | Display font, bold | 48pt | 36pt |
| Statement | Display font, bold | 48pt | 32pt |
| Body, first-level bullets, takeaways | Body font | 20pt | 16pt |
| Second-level text, KPI and card labels, asks, screenshot callouts | Body font | 18pt | 14pt |
| Small labels, card detail (14–16pt), table text, chart labels | Body font | 14pt | 12pt |
| Big numbers | Display font, bold | 54pt | 32pt |
| Sources and footnotes | Body font | 10pt | — |
| Footer line and slide number (master) | Body font | 9pt | — |

- **Fonts** are the brand's `display` and `body` fonts (Fonts, above); FONT fails any other typeface in the built file.
- **Font-based layout.** Every measurement uses the font file itself: widths for wrapping and auto-fit, and the vertical metrics (line spacing from the font's ascent, descent and line gap; the first-line center from its ascent and cap height) for card and row heights, title bands and the alignment of numbers, icons and dots with their first lines. A looser font (Segoe UI, 1.33 line spacing) gets taller cards than a tight one (Arial, 1.15); markers stay centered on the first line in both. When the project's font has no file on the build machine, the deck still names it, text is measured with the fallback Inter, and the BRAND line says so.
- **Auto-fit**: each text box starts at its theme size and steps down 1pt at a time until it fits, never below the floor. Parallel headings (card titles) step down together until all of them fit one line, so a wider font costs a point or two instead of one wrapped title. Objects adapt too: timeline and process cards grow with their text, pill-bar rows and summary rows share the space evenly, and KPI numbers shrink to fit narrower cards. Anything that still doesn't fit fails the lint gate (TEXT_OVERFLOW). The fix is shorter copy, never a smaller floor.
- **Proper Case** for every heading and header: slide titles, cover and section titles and subtitles, the summary headline, labels, KPI labels, diagram labels, comparison headings, table headers and the closing title. Rule (AP style): capitalize principal words and any word of 4+ letters; lowercase *a, an, the, and, but, or, nor, for, so, yet, if, as, at, by, in, of, off, on, per, to, up, via, vs* unless first, last or after a colon. Acronyms (UAT, BAN) and numbers stay as written. The builder converts headings and the lint gate fails any heading that isn't in Proper Case (PROPER_CASE). Body text, bullets, takeaways, statements and notes stay in sentence case. No ALL-CAPS labels.
- Two-tone titles: `meta.title_accent` (cover) and `accent` (section, hero, contact) recolor 1–3 title words, in primary on white, `context` on dark or `card` on primary.
- If a deck's font isn't installed where the deck is opened, PowerPoint substitutes it, and spacing shifts with the substitute's metrics. For exact rendering, install the project's fonts, or the fallback fonts from `assets/fonts/` (free under the OFL), or use PowerPoint's **Embed fonts** option when saving.

## Never
Draw, import, recolor or stretch a logo (other than the automatic white knockout on dark slides), or put content in the logo corner or footer band; use gradients, hard shadows, 3-D, clip-art, filled or multicolor icons, icons from other sets, decorative blobs or stock photos; put white text on the alert color; use the alert color without a reason; use colors outside the role table above.
