---
name: "infographic-design"
description: "Chooses when explanatory information should be presented as an infographic rather than a chart, table, prose block, or technical diagram, then designs and implements a restrained AntV Infographic composition that follows the product's existing visual system."
compatibility: "Intended for projects using @antv/infographic. Verify the installed package version and APIs before implementation. Existing product design systems, accessibility requirements, and user-provided visual direction take precedence."
---

# Infographic Design

Design explanatory visuals that compress structured information into a clear visual story.

This skill is the canonical owner for:
- deciding when an infographic is the correct communication form;
- selecting an infographic information structure;
- designing explanatory sequences, comparisons, hierarchies, relationships, timelines, cycles, and feature stories;
- mapping structured content into AntV Infographic syntax;
- choosing or registering AntV templates;
- constraining AntV themes to the product's design system;
- deciding icon, label, description, value, and annotation use inside infographics;
- infographic-specific responsive and accessibility behavior.

This skill does **not** own:
- quantitative analytical chart selection: use `analytics-chart-selection`;
- dashboard narrative and cross-visual interaction: use `dashboard-storytelling`;
- Tremor chart implementation: use `data-visualization-design`;
- application layout foundations: use `layout-spacing`, `layout-grids`, and `responsive-layout`;
- typography, geometry, icons, or motion globally: defer to the relevant foundation skills.

## Precedence

1. Explicit user requirements.
2. Existing coherent product/design system.
3. Accessibility and semantic clarity.
4. The communication goal and information structure.
5. This skill's defaults.

Do not use an infographic merely because it looks more polished than prose.

## Decide whether an infographic is appropriate

Use an infographic when the primary task is to explain structured information visually.

Strong use cases include:
- process or workflow;
- sequence of steps;
- timeline or chronology;
- customer or user journey;
- lifecycle;
- before/after comparison;
- side-by-side conceptual comparison;
- hierarchy;
- taxonomy;
- relationship map;
- cycle;
- feature map;
- conceptual architecture summary;
- ranked explanatory list;
- multi-step methodology;
- metric story where the values support an explanatory narrative rather than quantitative analysis.

Do **not** use an infographic when the primary task is:
- comparing quantitative magnitudes precisely;
- analyzing a time series;
- inspecting distribution;
- identifying correlation;
- looking up exact records;
- scanning a dense operational table;
- editing or manipulating a node graph;
- documenting a technical sequence better represented by a formal diagram language.

Use instead:
- `analytics-chart-selection` for quantitative analytical visuals;
- a table for exact lookup or dense records;
- prose for simple explanations that do not gain meaning from spatial structure;
- Mermaid or a technical-diagram tool for formal engineering/documentation diagrams;
- React Flow or a node-edge interaction library for interactive graph editors/workflows.

## Infographic versus analytical chart

Choose an infographic when **structure and narrative** carry more meaning than quantitative position or length.

Choose a chart when the user must judge:
- magnitude;
- trend;
- distribution;
- correlation;
- variance;
- rank;
- part-to-whole quantitatively.

Examples:

- `Five steps in the referral workflow` → infographic.
- `Referral volume by month` → chart.
- `How a lead moves from acquisition to retention` → infographic.
- `Conversion rate by funnel stage` → analytical chart or funnel chart, depending on the question.
- `Roles in the operating model` → infographic/hierarchy.
- `Headcount by role` → bar chart.
- `Architecture overview for nontechnical stakeholders` → infographic.
- `Exact service dependencies` → technical diagram.

When a visual contains quantitative data but the narrative structure dominates, the infographic may include values as supporting annotations. Do not use decorative value displays as a substitute for a real analytical chart.

## Infer the information structure

Before selecting a template, classify the content.

### List

Use for:
- peer concepts;
- features;
- principles;
- categories;
- ranked explanatory items.

A list should not imply order unless order matters.

### Sequence

Use for:
- process;
- steps;
- lifecycle;
- ordered stages;
- chronological flow.

Show direction clearly.

### Timeline

Use when elapsed time or chronology is central.

Include dates or time markers only when meaningful.

Do not fake a timeline for items that are merely sequential.

### Comparison

Use for:
- before versus after;
- option A versus option B;
- old versus new;
- paired concept comparison.

Keep dimensions parallel.

### Hierarchy

Use for:
- organizational structure;
- taxonomy;
- decomposition;
- parent-child conceptual relationships.

Avoid deep trees when a collapsed or staged explanation would be clearer.

