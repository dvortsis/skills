---
name: "application-interface-design"
description: "Designs and implements production application UX: navigation, forms, tables, lists, dialogs, drawers, popovers, feedback, loading/empty/error states, semantics, keyboard behavior, and daisyUI/Tailwind implementation. Use for application screens and workflows."
compatibility: "Intended primarily for Tailwind CSS and daisyUI projects; verify installed versions and project conventions before editing."
---

# Application Interface Design

Create application interfaces that optimize comprehension, task completion, and robustness rather than decoration.

## Precedence

Apply these rules in order:

1. Explicit user requirements.
2. Accessibility, platform behavior, and functional correctness.
3. A coherent existing product or design system, except where another installed subject skill explicitly owns the decision.
4. This skill's defaults.

Color choices belong to the user, product, or project. Do not invent a product palette, accent hue, surface palette, or light/dark theme requirement.


## Use companion foundations

When available, defer subject decisions to:

- `layout-spacing` for spacing and whitespace;
- `layout-grids` for grid structure and alignment;
- `responsive-layout` for breakpoint behavior;
- `typography-ui` for fonts and type hierarchy;
- `component-geometry` for radii, borders, hit targets, and component sizing;
- `iconography-ui` for icon systems;
- `motion-ui` for animation.

If no coherent product visual language exists, `minimalist-visual-style` may provide the aesthetic layer.

## Start with context

Before changing UI:

1. Inspect layout, theme configuration, component patterns, breakpoints, and package versions.
2. Reuse established primitives and semantic tokens when sound.
3. Identify the primary user goal, primary action, information hierarchy, and important states.
4. Preserve business logic, accessibility, framework behavior, and data semantics.

## Visual hierarchy

- Give every screen one clear primary purpose and usually one dominant action.
- Keep secondary actions quieter than primary actions.
- Use destructive treatment only for destructive actions.
- Group controls according to task relationships.
- Avoid making every piece of information look equally important.

## daisyUI and Tailwind

- Prefer daisyUI components and semantic modifiers when they meet the need.
- Verify syntax against the installed daisyUI version.
- Extend with Tailwind utilities rather than recreating standard components unnecessarily.
- Keep class strings understandable and extract repeated compositions when repetition becomes meaningful.
- When using daisyUI, use the project's semantic tokens instead of hard-coded product colors.
- Validate every theme the project actually supports. Do not impose light or dark mode.

## Component architecture and reuse

Optimize for the smallest coherent component system that makes app-wide UI changes safe and fast.

- Audit the existing component layer before creating anything. Reuse or extend a suitable primitive rather than adding a near-duplicate.
- Put broadly reused appearance and interaction behavior in the application's established UI component layer. If the repository has a shared design-system package, place product-agnostic primitives there only when its ownership, consumers, and release model support the change.
- Keep page-specific compositions close to the feature. Promote them only after a stable pattern appears in multiple places or centralization provides a clear maintenance benefit.
- Prefer a small component with explicit variants, slots, or composition over several components that differ only in classes, size, icon placement, or minor markup.
- Centralize visual decisions in semantic tokens, theme configuration, component variants, and shared primitives. Avoid repeating long utility-class recipes across pages when a single change should update the whole app.
- Use one canonical primitive for each common role, such as button, field, card, dialog, banner, badge, and empty state. Consolidate competing implementations when it can be done safely within scope.
- Keep component APIs narrow and semantic. Do not expose arbitrary styling knobs merely to accommodate one screen; prefer composition and well-named variants.
- Preserve accessibility, behavior, and state handling inside the shared primitive so consumers do not reimplement them.
- Avoid premature abstraction. Similar-looking elements with different semantics or behavior do not have to share a component.
- Do not create pass-through wrappers that add no meaningful behavior, policy, or stable styling contract.
- When modifying a repeated pattern, update its canonical primitive or token first and migrate consumers when practical instead of applying page-by-page patches.
- Prefer composition, slots, and small focused primitives over a universal component with many unrelated boolean props.
- Separate reusable behavior and semantics from feature-specific data fetching, permissions, routing, and business rules.
- Keep dependency direction one-way: feature components may consume shared UI primitives; shared primitives must not depend on feature modules.
- Use semantic variant names such as `primary`, `danger`, `compact`, or `quiet` rather than page names or raw visual descriptions that leak implementation details.
- Keep variants finite and intentional. If every consumer requires a unique variant, reconsider the primitive boundary or the underlying token system.
- Preserve native HTML behavior and support refs, names, IDs, form attributes, keyboard input, and assistive technology when wrapping native controls.
- Treat responsive behavior as part of the component contract only when it is intrinsic to that component. Keep page-layout decisions with the page or layout primitive.
- Add or update focused tests and usage examples for shared primitives when the repository already maintains them, especially for keyboard behavior, state transitions, and variants.
- Make breaking shared-component changes deliberately: inspect consumers, preserve compatibility when inexpensive, and migrate all affected call sites within the authorized scope.

