---
name: "component-geometry"
description: "Defines component radii, borders, sizing, control heights, touch targets, containment, and geometry consistency. Use for cards, buttons, dialogs, sheets, tags, fields, banners, nested components, and geometry polish."
---

# Component Geometry

This skill owns component shape and physical sizing. Spacing belongs to `layout-spacing`; color belongs to the product; typography belongs to `typography-ui`.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Global radius system

Unless the user explicitly specifies another radius system:

- `16px`: large containers such as sheets and dialogs.
- `12px`: default medium components such as cards, snack bars, and banners.
- `8px`: medium or small nested components such as buttons and controls.
- `4px`: small components such as tags.

Do not use `rounded-full` for large containers, cards, or primary buttons. Reserve pill geometry for controls whose semantics genuinely call for it.

## Borders

- When a component uses a border, prefer one clear `1px` solid border using the project's border token.
- Preserve an established borderless or surface-separated product pattern instead of forcing borders everywhere.
- Do not stack borders simply to create visual complexity.
- Dividers should communicate a real structural separation; use whitespace when it is sufficient.

## Controls

- Similar controls in the same context should have consistent visible heights.
- Keep icon and text alignment optically balanced.
- Avoid width changes when a button enters loading state.
- Use minimum and maximum widths intentionally.
- Define recurring heights, radii, borders, and size variants once in shared tokens or canonical primitives. Do not repeat equivalent geometry recipes across page-level components.
- Extend an existing component variant before creating a second primitive whose only distinction is geometry.

## Touch targets

Where touch input is plausible:

- iOS/Web target: at least about `44 × 44` CSS pixels.
- Android target: at least about `48 × 48` density-independent pixels.

The visible glyph can be smaller than the interactive target.

## Cards

- Use cards for coherent concepts or actions, not as the default wrapper for every section.
- Default radius: `12px`.
- Keep sibling geometry consistent.
- Avoid deeply nested cards; use spacing, dividers, or subtle surface separation instead.

## Buttons

- Default radius: `8px`.
- Follow existing product conventions for variant hierarchy.
- In daisyUI projects, use the project's semantic button variants rather than introducing custom palette values.

## Dialogs and sheets

- Default large-container radius: `16px`.
- Size the surface for its content and task.
- Avoid large empty surfaces and tiny internal scrolling panes.

## Tags

- Default radius: `4px`.
- Pill geometry is optional only when the semantics or established product language clearly call for it.

## Elevation

This skill does not define a shadow palette or elevation scale.

- Preserve the existing product's elevation language.
- Avoid combining border, heavy shadow, glow, and decorative surface treatment on one component without a clear reason.

## Review checklist

Verify radius consistency, border consistency, control heights, hit targets, containment, nested-component geometry, loading-state stability, and that recurring geometry is controlled from one shared source rather than duplicated across components.
