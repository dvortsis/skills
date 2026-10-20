---
name: "analytics-validation"
description: "Validates dashboards and charts against source data and against one another by independently calculating expected values, exercising filters and visual interactions, and comparing expected versus displayed results across states."
compatibility: "Use for BI, analytics dashboards, and data applications. Requires access to the underlying source or semantic model for full source-of-truth validation; browser or UI automation improves interaction testing but is not required for static reconciliation."
---

# Analytics Validation

Validate analytical products as testable systems, not as screenshots.

This skill is the canonical owner for:
- reconciling dashboard and chart values to source data or a semantic model;
- independently computing expected values;
- validating charts against KPIs, tables, and peer visuals;
- testing global and local filters;
- testing visual click/select actions;
- testing cross-filter and cross-highlight behavior;
- testing parameters and metric switches;
- testing drill-down and drill-through;
- testing reset and deselection behavior;
- detecting stale, hidden, or inconsistent analytical state;
- documenting expected versus actual results with reproducible evidence.

This skill does **not** own:
- chart-type selection: use `analytics-chart-selection`;
- dashboard narrative and intended interaction design: use `dashboard-storytelling`;
- Tremor implementation: use `data-visualization-design`;
- generic visual/craft QA: use `design-review`.

## Core principle

A dashboard value is not validated because it "looks right."

For each important analytical result:

1. identify the exact analytical context;
2. calculate the expected result independently from the authoritative data/model;
3. reproduce the same state in the dashboard;
4. capture the displayed result;
5. compare expected versus actual;
6. explain any difference;
7. repeat after meaningful interactions.

Do not validate a visualization by using the visualization itself as the source of truth.

## Validation hierarchy

Validate in this order when possible:

1. **Source/model correctness**
2. **Metric/calculation correctness**
3. **Filter-context correctness**
4. **Visual rendering correctness**
5. **Cross-visual consistency**
6. **Interaction correctness**
7. **Reset/state persistence correctness**
8. **Edge-case behavior**

A later layer cannot compensate for an earlier failure.

## Establish the source of truth

Before testing, identify the authoritative source for each metric.

Possible authorities:
- database query;
- warehouse/lakehouse table;
- semantic model;
- dbt model;
- governed metric layer;
- API response;
- trusted exported dataset;
- validated fixture/test dataset.

Document:
- source name;
- table/model;
- grain;
- measure definition;
- aggregation;
- filters;
- timezone;
- date logic;
- null treatment;
- duplicate handling;
- distinct-count logic;
- currency/unit conversions;
- row-level security or access scope;
- freshness timestamp.

If the authoritative definition is ambiguous, validation is blocked until the metric contract is resolved.

## Build a metric contract

For every important metric, record:

- **Metric name**
- **Business definition**
- **Numerator**
- **Denominator**
- **Aggregation**
- **Grain**
- **Date field**
- **Date window**
- **Comparison period**
- **Filter exclusions**
- **Null handling**
- **Distinctness rule**
- **Rounding/display precision**
- **Expected unit**
- **Source/model**

Examples of materially different metrics that must not be conflated:
- row count vs distinct entity count;
- average of rows vs weighted average;
- percentage vs percentage-point change;
- period total vs rolling total;
- calendar month vs fiscal month;
- event date vs posting date;
- current snapshot vs cumulative history.

## Create a validation matrix

Before interacting with the dashboard, create explicit test cases.

Recommended columns:

| ID | Visual/metric | State | Source calculation | Expected | Displayed | Tolerance | Result | Evidence |
|---|---|---|---|---:|---:|---:|---|---|

State should include all context that can affect the result:
- global filters;
- local filters;
- visual selection;
- parameter values;
- drill level;
- user/security context;
- date range;
- page/view.

Do not record only the final number. Record the state that produced it.

## Independently calculate expected values

Prefer the most direct authoritative calculation available.

Examples:
- SQL against the warehouse;
- DAX query against the semantic model;
- Python/Pandas against the source extract;
- API request with explicit parameters;
- deterministic in-memory calculation against fixture data.

