CREATE OR REPLACE TABLE silver_procedures AS
SELECT
    try_cast(p.subject_id AS BIGINT) AS subject_id,
    try_cast(p.hadm_id AS BIGINT) AS hadm_id,
    try_cast(p.seq_num AS INTEGER) AS seq_num,
    try_cast(p.chartdate AS DATE) AS chartdate,
    cast(p.icd_code AS VARCHAR) AS icd_code,
    try_cast(p.icd_version AS INTEGER) AS icd_version,
    cast(dp.long_title AS VARCHAR) AS procedure_label
FROM bronze_hosp_procedures_icd p
LEFT JOIN bronze_hosp_d_icd_procedures dp
    ON cast(p.icd_code AS VARCHAR) = cast(dp.icd_code AS VARCHAR)
   AND try_cast(p.icd_version AS INTEGER) = try_cast(dp.icd_version AS INTEGER)
WHERE try_cast(p.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(p.hadm_id AS BIGINT) IS NOT NULL;
