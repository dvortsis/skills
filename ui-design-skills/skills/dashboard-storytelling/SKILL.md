---
name: "dashboard-storytelling"
description: "Designs analytical dashboards as coherent decision stories, moving from high-level status to trends, drivers, segments, exceptions, and detail while defining filters, parameters, cross-filtering, highlighting, drill-down, drill-through, navigation, and other visual interactions."
compatibility: "Use for BI and analytics dashboards. Pair with analytics-chart-selection for individual chart decisions and data-visualization-design for Tremor implementation."
---

# Dashboard Storytelling

Design dashboards that answer a sequence of business questions rather than assembling unrelated charts.

This skill is the canonical owner for:
- dashboard narrative and information sequence;
- deciding which analytical views belong on a dashboard;
- moving from the 50,000-foot view to progressively deeper detail;
- dashboard-level hierarchy;
- global and local filters;
- parameters and scenario controls;
- cross-filtering and cross-highlighting;
- click/select actions;
- drill-down and drill-through;
- navigation between analytical views;
- interaction scope, state, reset behavior, and discoverability.

This skill does **not** own:
- chart-type selection or chart formatting: use `analytics-chart-selection`;
- explanatory infographic structure or AntV implementation: use `infographic-design`;
- source-data reconciliation or interaction correctness testing: use `analytics-validation`;
- Tremor component/API implementation: use `data-visualization-design`;
- general application controls/navigation: use `application-interface-design`;
- structural spacing/grids/responsiveness: use the layout skills.

## Precedence

1. The decisions the audience must make.
2. The analytical story the user wants to tell.
3. Data integrity and common filter context.
4. Accessibility and predictable interaction.
5. Existing product/report conventions.
6. This skill's defaults.

Do not add a chart merely because data is available.

Every dashboard element must support a question, decision, explanation, or navigation path.

## Start with the audience and decision

Before laying out visuals, establish:

- Who is the primary audience?
- What decisions should the dashboard support?
- What do they need to know first?
- What would cause them to investigate further?
- Which questions naturally follow from the first answer?
- What action should be possible after finding an issue or opportunity?
- What time horizon and comparison basis matter?
- Is the dashboard for monitoring, diagnosis, exploration, communication, or a mixture?

Executive and operational audiences usually need different density and depth.

Do not design a row-level operational dashboard as though it were an executive scorecard.

## Define the dashboard's story in questions

Write the intended sequence before choosing visuals.

A common analytical narrative is:

1. **Where are we now?**
2. **How is that changing?**
3. **Are we on target?**
4. **What is driving the change?**
5. **Where is the issue/opportunity concentrated?**
6. **Which exceptions deserve attention?**
7. **What detail do I need to act?**

Not every dashboard needs all seven stages.

Use only the stages required by the audience and decision.

## 50,000-foot-first hierarchy

Start with the broadest level of meaning.

For left-to-right reading contexts, the highest-level information generally belongs toward the top-left and top of the canvas.

Typical hierarchy:

### Level 1: orientation and current state
Show the smallest useful set of headline KPIs:
- current value;
- target or benchmark when meaningful;
- change versus an explicitly named comparison period;
- status only when status has defined business meaning.

Do not fill the top row with every available KPI.

### Level 2: movement
Show the primary trend or time-based pattern.

This answers:
- Is performance improving or deteriorating?
- Is the current state normal or unusual?
- When did the change begin?

### Level 3: drivers
Show the factors most responsible for the current result or change.

Examples:
- product;
- channel;
- region;
- customer segment;
- service line;
- root-cause category.

Use contribution analysis, ranking, or decomposition appropriate to the data.

### Level 4: segmentation
Show where or for whom the result differs.

This supports:
- comparison between groups;
- identifying concentration;
- finding high/low performers;
- detecting cohort differences.

### Level 5: exceptions and action
Surface:
- threshold breaches;
- material outliers;
- missing coverage;
- unusual changes;
- entities requiring attention.

