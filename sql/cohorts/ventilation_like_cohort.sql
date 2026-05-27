-- Ventilation-like ICU cohort.
-- Uses ICU procedure/chart labels containing ventilation-related terms. This is
-- a utilization proxy, not a mechanically ventilated phenotype guarantee.
WITH events AS (
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        starttime AS event_time,
        procedure_event_label AS event_label
    FROM silver_procedure_events
    WHERE lower(coalesce(procedure_event_label, '')) LIKE '%ventilat%'
       OR lower(coalesce(procedure_event_label, '')) LIKE '%intubat%'
    UNION ALL
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        charttime AS event_time,
        chart_label AS event_label
    FROM silver_chart_events
    WHERE lower(coalesce(chart_label, '')) LIKE '%ventilat%'
       OR lower(coalesce(chart_label, '')) LIKE '%intubat%'
),
cohort_rows AS (
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        1 AS ventilation_event_flag,
        min(event_time) AS first_ventilation_time,
        count(*) AS ventilation_event_count
    FROM events
    GROUP BY subject_id, hadm_id, stay_id
)
SELECT
    'ventilation_like_cohort' AS cohort_name,
    count(*) AS cohort_size,
    sum(ventilation_event_flag) AS stays_with_ventilation_proxy,
    avg(ventilation_event_count) AS avg_ventilation_event_count
FROM cohort_rows;
