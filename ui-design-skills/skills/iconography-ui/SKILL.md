---
name: "iconography-ui"
description: "Defines UI icon-family selection, stroke/weight consistency, sizing, optical alignment, labeling, and icon accessibility. Use for navigation icons, actions, status symbols, empty states, and icon-system cleanup."
---

# UI Iconography

Use icons as functional symbols, not generic decoration. This skill owns icon-system decisions.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Family selection

- If the product already has a coherent icon family, preserve it.
- In an existing daisyUI application, preserve the project's established icon family rather than introducing a second one.
- When no icon system exists, prefer **Phosphor Icons** in Bold or Fill weights, or **Radix UI Icons**.
- Do not default to a mixture of icon libraries.

## Consistency

Standardize:

- visual weight;
- stroke or fill treatment;
- bounding-box size;
- optical size;
- baseline/center alignment;
- corner and terminal character where practical.

Do not mix thin-line and filled icons casually.

## Usage

- Prefer familiar symbols.
- Pair ambiguous icons with text labels.
- Use icons in buttons when they improve recognition, not merely to decorate every action.
- Icon-only buttons should be reserved for universally understood actions or constrained contexts.
- Decorative icons should be hidden from assistive technology.
- Functional icons require an accessible name, either directly or through the control that contains them.

## Emoji

Do not use emoji as product-interface icons unless the product's established language explicitly calls for them.

## Optical alignment

Icons often need optical rather than mathematical alignment.

- Account for internal whitespace inside the icon bounding box.
- Use `layout-spacing` optical exceptions when needed.
- Evaluate the visible glyph, not only its CSS box.

## Review checklist

Verify family consistency, weight, sizing, alignment, recognizability, labeling, and accessibility.
