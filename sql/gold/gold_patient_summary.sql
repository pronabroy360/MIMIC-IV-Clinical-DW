CREATE OR REPLACE TABLE gold_patient_summary AS
SELECT
    p.subject_id,
    p.gender,
    p.anchor_age,
    p.anchor_year,
    p.anchor_year_group,
    p.derived_age_group,
    count(DISTINCT a.hadm_id) AS total_admissions,
    count(DISTINCT i.stay_id) AS total_icu_stays,
    min(a.admittime) AS first_admission_time,
    max(a.dischtime) AS last_discharge_time,
    coalesce(max(a.in_hospital_mortality_flag), 0) AS ever_in_hospital_mortality,
    coalesce(max(
        CASE
            WHEN p.dod IS NOT NULL AND i.intime IS NOT NULL AND i.outtime IS NOT NULL
             AND p.dod BETWEEN i.intime AND i.outtime THEN 1
            ELSE 0
        END
    ), 0) AS ever_icu_mortality
FROM silver_patients p
LEFT JOIN silver_admissions a
    ON p.subject_id = a.subject_id
LEFT JOIN silver_icustays i
    ON a.hadm_id = i.hadm_id
GROUP BY
    p.subject_id,
    p.gender,
    p.anchor_age,
    p.anchor_year,
    p.anchor_year_group,
    p.derived_age_group;
