# Migration from the previous five-skill package

The previous broad skills have been decomposed so each design subject has one canonical owner.

| Previous skill | Replaced / distributed into |
|---|---|
| `designing-layout-systems` | `layout-spacing`, `layout-grids`, `responsive-layout` |
| `designing-application-interfaces` | `application-interface-design` plus the shared foundation skills |
| `designing-tremor-charts` | `data-visualization-design` plus the shared foundation skills |
| `minimalist-ui` | `typography-ui`, `component-geometry`, `iconography-ui`, `motion-ui`, `minimalist-visual-style` |
| `superfuture-design-review` | `design-review` |

## Why the split

The broad skills repeated rules for spacing, type, radius, icons, responsiveness, and motion. That made precedence harder for an agent to interpret. The new package assigns each of those subjects to one skill and makes application, chart, style, and review skills defer to those owners.

## Removed duplicate authority

- Spacing values exist only in `layout-spacing`.
- Grid mechanics exist only in `layout-grids`.
- Breakpoint/adaptation behavior exists only in `responsive-layout`.
- Font-family and type-system rules exist only in `typography-ui`.
- Radius/border/touch-target rules exist only in `component-geometry`.
- Icon-family rules exist only in `iconography-ui`.
- Animation timing/easing rules exist only in `motion-ui`.
- Product color remains user/project-defined across the entire package.


## Analytics specialization

The analytics layer has been further decomposed so analytical reasoning and Tremor implementation do not compete.

| Concern | Canonical skill |
|---|---|
| infer the question from data or an existing chart | `analytics-chart-selection` |
| choose or critique the chart type | `analytics-chart-selection` |
| axes, labels, tooltip content, legends, annotations, formatting | `analytics-chart-selection` |
| dashboard narrative and visual sequence | `dashboard-storytelling` |
| global/local filters and parameters | `dashboard-storytelling` |
| cross-filtering, highlighting, drill-down, drill-through, navigation | `dashboard-storytelling` |
| Tremor component/API implementation | `data-visualization-design` |
| final QA | `design-review` |

`data-visualization-design` remains for compatibility but is now explicitly the Tremor implementation layer rather than the owner of analytical chart selection.


## Infographic specialization

Added `infographic-design` as the canonical owner of explanatory information graphics.

| Concern | Canonical skill |
|---|---|
| determine infographic vs chart/table/prose/technical diagram | `infographic-design` |
| choose list/sequence/timeline/comparison/hierarchy/relationship/cycle structure | `infographic-design` |
| AntV Infographic templates, syntax, themes, resource use | `infographic-design` |
| quantitative chart choice | `analytics-chart-selection` |
| dashboard story and interactions | `dashboard-storytelling` |
| Tremor implementation | `data-visualization-design` |
| final visual QA | `design-review` |

AntV Infographic should be wrapped behind product-owned components, themes, and a curated semantic template registry rather than exposed as an unrestricted visual-style engine.


## Analytics validation specialization

Added `analytics-validation` as the canonical owner of analytical correctness testing.

| Concern | Canonical skill |
|---|---|
| reconcile KPIs/charts to source/model | `analytics-validation` |
| validate same metric across visuals | `analytics-validation` |
| validate global/local filters | `analytics-validation` |
| validate click actions and cross-filter/highlight | `analytics-validation` |
| validate parameters and metric switches | `analytics-validation` |
| validate drill-down/drill-through/reset | `analytics-validation` |
| define intended interactions | `dashboard-storytelling` |
| choose the chart | `analytics-chart-selection` |
| implement Tremor | `data-visualization-design` |

The validation skill calculates expected values independently from the rendered dashboard and records expected versus actual results under explicit analytical state.
