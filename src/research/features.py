"""Explicitly timed prospective ICU feature construction."""

from __future__ import annotations

import duckdb

from src.research.cohorts import cohort_cte
from src.research.contracts import StudySpec
from src.research.tasks import task_definition


FEATURE_TABLE = "gold_research_prospective_icu_24h"


def build_prospective_feature_table(con: duckdb.DuckDBPyConnection, spec: StudySpec) -> str:
    """Materialize one ICU stay per row using event and availability timestamps.

    Whole-stay marts, diagnosis codes, procedure codes, and discharge coding are
    deliberately absent from the predictor columns.
    """
    task = task_definition(spec.task_name)
    hours = spec.horizon_hours
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {FEATURE_TABLE} AS
        WITH {cohort_cte(spec)},
        chart_events AS (
            SELECT e.stay_id, lower(e.chart_label) AS label, e.valuenum
            FROM eligible_stays s
            JOIN silver_chart_events e ON e.stay_id = s.stay_id
             AND e.charttime >= s.intime AND e.charttime < s.prediction_time
             AND e.storetime IS NOT NULL AND e.storetime >= e.charttime
             AND e.storetime <= s.prediction_time
            WHERE e.valuenum IS NOT NULL
        ),
        chart_features AS (
            SELECT stay_id,
                avg(valuenum) FILTER (WHERE label LIKE '%heart rate%') AS heart_rate_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%systolic%') AS sbp_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%diastolic%') AS dbp_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%respiratory rate%') AS resp_rate_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%temperature%') AS temperature_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%o2 saturation%' OR label LIKE '%spo2%') AS spo2_mean,
                count(*) AS chart_event_count_24h
            FROM chart_events GROUP BY stay_id
        ),
        lab_events AS (
            SELECT s.stay_id, lower(l.lab_label) AS label, l.valuenum
            FROM eligible_stays s
            JOIN silver_labs l ON l.hadm_id = s.hadm_id
             AND l.charttime >= s.intime AND l.charttime < s.prediction_time
             AND l.storetime IS NOT NULL AND l.storetime >= l.charttime
             AND l.storetime <= s.prediction_time
            WHERE l.valuenum IS NOT NULL
        ),
        lab_features AS (
            SELECT stay_id,
                avg(valuenum) FILTER (WHERE label LIKE '%white blood%' OR label LIKE '%wbc%') AS wbc_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%hemoglobin%') AS hemoglobin_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%platelet%') AS platelet_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%creatinine%') AS creatinine_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%urea nitrogen%' OR label LIKE '%bun%') AS bun_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%sodium%') AS sodium_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%potassium%') AS potassium_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%glucose%') AS glucose_mean,
                avg(valuenum) FILTER (WHERE label LIKE '%lactate%') AS lactate_mean,
                count(*) AS lab_event_count_24h
            FROM lab_events GROUP BY stay_id
        ),
        input_features AS (
            SELECT s.stay_id,
                max(CASE WHEN lower(i.input_label) LIKE '%norepinephrine%' THEN 1 ELSE 0 END) AS vasopressor_first_24h_flag
            FROM eligible_stays s
            LEFT JOIN silver_input_events i ON i.stay_id = s.stay_id
             AND i.starttime >= s.intime AND i.starttime < s.prediction_time
             AND i.storetime IS NOT NULL AND i.storetime >= i.starttime
             AND i.storetime <= s.prediction_time
            GROUP BY s.stay_id
        )
        SELECT
            s.subject_id, s.hadm_id, s.stay_id, s.intime, s.outtime,
            s.prediction_time, s.dischtime, s.deathtime, s.age_at_admission,
            s.gender, s.admission_type, s.first_careunit,
            c.heart_rate_mean, c.sbp_mean, c.dbp_mean, c.resp_rate_mean,
            c.temperature_mean, c.spo2_mean, l.wbc_mean, l.hemoglobin_mean,
            l.platelet_mean, l.creatinine_mean, l.bun_mean, l.sodium_mean,
            l.potassium_mean, l.glucose_mean, l.lactate_mean,
            coalesce(c.chart_event_count_24h, 0) AS chart_event_count_24h,
            coalesce(l.lab_event_count_24h, 0) AS lab_event_count_24h,
            coalesce(i.vasopressor_first_24h_flag, 0) AS vasopressor_first_24h_flag,
            CASE WHEN s.deathtime > s.prediction_time AND s.deathtime <= s.dischtime THEN 1 ELSE 0 END AS {task.target_column}
        FROM eligible_stays s
        LEFT JOIN chart_features c USING (stay_id)
        LEFT JOIN lab_features l USING (stay_id)
        LEFT JOIN input_features i USING (stay_id)
        """
    )
    return FEATURE_TABLE


def feature_audit(con: duckdb.DuckDBPyConnection, spec: StudySpec) -> list[dict[str, object]]:
    """Return aggregate active-feature coverage without patient-level exports."""
    task = task_definition(spec.task_name)
    rows: list[dict[str, object]] = []
    count = int(con.execute(f"SELECT count(*) FROM {FEATURE_TABLE}").fetchone()[0])
    for name in task.numeric_features + task.categorical_features:
        observed = int(con.execute(
            f"SELECT count(*) FROM {FEATURE_TABLE} WHERE \"{name}\" IS NOT NULL"
        ).fetchone()[0])
        distinct = int(con.execute(
            f"SELECT count(DISTINCT \"{name}\") FROM {FEATURE_TABLE} WHERE \"{name}\" IS NOT NULL"
        ).fetchone()[0])
        status = "active" if observed and distinct > 1 else "inactive_insufficient_variation"
        rows.append({"feature": name, "observed_rows": observed, "missing_rate": 1 - observed / max(1, count), "distinct_values": distinct, "status": status})
    return rows