Before adding a new reusable component, answer:

1. Does an existing primitive or variant already cover this need?
2. Will centralizing it remove meaningful duplication or enable a likely app-wide change?
3. Is its API based on stable semantics rather than the needs of one page?
4. Can the existing component count be reduced by extending or consolidating instead?

Do not optimize for the lowest possible file count. Optimize for the fewest clear, stable concepts: enough reuse for global consistency, enough locality for feature code to remain understandable.

## Navigation

- Make current location unmistakable without overpowering content.
- Keep top-level navigation short and stable.
- Move infrequent actions into a clearly labeled overflow menu.
- Preserve access to essential destinations at narrow widths.

## Buttons and actions

- Use one primary action per decision area when practical.
- Use outcome-oriented labels: `Save changes`, not `Submit`.
- Prevent duplicate submission.
- Show progress without causing layout shift.
- Icon-only actions need an accessible name and usually a tooltip.

## Forms

- Keep labels visible; placeholders are hints, not labels.
- Put help and validation near the related field.
- Validate at a useful moment and preserve entered values after errors.
- Group related fields and progressively reveal advanced controls.
- Avoid multi-column forms when reading or keyboard order becomes ambiguous.
- Use correct input types, autocomplete, labels, descriptions, and error associations.

## Tables and lists

- Use tables for genuinely tabular comparison.
- Use lists or cards for heterogeneous content.
- Align numeric values consistently and keep units explicit.
- Make row actions discoverable without turning every row into a toolbar.
- Add sorting, filtering, pagination, sticky headers, or horizontal scrolling only when data warrants them.
- Define loading, empty, error, and no-results states separately.

## Cards

- Use cards for coherent concepts or actions, not as the default wrapper for every section.
- Avoid deeply nested cards.
- Follow `component-geometry` for card radius and border behavior.

## Dialogs, drawers, and popovers

- Use a modal only when users must complete or dismiss a focused interruption before continuing.
- Use drawers for contextual workflows that benefit from retained page context.
- Use popovers for brief content anchored to a trigger.
- Do not put long, multi-step, highly navigational workflows in small modals.
- Provide clear title, purpose, predictable actions, initial focus, focus trapping, Escape behavior, and focus restoration.
- Confirm destructive or irreversible actions specifically; do not confirm routine reversible actions.

## Feedback and states

- Show immediate feedback near the action that caused it.
- Use skeletons when structure is known, spinners for short indeterminate work, and progress indicators for measurable longer work.
- Use toasts for non-blocking confirmation, not critical information requiring action.
- Empty states should explain the situation and offer one relevant next step.
- Make disabled states understandable; explain prerequisites when useful.
- Reserve layout space for asynchronous content and validation where practical.

## Accessibility and robustness

- Use semantic HTML before ARIA.
- Ensure complete keyboard operation, visible focus, sensible focus order, and no keyboard traps.
- Associate labels, descriptions, errors, headings, landmarks, and table headers correctly.
- Do not remove browser affordances without an equal or better replacement.
- Test zoom, text expansion, long labels, localization, empty values, large datasets, and narrow layouts.
- Do not communicate status through color alone.
- Maintain required contrast using the project's color system.

## Quality check

Verify the primary task, keyboard/focus behavior, all important states, real-data resilience, narrow layouts, theme compatibility, and consistency with the established product.
