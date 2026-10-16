# Cohort Time Contract

The prospective synthetic ICU mortality study has four mandatory concepts.
They are displayed in the Cohorts, Research Study Builder, and Feature Timing
Explorer pages, and are enforced by `src/research/cohorts.py` and
`src/research/features.py`.

| Concept | Enforced rule |
| --- | --- |
| **Index time (`t0`)** | ICU admission time of the patient’s first-ever ICU stay. Ties use `stay_id`. Later ICU stays are excluded before feature construction. |
| **Prediction window** | `[t0, t0 + 24 hours)`. A measurement must occur within this half-open interval and its `storetime` must be known, no earlier than measurement, and no later than prediction time. |
| **Outcome window** | Death is positive only when it occurs strictly after prediction time and on or before hospital discharge. Death at or before prediction time is an exclusion. |
| **Inclusion / exclusion** | Adult first stays only; selected care unit when requested; ICU departure at or before prediction time and death at or before prediction time are excluded. |

## Preventing common cohort errors

### Post-outcome variables

The prospective feature table cannot use diagnosis codes, procedure codes,
discharge outcomes, whole-stay summaries, identifiers, future events, or site
identifier. Event time and availability time are each checked, so a result that
becomes available after prediction time cannot enter the model even if it was
measured earlier.

### Multiple ICU stays

The cohort compiler applies `row_number()` by patient before age, care-unit,
and eligibility filters. This is deliberately **first-ever ICU stay**, rather
than first eligible ICU stay. A later stay cannot replace an ineligible first
stay, and event rows join using the selected `stay_id`.

## Regression evidence

`tests/test_study_platform.py` injects a later ICU stay and a heart-rate event
after prediction time. The test proves that the original selected stay remains
the only study row and its feature value remains unchanged.
