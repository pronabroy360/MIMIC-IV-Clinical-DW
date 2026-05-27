CREATE OR REPLACE TABLE silver_transfers AS
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(transfer_id AS BIGINT) AS transfer_id,
    cast(eventtype AS VARCHAR) AS eventtype,
    cast(careunit AS VARCHAR) AS careunit,
    try_cast(intime AS TIMESTAMP) AS intime,
    try_cast(outtime AS TIMESTAMP) AS outtime,
    datediff('hour', try_cast(intime AS TIMESTAMP), try_cast(outtime AS TIMESTAMP)) AS transfer_los_hours
FROM bronze_hosp_transfers
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL;
