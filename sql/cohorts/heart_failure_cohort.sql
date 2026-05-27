-- Heart failure admission cohort.
-- Uses ICD diagnosis labels and broad code patterns as a transparent proxy.
WITH hf_rows AS (
    SELECT
        subject_id,
        hadm_id,
        icd_code,
        diagnosis_label,
        row_number() OVER (PARTITION BY hadm_id ORDER BY seq_num NULLS LAST) AS rn
    FROM silver_diagnoses
    WHERE lower(coalesce(diagnosis_label, '')) LIKE '%heart failure%'
       OR lower(coalesce(diagnosis_label, '')) LIKE '%congestive%'
       OR icd_code LIKE 'I50%'
       OR icd_code LIKE '428%'
),
cohort_rows AS (
    SELECT
        subject_id,
        hadm_id,
        1 AS heart_failure_flag,
        icd_code AS primary_hf_code,
        diagnosis_label AS hf_diagnosis_label
    FROM hf_rows
    WHERE rn = 1
)
SELECT
    'heart_failure_cohort' AS cohort_name,
    count(*) AS cohort_size,
    sum(heart_failure_flag) AS heart_failure_admissions,
    count(DISTINCT primary_hf_code) AS distinct_hf_codes
FROM cohort_rows;