The expected-value calculation must be independent of the chart rendering logic.

When possible, preserve the query/calculation used so the test is reproducible.

## Compare at the correct grain

Do not compare values that are aggregated at different grains.

Examples:
- daily source rows vs monthly chart;
- facility-level KPI vs enterprise total;
- distinct patients vs encounter rows;
- local-time dates vs UTC dates.

Before declaring a mismatch:
1. align grain;
2. align filters;
3. align time boundaries;
4. align inclusion/exclusion logic;
5. align units;
6. align rounding.

## Numeric comparison and tolerances

Use exact equality for:
- counts;
- integer totals;
- IDs;
- categorical membership;
- deterministic whole-number outputs.

Use an explicit tolerance for:
- floating-point calculations;
- rates;
- currency converted through floating-point math;
- values intentionally rounded for display.

Distinguish:
- **calculation tolerance** from
- **display rounding**.

Example:
- source: `0.123456`
- dashboard display: `12.35%`

That may be correct if the metric contract requires two decimal places.

Do not use a broad tolerance to hide a genuine mismatch.

## Validate the unfiltered baseline first

Before testing interactions:

1. reset the dashboard to its documented default state;
2. record every active default filter;
3. record parameter defaults;
4. record date range;
5. validate headline KPIs;
6. validate primary charts;
7. validate supporting tables/details;
8. validate last-updated/freshness indicators where applicable.

This baseline becomes the control state.

If baseline values are wrong, interaction validation should not proceed as though the dashboard is healthy.

## Validate charts against source data

For each chart:

### Aggregated charts

Select representative marks:
- first;
- middle;
- last;
- largest;
- smallest;
- zero;
- null/missing where represented;
- unusual outlier.

For each mark:
1. reproduce the mark's filter context in the source;
2. calculate the expected measure;
3. compare with the rendered value and tooltip;
4. verify the axis/label formatting represents the same underlying value.

### Time series

Validate:
- time ordering;
- boundary dates;
- incomplete current period;
- missing dates;
- timezone/date truncation;
- rolling-window behavior;
- forecast vs actual boundaries;
- period-over-period comparisons.

### Stacked/part-to-whole charts

Validate:
- segment values;
- total;
- segment sum against total;
- percentage denominator;
- hidden/suppressed categories;
- "Other" bucket logic.

### Rates and percentages

Validate numerator and denominator separately before validating the final rate.

### Distinct counts

Check join duplication and grain explicitly.

Distinct-count defects often appear only after filters or joins.

## Validate charts against each other

Two visuals using the same metric under the same filter context should reconcile unless a documented difference exists.

Cross-check:
- KPI total vs chart total;
- chart total vs table total;
- same metric across pages;
- same time period across visuals;
- same segment across chart types;
- tooltip value vs data label;
- selected subset vs downstream total;
- summary card vs detail records.

When values differ, first determine whether the difference is intentional.

Document differences such as:
- different date field;
- different denominator;
- Top N restriction;
- hidden category;
- different aggregation;
- different security scope;
- visual-level filter;
- comparison-period logic.

Unexplained differences are defects.

## Validate filter controls

For every exposed filter:

1. record the baseline value;
2. select one representative value;
3. calculate expected results from source;
4. validate every intended target visual;
5. verify non-target visuals remain unchanged if the filter is local;
6. test multi-select when supported;
7. test select-all/clear;
8. test zero-result state;
9. test reset/default behavior.

Also test combinations of filters that users are likely to apply together.

Avoid testing only independent filters. Many defects arise from interaction between filters.

## Validate visual click/select actions

Use the interaction specification from `dashboard-storytelling`.

For each clickable/selectable visual:

1. identify the source visual;
2. identify the selected field/value;
3. identify intended targets;
4. identify intended action:
   - cross-filter;
   - cross-highlight;
   - parameter change;
   - drill-down;
   - drill-through;
   - navigation;
   - detail-panel update;
   - no action.
5. calculate expected target values independently;
6. perform the interaction;
7. compare every affected target;
8. verify unaffected visuals remain unchanged;
9. clear the selection;
10. confirm state returns correctly.