### Relationship

Use when the central message is how concepts connect rather than their order.

Keep edge meaning explicit.

Do not use relation layouts for arbitrary decoration.

### Cycle

Use only when the process genuinely repeats or feeds back into itself.

Do not turn a linear process into a cycle for visual novelty.

### Matrix or grouped structure

Use when two dimensions define meaningful categories or when information is best understood as grouped blocks.

Do not use a matrix if a simple list communicates the same thing more clearly.

## AntV Infographic implementation model

AntV Infographic separates:
- **information structure/data** from
- **graphic semantics/design**.

Use that separation deliberately.

Prefer:
- reusable templates for repeated product patterns;
- project-controlled themes;
- structured data;
- centralized wrappers/components.

Do not scatter raw AntV syntax and arbitrary theme overrides throughout the application.

## Recommended application architecture

Wrap AntV behind a product-level component.

Example conceptually:

```tsx
<AppInfographic
  template="process-horizontal"
  data={data}
  ariaLabel="Referral workflow from intake to activation"
/>
```

The wrapper should own:
- AntV initialization;
- project theme mapping;
- typography mapping;
- icon/resource loading;
- responsive sizing;
- accessibility fallback;
- allowed template registry;
- safe defaults.

Feature code should provide structured content, not arbitrary visual styling.

## Curated template registry

Do not expose the entire AntV template catalog directly to agents or product code.

Create a curated registry with semantic names such as:

- `process-horizontal`
- `process-vertical`
- `timeline`
- `comparison`
- `hierarchy`
- `sequence`
- `cycle`
- `relationship`
- `feature-map`
- `metric-story`

Each curated template should map to a vetted AntV template or custom template.

The semantic name should describe the communication structure, not the AntV implementation detail.

## Custom templates

Use `registerTemplate` when a recurring product pattern deserves a stable layout.

A custom template should define:
- structure;
- item treatment;
- title treatment;
- spacing;
- icon behavior;
- other reusable layout decisions.

Do not bake page-specific copy or arbitrary brand styling into a reusable template.

Register templates centrally.

## Theme discipline

The user/product owns color.

The infographic theme must map to:
- project typography;
- project color tokens;
- project iconography;
- project geometry;
- project spacing;
- supported theme modes.

When daisyUI is used, map to the project's semantic tokens or a centralized theme adapter.

Do not create an independent infographic brand inside the product.

## Minimalist visual constraints

When `minimalist-visual-style` is active:

- do not use gradients;
- do not use hand-drawn/rough stylization;
- do not use neon or decorative multicolor palettes;
- do not use heavy shadows;
- do not use 3D effects;
- do not use ornamental backgrounds;
- do not use decorative icons without informational value;
- keep borders, geometry, and spacing consistent with the shared product system;
- prefer flat SVG shapes, restrained connectors, and strong typography.

AntV supports decorative features, but availability does not make them appropriate.

## Typography

Use `typography-ui`.

Within an infographic:
- titles should establish the concept quickly;
- labels should be concise;
- descriptions should be short enough to scan;
- values should use appropriate numeric formatting;
- avoid paragraph-length text inside nodes/cards.

If a node requires a paragraph, the content likely needs restructuring.

## Icons

Use `iconography-ui`.

Icons should:
- aid recognition;
- use one coherent family;
- have consistent visual weight;
- remain secondary to the text when the concept is not universally recognized.

Do not auto-map ambiguous icons without reviewing the result.

Use AntV resource loaders or project-controlled SVG assets when needed.

## Spacing and layout

Use `layout-spacing` and `layout-grids`.

Within the infographic:
- proximity should communicate grouping;
- repeated items should use consistent spacing;
- sequence direction should be obvious;
- labels and descriptions should align predictably;
- empty space should separate conceptual groups;
- avoid dense ornamentation.

The infographic itself should align to the surrounding application grid.

## Geometry

Use `component-geometry`.

Do not create a separate radius system for infographic cards/nodes.

Use product borders and geometry.

Connectors and arrows should remain visually subordinate to the content unless the relationship itself is the primary message.

## Data and content modeling

Prefer structured data with explicit fields such as:
- `label`;
- `desc`;
- `value`;
- `time`;
- `icon`;
- nodes and relations where applicable.

Avoid embedding presentational syntax inside user-facing content strings.

Keep labels short and specific.

Do not use generic filler text.

## Infographic syntax

AntV Infographic uses a declarative syntax that combines template/design, data, and theme.

