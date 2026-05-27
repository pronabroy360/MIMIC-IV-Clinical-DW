# Data Access And Compliance

This repository does not contain MIMIC-IV data. Users must obtain access through PhysioNet and comply with the applicable Data Use Agreement. Demo mode uses the openly accessible MIMIC-IV demo dataset.

## Modes

Demo mode expects:

```text
data/raw/mimic-iv-demo/2.2/hosp/
data/raw/mimic-iv-demo/2.2/icu/
```

Full local mode expects credentialed files under:

```text
data/raw/mimic-iv/3.1/hosp/
data/raw/mimic-iv/3.1/icu/
```

BigQuery mode is represented by `configs/bigquery.yaml.example` and requires credentials configured outside the repository.

## LocalStack S3 Mode

For cloud-like local testing without BigQuery, use `mode: localstack` with `configs/localstack.s3.yaml.example`.

Recommended preflight:

```bash
make localstack-check
```

This writes `outputs/private/localstack_readiness_report.md` and helps confirm expected `hosp/` and `icu/` source objects before ingestion.

Expected object paths:

- `s3://<bucket>/<prefix>/hosp/*.csv` or `.csv.gz`
- `s3://<bucket>/<prefix>/icu/*.csv` or `.csv.gz`

This mode is still subject to the same privacy and DUA-safe output rules: no restricted rows are committed to the repo.

Common LocalStack troubleshooting:

- `Could not connect to server` in readiness report:
  - Ensure LocalStack is running and `localstack_endpoint` is reachable.
- `0 available source objects`:
  - Verify bucket/prefix and file layout under `hosp/` and `icu/`.
- Tables load as placeholders:
  - This is expected when optional files are absent; check ingestion report for per-table status.

## Synthetic Local Demo

When no MIMIC-IV files are available, run:

```bash
make seed-synthetic
make run-all
```

This writes fake CSVs into the ignored `data/raw/` folder. These files are not MIMIC-IV records and exist only to exercise the pipeline, dashboard, and API safely.

## Public-Safe Practices

Do not commit raw MIMIC-IV files, DuckDB databases, patient-level exports, subject IDs, admission IDs, stay IDs, raw event rows, timestamps copied from records, screenshots containing patient-level rows, credentials, or service account files.

Allowed public artifacts include code, SQL templates, diagrams, synthetic examples, documentation, aggregate statistics, and demo/synthetic screenshots.

## LLM Safety

The query assistant uses schema context and SQL guardrails. It rejects destructive SQL, `SELECT *`, Bronze table access, raw identifier projection, and non-aggregate patient-level queries. Query logs are private by default.
