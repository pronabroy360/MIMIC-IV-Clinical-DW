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


SQL_TEMPLATES: dict[str, str] = {
    "patients_count": "SELECT count(*) AS patient_count FROM gold_patient_summary",
    "admissions_count": "SELECT count(*) AS admission_count FROM gold_admission_summary",
    "icu_stays_count": "SELECT count(*) AS icu_stay_count FROM gold_icu_stay_summary",
    "average_icu_los": "SELECT avg(icu_los_days) AS avg_icu_los_days FROM gold_icu_stay_summary",
    "average_hospital_los": "SELECT avg(hospital_los_days) AS avg_hospital_los_days FROM gold_admission_summary",
    "admission_types": """
        SELECT admission_type, count(*) AS admission_count
        FROM gold_admission_summary
        GROUP BY admission_type
        ORDER BY admission_count DESC
    """,
    "discharge_locations": """
        SELECT discharge_location, count(*) AS admission_count
        FROM gold_admission_summary
        GROUP BY discharge_location
        ORDER BY admission_count DESC
    """,
    "diagnosis_groups": """
        SELECT
            sum(sepsis_diagnosis_proxy_flag) AS sepsis_proxy_admissions,
            sum(heart_failure_flag) AS heart_failure_admissions,
            sum(respiratory_failure_flag) AS respiratory_failure_admissions,
            sum(renal_dysfunction_proxy_flag) AS renal_dysfunction_admissions,
            sum(diabetes_flag) AS diabetes_admissions
        FROM gold_diagnosis_features
    """,
    "common_lab_tests": """
        SELECT
            sum(total_lab_events) AS total_lab_events,
            avg(distinct_lab_tests) AS avg_distinct_lab_tests_per_stay,
            avg(abnormal_lab_rate) AS avg_abnormal_lab_rate
        FROM gold_lab_features
    """,
    "lactate_measurement_rate": """
        SELECT avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_measured_first_24h_rate
        FROM gold_first_24h_features
    """,
    "creatinine_measurement_rate": """
        SELECT avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_measured_first_24h_rate
        FROM gold_first_24h_features
    """,
    "mortality_first_icu_stays": """
        SELECT avg(hospital_mortality_flag) AS mortality_rate_first_icu_stays
        FROM gold_icu_stay_summary
        WHERE is_first_icu_stay = 1
    """,
    "average_icu_los_by_care_unit": """
        SELECT first_careunit, avg(icu_los_days) AS avg_icu_los_days, count(*) AS stay_count
        FROM gold_icu_stay_summary
        GROUP BY first_careunit
        ORDER BY avg_icu_los_days DESC
    """,
    "diagnosis_groups_longer_los_proxy": """
        SELECT
            avg(CASE WHEN heart_failure_flag = 1 THEN diagnosis_count END) AS hf_avg_diagnosis_count,
            avg(diagnosis_count) AS overall_avg_diagnosis_count
        FROM gold_diagnosis_features
    """,
    "feature_completeness": """
        SELECT
            avg(CASE WHEN heart_rate_mean IS NOT NULL THEN 1 ELSE 0 END) AS heart_rate_completeness,
            avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_completeness,
            avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_completeness
        FROM gold_first_24h_features
    """,
    "multiple_icu_stays_patients": """
        SELECT count(*) AS patients_with_multiple_icu_stays
        FROM gold_patient_summary
        WHERE total_icu_stays > 1
    """,
    "admissions_with_procedures": """
        SELECT count(*) AS admissions_with_procedures
        FROM gold_admission_summary
        WHERE procedure_count > 0
    """,
    "admissions_with_microbiology_events": """
        SELECT count(*) AS admissions_with_microbiology_events
        FROM gold_admission_summary
        WHERE microbiology_event_count > 0
    """,
    "adult_first_icu_stay_characteristics": """
        SELECT
            count(*) AS adult_first_icu_stays,
            avg(age_at_admission) AS avg_age,
            avg(icu_los_days) AS avg_icu_los_days,
            avg(hospital_mortality_flag) AS hospital_mortality_rate
        FROM gold_icu_stay_summary
        WHERE is_first_icu_stay = 1 AND age_at_admission >= 18
    """,
}

RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("multiple", "icu", "stays"), "multiple_icu_stays_patients"),
    (("diagnosis", "longer", "los"), "diagnosis_groups_longer_los_proxy"),
    (("how many", "patients", "dataset"), "patients_count"),
    (("how many", "hospital", "admissions"), "admissions_count"),
    (("how many", "icu", "stays"), "icu_stays_count"),
    (("average", "icu", "length of stay"), "average_icu_los"),
    (("average", "hospital", "length of stay"), "average_hospital_los"),
    (("admission", "types"), "admission_types"),
    (("discharge", "locations"), "discharge_locations"),
    (("diagnosis", "groups"), "diagnosis_groups"),
    (("common", "lab", "tests"), "common_lab_tests"),
    (("lactate", "first", "24"), "lactate_measurement_rate"),
    (("creatinine", "first", "24"), "creatinine_measurement_rate"),
    (("mortality", "first", "icu", "stays"), "mortality_first_icu_stays"),
    (("care", "unit"), "average_icu_los_by_care_unit"),
    (("feature", "completeness", "vitals"), "feature_completeness"),
    (("feature", "completeness", "labs"), "feature_completeness"),
    (("admissions", "procedures"), "admissions_with_procedures"),
    (("admissions", "microbiology"), "admissions_with_microbiology_events"),
    (("adult", "first", "icu", "stay"), "adult_first_icu_stay_characteristics"),
)


def _has_terms(text: str, terms: tuple[str, ...]) -> bool:
    return all(term in text for term in terms)


def generate_sql(question: str) -> str | None:
    """Generate SQL for common aggregate questions using deterministic rules."""
    normalized = question.lower()
    for terms, template_key in RULES:
        if _has_terms(normalized, terms):
            return " ".join(SQL_TEMPLATES[template_key].split())
    return None


def answer_question(
    con: duckdb.DuckDBPyConnection,
    question: str,
    private_log_dir: Path,
    allowed_tables: set[str] | None = None,
    default_limit: int = 100,
) -> dict[str, object]:
    """Generate, validate, execute, and privately log an aggregate query."""
    sql = generate_sql(question)
    if sql is None:
        return {
            "allowed": False,
            "reasons": ("Unsupported question. Please ask one of the documented aggregate questions or define a study.",),
            "sql": None,
            "rows": [],
        }
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
