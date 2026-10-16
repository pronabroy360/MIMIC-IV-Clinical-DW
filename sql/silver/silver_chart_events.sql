CREATE OR REPLACE TABLE silver_chart_events AS
SELECT
    try_cast(c.subject_id AS BIGINT) AS subject_id,
    try_cast(c.hadm_id AS BIGINT) AS hadm_id,
    try_cast(c.stay_id AS BIGINT) AS stay_id,
    try_cast(c.itemid AS INTEGER) AS itemid,
    try_cast(c.charttime AS TIMESTAMP) AS charttime,
    try_cast(c.storetime AS TIMESTAMP) AS storetime,
    coalesce(cast(d.label AS VARCHAR), cast(c.itemid AS VARCHAR)) AS chart_label,
    try_cast(c.valuenum AS DOUBLE) AS valuenum,
    cast(c.valueuom AS VARCHAR) AS valueuom,
    try_cast(c.warning AS INTEGER) AS warning
FROM bronze_icu_chartevents c
LEFT JOIN bronze_icu_d_items d
    ON try_cast(c.itemid AS INTEGER) = try_cast(d.itemid AS INTEGER)
WHERE try_cast(c.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(c.stay_id AS BIGINT) IS NOT NULL
  AND try_cast(c.itemid AS INTEGER) IS NOT NULL;