### Level 6: detail
Provide precise rows, records, definitions, or drill-through paths only when users need to investigate further.

Do not place record-level detail at the top of an executive dashboard.

## One-screen versus progressive dashboard

For monitoring dashboards intended to be read at a glance:
- keep the primary story on one screen when practical;
- remove nonessential panels before adding scrolling;
- ensure the high-level state and major exception are visible without exploration.

For exploratory analytical products:
- controlled vertical scrolling is acceptable;
- preserve the narrative order from summary to explanation to detail;
- use strong section transitions;
- do not scatter unrelated questions down a long canvas.

The first viewport must orient the user even when more detail exists below.

## Dashboard visual inventory

Before implementation, create a visual inventory.

For each proposed visual define:
- question answered;
- audience need;
- chart type;
- level in the narrative;
- filter scope;
- interaction role;
- whether it is primary, supporting, or detail;
- whether it can be removed without reducing decision quality.

If two charts answer the same question, keep the clearer one unless the second provides a genuinely different analytical perspective.

Avoid variety for its own sake.


## Infographics inside dashboards

Use `infographic-design` sparingly inside analytical dashboards.

Appropriate uses:
- explaining a business process adjacent to its metrics;
- summarizing a causal/operating model;
- showing a nonquantitative workflow users need to interpret the dashboard;
- onboarding or explanatory sections.

Do not use an infographic in place of:
- a quantitative trend;
- category comparison;
- distribution;
- exact lookup;
- exception list.

The dashboard story should remain analytical first. Infographics should clarify context, not decorate the canvas.


## Chart selection handoff

Use `analytics-chart-selection` for each chart.

Do not independently decide:
- line versus bar;
- stacked versus grouped;
- donut versus bar;
- funnel versus bar;
- scatter versus another relationship view;
- data-label density;
- axes and tooltip craft.

This skill decides **which questions belong and in what order**. `analytics-chart-selection` decides **how each question should be visualized**.

## Visual hierarchy

Make the most important information:
- easier to find;
- larger when appropriate;
- earlier in the reading path;
- less visually crowded.

Not every panel should have equal dimensions.

A dashboard full of equal-sized cards implies equal importance and weakens the story.

Use `layout-grids` for structural regions and `layout-spacing` for grouping and whitespace.

## Shared analytical context

A dashboard must make its analytical context obvious.

Keep these consistent unless intentionally varied:
- date range;
- timezone;
- population;
- aggregation level;
- units;
- inclusion/exclusion rules;
- comparison period;
- forecast versus actual status.

If one visual uses a different context, label it clearly.

Do not place charts from incompatible periods beside one another without explaining the difference.

## Filter strategy

Filters should answer a real analytical need.

### Global filters

Use global filters for context that should apply broadly:
- date range;
- business unit;
- region;
- product family;
- population/cohort.

Make their scope obvious.

### Local filters

Use local filters when the choice affects only one section or analytical question.

Do not make a control look global if it affects one chart.

### Filter defaults

Choose defaults that reflect the normal decision context.

Avoid defaults that accidentally hide problems or produce empty views.

### Active state

Users should be able to tell:
- which filters are active;
- which visuals are affected;
- whether a selection came from a control or another visual;
- how to clear or reset the state.

Provide a clear reset path when interactions can materially change the dashboard.

### Filter count

Do not expose every dimension as a filter.

Too many filters turn the dashboard into a query builder.

Prefer the small number of dimensions users repeatedly need.

## Parameters

A parameter changes the analytical setup rather than simply restricting rows.

Use parameters for:
- metric switching;
- scenario selection;
- benchmark choice;
- Top N;
- threshold values;
- what-if analysis;
- measure or dimension switching;
- alternate calculation assumptions.

Do not use a parameter when a normal filter expresses the task more directly.

Parameter controls must clearly communicate:
- what they change;
- the current value;
- whether the change affects one visual, a section, or the entire dashboard.

When direct manipulation of a visual changes a parameter, make the resulting state visible.

## Interaction decision framework

