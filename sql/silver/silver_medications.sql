CREATE OR REPLACE TABLE silver_medications AS
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(starttime AS TIMESTAMP) AS medication_time,
    cast(drug AS VARCHAR) AS medication_name,
    cast(route AS VARCHAR) AS route,
    'prescriptions' AS source_table
FROM bronze_hosp_prescriptions
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL
UNION ALL
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(starttime AS TIMESTAMP) AS medication_time,
    cast(medication AS VARCHAR) AS medication_name,
    cast(route AS VARCHAR) AS route,
    'pharmacy' AS source_table
FROM bronze_hosp_pharmacy
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL
UNION ALL
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(charttime AS TIMESTAMP) AS medication_time,
    cast(medication AS VARCHAR) AS medication_name,
    NULL AS route,
    'emar' AS source_table
FROM bronze_hosp_emar
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL;
