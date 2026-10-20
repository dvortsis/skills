---
name: "design-review"
description: "Runs a prioritized senior-level UI critique across hierarchy, spacing, grids, responsiveness, typography, geometry, iconography, motion, accessibility, component states, content, data visualization, and brand consistency. Returns concrete fixes ranked from blocking to polish."
---

# Design Review

Run a specific, measurable craft critique rather than a generic checklist dump.

## Review authority

When the corresponding skills are installed, evaluate against them:

- `layout-spacing`
- `layout-grids`
- `responsive-layout`
- `typography-ui`
- `component-geometry`
- `iconography-ui`
- `motion-ui`
- `application-interface-design`
- `analytics-chart-selection` when charts are present
- `analytics-validation` when analytical correctness or interactions must be verified
- `infographic-design` when explanatory infographics are present
- `dashboard-storytelling` when dashboards are present
- `data-visualization-design` when Tremor implementation is present
- `minimalist-visual-style` only when that style is intended

Existing product requirements and explicit user decisions remain authoritative.

Color choices belong to the user/product/project. Review contrast, consistency, semantics, and accessibility without imposing a palette.

## Visual hierarchy

- One clear focal point and obvious primary action where applicable.
- Scan path follows importance.
- Grouping follows proximity and task relationships.
- Important content has appropriate spatial and visual weight.

## Spacing and whitespace

- Grouping and hierarchy follow `layout-spacing` or the project's existing scale.
- Repeated patterns have coherent rhythm.
- Optical exceptions are intentional.
- Flag unexplained one-off spacing values when they break the system.

## Grid and alignment

- Major regions align to shared columns, edges, or baselines.
- Gutters and margins are internally consistent.
- Asymmetrical compositions remain structurally aligned.
- No near-miss alignment.
- Content width fits the task.

## Responsiveness

- No accidental horizontal page scroll, clipping, or overlap.
- Intentional horizontal scrolling for dense tables/charts is acceptable when clearly contained and accessible.
- Responsive changes use reposition, resize, reflow, show/hide, or re-architect intentionally.
- Essential content/actions remain available.
- Test common widths across approximately `320px–1920px+` where supported.

## Typography

- Font roles match `typography-ui` unless the user explicitly chose otherwise.
- Limited, distinct type scale.
- Display line-height approximately `1.0–1.2`; body approximately `1.4–1.6` when suitable.
- Body measure roughly `45–75` characters where applicable.
- Headline wrapping, numeral alignment, and weights are deliberate.

## Component geometry

Unless the user explicitly chose another system, verify:

- `16px` large-container radius;
- `12px` medium/default card radius;
- `8px` nested/button radius;
- `4px` small/tag radius;
- coherent borders and control heights;
- adequate touch targets.

## Iconography

- One coherent family.
- Consistent weight, size, and optical alignment.
- Ambiguous icons have labels.
- Functional icons are accessible.

## Motion

- Routine transitions approximately `150–250ms`.
- Larger/entrance transitions approximately `300–500ms`.
- Motion has a purpose and does not delay content.
- Reduced-motion behavior exists.
- No layout shift, jank, or blocking animation.

## Project-defined color and contrast

- Do not impose hues or a palette.
- Verify WCAG AA contrast: body text at least `4.5:1`; large text and essential UI/icon boundaries at least `3:1` where applicable.
- Do not rely on color alone for meaning.
- Disabled and placeholder states remain distinguishable without appearing active.

## Component states and accessibility

- Interactive elements have appropriate hover, focus-visible, active, disabled, and loading states.
- Loading, empty, error, and success states are designed where applicable.
- Semantic HTML precedes ARIA.
- Form labels/errors are correctly associated.
- Full keyboard operation and visible focus work.
- Zoom, text expansion, and reduced motion are supported.

## Content and copy

- Headlines are specific and scannable.
- CTA labels describe the action.
- Microcopy guides without clutter.
- UI state copy is truthful.

## Analytical charts

When charts exist, review chart choice and craft against `analytics-chart-selection`:

- the intended analytical question is clear;
- chart type fits the question and data shape;
- baselines, sorting, periods, aggregation, and missing values are honest;
- axes, data labels, legends, tooltips, annotations, and precision are appropriate;
- the chart is not more complex than the question requires;
- responsive behavior preserves interpretation.

When Tremor is used, also review implementation against `data-visualization-design`:

- installed component APIs were respected;
- values shown in geometry, axes, tooltips, and detail representations agree;
- interaction callbacks and state are implemented predictably;
- loading, empty, stale, and error states work;
- accessibility alternatives exist when needed.

## Dashboard storytelling

When reviewing a dashboard, also evaluate against `dashboard-storytelling`:

- the first viewport establishes the 50,000-foot state;
- the narrative progresses from status to trend to drivers/segments to exceptions/detail as appropriate;
- each visual answers a distinct useful question;
- global versus local filter scope is clear;
- parameter use is distinct from filtering;
- cross-filter, cross-highlight, drill-down, drill-through, and navigation behavior is intentional;
- active selections are visible and resettable;
- the interaction model does not produce surprising or circular state changes.



## Analytical correctness

When analytical correctness is in scope, use `analytics-validation`.

Design review must not infer numerical correctness from appearance.

Require validation evidence for:
- source reconciliation of critical KPIs/charts;
- same-metric consistency across visuals;
- filter results;
- cross-filter/cross-highlight actions;
- parameter switches;
- drill paths;
- reset behavior.

A visually polished dashboard with incorrect or unreconciled values is a blocking failure.


## Infographics

When an infographic is present, review against `infographic-design`:

- an infographic is the correct communication form;
- information structure matches the message;
- sequence, hierarchy, comparison, or relationship is immediately understandable;
- text remains concise;
- icons are meaningful and consistent;
- visual styling matches the product rather than AntV defaults;
- narrow layouts preserve reading order;
- essential meaning has an accessible semantic equivalent;
- a chart/table/prose/technical diagram would not communicate the content more directly.


## Report format

Group findings by severity, most important first. Lead with the few that matter.

For each finding provide:

- **What:** exact issue and element.
- **Why:** one-line usability, accessibility, or craft reason.
- **Fix:** concrete change, preferably a token or exact value when objective.

Severity:

- **Blocking:** broken, inaccessible, fails required standards, or unusable on a target layout.
- **Important:** materially harms hierarchy, readability, usability, responsiveness, or consistency.
- **Polish:** refinement that improves craft without blocking use.

End with:

- **Strengths:** 2–4 things done well.
- **Highest-leverage change:** the single most useful next fix.

## Applying fixes

When asked to apply changes:

- automatically apply clear, safe findings such as spacing-token corrections, radius consistency, contrast, focus states, reduced-motion support, semantic structure, labels, and alt text;
- leave subjective or structural redesigns as recommendations unless the user asked for redesign;
- re-verify measurable values after editing.

## Provenance

Refactored from the supplied `superfuture-design-review` skill, which credited the original design-review skill at https://crit.officialjp.com.