For each interactive visual, decide what selection should mean.

### Cross-filter

Use when the user's selection should restrict the target visual to matching data.

Example:
Selecting a region should make the customer and product views show only that region.

Use cross-filter when removing nonmatching context helps answer the next question.

### Cross-highlight

Use when the user should see the selected subset **within the context of the whole**.

Example:
Selecting a customer segment highlights its contribution while retaining the total distribution.

Prefer highlight over filter when comparative context is important.

### Drill-down

Use for hierarchy exploration inside the same analytical view.

Examples:
- year → quarter → month;
- region → market → facility;
- category → subcategory → item.

Drill-down changes granularity.

Do not use drill-down when the user actually needs a different page with richer detail.

### Drill-through

Use to navigate from a summary context to a dedicated detail view filtered to the selected entity.

Examples:
- region summary → region detail page;
- customer bar → customer detail;
- metric exception → underlying records.

Preserve context and provide a clear route back.

### Navigation

Use navigation when the next analytical task is meaningfully different and deserves another view/page.

The label should describe the destination.

### Highlight-only

Use when the user needs orientation without changing totals, scales, or overall context.

### External action

Use an external link only when the task truly moves outside the analytical product.

Do not make critical analysis depend on an unexplained external navigation.

## Interaction map

For nontrivial dashboards, define an interaction map before implementation.

For every interactive source visual specify:

- **Trigger:** click/select, hover, menu, control change.
- **Source:** the control or visual.
- **Selection:** which field/value is emitted.
- **Targets:** affected visuals or page.
- **Action:** filter, highlight, drill-down, drill-through, parameter change, navigate, external URL, or none.
- **Scope:** visual, section, page, dashboard.
- **Persistence:** transient, retained until cleared, URL/state persisted, or saved.
- **Clear behavior:** deselect, reset button, breadcrumb/back, or control reset.
- **Empty behavior:** what happens if no values remain.

Do not create bidirectional interactions casually. Circular or surprising filter behavior is a usability defect.

## Click/select actions with Tremor

Where supported by the installed Tremor component, use `onValueChange` or the relevant event callback to expose chart selection.

Possible uses:
- cross-filter another chart;
- populate a detail panel;
- update a parameter;
- navigate to a detail view;
- set the active entity;
- synchronize selection state.

Use `tooltipCallback` for hover/inspection state when the installed component supports it.

Use `customTooltip` for analytical tooltip presentation, not as the sole interaction mechanism.

Always verify the installed Tremor API because interaction props vary by component/version.

## Interaction feedback

Selections must be visible.

Show:
- selected mark/state;
- affected filter context;
- active parameter;
- breadcrumb or drill level when relevant.

Do not allow a click to change multiple charts invisibly.

The user must be able to understand **why the numbers changed**.

## Progressive disclosure

Do not place every analytical detail on the first page.

Use:
- drill-down;
- drill-through;
- expandable details;
- contextual drawers;
- secondary pages;
- detail tables

to reveal depth after the high-level story is understood.

Summary and detail should not compete for the same visual priority.

## KPI design

Headline KPIs should:
- be decision-relevant;
- have explicit units;
- include scope/period;
- include target or comparison only when useful;
- use consistent comparison windows.

Avoid KPI rows so large that users must scan many numbers before understanding the story.

If a KPI cannot influence a decision or investigation, question whether it belongs.

## Comparative consistency

When multiple visuals are intended for comparison:
- align time ranges;
- align definitions;
- align sorting logic;
- use consistent series naming;
- use common scales where meaningful;
- maintain consistent metric formatting.

Do not force common scales when doing so destroys useful resolution, but disclose scale differences.

## Exceptions before exhaustive detail

Operational dashboards should surface the few items that need attention.

Prefer:
- Top/Bottom N;
- threshold breaches;
- material variance;
- unusual change;
- late/stale/missing data;
- high-risk entities

over exhaustive category walls.

Provide a path to the full detail when needed.

## Dashboard controls

Controls should be visually subordinate to the analytical content but easy to find.

