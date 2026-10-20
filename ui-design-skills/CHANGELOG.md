# Changelog

## Subject-specific refactor

- Replaced five broad skills with eleven subject-specific skills.
- Added one canonical owner for each foundational design subject.
- Preserved Fluent 2 spacing, whitespace, grid, alignment, and responsive principles while separating them into appropriate skills.
- Preserved the agreed global radius system: 16 / 12 / 8 / 4px.
- Preserved 150–250ms routine motion and 300–500ms larger/entrance motion.
- Preserved the rule that entrance animation never delays content access.
- Preserved staged mounting for non-critical staggered reveals with accessibility safeguards.
- Preserved intentional horizontal scrolling for dense charts/tables.
- Preserved restrained `shadow-sm` chart-container guidance.
- Preserved project/user ownership of color and theme mode.
- Preserved daisyUI semantic-token usage when daisyUI is used.
- Preserved existing product icon systems, with Phosphor Bold/Fill or Radix as fallback.
- Preserved the editorial/minimalist typography direction as its own canonical skill.
- Preserved the minimalist no-gradient rule.
- Added `MIGRATION.md` and updated `README.md` for `npx skills` installation.

## Packaging fix

- Canonical package root renamed to `ui-design-skills`.
- Quoted all YAML front-matter scalar values across every skill to prevent parse failures from punctuation such as colons.
- Validated all 11 `SKILL.md` front-matter blocks with a YAML parser before packaging.


## Analytics specialization

- Added `analytics-chart-selection`.
- Added `dashboard-storytelling`.
- Refactored `data-visualization-design` into the canonical Tremor implementation/API layer.
- Added an analytical question-first chart decision framework.
- Added guidance for KPI, trend, category comparison, composition, relationship, distribution, progress, funnel, tracker, combo, sparkline, and exact-lookup use cases.
- Added chart-craft guidance for axes, sorting, gridlines, labels, legends, tooltips, annotations, missing data, precision, and responsive behavior.
- Added dashboard narrative guidance from 50,000-foot status through trend, drivers, segmentation, exceptions, and detail.
- Added explicit guidance for global/local filters, parameters, cross-filtering, cross-highlighting, drill-down, drill-through, navigation, click/select actions, selection visibility, and reset behavior.
- Updated `design-review` to review chart-selection, dashboard-storytelling, and Tremor implementation as separate concerns.
- Package now contains 13 subject-specific skills.


## AntV Infographic integration

- Added `infographic-design`.
- Package now contains 14 subject-specific skills.
- Added explicit routing between analytical charts and explanatory infographics.
- Added information-structure guidance for lists, sequences, timelines, comparisons, hierarchies, relationships, cycles, and grouped/matrix structures.
- Added AntV Infographic implementation guidance for declarative syntax, custom templates, curated template registries, project-controlled themes, SVG resources, responsive layouts, and accessible fallbacks.
- Added restrictions preventing AntV's decorative defaults from overriding the product design system.
- `minimalist-visual-style` constraints continue to prohibit gradients and decorative effects when active.
- Updated `analytics-chart-selection`, `dashboard-storytelling`, and `design-review` to recognize `infographic-design` as the canonical infographic owner.


## Analytics validation

- Added `analytics-validation`.
- Package now contains 15 subject-specific skills.
- Added source-of-truth metric contracts and expected-value reconciliation.
- Added dashboard baseline validation and chart-to-source validation.
- Added chart-to-chart/KPI/table consistency checks.
- Added filter, multi-filter, click-action, cross-filter, cross-highlight, parameter, drill-down, drill-through, reset, and state-persistence validation.
- Added grain, timezone, null, distinct-count, stale-data, security-context, and asynchronous-state mismatch triage.
- Added validation-matrix and expected-versus-actual reporting guidance.
- Added test-layer guidance for unit, data/query, component, and end-to-end tests.
- Updated `analytics-chart-selection`, `dashboard-storytelling`, `data-visualization-design`, and `design-review` to hand off analytical correctness to `analytics-validation`.
