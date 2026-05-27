"""Rule-based natural-language-to-SQL demo assistant.

This module deliberately avoids requiring an external LLM key. It models the
schema-grounded workflow and sends every generated query through guardrails.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src.llm.query_explainer import explain_sql
from src.llm.sql_guardrails import GuardrailResult, validate_aggregate_sql


QUESTION_SQL: dict[str, str] = {
    "patients": "SELECT count(*) AS patient_count FROM gold_patient_summary",
    "admissions": "SELECT count(*) AS admission_count FROM gold_admission_summary",
    "icu stays": "SELECT count(*) AS icu_stay_count FROM gold_icu_stay_summary",
    "average icu length": "SELECT avg(icu_los_days) AS avg_icu_los_days FROM gold_icu_stay_summary",
    "average hospital length": "SELECT avg(hospital_los_days) AS avg_hospital_los_days FROM gold_admission_summary",
    "admission types": """
        SELECT admission_type, count(*) AS admission_count
        FROM gold_admission_summary
        GROUP BY admission_type
        ORDER BY admission_count DESC
    """,
    "discharge locations": """
        SELECT discharge_location, count(*) AS admission_count
        FROM gold_admission_summary
        GROUP BY discharge_location
        ORDER BY admission_count DESC
    """,
    "diagnosis groups": """
        SELECT
            sum(sepsis_diagnosis_proxy_flag) AS sepsis_proxy_admissions,
            sum(heart_failure_flag) AS heart_failure_admissions,
            sum(respiratory_failure_flag) AS respiratory_failure_admissions,
            sum(renal_dysfunction_proxy_flag) AS renal_dysfunction_admissions,
            sum(diabetes_flag) AS diabetes_admissions
        FROM gold_diagnosis_features
    """,
    "common lab": """
        SELECT
            sum(total_lab_events) AS total_lab_events,
            avg(distinct_lab_tests) AS avg_distinct_lab_tests_per_stay,
            avg(abnormal_lab_rate) AS avg_abnormal_lab_rate
        FROM gold_lab_features
    """,
    "lactate": """
        SELECT avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_measured_first_24h_rate
        FROM gold_first_24h_features
    """,
    "creatinine": """
        SELECT avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_measured_first_24h_rate
        FROM gold_first_24h_features
    """,
    "mortality first": """
        SELECT avg(hospital_mortality_flag) AS mortality_rate_first_icu_stays
        FROM gold_icu_stay_summary
        WHERE is_first_icu_stay = 1
    """,
    "care unit": """
        SELECT first_careunit, avg(icu_los_days) AS avg_icu_los_days, count(*) AS stay_count
        FROM gold_icu_stay_summary
        GROUP BY first_careunit
        ORDER BY avg_icu_los_days DESC
    """,
    "longer los": """
        SELECT
            avg(CASE WHEN heart_failure_flag = 1 THEN diagnosis_count END) AS hf_avg_diagnosis_count,
            avg(diagnosis_count) AS overall_avg_diagnosis_count
        FROM gold_diagnosis_features
    """,
    "feature completeness": """
        SELECT
            avg(CASE WHEN heart_rate_mean IS NOT NULL THEN 1 ELSE 0 END) AS heart_rate_completeness,
            avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_completeness,
            avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_completeness
        FROM gold_first_24h_features
    """,
    "multiple icu": """
        SELECT count(*) AS patients_with_multiple_icu_stays
        FROM gold_patient_summary
        WHERE total_icu_stays > 1
    """,
    "procedures": """
        SELECT count(*) AS admissions_with_procedures
        FROM gold_admission_summary
        WHERE procedure_count > 0
    """,
    "microbiology": """
        SELECT count(*) AS admissions_with_microbiology_events
        FROM gold_admission_summary
        WHERE microbiology_event_count > 0
    """,
    "adult first": """
        SELECT
            count(*) AS adult_first_icu_stays,
            avg(age_at_admission) AS avg_age,
            avg(icu_los_days) AS avg_icu_los_days,
            avg(hospital_mortality_flag) AS hospital_mortality_rate
        FROM gold_icu_stay_summary
        WHERE is_first_icu_stay = 1 AND age_at_admission >= 18
    """,
}


def generate_sql(question: str) -> str:
    """Generate SQL for common aggregate questions using deterministic rules."""
    normalized = question.lower()
    for key, sql in QUESTION_SQL.items():
        if key in normalized:
            return " ".join(sql.split())
    return (
        "SELECT count(*) AS row_count "
        "FROM gold_icu_stay_summary "
        "LIMIT 100"
    )


def answer_question(
    con: duckdb.DuckDBPyConnection,
    question: str,
    private_log_dir: Path,
    allowed_tables: set[str] | None = None,
    default_limit: int = 100,
) -> dict[str, object]:
    """Generate, validate, execute, and privately log an aggregate query."""
    sql = generate_sql(question)
    guardrail: GuardrailResult = validate_aggregate_sql(sql, allowed_tables, default_limit)
    log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "generated_sql": sql,
        "allowed": guardrail.allowed,
        "reasons": list(guardrail.reasons),
    }
    private_log_dir.mkdir(parents=True, exist_ok=True)
    with (private_log_dir / "llm_query_log.jsonl").open("a") as handle:
        handle.write(json.dumps(log) + "\n")

    if not guardrail.allowed or guardrail.sql is None:
        return {"allowed": False, "reasons": guardrail.reasons, "sql": None, "rows": []}

    rows = con.execute(guardrail.sql).fetchdf().to_dict(orient="records")
    return {
        "allowed": True,
        "sql": guardrail.sql,
        "rows": rows,
        "explanation": explain_sql(guardrail.sql),
    }
