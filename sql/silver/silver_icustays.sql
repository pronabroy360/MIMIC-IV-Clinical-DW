CREATE OR REPLACE TABLE silver_icustays AS
WITH typed AS (
    SELECT
        try_cast(subject_id AS BIGINT) AS subject_id,
        try_cast(hadm_id AS BIGINT) AS hadm_id,
        try_cast(stay_id AS BIGINT) AS stay_id,
        cast(first_careunit AS VARCHAR) AS first_careunit,
        cast(last_careunit AS VARCHAR) AS last_careunit,
        try_cast(intime AS TIMESTAMP) AS intime,
        try_cast(outtime AS TIMESTAMP) AS outtime,
        coalesce(
            try_cast(los AS DOUBLE) * 24.0,
            datediff('hour', try_cast(intime AS TIMESTAMP), try_cast(outtime AS TIMESTAMP))
        ) AS icu_los_hours
    FROM bronze_icu_icustays
    WHERE try_cast(subject_id AS BIGINT) IS NOT NULL
      AND try_cast(hadm_id AS BIGINT) IS NOT NULL
      AND try_cast(stay_id AS BIGINT) IS NOT NULL
)
SELECT
    subject_id,
    hadm_id,
    stay_id,
    first_careunit,
    last_careunit,
    intime,
    outtime,
    icu_los_hours,
    icu_los_hours / 24.0 AS icu_los_days,
    CASE
        WHEN row_number() OVER (PARTITION BY subject_id ORDER BY intime NULLS LAST, stay_id) = 1 THEN 1
        ELSE 0
    END AS is_first_icu_stay
FROM typed
QUALIFY row_number() OVER (PARTITION BY stay_id ORDER BY intime NULLS LAST) = 1;
