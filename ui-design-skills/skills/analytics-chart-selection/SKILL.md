---
name: "analytics-chart-selection"
description: "Selects and critiques analytical chart types based on the question, data shape, and intended message, then specifies chart craft for Tremor visualizations including axes, labels, tooltips, legends, annotations, formatting, and responsive behavior."
compatibility: "Use with analytics or BI work. For Tremor implementation details, pair with data-visualization-design and verify the installed Tremor APIs before editing."
---

# Analytics Chart Selection

Choose the visualization that answers the analytical question most clearly and honestly.

This skill is the canonical owner for:
- inferring the intended analytical question from data or an existing chart;
- deciding whether the current chart type is appropriate;
- selecting the most suitable visualization form;
- chart-level composition and formatting;
- axis, tick, gridline, data-label, legend, tooltip, annotation, and reference-line decisions;
- chart-specific responsive behavior and clarity;
- deciding when a table is better than a chart.

This skill does **not** own:
- Tremor API syntax or implementation plumbing: use `data-visualization-design`;
- dashboard-level narrative, layout, filtering strategy, or cross-visual interaction: use `dashboard-storytelling`;
- source-data reconciliation or cross-visual value validation: use `analytics-validation`;
- explanatory infographics, processes, conceptual sequences, hierarchies, timelines, or relationship stories: use `infographic-design`;
- product colors: the user/project owns color.

## Precedence

1. Explicit user requirements.
2. Data integrity, accessibility, and truthful analytical communication.
3. The analytical question and data properties.
4. Existing product/report conventions when they do not harm comprehension.
5. This skill's defaults.

Do not preserve a chart merely because it already exists. Preserve it only when it is a good match for the analytical intent.

## Start by inferring the analytical intent

When given raw data:

1. Identify dimensions and measures.
2. Identify data types: categorical, ordinal, temporal, quantitative, geospatial, hierarchical.
3. Check cardinality, missing values, zeros, negatives, outliers, sparsity, and sample size.
4. Identify whether measures are totals, rates, percentages, ratios, medians, averages, distinct counts, targets, forecasts, or estimates.
5. Determine the likely analytical question.
6. Choose the simplest chart that accurately answers that question.

When given an existing chart:

1. Read the title, subtitle, axes, legend, labels, filters, reference lines, and annotations.
2. Inspect the fields mapped to position, length, area, line, size, and category.
3. Infer the chart's intended question.
4. Determine whether the current chart actually answers that question.
5. Check whether another chart would make the comparison faster, more accurate, or less cognitively expensive.
6. Keep the current chart if it is already appropriate. Do not change chart type merely for variety.

If the intended question is ambiguous, infer the most defensible analytical task from the data and surrounding context. Prefer a simpler chart over a more novel one.


## Chart versus infographic

Use `infographic-design` when the primary question is explanatory rather than quantitative.

Examples:
- workflow steps → infographic;
- conceptual lifecycle → infographic;
- organizational hierarchy → infographic;
- feature relationship map → infographic;
- revenue over time → analytical chart;
- conversion by stage → analytical chart when magnitude/comparison is central;
- exact records → table.

Do not force conceptual/process information into a quantitative chart merely because a charting library is already present.


## Classify the analytical task

Use these categories before selecting a visual:

- **Current state / KPI:** What is the current value and how does it compare with a target or prior period?
- **Trend:** How has a measure changed across an ordered sequence, usually time?
- **Comparison / ranking:** Which categories are larger, smaller, highest, lowest, or materially different?
- **Composition / part-to-whole:** What contributes to a total, and how does composition change?
- **Relationship / correlation:** How do two quantitative measures vary together?
- **Distribution:** What is the shape, spread, concentration, or outlier structure?
- **Progress / threshold:** How far is a measure from a bounded target or threshold?
- **Conversion / process:** How does a cohort progress through ordered stages?
- **Status / sequence:** When or how often did states occur over a sequence?
- **Exact lookup:** What are the precise values for specific records or categories?
- **Exception detection:** Which observations materially deviate from expectations, targets, or peers?

## Chart-selection matrix

### KPI or current state

Use:
- a KPI/card for the current value;
- a sparkline when recent direction adds meaningful context;
- a `ProgressBar`, `CategoryBar`, or other bounded progress treatment only when there is a meaningful target, limit, threshold, or completion scale.

Include the period or scope and the single most useful comparison.

Do not display a delta without identifying the comparison basis.

### Trend over time

Default to:
- `LineChart` for one or a small number of measures over time;
- `AreaChart` only when magnitude or cumulative visual weight is analytically meaningful;
- sparkline variants for compact secondary context.

Prefer a line over bars for continuous time when the viewer should perceive trajectory.

Use bars for time only when individual periods should be compared as discrete units, such as monthly actual versus target or annual totals with few periods.

Do not connect unordered categories with a line.

### Category comparison or ranking

Default to `BarChart`.

Use horizontal bars when:
- category names are long;
- there are many categories;
- ranking is the main task.

