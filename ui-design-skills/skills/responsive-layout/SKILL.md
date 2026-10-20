---
name: "responsive-layout"
description: "Defines responsive and adaptive layout behavior, breakpoints, container-aware composition, and the techniques reposition, resize, reflow, show/hide, and re-architect. Use for mobile, tablet, desktop, resize, and cross-window behavior."
---

# Responsive Layout

Design for available space without treating responsive design as "shrink the desktop screen." This skill owns breakpoint and adaptation behavior. Grid structure belongs to `layout-grids`; spatial values belong to `layout-spacing`.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Principles

- Preserve task completion and access to essential information at every supported size.
- Use viewport breakpoints for page-level composition and container-aware behavior for reusable regions when appropriate.
- Breakpoints represent layout needs, not device identities.
- Prefer a responsive, adaptive, or hybrid approach according to the task.
- Do not shrink text or controls below readable or accessible sizes merely to preserve a desktop composition.

## Reference breakpoint ranges

When the project has no breakpoint system, use these Fluent 2 ranges as reference defaults:

- `small`: `320–479px`
- `medium`: `480–639px`
- `large`: `640–1023px`
- `x-large`: `1024–1365px`
- `xx-large`: `1366–1919px`
- `xxx-large`: `1920px+`

Treat these as defaults, not mandatory thresholds. Prefer breakpoints at widths where the composition actually needs to change.

## Responsive vs adaptive

### Responsive

One composition changes fluidly as available space changes.

### Adaptive

The interface switches between materially different compositions at defined ranges.

### Hybrid

Use fluid behavior inside a layout regime and switch architecture when the task requires a different composition.

## Five responsive techniques

### Reposition

Move elements to preserve reading order, balance, and focus.

Examples:
- stacked controls become horizontal;
- secondary content moves beside primary content;
- actions move closer to the region they affect.

### Resize

Adjust dimensions and margins as space changes.

- Use additional whitespace on larger canvases when it improves balance.
- Preserve readable line lengths.
- Avoid oversized empty panels simply because more width exists.

### Reflow

Change arrangement to use available space efficiently.

Examples:
- one column becomes two;
- stacked cards become a grid;
- a side region moves below the main region.

### Show / hide

Adjust secondary information density.

- Essential actions and content must remain accessible.
- Hide only genuinely secondary information.
- Do not use hiding to avoid solving a difficult responsive layout.

### Re-architect

Change the composition itself when scaling or stacking would produce a poor experience.

Examples:
- desktop master-detail becomes a focused single-view flow;
- persistent secondary navigation becomes a contextual drawer;
- a multi-panel workspace becomes progressive disclosure.

## Overflow

- No accidental horizontal page scrolling.
- Intentional horizontal scrolling is acceptable for dense tables or categorical charts when it preserves readability and is clearly contained.
- Nothing essential should be clipped or unreachable.

## Input modality

- Preserve adequate touch targets on touch-capable layouts.
- Do not depend on hover for essential information.
- Adapt affordances when pointer precision or available space changes.

## Validation

Test representative narrow, medium, wide, and very wide layouts, including at least `320px` and `1920px` when the product supports them.

Verify long labels, localization, zoom, text expansion, large values, empty content, and overflow states.
