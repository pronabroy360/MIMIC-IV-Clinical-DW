# Synthetic Research Workshop

This workshop adapts teaching ideas from
[`balubhasuran/mimic-ehr-learning`](https://github.com/balubhasuran/mimic-ehr-learning).
The implementation and source records here are original. That repository
describes synthetic data whose broad distributions were learned from a
credentialed MIMIC-IV cohort; this project's generator uses arbitrary,
documented rules and no restricted source data.

## Run

```bash
make setup
make research-demo
```

For a different cohort size or seed:

```bash
.venv/bin/python -m src.cli research-demo --patients 1000 --seed 42
```

The command uses `configs/research_synthetic.duckdb.yaml`. It writes generated
source-like CSVs to `data/raw/research-synthetic/` and a DuckDB warehouse to
`data/processed/mimic_research_synthetic.duckdb`; both paths are Git-ignored.
The command rejects unexpected source files or populated Bronze tables in
these isolated paths before writing a public report.
The aggregate report is
`outputs/public/research_synthetic/aggregate_results/research_demo_summary.md`.
Aggregate CSV tables and Plotly HTML charts are saved in the same directory.
They include aggregate demographics, missingness, comorbidity/intervention,
calibration, feature-importance, and LOS residual artifacts.
The workshop notebooks are `07_synthetic_research_workshop.ipynb`,
`08_synthetic_mortality_classification.ipynb`, and
`09_synthetic_los_regression.ipynb`.
The same research flow runs in the repository's `make ci` reproducibility gate.

## What the workshop adds

| Teaching idea in the learning repository | This project's implementation |
| --- | --- |
| Source-like synthetic EHR tables | Deterministic invented `patients`, `admissions`, `icustays`, diagnoses, procedures, services, labs, ICU charts, and input events feed the existing Bronze/Silver/Gold pipeline. |
| Cohort definition and row grain | `sql/research/gold_research_index_admissions.sql` selects the first admission per patient. |
| 30-day readmission and outcome timing | An urgent admission strictly after index discharge and within 30 days defines the label. Index deaths receive a null readmission label. |
| Explicit leakage exclusions | Versioned `configs/research/leakage_exclusions.yaml` keeps identifiers and outcomes out of model inputs. |
| Configurable feature audit | Versioned feature provenance, availability, and synthetic plausibility ranges live in `configs/research/`; workshop tests enforce grain, timing, ranges, leakage, and split isolation. |
| Data quality and feature audit | Standard warehouse validation plus cohort counts, predictor missingness, feature sources, and timing rules in the aggregate report. |
| Exploratory analysis | Aggregate age, LOS, gender, and diagnosis summaries plus a notebook chart. |
| Baseline comparisons | Dummy models, linear models, and random forests are compared on validation data for four teaching tasks. |
| Held-out evaluation | Patients are assigned once to 70/15/15 train/validation/test splits. Model selection uses validation scores; selected models are scored on test data. |
| Repeated cross-validation | The development partition also receives repeated 3-fold cross-validation; the held-out test split is never used by it. |
| Imbalance, calibration, interpretation, subgroups | AUPRC, AUROC, Brier score, calibration bins, permutation importance, linear coefficients, Shapley-style linear contribution magnitudes, and synthetic subgroup metrics are reported when defined. |

The feature catalog has 73 transparent documented predictors: 69 numeric and
four categorical values. The linear contribution artifact is a baseline-centred
coefficient approximation, not a run of the external SHAP package. We do not
generate a privacy similarity report against a real holdout because this
generator has no real source records or holdout. A similarity number without
that comparator would imply a privacy check that never happened. The model
report keeps all patient-level predictions inside the ignored local database
and process memory.

## Definitions

- **Grain:** one first hospital admission per synthetic patient.
- **Prediction time:** 24 hours after first ICU entry if an ICU stay exists;
  otherwise 24 hours after hospital admission.
- **Predictors:** the versioned feature configuration includes admission data,
  selected first-24-hour chart/lab summaries, transparent synthetic diagnosis
  flags, and explicitly named intervention proxies. Missing values stay null
  until model preprocessing, which is fitted on training data only.
- **Outcomes:** total hospital LOS, in-hospital death, urgent readmission
  within 30 days after discharge, and a compact primary diagnosis class.
- **Readmission exclusions:** index deaths; subsequent admissions at or before
  index discharge; non-urgent admissions; admissions after day 30.
- **Splits:** fixed random patient assignment with seed 42; no patient's
  admissions can appear in more than one split.

The diagnosis class is a synthetic teaching target, not a validated clinical
phenotype. The small code mapping in the SQL should not be used as a real
disease classifier. Reported scores measure recovery of invented generator
patterns, not medical prediction quality.

## Boundaries

The standard six-patient demo remains available through `make seed-synthetic`
and `make run-all`. The workshop uses separate paths. Real MIMIC-IV v3.1
requires PhysioNet credentialing, training, and a signed agreement. The
[open MIMIC-IV demo](https://physionet.org/content/mimic-iv-demo/2.2/) contains
real records from 100 patients and is suitable for engineering exercises, but
it is too small for clinical conclusions. The [full database](https://physionet.org/content/mimiciv/3.1/)
is needed for a properly designed MIMIC-IV study.
