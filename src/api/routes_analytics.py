"""Aggregate analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.core.db import connect
from src.llm.sql_guardrails import validate_aggregate_sql

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _records(con, sql: str) -> list[dict[str, object]]:
    return con.execute(sql).fetchdf().to_dict(orient="records")


@router.get("/overview")
def overview() -> dict[str, object]:
    from src.api.main import get_config

    sql = """
    SELECT
        (SELECT count(*) FROM gold_patient_summary) AS patient_count,
        (SELECT count(*) FROM gold_admission_summary) AS admission_count,
        (SELECT count(*) FROM gold_icu_stay_summary) AS icu_stay_count,
        (SELECT coalesce(sum(lab_event_count), 0) FROM gold_admission_summary) AS lab_event_count,
        (SELECT coalesce(sum(medication_count), 0) FROM gold_admission_summary) AS medication_event_count,
        (SELECT coalesce(sum(chart_event_count_24h), 0) FROM gold_first_24h_features) AS chart_event_count_24h,
        (SELECT avg(hospital_los_days) FROM gold_admission_summary) AS avg_hospital_los_days,
        (SELECT avg(icu_los_days) FROM gold_icu_stay_summary) AS avg_icu_los_days,
        (SELECT avg(in_hospital_mortality_flag) FROM gold_admission_summary) AS hospital_mortality_rate
    """
    with connect(get_config()) as con:
        return _records(con, sql)[0]


@router.get("/admissions")
def admissions() -> dict[str, list[dict[str, object]]]:
    from src.api.main import get_config

    with connect(get_config()) as con:
        return {
            "by_type": _records(
                con,
                """
                SELECT admission_type, count(*) AS admissions, avg(hospital_los_days) AS avg_los_days,
                       avg(in_hospital_mortality_flag) AS mortality_rate
                FROM gold_admission_summary
                GROUP BY admission_type
                ORDER BY admissions DESC
                LIMIT 100
                """,
            ),
            "by_race": _records(
                con,
                """
                SELECT race, count(*) AS admissions
                FROM gold_admission_summary
                GROUP BY race
                ORDER BY admissions DESC
                LIMIT 100
                """,
            ),
        }


@router.get("/icu")
def icu() -> dict[str, list[dict[str, object]]]:
    from src.api.main import get_config

    with connect(get_config()) as con:
        return {
            "by_careunit": _records(
                con,
                """
                SELECT first_careunit, count(*) AS stays, avg(icu_los_days) AS avg_icu_los_days,
                       avg(icu_mortality_flag) AS icu_mortality_rate
                FROM gold_icu_stay_summary
                GROUP BY first_careunit
                ORDER BY stays DESC
                LIMIT 100
                """,
            )
        }


@router.get("/labs")
def labs() -> dict[str, list[dict[str, object]]]:
    from src.api.main import get_config

    with connect(get_config()) as con:
        return {
            "feature_completeness": _records(
                con,
                """
                SELECT
                    avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_24h_rate,
                    avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_24h_rate,
                    avg(CASE WHEN wbc_mean IS NOT NULL THEN 1 ELSE 0 END) AS wbc_24h_rate
                FROM gold_first_24h_features
                LIMIT 100
                """,
            )
        }
