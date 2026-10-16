"""Cohort SQL and ordered aggregate flow for the supported ICU study."""

from __future__ import annotations

import duckdb

from src.core.db import sql_literal
from src.research.contracts import StudySpec


def cohort_cte(spec: StudySpec) -> str:
    """Compile a fixed-grain, parameter-free CTE from a validated spec."""
    hours = spec.horizon_hours
    care_unit_predicate = "" if spec.care_unit is None else f"WHERE first_careunit = {sql_literal(spec.care_unit)}"
    return f"""
    base AS (
        SELECT
            i.subject_id, i.hadm_id, i.stay_id, i.intime, i.outtime,
            a.admittime, a.dischtime, a.deathtime, a.admission_type,
            p.gender, a.age_at_admission, i.first_careunit,
            i.intime + INTERVAL '{hours} hours' AS prediction_time,
            row_number() OVER (PARTITION BY i.subject_id ORDER BY i.intime, i.stay_id) AS first_icu_rank
        FROM silver_icustays i
        JOIN silver_admissions a ON i.hadm_id = a.hadm_id
        JOIN silver_patients p ON i.subject_id = p.subject_id
    ),
    first_stays AS (
        SELECT * FROM base WHERE first_icu_rank = 1
    ),
    adult_stays AS (
        SELECT * FROM first_stays WHERE age_at_admission >= {spec.minimum_age}
    ),
    care_unit_stays AS (
        SELECT * FROM adult_stays {care_unit_predicate}
    ),
    eligible_stays AS (
        SELECT * FROM care_unit_stays
        WHERE intime IS NOT NULL
          AND outtime > prediction_time
          AND (deathtime IS NULL OR deathtime > prediction_time)
    )
    """


def cohort_flow(con: duckdb.DuckDBPyConnection, spec: StudySpec) -> list[dict[str, object]]:
    """Return ordered flow counts after each predicate at ICU-stay grain."""
    cte = cohort_cte(spec)
    rows = con.execute(
        f"""
        WITH {cte}
        SELECT 'all_icu_stays' AS step, count(*) AS icu_stays, count(DISTINCT subject_id) AS patients FROM base
        UNION ALL SELECT 'first_icu_stay_per_patient', count(*), count(DISTINCT subject_id) FROM first_stays
        UNION ALL SELECT 'adult_first_icu_stay', count(*), count(DISTINCT subject_id) FROM adult_stays
        UNION ALL SELECT 'selected_care_unit', count(*), count(DISTINCT subject_id) FROM care_unit_stays
        UNION ALL SELECT 'eligible_at_prediction_time', count(*), count(DISTINCT subject_id) FROM eligible_stays
        """
    ).fetchdf()
    return rows.to_dict(orient="records")
