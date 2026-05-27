# AGENTS.md

## Purpose

This document tracks what the MIMIC-IV Clinical Data Warehouse system is currently carrying out, which module is responsible, and what we should execute next.

This file is written for:

- project maintainers,
- collaborators joining mid-stream,
- professor/reviewer walkthroughs,
- future contributors implementing milestones.

As of: `2026-05-27`

Project completion status for declared scope: `Complete` (Demo + Full Local + LocalStack paths).

## Current System Snapshot

Latest local execution mode: synthetic demo seed on `configs/demo.duckdb.yaml`.

Latest validated aggregate counts:

- Bronze: `bronze_hosp_patients=6`, `bronze_hosp_admissions=7`, `bronze_icu_icustays=7`.
- Silver: `silver_patients=6`, `silver_admissions=7`, `silver_icustays=7`, `silver_labs=63`, `silver_chart_events=49`.
- Gold: `gold_patient_summary=6`, `gold_admission_summary=7`, `gold_icu_stay_summary=7`, `gold_first_24h_features=7`, `gold_mortality_model_dataset=7`.

Latest validation status from `outputs/private/validation_report.md`:

- Passed: `20`
- Failed: `0`
- Warnings: `0`

Latest test status:

- `pytest` suite: `11 passed`

## Agent Map

### 1. Orchestration Agent

Primary modules:

- `src/cli.py`
- `Makefile`

What it is carrying out now:

- Exposes runnable commands for ingestion, layer builds, validation, reporting, and LLM demo.
- Executes end-to-end flow with `run-all` using: ingest -> gold build (includes bronze/silver) -> validation -> pipeline report.
- Supports reproducibility command `make ci` for local parity with CI pipeline.

Current status:

- Stable.
- Redundant layer rebuild was removed from `run-all`.

### 2. Data Discovery and Seeding Agent

Primary modules:

- `src/ingest/discover_files.py`
- `src/ingest/seed_synthetic.py`
- `src/ingest/load_demo.py`
- `src/ingest/load_full_local.py`
- `src/ingest/load_bigquery_metadata.py`

What it is carrying out now:

- Scans expected `hosp/` and `icu/` tables.
- Creates placeholder bronze tables for missing files.
- Loads local CSV/CSV.GZ into DuckDB bronze tables when files exist.
- Generates synthetic public-safe fake files for local demos (`make seed-synthetic`).
- Writes ingestion metadata report to `outputs/private/ingestion_report.md`.

Current status:

- Stable for demo and synthetic paths.
- Full local and BigQuery paths are scaffolded and safe, but BigQuery data pull is intentionally metadata-only.

### 3. Bronze Layer Agent

Primary modules:

- `src/transform/build_bronze.py`
- `sql/bronze/*.sql`

What it is carrying out now:

- Ensures all expected bronze tables exist.
- Preserves raw-like structure and adds metadata columns:
  `source_file`, `loaded_at`, `source_module`, `pipeline_run_id`.

Current status:

- Stable.
- Designed to be tolerant of missing optional MIMIC files.

### 4. Silver Layer Agent

Primary modules:

- `src/transform/build_silver.py`
- `sql/silver/*.sql`

What it is carrying out now:

- Normalizes IDs, timestamps, and key derived fields.
- Builds cleaned tables for core entities and event streams.
- Adds LOS and first-stay logic where applicable.

Current status:

- Stable on synthetic and empty-demo runs.
- All required silver tables build successfully.

### 5. Gold Layer Agent

Primary modules:

- `src/transform/build_gold.py`
- `sql/gold/*.sql`

What it is carrying out now:

- Builds analytics marts:
  patient summary, admission summary, ICU stay summary, first-24-hour features, diagnosis/lab/vital/medication aggregates, and mortality baseline dataset.
- Enforces first-24-hour windowing logic in SQL feature construction.

Current status:

- Stable.
- Produces non-empty rows in synthetic mode and empty-safe tables when raw inputs are unavailable.

### 6. Cohort Agent

Primary modules:

- `sql/cohorts/*.sql`
- `src/api/routes_cohorts.py`
- `dashboard/pages/5_Cohorts.py`

What it is carrying out now:

- Defines adult first ICU stay, sepsis-like, heart failure, ventilation-like, and high-lab-utilization cohorts.
- Returns aggregate summaries by default in UI/API context.

Current status:

- Stable.
- Cohort SQL templates execute in tests.

### 7. Validation Agent

Primary modules:

- `src/validation/*.py`

What it is carrying out now:

- Validates required schemas and columns.
- Validates uniqueness and joins for core keys.
- Checks LOS sanity and date completeness.
- Checks expected row volume for foundational tables.
- Writes private report to `outputs/private/validation_report.md`.

Current status:

- Stable.
- Last run: zero failures, zero warnings.

### 8. LLM Guardrail Agent

Primary modules:

