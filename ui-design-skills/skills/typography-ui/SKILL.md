---
name: "typography-ui"
description: "Defines application typography, font families, type hierarchy, line-height, line length, tracking, numerals, and editorial contrast. Use for UI text, headings, labels, dashboards, landing pages, and typography polish."
---

# UI Typography

Typography is a primary visual-structure tool. This skill owns font and type-system decisions.

## Precedence

1. Explicit user typography requirements.
2. Accessibility, language, character-set, and platform requirements.
3. This skill's typography direction.

Unlike the other visual foundations, an existing product typeface does **not** automatically override this skill. Use the type direction below unless the user explicitly specifies another typeface or the required language/character set makes it unsuitable.

Color remains user/project-defined.

## Font roles

### Primary sans-serif

For body text, UI controls, labels, navigation, and buttons, prefer:

`SF Pro Display`, `Geist Sans`, `Helvetica Neue`, or `Switzer`, followed by an appropriate system fallback.

Do not default to `Inter`, `Roboto`, or `Open Sans`.

### Editorial serif

For hero headings, editorial statements, and quotations when stylistically appropriate, prefer:

`Lyon Text`, `Newsreader`, `Playfair Display`, or `Instrument Serif`.

### Monospace

For code, keyboard shortcuts, identifiers, and metadata, prefer:

`Geist Mono`, `SF Mono`, or `JetBrains Mono`.

## Type hierarchy

- Keep the scale restrained, usually about `5–7` clearly distinct steps.
- Each step should have a clear role rather than existing only for visual variety.
- Prefer size, weight, spacing, and placement for hierarchy before ornamental treatments.
- Use regular or medium body weights; reserve bold for meaningful emphasis.
- Avoid many competing weights and text styles on one screen.

## Line-height

- Display and large headings: approximately `1.0–1.2`.
- Body text: approximately `1.4–1.6`.
- Dense labels and controls may be tighter when readability remains strong.

## Measure

For body prose, target approximately `45–75` characters per line.

- Do not stretch reading text to fill a wide viewport.
- Dense tabular or application content is not prose and may use wider structures.

## Tracking

- Tighten display/large text approximately `-0.02em` to `-0.04em` when the chosen face supports it visually.
- Small caps and tiny labels may use slightly looser tracking.
- Avoid excessive letter spacing in normal body copy.

## Numerals

Use tabular numerals for aligned metrics, financial values, times, and comparable numbers when the typeface supports them.

## Editorial quality

- Avoid widows and awkward headline wrapping when practical.
- Keep headings concise and specific.
- Avoid uppercase paragraphs.
- Do not use typographic novelty that slows scanning or task completion.

## Review checklist

Verify hierarchy, line-height, measure, wrapping, weight consistency, numerical alignment, and legibility at zoom and narrow widths.
