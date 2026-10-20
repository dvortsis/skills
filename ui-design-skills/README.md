# UI Design Skills

Canonical repository/root folder: `ui-design-skills`.

Fifteen portable, subject-specific Agent Skills for building and reviewing modern application interfaces.

The package is intentionally split by **decision ownership**. Each design subject has one canonical skill so agents do not receive multiple competing rules for the same decision.

## Skills

| Skill | Owns |
|---|---|
| `layout-spacing` | spacing scale, proximity, whitespace hierarchy, density, visual rhythm |
| `layout-grids` | columns, gutters, margins, regions, alignment, content width, asymmetry |
| `responsive-layout` | breakpoints, container-aware layout, reposition, resize, reflow, show/hide, re-architect |
| `typography-ui` | font families, type scale, line-height, measure, tracking, numerals |
| `component-geometry` | radii, borders, sizing, control geometry, touch targets |
| `iconography-ui` | icon family, weight, sizing, optical alignment, accessibility |
| `motion-ui` | duration, easing, entrance behavior, staggered reveals, reduced motion |
| `application-interface-design` | navigation, forms, tables, dialogs, states, accessibility, Tailwind/daisyUI application UX |
| `analytics-chart-selection` | analytical intent, chart-type selection, chart critique, axes, labels, legends, tooltips, annotations, formatting |
| `analytics-validation` | source-data reconciliation, cross-visual consistency, filter/action/parameter/drill validation, expected-vs-actual testing |
| `infographic-design` | explanatory visual selection, information structures, curated AntV Infographic templates, themes, syntax, responsive and accessible infographic design |
| `dashboard-storytelling` | dashboard narrative, 50,000-foot hierarchy, filters, parameters, cross-filter/highlight, drill-down, drill-through, navigation |
| `data-visualization-design` | Tremor implementation/API verification, data plumbing, callbacks, states, accessibility implementation, performance |
| `minimalist-visual-style` | editorial/minimalist aesthetic direction only |
| `design-review` | final critique and QA across the installed design skills |

## Global precedence

1. Explicit user requirements.
2. Accessibility, platform behavior, business logic, and functional correctness.
3. A coherent existing product/design system, except where a subject skill intentionally owns the decision.
4. Subject-specific skill defaults.
5. `minimalist-visual-style` as an aesthetic layer when requested or when no coherent product language exists.

### Intentional exceptions

- **Typography:** `typography-ui` uses the selected editorial/minimalist font direction even when a product already has a different typeface, unless the user explicitly specifies another typeface or language/platform requirements make the preferred faces unsuitable.
- **Color:** no skill defines a product palette. Colors and theme modes are defined by the user/product/project. daisyUI implementations use the project's semantic tokens.
- **Gradients:** `minimalist-visual-style` prohibits gradients when that style skill applies.

## Recommended combinations

### Application screen

```text
layout-spacing
layout-grids
responsive-layout
typography-ui
component-geometry
iconography-ui
motion-ui
application-interface-design
```

Add `minimalist-visual-style` when that aesthetic is desired.

### Analytical chart

Use the relevant foundation skills plus:

```text
analytics-chart-selection
data-visualization-design
```

`analytics-chart-selection` owns the analytical choice and chart craft. `data-visualization-design` owns the Tremor implementation.

### Analytics/dashboard screen

Use the application set plus:

```text
analytics-chart-selection
dashboard-storytelling
data-visualization-design
analytics-validation
```

Use `dashboard-storytelling` for the narrative order and interaction model, `analytics-chart-selection` for each visual, `data-visualization-design` for Tremor implementation, and `analytics-validation` to reconcile source values and exercise filters/interactions before sign-off.


### Explanatory infographic

Use:

```text
infographic-design
layout-spacing
layout-grids
responsive-layout
typography-ui
component-geometry
iconography-ui
```

Add `minimalist-visual-style` when the project uses the minimalist editorial direction.

Use `infographic-design` for processes, sequences, timelines, comparisons, hierarchies, relationships, cycles, feature maps, and other explanatory visuals. Use `analytics-chart-selection` instead when quantitative comparison is the primary task.

### Review/polish

Add:

```text
design-review
```

## Install with `npx skills`

The repository layout uses the standard `skills/` directory, so the CLI can discover every skill directly.

From the extracted folder:

```powershell
npx skills add . --list
```

Install all skills interactively:

```powershell
npx skills add .
```

Install all skills globally for Codex, Claude Code, and Antigravity:

```powershell
npx skills add . `
  --skill '*' `
  --agent codex `
  --agent claude-code `
  --agent antigravity `
  --global
```

Install selected skills only:

```powershell
npx skills add . `
  --skill layout-spacing `
  --skill layout-grids `
  --skill responsive-layout `
  --agent codex
```

The `skills` CLI is preferable to manually hard-coding agent install paths because supported agent locations can change between CLI releases.

## Updating from a Git repository

Once this skill pack is stored in GitHub or another supported Git remote, install from that remote rather than a ZIP. Then updates can be checked and applied with:

```powershell
npx skills check
npx skills update
```

## Source design references

These skills synthesize and reorganize the supplied UI skills and the design decisions made during reconciliation. Layout foundations additionally draw from:

- Microsoft Fluent 2 Layout: https://fluent2.microsoft.design/layout
- Uber Base Dimensions: https://base.uber.com/6d2425e9f/p/598458-dimensions
- Uber Base Layout Grids: https://base.uber.com/6d2425e9f/p/785d5f-layout-grids
- Tableau Visual Best Practices: https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm
- Tableau Choose the Right Chart Type: https://help.tableau.com/current/pro/desktop/en-us/what_chart_example.htm
- Microsoft Power BI Dashboard Design Tips: https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
- Microsoft Power BI Visual Interactions: https://learn.microsoft.com/en-us/power-bi/create-reports/service-reports-visual-interactions
- Microsoft Power BI DAX Query View: https://learn.microsoft.com/en-us/power-bi/transform-model/dax-query-view
- Tableau View Underlying Data: https://help.tableau.com/current/pro/desktop/en-us/inspectdata_viewdata.htm
- Tremor visualizations: https://www.tremor.so/docs/visualizations
- AntV Infographic: https://infographic.antv.vision/
- AntV Infographic syntax: https://infographic.antv.vision/learn/infographic-syntax
- AntV Infographic custom templates: https://infographic.antv.vision/learn/custom-template
- Original design-review provenance from the supplied skill: https://crit.officialjp.com

The package does **not** import the color systems of those design systems.
