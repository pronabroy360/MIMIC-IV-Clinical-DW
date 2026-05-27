-- High lab utilization ICU cohort.
-- Defines high utilization as the top quartile of lab event counts within ICU
-- stays in the currently loaded dataset.
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
),
cohort_rows AS (
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        lab_event_count,
        lab_utilization_percentile
    FROM ranked
    WHERE lab_utilization_percentile >= 0.75
)
SELECT
    'high_lab_utilization_cohort' AS cohort_name,
    count(*) AS cohort_size,
    avg(lab_event_count) AS avg_lab_event_count,
    min(lab_event_count) AS min_lab_event_count_in_top_quartile,
    avg(lab_utilization_percentile) AS avg_lab_utilization_percentile
FROM cohort_rows;
