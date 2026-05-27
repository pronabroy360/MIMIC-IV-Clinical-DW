"""Evaluate generated aggregate SQL against manual SQL references."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.llm.nl_to_sql import generate_sql
from src.llm.sql_guardrails import validate_aggregate_sql


EVALUATION_SET: dict[str, str] = {
    "How many patients are in the dataset?": "SELECT count(*) AS patient_count FROM gold_patient_summary",
    "How many hospital admissions exist?": "SELECT count(*) AS admission_count FROM gold_admission_summary",
    "How many ICU stays exist?": "SELECT count(*) AS icu_stay_count FROM gold_icu_stay_summary",
    "What is the average ICU length of stay?": "SELECT avg(icu_los_days) AS avg_icu_los_days FROM gold_icu_stay_summary",
    "What is the average hospital length of stay?": "SELECT avg(hospital_los_days) AS avg_hospital_los_days FROM gold_admission_summary",
    "What are the most common admission types?": "SELECT admission_type, count(*) AS admission_count FROM gold_admission_summary GROUP BY admission_type ORDER BY admission_count DESC",
    "What are the most common discharge locations?": "SELECT discharge_location, count(*) AS admission_count FROM gold_admission_summary GROUP BY discharge_location ORDER BY admission_count DESC",
    "What are the most frequent diagnosis groups?": "SELECT sum(sepsis_diagnosis_proxy_flag) AS sepsis_proxy_admissions, sum(heart_failure_flag) AS heart_failure_admissions, sum(respiratory_failure_flag) AS respiratory_failure_admissions, sum(renal_dysfunction_proxy_flag) AS renal_dysfunction_admissions, sum(diabetes_flag) AS diabetes_admissions FROM gold_diagnosis_features",
    "What are the most common lab tests?": "SELECT sum(total_lab_events) AS total_lab_events, avg(distinct_lab_tests) AS avg_distinct_lab_tests_per_stay, avg(abnormal_lab_rate) AS avg_abnormal_lab_rate FROM gold_lab_features",
    "What percentage of ICU stays have lactate measured in the first 24 hours?": "SELECT avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_measured_first_24h_rate FROM gold_first_24h_features",
    "What percentage of ICU stays have creatinine measured in the first 24 hours?": "SELECT avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_measured_first_24h_rate FROM gold_first_24h_features",
    "What is the mortality rate among first ICU stays?": "SELECT avg(hospital_mortality_flag) AS mortality_rate_first_icu_stays FROM gold_icu_stay_summary WHERE is_first_icu_stay = 1",
    "What is the average ICU LOS by care unit?": "SELECT first_careunit, avg(icu_los_days) AS avg_icu_los_days, count(*) AS stay_count FROM gold_icu_stay_summary GROUP BY first_careunit ORDER BY avg_icu_los_days DESC",
    "What diagnosis groups are associated with longer LOS?": "SELECT avg(CASE WHEN heart_failure_flag = 1 THEN diagnosis_count END) AS hf_avg_diagnosis_count, avg(diagnosis_count) AS overall_avg_diagnosis_count FROM gold_diagnosis_features",
    "What is the feature completeness of first-24-hour vitals?": "SELECT avg(CASE WHEN heart_rate_mean IS NOT NULL THEN 1 ELSE 0 END) AS heart_rate_completeness, avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_completeness, avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_completeness FROM gold_first_24h_features",
    "What is the feature completeness of first-24-hour labs?": "SELECT avg(CASE WHEN heart_rate_mean IS NOT NULL THEN 1 ELSE 0 END) AS heart_rate_completeness, avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_completeness, avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_completeness FROM gold_first_24h_features",
    "How many patients have multiple ICU stays?": "SELECT count(*) AS patients_with_multiple_icu_stays FROM gold_patient_summary WHERE total_icu_stays > 1",
    "How many admissions include procedures?": "SELECT count(*) AS admissions_with_procedures FROM gold_admission_summary WHERE procedure_count > 0",
    "How many admissions include microbiology events?": "SELECT count(*) AS admissions_with_microbiology_events FROM gold_admission_summary WHERE microbiology_event_count > 0",
    "What are the aggregate characteristics of the adult first ICU stay cohort?": "SELECT count(*) AS adult_first_icu_stays, avg(age_at_admission) AS avg_age, avg(icu_los_days) AS avg_icu_los_days, avg(hospital_mortality_flag) AS hospital_mortality_rate FROM gold_icu_stay_summary WHERE is_first_icu_stay = 1 AND age_at_admission >= 18",
}


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.lower().split())


def run_sql_evaluation(
    con: duckdb.DuckDBPyConnection,
    output_private_dir: Path,
    output_public_dir: Path,
    allowed_tables: set[str],
    default_limit: int,
) -> tuple[Path, Path]:
    """Evaluate generated SQL and write comparison outputs."""
    rows: list[dict[str, object]] = []
    for question, manual_sql in EVALUATION_SET.items():
        generated_sql = generate_sql(question)
        generated_guard = validate_aggregate_sql(
            generated_sql,
            allowed_tables=allowed_tables,
            default_limit=default_limit,
        )
        manual_guard = validate_aggregate_sql(
            manual_sql,
            allowed_tables=allowed_tables,
            default_limit=default_limit,
        )
        generated_safe_sql = generated_guard.sql if generated_guard.allowed else ""
        manual_safe_sql = manual_guard.sql if manual_guard.allowed else ""
        exact_match = _normalize_sql(generated_safe_sql) == _normalize_sql(manual_safe_sql)

        execution_ok = False
        if generated_guard.allowed and generated_guard.sql:
            con.execute(generated_guard.sql).fetchdf()
            execution_ok = True

        rows.append(
            {
                "question": question,
                "generated_sql": generated_safe_sql,
                "manual_sql": manual_safe_sql,
                "generated_sql_allowed": generated_guard.allowed,
                "manual_sql_allowed": manual_guard.allowed,
                "exact_sql_match": exact_match,
                "execution_ok": execution_ok,
            }
        )

    df = pd.DataFrame(rows)
    output_private_dir.mkdir(parents=True, exist_ok=True)
    output_public_dir.mkdir(parents=True, exist_ok=True)

    private_path = output_private_dir / "llm_sql_evaluation_detailed.csv"
    public_path = output_public_dir / "llm_sql_evaluation_comparison.csv"
    summary_path = output_public_dir / "llm_sql_evaluation_summary.md"

    df.to_csv(private_path, index=False)
    df.to_csv(public_path, index=False)

    summary = {
        "total_questions": int(len(df)),
        "generated_allowed_count": int(df["generated_sql_allowed"].sum()),
        "manual_allowed_count": int(df["manual_sql_allowed"].sum()),
        "exact_sql_match_count": int(df["exact_sql_match"].sum()),
        "execution_ok_count": int(df["execution_ok"].sum()),
    }
    summary_path.write_text(
        "\n".join(
            [
                "# LLM SQL Evaluation Summary",
                "",
                f"- Total questions: {summary['total_questions']}",
                f"- Generated SQL allowed: {summary['generated_allowed_count']}",
                f"- Manual SQL allowed: {summary['manual_allowed_count']}",
                f"- Exact SQL matches: {summary['exact_sql_match_count']}",
                f"- Execution OK: {summary['execution_ok_count']}",
                "",
                "This file is generated from synthetic/demo-safe aggregate queries only.",
                "",
            ]
        )
    )
    return public_path, summary_path
