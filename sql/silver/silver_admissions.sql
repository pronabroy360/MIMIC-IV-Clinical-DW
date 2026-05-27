CREATE OR REPLACE TABLE silver_admissions AS
SELECT
    try_cast(a.subject_id AS BIGINT) AS subject_id,
    try_cast(a.hadm_id AS BIGINT) AS hadm_id,
    try_cast(a.admittime AS TIMESTAMP) AS admittime,
    try_cast(a.dischtime AS TIMESTAMP) AS dischtime,
    try_cast(a.deathtime AS TIMESTAMP) AS deathtime,
    cast(a.admission_type AS VARCHAR) AS admission_type,
    cast(a.admission_location AS VARCHAR) AS admission_location,
    cast(a.discharge_location AS VARCHAR) AS discharge_location,
    cast(a.insurance AS VARCHAR) AS insurance,
    cast(a.language AS VARCHAR) AS language,
    cast(a.marital_status AS VARCHAR) AS marital_status,
    cast(a.race AS VARCHAR) AS race,
    datediff('hour', try_cast(a.admittime AS TIMESTAMP), try_cast(a.dischtime AS TIMESTAMP)) AS hospital_los_hours,
    datediff('hour', try_cast(a.admittime AS TIMESTAMP), try_cast(a.dischtime AS TIMESTAMP)) / 24.0 AS hospital_los_days,
    CASE
        WHEN try_cast(a.deathtime AS TIMESTAMP) IS NOT NULL THEN 1
        WHEN try_cast(a.hospital_expire_flag AS INTEGER) = 1 THEN 1
        ELSE 0
    END AS in_hospital_mortality_flag,
    CASE
        WHEN p.anchor_age IS NULL OR p.anchor_year IS NULL OR try_cast(a.admittime AS TIMESTAMP) IS NULL THEN NULL
        ELSE p.anchor_age + (year(try_cast(a.admittime AS TIMESTAMP)) - p.anchor_year)
    END AS age_at_admission
FROM bronze_hosp_admissions a
LEFT JOIN silver_patients p
    ON try_cast(a.subject_id AS BIGINT) = p.subject_id
WHERE try_cast(a.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(a.hadm_id AS BIGINT) IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY try_cast(a.hadm_id AS BIGINT) ORDER BY try_cast(a.admittime AS TIMESTAMP)) = 1;