Use vertical bars when:
- there are relatively few categories;
- the axis order is naturally understood;
- labels remain readable without rotation.

Sort by the measure for rank questions. Preserve natural order for ordinal categories.

A bar chart is usually preferable to a map when geography is not analytically important.

### Part-to-whole

Use:
- stacked bar for composition across multiple categories;
- percent stacked bar for relative composition when totals differ;
- stacked area only when composition over ordered time is the question;
- `DonutChart` only for a small number of parts at one point in time when rough share recognition is sufficient.

Prefer a sorted bar chart when exact comparison between parts matters.

Avoid multiple donuts for cross-category comparison.

### Relationship

Use `ScatterChart` for two quantitative measures.

Use point size for a third quantitative variable only when the additional encoding is useful and readable.

Do not infer causation from correlation.

If time order matters, a line chart or small multiples may be more appropriate than scatter.

### Distribution

Prefer a histogram, box plot, strip/dot plot, density treatment, or distribution table depending on the question.

If the installed Tremor version does not provide the appropriate distribution visual, do **not** force the data into an unrelated chart. Either:
- implement the needed visualization with the underlying chart library;
- use a carefully binned `BarChart` for a histogram;
- or present a table/summary if that better preserves the analytical meaning.

Bins must be explicit and consistent. Do not disguise arbitrary categories as a distribution.

### Progress, target, and threshold

Use `ProgressBar`, `CategoryBar`, `MarkerBar`, `DeltaBar`, or related Tremor data bars when the measure has a meaningful target, threshold, range, or bounded scale.

Do not use a progress bar for an unbounded metric such as revenue unless it is explicitly compared with a defined target.

Avoid decorative gauges when a number plus target comparison is clearer.

### Funnel or ordered conversion

Use `FunnelChart` when:
- stages are sequential;
- the population/cohort relationship between stages is meaningful;
- progression or conversion loss is the analytical question.

Use a bar chart instead when the stages are simply categories rather than a true process.

Always show stage values and conversion/drop-off context where useful.

### Status across a sequence

Use `Tracker` when discrete status over intervals is the question and the sequence itself matters.

Do not use it when exact magnitude comparison is required.

### Mixed measures or actual + rate

Use `ComboChart` only when the bar and line encodings answer one coherent question.

Avoid a second y-axis by default.

Use a second axis only when:
- the two measures have different units or scales;
- displaying them together materially improves interpretation;
- each axis is clearly identified;
- the relationship cannot be communicated more honestly with aligned separate charts.

When comparison between panels matters, aligned small multiples are often preferable.

### Exact lookup

Use a table when users primarily need exact values, many fields, record-level detail, or scanning across rows.

A chart is not automatically better than a table.

## Chart hierarchy and layout

Each chart should communicate one primary analytical question.

Recommended internal order:

1. title;
2. optional concise subtitle/context;
3. optional headline value or summary;
4. plot;
5. source, definition, or footnote only when needed.

Place controls near the chart they affect.

Give primary charts more visual area than secondary charts.

Do not make every chart card the same size if analytical importance differs.

Use `layout-spacing` and `layout-grids` for the surrounding structure.

## Titles and subtitles

Prefer titles that name the measure or analytical question clearly.

Good:
- `Revenue by month`
- `Conversion rate by acquisition channel`
- `Readmission rate versus target`

Better, when the insight is stable and known:
- `Readmission rate remains above target`
- `Conversion fell after the July campaign`

Use subtitles for:
- date range;
- population;
- aggregation;
- comparison basis;
- important filter context.

Do not make users infer the time period or unit from the axes alone.

## Axes

### Quantitative axes

For bar charts:
- start the quantitative baseline at zero unless there is an exceptional analytical reason not to;
- never truncate bar length in a way that exaggerates differences.

For line and scatter charts:
- a non-zero baseline can be legitimate;
- choose the domain to reveal meaningful variation without implying false magnitude;
- keep comparable charts on consistent domains when users are expected to compare them.

### Axis labels

Use axis titles when the measure or unit is not obvious from nearby context.

Do not repeat information already stated clearly in the chart title.

Prefer concise units:
- `$M`
- `%`
- `days`
- `visits`

### Category labels

Reduce tick density before shrinking text.

Prefer horizontal bars over rotating long category labels.

Rotate labels only when the alternative would be materially worse.

Use `startEndOnly` or appropriate interval behavior for dense ordered axes only when intermediate labels are not required.

## Gridlines

Gridlines exist to support estimation.

- Keep them sparse.
- Remove them when they do not improve reading.
- Avoid visual competition with the data.
- Preserve a zero or target reference line when analytically useful.

## Data labels

Data labels are not mandatory.

Use them when:
- exact values are essential to the question;
- there are few marks;
- labeling eliminates a separate legend;
- endpoint, target, maximum/minimum, or exception values deserve emphasis.

Avoid labeling every mark when:
- the chart is dense;
- labels overlap;
- the axis already allows adequate estimation;
- the same values are available in a tooltip and exact lookup is not the primary task.