BI tools distinguish filtering and highlighting behavior, so validation must verify the intended effect rather than merely checking that "something changed."

## Cross-filter validation

For a cross-filter:

- target totals should reflect only matching records;
- filters should compose correctly with existing global/local filters;
- excluded categories should disappear or become empty according to the design;
- target tooltips/tables should reconcile to the filtered subset;
- clearing the source selection should restore the documented prior state.

Validate at least one selection that produces:
- many matching rows;
- one matching entity;
- zero matches, when possible.

## Cross-highlight validation

For a cross-highlight:

- the full context should remain visible where intended;
- the selected subset should be visually distinguishable;
- selected/subset values should reconcile to source;
- total/context values should remain unchanged unless the design specifies otherwise.

Do not accept cross-filter behavior where cross-highlight was intended.

## Parameter and metric-switch validation

For each parameter:

1. enumerate allowed values;
2. identify what each value changes;
3. calculate an expected result for representative parameter states;
4. verify labels, units, titles, tooltips, and formatting also update;
5. verify filters remain appropriately preserved or reset;
6. verify unsupported combinations are prevented or handled.

For metric switches, ensure the visible title and unit always correspond to the active metric.

## Drill-down validation

For each hierarchy:

1. validate parent total;
2. drill one branch;
3. independently calculate child values;
4. verify children reconcile to the parent where mathematically appropriate;
5. validate breadcrumbs/level indicators;
6. drill back up;
7. verify previous state is restored.

Do not assume children must sum to parent when the metric is non-additive, such as distinct counts or ratios. Validate according to the metric contract.

## Drill-through validation

For each drill-through path:

1. capture the selected entity/context;
2. calculate expected detail scope;
3. activate drill-through;
4. verify the destination inherits the intended context;
5. validate destination KPIs/detail rows;
6. verify unrelated filters do not leak unless specified;
7. navigate back;
8. verify source state restoration.

## Reset and state persistence

Test:
- deselection;
- "reset filters";
- page navigation;
- browser reload if state persistence is supported;
- back/forward navigation where applicable;
- saved/bookmarked state where applicable.

The reset state must match the documented baseline.

A reset that leaves hidden filter state behind is a defect.

## Hidden and implicit state

Inspect for state not obvious to the user:

- visual-level filters;
- page-level filters;
- report/global filters;
- hidden slicers;
- URL/query parameters;
- default parameter values;
- cached selection state;
- security filters;
- hidden exclusions;
- Top N filters;
- "Other" buckets;
- default date windows.

Unexpected hidden state is a common cause of apparent source mismatches.

## Validate empty, null, and edge states

Test representative cases:

- no matching rows;
- all values null;
- true zero;
- negative values;
- one record;
- one category;
- duplicate records;
- boundary date;
- future date;
- incomplete period;
- extremely large value;
- long label;
- suppressed value;
- stale data.

The dashboard must not silently turn:
- null into zero;
- unavailable comparison into `0%`;
- missing period into a connected time-series point;
- failed query into a valid-looking value.

## Freshness validation

Where freshness matters:

- compare dashboard last-updated timestamp to source/model refresh time;
- verify source data expected for that refresh is present;
- verify partial refreshes are labeled;
- check timezone of displayed refresh timestamps.

Do not declare a value incorrect before determining whether the dashboard is stale.

## Security-context validation

If role-based or row-level security exists:

- validate using authorized test contexts;
- calculate expected values for each role;
- confirm inaccessible rows do not affect totals;
- confirm drill-through/detail views do not expose filtered records;
- confirm cached state does not leak data between contexts.

Never bypass security controls to perform validation.

## Browser/UI automation

When browser or computer-use tooling is available, automate interaction tests where practical.

A deterministic test should:
1. open the target page;
2. wait for the dashboard to reach a stable loaded state;
3. reset to baseline;
4. capture displayed values;
5. apply one explicit action;
6. wait for affected visuals to settle;
7. capture actual values;
8. compare against independently calculated expectations;
9. clear/reset;
10. log the result.

