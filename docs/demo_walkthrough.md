# Demo Walkthrough

This is a 5-7 minute walkthrough for presenting the project in a reproducible, privacy-safe way.

## 1. Prepare Environment

```bash
make setup
make seed-synthetic
```

## 2. Build Warehouse Layers

```bash
make run-all
```

Show:

- `outputs/private/ingestion_report.md`
- `outputs/private/validation_report.md`
- `outputs/private/pipeline_report.md`

## 3. Show Aggregate Dashboard

```bash
make dashboard
```

Walk through:

1. Overview page for scale and mortality summary.
2. Admissions and ICU pages for aggregate utilization/outcomes.
3. Labs/Vitals page for common tests and completeness.
4. Cohorts page for aggregate demographics, outcomes, completeness.
5. Query Assistant page with guarded aggregate queries.

## 4. LLM Guardrail and Evaluation

```bash
make llm-demo
make llm-eval
```

Show:

- `outputs/private/llm_query_log.jsonl`
- `outputs/public/aggregate_results/llm_sql_evaluation_summary.md`
- `outputs/public/aggregate_results/llm_sql_evaluation_comparison.csv`

## 5. Baseline ML Demonstration

```bash
make ml-baseline
```

Show:

- `outputs/public/aggregate_results/ml_baseline_metrics.md`
- `outputs/public/aggregate_results/ml_baseline_metrics.csv`

## 6. One-Command Outreach Pack

```bash
make demo-pack
```

This regenerates synthetic data products, evaluation artifacts, and public aggregate summaries without exposing patient-level data.
