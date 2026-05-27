CREATE OR REPLACE TABLE silver_output_events AS
SELECT
    try_cast(o.subject_id AS BIGINT) AS subject_id,
    try_cast(o.hadm_id AS BIGINT) AS hadm_id,
    try_cast(o.stay_id AS BIGINT) AS stay_id,
    try_cast(o.itemid AS INTEGER) AS itemid,
    coalesce(cast(d.label AS VARCHAR), cast(o.itemid AS VARCHAR)) AS output_label,
    try_cast(o.charttime AS TIMESTAMP) AS charttime,
    try_cast(o.value AS DOUBLE) AS value,
    cast(o.valueuom AS VARCHAR) AS valueuom
FROM bronze_icu_outputevents o
LEFT JOIN bronze_icu_d_items d
    ON try_cast(o.itemid AS INTEGER) = try_cast(d.itemid AS INTEGER)
WHERE try_cast(o.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(o.stay_id AS BIGINT) IS NOT NULL;
