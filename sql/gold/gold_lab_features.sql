CREATE OR REPLACE TABLE gold_lab_features AS
WITH stay_labs AS (
    SELECT
        i.stay_id,
        i.subject_id,
        i.hadm_id,
        lower(l.lab_label) AS lab_label,
        l.is_abnormal,
        l.charttime
    FROM silver_icustays i
    LEFT JOIN silver_labs l
        ON i.hadm_id = l.hadm_id
       AND l.charttime >= i.intime
       AND l.charttime < i.outtime
)
SELECT
    subject_id,
    hadm_id,
    stay_id,
    count(lab_label) AS total_lab_events,
    count(DISTINCT lab_label) AS distinct_lab_tests,
    avg(is_abnormal) AS abnormal_lab_rate,
    max(CASE WHEN lab_label LIKE '%lactate%' THEN 1 ELSE 0 END) AS lactate_measured_during_icu,
    max(CASE WHEN lab_label LIKE '%creatinine%' THEN 1 ELSE 0 END) AS creatinine_measured_during_icu,
    max(CASE WHEN lab_label LIKE '%lactate%' AND charttime IS NOT NULL THEN 1 ELSE 0 END) AS lactate_measured_flag,
    max(CASE WHEN lab_label LIKE '%creatinine%' AND charttime IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_measured_flag
FROM stay_labs
GROUP BY subject_id, hadm_id, stay_id;
