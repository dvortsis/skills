---
name: "layout-spacing"
description: "Defines spacing, proximity, whitespace hierarchy, density, and spatial rhythm for modern interfaces. Use when deciding gaps, padding, grouping, section separation, or whether whitespace can replace visual dividers."
---

# Layout Spacing

Use space to communicate relationships, hierarchy, rhythm, and focus. This skill owns spacing and whitespace decisions. Grid structure belongs to `layout-grids`; breakpoint behavior belongs to `responsive-layout`.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Core principles

- Elements in close proximity are perceived as related.
- Increasing distance weakens the perceived relationship.
- Repeated spacing patterns imply equal weight and connection.
- Use whitespace to form logical groups before adding borders, boxes, or dividers.
- Whitespace is structural, not leftover space.
- More surrounding whitespace generally increases visual prominence.
- Dense information can be appropriate, but avoid making the entire screen uniformly dense.
- Use roomy whitespace around focal regions and major transitions, while keeping tightly related controls compact.

## Default spacing ramp

When the product does not already define a spacing scale, use this Fluent 2-inspired ramp:

`0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 28, 32, 36, 40, 48, 52, 56`

The base unit is `4px`. The `2px`, `6px`, and `10px` values are supported optical exceptions for fine internal alignment, including icons.

Do not introduce arbitrary values when a supported spacing token can express the same relationship.

## Structural levels

### Component spacing

Use smaller values inside a component so its parts read as one unit while remaining distinct.

### Pattern spacing

Use repeated values across recurring structures to create familiar rhythm.

### Layout spacing

Use larger values to separate regions, direct attention, and establish hierarchy.

### Responsive spacing

Spacing may change when available space changes. Use `responsive-layout` to decide when and why.

## Optical adjustment

Consistency is a tool, not a mechanical goal.

- Prefer visual alignment over blindly repeating the same spacer.
- Adjust spacing when equal numeric values produce visibly unequal balance.
- Text and icons may require different offsets because bounding boxes differ.
- Typography metrics, borders, chart geometry, and optical correction do not have to use spacing-ramp values when another value is functionally correct.

## Density

- Touch-heavy interfaces should generally be roomier than dense productivity or analytics surfaces.
- Dense data regions may remain compact when scanning efficiency benefits.
- Use larger whitespace between dense regions so the page still has hierarchy and breathing room.
- Do not increase whitespace so much that related controls feel disconnected or routine tasks require excessive scrolling.

## Review checklist

Before finishing, verify:

- related elements are closer than unrelated elements;
- whitespace creates visible grouping and hierarchy;
- repeated patterns share a consistent rhythm;
- large gaps express intentional hierarchy rather than decoration;
- dense regions are locally dense, not globally overwhelming;
- one-off values are justified by optical or functional needs.
