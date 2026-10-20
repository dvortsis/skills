---
name: "data-visualization-design"
description: "Implements analytical visualizations with Tremor, React, Tailwind CSS, and daisyUI after chart intent and chart type are established. Owns Tremor API verification, data plumbing, component props, callbacks, states, accessibility implementation, and chart performance."
compatibility: "Intended for React projects using Tremor and Tailwind CSS, optionally with daisyUI. Verify the installed Tremor APIs and versions before editing."
---

# Data Visualization Design

Implement trustworthy analytical visualizations in Tremor.

This skill is the canonical **Tremor implementation layer**.

Use:
- `analytics-chart-selection` for chart choice, chart critique, axes, labels, legends, tooltip content, annotations, formatting, and chart-level craft;
- `dashboard-storytelling` for dashboard narrative, visual inventory, filter strategy, parameters, cross-visual interactions, drill-down, drill-through, and navigation;
- `analytics-validation` for source-data reconciliation, cross-visual consistency checks, and interaction correctness testing;
- `layout-spacing`, `layout-grids`, and `responsive-layout` for dashboard structure;
- `typography-ui`, `component-geometry`, and `motion-ui` for shared UI foundations.

Do not independently override those skills.

Color choices belong to the user, product, or project.

## Precedence

1. Explicit user requirements.
2. Data correctness and accessibility.
3. `analytics-chart-selection` and `dashboard-storytelling` decisions.
4. Installed Tremor version and API constraints.
5. Existing product implementation conventions.
6. This skill's defaults.

## Verify the installed implementation

Before editing:

1. Identify whether the project uses current copy-and-paste Tremor components, `@tremor/react`, or another Tremor package/version.
2. Inspect existing chart components and project utilities.
3. Verify component names and prop contracts against the installed code/version.
4. Reuse existing chart wrappers, formatters, hooks, and tokens when sound.
5. Do not paste examples from a different Tremor generation without adapting them.

Tremor APIs have changed over time. The repository is authoritative for the project.

## Implement the selected visualization

Do not choose the chart type here.

Use the visualization selected by `analytics-chart-selection`, then map the analytical specification into the available Tremor component.

Common current Tremor visualization components include:
- `LineChart`;
- `BarChart`;
- `AreaChart`;
- `DonutChart`;
- `ComboChart`;
- `ScatterChart`;
- `FunnelChart`;
- spark chart variants;
- progress/data-bar components such as `ProgressBar` and `CategoryBar`;
- `Tracker`.

Availability depends on the installed version.

If the required analytical visual is not supported, do not substitute an analytically incorrect chart merely because Tremor has it. Implement the appropriate custom visualization with the underlying chart library or use an alternative representation approved by `analytics-chart-selection`.

## Data contract

Before rendering, confirm:

- index/category field;
- series fields;
- units;
- aggregation;
- sort order;
- time ordering;
- null meaning;
- zero meaning;
- negative values;
- forecast/estimate flags;
- comparison baseline;
- target/threshold;
- filter context.

Keep stored numeric values numeric.

Apply display formatting separately.

Do not pre-format numbers as strings before the chart needs them unless the component API explicitly requires it.

## Data transformation

Transform source data once when practical.

Use memoization when transformation is computationally meaningful.

Do not:
- recompute large derived datasets on every render;
- mutate source data in place;
- silently drop nulls;
- silently convert missing values to zero;
- sort chronological strings lexically when that changes time order.

Use real representative data during development:
- zeros;
- nulls;
- negatives;
- spikes;
- long labels;
- empty ranges;
- multiple series;
- large values.

## Value formatting

Use one formatter for the same metric across:
- axis;
- tooltip;
- KPI;
- label;
- table/detail representation.

Follow the precision and notation decision from `analytics-chart-selection`.

Prefer `Intl.NumberFormat` and appropriate date/time formatters when suitable.

## Axes and labels

Implement the axis specification from `analytics-chart-selection`.

Tremor controls may include version-dependent props such as:
- `showXAxis`;
- `showYAxis`;
- `xAxisLabel`;
- `yAxisLabel`;
- `yAxisWidth`;
- `startEndOnly`;
- `tickGap`;
- `intervalType`;
- `minValue`;
- `maxValue`;
- `autoMinValue`;
- `allowDecimals`.

Use only props present in the installed component.

Do not hide an axis merely to create a cleaner visual if doing so removes context required for interpretation.

## Tooltips

Use the tooltip content specification from `analytics-chart-selection`.

When the default tooltip is insufficient, use the installed component's supported mechanism such as:
- `customTooltip`;
- `tooltipCallback`;
- shared tooltip utilities.

A custom tooltip should remain:
- concise;
- stable in ordering;
- correctly formatted;
- accessible to the extent supported by the surrounding implementation.

Do not embed business logic only in tooltip rendering.

## Legends

