CREATE OR REPLACE TABLE gold_diagnosis_features AS
WITH labels AS (
    SELECT
        subject_id,
        hadm_id,
        seq_num,
        icd_code,
        icd_version,
        lower(coalesce(diagnosis_label, '')) AS label
    FROM silver_diagnoses
)
SELECT
    subject_id,
    hadm_id,
    count(*) AS diagnosis_count,
    max(CASE WHEN label LIKE '%sepsis%' OR label LIKE '%septic%' THEN 1 ELSE 0 END) AS sepsis_diagnosis_proxy_flag,
    max(CASE WHEN label LIKE '%heart failure%' OR label LIKE '%congestive%' THEN 1 ELSE 0 END) AS heart_failure_flag,
    max(CASE WHEN label LIKE '%respiratory failure%' THEN 1 ELSE 0 END) AS respiratory_failure_flag,
    max(CASE WHEN label LIKE '%kidney%' OR label LIKE '%renal failure%' THEN 1 ELSE 0 END) AS renal_dysfunction_proxy_flag,
    max(CASE WHEN label LIKE '%diabetes%' THEN 1 ELSE 0 END) AS diabetes_flag,
    max(CASE WHEN label LIKE '%pneumonia%' THEN 1 ELSE 0 END) AS pneumonia_flag
FROM labels
GROUP BY subject_id, hadm_id;
