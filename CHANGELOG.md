# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses semantic versioning principles.

## [Unreleased]

### Added
- Bronze/Silver/Gold DuckDB pipeline with CLI orchestration and validation.
- Aggregate-only Streamlit dashboard and FastAPI endpoints.
- Cohort SQL templates (adult first ICU stay, sepsis-like, heart failure, ventilation-like, high lab utilization).
- Schema-grounded LLM query assistant with SQL guardrails and evaluation outputs.
- ML baseline command for aggregate mortality metrics.
- LocalStack S3 ingestion mode and readiness preflight check.
- PRD completion checklist and execution tracking documentation.

### Changed
- `make ci` runs synthetic seed, full pipeline, tests, LLM demo/eval, and ML baseline.
- API route test coverage now includes aggregate endpoints and SQL guardrail rejection.

### Security
- Strengthened public-safe output guidance and LocalStack compliance notes.
