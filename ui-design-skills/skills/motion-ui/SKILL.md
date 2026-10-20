---
name: "motion-ui"
description: "Defines UI motion duration, easing, entrance behavior, staggered reveals, performance, reduced-motion support, and interaction animation. Use for transitions, hover/active feedback, scroll entry, modal motion, and animation polish."
---

# UI Motion

Motion should explain change, hierarchy, or continuity without delaying work. This skill owns motion behavior.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Durations

- Routine UI transitions: generally `150–250ms`.
- Larger or entrance transitions: generally `300–500ms`.
- Avoid slower motion unless the interaction genuinely requires it.

## Easing

- Prefer ease-out for entering elements.
- Prefer ease-in for exiting elements.
- Avoid linear easing except for continuous motion where constant velocity is intentional.

## Access to content

Never delay access to content or essential interaction for an entrance animation.

- The interface must remain usable when animation is disabled.
- Do not block input until decorative animation completes.

## Staggered reveals

When staggered reveals improve scan order:

- sequence non-critical item mounts rather than mounting every staggered item simultaneously;
- use small cascade delays, around `80ms` when appropriate;
- never withhold critical information, navigation, primary actions, or required form controls;
- the reduced-motion path should make all required content available immediately.

## Performance

- Prefer `transform` and `opacity`.
- Avoid animating layout-triggering properties such as `top`, `left`, `width`, and `height` when an equivalent transform is possible.
- Avoid layout shift, jank, and animation that causes repeated expensive reflow.
- Use `will-change` sparingly and only for actively animating elements.

## Interaction feedback

- Hover, focus-visible, active, loading, and state-transition motion should reinforce state changes.
- Active buttons may use a subtle scale response such as `scale(0.98)` when appropriate.
- Do not reanimate an entire dashboard after every small filter change.

## Reduced motion

Honor `prefers-reduced-motion`.

Provide a reduced or immediate variant that preserves meaning and functionality.

## Prohibited stylistic motion

- Do not use ambient gradient animation.
- Avoid motion that exists only to make an otherwise static page look "alive."
- Do not add parallax or continuous motion without a clear task or communication benefit.

## Review checklist

Verify purpose, duration, easing, reduced-motion behavior, content availability, jank, layout stability, and interaction responsiveness.