Implement the legend decision from `analytics-chart-selection`.

Where available, Tremor may expose controls such as:
- `showLegend`;
- `legendPosition`;
- `enableLegendSlider`.

Do not enable a legend slider merely because it exists.

## Interaction events

Use `dashboard-storytelling` to determine what interaction should happen.

Then implement that behavior with the Tremor callback supported by the component/version.

Common mechanisms may include:
- `onValueChange`;
- `tooltipCallback`;
- component-specific selection callbacks.

Selection state should be stored explicitly when downstream views depend on it.

Avoid implicit coupling between charts.

Document the emitted selection shape when multiple components participate in dashboard interactions.

## Cross-filter and cross-highlight implementation

Tremor does not automatically create a BI semantic interaction model.

When `dashboard-storytelling` specifies cross-filtering or highlighting:

1. capture the source selection;
2. normalize it to an explicit analytical filter state;
3. apply it to target data queries or transformations;
4. show the active selection visually;
5. provide clear behavior for deselection/reset;
6. prevent stale selections after upstream filters change.

Do not create circular filter dependencies.

## Chart containers

Adapt to the existing product.

For daisyUI/Tailwind, use project semantic tokens and the shared geometry skill.

A restrained example:

```tsx
<section className="card rounded-xl border border-base-300 bg-base-100 shadow-sm">
  <div className="card-body">
    {/* heading, context, chart */}
  </div>
</section>
```

Do not wrap every small metric in its own card when grouping communicates the structure better.

## Responsive implementation

Use `responsive-layout` and the chart-specific response specified by `analytics-chart-selection`.

Possible implementation changes:
- explicit responsive chart height;
- fewer ticks;
- legend repositioning;
- conditional axis labels;
- alternate chart/table at narrow widths;
- contained horizontal scrolling for dense categorical views.

Do not shrink text below readable sizes.

## Loading and data states

Reserve the final chart dimensions during loading.

Implement distinct states for:
- loading;
- no data;
- no filter matches;
- error;
- partial coverage;
- stale data;
- unavailable comparison.

Do not show a misleading zero when the comparison does not exist.

## Accessibility implementation

Where the chart library does not expose all values semantically, provide a useful accessible alternative.

Depending on the task:
- accessible summary text;
- data table;
- labelled region;
- keyboard-accessible controls;
- explicit selected-state text.

Do not rely on color alone.

Do not hide essential information exclusively behind hover.

## Performance

Avoid rendering thousands of marks when:
- aggregation;
- sampling;
- pagination;
- virtualization;
- a table

better matches the analytical task.

Debounce expensive interactive updates when necessary.

Keep deterministic series order and stable React keys.

Avoid full-dashboard reanimation after minor filter changes.

## Motion

Use `motion-ui`.

If Tremor exposes `showAnimation` and `animationDuration`, override library defaults when necessary to comply with the project's motion rules.

Do not assume a library default is automatically appropriate.

## Project-defined color

This skill does not define a chart palette.

Use project chart tokens and ensure the same analytical concept retains the same visual encoding across related charts.

If current Tremor utilities centralize series colors through a shared `chartUtils` file, reuse that mechanism.

## Validation hooks

Implement charts so `analytics-validation` can test them reliably.

Where practical:
- keep calculation logic separate from rendering;
- expose stable test IDs or semantic selectors for KPI values and chart containers;
- keep filter/parameter state explicit;
- expose deterministic selection state;
- avoid hiding source values only inside canvas pixels;
- make displayed values available through accessible text, tooltip state, or structured detail;
- prevent stale asynchronous responses from overwriting newer filter states;
- log or expose current analytical context in development/test environments when appropriate.

## Quality check

Before finishing:

- installed Tremor APIs were verified;
- the implemented component matches the chart selected by `analytics-chart-selection`;
- data transformations preserve meaning;
- geometry and tooltip values use the same transformed values;
- formatting is consistent;
- interaction callbacks match the `dashboard-storytelling` interaction map;
- selected/filter state can be cleared;
- narrow layouts remain usable;
- loading/empty/error/stale states are handled;
- accessibility alternatives exist when needed;
- project color and theme conventions are preserved;
- performance is appropriate for the number of marks and interactions.

## References

- Tremor documentation: https://www.tremor.so/docs
- Tremor visualizations: https://www.tremor.so/docs/visualizations
- Tremor Bar Chart: https://www.tremor.so/docs/visualizations/bar-chart
- Tremor Line Chart: https://www.tremor.so/docs/visualizations/line-chart
- Tremor Area Chart: https://www.tremor.so/docs/visualizations/area-chart
- Tremor Donut Chart: https://www.tremor.so/docs/visualizations/donut-chart
- Tremor Combo Chart: https://www.tremor.so/docs/visualizations/combo-chart
- Tremor chart utilities: https://www.tremor.so/docs/utilities/chartUtils
