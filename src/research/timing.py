"""Temporal predicates and aggregate timing audits for prospective studies."""

from __future__ import annotations

import duckdb

from src.research.contracts import StudySpec


def timing_audit(con: duckdb.DuckDBPyConnection, spec: StudySpec) -> list[dict[str, object]]:
    """Count lab events by prospective eligibility reason without exposing rows."""
    hours = spec.horizon_hours
    rows = con.execute(
        f"""
        WITH first_stays AS (
            SELECT i.*, a.deathtime, a.age_at_admission,
                row_number() OVER (PARTITION BY i.subject_id ORDER BY i.intime, i.stay_id) AS rn
            FROM silver_icustays i JOIN silver_admissions a USING (hadm_id)
        ), anchors AS (
            SELECT *, intime + INTERVAL '{hours} hours' AS prediction_time
            FROM first_stays WHERE rn = 1 AND age_at_admission >= {spec.minimum_age}
        )
        SELECT
            CASE
                WHEN l.charttime < a.intime THEN 'before_anchor'
                WHEN l.charttime >= a.prediction_time THEN 'after_prediction_time'
                WHEN l.storetime IS NULL THEN 'unknown_availability'
                WHEN l.storetime < l.charttime THEN 'availability_before_measurement'
                WHEN l.storetime > a.prediction_time THEN 'available_after_prediction_time'
                ELSE 'eligible'
            END AS reason,
            count(*) AS event_count
        FROM anchors a
        JOIN silver_labs l ON l.hadm_id = a.hadm_id
        GROUP BY 1 ORDER BY 1
        """
    ).fetchdf()
    return rows.to_dict(orient="records")
