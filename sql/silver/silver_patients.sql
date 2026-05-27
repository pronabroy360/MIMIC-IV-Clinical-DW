CREATE OR REPLACE TABLE silver_patients AS
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    upper(cast(gender AS VARCHAR)) AS gender,
    try_cast(anchor_age AS INTEGER) AS anchor_age,
    try_cast(anchor_year AS INTEGER) AS anchor_year,
    cast(anchor_year_group AS VARCHAR) AS anchor_year_group,
    try_cast(dod AS TIMESTAMP) AS dod,
    CASE
        WHEN try_cast(anchor_age AS INTEGER) IS NULL THEN 'unknown'
        WHEN try_cast(anchor_age AS INTEGER) < 18 THEN '<18'
        WHEN try_cast(anchor_age AS INTEGER) BETWEEN 18 AND 44 THEN '18-44'
        WHEN try_cast(anchor_age AS INTEGER) BETWEEN 45 AND 64 THEN '45-64'
        WHEN try_cast(anchor_age AS INTEGER) BETWEEN 65 AND 88 THEN '65-88'
        ELSE '89+'
    END AS derived_age_group
FROM bronze_hosp_patients
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY try_cast(subject_id AS BIGINT) ORDER BY try_cast(subject_id AS BIGINT)) = 1;
