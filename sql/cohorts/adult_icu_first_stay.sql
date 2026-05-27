-- Adult first ICU stay cohort.
-- Assumptions:
-- 1. Age is derived from MIMIC anchor age/year and admission year.
-- 2. Public/dashboard use returns aggregate counts only; the cohort_rows CTE is
--    the private row-level definition for credentialed local analysis.
WITH cohort_rows AS (
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        age_at_admission,
        gender,
        race,
        admission_type,
        intime,
        outtime,
        icu_los_days,
        NULL::DOUBLE AS hospital_los_days,
        hospital_mortality_flag
    FROM gold_icu_stay_summary
    WHERE is_first_icu_stay = 1
      AND age_at_admission >= 18
      AND intime IS NOT NULL
      AND outtime IS NOT NULL
      AND icu_los_days > 0
)
SELECT
    'adult_icu_first_stay' AS cohort_name,
    count(*) AS cohort_size,
    avg(age_at_admission) AS avg_age_at_admission,
    avg(icu_los_days) AS avg_icu_los_days,
    avg(hospital_mortality_flag) AS hospital_mortality_rate
FROM cohort_rows;
