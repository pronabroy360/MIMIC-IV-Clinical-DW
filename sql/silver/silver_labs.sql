CREATE OR REPLACE TABLE silver_labs AS
SELECT
    try_cast(l.subject_id AS BIGINT) AS subject_id,
    try_cast(l.hadm_id AS BIGINT) AS hadm_id,
    try_cast(l.itemid AS INTEGER) AS itemid,
    coalesce(cast(d.label AS VARCHAR), cast(l.itemid AS VARCHAR)) AS lab_label,
    try_cast(l.charttime AS TIMESTAMP) AS charttime,
    try_cast(l.storetime AS TIMESTAMP) AS storetime,
    try_cast(l.valuenum AS DOUBLE) AS valuenum,
    cast(l.valueuom AS VARCHAR) AS valueuom,
    cast(l.flag AS VARCHAR) AS flag,
    CASE
        WHEN l.flag IS NULL THEN 0
        WHEN lower(cast(l.flag AS VARCHAR)) IN ('', 'normal') THEN 0
        ELSE 1
    END AS is_abnormal
FROM bronze_hosp_labevents l
LEFT JOIN bronze_hosp_d_labitems d
    ON try_cast(l.itemid AS INTEGER) = try_cast(d.itemid AS INTEGER)
WHERE try_cast(l.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(l.itemid AS INTEGER) IS NOT NULL;
