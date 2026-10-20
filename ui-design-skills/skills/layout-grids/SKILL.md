---
name: "layout-grids"
description: "Defines structural grids, columns, gutters, margins, regions, alignment, content widths, and asymmetrical composition. Use when structuring pages, dashboards, editorial layouts, or major screen regions."
---

# Layout Grids

Use a structural grid to create coherent placement, hierarchy, and predictable alignment. This skill owns grid structure and alignment. Spacing values belong to `layout-spacing`; breakpoint behavior belongs to `responsive-layout`.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Grid anatomy

A grid is built from:

- **Columns:** placement fields that align content and components.
- **Gutters:** negative space between columns.
- **Margins:** outer space around the grid.
- **Regions:** meaningful groupings of columns, rows, or modules.

Gutters and margins may change as layout regimes change.

## Grid behavior

There is no one-size-fits-all grid.

- Use fixed, fluid, or hybrid behavior according to content and task.
- Prefer the available container width over assumed device identity when deciding a reusable component's local layout.
- A `12-column` grid is the default general-purpose fallback because it divides cleanly into halves, thirds, quarters, and sixths.
- Do not replace an established product grid merely to standardize on 12 columns.

## Grid types

### Column grid

Default for most application and web layouts. Align regions and components to shared vertical fields.

### Baseline grid

Useful when multiple text columns or repeated rows need a strong vertical rhythm.

### Manuscript grid

Use for reading-heavy content: one primary text column surrounded by margins. Prioritize readable line length over filling horizontal space.

### Modular grid

Use intersecting rows and columns for dashboards, dense structured content, and repeated modules.

## Regions and hierarchy

- Important content may occupy more grid area than supporting content.
- Do not force every panel to the same width or visual weight.
- Use unequal spans intentionally to reinforce hierarchy.
- Avoid dashboards made of equally sized cards when the information is not equally important.

## Alignment

- Align repeated elements to shared edges, columns, baselines, and planes.
- Text should usually share a consistent leading edge in the reading direction.
- Images, illustrations, and icons may align centrally relative to adjacent content when their bounding boxes are irregular.
- Use central composition deliberately when concentrating attention on a single focal region.
- Near-miss alignment is a defect: elements should align intentionally or differ intentionally.
- Optical alignment may override mathematically identical offsets.

## Content width

- Do not stretch prose simply because the viewport is wide.
- Use manuscript-like constraints for reading-heavy content.
- Let dense application and analytics regions use available width when task performance benefits.
- Forms and settings rows should not become harder to scan on large monitors.

## Asymmetrical composition

Asymmetry is encouraged when it improves hierarchy, but it must remain disciplined.

- Align asymmetrical regions to the underlying grid.
- Unequal column spans are valid.
- Unequal visual weight should be intentional.
- Do not use asymmetry as permission for arbitrary placement.

## Nested grids

A region may establish its own local grid when its internal structure requires it.

- Keep nested grid edges intentional relative to the parent region.
- Avoid excessive nesting that makes alignment relationships difficult to understand.
- Reusable components should respond to the container they receive rather than assuming full-page dimensions.

## Review checklist

Verify:

- columns, gutters, and margins form a coherent system;
- major regions align to shared structural lines;
- important regions receive appropriate area;
- content widths fit the task;
- asymmetry is grid-aligned;
- there are no accidental near-miss edges;
- nested grids are necessary and understandable.
