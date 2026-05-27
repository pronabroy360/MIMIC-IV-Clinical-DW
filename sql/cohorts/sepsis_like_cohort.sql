-- Diagnosis-based sepsis-like cohort.
-- This is a proxy cohort and does not claim Sepsis-3 compliance. It uses ICD
-- labels/codes containing sepsis/septic/infection-like terms and simple organ
-- dysfunction label proxies.
WITH diagnosis_flags AS (
    SELECT
        subject_id,
        hadm_id,
        max(CASE
            WHEN lower(coalesce(diagnosis_label, '')) LIKE '%sepsis%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%septic%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%infection%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%pneumonia%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%bacteremia%'
            THEN 1 ELSE 0
        END) AS sepsis_diagnosis_flag,
        sum(CASE
            WHEN lower(coalesce(diagnosis_label, '')) LIKE '%infection%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%pneumonia%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%bacteremia%'
            THEN 1 ELSE 0
        END) AS infection_related_diagnosis_count,
        max(CASE
            WHEN lower(coalesce(diagnosis_label, '')) LIKE '%shock%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%respiratory failure%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%renal failure%'
              OR lower(coalesce(diagnosis_label, '')) LIKE '%kidney failure%'
            THEN 1 ELSE 0
        END) AS organ_dysfunction_proxy_flag
    FROM silver_diagnoses
    GROUP BY subject_id, hadm_id
),
cohort_rows AS (
    SELECT
        i.subject_id,
        i.hadm_id,
        i.stay_id,
        coalesce(d.sepsis_diagnosis_flag, 0) AS sepsis_diagnosis_flag,
        coalesce(d.infection_related_diagnosis_count, 0) AS infection_related_diagnosis_count,
        coalesce(d.organ_dysfunction_proxy_flag, 0) AS organ_dysfunction_proxy_flag
    FROM gold_icu_stay_summary i
    LEFT JOIN diagnosis_flags d ON i.hadm_id = d.hadm_id
    WHERE coalesce(d.sepsis_diagnosis_flag, 0) = 1
)
SELECT
    'sepsis_like_cohort' AS cohort_name,
    count(*) AS cohort_size,
    sum(sepsis_diagnosis_flag) AS sepsis_diagnosis_count,
    avg(infection_related_diagnosis_count) AS avg_infection_related_diagnoses,
    avg(organ_dysfunction_proxy_flag) AS organ_dysfunction_proxy_rate
FROM cohort_rows;
