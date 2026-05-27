CREATE OR REPLACE TABLE silver_procedure_events AS
SELECT
    try_cast(p.subject_id AS BIGINT) AS subject_id,
    try_cast(p.hadm_id AS BIGINT) AS hadm_id,
    try_cast(p.stay_id AS BIGINT) AS stay_id,
    try_cast(p.itemid AS INTEGER) AS itemid,
    coalesce(cast(d.label AS VARCHAR), cast(p.itemid AS VARCHAR)) AS procedure_event_label,
    try_cast(p.starttime AS TIMESTAMP) AS starttime,
    try_cast(p.endtime AS TIMESTAMP) AS endtime,
    try_cast(p.value AS DOUBLE) AS value,
    cast(p.valueuom AS VARCHAR) AS valueuom,
    cast(p.location AS VARCHAR) AS location,
    cast(p.statusdescription AS VARCHAR) AS statusdescription
FROM bronze_icu_procedureevents p
LEFT JOIN bronze_icu_d_items d
    ON try_cast(p.itemid AS INTEGER) = try_cast(d.itemid AS INTEGER)
WHERE try_cast(p.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(p.stay_id AS BIGINT) IS NOT NULL;
