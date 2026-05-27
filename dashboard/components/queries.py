"""Aggregate DuckDB queries for Streamlit pages."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import load_config  # noqa: E402
from src.core.db import connect, table_exists  # noqa: E402
from src.core.paths import project_root  # noqa: E402
from src.llm.nl_to_sql import answer_question  # noqa: E402
from src.llm.sql_guardrails import validate_aggregate_sql  # noqa: E402


def get_config():
    """Load dashboard config."""
    return load_config(os.getenv("MIMIC_CONFIG_PATH", "configs/demo.duckdb.yaml"))


def query_df(sql: str) -> pd.DataFrame:
    """Run an aggregate query and return a DataFrame."""
    with connect(get_config()) as con:
        return con.execute(sql).fetchdf()


def safe_query_df(sql: str) -> pd.DataFrame:
    """Run guarded aggregate SQL from the dashboard query assistant."""
    config = get_config()
    guardrail = validate_aggregate_sql(
        sql,
        allowed_tables=set(config.llm.allowed_tables),
        default_limit=config.llm.default_limit,
    )
    if not guardrail.allowed or guardrail.sql is None:
        raise ValueError("; ".join(guardrail.reasons))
    return query_df(guardrail.sql)


def overview_metrics() -> dict[str, object]:
    """Return dashboard overview metrics."""
    df = query_df(
        """
        SELECT
            (SELECT count(*) FROM gold_patient_summary) AS patients,
            (SELECT count(*) FROM gold_admission_summary) AS admissions,
            (SELECT count(*) FROM gold_icu_stay_summary) AS icu_stays,
            (SELECT coalesce(sum(lab_event_count), 0) FROM gold_admission_summary) AS lab_events,
            (SELECT coalesce(sum(medication_count), 0) FROM gold_admission_summary) AS medication_events,
            (SELECT coalesce(sum(chart_event_count_24h), 0) FROM gold_first_24h_features) AS chart_events_24h,
            (SELECT avg(hospital_los_days) FROM gold_admission_summary) AS avg_hospital_los,
            (SELECT avg(icu_los_days) FROM gold_icu_stay_summary) AS avg_icu_los,
            (SELECT avg(in_hospital_mortality_flag) FROM gold_admission_summary) AS mortality_rate
        """
    )
    return df.iloc[0].to_dict() if not df.empty else {}


def table_exists_in_db(table: str) -> bool:
    """Check table existence."""
    with connect(get_config()) as con:
        return table_exists(con, table)


def cohort_summary(cohort_name: str) -> pd.DataFrame:
    """Execute privacy-safe cohort summary SQL."""
    path = project_root() / "sql" / "cohorts" / f"{cohort_name}.sql"
    if not path.exists():
        raise ValueError(f"Unknown cohort: {cohort_name}")
    return query_df(path.read_text())


def _cohort_rows_cte_sql(cohort_name: str) -> str:
    if cohort_name == "adult_icu_first_stay":
        return """
        SELECT subject_id, hadm_id, stay_id
        FROM gold_icu_stay_summary
        WHERE is_first_icu_stay = 1
          AND age_at_admission >= 18
          AND intime IS NOT NULL
          AND outtime IS NOT NULL
          AND icu_los_days > 0
        """
    if cohort_name == "sepsis_like_cohort":
        return """
        WITH diagnosis_flags AS (
            SELECT
                hadm_id,
                max(CASE
                    WHEN lower(coalesce(diagnosis_label, '')) LIKE '%sepsis%'
                      OR lower(coalesce(diagnosis_label, '')) LIKE '%septic%'
                      OR lower(coalesce(diagnosis_label, '')) LIKE '%infection%'
                      OR lower(coalesce(diagnosis_label, '')) LIKE '%pneumonia%'
                      OR lower(coalesce(diagnosis_label, '')) LIKE '%bacteremia%'
                    THEN 1 ELSE 0
                END) AS sepsis_diagnosis_flag
            FROM silver_diagnoses
            GROUP BY hadm_id
        )
        SELECT i.subject_id, i.hadm_id, i.stay_id
        FROM gold_icu_stay_summary i
        JOIN diagnosis_flags d ON i.hadm_id = d.hadm_id
        WHERE d.sepsis_diagnosis_flag = 1
        """
    if cohort_name == "heart_failure_cohort":
        return """
        WITH hf_admissions AS (
            SELECT DISTINCT hadm_id
            FROM silver_diagnoses
            WHERE lower(coalesce(diagnosis_label, '')) LIKE '%heart failure%'
               OR lower(coalesce(diagnosis_label, '')) LIKE '%congestive%'
               OR icd_code LIKE 'I50%'
               OR icd_code LIKE '428%'
        )
        SELECT i.subject_id, i.hadm_id, i.stay_id
        FROM gold_icu_stay_summary i
        JOIN hf_admissions h ON i.hadm_id = h.hadm_id
        """
    if cohort_name == "ventilation_like_cohort":
        return """
        WITH events AS (
            SELECT subject_id, hadm_id, stay_id
            FROM silver_procedure_events
            WHERE lower(coalesce(procedure_event_label, '')) LIKE '%ventilat%'
               OR lower(coalesce(procedure_event_label, '')) LIKE '%intubat%'
            UNION
            SELECT subject_id, hadm_id, stay_id
            FROM silver_chart_events
            WHERE lower(coalesce(chart_label, '')) LIKE '%ventilat%'
               OR lower(coalesce(chart_label, '')) LIKE '%intubat%'
        )
        SELECT DISTINCT subject_id, hadm_id, stay_id
        FROM events
        """
    if cohort_name == "high_lab_utilization_cohort":
        return """
        WITH lab_counts AS (
            SELECT
                i.subject_id,
                i.hadm_id,
                i.stay_id,
                count(l.itemid) AS lab_event_count
            FROM silver_icustays i
            LEFT JOIN silver_labs l
                ON i.hadm_id = l.hadm_id
               AND l.charttime >= i.intime
               AND l.charttime < i.outtime
            GROUP BY i.subject_id, i.hadm_id, i.stay_id
        ),
        ranked AS (
            SELECT
                *,
                cume_dist() OVER (ORDER BY lab_event_count) AS lab_utilization_percentile
            FROM lab_counts
        )
        SELECT subject_id, hadm_id, stay_id
        FROM ranked
        WHERE lab_utilization_percentile >= 0.75
        """
    raise ValueError(f"Unknown cohort: {cohort_name}")


def cohort_detail_tables(cohort_name: str) -> dict[str, pd.DataFrame]:
    """Return aggregate demographics, outcomes, and feature completeness for a cohort."""
    cohort_rows = _cohort_rows_cte_sql(cohort_name)
    demographics = query_df(
        f"""
        WITH cohort_rows AS ({cohort_rows})
        SELECT
            count(*) AS cohort_stay_count,
            count(DISTINCT s.subject_id) AS cohort_patient_count,
            avg(s.age_at_admission) AS avg_age_at_admission,
            avg(CASE WHEN s.gender = 'F' THEN 1 ELSE 0 END) AS female_rate,
            count(DISTINCT s.race) AS race_category_count
        FROM gold_icu_stay_summary s
        JOIN cohort_rows c
          ON s.stay_id = c.stay_id
        """
    )
    outcomes = query_df(
        f"""
        WITH cohort_rows AS ({cohort_rows})
        SELECT
            avg(s.icu_los_days) AS avg_icu_los_days,
            avg(a.hospital_los_days) AS avg_hospital_los_days,
            avg(s.icu_mortality_flag) AS icu_mortality_rate,
            avg(s.hospital_mortality_flag) AS hospital_mortality_rate
        FROM gold_icu_stay_summary s
        JOIN cohort_rows c
          ON s.stay_id = c.stay_id
        LEFT JOIN gold_admission_summary a
          ON s.hadm_id = a.hadm_id
        """
    )
    feature_completeness = query_df(
        f"""
        WITH cohort_rows AS ({cohort_rows})
        SELECT
            avg(CASE WHEN f.heart_rate_mean IS NOT NULL THEN 1 ELSE 0 END) AS heart_rate_completeness,
            avg(CASE WHEN f.creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_completeness,
            avg(CASE WHEN f.lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_completeness,
            avg(CASE WHEN f.wbc_mean IS NOT NULL THEN 1 ELSE 0 END) AS wbc_completeness
        FROM gold_first_24h_features f
        JOIN cohort_rows c
          ON f.stay_id = c.stay_id
        """
    )
    return {
        "demographics": demographics,
        "outcomes": outcomes,
        "feature_completeness": feature_completeness,
    }


def cohort_names() -> list[str]:
    """Return available cohort names."""
    return sorted(path.stem for path in (project_root() / "sql" / "cohorts").glob("*.sql"))


def ask_demo_question(question: str) -> dict[str, object]:
    """Run the guarded rule-based query assistant."""
    config = get_config()
    with connect(config) as con:
        return answer_question(
            con,
            question,
            config.outputs_private_path,
            allowed_tables=set(config.llm.allowed_tables),
            default_limit=config.llm.default_limit,
        )
