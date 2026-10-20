---
name: "minimalist-visual-style"
description: "Applies a premium utilitarian editorial-minimalist visual direction without owning layout mechanics, color palettes, typography rules, icon systems, geometry, or motion timing. Use when the user wants a clean, modern, restrained, document-style interface or when no coherent product visual language exists."
---

# Minimalist Visual Style

Apply a calm, editorial, utilitarian aesthetic while deferring technical decisions to the subject-specific foundation skills.

## Precedence

1. Explicit user requirements.
2. Accessibility and functional correctness.
3. A coherent existing product visual language.
4. This style skill when no coherent product visual language exists or when the user explicitly requests this aesthetic.

Typography is an intentional exception: use `typography-ui` for the prescribed font direction unless the user explicitly specifies another typeface.

Color is always defined by the user/product/project.

## Companion skills

Do not redefine their rules here:

- `layout-spacing`
- `layout-grids`
- `responsive-layout`
- `typography-ui`
- `component-geometry`
- `iconography-ui`
- `motion-ui`

## Aesthetic principles

- Favor a document-like, editorial hierarchy over generic SaaS ornamentation.
- Prefer flat, restrained surfaces and deliberate structure.
- Let typography, whitespace, alignment, and scale carry hierarchy.
- Use asymmetrical bento-style compositions when they improve hierarchy, but align them to `layout-grids`.
- Use cards only for meaningful grouping.
- Avoid decorative complexity that does not improve comprehension.

## Negative constraints

- **Do not use gradients.**
- Do not use neon effects or 3D glassmorphism.
- Avoid heavy drop shadows; preserve only restrained project elevation when useful.
- Do not use large pill-shaped containers or primary buttons unless the product language explicitly requires them.
- Do not use emoji in product-interface copy, headings, markup, or alt text unless the product language explicitly calls for emoji.
- Do not use generic placeholders such as `John Doe`, `Acme Corp`, or `Lorem Ipsum` in polished UI examples.
- Avoid AI-copy clichés such as `Elevate`, `Seamless`, `Unleash`, `Next-Gen`, `Game-changer`, and `Delve`.

## Imagery

- Use imagery only when it supports comprehension, context, hierarchy, or brand expression.
- Prefer high-quality, intentionally cropped photography.
- Keep illustration style coherent across a product.
- Do not add decorative backgrounds merely because a section feels empty.
- Do not use gradients as background depth.

## Density and whitespace

Use `layout-spacing` as the authority.

Within its allowed system:

- favor the roomier end for editorial or marketing surfaces;
- keep productivity controls and analytics regions appropriately compact;
- use whitespace as hierarchy rather than as decoration.

## Composition

- Prefer clear focal points and strong scale contrast.
- Avoid a uniform grid of same-sized cards when hierarchy calls for unequal weight.
- Favor crisp shared edges and controlled asymmetry.
- Keep surfaces visually quiet enough that content remains dominant.

## Execution

1. Inspect the existing product visual system.
2. Preserve it if coherent unless the user explicitly requests the minimalist direction.
3. Apply `typography-ui`.
4. Use project-defined color only.
5. Defer spatial, grid, responsive, geometry, icon, and motion decisions to their subject skills.
6. Remove decorative elements that do not improve comprehension or brand expression.
7. Verify the result still feels native to the product rather than like a pasted template.
