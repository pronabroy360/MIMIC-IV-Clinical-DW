CREATE OR REPLACE TABLE silver_input_events AS
SELECT
    try_cast(i.subject_id AS BIGINT) AS subject_id,
    try_cast(i.hadm_id AS BIGINT) AS hadm_id,
    try_cast(i.stay_id AS BIGINT) AS stay_id,
    try_cast(i.itemid AS INTEGER) AS itemid,
    coalesce(cast(d.label AS VARCHAR), cast(i.itemid AS VARCHAR)) AS input_label,
    try_cast(i.starttime AS TIMESTAMP) AS starttime,
    try_cast(i.endtime AS TIMESTAMP) AS endtime,
    try_cast(i.amount AS DOUBLE) AS amount,
    cast(i.amountuom AS VARCHAR) AS amountuom,
    try_cast(i.rate AS DOUBLE) AS rate,
    cast(i.rateuom AS VARCHAR) AS rateuom,
    cast(i.statusdescription AS VARCHAR) AS statusdescription
FROM bronze_icu_inputevents i
LEFT JOIN bronze_icu_d_items d
    ON try_cast(i.itemid AS INTEGER) = try_cast(d.itemid AS INTEGER)
WHERE try_cast(i.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(i.stay_id AS BIGINT) IS NOT NULL;