Use syntax generation when:
- the visual is generated dynamically;
- AI is authoring the visual;
- streaming rendering is useful;
- the content is easier to express declaratively.

Keep syntax generation deterministic where possible.

Do not let untrusted user input inject arbitrary theme or resource configuration without validation.

## AI-generated infographics

AntV syntax is suitable for AI generation and streaming rendering.

When an agent generates an infographic:

1. infer the communication goal;
2. select the information structure;
3. choose an approved semantic template;
4. generate structured content;
5. validate required fields;
6. render;
7. visually inspect the result;
8. revise overflow, hierarchy, spacing, or icon choices;
9. verify the accessible fallback.

Do not ask the model to invent a visual style from scratch when a product theme/template already exists.

## Responsive behavior

Use `responsive-layout`.

Do not simply scale a wide infographic down.

At narrow widths:
- switch horizontal sequences to vertical when needed;
- reduce parallel columns;
- preserve reading order;
- shorten secondary descriptions;
- move optional annotations below the main structure;
- avoid tiny text;
- avoid horizontal overflow unless the content genuinely requires a wide canvas.

A different custom template may be appropriate at narrow widths.

## Accessibility

SVG output is not automatically an adequate accessible representation.

Provide:
- an accessible region name;
- concise summary text;
- semantic HTML or a structured text/list equivalent when the infographic communicates essential information;
- meaningful labels for interactive controls;
- keyboard operation if editing/interaction is enabled.

Do not hide essential meaning only in spatial position, icon shape, or hover behavior.

The text fallback should preserve:
- sequence order;
- hierarchy;
- relationships;
- values;
- important annotations.

## Editing mode

AntV can support editable infographics.

Enable editing only when the product requires user editing.

Do not ship an editor merely because the library provides one.

When editing is enabled:
- preserve schema validity;
- constrain users to approved templates/theme behavior when brand consistency matters;
- validate output before persistence.

## Security and dependency hygiene

Treat infographic syntax, resource URLs, and dynamically loaded SVG assets as untrusted inputs when they originate outside the application.

- validate/sanitize remote resources;
- restrict allowed resource loaders where possible;
- pin and review dependency versions;
- use the project's dependency scanning and lockfile practices;
- verify the currently installed `@antv/infographic` package before deployment.

Do not load arbitrary third-party SVG resources directly from user input.

## Output when asked to choose an infographic

Report:

### Communication goal
State what the visual needs to explain.

### Why an infographic
Explain why spatial/narrative structure is better than chart, table, prose, or technical diagram.

### Information structure
Choose:
- list;
- sequence;
- timeline;
- comparison;
- hierarchy;
- relationship;
- cycle;
- matrix/grouped structure.

### Recommended template
Use the project's semantic template name.

### Content model
Specify the fields/items needed.

### Interaction
State whether it is static, editable, navigable, or contains links/actions.

### Responsive behavior
Describe narrow and wide layout behavior.

### Accessibility fallback
Specify the equivalent semantic representation.

## Review an existing infographic

Assess:

- Is an infographic the right communication form?
- Is the information structure correct?
- Does visual hierarchy match conceptual hierarchy?
- Is sequence/relationship direction obvious?
- Are there too many items?
- Are descriptions too long?
- Are icons meaningful?
- Does it match the product design system?
- Is it readable at target widths?
- Is essential meaning available accessibly?
- Would a chart, table, prose block, Mermaid diagram, or React Flow experience be more appropriate?

## Quality check

Before finalizing:

- the infographic has a clear explanatory purpose;
- an infographic is more appropriate than a chart/table/prose/technical diagram;
- the information structure matches the content;
- only approved templates are used;
- project typography, color, spacing, iconography, geometry, and theme modes are preserved;
- no gradients or decorative styling conflict with the active visual-style skill;
- content is concise and scannable;
- visual hierarchy matches conceptual hierarchy;
- reading order is unambiguous;
- responsive behavior is intentional;
- accessible equivalent content exists;
- AntV APIs match the installed package version;
- external SVG/resources are controlled and validated.

## References

- AntV Infographic: https://infographic.antv.vision/
- Getting Started: https://infographic.antv.vision/learn/getting-started
- Infographic Syntax: https://infographic.antv.vision/learn/infographic-syntax
- Custom Templates: https://infographic.antv.vision/learn/custom-template
- Theme: https://infographic.antv.vision/learn/theme
- GitHub: https://github.com/antvis/Infographic