Group controls by scope.

Common order:
1. global context controls;
2. primary analytical content;
3. section-specific controls near the section;
4. drill/navigation controls where the action occurs.

Do not build a large filter bar that dominates the dashboard unless filtering is the primary task.

## Empty, loading, stale, and partial states

Dashboard storytelling must survive imperfect data.

### Loading
Reserve the final layout to prevent reflow.

### Empty
Explain whether:
- there is no data;
- filters returned no results;
- access is restricted;
- data is not yet available.

### Stale
Show last-updated context when freshness matters.

### Partial
Disclose incomplete coverage rather than presenting partial data as complete.

If one visual fails, preserve enough surrounding context for the rest of the dashboard to remain understandable.

## Accessibility

Interactions must be operable without relying exclusively on pointer hover.

- Provide keyboard-accessible controls.
- Make selected state perceivable without color alone.
- Do not hide essential information only in tooltips.
- Ensure drill/navigation controls have accessible names.
- Announce significant filter/context changes where the application architecture supports it.

## Responsive storytelling

Use `responsive-layout`.

On smaller screens:
- preserve the narrative order;
- keep headline status first;
- move secondary controls/details later;
- reflow supporting charts;
- avoid simply shrinking a dense desktop dashboard;
- consider replacing a complex chart with a ranked list/table when clearer.

A responsive dashboard may need to re-architect rather than merely resize.

## Dashboard review output

When asked to assess an existing dashboard, report:

### Intended audience and decision
Infer what the dashboard appears to support.

### Story currently told
List the questions in the order the current layout presents them.

### Gaps
Identify missing transitions such as:
- status without trend;
- trend without drivers;
- drivers without actionable detail;
- detail without orientation.

### Redundancy
Identify visuals answering the same question.

### Interaction assessment
Document existing filters, parameter controls, cross-filter/highlight behavior, and drill paths.

### Recommended narrative
Provide the revised order from high level to detail.

### Visual inventory
Specify:
- keep;
- remove;
- combine;
- add;
- move;
- change interaction.

Use `analytics-chart-selection` separately for chart-type corrections.

## Validation handoff

After the interaction model is implemented, use `analytics-validation` to prove that:
- baseline values reconcile to the source/model;
- filters produce the expected values;
- click actions affect only intended targets;
- cross-filter and cross-highlight behavior matches the specification;
- parameters, drill-down, drill-through, and reset behavior preserve the intended context.

The interaction design is not complete merely because controls respond visually.

## Quality check

Before finalizing a dashboard:

- the audience and decision are clear;
- the first viewport communicates the high-level state;
- the dashboard progresses from summary to explanation to detail;
- every chart answers a distinct useful question;
- the most important information appears early in the reading path;
- date/population/filter context is consistent;
- global and local filters have clear scope;
- parameter use is distinct from filtering;
- interaction behaviors are intentional and documented;
- users can see and clear active state;
- drill-down and drill-through are used for the correct purposes;
- selections do not cause surprising cross-visual changes;
- details are progressively disclosed;
- exceptions are actionable;
- responsive layouts preserve narrative order;
- dashboard density matches the audience and task.

## References

- Power BI, Tips for Designing a Great Dashboard: https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
- Power BI, Introduction to Dashboards: https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards
- Power BI, Visual Interactions: https://learn.microsoft.com/en-us/power-bi/create-reports/service-reports-visual-interactions
- Power BI, Drillthrough Guidance: https://learn.microsoft.com/en-us/power-bi/guidance/report-drillthrough
- Tableau, Visual Best Practices: https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm
- Tableau, Actions: https://help.tableau.com/current/pro/desktop/en-us/actions.htm
- Tableau, Filter Actions: https://help.tableau.com/current/pro/desktop/en-us/actions_filter.htm
- Tableau, Parameter Actions: https://help.tableau.com/current/pro/desktop/en-us/actions_parameters.htm
- Tremor visualizations: https://www.tremor.so/docs/visualizations
