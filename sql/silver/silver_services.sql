CREATE OR REPLACE TABLE silver_services AS
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(transfertime AS TIMESTAMP) AS transfertime,
    cast(prev_service AS VARCHAR) AS prev_service,
    cast(curr_service AS VARCHAR) AS curr_service
FROM bronze_hosp_services
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL
  AND try_cast(hadm_id AS BIGINT) IS NOT NULL;