Prefer stable semantic selectors/test IDs over pixel coordinates.

Do not use screenshot comparison as the only validation of numeric correctness.

## Tremor/React validation

For Tremor applications:

- verify `onValueChange` or other selection callbacks emit the expected value;
- verify selected state is propagated only to intended targets;
- validate transformed data before it reaches the component;
- validate tooltip values against the same underlying transformed values;
- ensure memoization does not retain stale filter state;
- ensure async requests cannot overwrite newer filter results;
- verify loading states do not display previous values as current.

When feasible, separate:
- calculation functions;
- filter-state transformations;
- presentation formatting;
- chart rendering

so they can be unit tested independently.

## Automated test layers

Use multiple layers where practical.

### Unit tests
For:
- metric formulas;
- formatters;
- date windows;
- filter predicates;
- parameter transformations.

### Data/query tests
For:
- grain;
- uniqueness;
- null constraints;
- accepted values;
- relationship integrity;
- known aggregate fixtures.

### Component tests
For:
- active filter state;
- selected mark state;
- labels/units;
- emitted interactions.

### End-to-end tests
For:
- user filter workflows;
- cross-filter/highlight;
- parameter changes;
- drill paths;
- reset;
- values displayed after interaction.

Do not attempt to prove every data row through end-to-end tests. Use representative scenarios plus lower-level data tests.

## Golden test cases

Maintain a small set of deterministic scenarios with known expected results.

Good golden cases include:
- baseline/default;
- one common segment;
- one edge segment;
- one date boundary;
- one empty result;
- one distinct-count-sensitive case;
- one multi-filter case;
- one click-action case.

Golden cases should be easy to reproduce from source data.

## Mismatch triage

When expected and actual differ, classify before editing code.

Possible causes:

1. source data/freshness;
2. metric definition;
3. aggregation/grain;
4. date/timezone;
5. join duplication;
6. null handling;
7. hidden filter;
8. parameter state;
9. interaction state;
10. stale frontend request/cache;
11. display rounding only;
12. actual rendering defect.

Do not "fix" a chart until the mismatch layer is identified.

## Validation report

For each failed or material test, report:

### State
Exact filters, parameter values, selections, drill level, date range, and user/security context.

### Expected
Value calculated independently from source/model.

### Actual
Value displayed by the dashboard.

### Difference
Absolute and relative difference where meaningful.

### Source calculation
Query, formula, or reproducible method used to establish expected value.

### Likely layer
Source, model, calculation, filter context, interaction, frontend state, or presentation.

### Evidence
Relevant source result and dashboard observation.

### Recommended fix
Specific correction at the responsible layer.

Do not hide failed cases inside a general narrative.

## Severity

Use:
- **Blocking**: materially incorrect data, security leak, or interaction produces misleading analytical results.
- **Important**: inconsistent values, broken filter scope, stale state, wrong drill context, or significant rounding/unit defect.
- **Polish**: minor presentation discrepancy that does not change interpretation.

## Sign-off criteria

Do not call a dashboard validated until:

- authoritative metric definitions are known;
- baseline values reconcile;
- critical charts reconcile to source;
- same-metric visuals reconcile under the same context;
- global/local filters behave as designed;
- critical click actions produce expected target values;
- parameter switches are correct;
- drill paths preserve intended context;
- reset returns to baseline;
- empty/null/stale states are handled honestly;
- material mismatches are resolved or explicitly accepted.

## References

- Power BI visual interactions: https://learn.microsoft.com/en-us/power-bi/create-reports/service-reports-visual-interactions
- Power BI filters: https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-report-add-filter
- Power BI DAX query view: https://learn.microsoft.com/en-us/power-bi/transform-model/dax-query-view
- Tableau filter actions: https://help.tableau.com/current/pro/desktop/en-us/actions_filter.htm
- Tableau dashboard actions: https://help.tableau.com/current/pro/desktop/en-us/actions_dashboards.htm
- Tableau View Underlying Data: https://help.tableau.com/current/pro/desktop/en-us/inspectdata_viewdata.htm