Do not duplicate identical information in axis tick, label, and tooltip unless there is a specific reason.

## Legends and direct labels

Prefer direct labeling when a small number of series can be labeled without clutter.

Otherwise:
- keep legend order consistent with visual and tooltip order;
- use plain-language names rather than database field names;
- place the legend where it supports the reading path;
- use a legend slider only when many series are necessary.

If a chart needs an extensive legend explanation, simplify the chart.

## Tooltip design

Use Tremor's `customTooltip` when the default tooltip does not provide the required analytical context.

A clean analytical tooltip should normally contain:

1. the active category/date as the header;
2. series/metric name;
3. formatted value and unit;
4. comparison, delta, benchmark, target, or sample size only when it helps interpretation.

Formatting rules:
- use tabular numerals when values align vertically;
- keep precision consistent with the metric;
- use the same format as the axis/headline value;
- distinguish percent change from percentage-point change;
- show a full date when the axis uses abbreviated dates;
- use human-readable labels, not technical field names;
- keep ordering stable.

Do not turn the tooltip into a miniature report.

Do not place essential meaning exclusively behind hover. Touch and keyboard users need an alternative.

## Number formatting

Use the minimum precision needed to support the decision.

- Avoid false precision.
- Keep decimal places consistent for comparable values.
- Use localized number/date formatting when appropriate.
- Use compact notation only when it remains unambiguous.
- Do not mix `$2.1M`, `$2,100,000`, and `$2.10 million` in the same analytical context.
- Always distinguish `%` from percentage points when discussing changes in rates.

## Annotations and reference lines

Annotate:
- material events;
- targets;
- thresholds;
- policy changes;
- unusual outliers;
- forecast boundaries.

Use annotations sparingly.

An annotation should explain **why a change matters**, not restate the plotted value.

## Missing data

Never silently convert missing observations to zero.

Do not connect nulls unless continuity is analytically justified.

If connecting gaps is necessary, disclose that treatment.

Distinguish:
- true zero;
- missing;
- not applicable;
- suppressed;
- incomplete period.

## Responsive chart behavior

Do not simply shrink a desktop chart.

At narrow widths consider:
- fewer ticks;
- shorter labels;
- legend relocation;
- direct labels;
- stacked summary content;
- a ranked list or table;
- a different chart form.

Intentional horizontal scrolling is acceptable for dense categorical charts when it preserves readable labels and is clearly contained.

## Existing-chart review output

When asked whether an existing chart is correct, report:

### Intended question
State the analytical question the chart appears to be answering.

### Current chart
Name the current chart type and the key encodings.

### Assessment
Choose one:
- **Keep**
- **Keep with formatting changes**
- **Change chart type**

### Rationale
Explain the analytical reason, not aesthetic preference.

### Recommended chart
If changing it, specify the replacement visualization and why.

### Craft changes
List only the relevant changes to axes, sorting, labels, tooltip, legend, annotation, reference lines, or formatting.

## Tremor implementation handoff

After selecting the chart:
- use `data-visualization-design` to verify the installed Tremor API and implement it;
- use `dashboard-storytelling` for dashboard placement, filters, parameters, cross-filtering, drill-through, and multi-chart interaction;
- use `design-review` for final QA.

## Validation handoff

After implementation, use `analytics-validation` to reconcile:
- plotted marks to source calculations;
- tooltips and labels to the plotted values;
- chart totals to related KPIs/tables;
- filtered and selected states to independently calculated expected values.

Visual plausibility is not evidence of numerical correctness.

## Quality check

Before finalizing a chart decision, verify:

- the analytical question is explicit;
- the chart matches the question and data types;
- comparisons use perceptually accurate encodings;
- bars use honest baselines;
- sorting is intentional;
- time is ordered correctly;
- units and aggregation are clear;
- labels are readable;
- tooltip content is concise and useful;
- precision is appropriate;
- missing values are treated honestly;
- color is not the sole carrier of meaning;
- responsive behavior preserves comprehension;
- the selected chart exists in the installed Tremor version or a justified custom implementation is planned.

## References

- Tremor visualizations: https://www.tremor.so/docs/visualizations
- Tremor Line Chart: https://www.tremor.so/docs/visualizations/line-chart
- Tremor Bar Chart: https://www.tremor.so/docs/visualizations/bar-chart
- Tremor Area Chart: https://www.tremor.so/docs/visualizations/area-chart
- Tremor Donut Chart: https://www.tremor.so/docs/visualizations/donut-chart
- Tremor Combo Chart: https://www.tremor.so/docs/visualizations/combo-chart
- Tremor Scatter Chart: https://npm.tremor.so/docs/visualizations/scatter-chart
- Tremor Funnel Chart: https://npm.tremor.so/docs/visualizations/funnel-chart
- Tableau, Choose the Right Chart Type: https://help.tableau.com/current/pro/desktop/en-us/what_chart_example.htm
- Tableau, Visual Best Practices: https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm
- Power BI, Dashboard Design Tips: https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
