# LLM Query Assistant

The query assistant demonstrates schema-grounded natural-language-to-SQL for aggregate clinical analytics.

Workflow:

1. Build schema context from allowed Gold tables.
2. Generate SQL from a rule-based demo or optional external LLM.
3. Validate SQL with guardrails.
4. Execute only if safe.
5. Return aggregate results and a short explanation.

## Allowed Tables

- `gold_patient_summary`
- `gold_admission_summary`
- `gold_icu_stay_summary`
- `gold_first_24h_features`
- `gold_lab_features`
- `gold_vital_features`
- `gold_diagnosis_features`

## Guardrails

The assistant rejects destructive statements, `SELECT *`, Bronze table access, raw identifier projection, missing aggregation, and disallowed tables. It adds a row limit when a safe aggregate query omits one.

Unsafe examples:

```sql
SELECT * FROM gold_icu_stay_summary;
SELECT subject_id, stay_id FROM gold_icu_stay_summary;
DROP TABLE gold_patient_summary;
SELECT count(*) FROM bronze_hosp_patients;
```

## Evaluation Plan

The command `make llm-demo` runs 20 predefined aggregate questions and writes generated SQL to `outputs/private/llm_query_log.jsonl`.
