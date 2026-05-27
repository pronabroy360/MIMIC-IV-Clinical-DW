# PRD Completion Checklist

As of: `2026-05-27`

This checklist maps the project state to the PRD requirements.

Status legend:
- `Done`: implemented and verified in code/tests/artifacts.
- `Partial`: implemented scaffold, but full execution depends on credentials or future work.
- `Optional`: intentionally optional in PRD; implemented where noted.
- `Out of Scope`: explicitly excluded from this repository build scope.

## 1. Repository and Architecture

- Repository structure and module layout: `Done`
- Bronze/Silver/Gold architecture implemented: `Done`
- Privacy-safe public outputs policy reflected in docs/config: `Done`
- Required `.gitignore` protections: `Done`

Evidence:
- `src/`, `sql/`, `dashboard/`, `tests/`, `docs/`, `outputs/`
- `.gitignore`
- `README.md`, `docs/03_architecture.md`

## 2. Data Access Modes

- Demo mode (`configs/demo.duckdb.yaml`): `Done`
- Full local mode (`configs/full_local.duckdb.yaml`): `Done`
- BigQuery full execution path: `Out of Scope` (metadata-only scaffold retained)
- LocalStack S3 mode (cloud-style execution path for this repo): `Done`

Evidence:
- `src/ingest/load_demo.py`
- `src/ingest/load_full_local.py`
- `src/ingest/load_bigquery_metadata.py`
- `src/ingest/load_localstack_s3.py`
- `src/ingest/check_localstack.py`

## 3. Ingestion and Bronze Layer

- File discovery for `hosp/` and `icu/`: `Done`
- Missing-file tolerance with placeholder tables: `Done`
- Bronze naming convention and metadata columns: `Done`
- Ingestion report generation: `Done`

Evidence:
- `src/ingest/discover_files.py`
- `sql/bronze/create_bronze_hosp.sql`, `sql/bronze/create_bronze_icu.sql`
- `outputs/private/ingestion_report.md`

## 4. Silver Layer

- Required cleaned silver tables present: `Done`
- Type/key/date normalization and LOS derivations: `Done`
- Linkage logic and dictionary decoding in place: `Done`

Evidence:
- `sql/silver/*.sql`
- `src/transform/build_silver.py`
- `tests/test_silver_tables.py`

## 5. Gold Layer and Feature Marts

- Patient/admission/ICU summary marts: `Done`
- First-24h feature dataset with leakage-aware windowing: `Done`
- Labs/vitals/medications/diagnosis features: `Done`
- Mortality baseline dataset table: `Done`

Evidence:
- `sql/gold/*.sql`
- `tests/test_gold_tables.py`

## 6. Cohort Builder

- Adult first ICU stay cohort: `Done`
- Sepsis-like cohort: `Done`
- Heart failure cohort: `Done`
- Ventilation-like cohort: `Done`
- High lab utilization cohort: `Done`

Evidence:
- `sql/cohorts/*.sql`
- `tests/test_cohort_sql.py`

## 7. Validation and Testing

- Schema/key/date/range/volume validation checks: `Done`
- Validation report output to private folder: `Done`
- Pytest suite passing: `Done`

Evidence:
- `src/validation/*.py`
- `outputs/private/validation_report.md`
- `make test` -> passing

## 8. Dashboard

- Streamlit multi-page aggregate dashboard: `Done`
- Privacy warnings and aggregate-first display: `Done`
- Cohort summaries and guarded query assistant page: `Done`

Evidence:
- `dashboard/streamlit_app.py`
- `dashboard/pages/*.py`

## 9. FastAPI Service

- Required aggregate endpoints implemented: `Done`
- `/docs` available via FastAPI defaults: `Done`
- Unsafe aggregate SQL rejected by guardrails: `Done`

Evidence:
- `src/api/main.py`
- `src/api/routes_analytics.py`
- `src/api/routes_cohorts.py`
- `src/api/routes_health.py`
- `tests/test_api_routes.py`

## 10. LLM Query Assistant

- Schema-grounded NL-to-SQL flow: `Done`
- SQL guardrails for restricted patterns/tables/identifiers: `Done`
- 20-question evaluation coverage: `Done`
- Private logging + public-safe summaries: `Done`

Evidence:
- `src/llm/nl_to_sql.py`
- `src/llm/sql_guardrails.py`
- `src/llm/evaluate_sql.py`
- `outputs/private/llm_query_log.jsonl`
- `outputs/public/aggregate_results/llm_sql_evaluation_summary.md`

## 11. ML Baseline (Optional)

- CLI baseline model training/reporting: `Done`
- Aggregate-only metrics export: `Done`
- Demo-safe behavior with low-volume guardrails: `Done`

Evidence:
- `src/ml/train_baseline.py`
- `outputs/public/aggregate_results/ml_baseline_metrics.md`

## 12. Documentation and Outreach

- README with access/compliance/pipeline/API/dashboard instructions: `Done`
- Required docs set (`docs/01` through `docs/08`): `Done`
- Professor outreach summary: `Done`
- Detailed execution/status tracker (`AGENTS.md`): `Done`

## 13. Release and Collaboration Hygiene

- `CHANGELOG.md`: `Done`
- PR template: `Done`
- Issue templates: `Done`
- Pre-commit config and make targets: `Done`

## 14. Final Scope Status

This repository is complete for its declared scope:
- demo mode
- full local credentialed mode
- LocalStack S3 cloud-style mode
- aggregate dashboard/API/LLM guardrails
- validation, tests, docs, and outreach package

BigQuery execution is intentionally excluded from this scope and tracked as a future extension path only.