- `src/llm/sql_guardrails.py`
- `src/llm/nl_to_sql.py`
- `src/llm/schema_context_builder.py`
- `src/llm/query_explainer.py`

What it is carrying out now:

- Provides rule-based NL-to-SQL for predefined aggregate analytics prompts.
- Rejects unsafe SQL patterns (`DROP`, `DELETE`, `SELECT *`, bronze access, raw ID projection, non-aggregate queries).
- Logs generated queries to `outputs/private/llm_query_log.jsonl`.
- Generates generated-vs-manual SQL comparison artifacts through `make llm-eval`.

Current status:

- Stable.
- 20 predefined aggregate questions run through `make llm-demo`.
- Evaluation artifacts are produced in `outputs/public/aggregate_results/`.

### 9. Dashboard Agent

Primary modules:

- `dashboard/streamlit_app.py`
- `dashboard/pages/*.py`
- `dashboard/components/*.py`

What it is carrying out now:

- Serves aggregate-only visual analytics across overview, admissions, ICU, labs/vitals, cohorts, and query assistant pages.
- Provides guarded SQL execution path for advanced users.

Current status:

- Stable for local run.
- Uses local DuckDB file and current config.

### 10. API Agent

Primary modules:

- `src/api/main.py`
- `src/api/routes_health.py`
- `src/api/routes_analytics.py`
- `src/api/routes_cohorts.py`

What it is carrying out now:

- Exposes aggregate endpoints for health, analytics summaries, cohort summaries, and guarded ad hoc aggregate queries.
- Blocks patient-level raw ID query exposure via guardrails.

Current status:

- Stable for local usage.
- OpenAPI docs available via FastAPI `/docs` when running.

### 11. Reporting Agent

Primary modules:

- `src/reporting/generate_data_dictionary.py`
- `src/reporting/generate_pipeline_report.py`
- `src/reporting/generate_professor_summary.py`

What it is carrying out now:

- Produces aggregate-safe project artifacts in private/public outputs.
- Supports review packages without raw data leakage.

Current status:

- Stable.

### 12. CI Agent

Primary modules:

- `.github/workflows/ci.yml`
- `Makefile` target `ci`

What it is carrying out now:

- On push and pull request, runs full synthetic demo pipeline and tests on Python 3.11 and 3.12.
- Enforces reproducibility gate before merge.

Current status:

- Implemented.
- Local parity command works: `make ci`.

## Privacy and Compliance Guardrails

Current controls carrying out:

- `.gitignore` blocks raw data files, DB files, credentials, env files, and private outputs.
- Dashboard/API paths are aggregate-first.
- LLM SQL validation blocks destructive or patient-level unsafe patterns.
- Private logs and validation artifacts are isolated under `outputs/private/`.

## Known Gaps

These are not failures; they are the current development edge:

1. BigQuery execution is intentionally out of scope for this repository (metadata scaffold only).
2. LocalStack ingestion depends on the expected S3 object layout; missing tables produce placeholders by design.
3. LocalStack production use depends on endpoint/bucket availability and object coverage.

## Next Steps (Prioritized)

### Priority 1: LocalStack Operational Hardening

Goal:

- Improve reliability of the selected cloud-style path in this repo.

Tasks:

1. Expand readiness diagnostics for endpoint and bucket checks.
2. Add clearer operator playbooks for common networking/path failures.
3. Add optional smoke command that runs readiness + ingest + profile summary.

Acceptance criteria:

- Operators can diagnose LocalStack ingestion issues quickly.

### Priority 2: API Hardening

Goal:

- Improve API resilience and edge-case behavior.

Tasks:

1. Expand API tests with edge-case payloads and error-path assertions.
2. Add request validation boundary tests for payload shapes.
3. Add response contract snapshots for aggregate endpoints.

Acceptance criteria:

- API issues can be diagnosed quickly without code changes.

### Priority 3: Performance and Incremental Build Hardening

Goal:

- Improve robustness for full-mode large-table execution.

Tasks:

1. Add incremental table rebuild controls for large event tables.
2. Add documented performance baselines for demo vs full-local runs.
3. Add table-level runtime profiling output to support optimization.

Acceptance criteria:

- Full-mode users can tune runtime and avoid unnecessary full rebuilds.

## Operator Runbook

Fast path for local synthetic demo:

```bash
make setup
make seed-synthetic
make run-all
make report
make dashboard
```

Fast path for LocalStack preflight:

```bash
make localstack-check
make ingest-localstack
make run-localstack
```

Fast path for reproducibility gate:

```bash
make ci
```

## Definition of Done for This Phase

This current phase is considered complete when all are true:

1. `make ci` passes locally and in GitHub Actions.
2. Dashboard and API run with aggregate-only outputs.
3. Validation report remains zero-fail on synthetic flow.
4. Repo remains public-safe with no restricted data leakage.
