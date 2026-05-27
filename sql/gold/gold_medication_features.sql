CREATE OR REPLACE TABLE gold_medication_features AS
SELECT
    a.subject_id,
    a.hadm_id,
    count(m.medication_name) AS medication_event_count,
    count(DISTINCT lower(m.medication_name)) AS distinct_medication_count,
    max(CASE WHEN lower(m.medication_name) LIKE '%vasopress%' OR lower(m.medication_name) LIKE '%norepinephrine%' THEN 1 ELSE 0 END) AS vasopressor_name_proxy_flag,
    max(CASE WHEN lower(m.medication_name) LIKE '%antibiotic%' OR lower(m.medication_name) LIKE '%cef%' OR lower(m.medication_name) LIKE '%vancomycin%' THEN 1 ELSE 0 END) AS antibiotic_name_proxy_flag
FROM silver_admissions a
LEFT JOIN silver_medications m
    ON a.hadm_id = m.hadm_id
GROUP BY a.subject_id, a.hadm_id;
